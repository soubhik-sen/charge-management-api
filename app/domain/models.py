from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ChargeComponent(ApiModel):
    id: int
    component_code: str
    component_name: str
    category: str
    default_party_role: Literal["PAYER", "PAYEE", "BOTH"]
    charge_context: str
    calculation_basis: str
    charge_date_basis: Literal[
        "DOCUMENT_DATE",
        "SHIPMENT_DEPARTURE_DATE",
        "SHIPMENT_ARRIVAL_DATE",
        "HOUSE_BILL_ISSUE_DATE",
        "MANUAL",
    ] = "DOCUMENT_DATE"
    business_date_policy_mode: Literal["LEGACY_BASIS", "INHERIT_PROFILE", "PROFILE_OVERRIDE"] = "LEGACY_BASIS"
    business_date_profile_id: int | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    is_tax: bool = False
    is_active: bool = True


class ChargeComponentPayload(ApiModel):
    component_code: str
    component_name: str
    category: str = "ACCESSORIAL"
    default_party_role: Literal["PAYER", "PAYEE", "BOTH"] = "BOTH"
    charge_context: str = "TRANSPORT"
    calculation_basis: str = "FLAT"
    charge_date_basis: Literal[
        "DOCUMENT_DATE",
        "SHIPMENT_DEPARTURE_DATE",
        "SHIPMENT_ARRIVAL_DATE",
        "HOUSE_BILL_ISSUE_DATE",
        "MANUAL",
    ] = "DOCUMENT_DATE"
    business_date_policy_mode: Literal["LEGACY_BASIS", "INHERIT_PROFILE", "PROFILE_OVERRIDE"] = "LEGACY_BASIS"
    business_date_profile_id: int | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    is_tax: bool = False
    is_active: bool = True


class ChargeComponentListResponse(ApiModel):
    items: list[ChargeComponent]
    total: int
    limit: int
    offset: int


class ChargeComponentAliasPayload(ApiModel):
    document_kind: str = "CHARGE_PROPOSAL"
    template_key: str | None = None
    source_section: str | None = None
    customer_id: int | None = None
    forwarder_id: int | None = None
    transport_mode: str | None = None
    raw_label: str
    charge_component_id: int
    default_calculation_basis: str = "DOCUMENT"
    default_charge_level: str = "SHIPMENT"
    default_allocation_basis: str | None = None
    container_house_allocation_basis: str | None = None
    house_item_allocation_basis: str | None = None
    final_posting_level: Literal["HOUSE", "PO_SCHEDULE_LINE"] | None = "PO_SCHEDULE_LINE"
    default_quantity_uom: str | None = None
    allocation_override_mode: Literal["INHERIT_PROFILE", "OVERRIDE_PROFILE", "NO_ALLOCATION"] = "OVERRIDE_PROFILE"
    override_allocation_profile_id: int | None = None
    override_allocation_profile_version_id: int | None = None
    override_charge_level: str | None = None
    override_allocation_basis: str | None = None
    override_container_house_allocation_basis: str | None = None
    override_house_item_allocation_basis: str | None = None
    override_final_posting_level: Literal["HOUSE", "PO_SCHEDULE_LINE"] | None = None
    override_quantity_uom: str | None = None
    priority: int = 100
    is_active: bool = True


class ChargeComponentAlias(ChargeComponentAliasPayload):
    id: int
    normalized_label: str
    component_code: str
    component_name: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeComponentAliasListResponse(ApiModel):
    items: list[ChargeComponentAlias]
    total: int
    limit: int
    offset: int


class ChargeAllocationProfileVersionPayload(ApiModel):
    source_level: Literal["SHIPMENT", "CONTAINER", "HOUSE"]
    source_to_house_driver: str | None = None
    house_to_item_driver: str | None = None
    final_posting_level: Literal["HOUSE", "PO_SCHEDULE_LINE"]
    default_quantity_uom: str | None = None
    settings_json: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class ChargeAllocationProfileVersionCreate(ChargeAllocationProfileVersionPayload):
    pass


class ChargeAllocationProfileCreate(ApiModel):
    profile_code: str
    profile_name: str
    initial_version: ChargeAllocationProfileVersionCreate


class ChargeAllocationProfileUpdate(ApiModel):
    profile_code: str
    profile_name: str


