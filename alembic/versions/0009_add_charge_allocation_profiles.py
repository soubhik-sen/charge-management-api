"""Add charge allocation profiles and propagation fields.

Revision ID: 0009_charge_allocation_profiles
Revises: 0008_charge_component_charge_date_basis
Create Date: 2026-07-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_charge_allocation_profiles"
down_revision = "0008_charge_component_charge_date_basis"
branch_labels = None
depends_on = None


PROFILE_TABLE = "charge_allocation_profile"
VERSION_TABLE = "charge_allocation_profile_version"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, PROFILE_TABLE):
        op.create_table(
            PROFILE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_code", sa.String(length=80), nullable=False),
            sa.Column("profile_name", sa.String(length=180), nullable=False),
            sa.Column("published_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_code", name="uq_charge_allocation_profile_code"),
        )
        op.create_index("ix_charge_allocation_profile_code", PROFILE_TABLE, ["profile_code"])

    if not _table_exists(inspector, VERSION_TABLE):
        op.create_table(
            VERSION_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey(f"{PROFILE_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("source_level", sa.String(length=30), nullable=False),
            sa.Column("source_to_house_driver", sa.String(length=40), nullable=True),
            sa.Column("house_to_item_driver", sa.String(length=40), nullable=True),
            sa.Column("final_posting_level", sa.String(length=30), nullable=False),
            sa.Column("default_quantity_uom", sa.String(length=30), nullable=True),
            sa.Column("settings_json", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_id", "version_number", name="uq_charge_allocation_profile_version_number"),
            sa.CheckConstraint(
                "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
                name="ck_charge_allocation_profile_version_status",
            ),
            sa.CheckConstraint(
                "source_level in ('SHIPMENT', 'CONTAINER', 'HOUSE')",
                name="ck_charge_allocation_profile_version_source_level",
            ),
            sa.CheckConstraint(
                "final_posting_level in ('HOUSE', 'PO_SCHEDULE_LINE')",
                name="ck_charge_allocation_profile_version_final_posting_level",
            ),
        )
        op.create_index("ix_charge_allocation_profile_version_profile", VERSION_TABLE, ["profile_id"])

    inspector = inspect(bind)
    profile_columns = _column_names(inspector, PROFILE_TABLE)
    if "published_version_id" in profile_columns:
        foreign_keys = {fk["constrained_columns"][0] for fk in inspector.get_foreign_keys(PROFILE_TABLE) if fk.get("constrained_columns")}
        if "published_version_id" not in foreign_keys:
            with op.batch_alter_table(PROFILE_TABLE) as batch_op:
                batch_op.create_foreign_key(
                    "fk_charge_allocation_profile_published_version",
                    VERSION_TABLE,
                    ["published_version_id"],
                    ["id"],
                )

    _add_columns(
        inspector,
        "charge_component",
        [
            sa.Column("allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("allocation_profile_version_id", sa.Integer(), nullable=True),
        ],
    )
    _add_columns(
        inspector,
        "charge_rate_book_entry",
        [
            sa.Column("allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("allocation_profile_version_id", sa.Integer(), nullable=True),
        ],
    )
    _add_columns(
        inspector,
        "charge_contract_line",
        [
            sa.Column("allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("allocation_profile_version_id", sa.Integer(), nullable=True),
        ],
    )
    _add_columns(
        inspector,
        "charge_quote_option_line",
        [
            sa.Column("quantity_uom", sa.String(length=30), nullable=True),
            sa.Column("allocation_basis", sa.String(length=40), nullable=True),
            sa.Column("allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("allocation_profile_version_id", sa.Integer(), nullable=True),
            sa.Column("pinned_allocation_snapshot_json", sa.JSON(), nullable=True),
            sa.Column("effective_allocation_snapshot_json", sa.JSON(), nullable=True),
        ],
    )
    _add_columns(
        inspector,
        "charge_line",
        [
            sa.Column("allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("allocation_profile_version_id", sa.Integer(), nullable=True),
            sa.Column("pinned_allocation_snapshot_json", sa.JSON(), nullable=True),
            sa.Column("effective_allocation_snapshot_json", sa.JSON(), nullable=True),
        ],
    )
    _add_columns(
        inspector,
        "charge_component_alias",
        [
            sa.Column("allocation_override_mode", sa.String(length=30), nullable=False, server_default="OVERRIDE_PROFILE"),
            sa.Column("override_allocation_profile_id", sa.Integer(), nullable=True),
            sa.Column("override_allocation_profile_version_id", sa.Integer(), nullable=True),
            sa.Column("override_charge_level", sa.String(length=40), nullable=True),
            sa.Column("override_allocation_basis", sa.String(length=40), nullable=True),
            sa.Column("override_container_house_allocation_basis", sa.String(length=40), nullable=True),
            sa.Column("override_house_item_allocation_basis", sa.String(length=40), nullable=True),
            sa.Column("final_posting_level", sa.String(length=30), nullable=True),
            sa.Column("override_final_posting_level", sa.String(length=30), nullable=True),
            sa.Column("override_quantity_uom", sa.String(length=30), nullable=True),
        ],
    )

    inspector = inspect(bind)
    alias_checks = {constraint["name"] for constraint in inspector.get_check_constraints("charge_component_alias")}
    if "ck_charge_component_alias_override_mode" not in alias_checks:
        with op.batch_alter_table("charge_component_alias") as batch_op:
            batch_op.create_check_constraint(
                "ck_charge_component_alias_override_mode",
                "allocation_override_mode in ('INHERIT_PROFILE', 'OVERRIDE_PROFILE', 'NO_ALLOCATION')",
            )

    rows = bind.execute(sa.text(f"SELECT COUNT(*) FROM {PROFILE_TABLE}")).scalar_one()
    if rows == 0:
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {PROFILE_TABLE} (id, profile_code, profile_name, published_version_id)
                VALUES
                  (1, 'DIRECT_HEADER_DEFAULT', 'Direct Header Allocation', NULL),
                  (2, 'STAGED_CONTAINER_ITEM_DEFAULT', 'Staged Container Allocation', NULL),
                  (3, 'MANUAL_TARGET_DEFAULT', 'Manual Target Allocation', NULL)
                """
            )
        )
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {VERSION_TABLE} (
                    id,
                    profile_id,
                    version_number,
                    status,
                    source_level,
                    source_to_house_driver,
                    house_to_item_driver,
                    final_posting_level,
                    default_quantity_uom,
                    settings_json,
                    notes,
                    published_at
                )
                VALUES
                  (
                    1, 1, 1, 'PUBLISHED', 'HOUSE', NULL, NULL, 'HOUSE', NULL,
                    '{{"shape": "DIRECT"}}',
                    'Single-step allocation profile for direct document or header-level posting.',
                    CURRENT_TIMESTAMP
                  ),
                  (
                    2, 2, 1, 'PUBLISHED', 'CONTAINER', 'CBM', 'WEIGHT', 'PO_SCHEDULE_LINE', 'CBM',
                    '{{"shape": "STAGED"}}',
                    'Two-stage allocation profile for intermediate container-to-target propagation.',
                    CURRENT_TIMESTAMP
                  ),
                  (
                    3, 3, 1, 'PUBLISHED', 'SHIPMENT', 'CBM', 'WEIGHT', 'PO_SCHEDULE_LINE', NULL,
                    '{{"shape": "MANUAL"}}',
                    'Manual allocation profile with no automatic basis defaults.',
                    CURRENT_TIMESTAMP
                  )
                """
            )
        )
        bind.execute(
            sa.text(
                f"""
                UPDATE {PROFILE_TABLE}
                   SET published_version_id = CASE id
                       WHEN 1 THEN 1
                       WHEN 2 THEN 2
                       WHEN 3 THEN 3
                       ELSE published_version_id
                   END
                 WHERE id IN (1, 2, 3)
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _drop_columns(
        inspector,
        "charge_component_alias",
        [
            "override_quantity_uom",
            "override_house_item_allocation_basis",
            "override_container_house_allocation_basis",
            "override_allocation_basis",
            "override_charge_level",
            "override_allocation_profile_version_id",
            "override_allocation_profile_id",
            "allocation_override_mode",
        ],
        drop_check="ck_charge_component_alias_override_mode",
    )
    _drop_columns(
        inspector,
        "charge_line",
        [
            "effective_allocation_snapshot_json",
            "pinned_allocation_snapshot_json",
            "allocation_profile_version_id",
            "allocation_profile_id",
        ],
    )
    _drop_columns(
        inspector,
        "charge_quote_option_line",
        [
            "effective_allocation_snapshot_json",
            "pinned_allocation_snapshot_json",
            "allocation_profile_version_id",
            "allocation_profile_id",
            "allocation_basis",
            "quantity_uom",
        ],
    )
    _drop_columns(
        inspector,
        "charge_contract_line",
        ["allocation_profile_version_id", "allocation_profile_id"],
    )
    _drop_columns(
        inspector,
        "charge_rate_book_entry",
        ["allocation_profile_version_id", "allocation_profile_id"],
    )
    _drop_columns(
        inspector,
        "charge_component",
        ["allocation_profile_version_id", "allocation_profile_id"],
    )

    if _table_exists(inspector, PROFILE_TABLE):
        foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(PROFILE_TABLE)}
        if "fk_charge_allocation_profile_published_version" in foreign_keys:
            with op.batch_alter_table(PROFILE_TABLE) as batch_op:
                batch_op.drop_constraint("fk_charge_allocation_profile_published_version", type_="foreignkey")

    if _table_exists(inspector, VERSION_TABLE):
        op.drop_index("ix_charge_allocation_profile_version_profile", table_name=VERSION_TABLE)
        op.drop_table(VERSION_TABLE)
    if _table_exists(inspector, PROFILE_TABLE):
        op.drop_index("ix_charge_allocation_profile_code", table_name=PROFILE_TABLE)
        op.drop_table(PROFILE_TABLE)


def _add_columns(inspector: sa.Inspector, table_name: str, columns: list[sa.Column]) -> None:
    if not _table_exists(inspector, table_name):
        return
    existing = _column_names(inspector, table_name)
    with op.batch_alter_table(table_name) as batch_op:
        for column in columns:
            if column.name not in existing:
                batch_op.add_column(column)


def _drop_columns(
    inspector: sa.Inspector,
    table_name: str,
    columns: list[str],
    *,
    drop_check: str | None = None,
) -> None:
    if not _table_exists(inspector, table_name):
        return
    existing = _column_names(inspector, table_name)
    checks = {constraint["name"] for constraint in inspector.get_check_constraints(table_name)}
    with op.batch_alter_table(table_name) as batch_op:
        if drop_check and drop_check in checks:
            batch_op.drop_constraint(drop_check, type_="check")
        for column in columns:
            if column in existing:
                batch_op.drop_column(column)
