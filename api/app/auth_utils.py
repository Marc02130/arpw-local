from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from app.config import settings
from app.models import User

_DUMMY_PASSWORD = "dummy-password-not-a-real-login"
DUMMY_HASH = bcrypt.hashpw(
    hashlib.sha256(_DUMMY_PASSWORD.encode()).hexdigest().encode(),
    bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
)


def sha256_hex(password: str) -> bytes:
    return hashlib.sha256(password.encode()).hexdigest().encode()


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(sha256_hex(password), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS))
    return hashed.decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    hashed = password_hash.encode() if password_hash else DUMMY_HASH
    return bcrypt.checkpw(sha256_hex(password), hashed)


def cookie_kwargs() -> dict:
    return {
        "key": settings.COOKIE_NAME,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(value=token, max_age=settings.JWT_TTL_SECONDS, **cookie_kwargs())


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(**cookie_kwargs())


def encode_token(user: User, *, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(seconds=settings.JWT_TTL_SECONDS))
    return jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "iat": now,
            "exp": exp,
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )


def decode_token(token: str) -> uuid.UUID:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    return uuid.UUID(payload["sub"])


def new_email_token() -> str:
    return secrets.token_urlsafe(32)


def hash_email_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
