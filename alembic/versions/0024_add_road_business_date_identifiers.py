"""Add explicit road pickup, delivery, and CMR business-date identifiers.

Revision ID: 0024_road_business_dates
Revises: 0023_road_charge_metadata
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_road_business_dates"
down_revision = "0023_road_charge_metadata"
branch_labels = None
depends_on = None


ROAD_STEPS = (
    (10, "ROAD_ACTUAL_PICKUP_DATE", "Actual road pickup date."),
    (20, "ROAD_PLANNED_PICKUP_DATE", "Planned road pickup date."),
    (30, "CMR_ISSUE_DATE", "CMR or e-CMR consignment-note issue date."),
    (40, "DOCUMENT_DATE", "Charge document date."),
)

LEGACY_STEPS = (
    (10, "SHIPMENT_ACTUAL_DEPARTURE_DATE", "Actual pickup or dispatch date."),
    (20, "SHIPMENT_PLANNED_DEPARTURE_DATE", "Planned pickup or dispatch date."),
    (30, "DOCUMENT_DATE", "Charge document date."),
)


def _replace_steps(bind: sa.engine.Connection, steps: tuple[tuple[int, str, str], ...]) -> None:
    version_id = bind.execute(
        sa.text(
            "SELECT version.id FROM charge_business_date_profile_version AS version "
            "JOIN charge_business_date_profile AS profile ON profile.id = version.profile_id "
            "WHERE profile.profile_code = 'ROAD_SHIPMENT_STANDARD' "
            "AND version.version_number = 1"
        )
    ).scalar_one_or_none()
    if version_id is None:
        return

    bind.execute(
        sa.text("DELETE FROM charge_business_date_profile_step WHERE version_id = :version_id"),
        {"version_id": int(version_id)},
    )
    next_id = int(
        bind.execute(
            sa.text("SELECT COALESCE(MAX(id), 0) + 1 FROM charge_business_date_profile_step")
        ).scalar_one()
    )
    for offset, (step_number, date_key, notes) in enumerate(steps):
        bind.execute(
            sa.text(
                "INSERT INTO charge_business_date_profile_step "
                "(id, version_id, step_number, date_key, notes) "
                "VALUES (:id, :version_id, :step_number, :date_key, :notes)"
            ),
            {
                "id": next_id + offset,
                "version_id": int(version_id),
                "step_number": step_number,
                "date_key": date_key,
                "notes": notes,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE charge_business_date_profile "
            "SET description = 'Actual pickup, planned pickup, CMR issue, then document date.', "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE profile_code = 'ROAD_SHIPMENT_STANDARD'"
        )
    )
    _replace_steps(bind, ROAD_STEPS)


def downgrade() -> None:
    bind = op.get_bind()
    _replace_steps(bind, LEGACY_STEPS)
    bind.execute(
        sa.text(
            "UPDATE charge_business_date_profile "
            "SET description = 'Actual pickup/departure, planned pickup/departure, then document date.', "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE profile_code = 'ROAD_SHIPMENT_STANDARD'"
        )
    )
