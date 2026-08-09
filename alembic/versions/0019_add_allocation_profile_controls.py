"""Add effective dating and concurrency controls to allocation profiles.

Revision ID: 0019_allocation_profile_controls
Revises: 0018_business_date_effectivity
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0019_allocation_profile_controls"
down_revision = "0018_business_date_effectivity"
branch_labels = None
depends_on = None


TABLE = "charge_allocation_profile_version"


def _columns() -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return set()
    return {column["name"] for column in inspector.get_columns(TABLE)}


def upgrade() -> None:
    existing = _columns()
    if not existing:
        return
    with op.batch_alter_table(TABLE) as batch_op:
        definitions = (
            sa.Column("effective_from", sa.Date()),
            sa.Column("effective_to", sa.Date()),
            sa.Column(
                "missing_driver_policy",
                sa.String(length=20),
                nullable=False,
                server_default="BLOCK",
            ),
            sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        )
        for definition in definitions:
            if definition.name not in existing:
                batch_op.add_column(definition)
        check_names = {
            constraint["name"]
            for constraint in inspect(op.get_bind()).get_check_constraints(TABLE)
            if constraint.get("name")
        }
        if "ck_charge_allocation_profile_version_missing_driver_policy" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_allocation_profile_version_missing_driver_policy",
                "missing_driver_policy in ('BLOCK', 'EQUAL')",
            )
        if "ck_charge_allocation_profile_version_effectivity" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_allocation_profile_version_effectivity",
                "effective_from is null or effective_to is null or effective_from <= effective_to",
            )


def downgrade() -> None:
    existing = _columns()
    if not existing:
        return
    check_names = {
        constraint["name"]
        for constraint in inspect(op.get_bind()).get_check_constraints(TABLE)
        if constraint.get("name")
    }
    with op.batch_alter_table(TABLE) as batch_op:
        for constraint_name in (
            "ck_charge_allocation_profile_version_effectivity",
            "ck_charge_allocation_profile_version_missing_driver_policy",
        ):
            if constraint_name in check_names:
                batch_op.drop_constraint(constraint_name, type_="check")
        for column_name in (
            "lock_version",
            "missing_driver_policy",
            "effective_to",
            "effective_from",
        ):
            if column_name in existing:
                batch_op.drop_column(column_name)
