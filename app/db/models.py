from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ChargeManagementSettingsRow(TimestampMixin, Base):
    __tablename__ = "charge_management_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quotation_policy: Mapped[str] = mapped_column(String(30), nullable=False, default="OPTIONAL", server_default="OPTIONAL")
    quote_acceptance_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="CUSTOMER_ACCEPTANCE",
        server_default="CUSTOMER_ACCEPTANCE",
    )
    provider_cost_layer_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    settings_json: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("quotation_policy in ('REQUIRED', 'OPTIONAL', 'DIRECT_ONLY')", name="ck_charge_settings_quotation_policy"),
        CheckConstraint(
            "quote_acceptance_mode in ('AUTO_ACCEPT', 'CUSTOMER_ACCEPTANCE')",
            name="ck_charge_settings_quote_acceptance_mode",
        ),
    )


class ChargeIdSequenceRow(Base):
    __tablename__ = "charge_id_sequence"

    bucket: Mapped[str] = mapped_column(String(80), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class ChargeFxRateSourceRow(TimestampMixin, Base):
    __tablename__ = "charge_fx_rate_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(180), nullable=False)
    provider_url: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    rates: Mapped[list["ChargeFxRateRow"]] = relationship(back_populates="source")

    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_charge_fx_rate_source_priority"),
        Index("ix_charge_fx_rate_source_code", "source_code"),
    )


class ChargeFxRateRow(TimestampMixin, Base):
    __tablename__ = "charge_fx_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("charge_fx_rate_source.id"), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_date: Mapped[object] = mapped_column(Date, nullable=False)
    rate: Mapped[object] = mapped_column(Numeric(20, 10), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False, default="MID", server_default="MID")
    conversion_method: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="DIRECT",
        server_default="DIRECT",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    source: Mapped[ChargeFxRateSourceRow] = relationship(back_populates="rates")

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_currency",
            "target_currency",
            "rate_date",
            "rate_type",
            "conversion_method",
            name="uq_charge_fx_rate_pair_date_source_type_method",
        ),
        CheckConstraint("source_currency <> target_currency", name="ck_charge_fx_rate_currency_pair"),
        CheckConstraint("rate > 0", name="ck_charge_fx_rate_positive"),
        CheckConstraint(
            "rate_type in ('MID', 'BUY', 'SELL', 'CUSTOM')",
            name="ck_charge_fx_rate_type",
        ),
        Index(
            "ix_charge_fx_rate_lookup",
            "source_currency",
            "target_currency",
            "rate_date",
            "rate_type",
            "is_active",
        ),
        Index("ix_charge_fx_rate_source", "source_id"),
    )


class ChargeComponentRow(Base):
    __tablename__ = "charge_component"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    component_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    default_party_role: Mapped[str] = mapped_column(String(20), nullable=False)
    charge_context: Mapped[str] = mapped_column(String(80), nullable=False)
    calculation_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    charge_date_basis: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="DOCUMENT_DATE",
        server_default="DOCUMENT_DATE",
    )
    business_date_policy_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="LEGACY_BASIS",
        server_default="LEGACY_BASIS",
    )
    business_date_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_business_date_profile.id"))
    allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    allocation_profile_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))
    is_tax: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    aliases: Mapped[list["ChargeComponentAliasRow"]] = relationship(back_populates="component")

    __table_args__ = (
        CheckConstraint("default_party_role in ('PAYER', 'PAYEE', 'BOTH')", name="ck_charge_component_default_party_role"),
        CheckConstraint(
            "charge_date_basis in ('DOCUMENT_DATE', 'SHIPMENT_DEPARTURE_DATE', 'SHIPMENT_ARRIVAL_DATE', 'HOUSE_BILL_ISSUE_DATE', 'MANUAL')",
            name="ck_charge_component_charge_date_basis",
        ),
        CheckConstraint(
            "business_date_policy_mode in ('LEGACY_BASIS', 'INHERIT_PROFILE', 'PROFILE_OVERRIDE')",
            name="ck_charge_component_business_date_policy_mode",
        ),
    )


