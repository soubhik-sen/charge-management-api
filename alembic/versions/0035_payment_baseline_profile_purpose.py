"""Separate payment baseline profiles from exchange-rate date profiles."""
from alembic import op
import sqlalchemy as sa

revision = "0035_payment_baseline_profile_purpose"
down_revision = "0034_charge_calculation_profile_parity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("charge_business_date_profile", sa.Column("business_purpose", sa.String(40),
        nullable=False, server_default="EXCHANGE_RATE_DATE"))
    with op.batch_alter_table("charge_business_date_profile_assignment") as batch:
        batch.drop_constraint("ck_charge_business_date_profile_assignment_business_purpose", type_="check")
        batch.create_check_constraint("ck_charge_business_date_profile_assignment_business_purpose",
            "business_purpose in ('EXCHANGE_RATE_DATE', 'PAYMENT_BASELINE_DATE')")


def downgrade():
    # Refuse rollback while payment-purpose data exists; don't erase configuration.
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM charge_business_date_profile WHERE business_purpose = 'PAYMENT_BASELINE_DATE'")).scalar_one()
    if count:
        raise RuntimeError("Payment baseline profiles must be explicitly removed before downgrade.")
    with op.batch_alter_table("charge_business_date_profile_assignment") as batch:
        batch.drop_constraint("ck_charge_business_date_profile_assignment_business_purpose", type_="check")
        batch.create_check_constraint("ck_charge_business_date_profile_assignment_business_purpose",
            "business_purpose in ('EXCHANGE_RATE_DATE')")
    op.drop_column("charge_business_date_profile", "business_purpose")
