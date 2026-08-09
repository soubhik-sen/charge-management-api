"""Align reusable rating and charge execution persistence.

Revision ID: 0016_align_charge_runtime
Revises: 0015_charge_line_target_scope_subset
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0016_align_charge_runtime"
down_revision = "0015_charge_line_target_scope_subset"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_columns(table_name: str, definitions: list[sa.Column]) -> None:
    existing = _columns(table_name)
    if not existing:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for definition in definitions:
            if definition.name not in existing:
                batch_op.add_column(definition)


def upgrade() -> None:
    _add_columns(
        "charge_rate_book",
        [
            sa.Column("description", sa.Text()),
            sa.Column("valid_from", sa.Date()),
            sa.Column("valid_to", sa.Date()),
            sa.Column(
                "calculation_basis",
                sa.String(length=40),
                nullable=False,
                server_default="FLAT",
            ),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        ],
    )
    _add_columns(
        "charge_rate_book_entry",
        [
            sa.Column("rate_percent", sa.Numeric(18, 6)),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
    )
    if "rate_amount" in _columns("charge_rate_book_entry"):
        with op.batch_alter_table("charge_rate_book_entry") as batch_op:
            batch_op.alter_column("rate_amount", existing_type=sa.Numeric(18, 6), nullable=True)

    _add_columns(
        "charge_rate_contract",
        [
            sa.Column("description", sa.Text()),
            sa.Column("margin_type", sa.String(length=30)),
            sa.Column("margin_value", sa.Numeric(18, 6)),
            sa.Column("minimum_margin_amount", sa.Numeric(18, 6)),
            sa.Column("minimum_margin_percent", sa.Numeric(18, 6)),
            sa.Column("external_reference", sa.String(length=160)),
        ],
    )
    _add_columns(
        "charge_contract_line",
        [
            sa.Column("line_number", sa.Integer()),
            sa.Column("charge_context", sa.String(length=80)),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
    )
    if "line_number" in _columns("charge_contract_line"):
        op.execute(sa.text("UPDATE charge_contract_line SET line_number = id WHERE line_number IS NULL"))
        unique_names = {
            constraint["name"]
            for constraint in inspect(op.get_bind()).get_unique_constraints("charge_contract_line")
            if constraint.get("name")
        }
        with op.batch_alter_table("charge_contract_line") as batch_op:
            batch_op.alter_column("line_number", existing_type=sa.Integer(), nullable=False)
            if "uq_charge_contract_line_number" not in unique_names:
                batch_op.create_unique_constraint(
                    "uq_charge_contract_line_number",
                    ["contract_id", "line_number"],
                )
    _add_columns(
        "charge_quote_request",
        [
            sa.Column("request_number", sa.String(length=80)),
            sa.Column("chargeable_weight", sa.Numeric(18, 6)),
            sa.Column("charge_context", sa.String(length=80)),
        ],
    )
    _add_columns(
        "charge_quote_option_line",
        [
            sa.Column(
                "calculation_mode",
                sa.String(length=30),
                nullable=False,
                server_default="DIRECT",
            ),
            sa.Column(
                "calculation_status",
                sa.String(length=30),
                nullable=False,
                server_default="CALCULATED",
            ),
            sa.Column("allocation_mode", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column(
                "allocation_status",
                sa.String(length=30),
                nullable=False,
                server_default="NOT_REQUIRED",
            ),
            sa.Column("allocation_config_snapshot_json", sa.JSON()),
            sa.Column("is_customer_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
    )
    if "request_number" in _columns("charge_quote_request"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                sa.text(
                    "UPDATE charge_quote_request "
                    "SET request_number = 'Q-' || lpad(CAST(id AS text), 8, '0') "
                    "WHERE request_number IS NULL"
                )
            )
        else:
            op.execute(
                sa.text(
                    "UPDATE charge_quote_request "
                    "SET request_number = 'Q-' || printf('%08d', id) "
                    "WHERE request_number IS NULL"
                )
            )
        index_names = {
            index["name"]
            for index in inspect(op.get_bind()).get_indexes("charge_quote_request")
        }
        if "uq_charge_quote_request_number" not in index_names:
            op.create_index(
                "uq_charge_quote_request_number",
                "charge_quote_request",
                ["request_number"],
                unique=True,
            )

    _add_columns(
        "charge_line",
        [
            sa.Column(
                "calculation_mode",
                sa.String(length=30),
                nullable=False,
                server_default="DIRECT",
            ),
            sa.Column(
                "calculation_status",
                sa.String(length=30),
                nullable=False,
                server_default="CALCULATED",
            ),
            sa.Column("calculation_locked_at", sa.DateTime(timezone=True)),
            sa.Column("allocation_mode", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column(
                "allocation_status",
                sa.String(length=30),
                nullable=False,
                server_default="NOT_REQUIRED",
            ),
            sa.Column("allocation_config_snapshot_json", sa.JSON()),
            sa.Column("allocation_locked_at", sa.DateTime(timezone=True)),
            sa.Column("is_customer_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        ],
    )


def downgrade() -> None:
    if "request_number" in _columns("charge_quote_request"):
        index_names = {
            index["name"]
            for index in inspect(op.get_bind()).get_indexes("charge_quote_request")
        }
        if "uq_charge_quote_request_number" in index_names:
            op.drop_index("uq_charge_quote_request_number", table_name="charge_quote_request")

    if "line_number" in _columns("charge_contract_line"):
        unique_names = {
            constraint["name"]
            for constraint in inspect(op.get_bind()).get_unique_constraints("charge_contract_line")
            if constraint.get("name")
        }
        if "uq_charge_contract_line_number" in unique_names:
            with op.batch_alter_table("charge_contract_line") as batch_op:
                batch_op.drop_constraint("uq_charge_contract_line_number", type_="unique")

    drops = {
        "charge_line": [
            "is_customer_visible",
            "allocation_locked_at",
            "allocation_config_snapshot_json",
            "allocation_status",
            "allocation_mode",
            "calculation_locked_at",
            "calculation_status",
            "calculation_mode",
        ],
        "charge_quote_request": ["charge_context", "chargeable_weight", "request_number"],
        "charge_quote_option_line": [
            "is_customer_visible",
            "allocation_config_snapshot_json",
            "allocation_status",
            "allocation_mode",
            "calculation_status",
            "calculation_mode",
        ],
        "charge_contract_line": ["is_active", "priority", "charge_context", "line_number"],
        "charge_rate_contract": [
            "external_reference",
            "minimum_margin_percent",
            "minimum_margin_amount",
            "margin_value",
            "margin_type",
            "description",
        ],
        "charge_rate_book_entry": ["is_active", "priority", "rate_percent"],
        "charge_rate_book": ["status", "calculation_basis", "valid_to", "valid_from", "description"],
    }
    if "rate_amount" in _columns("charge_rate_book_entry"):
        op.execute(
            sa.text(
                "UPDATE charge_rate_book_entry "
                "SET rate_amount = COALESCE(rate_amount, rate_percent, 0)"
            )
        )
        with op.batch_alter_table("charge_rate_book_entry") as batch_op:
            batch_op.alter_column("rate_amount", existing_type=sa.Numeric(18, 6), nullable=False)
    for table_name, column_names in drops.items():
        existing = _columns(table_name)
        if not existing:
            continue
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in column_names:
                if column_name in existing:
                    batch_op.drop_column(column_name)
