"""Add charge component aliases and line calculation audit."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_component_alias_audit"
down_revision = "0004_charge_line_framework"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charge_component_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_kind", sa.String(length=60), server_default="CHARGE_PROPOSAL", nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("source_section", sa.String(length=160), nullable=True),
        sa.Column("raw_label", sa.String(length=240), nullable=False),
        sa.Column("normalized_label", sa.String(length=240), nullable=False),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("default_calculation_basis", sa.String(length=40), server_default="DOCUMENT", nullable=False),
        sa.Column("default_charge_level", sa.String(length=40), server_default="SHIPMENT", nullable=False),
        sa.Column("default_allocation_basis", sa.String(length=40), nullable=True),
        sa.Column("default_quantity_uom", sa.String(length=30), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_kind",
            "template_key",
            "source_section",
            "normalized_label",
            name="uq_charge_component_alias_scope_label",
        ),
    )
    op.create_index(
        "ix_charge_component_alias_component",
        "charge_component_alias",
        ["charge_component_id"],
    )
    op.create_index(
        "ix_charge_component_alias_lookup",
        "charge_component_alias",
        ["document_kind", "template_key", "normalized_label"],
    )
    op.add_column("charge_line", sa.Column("calculation_audit_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("charge_line", "calculation_audit_json")
    op.drop_index("ix_charge_component_alias_lookup", table_name="charge_component_alias")
    op.drop_index("ix_charge_component_alias_component", table_name="charge_component_alias")
    op.drop_table("charge_component_alias")
