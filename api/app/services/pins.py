from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ExampleVector, PinnedPassage, Reference, ReferenceVector
from app.services.templates import PAPER_SECTIONS


class PinError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class PinRow:
    pin_id: UUID
    paper_id: UUID
    file_id: UUID
    vector_id: UUID
    target_section: str | None
    created_at: datetime
    file_name: str
    source_role: str
    chunk_text: str
    section: str | None
    page: int | None
    chunk_role: str | None


def parse_target_section(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if value == "Interrogate":
        raise PinError("Invalid pin target section")
    if value not in PAPER_SECTIONS:
        raise PinError("Invalid pin target section")
    return value


def list_pins(session: Session, paper_id: UUID, user_id: UUID) -> list[PinRow]:
    rows = session.execute(
        select(PinnedPassage, Reference, ReferenceVector)
        .join(Reference, Reference.file_id == PinnedPassage.file_id)
        .join(ReferenceVector, ReferenceVector.vector_id == PinnedPassage.vector_id)
        .where(PinnedPassage.paper_id == paper_id, PinnedPassage.user_id == user_id)
        .order_by(PinnedPassage.created_at.asc())
    ).all()
    return [
        PinRow(
            pin_id=pin.pin_id,
            paper_id=pin.paper_id,
            file_id=pin.file_id,
            vector_id=pin.vector_id,
            target_section=pin.target_section,
            created_at=pin.created_at,
            file_name=ref.file_name,
            source_role=ref.source_role,
            chunk_text=vec.chunk_text,
            section=vec.section,
            page=vec.page,
            chunk_role=vec.chunk_role,
        )
        for pin, ref, vec in rows
    ]


def create_pin(
    session: Session,
    *,
    user_id: UUID,
    paper_id: UUID,
    file_id: UUID,
    vector_id: UUID,
    target_section: str | None,
) -> PinRow:
    target = parse_target_section(target_section)
    if session.get(ExampleVector, vector_id) is not None:
        raise PinError("Can only pin your own reference chunks", 400)
    vec = session.get(ReferenceVector, vector_id)
    if vec is None or vec.file_id != file_id:
        raise PinError("Can only pin your own reference chunks", 400)
    ref = session.get(Reference, file_id)
    if ref is None or ref.user_id != user_id:
        raise PinError("Can only pin your own reference chunks", 400)
    pin = PinnedPassage(
        user_id=user_id,
        paper_id=paper_id,
        file_id=file_id,
        vector_id=vector_id,
        target_section=target,
    )
    session.add(pin)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == "23505":
            raise PinError("Already pinned", 409) from exc
        raise PinError("Can only pin your own reference chunks", 400) from exc
    session.refresh(pin)
    return PinRow(
        pin_id=pin.pin_id,
        paper_id=pin.paper_id,
        file_id=pin.file_id,
        vector_id=pin.vector_id,
        target_section=pin.target_section,
        created_at=pin.created_at,
        file_name=ref.file_name,
        source_role=ref.source_role,
        chunk_text=vec.chunk_text,
        section=vec.section,
        page=vec.page,
        chunk_role=vec.chunk_role,
    )


def delete_pin(session: Session, pin_id: UUID, user_id: UUID, paper_id: UUID) -> None:
    pin = session.get(PinnedPassage, pin_id)
    if pin is None or pin.user_id != user_id or pin.paper_id != paper_id:
        raise PinError("Pin not found", 404)
    session.delete(pin)
    session.commit()