class ChargeComponentAliasRow(TimestampMixin, Base):
    __tablename__ = "charge_component_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_kind: Mapped[str] = mapped_column(String(60), nullable=False, default="CHARGE_PROPOSAL", server_default="CHARGE_PROPOSAL")
    template_key: Mapped[str | None] = mapped_column(String(120))
    source_section: Mapped[str | None] = mapped_column(String(160))
    customer_id: Mapped[int | None] = mapped_column(Integer)
    forwarder_id: Mapped[int | None] = mapped_column(Integer)
    transport_mode: Mapped[str | None] = mapped_column(String(40))
    raw_label: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_label: Mapped[str] = mapped_column(String(240), nullable=False)
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    default_calculation_basis: Mapped[str] = mapped_column(String(40), nullable=False, default="DOCUMENT", server_default="DOCUMENT")
    default_charge_level: Mapped[str] = mapped_column(String(40), nullable=False, default="SHIPMENT", server_default="SHIPMENT")
    default_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    container_house_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    house_item_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    final_posting_level: Mapped[str | None] = mapped_column(String(30))
    default_quantity_uom: Mapped[str | None] = mapped_column(String(30))
    allocation_override_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="OVERRIDE_PROFILE",
        server_default="OVERRIDE_PROFILE",
    )
    override_allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    override_allocation_profile_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("charge_allocation_profile_version.id")
    )
    override_charge_level: Mapped[str | None] = mapped_column(String(40))
    override_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    override_container_house_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    override_house_item_allocation_basis: Mapped[str | None] = mapped_column(String(40))
    override_final_posting_level: Mapped[str | None] = mapped_column(String(30))
    override_quantity_uom: Mapped[str | None] = mapped_column(String(30))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    component: Mapped[ChargeComponentRow] = relationship(back_populates="aliases")

    __table_args__ = (
        CheckConstraint(
            "allocation_override_mode in ('INHERIT_PROFILE', 'OVERRIDE_PROFILE', 'NO_ALLOCATION')",
            name="ck_charge_component_alias_override_mode",
        ),
        UniqueConstraint(
            "document_kind",
            "template_key",
            "source_section",
            "normalized_label",
            "customer_id",
            "forwarder_id",
            "transport_mode",
            name="uq_charge_component_alias_scope_label",
        ),
        Index(
            "ix_charge_component_alias_lookup",
            "document_kind",
            "template_key",
            "normalized_label",
            "customer_id",
            "forwarder_id",
            "transport_mode",
        ),
        Index("ix_charge_component_alias_component", "charge_component_id"),
    )


class ChargeAllocationProfileRow(TimestampMixin, Base):
    __tablename__ = "charge_allocation_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    profile_name: Mapped[str] = mapped_column(String(180), nullable=False)
    published_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))

    __table_args__ = (
        Index("ix_charge_allocation_profile_code", "profile_code"),
    )


class ChargeAllocationProfileVersionRow(TimestampMixin, Base):
    __tablename__ = "charge_allocation_profile_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("charge_allocation_profile.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    source_level: Mapped[str] = mapped_column(String(30), nullable=False)
    source_to_house_driver: Mapped[str | None] = mapped_column(String(40))
    house_to_item_driver: Mapped[str | None] = mapped_column(String(40))
    final_posting_level: Mapped[str] = mapped_column(String(30), nullable=False)
    default_quantity_uom: Mapped[str | None] = mapped_column(String(30))
    settings_json: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("profile_id", "version_number", name="uq_charge_allocation_profile_version_number"),
        CheckConstraint(
            "status in ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_charge_allocation_profile_version_status",
        ),
        CheckConstraint(
            "source_level in ('SHIPMENT', 'CONTAINER', 'HOUSE')",
            name="ck_charge_allocation_profile_version_source_level",
        ),
        CheckConstraint(
            "final_posting_level in ('HOUSE', 'PO_SCHEDULE_LINE')",
            name="ck_charge_allocation_profile_version_final_posting_level",
        ),
        Index("ix_charge_allocation_profile_version_profile", "profile_id"),
    )