class ChargeAllocationProfileVersion(ChargeAllocationProfileVersionPayload):
    id: int
    profile_id: int
    version_number: int
    status: Literal["DRAFT", "PUBLISHED", "RETIRED"] = "DRAFT"
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeAllocationProfile(ApiModel):
    id: int
    profile_code: str
    profile_name: str
    published_version_id: int | None = None
    published_version_number: int | None = None
    versions: list[ChargeAllocationProfileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeAllocationProfileListResponse(ApiModel):
    items: list[ChargeAllocationProfile]
    total: int
    limit: int
    offset: int


class BusinessDateProfileStepPayload(ApiModel):
    step_number: int
    date_key: str
    notes: str | None = None


class BusinessDateProfileStepCreate(BusinessDateProfileStepPayload):
    pass


class BusinessDateProfileVersionPayload(ApiModel):
    steps: list[BusinessDateProfileStepCreate] = Field(default_factory=list)
    notes: str | None = None


class BusinessDateProfileVersionCreate(BusinessDateProfileVersionPayload):
    pass


class BusinessDateProfileCreate(ApiModel):
    profile_code: str
    profile_name: str
    description: str | None = None
    initial_version: BusinessDateProfileVersionCreate


class BusinessDateProfileUpdate(ApiModel):
    profile_code: str
    profile_name: str
    description: str | None = None


class BusinessDateProfileStep(BusinessDateProfileStepPayload):
    id: int
    version_id: int


class BusinessDateProfileVersion(BusinessDateProfileVersionPayload):
    id: int
    profile_id: int
    version_number: int
    status: Literal["DRAFT", "PUBLISHED", "RETIRED"] = "DRAFT"
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    steps: list[BusinessDateProfileStep] = Field(default_factory=list)


class BusinessDateProfile(ApiModel):
    id: int
    profile_code: str
    profile_name: str
    description: str | None = None
    published_version_id: int | None = None
    published_version_number: int | None = None
    versions: list[BusinessDateProfileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BusinessDateProfileListResponse(ApiModel):
    items: list[BusinessDateProfile]
    total: int
    limit: int
    offset: int


class BusinessDateProfileAssignmentPayload(ApiModel):
    scope_type: Literal["GLOBAL", "COMPANY", "CUSTOMER", "VENDOR", "FORWARDER", "CARRIER"]
    scope_id: int | None = None
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE"]
    business_purpose: Literal["EXCHANGE_RATE_DATE"] = "EXCHANGE_RATE_DATE"
    priority: int = 100
    is_active: bool = True


class BusinessDateProfileAssignmentCreate(BusinessDateProfileAssignmentPayload):
    pass


class BusinessDateProfileAssignment(BusinessDateProfileAssignmentPayload):
    id: int
    profile_id: int
    owner_scope_key: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BusinessDateProfileAssignmentListResponse(ApiModel):
    items: list[BusinessDateProfileAssignment]
    total: int
    limit: int
    offset: int


class FxRateSourcePayload(ApiModel):
    source_code: str
    source_name: str
    provider_url: str | None = None
    timezone: str = "UTC"
    priority: int = 100
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FxRateSource(FxRateSourcePayload):
    id: int
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class FxRateSourceListResponse(ApiModel):
    items: list[FxRateSource]
    total: int
    limit: int
    offset: int


class FxRatePayload(ApiModel):
    source_id: int
    source_currency: str
    target_currency: str
    rate_date: date
    rate: Decimal
    rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] = "MID"
    conversion_method: str = "DIRECT"
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FxRate(FxRatePayload):
    id: int
    source_code: str
    source_name: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class FxRateListResponse(ApiModel):
    items: list[FxRate]
    total: int
    limit: int
    offset: int


class FxRateResolveRequest(ApiModel):
    source_currency: str
    target_currency: str
    rate_date: date
    amount: Decimal = Decimal("1")
    source_id: int | None = None
    source_code: str | None = None
    rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] = "MID"
    conversion_method: str = "DIRECT"
    allow_inverse: bool = True
    allow_prior_date: bool = True


class FxRateResolution(ApiModel):
    rate: FxRate | None = None
    effective_rate: Decimal
    converted_amount: Decimal
    requested_rate_date: date
    selected_rate_date: date | None = None
    inverse_applied: bool = False


