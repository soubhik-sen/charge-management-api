"""Assign calculation profiles to reusable distance and time components.

Revision ID: 0029_component_calculation_defaults
Revises: 0028_contract_template_routing
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


revision = "0029_component_calculation_defaults"
down_revision = "0028_contract_template_routing"
branch_labels = None
depends_on = None


COMPONENT_TABLE = "charge_component"
PROFILE_TABLE = "charge_calculation_profile"

PROFILE_BY_COMPONENT = {
    "LINE_HAUL": "PER_KILOMETER",
    "STORAGE": "PER_DAY",
    "DEMURRAGE": "PER_DAY",
    "DETENTION": "PER_DAY",
    "ROAD_TOLL": "PER_KILOMETER",
    "WAITING_TIME": "PER_HOUR",
    "PALLET_EXCHANGE": "PER_PALLET",
    "MULTI_STOP_SURCHARGE": "PER_STOP",
}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(COMPONENT_TABLE) or not inspector.has_table(PROFILE_TABLE):
        return
    for component_code, profile_code in PROFILE_BY_COMPONENT.items():
        op.execute(
            sa.text(
                "UPDATE charge_component "
                "SET default_calculation_profile_id = ("
                "SELECT id FROM charge_calculation_profile WHERE profile_code = :profile_code"
                ") "
                "WHERE component_code = :component_code "
                "AND default_calculation_profile_id IS NULL"
            ).bindparams(component_code=component_code, profile_code=profile_code)
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(COMPONENT_TABLE) or not inspector.has_table(PROFILE_TABLE):
        return
    for component_code, profile_code in PROFILE_BY_COMPONENT.items():
        op.execute(
            sa.text(
                "UPDATE charge_component SET default_calculation_profile_id = NULL "
                "WHERE component_code = :component_code "
                "AND default_calculation_profile_id = ("
                "SELECT id FROM charge_calculation_profile WHERE profile_code = :profile_code"
                ")"
            ).bindparams(component_code=component_code, profile_code=profile_code)
        )
