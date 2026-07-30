"""Add target scope mode and selected target references to charge lines.

Revision ID: 0015_charge_line_target_scope_subset
Revises: 0014_charge_line_lifecycle
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0015_charge_line_target_scope_subset"
down_revision = "0014_charge_line_lifecycle"
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
        if "target_scope_mode" not in columns:
            batch_op.add_column(
                sa.Column(
                    "target_scope_mode",
                    sa.String(length=30),
                    nullable=True,
                    server_default="ALL_ELIGIBLE",
                )
            )
        if "selected_target_references_json" not in columns:
            batch_op.add_column(
                sa.Column("selected_target_references_json", sa.JSON(), nullable=True)
            )

    op.execute(
        sa.text(
            """
            UPDATE charge_line
            SET target_scope_mode = COALESCE(NULLIF(target_scope_mode, ''), 'ALL_ELIGIBLE')
            WHERE target_scope_mode IS NULL OR target_scope_mode = ''
            """
        )
    )

    inspector = inspect(bind)
    check_names = _check_constraint_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        if "ck_charge_line_target_scope_mode" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_line_target_scope_mode",
                "target_scope_mode in ('ALL_ELIGIBLE', 'SELECTED_TARGETS')",
            )
        batch_op.alter_column(
            "target_scope_mode",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default="ALL_ELIGIBLE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _table_exists(inspector, "charge_line"):
        return

    columns = _column_names(inspector, "charge_line")
    check_names = _check_constraint_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        if "ck_charge_line_target_scope_mode" in check_names:
            batch_op.drop_constraint("ck_charge_line_target_scope_mode", type_="check")
        if "selected_target_references_json" in columns:
            batch_op.drop_column("selected_target_references_json")
        if "target_scope_mode" in columns:
            batch_op.drop_column("target_scope_mode")