class ChargeReferenceData(ApiModel):
    contract_roles: list[str] = ["PAYER", "PAYEE"]
    contract_statuses: list[str] = ["DRAFT", "RELEASED", "EXPIRED", "BLOCKED"]
    quote_statuses: list[str] = ["DRAFT", "REQUESTED", "RATED", "RANKED", "AWARDED", "EXPIRED", "CANCELLED"]
    document_statuses: list[str] = [
        "ESTIMATED",
        "ACCRUED",
        "ACTUAL",
        "DISPUTED",
        "APPROVED",
        "EXPORTED",
        "REVERSED",
    ]
    relationship_roles: list[str] = ["PAYER", "PAYEE"]
    bases: list[str] = [
        "FLAT",
        "SHIPMENT",
        "WEIGHT",
        "VOLUME",
        "CONTAINER",
        "PACKAGE",
        "DOCUMENT",
        "DAY",
        "PERCENTAGE",
    ]
    modes: list[str] = ["OCEAN", "AIR", "ROAD", "RAIL", "MULTIMODAL"]
    currencies: list[str] = ["USD", "EUR", "INR", "BRL", "GBP"]
    quotation_policies: list[str] = ["REQUIRED", "OPTIONAL", "DIRECT_ONLY"]
    quote_acceptance_modes: list[str] = ["AUTO_ACCEPT", "CUSTOMER_ACCEPTANCE"]
    charge_line_roles: list[str] = ["CALCULATION", "POSTING"]
    charge_target_levels: list[str] = ["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
    allocation_profile_source_levels: list[str] = ["SHIPMENT", "CONTAINER", "HOUSE"]
    allocation_profile_final_posting_levels: list[str] = ["HOUSE", "PO_SCHEDULE_LINE"]
    allocation_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
    allocation_override_modes: list[str] = ["INHERIT_PROFILE", "OVERRIDE_PROFILE", "NO_ALLOCATION"]
    business_date_policy_modes: list[str] = ["LEGACY_BASIS", "INHERIT_PROFILE", "PROFILE_OVERRIDE"]
    business_date_assignment_scope_types: list[str] = [
        "GLOBAL",
        "COMPANY",
        "CUSTOMER",
        "VENDOR",
        "FORWARDER",
        "CARRIER",
    ]
    business_date_shipment_scopes: list[str] = ["OCEAN_HOUSE", "AIR_HOUSE"]
    business_date_purposes: list[str] = ["EXCHANGE_RATE_DATE"]
    business_date_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
    fx_rate_types: list[str] = ["MID", "BUY", "SELL", "CUSTOM"]
    business_date_keys: list[str] = [
        "DOCUMENT_DATE",
        "MANUAL_LINE_DATE",
        "SHIPPED_ON_BOARD_DATE",
        "SHIPMENT_ACTUAL_DEPARTURE_DATE",
        "SHIPMENT_PLANNED_DEPARTURE_DATE",
        "SHIPMENT_ARRIVAL_DATE",
        "HOUSE_BILL_ISSUE_DATE",
        "ACTUAL_FLIGHT_DEPARTURE_DATE",
        "AWB_EXECUTION_DATE",
        "ESTIMATED_FLIGHT_DEPARTURE_DATE",
    ]


class ChargeManagementSettings(ApiModel):
    quotation_policy: Literal["REQUIRED", "OPTIONAL", "DIRECT_ONLY"] = "OPTIONAL"
    supported_quotation_policies: list[str] = ["REQUIRED", "OPTIONAL", "DIRECT_ONLY"]
    quote_acceptance_mode: Literal["AUTO_ACCEPT", "CUSTOMER_ACCEPTANCE"] = "CUSTOMER_ACCEPTANCE"
    supported_quote_acceptance_modes: list[str] = ["AUTO_ACCEPT", "CUSTOMER_ACCEPTANCE"]
    provider_cost_layer_enabled: bool = False


class ChargeInitializationData(ApiModel):
    components: list[ChargeComponent]
    reference_data: ChargeReferenceData = Field(default_factory=ChargeReferenceData)
    settings: ChargeManagementSettings = Field(default_factory=ChargeManagementSettings)


class RateBookEntryPayload(ApiModel):
    charge_component_code: str
    rate_amount: Decimal
    basis: str = "SHIPMENT"
    currency: str = "USD"
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    scale_from: Decimal | None = None
    scale_to: Decimal | None = None
    minimum_amount: Decimal | None = None
    maximum_amount: Decimal | None = None
    validity_from: date | None = None
    validity_to: date | None = None


class RateBookPayload(ApiModel):
    rate_book_code: str
    rate_book_name: str
    currency: str = "USD"
    entries: list[RateBookEntryPayload] = Field(default_factory=list)


class RateBookEntry(RateBookEntryPayload):
    id: int
    rate_book_id: int


class RateBook(ApiModel):
    id: int
    rate_book_code: str
    rate_book_name: str
    currency: str = "USD"
    entries: list[RateBookEntry] = Field(default_factory=list)
    is_active: bool = True


class RateBookListResponse(ApiModel):
    items: list[RateBook]
    total: int
    limit: int
    offset: int


class RateBookWorkspace(ApiModel):
    rate_book: RateBook
    entries: list[RateBookEntry] = Field(default_factory=list)


class CalculationTemplateStepPayload(ApiModel):
    step_number: int
    charge_component_code: str
    relationship_role: Literal["PAYER", "PAYEE", "BOTH"] = "BOTH"
    subtotal_key: str | None = None
    is_statistical: bool = False
    precondition_key: str | None = None
    rate_book_id: int | None = None


class CalculationTemplatePayload(ApiModel):
    template_code: str
    template_name: str
    description: str | None = None
    status: str = "DRAFT"
    is_active: bool = True
    steps: list[CalculationTemplateStepPayload] = Field(default_factory=list)


class CalculationTemplateStep(CalculationTemplateStepPayload):
    id: int
    template_id: int
    rate_book_code: str | None = None
    rate_book_name: str | None = None


class CalculationTemplate(CalculationTemplatePayload):
    id: int
    steps: list[CalculationTemplateStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CalculationTemplateListResponse(ApiModel):
    items: list[CalculationTemplate]
    total: int
    limit: int
    offset: int


class CalculationTemplateWorkspace(ApiModel):
    template: CalculationTemplate
    steps: list[CalculationTemplateStep] = Field(default_factory=list)


class ContractLinePayload(ApiModel):
    charge_component_code: str
    rate_book_id: int | None = None
    calculation_template_id: int | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class RateContractPayload(ApiModel):
    contract_number: str
    contract_name: str
    contract_role: Literal["PAYER", "PAYEE"]
    payer_party_ref: str | None = None
    payee_party_ref: str | None = None
    party_role_ref: str | None = None
    partner_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    company_id: int | None = None
    currency: str = "USD"
    valid_from: date | None = None
    valid_to: date | None = None
    default_rate_book_id: int | None = None
    default_calculation_template_id: int | None = None
    lines: list[ContractLinePayload] = Field(default_factory=list)


class ContractLine(ContractLinePayload):
    id: int
    contract_id: int


class RateContract(RateContractPayload):
    id: int
    status: str = "DRAFT"
    lines: list[ContractLine] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RateContractListResponse(ApiModel):
    items: list[RateContract]
    total: int
    limit: int
    offset: int


class ContractWorkspace(ApiModel):
    contract: RateContract
    rate_books: list[RateBook] = Field(default_factory=list)


class RateContractUpdate(ApiModel):
    contract_name: str | None = None
    status: str | None = None
    currency: str | None = None
    default_rate_book_id: int | None = None
    default_calculation_template_id: int | None = None
    lines: list[ContractLinePayload] | None = None


class QuoteRequestCreate(ApiModel):
    source_object_type: str = "MANUAL"
    source_object_id: str | None = None
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    currency: str = "USD"
    quantity: Decimal = Decimal("1")
    gross_weight: Decimal | None = None
    gross_volume_cbm: Decimal | None = None
    container_count: Decimal | None = None
    package_count: Decimal | None = None
    package_type: str | None = None
    requested_service_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    expires_at: datetime | None = None
    margin_rules: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class QuoteRequestWorkspaceUpdate(ApiModel):
    status: str | None = None
    source_object_type: str | None = None
    source_object_id: str | None = None
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    currency: str | None = None
    quantity: Decimal | None = None
    gross_weight: Decimal | None = None
    gross_volume_cbm: Decimal | None = None
    container_count: Decimal | None = None
    package_count: Decimal | None = None
    package_type: str | None = None
    requested_service_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    expires_at: datetime | None = None
    margin_rules: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class QuoteRequest(QuoteRequestCreate):
    id: int
    status: str = "DRAFT"
    quotation_policy_snapshot: Literal["REQUIRED", "OPTIONAL", "DIRECT_ONLY"] = "OPTIONAL"
    awarded_option_id: int | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class QuoteOfferCreate(ApiModel):
    provider_party_ref: str | None = None
    provider_role_ref: str | None = None
    offer_number: str | None = None
    source: str = "MANUAL"
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    is_sealed: bool = True
    transit_time_days: int | None = None
    service_level: str | None = None
    performance_score: Decimal | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class QuoteOffer(QuoteOfferCreate):
    id: int
    quote_request_id: int
    status: str = "SUBMITTED"
    is_sealed: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class QuoteOfferWorkspaceUpdate(ApiModel):
    offer_number: str | None = None
    source: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    transit_time_days: int | None = None
    service_level: str | None = None
    performance_score: Decimal | None = None
    expires_at: datetime | None = None
    notes: str | None = None


class QuoteOfferWithdrawRequest(ApiModel):
    reason: str | None = None


class QuoteOptionLine(ApiModel):
    id: int
    quote_option_id: int
    relationship_role: Literal["PAYER", "PAYEE"]
    payer_party_ref: str | None = None
    payee_party_ref: str | None = None
    party_role_ref: str | None = None
    charge_component_code: str
    description: str
    amount: Decimal
    currency: str
    basis: str
    quantity_uom: str | None = None
    allocation_basis: str | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    pinned_allocation_snapshot_json: dict[str, Any] | None = None
    effective_allocation_snapshot_json: dict[str, Any] | None = None
    source_contract_id: int | None = None
    source_rate_book_id: int | None = None
    is_margin_line: bool = False


class QuoteOption(ApiModel):
    id: int
    quote_request_id: int
    option_name: str
    source_offer_id: int | None = None
    payer_contract_id: int | None = None
    payee_contract_id: int | None = None
    payer_total_amount: Decimal = Decimal("0")
    payee_total_amount: Decimal = Decimal("0")
    margin_amount: Decimal = Decimal("0")
    margin_percent: Decimal = Decimal("0")
    transit_time_days: int | None = None
    service_level_score: Decimal = Decimal("0")
    policy_compliant: bool = True
    rank: int | None = None
    score: Decimal | None = None
    expires_at: datetime | None = None
    lines: list[QuoteOptionLine] = Field(default_factory=list)


class QuoteOfferWorkspace(ApiModel):
    offer: QuoteOffer
    quote_request: QuoteRequest
    quote_option: QuoteOption | None = None


class ContractDeterminationResponse(ApiModel):
    quote_request_id: int
    payer_contracts: list[RateContract]
    payee_contracts: list[RateContract]


class RateResponse(ApiModel):
    quote_request: QuoteRequest
    options: list[QuoteOption]


class RankResponse(ApiModel):
    quote_request_id: int
    options: list[QuoteOption]


class QuoteAwardRequest(ApiModel):
    quote_option_id: int


class ChargeDocumentLineCreate(ApiModel):
    relationship_role: Literal["PAYER", "PAYEE"]
    line_number: int | None = None
    parent_line_number: int | None = None
    line_role: Literal["CALCULATION", "POSTING"] = "POSTING"
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"] | None = None
    target_object_type: str | None = None
    target_object_id: str | None = None
    payer_party_ref: str | None = None
    payee_party_ref: str | None = None
    party_role_ref: str | None = None
    charge_component_code: str
    description: str | None = None
    charge_date: date | None = None
    charge_date_basis: Literal[
        "DOCUMENT_DATE",
        "SHIPMENT_DEPARTURE_DATE",
        "SHIPMENT_ARRIVAL_DATE",
        "HOUSE_BILL_ISSUE_DATE",
        "MANUAL",
    ] | None = None
    expected_amount: Decimal
    currency: str = "USD"
    quantity_uom: str | None = None
    source_currency: str | None = None
    source_amount: Decimal | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    fx_rate_id: int | None = None
    exchange_rate_source_code: str | None = None
    exchange_rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] | None = None
    exchange_rate_method: str | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    charge_text_snapshot: str | None = None
    allocation_basis: str | None = None
    allocation_ratio: Decimal | None = None
    allocation_driver_value: Decimal | None = None
    target_reference_snapshot_json: dict[str, Any] | None = None
    calculation_audit_json: dict[str, Any] | None = None
    basis: str = "FLAT"


class ChargeDocumentLineWorkspaceUpdate(ChargeDocumentLineCreate):
    id: int | None = None


class ChargeDocumentCreate(ApiModel):
    document_number: str | None = None
    source_object_type: str = "MANUAL"
    source_object_id: str | None = None
    document_scope_level: str | None = None
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE"] | None = None
    document_date: date | None = None
    source_reference_snapshot_json: dict[str, Any] | None = None
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    currency: str = "USD"
    lines: list[ChargeDocumentLineCreate] = Field(default_factory=list)


class ChargeLine(ApiModel):
    id: int
    charge_document_id: int
    relationship_role: Literal["PAYER", "PAYEE"]
    line_number: int | None = None
    parent_line_id: int | None = None
    parent_line_number: int | None = None
    line_role: Literal["CALCULATION", "POSTING"] = "POSTING"
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"] | None = None
    target_object_type: str | None = None
    target_object_id: str | None = None
    payer_party_ref: str | None = None
    payee_party_ref: str | None = None
    party_role_ref: str | None = None
    charge_component_code: str
    description: str
    charge_date: date | None = None
    charge_date_basis: Literal[
        "DOCUMENT_DATE",
        "SHIPMENT_DEPARTURE_DATE",
        "SHIPMENT_ARRIVAL_DATE",
        "HOUSE_BILL_ISSUE_DATE",
        "MANUAL",
    ] | None = None
    expected_amount: Decimal
    actual_amount: Decimal | None = None
    approved_amount: Decimal | None = None
    currency: str
    quantity_uom: str | None = None
    source_currency: str | None = None
    source_amount: Decimal | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    fx_rate_id: int | None = None
    exchange_rate_source_code: str | None = None
    exchange_rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] | None = None
    exchange_rate_method: str | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    pinned_allocation_snapshot_json: dict[str, Any] | None = None
    effective_allocation_snapshot_json: dict[str, Any] | None = None
    charge_text_snapshot: str | None = None
    allocation_basis: str | None = None
    allocation_ratio: Decimal | None = None
    allocation_driver_value: Decimal | None = None
    target_reference_snapshot_json: dict[str, Any] | None = None
    calculation_audit_json: dict[str, Any] | None = None
    basis: str
    source_quote_option_line_id: int | None = None


