from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import decrypt_secret, encrypt_secret
from app.models import User, UserLlmSettings

PROVIDERS = ("openai", "xai", "anthropic")
CHAT_MODELS = {
    "openai": settings.OPENAI_CHAT_MODEL,
    "xai": settings.XAI_CHAT_MODEL,
    "anthropic": settings.ANTHROPIC_CHAT_MODEL,
}
MIN_KEY_LEN = 10


def looks_like_path(value: str) -> bool:
    trimmed = value.strip()
    if not trimmed:
        return False
    if trimmed.startswith("/") or trimmed.startswith("./") or trimmed.startswith("../"):
        return True
    if trimmed.lower().startswith("file:"):
        return True
    if "\\" in trimmed:
        return True
    return False


def validate_key(provider: str, raw: str) -> str:
    trimmed = raw.strip()
    if looks_like_path(trimmed):
        raise ValueError("API key looks like a file path")
    if len(trimmed) < MIN_KEY_LEN:
        raise ValueError("API key appears to be too short")
    if provider == "xai" and not trimmed.startswith("xai-"):
        raise ValueError("xAI API key must start with xai-")
    return trimmed


def get_or_create_settings(session: Session, user: User) -> UserLlmSettings:
    row = session.get(UserLlmSettings, user.id)
    if row is None:
        row = UserLlmSettings(user_id=user.id, chat_provider="xai")
        session.add(row)
        session.flush()
    return row


def configured_map(row: UserLlmSettings | None) -> dict[str, bool]:
    return {
        "openai": bool(row and row.openai_key_enc),
        "xai": bool(row and row.xai_key_enc),
        "anthropic": bool(row and row.anthropic_key_enc),
    }


def last4_map(row: UserLlmSettings | None) -> dict[str, str | None]:
    return {
        "openai": row.openai_last4 if row else None,
        "xai": row.xai_last4 if row else None,
        "anthropic": row.anthropic_last4 if row else None,
    }


def resolve_key(row: UserLlmSettings | None, provider: str) -> str | None:
    """Decrypt the user-row key only. No env fallback."""
    if row is None:
        return None
    enc = None
    if provider == "openai":
        enc = row.openai_key_enc
    elif provider == "xai":
        enc = row.xai_key_enc
    elif provider == "anthropic":
        enc = row.anthropic_key_enc
    if not enc:
        return None
    return decrypt_secret(enc)


def _set_key(row: UserLlmSettings, provider: str, value: str | None) -> None:
    if value is None:
        return
    if value.strip() == "":
        cipher, last4 = None, None
    else:
        plain = validate_key(provider, value)
        cipher, last4 = encrypt_secret(plain), plain[-4:]
    if provider == "openai":
        row.openai_key_enc = cipher
        row.openai_last4 = last4
    elif provider == "xai":
        row.xai_key_enc = cipher
        row.xai_last4 = last4
    else:
        row.anthropic_key_enc = cipher
        row.anthropic_last4 = last4


def apply_update(
    session: Session,
    user: User,
    *,
    openai_api_key: str | None = None,
    xai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    chat_provider: str | None = None,
) -> UserLlmSettings:
    row = get_or_create_settings(session, user)
    _set_key(row, "openai", openai_api_key)
    _set_key(row, "xai", xai_api_key)
    _set_key(row, "anthropic", anthropic_api_key)
    if chat_provider is not None:
        if chat_provider not in PROVIDERS:
            raise ValueError("invalid chat_provider")
        row.chat_provider = chat_provider
    flags = configured_map(row)
    if not flags.get(row.chat_provider):
        if chat_provider is not None:
            raise ValueError(f"no API key configured for {chat_provider}")
        for name in PROVIDERS:
            if flags[name]:
                row.chat_provider = name
                break
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return row
