"""Identify quote commitments by executable plan route.

Revision ID: 0031_route_commitment_identity
Revises: 0030_caller_dimension_mapping
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0031_route_commitment_identity"
down_revision = "0030_caller_dimension_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_identity", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_source_system", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_plan_id", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_route_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_source_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "charge_quote_commitment",
        sa.Column("execution_request_number", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "uq_charge_quote_commitment_execution_identity",
        "charge_quote_commitment",
        ["execution_identity"],
        unique=True,
    )
    op.create_index(
        "ix_charge_quote_commitment_execution_route",
        "charge_quote_commitment",
        ["execution_source_system", "execution_plan_id", "execution_route_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_charge_quote_commitment_execution_route",
        table_name="charge_quote_commitment",
    )
    op.drop_index(
        "uq_charge_quote_commitment_execution_identity",
        table_name="charge_quote_commitment",
    )
    op.drop_column("charge_quote_commitment", "execution_request_number")
    op.drop_column("charge_quote_commitment", "execution_source_id")
    op.drop_column("charge_quote_commitment", "execution_route_id")
    op.drop_column("charge_quote_commitment", "execution_plan_id")
    op.drop_column("charge_quote_commitment", "execution_source_system")
    op.drop_column("charge_quote_commitment", "execution_identity")