class ChargeBusinessDateProfileRow(TimestampMixin, Base):
    __tablename__ = "charge_business_date_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    profile_name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    published_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_business_date_profile_version.id"))

    versions: Mapped[list["ChargeBusinessDateProfileVersionRow"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        foreign_keys="ChargeBusinessDateProfileVersionRow.profile_id",
    )
    assignments: Mapped[list["ChargeBusinessDateProfileAssignmentRow"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_charge_business_date_profile_code", "profile_code"),)


class ChargeBusinessDateProfileVersionRow(TimestampMixin, Base):
    __tablename__ = "charge_business_date_profile_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("charge_business_date_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    notes: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[ChargeBusinessDateProfileRow] = relationship(
        back_populates="versions",
        foreign_keys=[profile_id],
    )
    steps: Mapped[list["ChargeBusinessDateProfileStepRow"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "version_number", name="uq_charge_business_date_profile_version_number"),
        CheckConstraint("status in ('DRAFT', 'PUBLISHED', 'RETIRED')", name="ck_charge_business_date_profile_version_status"),
        Index("ix_charge_business_date_profile_version_profile", "profile_id"),
    )


class ChargeBusinessDateProfileStepRow(Base):
    __tablename__ = "charge_business_date_profile_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("charge_business_date_profile_version.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date_key: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    version: Mapped[ChargeBusinessDateProfileVersionRow] = relationship(back_populates="steps")

    __table_args__ = (
        UniqueConstraint("version_id", "step_number", name="uq_charge_business_date_profile_step_number"),
        Index("ix_charge_business_date_profile_step_version", "version_id"),
    )


class ChargeBusinessDateProfileAssignmentRow(TimestampMixin, Base):
    __tablename__ = "charge_business_date_profile_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("charge_business_date_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_id: Mapped[int | None] = mapped_column(Integer)
    owner_scope_key: Mapped[str] = mapped_column(String(80), nullable=False)
    shipment_scope: Mapped[str] = mapped_column(String(30), nullable=False)
    business_purpose: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="EXCHANGE_RATE_DATE",
        server_default="EXCHANGE_RATE_DATE",
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    profile: Mapped[ChargeBusinessDateProfileRow] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint(
            "owner_scope_key",
            "shipment_scope",
            "business_purpose",
            name="uq_charge_business_date_profile_assignment_effective_scope",
        ),
        CheckConstraint(
            "scope_type in ('GLOBAL', 'COMPANY', 'CUSTOMER', 'VENDOR', 'FORWARDER', 'CARRIER')",
            name="ck_charge_business_date_profile_assignment_scope_type",
        ),
        CheckConstraint(
            "(scope_type = 'GLOBAL' and scope_id is null) or (scope_type <> 'GLOBAL' and scope_id is not null)",
            name="ck_charge_business_date_profile_assignment_scope_id",
        ),
        CheckConstraint(
            "length(owner_scope_key) > 0",
            name="ck_charge_business_date_profile_assignment_owner_scope_key",
        ),
        CheckConstraint(
            "shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
            name="ck_charge_business_date_profile_assignment_shipment_scope",
        ),
        CheckConstraint(
            "business_purpose in ('EXCHANGE_RATE_DATE')",
            name="ck_charge_business_date_profile_assignment_business_purpose",
        ),
        Index("ix_charge_business_date_profile_assignment_profile", "profile_id"),
        Index(
            "ix_charge_business_date_profile_assignment_scope",
            "scope_type",
            "scope_id",
            "shipment_scope",
            "business_purpose",
            "priority",
        ),
    )


class ChargeRateBookRow(TimestampMixin, Base):
    __tablename__ = "charge_rate_book"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_book_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    rate_book_name: Mapped[str] = mapped_column(String(180), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    entries: Mapped[list["ChargeRateBookEntryRow"]] = relationship(
        back_populates="rate_book",
        cascade="all, delete-orphan",
    )


class ChargeRateBookEntryRow(Base):
    __tablename__ = "charge_rate_book_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_book_id: Mapped[int] = mapped_column(ForeignKey("charge_rate_book.id", ondelete="CASCADE"), nullable=False)
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    rate_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    basis: Mapped[str] = mapped_column(String(40), nullable=False, default="SHIPMENT")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    allocation_profile_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))
    origin_code: Mapped[str | None] = mapped_column(String(40))
    destination_code: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str | None] = mapped_column(String(40))
    equipment_type: Mapped[str | None] = mapped_column(String(60))
    commodity_code: Mapped[str | None] = mapped_column(String(80))
    service_level: Mapped[str | None] = mapped_column(String(80))
    scale_from: Mapped[object | None] = mapped_column(Numeric(18, 6))
    scale_to: Mapped[object | None] = mapped_column(Numeric(18, 6))
    minimum_amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    maximum_amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    validity_from: Mapped[object | None] = mapped_column(Date)
    validity_to: Mapped[object | None] = mapped_column(Date)
    attributes_json: Mapped[dict | None] = mapped_column(JSON)

    rate_book: Mapped[ChargeRateBookRow] = relationship(back_populates="entries")
    component: Mapped[ChargeComponentRow] = relationship()

    __table_args__ = (
        Index("ix_charge_rate_book_entry_book_component", "rate_book_id", "charge_component_id"),
        Index("ix_charge_rate_book_entry_lane", "origin_code", "destination_code", "mode"),
    )


