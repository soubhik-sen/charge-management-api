"""Add persistent repository sequences and adapter-neutral FX rates.

Revision ID: 0012_fx_rates_and_sequences
Revises: 0011_add_business_date_profiles
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0012_fx_rates_and_sequences"
down_revision = "0011_add_business_date_profiles"
branch_labels = None
depends_on = None


SEQUENCE_TABLE = "charge_id_sequence"
SOURCE_TABLE = "charge_fx_rate_source"
RATE_TABLE = "charge_fx_rate"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if SEQUENCE_TABLE not in tables:
        op.create_table(
            SEQUENCE_TABLE,
            sa.Column("bucket", sa.String(length=80), primary_key=True),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        )

    if SOURCE_TABLE not in tables:
        op.create_table(
            SOURCE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_code", sa.String(length=60), nullable=False),
            sa.Column("source_name", sa.String(length=180), nullable=False),
            sa.Column("provider_url", sa.String(length=500), nullable=True),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("source_code", name="uq_charge_fx_rate_source_code"),
            sa.CheckConstraint("priority >= 0", name="ck_charge_fx_rate_source_priority"),
        )
        op.create_index("ix_charge_fx_rate_source_code", SOURCE_TABLE, ["source_code"])

    inspector = inspect(bind)
    if RATE_TABLE not in inspector.get_table_names():
        op.create_table(
            RATE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("source_currency", sa.String(length=3), nullable=False),
            sa.Column("target_currency", sa.String(length=3), nullable=False),
            sa.Column("rate_date", sa.Date(), nullable=False),
            sa.Column("rate", sa.Numeric(20, 10), nullable=False),
            sa.Column("rate_type", sa.String(length=20), nullable=False, server_default="MID"),
            sa.Column("conversion_method", sa.String(length=60), nullable=False, server_default="DIRECT"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["source_id"], [f"{SOURCE_TABLE}.id"]),
            sa.UniqueConstraint(
                "source_id",
                "source_currency",
                "target_currency",
                "rate_date",
                "rate_type",
                "conversion_method",
                name="uq_charge_fx_rate_pair_date_source_type_method",
            ),
            sa.CheckConstraint("source_currency <> target_currency", name="ck_charge_fx_rate_currency_pair"),
            sa.CheckConstraint("rate > 0", name="ck_charge_fx_rate_positive"),
            sa.CheckConstraint(
                "rate_type in ('MID', 'BUY', 'SELL', 'CUSTOM')",
                name="ck_charge_fx_rate_type",
            ),
        )
        op.create_index(
            "ix_charge_fx_rate_lookup",
            RATE_TABLE,
            ["source_currency", "target_currency", "rate_date", "rate_type", "is_active"],
        )
        op.create_index("ix_charge_fx_rate_source", RATE_TABLE, ["source_id"])

    inspector = inspect(bind)
    line_columns = {column["name"] for column in inspector.get_columns("charge_line")}
    line_checks = {constraint.get("name") for constraint in inspector.get_check_constraints("charge_line")}
    line_foreign_keys = {
        constraint.get("name") for constraint in inspector.get_foreign_keys("charge_line")
    }
    with op.batch_alter_table("charge_line") as batch_op:
        if "fx_rate_id" not in line_columns:
            batch_op.add_column(sa.Column("fx_rate_id", sa.Integer(), nullable=True))
        if "exchange_rate_source_code" not in line_columns:
            batch_op.add_column(sa.Column("exchange_rate_source_code", sa.String(length=60), nullable=True))
        if "exchange_rate_type" not in line_columns:
            batch_op.add_column(sa.Column("exchange_rate_type", sa.String(length=20), nullable=True))
        if "exchange_rate_method" not in line_columns:
            batch_op.add_column(sa.Column("exchange_rate_method", sa.String(length=60), nullable=True))
        if "fk_charge_line_fx_rate" not in line_foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_line_fx_rate",
                RATE_TABLE,
                ["fx_rate_id"],
                ["id"],
            )
        if "ck_charge_line_exchange_rate_type" not in line_checks:
            batch_op.create_check_constraint(
                "ck_charge_line_exchange_rate_type",
                "exchange_rate_type is null or exchange_rate_type in ('MID', 'BUY', 'SELL', 'CUSTOM')",
            )

    inspector = inspect(bind)
    template_step_columns = {
        column["name"] for column in inspector.get_columns("charge_calculation_template_step")
    }
    template_step_checks = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("charge_calculation_template_step")
    }
    with op.batch_alter_table("charge_calculation_template_step") as batch_op:
        if "relationship_role" not in template_step_columns:
            batch_op.add_column(
                sa.Column("relationship_role", sa.String(length=20), nullable=False, server_default="BOTH")
            )
        if "ck_charge_calc_template_step_relationship_role" not in template_step_checks:
            batch_op.create_check_constraint(
                "ck_charge_calc_template_step_relationship_role",
                "relationship_role in ('PAYER', 'PAYEE', 'BOTH')",
            )

    source_table = sa.table(
        SOURCE_TABLE,
        sa.column("source_code", sa.String),
        sa.column("source_name", sa.String),
        sa.column("timezone", sa.String),
        sa.column("priority", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("metadata_json", sa.JSON),
    )
    existing_manual = bind.execute(
        sa.select(sa.literal(1)).select_from(source_table).where(source_table.c.source_code == "MANUAL")
    ).first()
    if existing_manual is None:
        op.bulk_insert(
            source_table,
            [
                {
                    "source_code": "MANUAL",
                    "source_name": "Manual Rate Maintenance",
                    "timezone": "UTC",
                    "priority": 100,
                    "is_active": True,
                    "metadata_json": {"system_seed": True},
                }
            ],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "charge_line" in inspector.get_table_names():
        line_columns = {column["name"] for column in inspector.get_columns("charge_line")}
        line_checks = {constraint.get("name") for constraint in inspector.get_check_constraints("charge_line")}
        line_foreign_keys = {
            constraint.get("name") for constraint in inspector.get_foreign_keys("charge_line")
        }
        with op.batch_alter_table("charge_line") as batch_op:
            if "ck_charge_line_exchange_rate_type" in line_checks:
                batch_op.drop_constraint("ck_charge_line_exchange_rate_type", type_="check")
            if "fk_charge_line_fx_rate" in line_foreign_keys:
                batch_op.drop_constraint("fk_charge_line_fx_rate", type_="foreignkey")
            for column_name in (
                "exchange_rate_method",
                "exchange_rate_type",
                "exchange_rate_source_code",
                "fx_rate_id",
            ):
                if column_name in line_columns:
                    batch_op.drop_column(column_name)

    inspector = inspect(bind)
    if "charge_calculation_template_step" in inspector.get_table_names():
        template_step_columns = {
            column["name"] for column in inspector.get_columns("charge_calculation_template_step")
        }
        template_step_checks = {
            constraint.get("name")
            for constraint in inspector.get_check_constraints("charge_calculation_template_step")
        }
        with op.batch_alter_table("charge_calculation_template_step") as batch_op:
            if "ck_charge_calc_template_step_relationship_role" in template_step_checks:
                batch_op.drop_constraint(
                    "ck_charge_calc_template_step_relationship_role",
                    type_="check",
                )
            if "relationship_role" in template_step_columns:
                batch_op.drop_column("relationship_role")

    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if RATE_TABLE in tables:
        op.drop_index("ix_charge_fx_rate_source", table_name=RATE_TABLE)
        op.drop_index("ix_charge_fx_rate_lookup", table_name=RATE_TABLE)
        op.drop_table(RATE_TABLE)
    if SOURCE_TABLE in tables:
        op.drop_index("ix_charge_fx_rate_source_code", table_name=SOURCE_TABLE)
        op.drop_table(SOURCE_TABLE)
    if SEQUENCE_TABLE in tables:
        op.drop_table(SEQUENCE_TABLE)
