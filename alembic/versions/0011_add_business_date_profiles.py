"""Add business date profiles and component policy fields.

Revision ID: 0011_add_business_date_profiles
Revises: 0010_align_allocation_profile_contract
Create Date: 2026-07-20 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_add_business_date_profiles"
down_revision = "0010_align_allocation_profile_contract"
branch_labels = None
depends_on = None


COMPONENT_TABLE = "charge_component"
DOCUMENT_TABLE = "charge_document"
LINE_TABLE = "charge_line"
PROFILE_TABLE = "charge_business_date_profile"
VERSION_TABLE = "charge_business_date_profile_version"
STEP_TABLE = "charge_business_date_profile_step"
ASSIGNMENT_TABLE = "charge_business_date_profile_assignment"


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

    if not _table_exists(inspector, PROFILE_TABLE):
        op.create_table(
            PROFILE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_code", sa.String(length=80), nullable=False),
            sa.Column("profile_name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("published_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_code", name="uq_charge_business_date_profile_code"),
        )
        op.create_index("ix_charge_business_date_profile_code", PROFILE_TABLE, ["profile_code"])

    if not _table_exists(inspector, VERSION_TABLE):
        op.create_table(
            VERSION_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey(f"{PROFILE_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("profile_id", "version_number", name="uq_charge_business_date_profile_version_number"),
            sa.CheckConstraint(
                "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
                name="ck_charge_business_date_profile_version_status",
            ),
        )
        op.create_index("ix_charge_business_date_profile_version_profile", VERSION_TABLE, ["profile_id"])

    if not _table_exists(inspector, STEP_TABLE):
        op.create_table(
            STEP_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("version_id", sa.Integer(), sa.ForeignKey(f"{VERSION_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("date_key", sa.String(length=80), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("version_id", "step_number", name="uq_charge_business_date_profile_step_number"),
        )
        op.create_index("ix_charge_business_date_profile_step_version", STEP_TABLE, ["version_id"])

    if not _table_exists(inspector, ASSIGNMENT_TABLE):
        op.create_table(
            ASSIGNMENT_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey(f"{PROFILE_TABLE}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scope_type", sa.String(length=30), nullable=False),
            sa.Column("scope_id", sa.Integer(), nullable=True),
            sa.Column("owner_scope_key", sa.String(length=80), nullable=False),
            sa.Column("shipment_scope", sa.String(length=30), nullable=False),
            sa.Column("business_purpose", sa.String(length=40), nullable=False, server_default="EXCHANGE_RATE_DATE"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint(
                "owner_scope_key",
                "shipment_scope",
                "business_purpose",
                name="uq_charge_business_date_profile_assignment_effective_scope",
            ),
            sa.CheckConstraint(
                "scope_type in ('GLOBAL', 'COMPANY', 'CUSTOMER', 'VENDOR', 'FORWARDER', 'CARRIER')",
                name="ck_charge_business_date_profile_assignment_scope_type",
            ),
            sa.CheckConstraint(
                "(scope_type = 'GLOBAL' and scope_id is null) or (scope_type <> 'GLOBAL' and scope_id is not null)",
                name="ck_charge_business_date_profile_assignment_scope_id",
            ),
            sa.CheckConstraint(
                "length(owner_scope_key) > 0",
                name="ck_charge_business_date_profile_assignment_owner_scope_key",
            ),
            sa.CheckConstraint(
                "shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
                name="ck_charge_business_date_profile_assignment_shipment_scope",
            ),
            sa.CheckConstraint(
                "business_purpose in ('EXCHANGE_RATE_DATE')",
                name="ck_charge_business_date_profile_assignment_business_purpose",
            ),
        )
        op.create_index(
            "ix_charge_business_date_profile_assignment_profile",
            ASSIGNMENT_TABLE,
            ["profile_id"],
        )
        op.create_index(
            "ix_charge_business_date_profile_assignment_scope",
            ASSIGNMENT_TABLE,
            ["scope_type", "scope_id", "shipment_scope", "business_purpose", "priority"],
        )

    inspector = inspect(bind)
    component_columns = _column_names(inspector, COMPONENT_TABLE)
    component_checks = _check_names(inspector, COMPONENT_TABLE)
    with op.batch_alter_table(COMPONENT_TABLE) as batch_op:
        if "business_date_policy_mode" not in component_columns:
            batch_op.add_column(
                sa.Column(
                    "business_date_policy_mode",
                    sa.String(length=30),
                    nullable=False,
                    server_default="LEGACY_BASIS",
                )
            )
        if "business_date_profile_id" not in component_columns:
            batch_op.add_column(sa.Column("business_date_profile_id", sa.Integer(), nullable=True))
        if "ck_charge_component_business_date_policy_mode" not in component_checks:
            batch_op.create_check_constraint(
                "ck_charge_component_business_date_policy_mode",
                "business_date_policy_mode in ('LEGACY_BASIS', 'INHERIT_PROFILE', 'PROFILE_OVERRIDE')",
            )

    inspector = inspect(bind)
    document_columns = _column_names(inspector, DOCUMENT_TABLE)
    document_checks = _check_names(inspector, DOCUMENT_TABLE)
    with op.batch_alter_table(DOCUMENT_TABLE) as batch_op:
        if "shipment_scope" not in document_columns:
            batch_op.add_column(sa.Column("shipment_scope", sa.String(length=30), nullable=True))
        if "ck_charge_document_shipment_scope" not in document_checks:
            batch_op.create_check_constraint(
                "ck_charge_document_shipment_scope",
                "shipment_scope is null or shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
            )

    inspector = inspect(bind)
    line_columns = _column_names(inspector, LINE_TABLE)
    line_checks = _check_names(inspector, LINE_TABLE)
    with op.batch_alter_table(LINE_TABLE) as batch_op:
        if "charge_date_basis" not in line_columns:
            batch_op.add_column(sa.Column("charge_date_basis", sa.String(length=40), nullable=True))
        if "ck_charge_line_charge_date_basis" not in line_checks:
            batch_op.create_check_constraint(
                "ck_charge_line_charge_date_basis",
                "charge_date_basis is null or charge_date_basis in ('DOCUMENT_DATE', 'SHIPMENT_DEPARTURE_DATE', 'SHIPMENT_ARRIVAL_DATE', 'HOUSE_BILL_ISSUE_DATE', 'MANUAL')",
            )

    op.execute(
        sa.text(
            f"""
            UPDATE {COMPONENT_TABLE}
               SET business_date_policy_mode = COALESCE(NULLIF(UPPER(business_date_policy_mode), ''), 'LEGACY_BASIS'),
                   business_date_profile_id = NULL
             WHERE business_date_policy_mode IS NULL
                OR business_date_policy_mode = ''
            """
        )
    )

    _seed_business_date_profiles(bind)
    _link_profile_foreign_key(inspect(bind))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _drop_line_charge_date_basis(inspector)
    _drop_document_shipment_scope(inspect(bind))
    _drop_component_columns(inspector)
    if _table_exists(inspector, ASSIGNMENT_TABLE):
        op.drop_index("ix_charge_business_date_profile_assignment_scope", table_name=ASSIGNMENT_TABLE)
        op.drop_index("ix_charge_business_date_profile_assignment_profile", table_name=ASSIGNMENT_TABLE)
        op.drop_table(ASSIGNMENT_TABLE)
    if _table_exists(inspector, STEP_TABLE):
        op.drop_index("ix_charge_business_date_profile_step_version", table_name=STEP_TABLE)
        op.drop_table(STEP_TABLE)
    if _table_exists(inspector, VERSION_TABLE):
        op.drop_index("ix_charge_business_date_profile_version_profile", table_name=VERSION_TABLE)
        op.drop_table(VERSION_TABLE)
    if _table_exists(inspector, PROFILE_TABLE):
        op.drop_index("ix_charge_business_date_profile_code", table_name=PROFILE_TABLE)
        op.drop_table(PROFILE_TABLE)


def _seed_business_date_profiles(bind: sa.engine.Connection) -> None:
    rows = bind.execute(sa.text(f"SELECT COUNT(*) FROM {PROFILE_TABLE}")).scalar_one()
    if rows != 0:
        return
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {PROFILE_TABLE} (id, profile_code, profile_name, description, published_version_id)
            VALUES
              (1, 'OCEAN_HOUSE_STANDARD', 'Ocean House Exchange Rate Policy', 'Fallback chain for ocean-house exchange-rate date resolution.', 1),
              (2, 'AIR_HOUSE_STANDARD', 'Air House Exchange Rate Policy', 'Fallback chain for air-house exchange-rate date resolution.', 2)
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
                notes,
                published_at
            )
            VALUES
              (1, 1, 1, 'PUBLISHED', 'Fallback chain for ocean-house exchange-rate date resolution.', CURRENT_TIMESTAMP),
              (2, 2, 1, 'PUBLISHED', 'Fallback chain for air-house exchange-rate date resolution.', CURRENT_TIMESTAMP)
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {STEP_TABLE} (id, version_id, step_number, date_key, notes)
            VALUES
              (1, 1, 10, 'SHIPPED_ON_BOARD_DATE', 'Prefer shipped-on-board date when the source system provides it.'),
              (2, 1, 20, 'SHIPMENT_ACTUAL_DEPARTURE_DATE', 'Fallback to the actual departure date.'),
              (3, 1, 30, 'SHIPMENT_PLANNED_DEPARTURE_DATE', 'Fallback to the estimated departure date.'),
              (4, 2, 10, 'ACTUAL_FLIGHT_DEPARTURE_DATE', 'Prefer the actual flight departure date when available.'),
              (5, 2, 20, 'AWB_EXECUTION_DATE', 'Fallback to the air waybill execution date.'),
              (6, 2, 30, 'ESTIMATED_FLIGHT_DEPARTURE_DATE', 'Fallback to the estimated flight departure date.')
            """
        )
    )


