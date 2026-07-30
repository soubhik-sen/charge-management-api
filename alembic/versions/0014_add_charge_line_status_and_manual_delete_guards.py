"""Add charge line lifecycle status for manual deletion and document locking.

Revision ID: 0014_charge_line_lifecycle
Revises: 0013_add_charge_calculation_profiles
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0014_charge_line_lifecycle"
down_revision = "0013_add_charge_calculation_profiles"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _check_constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint.get("name")
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    } if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _table_exists(inspector, "charge_line"):
        return

    columns = _column_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        if "source" not in columns:
            batch_op.add_column(
                sa.Column("source", sa.String(length=40), nullable=True)
            )
        if "status" not in columns:
            batch_op.add_column(
                sa.Column("status", sa.String(length=30), nullable=True, server_default="ESTIMATED")
            )

    op.execute(
        sa.text(
            """
            UPDATE charge_line
            SET source = CASE
                WHEN source_quote_option_line_id IS NOT NULL THEN 'QUOTE'
                ELSE 'DIRECT'
            END
            WHERE source IS NULL OR source = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE charge_line
            SET status = COALESCE(
                (
                    SELECT charge_document.status
                    FROM charge_document
                    WHERE charge_document.id = charge_line.charge_document_id
                ),
                'ESTIMATED'
            )
            WHERE status IS NULL
            """
        )
    )

    inspector = inspect(bind)
    check_names = _check_constraint_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=40),
            nullable=False,
            server_default="MANUAL",
        )
        if "ck_charge_line_status" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_line_status",
                "status in ('ESTIMATED', 'ACCRUED', 'ACTUAL', 'DISPUTED', 'APPROVED', 'EXPORTED', 'REVERSED')",
            )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default="ESTIMATED",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _table_exists(inspector, "charge_line"):
        return

    columns = _column_names(inspector, "charge_line")
    check_names = _check_constraint_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        if "ck_charge_line_status" in check_names:
            batch_op.drop_constraint("ck_charge_line_status", type_="check")
        if "status" in columns:
            batch_op.drop_column("status")
        if "source" in columns:
            batch_op.drop_column("source")