class ChargeRateContractRow(TimestampMixin, Base):
    __tablename__ = "charge_rate_contract"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    contract_name: Mapped[str] = mapped_column(String(180), nullable=False)
    contract_role: Mapped[str] = mapped_column(String(20), nullable=False)
    payer_party_ref: Mapped[str | None] = mapped_column(String(120))
    payee_party_ref: Mapped[str | None] = mapped_column(String(120))
    party_role_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")
    partner_id: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int | None] = mapped_column(Integer)
    vendor_id: Mapped[int | None] = mapped_column(Integer)
    forwarder_id: Mapped[int | None] = mapped_column(Integer)
    carrier_id: Mapped[int | None] = mapped_column(Integer)
    company_id: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    valid_from: Mapped[object | None] = mapped_column(Date)
    valid_to: Mapped[object | None] = mapped_column(Date)
    default_rate_book_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_book.id"))
    default_calculation_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("charge_calculation_template.id")
    )

    lines: Mapped[list["ChargeContractLineRow"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("contract_role in ('PAYER', 'PAYEE')", name="ck_charge_rate_contract_role"),
        Index("ix_charge_rate_contract_scope", "company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"),
    )


class ChargeContractLineRow(Base):
    __tablename__ = "charge_contract_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("charge_rate_contract.id", ondelete="CASCADE"), nullable=False)
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    rate_book_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_book.id"))
    calculation_template_id: Mapped[int | None] = mapped_column(Integer)
    allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    allocation_profile_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))
    origin_code: Mapped[str | None] = mapped_column(String(40))
    destination_code: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str | None] = mapped_column(String(40))
    equipment_type: Mapped[str | None] = mapped_column(String(60))
    commodity_code: Mapped[str | None] = mapped_column(String(80))
    service_level: Mapped[str | None] = mapped_column(String(80))
    valid_from: Mapped[object | None] = mapped_column(Date)
    valid_to: Mapped[object | None] = mapped_column(Date)
    attributes_json: Mapped[dict | None] = mapped_column(JSON)

    contract: Mapped[ChargeRateContractRow] = relationship(back_populates="lines")
    component: Mapped[ChargeComponentRow] = relationship()
    rate_book: Mapped[ChargeRateBookRow | None] = relationship()

    __table_args__ = (
        Index("ix_charge_contract_line_contract_component", "contract_id", "charge_component_id"),
        Index("ix_charge_contract_line_lane", "origin_code", "destination_code", "mode"),
    )


class ChargeCalculationTemplateRow(TimestampMixin, Base):
    __tablename__ = "charge_calculation_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    template_name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    steps: Mapped[list["ChargeCalculationTemplateStepRow"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )


class ChargeCalculationTemplateStepRow(Base):
    __tablename__ = "charge_calculation_template_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("charge_calculation_template.id", ondelete="CASCADE"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    relationship_role: Mapped[str] = mapped_column(String(20), nullable=False, default="BOTH", server_default="BOTH")
    rate_book_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_book.id"))
    precondition_json: Mapped[dict | None] = mapped_column(JSON)
    subtotal_group: Mapped[str | None] = mapped_column(String(80))
    is_statistical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    template: Mapped[ChargeCalculationTemplateRow] = relationship(back_populates="steps")
    component: Mapped[ChargeComponentRow] = relationship()
    rate_book: Mapped[ChargeRateBookRow | None] = relationship()

    __table_args__ = (
        UniqueConstraint("template_id", "sequence_no", name="uq_charge_calc_template_step_sequence"),
        CheckConstraint(
            "relationship_role in ('PAYER', 'PAYEE', 'BOTH')",
            name="ck_charge_calc_template_step_relationship_role",
        ),
    )


