"""Slice 3 unit: register/login/confirm/reset cookie JWT."""

from __future__ import annotations

import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import bcrypt
import pytest

from tests.paths import AUTH_ROUTER
from tests.slices import skip_reason, slice_ready

pytestmark = [
    pytest.mark.unit,
    pytest.mark.slice03,
    pytest.mark.skipif(not slice_ready(3), reason=skip_reason(3)),
]


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _register(client, monkeypatch, **kwargs):
    captured: dict[str, str] = {}

    def fake_send(to: str, subject: str, body: str) -> None:
        captured["to"] = to
        captured["subject"] = subject
        captured["body"] = body

    monkeypatch.setattr("app.mailer.send_mail", fake_send)
    email = kwargs.get("email") or _email()
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": kwargs.get("password", "correct-horse"),
            "full_name": kwargs.get("full_name", "Ada Lovelace"),
        },
    )
    return response, captured


def _token_from_body(body: str) -> str:
    for part in body.split():
        if "token=" in part:
            return parse_qs(urlparse(part.strip()).query)["token"][0]
    raise AssertionError(f"no token in mail body: {body!r}")


def test_auth_router_exists() -> None:
    text = AUTH_ROUTER.read_text()
    utils = (AUTH_ROUTER.parents[1] / "auth_utils.py").read_text()
    assert "register" in text
    assert "login" in text
    assert "logout" in text
    assert "httponly" in utils.lower()
    assert "set_session_cookie" in text
    assert "needs_email_confirmation" in text or "RegisterOut" in text


def test_register_does_not_set_cookie(client, monkeypatch) -> None:
    response, captured = _register(client, monkeypatch)
    assert response.status_code == 201
    body = response.json()
    assert body["needs_email_confirmation"] is True
    assert body["email_confirmed_at"] is None
    assert "password_hash" not in body
    assert "jwt" not in response.text.lower()
    assert "access_token" not in body
    cookie = response.headers.get("set-cookie", "")
    assert "arpw_session=" not in cookie
    assert captured["subject"] == "Confirm Your Email"
    me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_login_unconfirmed_is_403(client, monkeypatch) -> None:
    email = _email()
    _register(client, monkeypatch, email=email)
    login = client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse"}
    )
    assert login.status_code == 403
    detail = login.json()["detail"]
    assert detail["code"] == "email_not_confirmed"


def test_confirm_then_login_cookie_flags(client, monkeypatch) -> None:
    email = _email()
    registered, captured = _register(client, monkeypatch, email=email)
    raw = _token_from_body(captured["body"])
    confirm = client.get(f"/api/auth/confirm?token={raw}", follow_redirects=False)
    assert confirm.status_code == 302
    assert confirm.headers["location"] == "/login?confirmed=1"
    login = client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse"}
    )
    assert login.status_code == 200
    cookie = login.headers.get("set-cookie", "")
    assert "arpw_session=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "path=/" in cookie.lower()
    assert "domain=" not in cookie.lower()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["email_confirmed_at"] is not None


def test_invalid_confirm_redirects(client) -> None:
    response = client.get("/api/auth/confirm?token=not-a-real-token", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/verify-email?error=invalid"


def test_logout_without_cookie_and_expired_cookie(client, monkeypatch) -> None:
    bare = client.post("/api/auth/logout")
    assert bare.status_code == 204
    cookie = bare.headers.get("set-cookie", "")
    assert "arpw_session=" in cookie.lower() or "max-age=0" in cookie.lower()
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "path=/" in cookie.lower()
    assert "domain=" not in cookie.lower()

    from app.auth_utils import encode_token
    from app.models import User

    email = _email()
    created, captured = _register(client, monkeypatch, email=email)
    raw = _token_from_body(captured["body"])
    client.get(f"/api/auth/confirm?token={raw}", follow_redirects=False)
    user = User(id=created.json()["id"], email=email, password_hash="x")
    expired = encode_token(user, expires_delta=timedelta(seconds=-10))
    client.cookies.set("arpw_session", expired)
    out = client.post("/api/auth/logout")
    assert out.status_code == 204
    assert "max-age=0" in out.headers.get("set-cookie", "").lower()


def test_duplicate_email_409(client, monkeypatch) -> None:
    email = _email()
    _register(client, monkeypatch, email=email)
    again, _ = _register(client, monkeypatch, email=email.upper())
    assert again.status_code == 409


def test_short_password_422(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": _email(), "password": "short", "full_name": "Ada Lovelace"},
    )
    assert response.status_code == 422


def test_unknown_email_hits_dummy_bcrypt(client, monkeypatch) -> None:
    from app import auth_utils

    seen: list[bytes] = []
    real = bcrypt.checkpw

    def wrapped(password: bytes, hashed: bytes) -> bool:
        seen.append(hashed)
        return real(password, hashed)

    monkeypatch.setattr(auth_utils.bcrypt, "checkpw", wrapped)
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 401
    assert seen
    assert seen[0] == auth_utils.DUMMY_HASH


def test_user_id_in_body_is_422(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": _email(),
            "password": "correct-horse",
            "full_name": "Ada Lovelace",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422


def test_resend_and_forgot_always_200(client) -> None:
    resend = client.post(
        "/api/auth/resend-confirmation", json={"email": "missing@example.com"}
    )
    assert resend.status_code == 200
    forgot = client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})
    assert forgot.status_code == 200


def test_reset_password_sets_cookie(client, monkeypatch) -> None:
    email = _email()
    registered, confirm_mail = _register(client, monkeypatch, email=email)
    raw_confirm = _token_from_body(confirm_mail["body"])
    client.get(f"/api/auth/confirm?token={raw_confirm}", follow_redirects=False)
    captured: dict[str, str] = {}

    def fake_send(to: str, subject: str, body: str) -> None:
        captured["subject"] = subject
        captured["body"] = body

    monkeypatch.setattr("app.mailer.send_mail", fake_send)
    forgot = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    assert captured["subject"] == "Reset Your Password"
    raw_reset = _token_from_body(captured["body"])
    reset = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset, "password": "new-horse-battery"},
    )
    assert reset.status_code == 200
    assert "arpw_session=" in reset.headers.get("set-cookie", "")
    login = client.post(
        "/api/auth/login", json={"email": email, "password": "new-horse-battery"}
    )
    assert login.status_code == 200


def test_origin_allowlist_on_forgot(client) -> None:
    payload = {"email": "csrf@example.com"}
    ok_3001 = client.post(
        "/api/auth/forgot-password",
        json=payload,
        headers={"Origin": "http://localhost:3001"},
    )
    assert ok_3001.status_code == 200
    ok_8082 = client.post(
        "/api/auth/forgot-password",
        json=payload,
        headers={"Origin": "http://localhost:8082"},
    )
    assert ok_8082.status_code == 200
    evil = client.post(
        "/api/auth/forgot-password",
        json=payload,
        headers={"Origin": "http://evil.example"},
    )
    assert evil.status_code == 403


def test_cors_middleware_not_mounted() -> None:
    from app.main import app

    names = [getattr(m, "cls", type(m)).__name__ for m in app.user_middleware]
    assert "CORSMiddleware" not in names
