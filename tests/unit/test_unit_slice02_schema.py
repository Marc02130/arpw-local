"""Slice 2 unit: Alembic paper-centric schema."""

import pytest

from tests.paths import ALEMBIC_INITIAL
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice02,
    pytest.mark.skipif(not slice_ready(2), reason=skip_reason(2)),
]

MINILM = "sentence-transformers/all-MiniLM-L6-v2"


def test_initial_migration_is_paper_centric_minilm() -> None:
    text = ALEMBIC_INITIAL.read_text()
    assert "vector(384)" in text
    assert "CREATE TABLE users" in text
    assert "email = lower(email)" in text
    assert "uuid-ossp" not in text
    assert "auth.users" not in text
    assert "CREATE TABLE threads" not in text
    assert "CREATE EXTENSION IF NOT EXISTS vector" in text
    assert MINILM in text
    assert "hash-384" not in text
    assert "filter_user uuid" in text
    assert "auth.uid()" not in text
    assert "attribution JSONB NOT NULL DEFAULT '[]'" in text
    assert "token_hash TEXT NOT NULL UNIQUE" in text
    assert "ARRAY['literature']::text[]" in text
    assert "chat_provider TEXT NOT NULL DEFAULT 'xai'" in text
    assert "Reference cap of 500 files reached" in text
    assert "Example cap of 10 files reached" in text
    assert "chunk_tsv tsvector GENERATED ALWAYS" in text
    assert "hnsw" not in text.lower()


def test_alembic_applies_vector_extension(postgres_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        names = [
            row[0]
            for row in conn.execute(text("SELECT extname FROM pg_extension")).fetchall()
        ]
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).fetchall()
        }
    assert "vector" in names
    assert "uuid-ossp" not in names
    assert "users" in tables
    assert "references" in tables
    assert "user_papers" in tables
    assert "user_llm_settings" in tables
    assert "threads" not in tables


def test_alembic_vector_dim_and_users_fk(postgres_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        dim = conn.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                WHERE c.relname = 'reference_vectors'
                  AND a.attname = 'vector'
                  AND a.attnum > 0
                """
            )
        ).scalar_one()
        assert dim == "vector(384)"
        fks = conn.execute(
            text(
                """
                SELECT c.relname AS src, p.relname AS dst
                FROM pg_constraint con
                JOIN pg_class c ON con.conrelid = c.oid
                JOIN pg_class p ON con.confrelid = p.oid
                WHERE con.contype = 'f'
                  AND c.relname IN
                    ('references', 'reference_vectors', 'user_papers', 'pinned_passages')
                """
            )
        ).fetchall()
    refs = {row[1] for row in fks}
    assert "users" in refs
    assert "auth.users" not in refs


def test_alembic_users_email_check(postgres_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        check = conn.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'users'::regclass AND contype = 'c'
                """
            )
        ).scalar_one()
    assert "email = lower(email)" in check


def test_match_reference_chunks_defaults_to_minilm(postgres_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        src = conn.execute(
            text(
                """
                SELECT pg_get_functiondef(oid)
                FROM pg_proc
                WHERE proname = 'match_reference_chunks'
                """
            )
        ).scalar_one()
    assert MINILM in src
    assert "hash-384" not in src
    assert "filter_user" in src
    assert "auth.uid()" not in src


def test_ready_selects_one(postgres_url: str) -> None:
    from fastapi.testclient import TestClient

    from app import db
    from app.main import app

    db.configure_engine(postgres_url)
    client = TestClient(app)
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_example_cap_counts_all_rows(postgres_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(postgres_url)
    with engine.begin() as conn:
        user_id = conn.execute(
            text(
                """
                INSERT INTO users (email, password_hash)
                VALUES ('cap@example.com', 'x')
                RETURNING id
                """
            )
        ).scalar_one()
        for i in range(10):
            conn.execute(
                text(
                    """
                    INSERT INTO examples (
                      user_id, file_name, file_size, file_path, file_type, status
                    ) VALUES (
                      :uid, :name, 12, :path, 'text/plain', 'failed'
                    )
                    """
                ),
                {
                    "uid": user_id,
                    "name": f"e{i}.txt",
                    "path": f"{user_id}/{i}.txt",
                },
            )
        with pytest.raises(Exception) as exc:
            conn.execute(
                text(
                    """
                    INSERT INTO examples (
                      user_id, file_name, file_size, file_path, file_type, status
                    ) VALUES (
                      :uid, 'e10.txt', 12, :path, 'text/plain', 'failed'
                    )
                    """
                ),
                {"uid": user_id, "path": f"{user_id}/10.txt"},
            )
    assert "Example cap of 10 files reached" in str(exc.value)
