"""Align free-time scopes and pricing-dimension identity.

Revision ID: 0033_free_time_scope_and_dimension_identity
Revises: 0032_owner_scoped_profiles_and_free_time_rules
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0033_free_time_scope_and_dimension_identity"
down_revision = "0032_owner_scoped_profiles_and_free_time_rules"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "ck_charge_free_time_rule_scope_type"
CURRENT_SCOPE_CHECK = (
    "scope_type in ('GLOBAL', 'TENANT', 'COMPANY', 'CUSTOMER', "
    "'VENDOR', 'FORWARDER', 'CARRIER')"
)
PREVIOUS_SCOPE_CHECK = (
    "scope_type in ('GLOBAL', 'COMPANY', 'CUSTOMER', 'VENDOR', "
    "'FORWARDER', 'CARRIER')"
)


def _replace_scope_constraint(bind: sa.engine.Connection, condition: str) -> None:
    inspector = inspect(bind)
    if not inspector.has_table("charge_free_time_rule"):
        return
    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("charge_free_time_rule")
        if constraint.get("name")
    }
    with op.batch_alter_table("charge_free_time_rule") as batch_op:
        if CONSTRAINT_NAME in constraint_names:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
        batch_op.create_check_constraint(CONSTRAINT_NAME, condition)


def _synchronize_pricing_dimension_identity(bind: sa.engine.Connection) -> None:
    if bind.dialect.name != "postgresql" or not inspect(bind).has_table("charge_pricing_dimension"):
        return
    bind.execute(
        sa.text(
            "SELECT setval("
            "pg_get_serial_sequence('charge_pricing_dimension', 'id'), "
            "COALESCE(MAX(id), 1), COUNT(*) > 0) "
            "FROM charge_pricing_dimension"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    _replace_scope_constraint(bind, CURRENT_SCOPE_CHECK)
    _synchronize_pricing_dimension_identity(bind)


def downgrade() -> None:
    _replace_scope_constraint(op.get_bind(), PREVIOUS_SCOPE_CHECK)
