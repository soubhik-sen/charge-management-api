"""Align charge allocation profile contract with canonical standalone names.

Revision ID: 0010_align_allocation_profile_contract
Revises: 0009_charge_allocation_profiles
Create Date: 2026-07-15 00:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0010_align_allocation_profile_contract"
down_revision = "0009_charge_allocation_profiles"
branch_labels = None
depends_on = None


PROFILE_VERSION_TABLE = "charge_allocation_profile_version"
ALIAS_TABLE = "charge_component_alias"
LINE_TABLE = "charge_line"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _check_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    } if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _upgrade_component_alias(inspector)
    inspector = inspect(bind)
    _upgrade_profile_versions(inspector)
    inspector = inspect(bind)
    _upgrade_charge_line_target_level(inspector)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _downgrade_component_alias(inspector)
    inspector = inspect(bind)
    _downgrade_profile_versions(inspector)
    inspector = inspect(bind)
    _downgrade_charge_line_target_level(inspector)


def _upgrade_component_alias(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, ALIAS_TABLE):
        return
    columns = _column_names(inspector, ALIAS_TABLE)
    checks = _check_names(inspector, ALIAS_TABLE)

    with op.batch_alter_table(ALIAS_TABLE) as batch_op:
        if "final_posting_level" not in columns:
            batch_op.add_column(sa.Column("final_posting_level", sa.String(length=30), nullable=True))
        if "override_final_posting_level" not in columns:
            batch_op.add_column(sa.Column("override_final_posting_level", sa.String(length=30), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE charge_component_alias
               SET allocation_override_mode = CASE UPPER(COALESCE(allocation_override_mode, ''))
                   WHEN 'INHERIT' THEN 'INHERIT_PROFILE'
                   WHEN 'OVERRIDE' THEN 'OVERRIDE_PROFILE'
                   WHEN 'CLEAR' THEN 'NO_ALLOCATION'
                   WHEN 'INHERIT_PROFILE' THEN 'INHERIT_PROFILE'
                   WHEN 'OVERRIDE_PROFILE' THEN 'OVERRIDE_PROFILE'
                   WHEN 'NO_ALLOCATION' THEN 'NO_ALLOCATION'
                   ELSE 'OVERRIDE_PROFILE'
               END,
                   final_posting_level = COALESCE(NULLIF(UPPER(final_posting_level), ''), 'PO_SCHEDULE_LINE'),
                   override_final_posting_level = NULLIF(UPPER(override_final_posting_level), '')
            """
        )
    )

    with op.batch_alter_table(ALIAS_TABLE) as batch_op:
        if "ck_charge_component_alias_override_mode" in checks:
            batch_op.drop_constraint("ck_charge_component_alias_override_mode", type_="check")
        batch_op.alter_column(
            "allocation_override_mode",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
            server_default="OVERRIDE_PROFILE",
        )
        batch_op.create_check_constraint(
            "ck_charge_component_alias_override_mode",
            "allocation_override_mode in ('INHERIT_PROFILE', 'OVERRIDE_PROFILE', 'NO_ALLOCATION')",
        )


