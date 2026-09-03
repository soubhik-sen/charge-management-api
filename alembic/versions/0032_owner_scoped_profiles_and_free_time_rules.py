"""Add owner-scoped reusable profiles and free-time rules.

Revision ID: 0032_owner_scoped_profiles_and_free_time_rules
Revises: 0031_route_commitment_identity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0032_owner_scoped_profiles_and_free_time_rules"
down_revision = "0031_route_commitment_identity"
branch_labels = None
depends_on = None


OWNER_SCOPED_PROFILE_TABLES = (
    (
        "charge_allocation_profile",
        "uq_charge_allocation_profile_code",
        "uq_charge_allocation_profile_owner_code",
        "ix_charge_allocation_profile_code",
        "ix_charge_allocation_profile_owner",
    ),
    (
        "charge_calculation_profile",
        "uq_charge_calculation_profile_code",
        "uq_charge_calculation_profile_owner_code",
        "ix_charge_calculation_profile_code",
        "ix_charge_calculation_profile_owner",
    ),
    (
        "charge_business_date_profile",
        "uq_charge_business_date_profile_code",
        "uq_charge_business_date_profile_owner_code",
        "ix_charge_business_date_profile_code",
        "ix_charge_business_date_profile_owner",
    ),
)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _unique_constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    } if inspector.has_table(table_name) else set()


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)} if inspector.has_table(table_name) else set()


def _add_owner_scope_columns(bind: sa.engine.Connection, table_name: str) -> None:
    inspector = inspect(bind)
    column_names = _column_names(inspector, table_name)

    with op.batch_alter_table(table_name) as batch_op:
        if "owner_type" not in column_names:
            batch_op.add_column(
                sa.Column(
                    "owner_type",
                    sa.String(length=80),
                    nullable=False,
                    server_default="SYSTEM",
                )
            )
        if "owner_id" not in column_names:
            batch_op.add_column(
                sa.Column(
                    "owner_id",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )

    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
               SET owner_type = COALESCE(NULLIF(owner_type, ''), 'SYSTEM'),
                   owner_id = COALESCE(owner_id, 0)
             WHERE owner_type IS NULL
                OR owner_type = ''
                OR owner_id IS NULL
            """
        )
    )

    if f"ix_{table_name}_owner" not in _index_names(inspect(bind), table_name):
        op.create_index(f"ix_{table_name}_owner", table_name, ["owner_type", "owner_id"])


