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
    with op.batch_alter_table("charge_rate_contract") as batch_op:
        batch_op.add_column(sa.Column("default_rate_book_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("default_calculation_template_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_charge_rate_contract_default_rate_book",
            "charge_rate_book",
            ["default_rate_book_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_charge_rate_contract_default_calculation_template",
            "charge_calculation_template",
            ["default_calculation_template_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("charge_rate_contract") as batch_op:
        batch_op.drop_constraint(
            "fk_charge_rate_contract_default_calculation_template",
            type_="foreignkey",
        )
        batch_op.drop_constraint("fk_charge_rate_contract_default_rate_book", type_="foreignkey")
        batch_op.drop_column("default_calculation_template_id")
        batch_op.drop_column("default_rate_book_id")
