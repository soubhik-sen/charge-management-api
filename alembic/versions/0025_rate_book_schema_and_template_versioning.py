"""Add component-scoped rate books and version calculation templates.

Revision ID: 0025_rate_book_template_schema
Revises: 0024_road_business_dates
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0025_rate_book_template_schema"
down_revision = "0024_road_business_dates"
branch_labels = None
depends_on = None


RATE_BOOK_TABLE = "charge_rate_book"
TEMPLATE_TABLE = "charge_calculation_template"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table(RATE_BOOK_TABLE):
        columns = {column["name"] for column in inspector.get_columns(RATE_BOOK_TABLE)}
        with op.batch_alter_table(RATE_BOOK_TABLE) as batch_op:
            if "charge_component_id" not in columns:
                batch_op.add_column(sa.Column("charge_component_id", sa.Integer()))
                batch_op.create_foreign_key(
                    "fk_charge_rate_book_component",
                    "charge_component",
                    ["charge_component_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "row_attribute_keys_json" not in columns:
                batch_op.add_column(sa.Column("row_attribute_keys_json", sa.JSON()))
        op.execute(
            sa.text(
                "UPDATE charge_rate_book SET charge_component_id = ("
                "SELECT MIN(entry.charge_component_id) "
                "FROM charge_rate_book_entry AS entry "
                "WHERE entry.rate_book_id = charge_rate_book.id "
                "HAVING COUNT(DISTINCT entry.charge_component_id) = 1"
                ") WHERE charge_component_id IS NULL"
            )
        )

    inspector = inspect(op.get_bind())
    if not inspector.has_table(TEMPLATE_TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TEMPLATE_TABLE)}
    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TEMPLATE_TABLE)
        if constraint.get("name")
    }
    with op.batch_alter_table(TEMPLATE_TABLE) as batch_op:
        if "version_number" not in columns:
            batch_op.add_column(
                sa.Column("version_number", sa.Integer(), nullable=False, server_default="1")
            )
        if "supersedes_calculation_template_id" not in columns:
            batch_op.add_column(sa.Column("supersedes_calculation_template_id", sa.Integer()))
            batch_op.create_foreign_key(
                "fk_charge_calculation_template_supersedes",
                TEMPLATE_TABLE,
                ["supersedes_calculation_template_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "lock_version" not in columns:
            batch_op.add_column(
                sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1")
            )
        if "published_at" not in columns:
            batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True)))
        if "uq_charge_calculation_template_code" in unique_names:
            batch_op.drop_constraint("uq_charge_calculation_template_code", type_="unique")
        if "uq_charge_calculation_template_code_version" not in unique_names:
            batch_op.create_unique_constraint(
                "uq_charge_calculation_template_code_version",
                ["template_code", "version_number"],
            )
    op.execute(
        sa.text(
            "UPDATE charge_calculation_template "
            "SET status = 'PUBLISHED', published_at = COALESCE(published_at, CURRENT_TIMESTAMP) "
            "WHERE UPPER(status) IN ('ACTIVE', 'RELEASED')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE charge_calculation_template SET status = 'RETIRED' "
            "WHERE UPPER(status) = 'INACTIVE'"
        )
    )
    indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(TEMPLATE_TABLE)}
    if "ix_charge_calculation_template_code_version" not in indexes:
        op.create_index(
            "ix_charge_calculation_template_code_version",
            TEMPLATE_TABLE,
            ["template_code", "version_number"],
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table(TEMPLATE_TABLE):
        columns = {column["name"] for column in inspector.get_columns(TEMPLATE_TABLE)}
        unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints(TEMPLATE_TABLE)
            if constraint.get("name")
        }
        indexes = {index["name"] for index in inspector.get_indexes(TEMPLATE_TABLE)}
        op.execute(
            sa.text(
                "UPDATE charge_calculation_template SET status = 'ACTIVE' "
                "WHERE UPPER(status) = 'PUBLISHED'"
            )
        )
        if "ix_charge_calculation_template_code_version" in indexes:
            op.drop_index(
                "ix_charge_calculation_template_code_version",
                table_name=TEMPLATE_TABLE,
            )
        with op.batch_alter_table(TEMPLATE_TABLE) as batch_op:
            if "uq_charge_calculation_template_code_version" in unique_names:
                batch_op.drop_constraint(
                    "uq_charge_calculation_template_code_version",
                    type_="unique",
                )
            if "uq_charge_calculation_template_code" not in unique_names:
                batch_op.create_unique_constraint(
                    "uq_charge_calculation_template_code",
                    ["template_code"],
                )
            for column_name in (
                "published_at",
                "lock_version",
                "supersedes_calculation_template_id",
                "version_number",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    inspector = inspect(op.get_bind())
    if inspector.has_table(RATE_BOOK_TABLE):
        columns = {column["name"] for column in inspector.get_columns(RATE_BOOK_TABLE)}
        with op.batch_alter_table(RATE_BOOK_TABLE) as batch_op:
            for column_name in ("row_attribute_keys_json", "charge_component_id"):
                if column_name in columns:
                    batch_op.drop_column(column_name)
