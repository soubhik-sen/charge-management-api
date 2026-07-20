"""Add contract header defaults.

Revision ID: 0003_contract_header_defaults
Revises: 0002_quote_validity
Create Date: 2026-06-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_contract_header_defaults"
down_revision = "0002_quote_validity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "charge_rate_contract",
        sa.Column(
            "default_rate_book_id",
            sa.Integer(),
            sa.ForeignKey("charge_rate_book.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "charge_rate_contract",
        sa.Column(
            "default_calculation_template_id",
            sa.Integer(),
            sa.ForeignKey("charge_calculation_template.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("charge_rate_contract", "default_calculation_template_id")
    op.drop_column("charge_rate_contract", "default_rate_book_id")
