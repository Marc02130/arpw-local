"""Slice 3 UAT: register does not set a cookie; Origin allowlist."""

import uuid

import httpx
import pytest

from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.uat,
    pytest.mark.slice03,
    pytest.mark.skipif(not slice_ready(3), reason=skip_reason(3)),
]


def test_register_does_not_set_cookie(compose_stack: str) -> None:
    email = f"uat-{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "correct-horse-battery",
                "full_name": "UAT User",
            },
        )
        assert response.status_code == 201
        cookie = response.headers.get("set-cookie", "")
        assert "arpw_session=" not in cookie
        assert "access_token" not in response.json()
        assert response.json()["needs_email_confirmation"] is True
        me = client.get("/api/auth/me")
        assert me.status_code == 401
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": "correct-horse-battery"},
        )
        assert login.status_code == 403


def test_origin_allowlist_default_env(compose_stack: str) -> None:
    payload = {"email": f"uat-origin-{uuid.uuid4().hex[:8]}@example.com"}
    with httpx.Client(base_url=compose_stack, timeout=10.0) as client:
        assert (
            client.post(
                "/api/auth/forgot-password",
                json=payload,
                headers={"Origin": "http://localhost:3001"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/auth/forgot-password",
                json=payload,
                headers={"Origin": "http://localhost:8082"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/auth/forgot-password",
                json=payload,
                headers={"Origin": "http://evil.example"},
            ).status_code
            == 403
        )
