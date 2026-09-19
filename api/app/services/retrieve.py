from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.services import classify
from app.services import embeddings as embeddings_service
from app.services.templates import PAPER_SECTIONS, build_retrieval_query, get_section_template

MINILM = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60
PINNED_SCORE = 1.0
MATCH_COUNT = 20


@dataclass
class Passage:
    vector_id: UUID
    file_id: UUID
    chunk_text: str
    section: str | None
    source_role: str
    score: float
    page: int | None
    chunk_role: str | None


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"


def _match(
    session: Session,
    user_id: UUID,
    query: str,
    filter_role: str | None,
    prefer_section: str | None,
    k: int = MATCH_COUNT,
) -> list[Passage]:
    vectors = embeddings_service.embed_texts([query])
    if not vectors:
        return []
    rows = session.execute(
        text(
            """
            SELECT vector_id, file_id, chunk_text, section, source_role, score, page, chunk_role
            FROM match_reference_chunks(
              CAST(:emb AS vector),
              :k,
              :filter_user,
              :filter_role,
              :prefer_section,
              :filter_model,
              :query_text
            )
            """
        ),
        {
            "emb": _vector_literal(vectors[0]),
            "k": k,
            "filter_user": str(user_id),
            "filter_role": filter_role,
            "prefer_section": prefer_section,
            "filter_model": settings.EMBEDDING_MODEL or MINILM,
            "query_text": query,
        },
    ).mappings()
    out: list[Passage] = []
    for row in rows:
        role = row["chunk_role"]
        if not role:
            role = classify.classify_chunk(row["chunk_text"] or "", row["section"] or "")
        if role in classify.EXCLUDE_DEFAULT:
            continue
        out.append(
            Passage(
                vector_id=row["vector_id"],
                file_id=row["file_id"],
                chunk_text=row["chunk_text"],
                section=row["section"],
                source_role=row["source_role"],
                score=float(row["score"] or 0),
                page=row["page"],
                chunk_role=role,
            )
        )
    return out


def retrieve_for_section(
    session: Session,
    user_id: UUID,
    paper_type: str,
    section: str,
    research_prompt: str,
) -> list[Passage]:
    template = get_section_template(paper_type, section)
    if template.preferred_source_role == "none":
        return []
    query = build_retrieval_query(paper_type, section, research_prompt)
    role = template.preferred_source_role
    if role == "both":
        return _match(session, user_id, query, None, section)
    if role == "primary":
        primary = _match(session, user_id, query, "primary", section)
        if primary:
            return primary
        return _match(session, user_id, query, "literature", section)
    return _match(session, user_id, query, "literature", section)


def retrieve_for_query_sources(
    session: Session,
    user_id: UUID,
    paper_type: str,
    research_prompt: str,
    sections: list[str] | None,
) -> list[Passage]:
    chosen = [s for s in (sections or list(PAPER_SECTIONS)) if s in PAPER_SECTIONS]
    seen: set[UUID] = set()
    merged: list[Passage] = []
    for section in chosen:
        for passage in retrieve_for_section(
            session, user_id, paper_type, section, research_prompt
        ):
            if passage.vector_id in seen:
                continue
            seen.add(passage.vector_id)
            merged.append(passage)
            if len(merged) >= MATCH_COUNT:
                return merged
    return merged
