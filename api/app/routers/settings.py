from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_confirmed_user
from app.models import User
from app.schemas import LlmProviderStatus, LlmSettingsOut, LlmSettingsUpdate
from app.services import llm_keys

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_out(row) -> LlmSettingsOut:
    flags = llm_keys.configured_map(row)
    last4 = llm_keys.last4_map(row)
    return LlmSettingsOut(
        openai=LlmProviderStatus(configured=flags["openai"], last4=last4["openai"]),
        xai=LlmProviderStatus(configured=flags["xai"], last4=last4["xai"]),
        anthropic=LlmProviderStatus(configured=flags["anthropic"], last4=last4["anthropic"]),
        chat_provider=row.chat_provider if row else "xai",
        chat_models=dict(llm_keys.CHAT_MODELS),
    )


@router.get("/llm", response_model=LlmSettingsOut)
def get_llm_settings(
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> LlmSettingsOut:
    row = llm_keys.get_or_create_settings(session, user)
    session.commit()
    return _to_out(row)


@router.put("/llm", response_model=LlmSettingsOut)
def put_llm_settings(
    body: LlmSettingsUpdate,
    user: User = Depends(get_confirmed_user),
    session: Session = Depends(get_db),
) -> LlmSettingsOut:
    try:
        row = llm_keys.apply_update(
            session,
            user,
            openai_api_key=body.openai_api_key,
            xai_api_key=body.xai_api_key,
            anthropic_api_key=body.anthropic_api_key,
            chat_provider=body.chat_provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _to_out(row)
