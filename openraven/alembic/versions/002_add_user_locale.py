"""Add locale column to users table.

Revision ID: 002
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(10)))


def downgrade() -> None:
    op.drop_column("users", "locale")
