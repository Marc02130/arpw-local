import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="users_email_lower"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    llm_settings: Mapped["UserLlmSettings | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class UserLlmSettings(Base):
    __tablename__ = "user_llm_settings"
    __table_args__ = (
        CheckConstraint(
            "chat_provider IN ('openai', 'xai', 'anthropic')",
            name="user_llm_settings_chat_provider_check",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    openai_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    xai_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    openai_last4: Mapped[str | None] = mapped_column(Text, nullable=True)
    xai_last4: Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_last4: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_provider: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'xai'")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="llm_settings")


class EmailToken(Base):
    __tablename__ = "email_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('confirm', 'reset')", name="email_tokens_purpose_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Reference(Base):
    __tablename__ = "references"
    __table_args__ = (
        UniqueConstraint("file_id", "user_id", name="references_file_id_user_id_key"),
        CheckConstraint("document_type = 'reference'", name="references_document_type_check"),
        CheckConstraint("file_name ~* '\\.(pdf|docx|txt)$'", name="references_file_name_ext"),
        CheckConstraint(
            "file_size > 0 AND file_size <= 10485760", name="references_file_size_check"
        ),
        CheckConstraint(
            "source_role IN ('literature', 'primary')", name="references_source_role_check"
        ),
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')", name="references_status_check"
        ),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'reference'")
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_role: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'literature'")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'processing'")
    )
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bibliographic: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    vectors: Mapped[list["ReferenceVector"]] = relationship(
        back_populates="reference", cascade="all, delete-orphan"
    )


class Example(Base):
    __tablename__ = "examples"
    __table_args__ = (
        UniqueConstraint("file_id", "user_id", name="examples_file_id_user_id_key"),
        CheckConstraint("document_type = 'example'", name="examples_document_type_check"),
        CheckConstraint("file_name ~* '\\.(pdf|docx|txt)$'", name="examples_file_name_ext"),
        CheckConstraint(
            "file_size > 0 AND file_size <= 10485760", name="examples_file_size_check"
        ),
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')", name="examples_status_check"
        ),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'example'")
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'processing'")
    )
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    vectors: Mapped[list["ExampleVector"]] = relationship(
        back_populates="example", cascade="all, delete-orphan"
    )


class ReferenceVector(Base):
    __tablename__ = "reference_vectors"
    __table_args__ = (
        UniqueConstraint("vector_id", "file_id", name="reference_vectors_vector_id_file_id_key"),
    )

    vector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("references.file_id", ondelete="CASCADE"),
        nullable=False,
    )
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', chunk_text)", persisted=True)
    )

    reference: Mapped[Reference] = relationship(back_populates="vectors")


class ExampleVector(Base):
    __tablename__ = "example_vectors"
    __table_args__ = (
        UniqueConstraint("vector_id", "file_id", name="example_vectors_vector_id_file_id_key"),
    )

    vector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examples.file_id", ondelete="CASCADE"),
        nullable=False,
    )
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', chunk_text)", persisted=True)
    )

    example: Mapped[Example] = relationship(back_populates="vectors")


class UserPaper(Base):
    __tablename__ = "user_papers"
    __table_args__ = (
        UniqueConstraint("paper_id", "user_id", name="user_papers_paper_id_user_id_key"),
        CheckConstraint(
            "paper_type IN ("
            "'Empirical Study', 'Literature Review', 'Theoretical Paper', 'Case Study')",
            name="user_papers_paper_type_check",
        ),
        CheckConstraint(
            "citation_style IN ('APA', 'MLA', 'Chicago')",
            name="user_papers_citation_style_check",
        ),
        CheckConstraint(
            "output_format IN ('markdown', 'word')", name="user_papers_output_format_check"
        ),
        CheckConstraint("status IN ('draft', 'completed')", name="user_papers_status_check"),
    )

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    sections: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    paper_type: Mapped[str] = mapped_column(Text, nullable=False)
    citation_style: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'APA'")
    )
    output_format: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'markdown'")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    research_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    outline: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    attribution: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PaperReference(Base):
    __tablename__ = "paper_references"

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_papers.paper_id", ondelete="CASCADE"),
        primary_key=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("references.file_id", ondelete="CASCADE"),
        primary_key=True,
    )


class PinnedPassage(Base):
    __tablename__ = "pinned_passages"
    __table_args__ = (
        UniqueConstraint("paper_id", "vector_id", name="pinned_passages_paper_vector_key"),
        ForeignKeyConstraint(
            ["paper_id", "user_id"],
            ["user_papers.paper_id", "user_papers.user_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["file_id", "user_id"],
            ["references.file_id", "references.user_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["vector_id", "file_id"],
            ["reference_vectors.vector_id", "reference_vectors.file_id"],
            ondelete="CASCADE",
        ),
    )

    pin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class InterrogationTurn(Base):
    __tablename__ = "interrogation_turns"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="interrogation_turns_role_check"),
        ForeignKeyConstraint(
            ["paper_id", "user_id"],
            ["user_papers.paper_id", "user_papers.user_id"],
            ondelete="CASCADE",
        ),
    )

    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY['literature']::text[]")
    )
    filter_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    passages: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
