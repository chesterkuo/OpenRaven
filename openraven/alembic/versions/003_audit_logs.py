"""Audit logs table.

Revision ID: 003
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_tenant_timestamp", "audit_logs", ["tenant_id", sa.text("timestamp DESC")])


def downgrade() -> None:
    op.drop_index("ix_audit_tenant_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
