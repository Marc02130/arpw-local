from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_utils import (
    encode_token,
    hash_email_token,
    hash_password,
    new_email_token,
    set_session_cookie,
    clear_session_cookie,
    verify_password,
)
from app.config import settings
from app.db import get_db
from app.deps import get_confirmed_user, get_current_user
from app.mailer import send_confirm_email, send_reset_email
from app.models import EmailToken, User
from app.schemas import (
    AuthCredentials,
    EmailBody,
    FullNameBody,
    RegisterBody,
    RegisterOut,
    ResetPasswordBody,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_GENERIC_FORGOT = "If an account exists for that address, a reset link is on its way."
_GENERIC_RESEND = "If an account needs confirmation, a new email is on its way."
_RESET_INVALID = "This reset link is invalid or has expired"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_email(email: str) -> str:
    lowered = email.strip().lower()
    if not _EMAIL_RE.match(lowered):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    return lowered


def _under_email_rate(session: Session, user_id) -> bool:
    cutoff = _now() - timedelta(hours=1)
    count = session.scalar(
        select(func.count())
        .select_from(EmailToken)
        .where(EmailToken.user_id == user_id, EmailToken.created_at >= cutoff)
    )
    return (count or 0) < settings.AUTH_EMAIL_RATE_PER_HOUR


def _issue_token(session: Session, user: User, purpose: str) -> str:
    session.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )
    raw = new_email_token()
    session.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_email_token(raw),
            expires_at=_now() + timedelta(seconds=settings.EMAIL_TOKEN_TTL_SECONDS),
        )
    )
    return raw


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterBody, session: Session = Depends(get_db)) -> User:
    email = _valid_email(body.email)
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    raw = _issue_token(session, user, "confirm")
    session.commit()
    session.refresh(user)
    send_confirm_email(user.email, raw)
    return user


@router.post("/login", response_model=UserOut)
def login(
    body: AuthCredentials, response: Response, session: Session = Depends(get_db)
) -> User:
    email = body.email.strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.email_confirmed_at is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_confirmed",
                "detail": "Confirm your email before signing in.",
            },
        )
    set_session_cookie(response, encode_token(user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def patch_me(
    body: FullNameBody,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> User:
    user.full_name = body.full_name.strip()
    user.updated_at = _now()
    session.commit()
    session.refresh(user)
    return user


@router.post("/resend-confirmation")
def resend_confirmation(body: EmailBody, session: Session = Depends(get_db)) -> dict[str, str]:
    email = body.email.strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if user is not None and user.email_confirmed_at is None and _under_email_rate(session, user.id):
        raw = _issue_token(session, user, "confirm")
        session.commit()
        send_confirm_email(user.email, raw)
    return {"detail": _GENERIC_RESEND}


@router.get("/confirm")
def confirm(token: str = Query(...), session: Session = Depends(get_db)) -> RedirectResponse:
    invalid = RedirectResponse("/verify-email?error=invalid", status_code=302)
    hashed = hash_email_token(token)
    row = session.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == hashed,
            EmailToken.purpose == "confirm",
        )
    )
    if row is None or row.used_at is not None or row.expires_at < _now():
        return invalid
    user = session.get(User, row.user_id)
    if user is None:
        return invalid
    row.used_at = _now()
    user.email_confirmed_at = _now()
    session.commit()
    return RedirectResponse("/login?confirmed=1", status_code=302)


@router.post("/forgot-password")
def forgot_password(body: EmailBody, session: Session = Depends(get_db)) -> dict[str, str]:
    email = body.email.strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if (
        user is not None
        and user.email_confirmed_at is not None
        and _under_email_rate(session, user.id)
    ):
        raw = _issue_token(session, user, "reset")
        session.commit()
        send_reset_email(user.email, raw)
    return {"detail": _GENERIC_FORGOT}


@router.post("/reset-password", response_model=UserOut)
def reset_password(
    body: ResetPasswordBody, response: Response, session: Session = Depends(get_db)
) -> User:
    hashed = hash_email_token(body.token)
    row = session.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == hashed,
            EmailToken.purpose == "reset",
        )
    )
    if row is None or row.used_at is not None or row.expires_at < _now():
        raise HTTPException(status_code=400, detail=_RESET_INVALID)
    user = session.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail=_RESET_INVALID)
    row.used_at = _now()
    user.password_hash = hash_password(body.password)
    user.updated_at = _now()
    session.commit()
    session.refresh(user)
    set_session_cookie(response, encode_token(user))
    return user