class ChargeDocument(ApiModel):
    id: int
    document_number: str
    quote_request_id: int | None = None
    quote_option_id: int | None = None
    quotation_policy_snapshot: Literal["REQUIRED", "OPTIONAL", "DIRECT_ONLY"] = "OPTIONAL"
    source_object_type: str = "MANUAL"
    source_object_id: str | None = None
    document_scope_level: str | None = None
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE"] | None = None
    document_date: date | None = None
    source_reference_snapshot_json: dict[str, Any] | None = None
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    status: str = "ESTIMATED"
    currency: str = "USD"
    payer_total_amount: Decimal = Decimal("0")
    payee_total_amount: Decimal = Decimal("0")
    margin_amount: Decimal = Decimal("0")
    lines: list[ChargeLine] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    approved_at: datetime | None = None
    exported_at: datetime | None = None
    reversed_at: datetime | None = None
    reversal_reason: str | None = None


class ChargeDocumentListResponse(ApiModel):
    items: list[ChargeDocument]
    total: int
    limit: int
    offset: int


class ChargeDocumentWorkspace(ApiModel):
    document: ChargeDocument
    invoices: list["ChargeInvoice"] = Field(default_factory=list)
    match_results: list["ChargeMatchResult"] = Field(default_factory=list)


class ChargeDocumentWorkspaceUpdate(ApiModel):
    status: str | None = None
    lines: list[ChargeDocumentLineWorkspaceUpdate] | None = None


