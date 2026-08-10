"""Add explicit rate-entry overrides and resolved component defaults.

Revision ID: 0022_rate_entry_defaults
Revises: 0021_version_rate_books
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0022_rate_entry_defaults"
down_revision = "0021_version_rate_books"
branch_labels = None
depends_on = None


TABLE = "charge_rate_book_entry"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    definitions = (
        sa.Column("basis_override", sa.String(length=40)),
        sa.Column("charge_context", sa.String(length=80)),
        sa.Column("charge_context_override", sa.String(length=80)),
    )
    with op.batch_alter_table(TABLE) as batch_op:
        for definition in definitions:
            if definition.name not in columns:
                batch_op.add_column(definition)

    # The legacy contract required a row basis, so preserve it as an explicit
    # override rather than letting a later component edit change old pricing.
    op.execute(
        sa.text(
            "UPDATE charge_rate_book_entry SET basis_override = basis WHERE basis_override IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE charge_rate_book_entry "
            "SET charge_context = ("
            "SELECT charge_context FROM charge_component "
            "WHERE charge_component.id = charge_rate_book_entry.charge_component_id"
            ") WHERE charge_context IS NULL"
        )
    )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    with op.batch_alter_table(TABLE) as batch_op:
        for column_name in (
            "charge_context_override",
            "charge_context",
            "basis_override",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)
