"""Slice 4 UAT: settings require a confirmed session."""

import uuid

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice04,
    pytest.mark.skipif(not slice_ready(4), reason=skip_reason(4)),
]


def test_settings_401_without_cookie(compose_stack: str) -> None:
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        assert client.get("/api/settings/llm").status_code == 401


def test_unconfirmed_cannot_read_settings(compose_stack: str) -> None:
    email = f"uat-llm-{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "correct-horse-battery",
                "full_name": "UAT User",
            },
        )
        assert registered.status_code == 201
        assert client.get("/api/settings/llm").status_code == 401
