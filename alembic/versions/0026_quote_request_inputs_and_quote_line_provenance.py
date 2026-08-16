"""Add quote request calculation inputs and quote line provenance.

Revision ID: 0026_quote_request_inputs_quote_line_provenance
Revises: 0025_rate_book_template_schema
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0026_quote_request_inputs_quote_line_provenance"
down_revision = "0025_rate_book_template_schema"
branch_labels = None
depends_on = None


QUOTE_REQUEST_TABLE = "charge_quote_request"
QUOTE_OPTION_LINE_TABLE = "charge_quote_option_line"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table(QUOTE_REQUEST_TABLE):
        columns = {column["name"] for column in inspector.get_columns(QUOTE_REQUEST_TABLE)}
        with op.batch_alter_table(QUOTE_REQUEST_TABLE) as batch_op:
            if "calculation_inputs_json" not in columns:
                batch_op.add_column(sa.Column("calculation_inputs_json", sa.JSON(), nullable=True))
            if "component_calculation_inputs_json" not in columns:
                batch_op.add_column(sa.Column("component_calculation_inputs_json", sa.JSON(), nullable=True))
            if "date_values_json" not in columns:
                batch_op.add_column(sa.Column("date_values_json", sa.JSON(), nullable=True))
        op.execute(
            sa.text(
                "UPDATE charge_quote_request "
                "SET calculation_inputs_json = COALESCE(calculation_inputs_json, '{}'), "
                "component_calculation_inputs_json = COALESCE(component_calculation_inputs_json, '{}'), "
                "date_values_json = COALESCE(date_values_json, '[]')"
            )
        )
        with op.batch_alter_table(QUOTE_REQUEST_TABLE) as batch_op:
            batch_op.alter_column("calculation_inputs_json", existing_type=sa.JSON(), nullable=False)
            batch_op.alter_column(
                "component_calculation_inputs_json",
                existing_type=sa.JSON(),
                nullable=False,
            )
            batch_op.alter_column("date_values_json", existing_type=sa.JSON(), nullable=False)

    inspector = inspect(bind)
    if inspector.has_table(QUOTE_OPTION_LINE_TABLE):
        columns = {column["name"] for column in inspector.get_columns(QUOTE_OPTION_LINE_TABLE)}
        foreign_keys = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys(QUOTE_OPTION_LINE_TABLE)
            if foreign_key.get("name")
        }
        with op.batch_alter_table(QUOTE_OPTION_LINE_TABLE) as batch_op:
            if "source_contract_line_id" not in columns:
                batch_op.add_column(sa.Column("source_contract_line_id", sa.Integer(), nullable=True))
            if "source_calculation_template_id" not in columns:
                batch_op.add_column(sa.Column("source_calculation_template_id", sa.Integer(), nullable=True))
            if "source_calculation_template_step_id" not in columns:
                batch_op.add_column(sa.Column("source_calculation_template_step_id", sa.Integer(), nullable=True))
            if "fk_charge_quote_option_line_source_contract_line" not in foreign_keys:
                batch_op.create_foreign_key(
                    "fk_charge_quote_option_line_source_contract_line",
                    "charge_contract_line",
                    ["source_contract_line_id"],
                    ["id"],
                )
            if "fk_charge_quote_option_line_source_calc_template" not in foreign_keys:
                batch_op.create_foreign_key(
                    "fk_charge_quote_option_line_source_calc_template",
                    "charge_calculation_template",
                    ["source_calculation_template_id"],
                    ["id"],
                )
            if "fk_charge_quote_option_line_source_calc_template_step" not in foreign_keys:
                batch_op.create_foreign_key(
                    "fk_charge_quote_option_line_source_calc_template_step",
                    "charge_calculation_template_step",
                    ["source_calculation_template_step_id"],
                    ["id"],
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table(QUOTE_OPTION_LINE_TABLE):
        columns = {column["name"] for column in inspector.get_columns(QUOTE_OPTION_LINE_TABLE)}
        foreign_keys = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys(QUOTE_OPTION_LINE_TABLE)
            if foreign_key.get("name")
        }
        with op.batch_alter_table(QUOTE_OPTION_LINE_TABLE) as batch_op:
            if "fk_charge_quote_option_line_source_calc_template_step" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_quote_option_line_source_calc_template_step",
                    type_="foreignkey",
                )
            if "fk_charge_quote_option_line_source_calc_template" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_quote_option_line_source_calc_template",
                    type_="foreignkey",
                )
            if "fk_charge_quote_option_line_source_contract_line" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_quote_option_line_source_contract_line",
                    type_="foreignkey",
                )
            for column_name in (
                "source_calculation_template_step_id",
                "source_calculation_template_id",
                "source_contract_line_id",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    inspector = inspect(bind)
    if inspector.has_table(QUOTE_REQUEST_TABLE):
        columns = {column["name"] for column in inspector.get_columns(QUOTE_REQUEST_TABLE)}
        with op.batch_alter_table(QUOTE_REQUEST_TABLE) as batch_op:
            for column_name in (
                "date_values_json",
                "component_calculation_inputs_json",
                "calculation_inputs_json",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)
