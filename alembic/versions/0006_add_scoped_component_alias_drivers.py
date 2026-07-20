"""Add scoped component alias allocation drivers.

Revision ID: 0006_scoped_alias_drivers
Revises: 0005_component_alias_audit
Create Date: 2026-07-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_scoped_alias_drivers"
down_revision = "0005_component_alias_audit"
branch_labels = None
depends_on = None


_TABLE = "charge_component_alias"
_UNIQUE = "uq_charge_component_alias_scope_label"
_LOOKUP_INDEX = "ix_charge_component_alias_lookup"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(_TABLE)}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints(_TABLE)}

    if _LOOKUP_INDEX in indexes:
        op.drop_index(_LOOKUP_INDEX, table_name=_TABLE)

    with op.batch_alter_table(_TABLE) as batch_op:
        if "customer_id" not in columns:
            batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        if "forwarder_id" not in columns:
            batch_op.add_column(sa.Column("forwarder_id", sa.Integer(), nullable=True))
        if "container_house_allocation_basis" not in columns:
            batch_op.add_column(sa.Column("container_house_allocation_basis", sa.String(length=40), nullable=True))
        if "house_item_allocation_basis" not in columns:
            batch_op.add_column(sa.Column("house_item_allocation_basis", sa.String(length=40), nullable=True))
        if _UNIQUE in uniques:
            batch_op.drop_constraint(_UNIQUE, type_="unique")
        batch_op.create_unique_constraint(
            _UNIQUE,
            [
                "document_kind",
                "template_key",
                "source_section",
                "normalized_label",
                "customer_id",
                "forwarder_id",
            ],
        )

    op.execute(
        sa.text(
            """
            UPDATE charge_component_alias
               SET container_house_allocation_basis = COALESCE(NULLIF(container_house_allocation_basis, ''), NULLIF(default_allocation_basis, ''), 'CBM'),
                   house_item_allocation_basis = COALESCE(NULLIF(house_item_allocation_basis, ''), NULLIF(default_allocation_basis, ''), 'CBM')
            """
        )
    )

    op.create_index(
        _LOOKUP_INDEX,
        _TABLE,
        ["document_kind", "template_key", "normalized_label", "customer_id", "forwarder_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(_TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(_TABLE)}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints(_TABLE)}

    if _LOOKUP_INDEX in indexes:
        op.drop_index(_LOOKUP_INDEX, table_name=_TABLE)

    with op.batch_alter_table(_TABLE) as batch_op:
        if _UNIQUE in uniques:
            batch_op.drop_constraint(_UNIQUE, type_="unique")
        batch_op.create_unique_constraint(
            _UNIQUE,
            ["document_kind", "template_key", "source_section", "normalized_label"],
        )
        if "house_item_allocation_basis" in columns:
            batch_op.drop_column("house_item_allocation_basis")
        if "container_house_allocation_basis" in columns:
            batch_op.drop_column("container_house_allocation_basis")
        if "forwarder_id" in columns:
            batch_op.drop_column("forwarder_id")
        if "customer_id" in columns:
            batch_op.drop_column("customer_id")

    op.create_index(_LOOKUP_INDEX, _TABLE, ["document_kind", "template_key", "normalized_label"])