def _link_profile_foreign_key(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, PROFILE_TABLE):
        return
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(PROFILE_TABLE)}
    if "fk_charge_business_date_profile_published_version" not in foreign_keys:
        with op.batch_alter_table(PROFILE_TABLE) as batch_op:
            batch_op.create_foreign_key(
                "fk_charge_business_date_profile_published_version",
                VERSION_TABLE,
                ["published_version_id"],
                ["id"],
            )


def _drop_component_columns(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, COMPONENT_TABLE):
        return
    checks = _check_names(inspector, COMPONENT_TABLE)
    columns = _column_names(inspector, COMPONENT_TABLE)
    with op.batch_alter_table(COMPONENT_TABLE) as batch_op:
        if "ck_charge_component_business_date_policy_mode" in checks:
            batch_op.drop_constraint("ck_charge_component_business_date_policy_mode", type_="check")
        for column_name in ("business_date_profile_id", "business_date_policy_mode"):
            if column_name in columns:
                batch_op.drop_column(column_name)


def _drop_document_shipment_scope(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, DOCUMENT_TABLE):
        return
    checks = _check_names(inspector, DOCUMENT_TABLE)
    columns = _column_names(inspector, DOCUMENT_TABLE)
    with op.batch_alter_table(DOCUMENT_TABLE) as batch_op:
        if "ck_charge_document_shipment_scope" in checks:
            batch_op.drop_constraint("ck_charge_document_shipment_scope", type_="check")
        if "shipment_scope" in columns:
            batch_op.drop_column("shipment_scope")


def _drop_line_charge_date_basis(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, LINE_TABLE):
        return
    checks = _check_names(inspector, LINE_TABLE)
    columns = _column_names(inspector, LINE_TABLE)
    with op.batch_alter_table(LINE_TABLE) as batch_op:
        if "ck_charge_line_charge_date_basis" in checks:
            batch_op.drop_constraint("ck_charge_line_charge_date_basis", type_="check")
        if "charge_date_basis" in columns:
            batch_op.drop_column("charge_date_basis")
