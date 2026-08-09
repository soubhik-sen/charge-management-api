"""Add optimistic concurrency to business date profile versions.

Revision ID: 0020_business_date_lock_version
Revises: 0019_allocation_profile_controls
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0020_business_date_lock_version"
down_revision = "0019_allocation_profile_controls"
branch_labels = None
depends_on = None


TABLE = "charge_business_date_profile_version"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    if "lock_version" not in columns:
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.add_column(
                sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1")
            )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    if "lock_version" in columns:
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.drop_column("lock_version")
