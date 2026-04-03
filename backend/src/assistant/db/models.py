from __future__ import annotations

from datetime import datetime, timezone, UTC

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    memory_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    sensitivity_class: Mapped[str] = mapped_column(String(50), default="none")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_memory_source_updated", "source_type", "updated_at"),
        Index("ix_memory_active", "deleted_at"),
    )


class SourceDocument(Base):
    __tablename__ = "source_documents"

    source_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="")
    sync_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="pending")
    consent_snapshot: Mapped[str] = mapped_column(String(50), default="granted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class BrowserCapture(Base):
    __tablename__ = "browser_captures"

    capture_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="")
    selected_text: Mapped[str] = mapped_column(Text, default="")
    full_page_content_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capture_mode: Mapped[str] = mapped_column(String(50), default="selection")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TaskRecord(Base):
    __tablename__ = "task_records"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), default="user")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created")
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (Index("ix_task_status_due", "status", "due_at"),)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    topic_tags: Mapped[str] = mapped_column(Text, default="[]")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (Index("ix_msg_session", "session_id", "created_at"),)


class NoteItem(Base):
    __tablename__ = "note_items"

    note_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="[]")
    sensitivity_level: Mapped[str] = mapped_column(String(50), default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class RoutingEvent(Base):
    __tablename__ = "routing_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sensitivity_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    chosen_model: Mapped[str] = mapped_column(String(100), nullable=False)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (Index("ix_routing_created_sensitivity", "created_at", "sensitivity_decision"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor: Mapped[str] = mapped_column(String(200), default="user")
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(200), nullable=False)
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (Index("ix_audit_created", "created_at"),)


class UserSettings(Base):
    __tablename__ = "user_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    updated_by: Mapped[str] = mapped_column(String(200), default="user")
