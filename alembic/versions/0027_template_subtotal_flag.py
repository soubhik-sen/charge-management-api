"""Control whether template step results accumulate into subtotals.

Revision ID: 0027_template_subtotal_flag
Revises: 0026_quote_request_inputs_quote_line_provenance
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0027_template_subtotal_flag"
down_revision = "0026_quote_request_inputs_quote_line_provenance"
branch_labels = None
depends_on = None


TABLE_NAME = "charge_calculation_template_step"
COLUMN_NAME = "accumulate_result_in_subtotal"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME in columns:
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.add_column(
            sa.Column(
                COLUMN_NAME,
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME not in columns:
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_column(COLUMN_NAME)
