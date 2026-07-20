"""Initial charge management schema.

Revision ID: 0001_initial_charge_management
Revises:
Create Date: 2026-05-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_charge_management"
down_revision = None
branch_labels = None
depends_on = None


COMMON_COMPONENTS = (
    ("BASE_FREIGHT", "Base Freight", "FREIGHT", "BOTH", "TRANSPORT", "SHIPMENT", False),
    ("AIR_FREIGHT", "Air Freight", "FREIGHT", "BOTH", "TRANSPORT", "WEIGHT", False),
    ("LINE_HAUL", "Line Haul", "FREIGHT", "BOTH", "TRANSPORT", "DISTANCE", False),
    ("DRAYAGE", "Drayage", "FREIGHT", "BOTH", "TRANSPORT", "CONTAINER", False),
    ("PICKUP", "Pickup", "ORIGIN", "BOTH", "ORIGIN", "SHIPMENT", False),
    ("ORIGIN_HANDLING", "Origin Handling", "HANDLING", "BOTH", "ORIGIN", "CONTAINER", False),
    ("DESTINATION_HANDLING", "Destination Handling", "HANDLING", "BOTH", "DESTINATION", "CONTAINER", False),
    ("EXPORT_CUSTOMS_CLEARANCE", "Export Customs Clearance", "CUSTOMS", "BOTH", "ORIGIN", "SHIPMENT", False),
    ("IMPORT_CUSTOMS_CLEARANCE", "Import Customs Clearance", "CUSTOMS", "BOTH", "DESTINATION", "SHIPMENT", False),
    ("CUSTOMS_EXAM", "Customs Exam", "CUSTOMS", "BOTH", "CUSTOMS", "SHIPMENT", False),
    ("DUTY", "Duty", "TAX", "PAYER", "CUSTOMS", "PERCENTAGE", True),
    ("VAT_GST_TAX", "VAT/GST Tax", "TAX", "PAYER", "TAX", "PERCENTAGE", True),
    ("INSURANCE", "Insurance", "INSURANCE", "BOTH", "COMMERCIAL", "PERCENTAGE", False),
    ("FUEL_SURCHARGE", "Fuel Surcharge", "SURCHARGE", "BOTH", "TRANSPORT", "PERCENTAGE", False),
    ("CURRENCY_ADJUSTMENT", "Currency Adjustment", "SURCHARGE", "BOTH", "COMMERCIAL", "PERCENTAGE", False),
    ("SECURITY_SURCHARGE", "Security Surcharge", "SURCHARGE", "BOTH", "COMPLIANCE", "SHIPMENT", False),
    ("PEAK_SEASON_SURCHARGE", "Peak Season Surcharge", "SURCHARGE", "BOTH", "TRANSPORT", "CONTAINER", False),
    ("PORT_CONGESTION", "Port Congestion", "SURCHARGE", "BOTH", "PORT", "CONTAINER", False),
    ("TOLL", "Toll", "ACCESSORIAL", "BOTH", "TRANSPORT", "SHIPMENT", False),
    ("LIFT_ON_LIFT_OFF", "Lift On Lift Off", "ACCESSORIAL", "BOTH", "PORT", "CONTAINER", False),
    ("REEFER_SURCHARGE", "Reefer Surcharge", "ACCESSORIAL", "BOTH", "EQUIPMENT", "CONTAINER", False),
    ("HAZMAT_SURCHARGE", "Hazmat Surcharge", "ACCESSORIAL", "BOTH", "COMMODITY", "SHIPMENT", False),
    ("STORAGE", "Storage", "TIME_BASED", "BOTH", "WAREHOUSE", "DAY", False),
    ("DEMURRAGE", "Demurrage", "TIME_BASED", "BOTH", "PORT", "DAY", False),
    ("DETENTION", "Detention", "TIME_BASED", "BOTH", "EQUIPMENT", "DAY", False),
    ("ORIGIN_DOCUMENTATION", "Origin Documentation", "DOCUMENTATION", "BOTH", "ORIGIN", "DOCUMENT", False),
    ("AWB_DOCUMENTATION", "AWB Documentation", "DOCUMENTATION", "BOTH", "AIR", "DOCUMENT", False),
    ("WEIGHBRIDGE_VGM", "Weighbridge/VGM", "DOCUMENTATION", "BOTH", "COMPLIANCE", "CONTAINER", False),
    ("SCREENING", "Screening", "COMPLIANCE", "BOTH", "SECURITY", "SHIPMENT", False),
    ("ROUNDING_ADJUSTMENT", "Rounding Adjustment", "ADJUSTMENT", "BOTH", "FINANCE", "FLAT", False),
    ("MANUAL_ADJUSTMENT", "Manual Adjustment", "ADJUSTMENT", "BOTH", "FINANCE", "FLAT", False),
    ("MARGIN_MARKUP", "Margin Markup", "MARGIN", "PAYEE", "COMMERCIAL", "FLAT", False),
)


def upgrade() -> None:
    op.create_table(
        "charge_management_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_policy", sa.String(length=30), nullable=False, server_default="OPTIONAL"),
        sa.Column("quote_acceptance_mode", sa.String(length=30), nullable=False, server_default="CUSTOMER_ACCEPTANCE"),
        sa.Column("provider_cost_layer_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "quotation_policy in ('REQUIRED', 'OPTIONAL', 'DIRECT_ONLY')",
            name="ck_charge_settings_quotation_policy",
        ),
        sa.CheckConstraint(
            "quote_acceptance_mode in ('AUTO_ACCEPT', 'CUSTOMER_ACCEPTANCE')",
            name="ck_charge_settings_quote_acceptance_mode",
        ),
    )

    op.create_table(
        "charge_component",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_code", sa.String(length=60), nullable=False),
        sa.Column("component_name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("default_party_role", sa.String(length=20), nullable=False),
        sa.Column("charge_context", sa.String(length=80), nullable=False),
        sa.Column("calculation_basis", sa.String(length=40), nullable=False),
        sa.Column("is_tax", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("default_party_role in ('PAYER', 'PAYEE', 'BOTH')", name="ck_charge_component_default_party_role"),
        sa.UniqueConstraint("component_code", name="uq_charge_component_component_code"),
    )
    op.create_index("ix_charge_component_component_code", "charge_component", ["component_code"])

    op.create_table(
        "charge_rate_book",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rate_book_code", sa.String(length=80), nullable=False),
        sa.Column("rate_book_name", sa.String(length=180), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("rate_book_code", name="uq_charge_rate_book_code"),
    )

    op.create_table(
        "charge_rate_contract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_number", sa.String(length=80), nullable=False),
        sa.Column("contract_name", sa.String(length=180), nullable=False),
        sa.Column("contract_role", sa.String(length=20), nullable=False),
        sa.Column("payer_party_ref", sa.String(length=120), nullable=True),
        sa.Column("payee_party_ref", sa.String(length=120), nullable=True),
        sa.Column("party_role_ref", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("partner_id", sa.Integer()),
        sa.Column("customer_id", sa.Integer()),
        sa.Column("vendor_id", sa.Integer()),
        sa.Column("forwarder_id", sa.Integer()),
        sa.Column("carrier_id", sa.Integer()),
        sa.Column("company_id", sa.Integer()),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("contract_role in ('PAYER', 'PAYEE')", name="ck_charge_rate_contract_role"),
        sa.UniqueConstraint("contract_number", name="uq_charge_rate_contract_number"),
    )
    op.create_index(
        "ix_charge_rate_contract_scope",
        "charge_rate_contract",
        ["company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"],
    )

    op.create_table(
        "charge_rate_book_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rate_book_id", sa.Integer(), nullable=False),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("rate_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("basis", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("origin_code", sa.String(length=40)),
        sa.Column("destination_code", sa.String(length=40)),
        sa.Column("mode", sa.String(length=40)),
        sa.Column("equipment_type", sa.String(length=60)),
        sa.Column("commodity_code", sa.String(length=80)),
        sa.Column("service_level", sa.String(length=80)),
        sa.Column("scale_from", sa.Numeric(18, 6)),
        sa.Column("scale_to", sa.Numeric(18, 6)),
        sa.Column("minimum_amount", sa.Numeric(18, 6)),
        sa.Column("maximum_amount", sa.Numeric(18, 6)),
        sa.Column("validity_from", sa.Date()),
        sa.Column("validity_to", sa.Date()),
        sa.Column("attributes_json", sa.JSON()),
        sa.ForeignKeyConstraint(["rate_book_id"], ["charge_rate_book.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
    )
    op.create_index("ix_charge_rate_book_entry_book_component", "charge_rate_book_entry", ["rate_book_id", "charge_component_id"])
    op.create_index("ix_charge_rate_book_entry_lane", "charge_rate_book_entry", ["origin_code", "destination_code", "mode"])

    op.create_table(
        "charge_contract_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("rate_book_id", sa.Integer()),
        sa.Column("calculation_template_id", sa.Integer()),
        sa.Column("origin_code", sa.String(length=40)),
        sa.Column("destination_code", sa.String(length=40)),
        sa.Column("mode", sa.String(length=40)),
        sa.Column("equipment_type", sa.String(length=60)),
        sa.Column("commodity_code", sa.String(length=80)),
        sa.Column("service_level", sa.String(length=80)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("attributes_json", sa.JSON()),
        sa.ForeignKeyConstraint(["contract_id"], ["charge_rate_contract.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
        sa.ForeignKeyConstraint(["rate_book_id"], ["charge_rate_book.id"]),
    )
    op.create_index("ix_charge_contract_line_contract_component", "charge_contract_line", ["contract_id", "charge_component_id"])
    op.create_index("ix_charge_contract_line_lane", "charge_contract_line", ["origin_code", "destination_code", "mode"])

    op.create_table(
        "charge_calculation_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_code", sa.String(length=80), nullable=False),
        sa.Column("template_name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("template_code", name="uq_charge_calculation_template_code"),
    )
    op.create_table(
        "charge_calculation_template_step",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("rate_book_id", sa.Integer()),
        sa.Column("precondition_json", sa.JSON()),
        sa.Column("subtotal_group", sa.String(length=80)),
        sa.Column("is_statistical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["template_id"], ["charge_calculation_template.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
        sa.ForeignKeyConstraint(["rate_book_id"], ["charge_rate_book.id"]),
        sa.UniqueConstraint("template_id", "sequence_no", name="uq_charge_calc_template_step_sequence"),
    )

    op.create_table(
        "charge_quote_request",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_object_type", sa.String(length=60), nullable=False, server_default="MANUAL"),
        sa.Column("source_object_id", sa.String(length=120)),
        sa.Column("company_id", sa.Integer()),
        sa.Column("customer_id", sa.Integer()),
        sa.Column("vendor_id", sa.Integer()),
        sa.Column("forwarder_id", sa.Integer()),
        sa.Column("carrier_id", sa.Integer()),
        sa.Column("origin_code", sa.String(length=40)),
        sa.Column("destination_code", sa.String(length=40)),
        sa.Column("mode", sa.String(length=40)),
        sa.Column("equipment_type", sa.String(length=60)),
        sa.Column("commodity_code", sa.String(length=80)),
        sa.Column("service_level", sa.String(length=80)),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("gross_weight", sa.Numeric(18, 6)),
        sa.Column("gross_volume_cbm", sa.Numeric(18, 6)),
        sa.Column("container_count", sa.Numeric(18, 6)),
        sa.Column("package_count", sa.Numeric(18, 6)),
        sa.Column("package_type", sa.String(length=60)),
        sa.Column("requested_service_date", sa.Date()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("quotation_policy_snapshot", sa.String(length=30), nullable=False, server_default="OPTIONAL"),
        sa.Column("awarded_option_id", sa.Integer()),
        sa.Column("margin_rules_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("context_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_charge_quote_request_scope", "charge_quote_request", ["company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"])
    op.create_index("ix_charge_quote_request_source", "charge_quote_request", ["source_object_type", "source_object_id"])

    op.create_table(
        "charge_quote_offer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_request_id", sa.Integer(), nullable=False),
        sa.Column("provider_party_ref", sa.String(length=160)),
        sa.Column("provider_role_ref", sa.String(length=120)),
        sa.Column("offer_number", sa.String(length=120)),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="MANUAL"),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("is_sealed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("transit_time_days", sa.Integer()),
        sa.Column("service_level", sa.String(length=80)),
        sa.Column("performance_score", sa.Numeric(18, 6)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="SUBMITTED"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quote_request_id"], ["charge_quote_request.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_charge_quote_offer_quote", "charge_quote_offer", ["quote_request_id"])
    op.create_index("ix_charge_quote_offer_provider", "charge_quote_offer", ["provider_party_ref", "provider_role_ref"])
    op.create_index("ix_charge_quote_offer_status", "charge_quote_offer", ["status"])

    op.create_table(
        "charge_quote_option",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_request_id", sa.Integer(), nullable=False),
        sa.Column("option_name", sa.String(length=180), nullable=False),
        sa.Column("source_offer_id", sa.Integer()),
        sa.Column("payer_contract_id", sa.Integer()),
        sa.Column("payee_contract_id", sa.Integer()),
        sa.Column("payer_total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("payee_total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("margin_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("margin_percent", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("transit_time_days", sa.Integer()),
        sa.Column("service_level_score", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("policy_compliant", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rank", sa.Integer()),
        sa.Column("score", sa.Numeric(18, 6)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["quote_request_id"], ["charge_quote_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_offer_id"], ["charge_quote_offer.id"]),
        sa.ForeignKeyConstraint(["payer_contract_id"], ["charge_rate_contract.id"]),
        sa.ForeignKeyConstraint(["payee_contract_id"], ["charge_rate_contract.id"]),
    )

    op.create_table(
        "charge_quote_option_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_option_id", sa.Integer(), nullable=False),
        sa.Column("relationship_role", sa.String(length=20), nullable=False),
        sa.Column("payer_party_ref", sa.String(length=120), nullable=True),
        sa.Column("payee_party_ref", sa.String(length=120), nullable=True),
        sa.Column("party_role_ref", sa.String(length=120), nullable=True),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("basis", sa.String(length=40), nullable=False),
        sa.Column("source_contract_id", sa.Integer()),
        sa.Column("source_rate_book_id", sa.Integer()),
        sa.Column("is_margin_line", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("relationship_role in ('PAYER', 'PAYEE')", name="ck_charge_quote_option_line_role"),
        sa.ForeignKeyConstraint(["quote_option_id"], ["charge_quote_option.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
        sa.ForeignKeyConstraint(["source_contract_id"], ["charge_rate_contract.id"]),
        sa.ForeignKeyConstraint(["source_rate_book_id"], ["charge_rate_book.id"]),
    )

    op.create_table(
        "charge_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_number", sa.String(length=80), nullable=False),
        sa.Column("quote_request_id", sa.Integer()),
        sa.Column("quote_option_id", sa.Integer()),
        sa.Column("quotation_policy_snapshot", sa.String(length=30), nullable=False, server_default="OPTIONAL"),
        sa.Column("source_object_type", sa.String(length=60), nullable=False, server_default="MANUAL"),
        sa.Column("source_object_id", sa.String(length=120)),
        sa.Column("company_id", sa.Integer()),
        sa.Column("customer_id", sa.Integer()),
        sa.Column("vendor_id", sa.Integer()),
        sa.Column("forwarder_id", sa.Integer()),
        sa.Column("carrier_id", sa.Integer()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ESTIMATED"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("payer_total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("payee_total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("margin_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("exported_at", sa.DateTime(timezone=True)),
        sa.Column("reversed_at", sa.DateTime(timezone=True)),
        sa.Column("reversal_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quote_request_id"], ["charge_quote_request.id"]),
        sa.ForeignKeyConstraint(["quote_option_id"], ["charge_quote_option.id"]),
        sa.UniqueConstraint("document_number", name="uq_charge_document_number"),
    )
    op.create_index("ix_charge_document_scope", "charge_document", ["company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"])
    op.create_index("ix_charge_document_source", "charge_document", ["source_object_type", "source_object_id"])

    op.create_table(
        "charge_quote_commitment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("commitment_number", sa.String(length=80), nullable=False),
        sa.Column("quote_request_id", sa.Integer(), nullable=False),
        sa.Column("quote_option_id", sa.Integer(), nullable=False),
        sa.Column("charge_document_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer()),
        sa.Column("customer_id", sa.Integer()),
        sa.Column("vendor_id", sa.Integer()),
        sa.Column("forwarder_id", sa.Integer()),
        sa.Column("carrier_id", sa.Integer()),
        sa.Column("origin_code", sa.String(length=40)),
        sa.Column("destination_code", sa.String(length=40)),
        sa.Column("mode", sa.String(length=40)),
        sa.Column("equipment_type", sa.String(length=60)),
        sa.Column("commodity_code", sa.String(length=80)),
        sa.Column("service_level", sa.String(length=80)),
        sa.Column("package_type", sa.String(length=60)),
        sa.Column("requested_service_date", sa.Date()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("committed_container_count", sa.Numeric(18, 6)),
        sa.Column("consumed_container_count", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("committed_package_count", sa.Numeric(18, 6)),
        sa.Column("consumed_package_count", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("committed_chargeable_weight", sa.Numeric(18, 6)),
        sa.Column("consumed_chargeable_weight", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("committed_quantity", sa.Numeric(18, 6), nullable=False, server_default="1"),
        sa.Column("consumed_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("committed_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("consumed_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quote_request_id"], ["charge_quote_request.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quote_option_id"], ["charge_quote_option.id"]),
        sa.ForeignKeyConstraint(["charge_document_id"], ["charge_document.id"]),
        sa.UniqueConstraint("commitment_number", name="uq_charge_quote_commitment_number"),
        sa.UniqueConstraint("quote_option_id", name="uq_charge_quote_commitment_quote_option_id"),
    )
    op.create_index("ix_charge_quote_commitment_scope", "charge_quote_commitment", ["company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"])
    op.create_index("ix_charge_quote_commitment_lane", "charge_quote_commitment", ["origin_code", "destination_code", "mode"])
    op.create_index("ix_charge_quote_commitment_status_validity", "charge_quote_commitment", ["status", "valid_to"])

    op.create_table(
        "charge_quote_commitment_consumption",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("commitment_id", sa.Integer(), nullable=False),
        sa.Column("source_object_type", sa.String(length=60), nullable=False),
        sa.Column("source_object_id", sa.String(length=120)),
        sa.Column("reference_number", sa.String(length=120)),
        sa.Column("container_count", sa.Numeric(18, 6)),
        sa.Column("package_count", sa.Numeric(18, 6)),
        sa.Column("chargeable_weight", sa.Numeric(18, 6)),
        sa.Column("quantity", sa.Numeric(18, 6)),
        sa.Column("amount", sa.Numeric(18, 6)),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("reversed_at", sa.DateTime(timezone=True)),
        sa.Column("reversal_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["commitment_id"], ["charge_quote_commitment.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_charge_quote_commitment_consumption_commitment", "charge_quote_commitment_consumption", ["commitment_id"])
    op.create_index("ix_charge_quote_commitment_consumption_source", "charge_quote_commitment_consumption", ["source_object_type", "source_object_id"])
    op.create_index("ix_charge_quote_commitment_consumption_status", "charge_quote_commitment_consumption", ["status"])

    op.create_table(
        "charge_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("charge_document_id", sa.Integer(), nullable=False),
        sa.Column("relationship_role", sa.String(length=20), nullable=False),
        sa.Column("payer_party_ref", sa.String(length=120), nullable=True),
        sa.Column("payee_party_ref", sa.String(length=120), nullable=True),
        sa.Column("party_role_ref", sa.String(length=120), nullable=True),
        sa.Column("charge_component_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("expected_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("actual_amount", sa.Numeric(18, 6)),
        sa.Column("approved_amount", sa.Numeric(18, 6)),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("basis", sa.String(length=40), nullable=False),
        sa.Column("source_quote_option_line_id", sa.Integer()),
        sa.CheckConstraint("relationship_role in ('PAYER', 'PAYEE')", name="ck_charge_line_role"),
        sa.ForeignKeyConstraint(["charge_document_id"], ["charge_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
        sa.ForeignKeyConstraint(["source_quote_option_line_id"], ["charge_quote_option_line.id"]),
    )

    op.create_table(
        "charge_invoice",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("charge_document_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=120), nullable=False),
        sa.Column("invoice_type", sa.String(length=30), nullable=False),
        sa.Column("invoice_date", sa.Date()),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("total_amount", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="CAPTURED"),
        sa.Column("lines_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["charge_document_id"], ["charge_document.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("charge_document_id", "invoice_number", name="uq_charge_invoice_document_number"),
    )

    op.create_table(
        "charge_match_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("charge_document_id", sa.Integer(), nullable=False),
        sa.Column("charge_line_id", sa.Integer()),
        sa.Column("charge_component_id", sa.Integer()),
        sa.Column("expected_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("invoice_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("variance_percent", sa.Numeric(18, 6), nullable=False),
        sa.Column("match_status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["invoice_id"], ["charge_invoice.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_document_id"], ["charge_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_line_id"], ["charge_line.id"]),
        sa.ForeignKeyConstraint(["charge_component_id"], ["charge_component.id"]),
    )
    op.create_index("ix_charge_match_result_invoice", "charge_match_result", ["invoice_id"])
    op.create_index("ix_charge_match_result_document", "charge_match_result", ["charge_document_id"])

    op.create_table(
        "charge_export_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("export_number", sa.String(length=80), nullable=False),
        sa.Column("charge_document_id", sa.Integer(), nullable=False),
        sa.Column("target_system", sa.String(length=80), nullable=False, server_default="INTERNAL_LEDGER"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="POSTED"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["charge_document_id"], ["charge_document.id"]),
        sa.UniqueConstraint("export_number", name="uq_charge_export_batch_number"),
    )

    _seed_components()
    _seed_settings()


def downgrade() -> None:
    op.drop_table("charge_export_batch")
    op.drop_index("ix_charge_match_result_document", table_name="charge_match_result")
    op.drop_index("ix_charge_match_result_invoice", table_name="charge_match_result")
    op.drop_table("charge_match_result")
    op.drop_table("charge_invoice")
    op.drop_table("charge_line")
    op.drop_index("ix_charge_quote_commitment_consumption_source", table_name="charge_quote_commitment_consumption")
    op.drop_index("ix_charge_quote_commitment_consumption_commitment", table_name="charge_quote_commitment_consumption")
    op.drop_index("ix_charge_quote_commitment_consumption_status", table_name="charge_quote_commitment_consumption")
    op.drop_table("charge_quote_commitment_consumption")
    op.drop_index("ix_charge_quote_commitment_status_validity", table_name="charge_quote_commitment")
    op.drop_index("ix_charge_quote_commitment_lane", table_name="charge_quote_commitment")
    op.drop_index("ix_charge_quote_commitment_scope", table_name="charge_quote_commitment")
    op.drop_table("charge_quote_commitment")
    op.drop_index("ix_charge_document_source", table_name="charge_document")
    op.drop_index("ix_charge_document_scope", table_name="charge_document")
    op.drop_table("charge_document")
    op.drop_table("charge_quote_option_line")
    op.drop_table("charge_quote_option")
    op.drop_index("ix_charge_quote_offer_status", table_name="charge_quote_offer")
    op.drop_index("ix_charge_quote_offer_provider", table_name="charge_quote_offer")
    op.drop_index("ix_charge_quote_offer_quote", table_name="charge_quote_offer")
    op.drop_table("charge_quote_offer")
    op.drop_index("ix_charge_quote_request_source", table_name="charge_quote_request")
    op.drop_index("ix_charge_quote_request_scope", table_name="charge_quote_request")
    op.drop_table("charge_quote_request")
    op.drop_table("charge_calculation_template_step")
    op.drop_table("charge_calculation_template")
    op.drop_index("ix_charge_contract_line_lane", table_name="charge_contract_line")
    op.drop_index("ix_charge_contract_line_contract_component", table_name="charge_contract_line")
    op.drop_table("charge_contract_line")
    op.drop_index("ix_charge_rate_book_entry_lane", table_name="charge_rate_book_entry")
    op.drop_index("ix_charge_rate_book_entry_book_component", table_name="charge_rate_book_entry")
    op.drop_table("charge_rate_book_entry")
    op.drop_index("ix_charge_rate_contract_scope", table_name="charge_rate_contract")
    op.drop_table("charge_rate_contract")
    op.drop_table("charge_rate_book")
    op.drop_index("ix_charge_component_component_code", table_name="charge_component")
    op.drop_table("charge_component")
    op.drop_table("charge_management_settings")


def _seed_components() -> None:
    component_table = sa.table(
        "charge_component",
        sa.column("component_code", sa.String),
        sa.column("component_name", sa.String),
        sa.column("category", sa.String),
        sa.column("default_party_role", sa.String),
        sa.column("charge_context", sa.String),
        sa.column("calculation_basis", sa.String),
        sa.column("is_tax", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        component_table,
        [
            {
                "component_code": code,
                "component_name": name,
                "category": category,
                "default_party_role": party_role,
                "charge_context": context,
                "calculation_basis": basis,
                "is_tax": is_tax,
                "is_active": True,
            }
            for code, name, category, party_role, context, basis, is_tax in COMMON_COMPONENTS
        ],
    )


def _seed_settings() -> None:
    settings_table = sa.table(
        "charge_management_settings",
        sa.column("id", sa.Integer),
        sa.column("quotation_policy", sa.String),
        sa.column("quote_acceptance_mode", sa.String),
        sa.column("provider_cost_layer_enabled", sa.Boolean),
        sa.column("settings_json", sa.JSON),
    )
    op.bulk_insert(
        settings_table,
        [
            {
                "id": 1,
                "quotation_policy": "OPTIONAL",
                "quote_acceptance_mode": "CUSTOMER_ACCEPTANCE",
                "provider_cost_layer_enabled": False,
                "settings_json": {
                    "supported_quotation_policies": ["REQUIRED", "OPTIONAL", "DIRECT_ONLY"],
                    "supported_quote_acceptance_modes": ["AUTO_ACCEPT", "CUSTOMER_ACCEPTANCE"],
                },
            }
        ],
    )
