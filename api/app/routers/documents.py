from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_confirmed_user
from app.models import Example, Reference, User
from app.services import extract as extract_service
from app.services import files as files_service
from app.services import ingest as ingest_service
from app.services.extract import KIND_MIME, UnsupportedFileType

router = APIRouter(tags=["documents"])


class ReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: UUID
    file_name: str
    file_size: int
    source_role: str
    status: str
    chunk_count: int
    embedding_model: str | None
    error_message: str | None
    citation_text: str | None
    bibliographic: dict[str, Any] | None
    uploaded_at: datetime
    updated_at: datetime


class ExampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: UUID
    file_name: str
    file_size: int
    status: str
    chunk_count: int
    embedding_model: str | None
    error_message: str | None
    uploaded_at: datetime
    updated_at: datetime


class ReferencePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_role: str | None = Field(default=None)
    citation_text: str | None = None


def _cap_message(exc: IntegrityError) -> str | None:
    raw = str(getattr(exc, "orig", exc))
    for message in (
        "Literature cap of 500 files reached",
        "Original research cap of 100 files reached",
        "Example cap of 10 files reached",
    ):
        if message in raw:
            return message
    return None


def _role_cap(source_role: str) -> tuple[int, str]:
    if source_role == "primary":
        return settings.PRIMARY_FILE_CAP, "Original research cap of 100 files reached"
    return settings.LITERATURE_FILE_CAP, "Literature cap of 500 files reached"


def _read_one_file(request: Request, upload: UploadFile) -> tuple[str, bytes, str]:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_UPLOAD_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Request body too large")
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=413, detail="File is empty")
    if len(data) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        kind = extract_service.detect_kind(data)
    except UnsupportedFileType:
        raise HTTPException(status_code=415, detail="Unsupported file type") from None
    name = files_service.display_name(upload.filename)
    if not name.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=415, detail="Unsupported file type")
    return name, data, kind


@router.get("/references", response_model=list[ReferenceOut])
def list_references(
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> list[Reference]:
    ingest_service.mark_stale_references(session, user)
    return list(
        session.scalars(
            select(Reference)
            .where(Reference.user_id == user.id)
            .order_by(Reference.uploaded_at.desc())
        )
    )


@router.post("/references", response_model=ReferenceOut, status_code=status.HTTP_201_CREATED)
def upload_reference(
    request: Request,
    file: UploadFile = File(...),
    source_role: str = Form("literature"),
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> Reference:
    if source_role not in ("literature", "primary"):
        raise HTTPException(status_code=422, detail="source_role must be literature or primary")
    name, data, kind = _read_one_file(request, file)
    session.execute(select(User).where(User.id == user.id).with_for_update())
    cap, cap_detail = _role_cap(source_role)
    count = session.scalar(
        select(func.count())
        .select_from(Reference)
        .where(Reference.user_id == user.id, Reference.source_role == source_role)
    ) or 0
    if count >= cap:
        raise HTTPException(status_code=413, detail=cap_detail)
    file_id = uuid4()
    relative = files_service.new_relative_path(user.id, file_id, kind)
    files_service.write_bytes(relative, data)
    doc = Reference(
        file_id=file_id,
        user_id=user.id,
        file_name=name,
        file_size=len(data),
        file_path=relative,
        file_type=KIND_MIME[kind],
        source_role=source_role,
        status="processing",
    )
    session.add(doc)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        files_service.unlink_if_exists(relative)
        message = _cap_message(exc) or "Could not save file"
        raise HTTPException(status_code=413, detail=message) from None
    session.refresh(doc)
    ingest_service.ingest_reference(session, doc, data, kind)
    row = session.get(Reference, file_id)
    assert row is not None
    return row


@router.patch("/references/{file_id}", response_model=ReferenceOut)
def patch_reference(
    file_id: UUID,
    body: ReferencePatch,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> Reference:
    doc = session.get(Reference, file_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Reference not found")
    if body.source_role is not None:
        if body.source_role not in ("literature", "primary"):
            raise HTTPException(status_code=422, detail="source_role must be literature or primary")
        if body.source_role != doc.source_role:
            cap, cap_detail = _role_cap(body.source_role)
            count = session.scalar(
                select(func.count())
                .select_from(Reference)
                .where(
                    Reference.user_id == user.id,
                    Reference.source_role == body.source_role,
                    Reference.file_id != doc.file_id,
                )
            ) or 0
            if count >= cap:
                raise HTTPException(status_code=413, detail=cap_detail)
        doc.source_role = body.source_role
    if body.citation_text is not None:
        doc.citation_text = body.citation_text
    session.commit()
    session.refresh(doc)
    return doc


@router.delete("/references/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    file_id: UUID,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> Response:
    doc = session.get(Reference, file_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Reference not found")
    relative = doc.file_path
    session.delete(doc)
    session.commit()
    try:
        files_service.unlink_if_exists(relative)
    except ValueError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/examples", response_model=list[ExampleOut])
def list_examples(
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> list[Example]:
    ingest_service.mark_stale_examples(session, user)
    return list(
        session.scalars(
            select(Example).where(Example.user_id == user.id).order_by(Example.uploaded_at.desc())
        )
    )


@router.post("/examples", response_model=ExampleOut, status_code=status.HTTP_201_CREATED)
def upload_example(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> Example:
    name, data, kind = _read_one_file(request, file)
    session.execute(select(User).where(User.id == user.id).with_for_update())
    count = session.scalar(
        select(func.count()).select_from(Example).where(Example.user_id == user.id)
    ) or 0
    if count >= settings.EXAMPLE_FILE_CAP:
        raise HTTPException(status_code=413, detail="Example cap of 10 files reached")
    file_id = uuid4()
    relative = files_service.new_relative_path(user.id, file_id, kind)
    files_service.write_bytes(relative, data)
    doc = Example(
        file_id=file_id,
        user_id=user.id,
        file_name=name,
        file_size=len(data),
        file_path=relative,
        file_type=KIND_MIME[kind],
        status="processing",
    )
    session.add(doc)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        files_service.unlink_if_exists(relative)
        message = _cap_message(exc) or "Could not save file"
        raise HTTPException(status_code=413, detail=message) from None
    session.refresh(doc)
    ingest_service.ingest_example(session, doc, data, kind)
    row = session.get(Example, file_id)
    assert row is not None
    return row


@router.delete("/examples/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_example(
    file_id: UUID,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> Response:
    doc = session.get(Example, file_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Example not found")
    relative = doc.file_path
    session.delete(doc)
    session.commit()
    try:
        files_service.unlink_if_exists(relative)
    except ValueError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
