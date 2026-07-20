"""Add charge document line framework.

Revision ID: 0004_charge_line_framework
Revises: 0003_contract_header_defaults
Create Date: 2026-06-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_charge_line_framework"
down_revision = "0003_contract_header_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("charge_document", sa.Column("document_scope_level", sa.String(length=30), nullable=True))
    op.add_column("charge_document", sa.Column("document_date", sa.Date(), nullable=True))
    op.add_column("charge_document", sa.Column("source_reference_snapshot_json", sa.JSON(), nullable=True))

    op.add_column("charge_line", sa.Column("line_number", sa.Integer(), nullable=True))
    op.add_column("charge_line", sa.Column("parent_line_id", sa.Integer(), nullable=True))
    op.add_column("charge_line", sa.Column("line_role", sa.String(length=20), nullable=False, server_default="POSTING"))
    op.add_column("charge_line", sa.Column("target_level", sa.String(length=30), nullable=True))
    op.add_column("charge_line", sa.Column("target_object_type", sa.String(length=80), nullable=True))
    op.add_column("charge_line", sa.Column("target_object_id", sa.String(length=120), nullable=True))
    op.add_column("charge_line", sa.Column("charge_date", sa.Date(), nullable=True))
    op.add_column("charge_line", sa.Column("quantity_uom", sa.String(length=30), nullable=True))
    op.add_column("charge_line", sa.Column("source_currency", sa.String(length=3), nullable=True))
    op.add_column("charge_line", sa.Column("source_amount", sa.Numeric(18, 6), nullable=True))
    op.add_column("charge_line", sa.Column("exchange_rate", sa.Numeric(18, 8), nullable=True))
    op.add_column("charge_line", sa.Column("exchange_rate_date", sa.Date(), nullable=True))
    op.add_column("charge_line", sa.Column("charge_text_snapshot", sa.String(length=255), nullable=True))
    op.add_column("charge_line", sa.Column("allocation_basis", sa.String(length=40), nullable=True))
    op.add_column("charge_line", sa.Column("allocation_ratio", sa.Numeric(18, 8), nullable=True))
    op.add_column("charge_line", sa.Column("allocation_driver_value", sa.Numeric(18, 6), nullable=True))
    op.add_column("charge_line", sa.Column("target_reference_snapshot_json", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_charge_line_parent_line_id",
        "charge_line",
        "charge_line",
        ["parent_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_charge_line_document_line_number",
        "charge_line",
        ["charge_document_id", "line_number"],
    )
    op.create_check_constraint(
        "ck_charge_line_line_role",
        "charge_line",
        "line_role in ('CALCULATION', 'POSTING')",
    )
    op.create_check_constraint(
        "ck_charge_line_target_level",
        "charge_line",
        "target_level is null or target_level in ('HEADER', 'ITEM', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE')",
    )
    op.create_index(
        "ix_charge_line_document_line_number",
        "charge_line",
        ["charge_document_id", "line_number"],
    )
    op.create_index(
        "ix_charge_line_target",
        "charge_line",
        ["target_level", "target_object_type", "target_object_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_charge_line_target", table_name="charge_line")
    op.drop_index("ix_charge_line_document_line_number", table_name="charge_line")
    op.drop_constraint("ck_charge_line_target_level", "charge_line", type_="check")
    op.drop_constraint("ck_charge_line_line_role", "charge_line", type_="check")
    op.drop_constraint("uq_charge_line_document_line_number", "charge_line", type_="unique")
    op.drop_constraint("fk_charge_line_parent_line_id", "charge_line", type_="foreignkey")
    for column_name in (
        "target_reference_snapshot_json",
        "allocation_driver_value",
        "allocation_ratio",
        "allocation_basis",
        "charge_text_snapshot",
        "exchange_rate_date",
        "exchange_rate",
        "source_amount",
        "source_currency",
        "quantity_uom",
        "charge_date",
        "target_object_id",
        "target_object_type",
        "target_level",
        "line_role",
        "parent_line_id",
        "line_number",
    ):
        op.drop_column("charge_line", column_name)
    op.drop_column("charge_document", "source_reference_snapshot_json")
    op.drop_column("charge_document", "document_date")
    op.drop_column("charge_document", "document_scope_level")
