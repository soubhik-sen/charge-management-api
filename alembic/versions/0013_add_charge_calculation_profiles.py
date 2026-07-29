"""Add adapter-neutral charge calculation profiles.

Revision ID: 0013_add_charge_calculation_profiles
Revises: 0012_fx_rates_and_sequences
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0013_add_charge_calculation_profiles"
down_revision = "0012_fx_rates_and_sequences"
branch_labels = None
depends_on = None


PROFILE_TABLE = "charge_calculation_profile"
VERSION_TABLE = "charge_calculation_profile_version"
FACTOR_TABLE = "charge_calculation_profile_factor"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _fk_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint.get("name")
        for constraint in inspector.get_foreign_keys(table_name)
        if constraint.get("name")
    } if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, PROFILE_TABLE):
        op.create_table(
            PROFILE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_code", sa.String(length=80), nullable=False),
            sa.Column("profile_name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("published_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_code", name="uq_charge_calculation_profile_code"),
        )
        op.create_index("ix_charge_calculation_profile_code", PROFILE_TABLE, ["profile_code"])

    if not _table_exists(inspector, VERSION_TABLE):
        op.create_table(
            VERSION_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey(f"{PROFILE_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("application_level", sa.String(length=30), nullable=False),
            sa.Column("calculation_method", sa.String(length=30), nullable=False, server_default="RATE_TIMES_PRODUCT"),
            sa.Column("rate_uom", sa.String(length=80), nullable=True),
            sa.Column("missing_factor_policy", sa.String(length=20), nullable=False, server_default="BLOCK"),
            sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_by", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_id", "version_number", name="uq_charge_calculation_profile_version_number"),
            sa.CheckConstraint(
                "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
                name="ck_charge_calculation_profile_version_status",
            ),
            sa.CheckConstraint(
                "application_level in ('SHIPMENT', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE')",
                name="ck_charge_calculation_profile_version_application_level",
            ),
            sa.CheckConstraint(
                "calculation_method in ('FLAT_AMOUNT', 'RATE_TIMES_PRODUCT')",
                name="ck_charge_calculation_profile_version_method",
            ),
            sa.CheckConstraint(
                "missing_factor_policy in ('BLOCK')",
                name="ck_charge_calculation_profile_version_missing_factor_policy",
            ),
        )
        op.create_index("ix_charge_calculation_profile_version_profile", VERSION_TABLE, ["profile_id"])
        op.create_index("ix_charge_calculation_profile_version_status", VERSION_TABLE, ["status"])

    if not _table_exists(inspector, FACTOR_TABLE):
        op.create_table(
            FACTOR_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_version_id", sa.Integer(), sa.ForeignKey(f"{VERSION_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("factor_code", sa.String(length=60), nullable=False),
            sa.Column("factor_label", sa.String(length=160), nullable=False),
            sa.Column("resolver", sa.String(length=40), nullable=False),
            sa.Column("uom", sa.String(length=30), nullable=True),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("default_value", sa.Numeric(18, 6), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_version_id", "factor_code", name="uq_charge_calculation_profile_factor_code"),
            sa.UniqueConstraint("profile_version_id", "sequence", name="uq_charge_calculation_profile_factor_sequence"),
            sa.CheckConstraint(
                "resolver in ('MANUAL', 'TARGET_COUNT', 'CONTAINER_COUNT', 'HOUSE_COUNT', "
                "'PO_SCHEDULE_LINE_COUNT', 'QUANTITY', 'WEIGHT', 'VOLUME', "
                "'CHARGEABLE_WEIGHT', 'DURATION_HOURS', 'DURATION_DAYS', 'FIXED_VALUE')",
                name="ck_charge_calculation_profile_factor_resolver",
            ),
        )
        op.create_index("ix_charge_calculation_profile_factor_profile_version", FACTOR_TABLE, ["profile_version_id"])

    inspector = inspect(bind)
    _add_profile_fk(inspector, "charge_component", "default_calculation_profile_id", PROFILE_TABLE, "fk_charge_component_default_calculation_profile")
    _add_profile_fk(inspector, "charge_contract_line", "calculation_profile_id", PROFILE_TABLE, "fk_charge_contract_line_calculation_profile")
    _add_profile_fk(inspector, "charge_rate_book_entry", "calculation_profile_id", PROFILE_TABLE, "fk_charge_rate_book_entry_calculation_profile")
    _add_profile_fk(
        inspector,
        "charge_quote_option_line",
        "calculation_profile_version_id",
        VERSION_TABLE,
        "fk_charge_quote_option_line_calculation_profile_version",
    )
    _add_profile_fk(
        inspector,
        "charge_line",
        "calculation_profile_version_id",
        VERSION_TABLE,
        "fk_charge_line_calculation_profile_version",
    )

    inspector = inspect(bind)
    quote_columns = _column_names(inspector, "charge_quote_option_line")
    with op.batch_alter_table("charge_quote_option_line") as batch_op:
        if "rate_amount" not in quote_columns:
            batch_op.add_column(sa.Column("rate_amount", sa.Numeric(18, 6), nullable=True))
        if "quantity" not in quote_columns:
            batch_op.add_column(sa.Column("quantity", sa.Numeric(18, 6), nullable=False, server_default="1"))
        if "quantity_uom" not in quote_columns:
            batch_op.add_column(sa.Column("quantity_uom", sa.String(length=30), nullable=True))
        if "calculation_config_snapshot_json" not in quote_columns:
            batch_op.add_column(sa.Column("calculation_config_snapshot_json", sa.JSON(), nullable=True))
        if "calculation_input_snapshot_json" not in quote_columns:
            batch_op.add_column(sa.Column("calculation_input_snapshot_json", sa.JSON(), nullable=True))

    inspector = inspect(bind)
    line_columns = _column_names(inspector, "charge_line")
    with op.batch_alter_table("charge_line") as batch_op:
        if "rate_amount" not in line_columns:
            batch_op.add_column(sa.Column("rate_amount", sa.Numeric(18, 6), nullable=True))
        if "quantity_uom" not in line_columns:
            batch_op.add_column(sa.Column("quantity_uom", sa.String(length=30), nullable=True))
        if "calculation_config_snapshot_json" not in line_columns:
            batch_op.add_column(sa.Column("calculation_config_snapshot_json", sa.JSON(), nullable=True))
        if "calculation_input_snapshot_json" not in line_columns:
            batch_op.add_column(sa.Column("calculation_input_snapshot_json", sa.JSON(), nullable=True))

    _seed_profiles(bind)
    _link_published_version_fk()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table(PROFILE_TABLE):
        foreign_keys = _fk_names(inspector, PROFILE_TABLE)
        if "fk_charge_calculation_profile_published_version" in foreign_keys:
            with op.batch_alter_table(PROFILE_TABLE) as batch_op:
                batch_op.drop_constraint(
                    "fk_charge_calculation_profile_published_version",
                    type_="foreignkey",
                )
        inspector = inspect(bind)

    for table_name, fk_name, column_name in (
        ("charge_line", "fk_charge_line_calculation_profile_version", "calculation_profile_version_id"),
        ("charge_quote_option_line", "fk_charge_quote_option_line_calculation_profile_version", "calculation_profile_version_id"),
        ("charge_rate_book_entry", "fk_charge_rate_book_entry_calculation_profile", "calculation_profile_id"),
        ("charge_contract_line", "fk_charge_contract_line_calculation_profile", "calculation_profile_id"),
        ("charge_component", "fk_charge_component_default_calculation_profile", "default_calculation_profile_id"),
    ):
        if inspector.has_table(table_name):
            columns = _column_names(inspector, table_name)
            foreign_keys = _fk_names(inspector, table_name)
            with op.batch_alter_table(table_name) as batch_op:
                if fk_name in foreign_keys:
                    batch_op.drop_constraint(fk_name, type_="foreignkey")
                if column_name in columns:
                    batch_op.drop_column(column_name)
        inspector = inspect(bind)

    if inspector.has_table("charge_quote_option_line"):
        columns = _column_names(inspector, "charge_quote_option_line")
        with op.batch_alter_table("charge_quote_option_line") as batch_op:
            for column_name in (
                "calculation_input_snapshot_json",
                "calculation_config_snapshot_json",
                "quantity",
                "rate_amount",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    inspector = inspect(bind)
    if inspector.has_table("charge_line"):
        columns = _column_names(inspector, "charge_line")
        with op.batch_alter_table("charge_line") as batch_op:
            for column_name in (
                "calculation_input_snapshot_json",
                "calculation_config_snapshot_json",
                "rate_amount",
            ):
                if column_name in columns:
                    batch_op.drop_column(column_name)

    inspector = inspect(bind)
    if inspector.has_table(FACTOR_TABLE):
        op.drop_index("ix_charge_calculation_profile_factor_profile_version", table_name=FACTOR_TABLE)
        op.drop_table(FACTOR_TABLE)
    if inspector.has_table(VERSION_TABLE):
        op.drop_index("ix_charge_calculation_profile_version_status", table_name=VERSION_TABLE)
        op.drop_index("ix_charge_calculation_profile_version_profile", table_name=VERSION_TABLE)
        op.drop_table(VERSION_TABLE)
    if inspector.has_table(PROFILE_TABLE):
        op.drop_index("ix_charge_calculation_profile_code", table_name=PROFILE_TABLE)
        op.drop_table(PROFILE_TABLE)


def _add_profile_fk(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
    referred_table: str,
    fk_name: str,
) -> None:
    columns = _column_names(inspector, table_name)
    foreign_keys = _fk_names(inspector, table_name)
    with op.batch_alter_table(table_name) as batch_op:
        if column_name not in columns:
            batch_op.add_column(sa.Column(column_name, sa.Integer(), nullable=True))
        if fk_name not in foreign_keys:
            batch_op.create_foreign_key(fk_name, referred_table, [column_name], ["id"])


def _seed_profiles(bind: sa.engine.Connection) -> None:
    rows = bind.execute(sa.text(f"SELECT COUNT(*) FROM {PROFILE_TABLE}")).scalar_one()
    if rows != 0:
        return
    profiles = (
        (1, "FLAT_AMOUNT", "Flat amount", "Uses the provided amount directly without factor multiplication.", "SHIPMENT", "FLAT_AMOUNT", None, ()),
        (2, "QUANTITY", "Rate per quantity", "Multiplies the unit rate by the target quantity.", "SHIPMENT", "RATE_TIMES_PRODUCT", "UNIT", ((1, "QUANTITY", "Quantity", "QUANTITY", "UNIT"),)),
        (3, "WEIGHT", "Rate per weight", "Multiplies the unit rate by gross weight.", "SHIPMENT", "RATE_TIMES_PRODUCT", "KG", ((1, "WEIGHT", "Weight", "WEIGHT", "KG"),)),
        (4, "VOLUME", "Rate per volume", "Multiplies the unit rate by gross volume.", "SHIPMENT", "RATE_TIMES_PRODUCT", "CBM", ((1, "VOLUME", "Volume", "VOLUME", "CBM"),)),
        (5, "PER_CONTAINER", "Rate per container", "Multiplies the unit rate by eligible container count.", "CONTAINER", "RATE_TIMES_PRODUCT", "CONTAINER", ((1, "CONTAINER_COUNT", "Container count", "CONTAINER_COUNT", "CONTAINER"),)),
        (6, "PER_HOUSE", "Rate per house", "Multiplies the unit rate by approved house count.", "HOUSE", "RATE_TIMES_PRODUCT", "HOUSE", ((1, "HOUSE_COUNT", "House count", "HOUSE_COUNT", "HOUSE"),)),
        (7, "PER_DAY", "Rate per day", "Multiplies the unit rate by duration in days.", "SHIPMENT", "RATE_TIMES_PRODUCT", "DAY", ((1, "DURATION_DAYS", "Duration days", "DURATION_DAYS", "DAY"),)),
        (8, "PER_CONTAINER_PER_HOUR", "Rate per container per hour", "Multiplies the unit rate by container count and duration hours.", "CONTAINER", "RATE_TIMES_PRODUCT", "CONTAINER_HOUR", ((1, "CONTAINER_COUNT", "Container count", "CONTAINER_COUNT", "CONTAINER"), (2, "DURATION_HOURS", "Duration hours", "DURATION_HOURS", "HOUR"))),
    )
    for profile_id, profile_code, profile_name, description, application_level, calculation_method, rate_uom, factors in profiles:
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {PROFILE_TABLE}
                    (id, profile_code, profile_name, description, is_active, published_version_id, created_at, updated_at)
                VALUES
                    (:profile_id, :profile_code, :profile_name, :description, true, :profile_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "profile_id": profile_id,
                "profile_code": profile_code,
                "profile_name": profile_name,
                "description": description,
            },
        )
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {VERSION_TABLE}
                    (id, profile_id, version_number, status, effective_from, effective_to, application_level,
                     calculation_method, rate_uom, missing_factor_policy, lock_version, published_at, published_by,
                     created_at, updated_at)
                VALUES
                    (:version_id, :profile_id, 1, 'PUBLISHED', NULL, NULL, :application_level,
                     :calculation_method, :rate_uom, 'BLOCK', 1, CURRENT_TIMESTAMP, 'SYSTEM',
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "version_id": profile_id,
                "profile_id": profile_id,
                "application_level": application_level,
                "calculation_method": calculation_method,
                "rate_uom": rate_uom,
            },
        )
        factor_id = profile_id * 100
        for sequence, factor_code, factor_label, resolver, uom in factors:
            bind.execute(
                sa.text(
                    f"""
                    INSERT INTO {FACTOR_TABLE}
                        (id, profile_version_id, sequence, factor_code, factor_label, resolver, uom,
                         is_required, default_value, created_at, updated_at)
                    VALUES
                        (:id, :profile_version_id, :sequence, :factor_code, :factor_label, :resolver, :uom,
                         true, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id": factor_id + sequence,
                    "profile_version_id": profile_id,
                    "sequence": sequence,
                    "factor_code": factor_code,
                    "factor_label": factor_label,
                    "resolver": resolver,
                    "uom": uom,
                },
            )


def _link_published_version_fk() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = _column_names(inspector, PROFILE_TABLE)
    foreign_keys = _fk_names(inspector, PROFILE_TABLE)
    with op.batch_alter_table(PROFILE_TABLE) as batch_op:
        if "published_version_id" not in columns:
            batch_op.add_column(sa.Column("published_version_id", sa.Integer(), nullable=True))
        if "fk_charge_calculation_profile_published_version" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_calculation_profile_published_version",
                VERSION_TABLE,
                ["published_version_id"],
                ["id"],
            )

