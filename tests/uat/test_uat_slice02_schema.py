"""Slice 2 UAT: pgvector extension and paper-centric tables in the running DB."""

import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice02,
    pytest.mark.skipif(not slice_ready(2), reason=skip_reason(2)),
]


def test_vector_extension_and_users_fk(compose_stack: str) -> None:
    from tests import compose_support

    dx = compose_support.psql(r"\dx")
    assert "vector" in dx

    chunks = compose_support.psql(r"\d reference_vectors")
    assert "384" in chunks
    assert "file_id" in chunks
    assert "auth.users" not in chunks

    refs = compose_support.psql(r'\d "references"')
    assert "user_id" in refs
    assert "users" in refs
    assert "auth.users" not in refs

    users = compose_support.psql(r"\d users")
    assert "email" in users
    assert "email_confirmed_at" in users

    tables = compose_support.psql(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
    )
    assert "threads" not in tables

    check = compose_support.psql(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'users'::regclass AND contype = 'c';"
    )
    assert "email = lower(email)" in check


def test_ready_selects_one(compose_stack: str) -> None:
    import httpx

    response = httpx.get(f"{compose_stack}/api/ready", timeout=5.0)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
