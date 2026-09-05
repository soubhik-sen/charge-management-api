"""Add adapter-neutral calculation profile parity support.

Revision ID: 0034_charge_calculation_profile_parity
Revises: 0033_free_time_scope_and_dimension_identity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0034_charge_calculation_profile_parity"
down_revision = "0033_free_time_scope_and_dimension_identity"
branch_labels = None
depends_on = None


PROFILE_TABLE = "charge_calculation_profile"
VERSION_TABLE = "charge_calculation_profile_version"
FACTOR_TABLE = "charge_calculation_profile_factor"
ALIAS_TABLE = "charge_component_alias"

IDENTITY_SEQUENCE_TABLES = (
    PROFILE_TABLE,
    VERSION_TABLE,
    FACTOR_TABLE,
)

CURRENT_METHOD_CHECK = (
    "calculation_method in ('FLAT_AMOUNT', 'RATE_TIMES_PRODUCT', 'PERCENT_OF_REFERENCE')"
)
PREVIOUS_METHOD_CHECK = "calculation_method in ('FLAT_AMOUNT', 'RATE_TIMES_PRODUCT')"
CURRENT_FACTOR_CHECK = (
    "resolver in ('MANUAL', 'TARGET_COUNT', 'CONTAINER_COUNT', 'HOUSE_COUNT', "
    "'PO_SCHEDULE_LINE_COUNT', 'QUANTITY', 'WEIGHT', 'VOLUME', "
    "'CHARGEABLE_WEIGHT', 'OCEAN_WM', 'REFERENCE_AMOUNT', "
    "'DURATION_HOURS', 'DURATION_DAYS', 'FIXED_VALUE')"
)
PREVIOUS_FACTOR_CHECK = (
    "resolver in ('MANUAL', 'TARGET_COUNT', 'CONTAINER_COUNT', 'HOUSE_COUNT', "
    "'PO_SCHEDULE_LINE_COUNT', 'QUANTITY', 'WEIGHT', 'VOLUME', "
    "'CHARGEABLE_WEIGHT', 'DURATION_HOURS', 'DURATION_DAYS', 'FIXED_VALUE')"
)


CALCULATION_PROFILE_SEEDS: tuple[dict[str, object], ...] = (
    {
        "profile_code": "OCEAN_WM",
        "profile_name": "Ocean W/M",
        "description": "Multiplies the unit rate by ocean weight-or-measure quantity.",
        "application_level": "SHIPMENT",
        "calculation_method": "RATE_TIMES_PRODUCT",
        "rate_uom": "WM",
        "missing_factor_policy": "BLOCK",
        "factors": ((1, "OCEAN_WM", "Ocean W/M", "OCEAN_WM", "WM"),),
    },
    {
        "profile_code": "PERCENT_OF_REFERENCE",
        "profile_name": "Percentage of reference",
        "description": "Applies a percentage rate to a reference amount with optional min/max caps.",
        "application_level": "SHIPMENT",
        "calculation_method": "PERCENT_OF_REFERENCE",
        "rate_uom": "PERCENT",
        "missing_factor_policy": "BLOCK",
        "factors": (),
    },
)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return (
        {column["name"] for column in inspector.get_columns(table_name)}
        if inspector.has_table(table_name)
        else set()
    )


def _check_constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return (
        {
            constraint["name"]
            for constraint in inspector.get_check_constraints(table_name)
            if constraint.get("name")
        }
        if inspector.has_table(table_name)
        else set()
    )


def _foreign_key_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return (
        {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}
        if inspector.has_table(table_name)
        else set()
    )


def _unique_constraints(inspector: sa.Inspector, table_name: str) -> dict[str, tuple[str, ...]]:
    if not inspector.has_table(table_name):
        return {}
    return {
        str(constraint["name"]): tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {str(index["name"]) for index in inspector.get_indexes(table_name) if index.get("name")}


def _table_definitions() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause]:
    profile_table = sa.table(
        PROFILE_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("profile_code", sa.String(length=80)),
        sa.column("profile_name", sa.String(length=180)),
        sa.column("description", sa.Text()),
        sa.column("owner_type", sa.String(length=80)),
        sa.column("owner_id", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("published_version_id", sa.Integer()),
    )
    version_table = sa.table(
        VERSION_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("profile_id", sa.Integer()),
        sa.column("version_number", sa.Integer()),
        sa.column("status", sa.String(length=20)),
        sa.column("effective_from", sa.Date()),
        sa.column("effective_to", sa.Date()),
        sa.column("application_level", sa.String(length=30)),
        sa.column("calculation_method", sa.String(length=30)),
        sa.column("rate_uom", sa.String(length=80)),
        sa.column("missing_factor_policy", sa.String(length=20)),
        sa.column("minimum_amount", sa.Numeric(18, 6)),
        sa.column("maximum_amount", sa.Numeric(18, 6)),
        sa.column("lock_version", sa.Integer()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("published_by", sa.String(length=255)),
    )
    factor_table = sa.table(
        FACTOR_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("profile_version_id", sa.Integer()),
        sa.column("sequence", sa.Integer()),
        sa.column("factor_code", sa.String(length=60)),
        sa.column("factor_label", sa.String(length=160)),
        sa.column("resolver", sa.String(length=40)),
        sa.column("uom", sa.String(length=30)),
        sa.column("is_required", sa.Boolean()),
        sa.column("default_value", sa.Numeric(18, 6)),
    )
    return profile_table, version_table, factor_table


def _synchronize_identity_sequences(bind: sa.engine.Connection) -> None:
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    for table_name in IDENTITY_SEQUENCE_TABLES:
        if not inspector.has_table(table_name):
            continue
        bind.execute(
            sa.text(
                "SELECT setval("
                f"pg_get_serial_sequence('{table_name}', 'id'), "
                f"COALESCE(MAX(id), 1), COUNT(*) > 0) FROM {table_name}"
            )
        )


def _replace_check_constraint(
    bind: sa.engine.Connection,
    *,
    table_name: str,
    constraint_name: str,
    condition: str,
) -> None:
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return
    constraint_names = _check_constraint_names(inspector, table_name)
    with op.batch_alter_table(table_name) as batch_op:
        if constraint_name in constraint_names:
            batch_op.drop_constraint(constraint_name, type_="check")
        batch_op.create_check_constraint(constraint_name, condition)


def _add_version_columns(bind: sa.engine.Connection) -> None:
    inspector = inspect(bind)
    if not inspector.has_table(VERSION_TABLE):
        return
    column_names = _column_names(inspector, VERSION_TABLE)
    with op.batch_alter_table(VERSION_TABLE) as batch_op:
        if "minimum_amount" not in column_names:
            batch_op.add_column(sa.Column("minimum_amount", sa.Numeric(18, 6), nullable=True))
        if "maximum_amount" not in column_names:
            batch_op.add_column(sa.Column("maximum_amount", sa.Numeric(18, 6), nullable=True))


def _add_alias_columns(bind: sa.engine.Connection) -> None:
    inspector = inspect(bind)
    if not inspector.has_table(ALIAS_TABLE):
        return
    column_names = _column_names(inspector, ALIAS_TABLE)
    foreign_keys = _foreign_key_names(inspector, ALIAS_TABLE)
    unique_constraints = _unique_constraints(inspector, ALIAS_TABLE)
    expected_scope_columns = (
        "document_kind",
        "template_key",
        "source_section",
        "source_uom",
        "normalized_label",
        "customer_id",
        "forwarder_id",
        "transport_mode",
    )
    rebuild_scope_constraint = (
        unique_constraints.get("uq_charge_component_alias_scope_label") != expected_scope_columns
    )
    index_names = _index_names(inspector, ALIAS_TABLE)
    with op.batch_alter_table(ALIAS_TABLE) as batch_op:
        if (
            rebuild_scope_constraint
            and "uq_charge_component_alias_scope_label" in unique_constraints
        ):
            batch_op.drop_constraint("uq_charge_component_alias_scope_label", type_="unique")
        if "source_uom" not in column_names:
            batch_op.add_column(sa.Column("source_uom", sa.String(length=40), nullable=True))
        if "default_calculation_profile_id" not in column_names:
            batch_op.add_column(
                sa.Column("default_calculation_profile_id", sa.Integer(), nullable=True)
            )
        if "default_calculation_profile_version_id" not in column_names:
            batch_op.add_column(
                sa.Column("default_calculation_profile_version_id", sa.Integer(), nullable=True)
            )
        if "override_calculation_profile_id" not in column_names:
            batch_op.add_column(
                sa.Column("override_calculation_profile_id", sa.Integer(), nullable=True)
            )
        if "override_calculation_profile_version_id" not in column_names:
            batch_op.add_column(
                sa.Column("override_calculation_profile_version_id", sa.Integer(), nullable=True)
            )
        if "fk_charge_component_alias_default_calculation_profile" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_component_alias_default_calculation_profile",
                PROFILE_TABLE,
                ["default_calculation_profile_id"],
                ["id"],
            )
        if "fk_charge_component_alias_default_calculation_profile_version" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_component_alias_default_calculation_profile_version",
                VERSION_TABLE,
                ["default_calculation_profile_version_id"],
                ["id"],
            )
        if "fk_charge_component_alias_override_calculation_profile" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_component_alias_override_calculation_profile",
                PROFILE_TABLE,
                ["override_calculation_profile_id"],
                ["id"],
            )
        if "fk_charge_component_alias_override_calculation_profile_version" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_charge_component_alias_override_calculation_profile_version",
                VERSION_TABLE,
                ["override_calculation_profile_version_id"],
                ["id"],
            )
        if rebuild_scope_constraint:
            batch_op.create_unique_constraint(
                "uq_charge_component_alias_scope_label",
                list(expected_scope_columns),
            )
        if "ix_charge_component_alias_source_uom" not in index_names:
            batch_op.create_index(
                "ix_charge_component_alias_source_uom",
                ["source_uom"],
                unique=False,
            )


def _seed_calculation_profile(bind: sa.engine.Connection, row: dict[str, object]) -> None:
    profile_table, version_table, factor_table = _table_definitions()
    profile_code = str(row["profile_code"])
    existing_profile_id = bind.execute(
        sa.select(profile_table.c.id).where(profile_table.c.profile_code == profile_code)
    ).scalar_one_or_none()
    if existing_profile_id is not None:
        return

    bind.execute(
        sa.insert(profile_table).values(
            profile_code=profile_code,
            profile_name=str(row["profile_name"]),
            description=str(row["description"]) if row.get("description") is not None else None,
            owner_type="SYSTEM",
            owner_id=0,
            is_active=True,
            published_version_id=None,
        )
    )
    profile_id = int(
        bind.execute(
            sa.select(profile_table.c.id).where(profile_table.c.profile_code == profile_code)
        ).scalar_one()
    )

    bind.execute(
        sa.insert(version_table).values(
            profile_id=profile_id,
            version_number=1,
            status="PUBLISHED",
            effective_from=row.get("effective_from"),
            effective_to=row.get("effective_to"),
            application_level=str(row["application_level"]),
            calculation_method=str(row["calculation_method"]),
            rate_uom=str(row["rate_uom"]) if row.get("rate_uom") is not None else None,
            missing_factor_policy=str(row.get("missing_factor_policy", "BLOCK")),
            minimum_amount=row.get("minimum_amount"),
            maximum_amount=row.get("maximum_amount"),
            lock_version=1,
            published_at=sa.func.now(),
            published_by="SYSTEM",
        )
    )
    version_id = int(
        bind.execute(
            sa.select(version_table.c.id).where(version_table.c.profile_id == profile_id)
        ).scalar_one()
    )

    for sequence, factor_code, factor_label, resolver, uom in row.get("factors", ()):
        bind.execute(
            sa.insert(factor_table).values(
                profile_version_id=version_id,
                sequence=int(sequence),
                factor_code=str(factor_code).strip().upper(),
                factor_label=str(factor_label).strip(),
                resolver=str(resolver).strip().upper(),
                uom=str(uom).strip().upper() if uom else None,
                is_required=True,
                default_value=None,
            )
        )

    bind.execute(
        sa.update(profile_table)
        .where(profile_table.c.id == profile_id)
        .values(published_version_id=version_id)
    )


def _seed_calculation_profiles(bind: sa.engine.Connection) -> None:
    for row in CALCULATION_PROFILE_SEEDS:
        _seed_calculation_profile(bind, row)


def _remove_seed_calculation_profiles(bind: sa.engine.Connection) -> None:
    profile_table, version_table, factor_table = _table_definitions()
    inspector = inspect(bind)
    if not inspector.has_table(PROFILE_TABLE):
        return
    seed_codes = [str(row["profile_code"]) for row in CALCULATION_PROFILE_SEEDS]
    profile_ids = list(
        bind.execute(
            sa.select(profile_table.c.id).where(profile_table.c.profile_code.in_(seed_codes))
        ).scalars()
    )
    if not profile_ids:
        return
    version_ids = list(
        bind.execute(
            sa.select(version_table.c.id).where(version_table.c.profile_id.in_(profile_ids))
        ).scalars()
    )
    if inspector.has_table(ALIAS_TABLE):
        alias_table = sa.table(
            ALIAS_TABLE,
            sa.column("default_calculation_profile_id", sa.Integer()),
            sa.column("default_calculation_profile_version_id", sa.Integer()),
            sa.column("override_calculation_profile_id", sa.Integer()),
            sa.column("override_calculation_profile_version_id", sa.Integer()),
        )
        bind.execute(
            sa.update(alias_table)
            .where(alias_table.c.default_calculation_profile_id.in_(profile_ids))
            .values(default_calculation_profile_id=None)
        )
        bind.execute(
            sa.update(alias_table)
            .where(alias_table.c.override_calculation_profile_id.in_(profile_ids))
            .values(override_calculation_profile_id=None)
        )
        if version_ids:
            bind.execute(
                sa.update(alias_table)
                .where(alias_table.c.default_calculation_profile_version_id.in_(version_ids))
                .values(default_calculation_profile_version_id=None)
            )
            bind.execute(
                sa.update(alias_table)
                .where(alias_table.c.override_calculation_profile_version_id.in_(version_ids))
                .values(override_calculation_profile_version_id=None)
            )
    component_table = sa.table(
        "charge_component",
        sa.column("default_calculation_profile_id", sa.Integer()),
    )
    bind.execute(
        sa.update(component_table)
        .where(component_table.c.default_calculation_profile_id.in_(profile_ids))
        .values(default_calculation_profile_id=None)
    )
    rate_book_entry_table = sa.table(
        "charge_rate_book_entry",
        sa.column("calculation_profile_id", sa.Integer()),
    )
    bind.execute(
        sa.update(rate_book_entry_table)
        .where(rate_book_entry_table.c.calculation_profile_id.in_(profile_ids))
        .values(calculation_profile_id=None)
    )
    contract_line_table = sa.table(
        "charge_contract_line",
        sa.column("calculation_profile_id", sa.Integer()),
    )
    bind.execute(
        sa.update(contract_line_table)
        .where(contract_line_table.c.calculation_profile_id.in_(profile_ids))
        .values(calculation_profile_id=None)
    )
    if version_ids:
        bind.execute(
            sa.delete(factor_table).where(factor_table.c.profile_version_id.in_(version_ids))
        )
        bind.execute(sa.delete(version_table).where(version_table.c.profile_id.in_(profile_ids)))
    bind.execute(
        sa.update(profile_table)
        .where(profile_table.c.id.in_(profile_ids))
        .values(published_version_id=None)
    )
    bind.execute(sa.delete(profile_table).where(profile_table.c.id.in_(profile_ids)))


def upgrade() -> None:
    bind = op.get_bind()
    _add_version_columns(bind)
    _replace_check_constraint(
        bind,
        table_name=VERSION_TABLE,
        constraint_name="ck_charge_calculation_profile_version_method",
        condition=CURRENT_METHOD_CHECK,
    )
    _replace_check_constraint(
        bind,
        table_name=FACTOR_TABLE,
        constraint_name="ck_charge_calculation_profile_factor_resolver",
        condition=CURRENT_FACTOR_CHECK,
    )
    _add_alias_columns(bind)
    _synchronize_identity_sequences(bind)
    _seed_calculation_profiles(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _remove_seed_calculation_profiles(bind)
    profile_table, version_table, _ = _table_definitions()
    if inspect(bind).has_table(PROFILE_TABLE):
        for profile_code in ("PERCENT_OF_REFERENCE", "OCEAN_WM"):
            existing_profile_id = bind.execute(
                sa.select(profile_table.c.id).where(profile_table.c.profile_code == profile_code)
            ).scalar_one_or_none()
            if existing_profile_id is not None:
                bind.execute(
                    sa.delete(profile_table).where(profile_table.c.id == int(existing_profile_id))
                )
    _replace_check_constraint(
        bind,
        table_name=VERSION_TABLE,
        constraint_name="ck_charge_calculation_profile_version_method",
        condition=PREVIOUS_METHOD_CHECK,
    )
    _replace_check_constraint(
        bind,
        table_name=FACTOR_TABLE,
        constraint_name="ck_charge_calculation_profile_factor_resolver",
        condition=PREVIOUS_FACTOR_CHECK,
    )
    inspector = inspect(bind)
    if inspector.has_table(VERSION_TABLE):
        column_names = _column_names(inspector, VERSION_TABLE)
        with op.batch_alter_table(VERSION_TABLE) as batch_op:
            if "maximum_amount" in column_names:
                batch_op.drop_column("maximum_amount")
            if "minimum_amount" in column_names:
                batch_op.drop_column("minimum_amount")
    inspector = inspect(bind)
    if inspector.has_table(ALIAS_TABLE):
        column_names = _column_names(inspector, ALIAS_TABLE)
        foreign_keys = _foreign_key_names(inspector, ALIAS_TABLE)
        unique_constraints = _unique_constraints(inspector, ALIAS_TABLE)
        index_names = _index_names(inspector, ALIAS_TABLE)
        with op.batch_alter_table(ALIAS_TABLE) as batch_op:
            if "ix_charge_component_alias_source_uom" in index_names:
                batch_op.drop_index("ix_charge_component_alias_source_uom")
            if "uq_charge_component_alias_scope_label" in unique_constraints:
                batch_op.drop_constraint("uq_charge_component_alias_scope_label", type_="unique")
            if "fk_charge_component_alias_override_calculation_profile_version" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_component_alias_override_calculation_profile_version",
                    type_="foreignkey",
                )
            if "fk_charge_component_alias_override_calculation_profile" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_component_alias_override_calculation_profile", type_="foreignkey"
                )
            if "fk_charge_component_alias_default_calculation_profile_version" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_component_alias_default_calculation_profile_version",
                    type_="foreignkey",
                )
            if "fk_charge_component_alias_default_calculation_profile" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_charge_component_alias_default_calculation_profile", type_="foreignkey"
                )
            if "override_calculation_profile_version_id" in column_names:
                batch_op.drop_column("override_calculation_profile_version_id")
            if "override_calculation_profile_id" in column_names:
                batch_op.drop_column("override_calculation_profile_id")
            if "default_calculation_profile_version_id" in column_names:
                batch_op.drop_column("default_calculation_profile_version_id")
            if "default_calculation_profile_id" in column_names:
                batch_op.drop_column("default_calculation_profile_id")
            if "source_uom" in column_names:
                batch_op.drop_column("source_uom")
            batch_op.create_unique_constraint(
                "uq_charge_component_alias_scope_label",
                [
                    "document_kind",
                    "template_key",
                    "source_section",
                    "normalized_label",
                    "customer_id",
                    "forwarder_id",
                    "transport_mode",
                ],
            )
