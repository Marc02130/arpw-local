from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_confirmed_user, get_owned_paper
from app.models import PaperReference, User, UserPaper
from app.services import pins as pins_service
from app.services import retrieve as retrieve_service
from app.services.pins import PinError
from app.services.templates import (
    CITATION_STYLES,
    DEFAULT_PAPER_SECTIONS,
    OUTPUT_FORMATS,
    PAPER_SECTIONS,
    PAPER_TYPES,
    is_known_paper_type,
)

router = APIRouter(prefix="/papers", tags=["papers"])


class PaperCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=500)
    paper_type: str


class PaperPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)
    paper_type: str | None = None
    sections: list[str] | None = None
    citation_style: str | None = None
    output_format: str | None = None
    research_prompt: str | None = None
    outline: str | None = None


class RetrieveBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    research_prompt: str = ""
    paper_type: str
    sections: list[str] | None = None

    @field_validator("paper_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if not is_known_paper_type(value):
            raise ValueError("Unknown paper type")
        return value


class PaperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    paper_id: UUID
    title: str
    content: str
    sections: list[str] | None
    paper_type: str
    citation_style: str
    output_format: str
    version: int
    status: str
    research_prompt: str
    outline: str
    attribution: Any
    created_at: datetime
    reference_count: int = 0


class PassageOut(BaseModel):
    vector_id: UUID
    file_id: UUID
    chunk_text: str
    section: str | None
    source_role: str
    score: float
    page: int | None
    chunk_role: str | None
    pinned: bool = False


class PinCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vector_id: UUID
    file_id: UUID
    target_section: str | None = None


class PinOut(BaseModel):
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


def _draft_title(raw: str) -> str:
    title = raw.strip()
    return title if title else "Untitled paper"


def _with_count(session: Session, paper: UserPaper) -> PaperOut:
    count = session.scalar(
        select(func.count())
        .select_from(PaperReference)
        .where(PaperReference.paper_id == paper.paper_id)
    ) or 0
    out = PaperOut.model_validate(paper)
    return out.model_copy(update={"reference_count": int(count)})


@router.get("", response_model=list[PaperOut])
def list_papers(
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> list[PaperOut]:
    rows = session.scalars(
        select(UserPaper)
        .where(UserPaper.user_id == user.id)
        .order_by(UserPaper.created_at.desc())
    ).all()
    return [_with_count(session, row) for row in rows]


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def create_paper(
    body: PaperCreate,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> PaperOut:
    if not is_known_paper_type(body.paper_type):
        raise HTTPException(status_code=422, detail="Unknown paper type")
    paper = UserPaper(
        user_id=user.id,
        title=_draft_title(body.title),
        paper_type=body.paper_type,
        citation_style="APA",
        output_format="markdown",
        sections=list(DEFAULT_PAPER_SECTIONS),
        status="draft",
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return _with_count(session, paper)


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
) -> PaperOut:
    return _with_count(session, paper)


@router.patch("/{paper_id}", response_model=PaperOut)
def patch_paper(
    body: PaperPatch,
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
) -> PaperOut:
    if body.title is not None:
        paper.title = _draft_title(body.title)
    if body.paper_type is not None:
        if not is_known_paper_type(body.paper_type):
            raise HTTPException(status_code=422, detail="Unknown paper type")
        paper.paper_type = body.paper_type
    if body.sections is not None:
        unknown = [s for s in body.sections if s not in PAPER_SECTIONS]
        if unknown:
            raise HTTPException(status_code=422, detail="Unknown paper section")
        paper.sections = body.sections
    if body.citation_style is not None:
        if body.citation_style not in CITATION_STYLES:
            raise HTTPException(status_code=422, detail="Unknown citation style")
        paper.citation_style = body.citation_style
    if body.output_format is not None:
        if body.output_format not in OUTPUT_FORMATS:
            raise HTTPException(status_code=422, detail="Unknown output format")
        paper.output_format = body.output_format
    if body.research_prompt is not None:
        paper.research_prompt = body.research_prompt
    if body.outline is not None:
        paper.outline = body.outline
    session.commit()
    session.refresh(paper)
    return _with_count(session, paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
) -> None:
    session.delete(paper)
    session.commit()


@router.post("/{paper_id}/regenerate", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def regenerate_paper(
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
) -> PaperOut:
    nxt = UserPaper(
        user_id=paper.user_id,
        title=paper.title,
        paper_type=paper.paper_type,
        citation_style=paper.citation_style,
        output_format=paper.output_format,
        sections=list(paper.sections or DEFAULT_PAPER_SECTIONS),
        research_prompt=paper.research_prompt,
        version=paper.version + 1,
        status="draft",
    )
    session.add(nxt)
    session.commit()
    session.refresh(nxt)
    return _with_count(session, nxt)


@router.post("/{paper_id}/retrieve")
def query_sources(
    body: RetrieveBody,
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
    user: User = Depends(get_confirmed_user),
) -> dict[str, list[PassageOut]]:
    passages = retrieve_service.retrieve_for_query_sources(
        session,
        user.id,
        body.paper_type,
        body.research_prompt,
        body.sections,
        paper_id=paper.paper_id,
    )
    return {"passages": [PassageOut.model_validate(p, from_attributes=True) for p in passages]}


@router.get("/{paper_id}/pins", response_model=list[PinOut])
def get_pins(
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
    user: User = Depends(get_confirmed_user),
) -> list[PinOut]:
    return [
        PinOut.model_validate(row, from_attributes=True)
        for row in pins_service.list_pins(session, paper.paper_id, user.id)
    ]


@router.post("/{paper_id}/pins", response_model=PinOut, status_code=status.HTTP_201_CREATED)
def post_pin(
    body: PinCreate,
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
    user: User = Depends(get_confirmed_user),
) -> PinOut:
    try:
        row = pins_service.create_pin(
            session,
            user_id=user.id,
            paper_id=paper.paper_id,
            file_id=body.file_id,
            vector_id=body.vector_id,
            target_section=body.target_section,
        )
    except PinError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return PinOut.model_validate(row, from_attributes=True)


@router.delete("/{paper_id}/pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pin(
    pin_id: UUID,
    paper: UserPaper = Depends(get_owned_paper),
    session: Session = Depends(get_db),
    user: User = Depends(get_confirmed_user),
) -> None:
    try:
        pins_service.delete_pin(session, pin_id, user.id, paper.paper_id)
    except PinError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
