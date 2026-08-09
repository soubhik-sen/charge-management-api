"""Version rate books and make published rows immutable.

Revision ID: 0021_version_rate_books
Revises: 0020_business_date_lock_version
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0021_version_rate_books"
down_revision = "0020_business_date_lock_version"
branch_labels = None
depends_on = None


TABLE = "charge_rate_book"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE)
        if constraint.get("name")
    }
    with op.batch_alter_table(TABLE) as batch_op:
        definitions = (
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "supersedes_rate_book_id",
                sa.Integer(),
                sa.ForeignKey(
                    "charge_rate_book.id",
                    name="fk_charge_rate_book_supersedes",
                    ondelete="SET NULL",
                ),
            ),
            sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("published_at", sa.DateTime(timezone=True)),
        )
        for definition in definitions:
            if definition.name not in columns:
                batch_op.add_column(definition)
        if "uq_charge_rate_book_code" in unique_names:
            batch_op.drop_constraint("uq_charge_rate_book_code", type_="unique")
        if "uq_charge_rate_book_code_version" not in unique_names:
            batch_op.create_unique_constraint(
                "uq_charge_rate_book_code_version",
                ["rate_book_code", "version_number"],
            )
    op.execute(
        sa.text(
            "UPDATE charge_rate_book "
            "SET status = 'PUBLISHED', published_at = COALESCE(published_at, CURRENT_TIMESTAMP) "
            "WHERE UPPER(status) = 'ACTIVE'"
        )
    )
    indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(TABLE)}
    if "ix_charge_rate_book_code_version" not in indexes:
        op.create_index(
            "ix_charge_rate_book_code_version",
            TABLE,
            ["rate_book_code", "version_number"],
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(TABLE)}
    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE)
        if constraint.get("name")
    }
    indexes = {index["name"] for index in inspector.get_indexes(TABLE)}
    op.execute(
        sa.text(
            "UPDATE charge_rate_book SET status = 'ACTIVE' "
            "WHERE UPPER(status) = 'PUBLISHED'"
        )
    )
    if "ix_charge_rate_book_code_version" in indexes:
        op.drop_index("ix_charge_rate_book_code_version", table_name=TABLE)
    with op.batch_alter_table(TABLE) as batch_op:
        if "uq_charge_rate_book_code_version" in unique_names:
            batch_op.drop_constraint("uq_charge_rate_book_code_version", type_="unique")
        if "uq_charge_rate_book_code" not in unique_names:
            batch_op.create_unique_constraint("uq_charge_rate_book_code", ["rate_book_code"])
        for column_name in (
            "published_at",
            "lock_version",
            "supersedes_rate_book_id",
            "version_number",
        ):
            if column_name in columns:
                batch_op.drop_column(column_name)