class QuoteCommitmentConsumption(ApiModel):
    id: int
    commitment_id: int
    source_object_type: str
    source_object_id: str | None = None
    reference_number: str | None = None
    container_count: Decimal | None = None
    package_count: Decimal | None = None
    chargeable_weight: Decimal | None = None
    quantity: Decimal | None = None
    amount: Decimal | None = None
    consumed_at: datetime = Field(default_factory=utcnow)
    status: str = "ACTIVE"
    reversed_at: datetime | None = None
    reversal_reason: str | None = None


class QuoteCommitment(ApiModel):
    id: int
    commitment_number: str
    quote_request_id: int
    quote_option_id: int
    charge_document_id: int
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    package_type: str | None = None
    requested_service_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    committed_container_count: Decimal | None = None
    consumed_container_count: Decimal = Decimal("0")
    remaining_container_count: Decimal | None = None
    committed_package_count: Decimal | None = None
    consumed_package_count: Decimal = Decimal("0")
    remaining_package_count: Decimal | None = None
    committed_chargeable_weight: Decimal | None = None
    consumed_chargeable_weight: Decimal = Decimal("0")
    remaining_chargeable_weight: Decimal | None = None
    committed_quantity: Decimal = Decimal("1")
    consumed_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("1")
    committed_amount: Decimal = Decimal("0")
    consumed_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    currency: str = "USD"
    status: str = "ACTIVE"
    consumptions: list[QuoteCommitmentConsumption] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class QuoteCommitmentMatchRequest(ApiModel):
    source_object_type: str | None = None
    source_object_id: str | None = None
    company_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    package_type: str | None = None
    requested_service_date: date | None = None
    container_count: Decimal | None = None
    package_count: Decimal | None = None
    chargeable_weight: Decimal | None = None
    quantity: Decimal | None = None


