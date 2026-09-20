from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterrogationTurn, User
from app.services import chat as chat_service
from app.services import citations as citations_service
from app.services import llm_keys
from app.services import retrieve as retrieve_service
from app.services.chat import MissingLlmKey

NO_LITERATURE_MATCH = (
    "No passages matched. Upload and index research papers (literature) on the Upload tab."
)
NO_SELECTED_MATCH = "No passages matched in the sources you included."
ALLOWED_SOURCES = ("literature", "primary", "examples")


def parse_sources(body: dict) -> list[str]:
    raw = body.get("sources")
    leftover = body.get("filter_role")
    if leftover in ("literature", "primary", "both") and not raw:
        if leftover == "both":
            raw = ["literature", "primary"]
        else:
            raw = [leftover]
    if not isinstance(raw, list) or not raw:
        return ["literature"]
    out: list[str] = []
    for item in raw:
        if item in ALLOWED_SOURCES and item not in out:
            out.append(item)
    return out or ["literature"]


def build_prompt(question: str, source_block: str) -> str:
    return (
        "You are helping a researcher inspect their own uploaded corpus. "
        "Answer the question using only the retrieved sources. Cite with [S#] ids "
        "exactly as given. Do not invent ids. If the sources do not support an answer, "
        "say so and include no [S#] citations.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved sources (cite only these ids, like [S1]):\n{source_block}"
    )


def empty_message(sources: list[str]) -> str:
    if "literature" in sources:
        return NO_LITERATURE_MATCH
    return NO_SELECTED_MATCH


def interrogate(
    session: Session,
    user: User,
    paper_id: UUID,
    question: str,
    sources: list[str],
) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Enter a question")
    if len(question) > 8000:
        raise ValueError("Question is too long")
    row = llm_keys.get_or_create_settings(session, user)
    key = llm_keys.resolve_key(row, row.chat_provider)
    if not key:
        raise MissingLlmKey(row.chat_provider)
    passages = retrieve_service.retrieve_for_interrogate(
        session, user.id, question, sources
    )
    numbered = citations_service.number_sources(passages)
    if not numbered:
        answer = empty_message(sources)
    else:
        prompt = build_prompt(question, citations_service.format_sources_for_prompt(numbered))
        raw = chat_service.complete(prompt, user, row)
        answer = citations_service.strip_unknown_citations(
            raw, citations_service.allowed_sid_set(numbered)
        )
    payload = [
        {
            "vector_id": str(p.vector_id),
            "file_id": str(p.file_id),
            "chunk_text": p.chunk_text,
            "section": p.section,
            "source_role": p.source_role,
            "score": p.score,
            "page": p.page,
            "chunk_role": p.chunk_role,
            "sid": f"S{i + 1}",
        }
        for i, p in enumerate(passages)
    ]
    session.add(
        InterrogationTurn(
            user_id=user.id,
            paper_id=paper_id,
            role="user",
            content=question,
            sources=sources,
            filter_role=_legacy_filter(sources),
            passages=[],
        )
    )
    session.add(
        InterrogationTurn(
            user_id=user.id,
            paper_id=paper_id,
            role="assistant",
            content=answer,
            sources=sources,
            filter_role=_legacy_filter(sources),
            passages=payload,
        )
    )
    session.commit()
    return {"answer": answer, "passages": payload, "sources": sources}


def _legacy_filter(sources: list[str]) -> str | None:
    has_l = "literature" in sources
    has_p = "primary" in sources
    if has_l and has_p:
        return "both"
    if has_l:
        return "literature"
    if has_p:
        return "primary"
    return None


def list_turns(session: Session, paper_id: UUID, user_id) -> list[InterrogationTurn]:
    return list(
        session.scalars(
            select(InterrogationTurn)
            .where(
                InterrogationTurn.paper_id == paper_id,
                InterrogationTurn.user_id == user_id,
            )
            .order_by(InterrogationTurn.created_at.asc())
        )
    )
