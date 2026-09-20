from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://arpw:changeme@127.0.0.1:5432/arpw"
    JWT_SECRET: str = "dev-only-change-me-32-bytes-min!!"
    JWT_TTL_SECONDS: int = 604800
    COOKIE_NAME: str = "arpw_session"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_PATH: str = "/"
    PUBLIC_ORIGINS: str = "http://localhost:8082,http://localhost:3001"
    CORS_ORIGINS: str = ""
    PUBLIC_APP_URL: str = "http://localhost:8082"
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    XAI_CHAT_MODEL: str = "grok-4.3"
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    ANTHROPIC_CHAT_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_API_URL: str = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION: str = "2023-06-01"
    CHAT_TIMEOUT_SECONDS: int = 120
    CHAT_MAX_TOKENS: int = 4096
    CHAT_TEMPERATURE: float = 0.2
    MAX_FILE_SIZE: int = 10_485_760
    MAX_UPLOAD_BODY_BYTES: int = 12_582_912
    LITERATURE_FILE_CAP: int = 500
    PRIMARY_FILE_CAP: int = 100
    EXAMPLE_FILE_CAP: int = 10
    UPLOAD_BATCH_SIZE: int = 10
    SPA_UPLOAD_CONCURRENCY: int = 10
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MIN_CHUNK_CHARS: int = 50
    MAX_CONTENT_CHARS: int = 2_000_000
    MAX_CHUNKS_PER_DOCUMENT: int = 2000
    STALE_PROCESSING_SECONDS: int = 600
    UPLOAD_ROOT: str = "/data/uploads"
    SMTP_HOST: str = "mail"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "noreply@localhost"
    EMAIL_TOKEN_TTL_SECONDS: int = 3600
    AUTH_EMAIL_RATE_PER_HOUR: int = 30
    BCRYPT_ROUNDS: int = 12
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    @model_validator(mode="after")
    def reject_wildcard_origins(self) -> "Settings":
        public = [o.strip() for o in self.PUBLIC_ORIGINS.split(",") if o.strip()]
        if not public or "*" in public:
            raise ValueError("PUBLIC_ORIGINS must be a non-empty allowlist without *")
        cors = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if "*" in cors:
            raise ValueError("CORS_ORIGINS must not contain *")
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return self

    @property
    def public_origin_list(self) -> list[str]:
        return [o.strip() for o in self.PUBLIC_ORIGINS.split(",") if o.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