class QuoteCommitmentMatchResponse(ApiModel):
    matches: list[QuoteCommitment]


class QuoteCommitmentConsumeRequest(ApiModel):
    source_object_type: str
    source_object_id: str | None = None
    reference_number: str | None = None
    container_count: Decimal | None = None
    package_count: Decimal | None = None
    chargeable_weight: Decimal | None = None
    quantity: Decimal | None = None
    amount: Decimal | None = None


class QuoteCommitmentConsumeResponse(ApiModel):
    commitment: QuoteCommitment
    consumption: QuoteCommitmentConsumption


class QuoteCommitmentConsumptionReverseRequest(ApiModel):
    reason: str | None = None


class QuoteAwardResponse(ApiModel):
    quote_request: QuoteRequest
    awarded_option: QuoteOption
    charge_document: ChargeDocument
    quote_commitment: QuoteCommitment | None = None


class QuoteRequestListResponse(ApiModel):
    items: list[QuoteRequest]
    total: int
    limit: int
    offset: int


class QuoteRequestWorkspace(ApiModel):
    quote_request: QuoteRequest
    options: list[QuoteOption] = Field(default_factory=list)
    offers: list[QuoteOffer] = Field(default_factory=list)
    commitments: list[QuoteCommitment] = Field(default_factory=list)
    charge_documents: list[ChargeDocument] = Field(default_factory=list)