class ChargeQuoteRequestRow(TimestampMixin, Base):
    __tablename__ = "charge_quote_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_object_type: Mapped[str] = mapped_column(String(60), nullable=False, default="MANUAL", server_default="MANUAL")
    source_object_id: Mapped[str | None] = mapped_column(String(120))
    company_id: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int | None] = mapped_column(Integer)
    vendor_id: Mapped[int | None] = mapped_column(Integer)
    forwarder_id: Mapped[int | None] = mapped_column(Integer)
    carrier_id: Mapped[int | None] = mapped_column(Integer)
    origin_code: Mapped[str | None] = mapped_column(String(40))
    destination_code: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str | None] = mapped_column(String(40))
    equipment_type: Mapped[str | None] = mapped_column(String(60))
    commodity_code: Mapped[str | None] = mapped_column(String(80))
    service_level: Mapped[str | None] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    quantity: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=1)
    gross_weight: Mapped[object | None] = mapped_column(Numeric(18, 6))
    gross_volume_cbm: Mapped[object | None] = mapped_column(Numeric(18, 6))
    container_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    package_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    package_type: Mapped[str | None] = mapped_column(String(60))
    requested_service_date: Mapped[object | None] = mapped_column(Date)
    valid_from: Mapped[object | None] = mapped_column(Date)
    valid_to: Mapped[object | None] = mapped_column(Date)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", server_default="DRAFT")
    quotation_policy_snapshot: Mapped[str] = mapped_column(String(30), nullable=False, default="OPTIONAL", server_default="OPTIONAL")
    awarded_option_id: Mapped[int | None] = mapped_column(Integer)
    margin_rules_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    options: Mapped[list["ChargeQuoteOptionRow"]] = relationship(
        back_populates="quote_request",
        cascade="all, delete-orphan",
        foreign_keys="ChargeQuoteOptionRow.quote_request_id",
    )
    offers: Mapped[list["ChargeQuoteOfferRow"]] = relationship(
        back_populates="quote_request",
        cascade="all, delete-orphan",
        foreign_keys="ChargeQuoteOfferRow.quote_request_id",
    )

    __table_args__ = (
        Index("ix_charge_quote_request_scope", "company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"),
        Index("ix_charge_quote_request_source", "source_object_type", "source_object_id"),
    )


