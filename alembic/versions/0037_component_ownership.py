"""Add per-forwarder charge component ownership and code uniqueness."""

from alembic import op
import sqlalchemy as sa

revision = "0037_component_ownership"
down_revision = "0036_component_manual_entry_eligibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("charge_component") as batch:
        batch.add_column(sa.Column("owner_type", sa.String(20), nullable=False, server_default="GLOBAL"))
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=False, server_default="0"))
        batch.drop_constraint("uq_charge_component_code", type_="unique")
        batch.create_unique_constraint("uq_charge_component_owner_code", ["owner_type", "owner_id", "component_code"])
        batch.create_check_constraint(
            "ck_charge_component_owner",
            "(owner_type = 'GLOBAL' AND owner_id = 0) OR (owner_type = 'FORWARDER' AND owner_id > 0)",
        )


def downgrade() -> None:
    duplicates = op.get_bind().execute(sa.text(
        "SELECT component_code FROM charge_component GROUP BY component_code HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates is not None:
        raise RuntimeError("Cannot remove component ownership while codes repeat across owners.")
    with op.batch_alter_table("charge_component") as batch:
        batch.drop_constraint("ck_charge_component_owner", type_="check")
        batch.drop_constraint("uq_charge_component_owner_code", type_="unique")
        batch.create_unique_constraint("uq_charge_component_code", ["component_code"])
        batch.drop_column("owner_id")
        batch.drop_column("owner_type")
