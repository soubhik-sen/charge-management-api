"""Add immutable FX and rate-row provenance to quote option lines.

Revision ID: 0017_quote_line_fx_provenance
Revises: 0016_align_charge_runtime
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0017_quote_line_fx_provenance"
down_revision = "0016_align_charge_runtime"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _columns("charge_quote_option_line")
    if not existing:
        return
    definitions = [
        sa.Column("source_currency", sa.String(length=3)),
        sa.Column("source_amount", sa.Numeric(18, 6)),
        sa.Column("exchange_rate", sa.Numeric(18, 8)),
        sa.Column("exchange_rate_date", sa.Date()),
        sa.Column(
            "fx_rate_id",
            sa.Integer(),
            sa.ForeignKey("charge_fx_rate.id", name="fk_quote_line_fx_rate"),
        ),
        sa.Column("exchange_rate_source_code", sa.String(length=60)),
        sa.Column("exchange_rate_type", sa.String(length=20)),
        sa.Column("exchange_rate_method", sa.String(length=60)),
        sa.Column(
            "source_rate_book_entry_id",
            sa.Integer(),
            sa.ForeignKey(
                "charge_rate_book_entry.id",
                name="fk_quote_line_source_rate_book_entry",
            ),
        ),
        sa.Column("is_statistical", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]
    with op.batch_alter_table("charge_quote_option_line") as batch_op:
        for definition in definitions:
            if definition.name not in existing:
                batch_op.add_column(definition)
        check_names = {
            constraint["name"]
            for constraint in inspect(op.get_bind()).get_check_constraints("charge_quote_option_line")
            if constraint.get("name")
        }
        if "ck_charge_quote_option_line_exchange_rate_type" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_quote_option_line_exchange_rate_type",
                "exchange_rate_type is null or exchange_rate_type in ('MID', 'BUY', 'SELL', 'CUSTOM')",
            )


def downgrade() -> None:
    existing = _columns("charge_quote_option_line")
    if not existing:
        return
    check_names = {
        constraint["name"]
        for constraint in inspect(op.get_bind()).get_check_constraints("charge_quote_option_line")
        if constraint.get("name")
    }
    with op.batch_alter_table("charge_quote_option_line") as batch_op:
        if "ck_charge_quote_option_line_exchange_rate_type" in check_names:
            batch_op.drop_constraint(
                "ck_charge_quote_option_line_exchange_rate_type",
                type_="check",
            )
        for column_name in (
            "is_statistical",
            "source_rate_book_entry_id",
            "exchange_rate_method",
            "exchange_rate_type",
            "exchange_rate_source_code",
            "fx_rate_id",
            "exchange_rate_date",
            "exchange_rate",
            "source_amount",
            "source_currency",
        ):
            if column_name in existing:
                batch_op.drop_column(column_name)