class ChargeQuoteOfferRow(TimestampMixin, Base):
    __tablename__ = "charge_quote_offer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_request_id: Mapped[int] = mapped_column(
        ForeignKey("charge_quote_request.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_party_ref: Mapped[str | None] = mapped_column(String(160))
    provider_role_ref: Mapped[str | None] = mapped_column(String(120))
    offer_number: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL", server_default="MANUAL")
    amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    is_sealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    transit_time_days: Mapped[int | None] = mapped_column(Integer)
    service_level: Mapped[str | None] = mapped_column(String(80))
    performance_score: Mapped[object | None] = mapped_column(Numeric(18, 6))
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUBMITTED", server_default="SUBMITTED")
    notes: Mapped[str | None] = mapped_column(Text)

    quote_request: Mapped[ChargeQuoteRequestRow] = relationship(
        back_populates="offers",
        foreign_keys=[quote_request_id],
    )
    options: Mapped[list["ChargeQuoteOptionRow"]] = relationship(
        back_populates="source_offer",
        foreign_keys="ChargeQuoteOptionRow.source_offer_id",
    )

    __table_args__ = (
        Index("ix_charge_quote_offer_quote", "quote_request_id"),
        Index("ix_charge_quote_offer_provider", "provider_party_ref", "provider_role_ref"),
        Index("ix_charge_quote_offer_status", "status"),
    )


class ChargeQuoteOptionRow(Base):
    __tablename__ = "charge_quote_option"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_request_id: Mapped[int] = mapped_column(ForeignKey("charge_quote_request.id", ondelete="CASCADE"), nullable=False)
    option_name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_offer_id: Mapped[int | None] = mapped_column(ForeignKey("charge_quote_offer.id"))
    payer_contract_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_contract.id"))
    payee_contract_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_contract.id"))
    payer_total_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    payee_total_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    margin_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    margin_percent: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    transit_time_days: Mapped[int | None] = mapped_column(Integer)
    service_level_score: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    policy_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    rank: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[object | None] = mapped_column(Numeric(18, 6))
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    quote_request: Mapped[ChargeQuoteRequestRow] = relationship(
        back_populates="options",
        foreign_keys=[quote_request_id],
    )
    source_offer: Mapped[ChargeQuoteOfferRow | None] = relationship(
        back_populates="options",
        foreign_keys=[source_offer_id],
    )
    lines: Mapped[list["ChargeQuoteOptionLineRow"]] = relationship(
        back_populates="quote_option",
        cascade="all, delete-orphan",
    )


class ChargeQuoteOptionLineRow(Base):
    __tablename__ = "charge_quote_option_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_option_id: Mapped[int] = mapped_column(ForeignKey("charge_quote_option.id", ondelete="CASCADE"), nullable=False)
    relationship_role: Mapped[str] = mapped_column(String(20), nullable=False)
    payer_party_ref: Mapped[str | None] = mapped_column(String(120))
    payee_party_ref: Mapped[str | None] = mapped_column(String(120))
    party_role_ref: Mapped[str | None] = mapped_column(String(120))
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    basis: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity_uom: Mapped[str | None] = mapped_column(String(30))
    allocation_basis: Mapped[str | None] = mapped_column(String(40))
    allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    allocation_profile_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))
    pinned_allocation_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    effective_allocation_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    source_contract_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_contract.id"))
    source_rate_book_id: Mapped[int | None] = mapped_column(ForeignKey("charge_rate_book.id"))
    is_margin_line: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    quote_option: Mapped[ChargeQuoteOptionRow] = relationship(back_populates="lines")
    component: Mapped[ChargeComponentRow] = relationship()

    __table_args__ = (
        CheckConstraint("relationship_role in ('PAYER', 'PAYEE')", name="ck_charge_quote_option_line_role"),
    )


class ChargeDocumentRow(TimestampMixin, Base):
    __tablename__ = "charge_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    quote_request_id: Mapped[int | None] = mapped_column(ForeignKey("charge_quote_request.id"))
    quote_option_id: Mapped[int | None] = mapped_column(ForeignKey("charge_quote_option.id"))
    quotation_policy_snapshot: Mapped[str] = mapped_column(String(30), nullable=False, default="OPTIONAL", server_default="OPTIONAL")
    source_object_type: Mapped[str] = mapped_column(String(60), nullable=False, default="MANUAL", server_default="MANUAL")
    source_object_id: Mapped[str | None] = mapped_column(String(120))
    document_scope_level: Mapped[str | None] = mapped_column(String(30))
    shipment_scope: Mapped[str | None] = mapped_column(String(30))
    document_date: Mapped[object | None] = mapped_column(Date)
    source_reference_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    company_id: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int | None] = mapped_column(Integer)
    vendor_id: Mapped[int | None] = mapped_column(Integer)
    forwarder_id: Mapped[int | None] = mapped_column(Integer)
    carrier_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ESTIMATED", server_default="ESTIMATED")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    payer_total_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    payee_total_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    margin_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    approved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    exported_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    reversed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    reversal_reason: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list["ChargeLineRow"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "shipment_scope is null or shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
            name="ck_charge_document_shipment_scope",
        ),
        Index("ix_charge_document_scope", "company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"),
        Index("ix_charge_document_source", "source_object_type", "source_object_id"),
    )


