"""Add charge date basis to charge components.

Revision ID: 0008_charge_component_charge_date_basis
Revises: 0007_alias_transport_mode
Create Date: 2026-07-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_charge_component_charge_date_basis"
down_revision = "0007_alias_transport_mode"
branch_labels = None
depends_on = None


_TABLE = "charge_component"
_CHECK = "ck_charge_component_charge_date_basis"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(_TABLE):
        return

    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints(_TABLE)}

    with op.batch_alter_table(_TABLE) as batch_op:
        if "charge_date_basis" not in columns:
            batch_op.add_column(
                sa.Column(
                    "charge_date_basis",
                    sa.String(length=40),
                    nullable=False,
                    server_default="DOCUMENT_DATE",
                )
            )
        if _CHECK not in checks:
            batch_op.create_check_constraint(
                _CHECK,
                "charge_date_basis in ('DOCUMENT_DATE', 'SHIPMENT_DEPARTURE_DATE', 'SHIPMENT_ARRIVAL_DATE', 'HOUSE_BILL_ISSUE_DATE', 'MANUAL')",
            )

    op.execute(
        sa.text(
            """
            UPDATE charge_component
               SET charge_date_basis = 'DOCUMENT_DATE'
             WHERE charge_date_basis IS NULL
                OR charge_date_basis = ''
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(_TABLE):
        return

    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints(_TABLE)}

    with op.batch_alter_table(_TABLE) as batch_op:
        if _CHECK in checks:
            batch_op.drop_constraint(_CHECK, type_="check")
        if "charge_date_basis" in columns:
            batch_op.drop_column("charge_date_basis")
