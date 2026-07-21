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
    with op.batch_alter_table("charge_document") as batch_op:
        batch_op.add_column(sa.Column("document_scope_level", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("document_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("source_reference_snapshot_json", sa.JSON(), nullable=True))

    with op.batch_alter_table("charge_line") as batch_op:
        batch_op.add_column(sa.Column("line_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("parent_line_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("line_role", sa.String(length=20), nullable=False, server_default="POSTING"))
        batch_op.add_column(sa.Column("target_level", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("target_object_type", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("target_object_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("charge_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("quantity_uom", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("source_currency", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("source_amount", sa.Numeric(18, 6), nullable=True))
        batch_op.add_column(sa.Column("exchange_rate", sa.Numeric(18, 8), nullable=True))
        batch_op.add_column(sa.Column("exchange_rate_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("charge_text_snapshot", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("allocation_basis", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("allocation_ratio", sa.Numeric(18, 8), nullable=True))
        batch_op.add_column(sa.Column("allocation_driver_value", sa.Numeric(18, 6), nullable=True))
        batch_op.add_column(sa.Column("target_reference_snapshot_json", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_charge_line_parent_line_id",
            "charge_line",
            ["parent_line_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_charge_line_document_line_number",
            ["charge_document_id", "line_number"],
        )
        batch_op.create_check_constraint(
            "ck_charge_line_line_role",
            "line_role in ('CALCULATION', 'POSTING')",
        )
        batch_op.create_check_constraint(
            "ck_charge_line_target_level",
            "target_level is null or target_level in ('HEADER', 'ITEM', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE')",
        )
        batch_op.create_index(
            "ix_charge_line_document_line_number",
            ["charge_document_id", "line_number"],
        )
        batch_op.create_index(
            "ix_charge_line_target",
            ["target_level", "target_object_type", "target_object_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("charge_line") as batch_op:
        batch_op.drop_index("ix_charge_line_target")
        batch_op.drop_index("ix_charge_line_document_line_number")
        batch_op.drop_constraint("ck_charge_line_target_level", type_="check")
        batch_op.drop_constraint("ck_charge_line_line_role", type_="check")
        batch_op.drop_constraint("uq_charge_line_document_line_number", type_="unique")
        batch_op.drop_constraint("fk_charge_line_parent_line_id", type_="foreignkey")
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
            batch_op.drop_column(column_name)
    with op.batch_alter_table("charge_document") as batch_op:
        batch_op.drop_column("source_reference_snapshot_json")
        batch_op.drop_column("document_date")
        batch_op.drop_column("document_scope_level")
