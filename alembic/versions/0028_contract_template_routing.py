"""Add header-template routing and deterministic contract selection.

Revision ID: 0028_contract_template_routing
Revises: 0027_template_subtotal_flag
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0028_contract_template_routing"
down_revision = "0027_template_subtotal_flag"
branch_labels = None
depends_on = None


CONTRACT_TABLE = "charge_rate_contract"
ROUTE_TABLE = "charge_contract_template_route"
QUOTE_LINE_TABLE = "charge_quote_option_line"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table(CONTRACT_TABLE):
        contract_columns = {column["name"] for column in inspector.get_columns(CONTRACT_TABLE)}
        if "selection_priority" not in contract_columns:
            with op.batch_alter_table(CONTRACT_TABLE) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "selection_priority",
                        sa.Integer(),
                        nullable=False,
                        server_default="100",
                    )
                )

    inspector = inspect(bind)
    if not inspector.has_table(ROUTE_TABLE):
        op.create_table(
            ROUTE_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=False),
            sa.Column("calculation_template_id", sa.Integer(), nullable=False),
            sa.Column("route_number", sa.Integer(), nullable=False),
            sa.Column("origin_code", sa.String(length=40), nullable=True),
            sa.Column("destination_code", sa.String(length=40), nullable=True),
            sa.Column("mode", sa.String(length=40), nullable=True),
            sa.Column("equipment_type", sa.String(length=60), nullable=True),
            sa.Column("commodity_code", sa.String(length=80), nullable=True),
            sa.Column("service_level", sa.String(length=80), nullable=True),
            sa.Column("charge_context", sa.String(length=80), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.ForeignKeyConstraint(
                ["calculation_template_id"],
                ["charge_calculation_template.id"],
                name="fk_contract_template_route_template",
            ),
            sa.ForeignKeyConstraint(
                ["contract_id"],
                ["charge_rate_contract.id"],
                name="fk_contract_template_route_contract",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "contract_id",
                "route_number",
                name="uq_charge_contract_template_route_number",
            ),
        )
        op.create_index(
            "ix_charge_contract_template_route_contract",
            ROUTE_TABLE,
            ["contract_id", "priority"],
        )
        op.create_index(
            "ix_charge_contract_template_route_scope",
            ROUTE_TABLE,
            ["origin_code", "destination_code", "mode"],
        )

    inspector = inspect(bind)
    if inspector.has_table(QUOTE_LINE_TABLE):
        quote_line_columns = {column["name"] for column in inspector.get_columns(QUOTE_LINE_TABLE)}
        foreign_keys = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys(QUOTE_LINE_TABLE)
            if foreign_key.get("name")
        }
        with op.batch_alter_table(QUOTE_LINE_TABLE) as batch_op:
            if "source_contract_template_route_id" not in quote_line_columns:
                batch_op.add_column(
                    sa.Column("source_contract_template_route_id", sa.Integer(), nullable=True)
                )
            if "fk_quote_line_contract_template_route" not in foreign_keys:
                batch_op.create_foreign_key(
                    "fk_quote_line_contract_template_route",
                    ROUTE_TABLE,
                    ["source_contract_template_route_id"],
                    ["id"],
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table(QUOTE_LINE_TABLE):
        quote_line_columns = {column["name"] for column in inspector.get_columns(QUOTE_LINE_TABLE)}
        foreign_keys = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys(QUOTE_LINE_TABLE)
            if foreign_key.get("name")
        }
        with op.batch_alter_table(QUOTE_LINE_TABLE) as batch_op:
            if "fk_quote_line_contract_template_route" in foreign_keys:
                batch_op.drop_constraint("fk_quote_line_contract_template_route", type_="foreignkey")
            if "source_contract_template_route_id" in quote_line_columns:
                batch_op.drop_column("source_contract_template_route_id")

    inspector = inspect(bind)
    if inspector.has_table(ROUTE_TABLE):
        op.drop_index("ix_charge_contract_template_route_scope", table_name=ROUTE_TABLE)
        op.drop_index("ix_charge_contract_template_route_contract", table_name=ROUTE_TABLE)
        op.drop_table(ROUTE_TABLE)

    inspector = inspect(bind)
    if inspector.has_table(CONTRACT_TABLE):
        contract_columns = {column["name"] for column in inspector.get_columns(CONTRACT_TABLE)}
        if "selection_priority" in contract_columns:
            with op.batch_alter_table(CONTRACT_TABLE) as batch_op:
                batch_op.drop_column("selection_priority")