class ChargeQuoteCommitmentRow(TimestampMixin, Base):
    __tablename__ = "charge_quote_commitment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commitment_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    quote_request_id: Mapped[int] = mapped_column(ForeignKey("charge_quote_request.id", ondelete="CASCADE"), nullable=False)
    quote_option_id: Mapped[int] = mapped_column(ForeignKey("charge_quote_option.id"), nullable=False, unique=True)
    charge_document_id: Mapped[int] = mapped_column(ForeignKey("charge_document.id"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int | None] = mapped_column(Integer)
    vendor_id: Mapped[int | None] = mapped_column(Integer)
    forwarder_id: Mapped[int | None] = mapped_column(Integer)
    carrier_id: Mapped[int | None] = mapped_column(Integer)
    origin_code: Mapped[str | None] = mapped_column(String(40))
    destination_code: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str | None] = mapped_column(String(40))
    equipment_type: Mapped[str | None] = mapped_column(String(60))
    commodity_code: Mapped[str | None] = mapped_column(String(80))
    service_level: Mapped[str | None] = mapped_column(String(80))
    package_type: Mapped[str | None] = mapped_column(String(60))
    requested_service_date: Mapped[object | None] = mapped_column(Date)
    valid_from: Mapped[object | None] = mapped_column(Date)
    valid_to: Mapped[object | None] = mapped_column(Date)
    committed_container_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    consumed_container_count: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    committed_package_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    consumed_package_count: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    committed_chargeable_weight: Mapped[object | None] = mapped_column(Numeric(18, 6))
    consumed_chargeable_weight: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    committed_quantity: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=1)
    consumed_quantity: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    committed_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    consumed_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", server_default="ACTIVE")

    __table_args__ = (
        Index("ix_charge_quote_commitment_scope", "company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"),
        Index("ix_charge_quote_commitment_lane", "origin_code", "destination_code", "mode"),
        Index("ix_charge_quote_commitment_status_validity", "status", "valid_to"),
    )


class ChargeQuoteCommitmentConsumptionRow(TimestampMixin, Base):
    __tablename__ = "charge_quote_commitment_consumption"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commitment_id: Mapped[int] = mapped_column(ForeignKey("charge_quote_commitment.id", ondelete="CASCADE"), nullable=False)
    source_object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_object_id: Mapped[str | None] = mapped_column(String(120))
    reference_number: Mapped[str | None] = mapped_column(String(120))
    container_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    package_count: Mapped[object | None] = mapped_column(Numeric(18, 6))
    chargeable_weight: Mapped[object | None] = mapped_column(Numeric(18, 6))
    quantity: Mapped[object | None] = mapped_column(Numeric(18, 6))
    amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    consumed_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", server_default="ACTIVE")
    reversed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    reversal_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_charge_quote_commitment_consumption_commitment", "commitment_id"),
        Index("ix_charge_quote_commitment_consumption_source", "source_object_type", "source_object_id"),
        Index("ix_charge_quote_commitment_consumption_status", "status"),
    )


