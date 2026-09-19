from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=6, max_length=1024)


class RegisterBody(AuthCredentials):
    full_name: str = Field(min_length=2, max_length=200)


class EmailBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)


class ResetPasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=8, max_length=256)
    password: str = Field(min_length=6, max_length=1024)


class FullNameBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    email_confirmed_at: datetime | None
    created_at: datetime


class RegisterOut(UserOut):
    needs_email_confirmation: bool = True


class LlmProviderStatus(BaseModel):
    configured: bool
    last4: str | None = None


class LlmSettingsOut(BaseModel):
    openai: LlmProviderStatus
    xai: LlmProviderStatus
    anthropic: LlmProviderStatus
    chat_provider: str
    chat_models: dict[str, str]


class LlmSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    openai_api_key: str | None = None
    xai_api_key: str | None = None
    anthropic_api_key: str | None = None
    chat_provider: str | None = None