def _upgrade_profile_versions(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, PROFILE_VERSION_TABLE):
        return
    columns = _column_names(inspector, PROFILE_VERSION_TABLE)
    checks = _check_names(inspector, PROFILE_VERSION_TABLE)

    with op.batch_alter_table(PROFILE_VERSION_TABLE) as batch_op:
        if "source_level" not in columns:
            batch_op.add_column(sa.Column("source_level", sa.String(length=30), nullable=True))
        if "source_to_house_driver" not in columns:
            batch_op.add_column(sa.Column("source_to_house_driver", sa.String(length=40), nullable=True))
        if "house_to_item_driver" not in columns:
            batch_op.add_column(sa.Column("house_to_item_driver", sa.String(length=40), nullable=True))
        if "final_posting_level" not in columns:
            batch_op.add_column(sa.Column("final_posting_level", sa.String(length=30), nullable=True))

    default_charge_level_expr = "UPPER(COALESCE(default_charge_level, ''))" if "default_charge_level" in columns else "''"
    profile_shape_expr = "UPPER(COALESCE(profile_shape, ''))" if "profile_shape" in columns else "''"
    default_allocation_basis_expr = "NULLIF(UPPER(default_allocation_basis), '')" if "default_allocation_basis" in columns else "NULL"
    container_driver_expr = (
        "NULLIF(UPPER(container_house_allocation_basis), '')" if "container_house_allocation_basis" in columns else "NULL"
    )
    house_driver_expr = "NULLIF(UPPER(house_item_allocation_basis), '')" if "house_item_allocation_basis" in columns else "NULL"

    op.execute(
        sa.text(
            f"""
            UPDATE {PROFILE_VERSION_TABLE}
               SET status = CASE UPPER(COALESCE(status, ''))
                   WHEN 'SUPERSEDED' THEN 'RETIRED'
                   ELSE UPPER(COALESCE(status, 'DRAFT'))
               END,
                   source_level = COALESCE(
                       NULLIF(UPPER(source_level), ''),
                       CASE
                           WHEN {default_charge_level_expr} = 'CONTAINER' THEN 'CONTAINER'
                           WHEN {default_charge_level_expr} IN ('HOUSE', 'ITEM') THEN 'HOUSE'
                           ELSE 'SHIPMENT'
                       END
                   ),
                   source_to_house_driver = COALESCE(
                       NULLIF(UPPER(source_to_house_driver), ''),
                       CASE
                           WHEN {default_charge_level_expr} = 'CONTAINER' THEN COALESCE({container_driver_expr}, {default_allocation_basis_expr})
                           ELSE NULL
                       END
                   ),
                   house_to_item_driver = COALESCE(
                       NULLIF(UPPER(house_to_item_driver), ''),
                       CASE
                           WHEN {default_charge_level_expr} = 'ITEM' THEN COALESCE({house_driver_expr}, {default_allocation_basis_expr})
                           WHEN {profile_shape_expr} = 'STAGED' THEN {house_driver_expr}
                           ELSE NULL
                       END
                   ),
                   final_posting_level = COALESCE(
                       NULLIF(UPPER(final_posting_level), ''),
                       CASE
                           WHEN {default_charge_level_expr} = 'HOUSE' THEN 'HOUSE'
                           WHEN {profile_shape_expr} = 'DIRECT' AND {default_charge_level_expr} = 'HEADER' THEN 'HOUSE'
                           ELSE 'PO_SCHEDULE_LINE'
                       END
                   )
            """
        )
    )

    with op.batch_alter_table(PROFILE_VERSION_TABLE) as batch_op:
        if "ck_charge_allocation_profile_version_status" in checks:
            batch_op.drop_constraint("ck_charge_allocation_profile_version_status", type_="check")
        if "ck_charge_allocation_profile_version_shape" in checks:
            batch_op.drop_constraint("ck_charge_allocation_profile_version_shape", type_="check")
        if "ck_charge_allocation_profile_version_source_level" in checks:
            batch_op.drop_constraint("ck_charge_allocation_profile_version_source_level", type_="check")
        if "ck_charge_allocation_profile_version_final_posting_level" in checks:
            batch_op.drop_constraint("ck_charge_allocation_profile_version_final_posting_level", type_="check")
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default="DRAFT",
        )
        batch_op.alter_column(
            "source_level",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        batch_op.alter_column(
            "final_posting_level",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_charge_allocation_profile_version_status",
            "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
        )
        batch_op.create_check_constraint(
            "ck_charge_allocation_profile_version_source_level",
            "source_level in ('SHIPMENT', 'CONTAINER', 'HOUSE')",
        )
        batch_op.create_check_constraint(
            "ck_charge_allocation_profile_version_final_posting_level",
            "final_posting_level in ('HOUSE', 'PO_SCHEDULE_LINE')",
        )
        for column_name in (
            "profile_shape",
            "default_charge_level",
            "default_allocation_basis",
            "container_house_allocation_basis",
            "house_item_allocation_basis",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)


def _upgrade_charge_line_target_level(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, LINE_TABLE):
        return
    checks = _check_names(inspector, LINE_TABLE)
    with op.batch_alter_table(LINE_TABLE) as batch_op:
        if "ck_charge_line_target_level" in checks:
            batch_op.drop_constraint("ck_charge_line_target_level", type_="check")
        batch_op.create_check_constraint(
            "ck_charge_line_target_level",
            "target_level is null or target_level in ('HEADER', 'ITEM', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE')",
        )


def _downgrade_component_alias(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, ALIAS_TABLE):
        return
    columns = _column_names(inspector, ALIAS_TABLE)
    checks = _check_names(inspector, ALIAS_TABLE)

    op.execute(
        sa.text(
            """
            UPDATE charge_component_alias
               SET allocation_override_mode = CASE UPPER(COALESCE(allocation_override_mode, ''))
                   WHEN 'INHERIT_PROFILE' THEN 'INHERIT'
                   WHEN 'OVERRIDE_PROFILE' THEN 'OVERRIDE'
                   WHEN 'NO_ALLOCATION' THEN 'CLEAR'
                   ELSE 'OVERRIDE'
               END
            """
        )
    )

    with op.batch_alter_table(ALIAS_TABLE) as batch_op:
        if "ck_charge_component_alias_override_mode" in checks:
            batch_op.drop_constraint("ck_charge_component_alias_override_mode", type_="check")
        batch_op.alter_column(
            "allocation_override_mode",
            existing_type=sa.String(length=30),
            type_=sa.String(length=20),
            existing_nullable=False,
            server_default="OVERRIDE",
        )
        batch_op.create_check_constraint(
            "ck_charge_component_alias_override_mode",
            "allocation_override_mode in ('INHERIT', 'OVERRIDE', 'CLEAR')",
        )
        if "override_final_posting_level" in columns:
            batch_op.drop_column("override_final_posting_level")
        if "final_posting_level" in columns:
            batch_op.drop_column("final_posting_level")


def _downgrade_profile_versions(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, PROFILE_VERSION_TABLE):
        return
    columns = _column_names(inspector, PROFILE_VERSION_TABLE)
    checks = _check_names(inspector, PROFILE_VERSION_TABLE)

    with op.batch_alter_table(PROFILE_VERSION_TABLE) as batch_op:
        if "profile_shape" not in columns:
            batch_op.add_column(sa.Column("profile_shape", sa.String(length=20), nullable=True))
        if "default_charge_level" not in columns:
            batch_op.add_column(sa.Column("default_charge_level", sa.String(length=40), nullable=True))
        if "default_allocation_basis" not in columns:
            batch_op.add_column(sa.Column("default_allocation_basis", sa.String(length=40), nullable=True))
        if "container_house_allocation_basis" not in columns:
            batch_op.add_column(sa.Column("container_house_allocation_basis", sa.String(length=40), nullable=True))
        if "house_item_allocation_basis" not in columns:
            batch_op.add_column(sa.Column("house_item_allocation_basis", sa.String(length=40), nullable=True))

    op.execute(
        sa.text(
            f"""
            UPDATE {PROFILE_VERSION_TABLE}
               SET status = CASE UPPER(COALESCE(status, ''))
                   WHEN 'RETIRED' THEN 'SUPERSEDED'
                   ELSE UPPER(COALESCE(status, 'DRAFT'))
               END,
                   profile_shape = CASE
                       WHEN UPPER(COALESCE(source_level, '')) = 'CONTAINER' THEN 'STAGED'
                       WHEN UPPER(COALESCE(final_posting_level, '')) = 'HOUSE' THEN 'DIRECT'
                       WHEN UPPER(COALESCE(source_level, '')) = 'SHIPMENT' THEN 'MANUAL'
                       ELSE 'DIRECT'
                   END,
                   default_charge_level = CASE
                       WHEN UPPER(COALESCE(final_posting_level, '')) = 'HOUSE' THEN 'HOUSE'
                       WHEN UPPER(COALESCE(source_level, '')) = 'CONTAINER' THEN 'CONTAINER'
                       WHEN UPPER(COALESCE(source_level, '')) = 'HOUSE' THEN 'ITEM'
                       ELSE 'ITEM'
                   END,
                   default_allocation_basis = COALESCE(NULLIF(UPPER(house_to_item_driver), ''), NULLIF(UPPER(source_to_house_driver), '')),
                   container_house_allocation_basis = NULLIF(UPPER(source_to_house_driver), ''),
                   house_item_allocation_basis = NULLIF(UPPER(house_to_item_driver), '')
            """
        )
    )

    with op.batch_alter_table(PROFILE_VERSION_TABLE) as batch_op:
        for constraint_name in (
            "ck_charge_allocation_profile_version_status",
            "ck_charge_allocation_profile_version_source_level",
            "ck_charge_allocation_profile_version_final_posting_level",
        ):
            if constraint_name in checks:
                batch_op.drop_constraint(constraint_name, type_="check")
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default="DRAFT",
        )
        batch_op.create_check_constraint(
            "ck_charge_allocation_profile_version_status",
            "status in ('DRAFT', 'PUBLISHED', 'SUPERSEDED')",
        )
        batch_op.create_check_constraint(
            "ck_charge_allocation_profile_version_shape",
            "profile_shape in ('DIRECT', 'STAGED', 'MANUAL')",
        )
        for column_name in (
            "final_posting_level",
            "house_to_item_driver",
            "source_to_house_driver",
            "source_level",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)


def _downgrade_charge_line_target_level(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, LINE_TABLE):
        return
    checks = _check_names(inspector, LINE_TABLE)
    op.execute(sa.text("UPDATE charge_line SET target_level = 'PO_SCHEDULE_LINE' WHERE UPPER(COALESCE(target_level, '')) = 'HOUSE'"))
    with op.batch_alter_table(LINE_TABLE) as batch_op:
        if "ck_charge_line_target_level" in checks:
            batch_op.drop_constraint("ck_charge_line_target_level", type_="check")
        batch_op.create_check_constraint(
            "ck_charge_line_target_level",
            "target_level is null or target_level in ('HEADER', 'ITEM', 'CONTAINER', 'PO_SCHEDULE_LINE')",
        )
