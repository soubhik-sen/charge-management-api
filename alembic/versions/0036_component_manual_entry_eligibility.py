"""Add component manual-entry eligibility and direct document allocation profiles."""

from alembic import op
import sqlalchemy as sa


revision = "0036_component_manual_entry_eligibility"
down_revision = "0035_payment_baseline_profile_purpose"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "charge_component",
        sa.Column("manual_entry_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "charge_allocation_profile_version",
        sa.Column("source_to_item_driver", sa.String(length=40), nullable=True),
    )
    with op.batch_alter_table("charge_allocation_profile_version") as batch:
        batch.drop_constraint("ck_charge_allocation_profile_version_source_level", type_="check")
        batch.create_check_constraint(
            "ck_charge_allocation_profile_version_source_level",
            "source_level in ('SHIPMENT', 'CONTAINER', 'HOUSE', 'DOCUMENT')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM charge_component WHERE manual_entry_enabled = true")).scalar_one():
        raise RuntimeError("Manually enabled components must be explicitly disabled before downgrade.")
    if bind.execute(
        sa.text(
            "SELECT count(*) FROM charge_allocation_profile_version "
            "WHERE source_level = 'DOCUMENT' OR source_to_item_driver IS NOT NULL"
        )
    ).scalar_one():
        raise RuntimeError("DOCUMENT allocation profiles must be explicitly removed before downgrade.")
    with op.batch_alter_table("charge_allocation_profile_version") as batch:
        batch.drop_constraint("ck_charge_allocation_profile_version_source_level", type_="check")
        batch.create_check_constraint(
            "ck_charge_allocation_profile_version_source_level",
            "source_level in ('SHIPMENT', 'CONTAINER', 'HOUSE')",
        )
    op.drop_column("charge_allocation_profile_version", "source_to_item_driver")
    op.drop_column("charge_component", "manual_entry_enabled")