class ChargeLineRow(Base):
    __tablename__ = "charge_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    charge_document_id: Mapped[int] = mapped_column(ForeignKey("charge_document.id", ondelete="CASCADE"), nullable=False)
    relationship_role: Mapped[str] = mapped_column(String(20), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer)
    parent_line_id: Mapped[int | None] = mapped_column(ForeignKey("charge_line.id", ondelete="SET NULL"))
    line_role: Mapped[str] = mapped_column(String(20), nullable=False, default="POSTING", server_default="POSTING")
    target_level: Mapped[str | None] = mapped_column(String(30))
    target_object_type: Mapped[str | None] = mapped_column(String(80))
    target_object_id: Mapped[str | None] = mapped_column(String(120))
    payer_party_ref: Mapped[str | None] = mapped_column(String(120))
    payee_party_ref: Mapped[str | None] = mapped_column(String(120))
    party_role_ref: Mapped[str | None] = mapped_column(String(120))
    charge_component_id: Mapped[int] = mapped_column(ForeignKey("charge_component.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    charge_date: Mapped[object | None] = mapped_column(Date)
    charge_date_basis: Mapped[str | None] = mapped_column(String(40))
    expected_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    actual_amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    approved_amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity_uom: Mapped[str | None] = mapped_column(String(30))
    source_currency: Mapped[str | None] = mapped_column(String(3))
    source_amount: Mapped[object | None] = mapped_column(Numeric(18, 6))
    exchange_rate: Mapped[object | None] = mapped_column(Numeric(18, 8))
    exchange_rate_date: Mapped[object | None] = mapped_column(Date)
    fx_rate_id: Mapped[int | None] = mapped_column(ForeignKey("charge_fx_rate.id"))
    exchange_rate_source_code: Mapped[str | None] = mapped_column(String(60))
    exchange_rate_type: Mapped[str | None] = mapped_column(String(20))
    exchange_rate_method: Mapped[str | None] = mapped_column(String(60))
    allocation_profile_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile.id"))
    allocation_profile_version_id: Mapped[int | None] = mapped_column(ForeignKey("charge_allocation_profile_version.id"))
    pinned_allocation_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    effective_allocation_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    charge_text_snapshot: Mapped[str | None] = mapped_column(String(255))
    allocation_basis: Mapped[str | None] = mapped_column(String(40))
    allocation_ratio: Mapped[object | None] = mapped_column(Numeric(18, 8))
    allocation_driver_value: Mapped[object | None] = mapped_column(Numeric(18, 6))
    target_reference_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    calculation_audit_json: Mapped[dict | None] = mapped_column(JSON)
    basis: Mapped[str] = mapped_column(String(40), nullable=False)
    source_quote_option_line_id: Mapped[int | None] = mapped_column(ForeignKey("charge_quote_option_line.id"))

    document: Mapped[ChargeDocumentRow] = relationship(back_populates="lines")
    component: Mapped[ChargeComponentRow] = relationship()
    parent_line: Mapped["ChargeLineRow | None"] = relationship(
        "ChargeLineRow",
        remote_side=[id],
        back_populates="child_lines",
    )
    child_lines: Mapped[list["ChargeLineRow"]] = relationship(
        "ChargeLineRow",
        back_populates="parent_line",
    )

    __table_args__ = (
        CheckConstraint("relationship_role in ('PAYER', 'PAYEE')", name="ck_charge_line_role"),
        CheckConstraint("line_role in ('CALCULATION', 'POSTING')", name="ck_charge_line_line_role"),
        CheckConstraint(
            "charge_date_basis is null or charge_date_basis in ('DOCUMENT_DATE', 'SHIPMENT_DEPARTURE_DATE', 'SHIPMENT_ARRIVAL_DATE', 'HOUSE_BILL_ISSUE_DATE', 'MANUAL')",
            name="ck_charge_line_charge_date_basis",
        ),
        CheckConstraint(
            "exchange_rate_type is null or exchange_rate_type in ('MID', 'BUY', 'SELL', 'CUSTOM')",
            name="ck_charge_line_exchange_rate_type",
        ),
        CheckConstraint(
            "target_level is null or target_level in ('HEADER', 'ITEM', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE')",
            name="ck_charge_line_target_level",
        ),
        UniqueConstraint("charge_document_id", "line_number", name="uq_charge_line_document_line_number"),
        Index("ix_charge_line_document_line_number", "charge_document_id", "line_number"),
        Index("ix_charge_line_target", "target_level", "target_object_type", "target_object_id"),
    )


class ChargeInvoiceRow(TimestampMixin, Base):
    __tablename__ = "charge_invoice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    charge_document_id: Mapped[int] = mapped_column(ForeignKey("charge_document.id", ondelete="CASCADE"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(120), nullable=False)
    invoice_type: Mapped[str] = mapped_column(String(30), nullable=False)
    invoice_date: Mapped[object | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    total_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CAPTURED", server_default="CAPTURED")
    lines_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("charge_document_id", "invoice_number", name="uq_charge_invoice_document_number"),
    )


class ChargeMatchResultRow(Base):
    __tablename__ = "charge_match_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("charge_invoice.id", ondelete="CASCADE"), nullable=False)
    charge_document_id: Mapped[int] = mapped_column(ForeignKey("charge_document.id", ondelete="CASCADE"), nullable=False)
    charge_line_id: Mapped[int | None] = mapped_column(ForeignKey("charge_line.id"))
    charge_component_id: Mapped[int | None] = mapped_column(ForeignKey("charge_component.id"))
    expected_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    invoice_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    variance_amount: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    variance_percent: Mapped[object] = mapped_column(Numeric(18, 6), nullable=False)
    match_status: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_charge_match_result_invoice", "invoice_id"),
        Index("ix_charge_match_result_document", "charge_document_id"),
    )


class ChargeExportBatchRow(TimestampMixin, Base):
    __tablename__ = "charge_export_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    export_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    charge_document_id: Mapped[int] = mapped_column(ForeignKey("charge_document.id"), nullable=False)
    target_system: Mapped[str] = mapped_column(String(80), nullable=False, default="INTERNAL_LEDGER")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="POSTED")
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
