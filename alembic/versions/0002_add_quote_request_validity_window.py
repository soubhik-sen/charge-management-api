"""Add quote request validity window.

Revision ID: 0002_quote_validity
Revises: 0001_initial_charge_management
Create Date: 2026-05-31 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_quote_validity"
down_revision = "0001_initial_charge_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("charge_quote_request", sa.Column("valid_from", sa.Date(), nullable=True))
    op.add_column("charge_quote_request", sa.Column("valid_to", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("charge_quote_request", "valid_to")
    op.drop_column("charge_quote_request", "valid_from")