def _create_free_time_tables(bind: sa.engine.Connection) -> None:
    inspector = inspect(bind)

    if not inspector.has_table("charge_free_time_profile"):
        op.create_table(
            "charge_free_time_profile",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_code", sa.String(length=80), nullable=False),
            sa.Column("profile_name", sa.String(length=180), nullable=False),
            sa.Column("owner_type", sa.String(length=80), nullable=False, server_default="SYSTEM"),
            sa.Column("owner_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("published_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint(
                "owner_type",
                "owner_id",
                "profile_code",
                name="uq_charge_free_time_profile_owner_code",
            ),
        )
        op.create_index("ix_charge_free_time_profile_code", "charge_free_time_profile", ["profile_code"])
        op.create_index(
            "ix_charge_free_time_profile_owner",
            "charge_free_time_profile",
            ["owner_type", "owner_id"],
        )

    inspector = inspect(bind)
    if not inspector.has_table("charge_free_time_profile_version"):
        op.create_table(
            "charge_free_time_profile_version",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "profile_id",
                sa.Integer(),
                sa.ForeignKey("charge_free_time_profile.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint(
                "profile_id",
                "version_number",
                name="uq_charge_free_time_profile_version_number",
            ),
            sa.CheckConstraint(
                "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
                name="ck_charge_free_time_profile_version_status",
            ),
            sa.CheckConstraint(
                "effective_from is null or effective_to is null or effective_from <= effective_to",
                name="ck_charge_free_time_profile_version_effectivity",
            ),
        )
        op.create_index(
            "ix_charge_free_time_profile_version_profile",
            "charge_free_time_profile_version",
            ["profile_id"],
        )

    inspector = inspect(bind)
    if not inspector.has_table("charge_free_time_rule"):
        op.create_table(
            "charge_free_time_rule",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "version_id",
                sa.Integer(),
                sa.ForeignKey("charge_free_time_profile_version.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("rule_code", sa.String(length=80), nullable=False),
            sa.Column("rule_name", sa.String(length=180), nullable=False),
            sa.Column("scope_type", sa.String(length=80), nullable=False, server_default="GLOBAL"),
            sa.Column("scope_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=True),
            sa.Column("start_timestamp_key", sa.String(length=120), nullable=False),
            sa.Column("end_timestamp_key", sa.String(length=120), nullable=False),
            sa.Column("free_time_days", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("match_facts_json", sa.JSON(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("version_id", "sequence", name="uq_charge_free_time_rule_sequence"),
            sa.UniqueConstraint("version_id", "rule_code", name="uq_charge_free_time_rule_code"),
            sa.CheckConstraint(
                "scope_type in ('GLOBAL', 'COMPANY', 'CUSTOMER', 'VENDOR', 'FORWARDER', 'CARRIER')",
                name="ck_charge_free_time_rule_scope_type",
            ),
        )
        op.create_index("ix_charge_free_time_rule_version", "charge_free_time_rule", ["version_id"])
        op.create_index(
            "ix_charge_free_time_rule_scope",
            "charge_free_time_rule",
            ["scope_type", "scope_id", "event_type", "priority"],
        )

    inspector = inspect(bind)
    profile_columns = _column_names(inspector, "charge_free_time_profile")
    if "published_version_id" in profile_columns:
        foreign_keys = {
            fk["constrained_columns"][0]
            for fk in inspector.get_foreign_keys("charge_free_time_profile")
            if fk.get("constrained_columns")
        }
        if "published_version_id" not in foreign_keys:
            with op.batch_alter_table("charge_free_time_profile") as batch_op:
                batch_op.create_foreign_key(
                    "fk_charge_free_time_profile_published_version",
                    "charge_free_time_profile_version",
                    ["published_version_id"],
                    ["id"],
                )


def upgrade() -> None:
    bind = op.get_bind()
    for table_name, old_unique, new_unique, code_index, owner_index in OWNER_SCOPED_PROFILE_TABLES:
        inspector = inspect(bind)
        if inspector.has_table(table_name):
            _add_owner_scope_columns(bind, table_name)
            inspector = inspect(bind)
            if old_unique in _unique_constraint_names(inspector, table_name):
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.drop_constraint(old_unique, type_="unique")
            if new_unique not in _unique_constraint_names(inspector, table_name):
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.create_unique_constraint(
                        new_unique,
                        ["owner_type", "owner_id", "profile_code"],
                    )
            if code_index not in _index_names(inspect(bind), table_name):
                op.create_index(code_index, table_name, ["profile_code"])
            if owner_index not in _index_names(inspect(bind), table_name):
                op.create_index(owner_index, table_name, ["owner_type", "owner_id"])

    _create_free_time_tables(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("charge_free_time_rule"):
        op.drop_index("ix_charge_free_time_rule_scope", table_name="charge_free_time_rule")
        op.drop_index("ix_charge_free_time_rule_version", table_name="charge_free_time_rule")
        op.drop_table("charge_free_time_rule")

    if inspector.has_table("charge_free_time_profile"):
        profile_unique = _unique_constraint_names(inspector, "charge_free_time_profile")
        if "fk_charge_free_time_profile_published_version" in {
            fk["name"] for fk in inspector.get_foreign_keys("charge_free_time_profile") if fk.get("name")
        }:
            with op.batch_alter_table("charge_free_time_profile") as batch_op:
                batch_op.drop_constraint("fk_charge_free_time_profile_published_version", type_="foreignkey")

    inspector = inspect(bind)
    if inspector.has_table("charge_free_time_profile_version"):
        op.drop_index("ix_charge_free_time_profile_version_profile", table_name="charge_free_time_profile_version")
        op.drop_table("charge_free_time_profile_version")

    inspector = inspect(bind)
    if inspector.has_table("charge_free_time_profile"):
        profile_unique = _unique_constraint_names(inspector, "charge_free_time_profile")
        op.drop_index("ix_charge_free_time_profile_owner", table_name="charge_free_time_profile")
        op.drop_index("ix_charge_free_time_profile_code", table_name="charge_free_time_profile")
        if "uq_charge_free_time_profile_owner_code" in profile_unique:
            with op.batch_alter_table("charge_free_time_profile") as batch_op:
                batch_op.drop_constraint("uq_charge_free_time_profile_owner_code", type_="unique")
        op.drop_table("charge_free_time_profile")

    for table_name, old_unique, new_unique, code_index, owner_index in reversed(OWNER_SCOPED_PROFILE_TABLES):
        if inspector.has_table(table_name):
            if new_unique in _unique_constraint_names(inspect(bind), table_name):
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.drop_constraint(new_unique, type_="unique")
            inspector = inspect(bind)
            if owner_index in _index_names(inspector, table_name):
                op.drop_index(owner_index, table_name=table_name)
            if code_index not in _index_names(inspect(bind), table_name):
                op.create_index(code_index, table_name, ["profile_code"])
            if old_unique not in _unique_constraint_names(inspect(bind), table_name):
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.create_unique_constraint(old_unique, ["profile_code"])
            inspector = inspect(bind)
            columns = _column_names(inspector, table_name)
            with op.batch_alter_table(table_name) as batch_op:
                if "owner_id" in columns:
                    batch_op.drop_column("owner_id")
                if "owner_type" in columns:
                    batch_op.drop_column("owner_type")
