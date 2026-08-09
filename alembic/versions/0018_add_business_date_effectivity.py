"""Add effective periods to business date profile versions.

Revision ID: 0018_business_date_effectivity
Revises: 0017_quote_line_fx_provenance
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0018_business_date_effectivity"
down_revision = "0017_quote_line_fx_provenance"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("charge_business_date_profile_version"):
        return set()
    return {
        column["name"]
        for column in inspector.get_columns("charge_business_date_profile_version")
    }


def upgrade() -> None:
    existing = _columns()
    if not existing:
        return
    with op.batch_alter_table("charge_business_date_profile_version") as batch_op:
        if "effective_from" not in existing:
            batch_op.add_column(sa.Column("effective_from", sa.Date()))
        if "effective_to" not in existing:
            batch_op.add_column(sa.Column("effective_to", sa.Date()))
        check_names = {
            constraint["name"]
            for constraint in inspect(op.get_bind()).get_check_constraints(
                "charge_business_date_profile_version"
            )
            if constraint.get("name")
        }
        if "ck_charge_business_date_profile_version_effectivity" not in check_names:
            batch_op.create_check_constraint(
                "ck_charge_business_date_profile_version_effectivity",
                "effective_from is null or effective_to is null or effective_from <= effective_to",
            )


def downgrade() -> None:
    existing = _columns()
    if not existing:
        return
    check_names = {
        constraint["name"]
        for constraint in inspect(op.get_bind()).get_check_constraints(
            "charge_business_date_profile_version"
        )
        if constraint.get("name")
    }
    with op.batch_alter_table("charge_business_date_profile_version") as batch_op:
        if "ck_charge_business_date_profile_version_effectivity" in check_names:
            batch_op.drop_constraint(
                "ck_charge_business_date_profile_version_effectivity",
                type_="check",
            )
        if "effective_to" in existing:
            batch_op.drop_column("effective_to")
        if "effective_from" in existing:
            batch_op.drop_column("effective_from")
