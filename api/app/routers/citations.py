from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_confirmed_user
from app.models import User
from app.routers.documents import ReferenceOut
from app.services import bibliographic as bibliographic_service

router = APIRouter(prefix="/citations", tags=["citations"])


class LookupBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: UUID | None = None
    doi: str | None = None
    pmid: str | None = None


@router.post("/lookup", response_model=ReferenceOut)
def lookup_citation(
    body: LookupBody,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> ReferenceOut:
    try:
        doc = bibliographic_service.lookup_for_file(session, user.id, body.file_id, body.doi)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ReferenceOut.model_validate(doc)
