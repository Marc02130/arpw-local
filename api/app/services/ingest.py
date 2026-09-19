from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Example, ExampleVector, Reference, ReferenceVector, User
from app.services import classify, embeddings as embeddings_service
from app.services import chunk as chunk_service
from app.services import extract as extract_service
from app.services.extract import KIND_MIME


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ingest_reference(session: Session, doc: Reference, data: bytes, kind: str) -> None:
    try:
        chunks = _prepare_chunks(data, kind)
        vectors = embeddings_service.embed_texts([c.text for c in chunks])
        for piece, vector in zip(chunks, vectors, strict=True):
            session.add(
                ReferenceVector(
                    file_id=doc.file_id,
                    vector=vector,
                    chunk_text=piece.text,
                    chunk_index=piece.chunk_index,
                    section=piece.section,
                    page=piece.page,
                    embedding_model=settings.EMBEDDING_MODEL,
                    chunk_role=piece.chunk_role,
                )
            )
        doc.status = "ready"
        doc.chunk_count = len(chunks)
        doc.embedding_model = settings.EMBEDDING_MODEL
        doc.error_message = None
        doc.file_type = KIND_MIME[kind]
        doc.updated_at = _now()
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        fail_reference(session, doc.file_id, str(exc))


def ingest_example(session: Session, doc: Example, data: bytes, kind: str) -> None:
    try:
        chunks = _prepare_chunks(data, kind)
        vectors = embeddings_service.embed_texts([c.text for c in chunks])
        for piece, vector in zip(chunks, vectors, strict=True):
            session.add(
                ExampleVector(
                    file_id=doc.file_id,
                    vector=vector,
                    chunk_text=piece.text,
                    chunk_index=piece.chunk_index,
                    section=piece.section,
                    page=piece.page,
                    embedding_model=settings.EMBEDDING_MODEL,
                    chunk_role=piece.chunk_role,
                )
            )
        doc.status = "ready"
        doc.chunk_count = len(chunks)
        doc.embedding_model = settings.EMBEDDING_MODEL
        doc.error_message = None
        doc.file_type = KIND_MIME[kind]
        doc.updated_at = _now()
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        fail_example(session, doc.file_id, str(exc))


def _prepare_chunks(data: bytes, kind: str):
    pages = extract_service.extract_pages(data, kind)
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("empty extract")
    if len(text) > settings.MAX_CONTENT_CHARS:
        raise ValueError("extracted text too large")
    chunks = chunk_service.chunk_pages(pages)
    kept = []
    for item in chunks:
        if classify.is_junk_chunk(item.text, item.section):
            continue
        item.chunk_role = classify.classify_chunk(item.text, item.section)
        kept.append(item)
    if not kept:
        raise ValueError("no usable text after dropping junk chunks")
    if len(kept) > settings.MAX_CHUNKS_PER_DOCUMENT:
        raise ValueError("too many chunks")
    for index, item in enumerate(kept):
        item.chunk_index = index
    return kept


def fail_reference(session: Session, file_id: UUID, message: str) -> None:
    doc = session.get(Reference, file_id)
    if doc is None:
        return
    session.execute(delete(ReferenceVector).where(ReferenceVector.file_id == file_id))
    doc.status = "failed"
    doc.chunk_count = 0
    doc.error_message = message
    doc.updated_at = _now()
    session.commit()


def fail_example(session: Session, file_id: UUID, message: str) -> None:
    doc = session.get(Example, file_id)
    if doc is None:
        return
    session.execute(delete(ExampleVector).where(ExampleVector.file_id == file_id))
    doc.status = "failed"
    doc.chunk_count = 0
    doc.error_message = message
    doc.updated_at = _now()
    session.commit()


def mark_stale_references(session: Session, user: User) -> None:
    from datetime import timedelta

    cutoff = _now() - timedelta(seconds=settings.STALE_PROCESSING_SECONDS)
    rows = session.scalars(
        select(Reference).where(
            Reference.user_id == user.id,
            Reference.status == "processing",
            Reference.updated_at < cutoff,
        )
    ).all()
    for doc in rows:
        fail_reference(session, doc.file_id, "ingest timed out")


def mark_stale_examples(session: Session, user: User) -> None:
    from datetime import timedelta

    cutoff = _now() - timedelta(seconds=settings.STALE_PROCESSING_SECONDS)
    rows = session.scalars(
        select(Example).where(
            Example.user_id == user.id,
            Example.status == "processing",
            Example.updated_at < cutoff,
        )
    ).all()
    for doc in rows:
        fail_example(session, doc.file_id, "ingest timed out")
