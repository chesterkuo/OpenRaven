"""PostgreSQL database connection and table definitions."""

from sqlalchemy import (
    MetaData, Table, Column, String, Boolean, Integer, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, Text, JSON, create_engine,
)
from sqlalchemy.engine import Engine
from datetime import datetime, timezone

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("avatar_url", String(1024)),
    Column("google_id", String(255), unique=True),
    Column("password_hash", String(255)),
    Column("email_verified", Boolean, default=False),
    Column("locale", String(10)),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    CheckConstraint(
        "google_id IS NOT NULL OR password_hash IS NOT NULL",
        name="auth_method_check",
    ),
)

sessions = Table(
    "sessions", metadata,
    Column("id", String(255), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("is_demo", Boolean, default=False, nullable=False),
    Column("demo_theme", String(50), nullable=True),
)

tenants = Table(
    "tenants", metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("owner_user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("storage_quota_mb", Integer, default=500),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

tenant_members = Table(
    "tenant_members", metadata,
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False, default="owner"),
    UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
)

password_reset_tokens = Table(
    "password_reset_tokens", metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", String(255), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used", Boolean, default=False),
)

audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
    Column("action", String(50), nullable=False),
    Column("details", Text, nullable=True),
    Column("ip_address", String(45), nullable=True),
    Column("timestamp", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

invitations = Table(
    "invitations", metadata,
    Column("id", String(36), primary_key=True),
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    Column("token", String(64), unique=True, nullable=False),
    Column("created_by", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("max_uses", Integer, nullable=True),
    Column("use_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

sync_config = Table(
    "sync_config", metadata,
    Column("tenant_id", String(36), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("passphrase_hash", String(255), nullable=False),
    Column("last_sync_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

conversations = Table(
    "conversations", metadata,
    Column("id", String(36), primary_key=True),
    Column("tenant_id", String(255), nullable=False),
    Column("user_id", String(36), nullable=True),
    Column("session_id", String(255), nullable=True),
    Column("title", String(200), nullable=True),
    Column("demo_theme", String(50), nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

messages = Table(
    "messages", metadata,
    Column("id", String(36), primary_key=True),
    Column("conversation_id", String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(10), nullable=False),
    Column("content", Text, nullable=False),
    Column("sources", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)


def get_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from a database URL."""
    return create_engine(database_url, echo=False)


def create_tables(engine: Engine) -> None:
    """Create all auth tables if they don't exist."""
    metadata.create_all(engine)
