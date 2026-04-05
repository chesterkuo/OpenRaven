"""Initial auth tables.

Revision ID: 001
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(1024)),
        sa.Column("google_id", sa.String(255), unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("email_verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("google_id IS NOT NULL OR password_hash IS NOT NULL", name="auth_method_check"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_quota_mb", sa.Integer, default=500),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tenant_members",
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, default=False),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("tenant_members")
    op.drop_table("tenants")
    op.drop_table("sessions")
    op.drop_table("users")
