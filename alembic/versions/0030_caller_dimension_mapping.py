"""Add canonical pricing dimensions and caller mapping profiles.

Revision ID: 0030_caller_dimension_mapping
Revises: 0029_component_calculation_defaults
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0030_caller_dimension_mapping"
down_revision = "0029_component_calculation_defaults"
branch_labels = None
depends_on = None


DIMENSION_TABLE = "charge_pricing_dimension"
MAPPING_TABLE = "charge_caller_mapping_profile"
RATE_BOOK_TABLE = "charge_rate_book"
QUOTE_TABLE = "charge_quote_request"

SYSTEM_DIMENSIONS = (
    (1, "ORIGIN_CODE", "Origin", "origin_code"),
    (2, "DESTINATION_CODE", "Destination", "destination_code"),
    (3, "TRANSPORT_MODE", "Transport mode", "mode"),
    (4, "EQUIPMENT_TYPE", "Equipment type", "equipment_type"),
    (5, "COMMODITY_CODE", "Commodity", "commodity_code"),
    (6, "SERVICE_LEVEL", "Service level", "service_level"),
    (7, "CHARGE_CONTEXT", "Charge context", "charge_context"),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(DIMENSION_TABLE):
        op.create_table(
            DIMENSION_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dimension_code", sa.String(length=80), nullable=False),
            sa.Column("dimension_name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("data_type", sa.String(length=20), nullable=False, server_default="STRING"),
            sa.Column("built_in_field", sa.String(length=80), nullable=True),
            sa.Column("allowed_values_json", sa.JSON(), nullable=True),
            sa.Column("case_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "data_type in ('STRING', 'DECIMAL', 'INTEGER', 'BOOLEAN', 'DATE')",
                name="ck_charge_pricing_dimension_data_type",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("built_in_field"),
            sa.UniqueConstraint("dimension_code"),
        )
        op.create_index(
            "ix_charge_pricing_dimension_active_code",
            DIMENSION_TABLE,
            ["is_active", "dimension_code"],
        )

    inspector = inspect(bind)
    if not inspector.has_table(MAPPING_TABLE):
        op.create_table(
            MAPPING_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("profile_code", sa.String(length=80), nullable=False),
            sa.Column("profile_name", sa.String(length=180), nullable=False),
            sa.Column("caller_system_code", sa.String(length=80), nullable=False),
            sa.Column("schema_version", sa.String(length=40), nullable=False, server_default="1"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("mappings_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("profile_code"),
        )
        op.create_index(
            "ix_charge_caller_mapping_profile_lookup",
            MAPPING_TABLE,
            ["caller_system_code", "schema_version", "is_active"],
        )

    inspector = inspect(bind)
    rate_book_columns = {column["name"] for column in inspector.get_columns(RATE_BOOK_TABLE)}
    if "dimension_codes_json" not in rate_book_columns:
        with op.batch_alter_table(RATE_BOOK_TABLE) as batch_op:
            batch_op.add_column(sa.Column("dimension_codes_json", sa.JSON(), nullable=True))

    quote_columns = {column["name"] for column in inspector.get_columns(QUOTE_TABLE)}
    with op.batch_alter_table(QUOTE_TABLE) as batch_op:
        if "caller_system_code" not in quote_columns:
            batch_op.add_column(sa.Column("caller_system_code", sa.String(length=80), nullable=True))
        if "caller_schema_version" not in quote_columns:
            batch_op.add_column(sa.Column("caller_schema_version", sa.String(length=40), nullable=True))
        if "caller_mapping_profile_code" not in quote_columns:
            batch_op.add_column(sa.Column("caller_mapping_profile_code", sa.String(length=80), nullable=True))
        if "caller_attributes_json" not in quote_columns:
            batch_op.add_column(
                sa.Column("caller_attributes_json", sa.JSON(), nullable=False, server_default="{}")
            )
        if "dimension_values_json" not in quote_columns:
            batch_op.add_column(
                sa.Column("dimension_values_json", sa.JSON(), nullable=False, server_default="{}")
            )

    dimension_table = sa.table(
        DIMENSION_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("dimension_code", sa.String()),
        sa.column("dimension_name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("data_type", sa.String()),
        sa.column("built_in_field", sa.String()),
        sa.column("allowed_values_json", sa.JSON()),
        sa.column("case_sensitive", sa.Boolean()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    existing_codes = {
        str(row[0])
        for row in bind.execute(sa.text(f"SELECT dimension_code FROM {DIMENSION_TABLE}"))
    }
    rows = [
        {
            "id": row_id,
            "dimension_code": code,
            "dimension_name": name,
            "description": f"Built-in LedgerFlow applicability dimension mapped to {field}.",
            "data_type": "STRING",
            "built_in_field": field,
            "allowed_values_json": json.loads("[]"),
            "case_sensitive": False,
            "is_system": True,
            "is_active": True,
        }
        for row_id, code, name, field in SYSTEM_DIMENSIONS
        if code not in existing_codes
    ]
    if rows:
        op.bulk_insert(dimension_table, rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table(QUOTE_TABLE):
        quote_columns = {column["name"] for column in inspector.get_columns(QUOTE_TABLE)}
        with op.batch_alter_table(QUOTE_TABLE) as batch_op:
            for column_name in (
                "dimension_values_json",
                "caller_attributes_json",
                "caller_mapping_profile_code",
                "caller_schema_version",
                "caller_system_code",
            ):
                if column_name in quote_columns:
                    batch_op.drop_column(column_name)
    inspector = inspect(bind)
    if inspector.has_table(RATE_BOOK_TABLE):
        rate_book_columns = {column["name"] for column in inspector.get_columns(RATE_BOOK_TABLE)}
        if "dimension_codes_json" in rate_book_columns:
            with op.batch_alter_table(RATE_BOOK_TABLE) as batch_op:
                batch_op.drop_column("dimension_codes_json")
    inspector = inspect(bind)
    if inspector.has_table(MAPPING_TABLE):
        op.drop_index("ix_charge_caller_mapping_profile_lookup", table_name=MAPPING_TABLE)
        op.drop_table(MAPPING_TABLE)
    inspector = inspect(bind)
    if inspector.has_table(DIMENSION_TABLE):
        op.drop_index("ix_charge_pricing_dimension_active_code", table_name=DIMENSION_TABLE)
        op.drop_table(DIMENSION_TABLE)