class ChargeInvoiceCreate(ApiModel):
    charge_document_id: int
    invoice_number: str
    invoice_type: Literal["SUPPLIER", "CUSTOMER"] = "SUPPLIER"
    invoice_date: date | None = None
    currency: str = "USD"
    lines: list[dict[str, Any]] = Field(default_factory=list)


class ChargeInvoiceWorkspaceUpdate(ApiModel):
    invoice_number: str | None = None
    invoice_type: Literal["SUPPLIER", "CUSTOMER"] | None = None
    invoice_date: date | None = None
    currency: str | None = None
    lines: list[dict[str, Any]] | None = None


class ChargeInvoice(ChargeInvoiceCreate):
    id: int
    charge_document_number: str | None = None
    charge_document_status: str | None = None
    status: str = "CAPTURED"
    total_amount: Decimal = Decimal("0")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeInvoiceListResponse(ApiModel):
    items: list[ChargeInvoice]
    total: int
    limit: int
    offset: int


class ChargeMatchResult(ApiModel):
    id: int
    invoice_id: int
    charge_document_id: int
    charge_line_id: int | None = None
    charge_component_code: str
    expected_amount: Decimal
    invoice_amount: Decimal
    variance_amount: Decimal
    variance_percent: Decimal
    match_status: str
    notes: str | None = None


class InvoiceMatchResponse(ApiModel):
    invoice: ChargeInvoice
    results: list[ChargeMatchResult]


class ChargeInvoiceWorkspace(ApiModel):
    invoice: ChargeInvoice
    charge_document: ChargeDocument
    match_results: list[ChargeMatchResult] = Field(default_factory=list)


class ChargeActionResponse(ApiModel):
    document: ChargeDocument


class ChargeExportResponse(ApiModel):
    document: ChargeDocument
    export_number: str
    target_system: str
    status: str
    payload_json: dict[str, Any]


class ChargeReverseRequest(ApiModel):
    reason: str
