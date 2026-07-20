"""Add transport mode scope to component aliases.

Revision ID: 0007_alias_transport_mode
Revises: 0006_scoped_alias_drivers
Create Date: 2026-07-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0007_alias_transport_mode"
down_revision = "0006_scoped_alias_drivers"
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
        if "transport_mode" not in columns:
            batch_op.add_column(sa.Column("transport_mode", sa.String(length=40), nullable=True))
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
                "transport_mode",
            ],
        )

    op.create_index(
        _LOOKUP_INDEX,
        _TABLE,
        [
            "document_kind",
            "template_key",
            "normalized_label",
            "customer_id",
            "forwarder_id",
            "transport_mode",
        ],
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
            [
                "document_kind",
                "template_key",
                "source_section",
                "normalized_label",
                "customer_id",
                "forwarder_id",
            ],
        )
        if "transport_mode" in columns:
            batch_op.drop_column("transport_mode")

    op.create_index(
        _LOOKUP_INDEX,
        _TABLE,
        ["document_kind", "template_key", "normalized_label", "customer_id", "forwarder_id"],
    )
