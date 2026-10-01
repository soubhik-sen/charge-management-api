from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


CalculationProfileStatus = Literal["DRAFT", "PUBLISHED", "RETIRED"]
CalculationTemplateStatus = Literal["DRAFT", "PUBLISHED", "RETIRED"]
RateBookRowAttributeKey = Literal[
    "basis_override",
    "charge_context_override",
    "origin_code",
    "destination_code",
    "mode",
    "equipment_type",
    "commodity_code",
    "service_level",
    "scale_from",
    "scale_to",
    "minimum_amount",
    "maximum_amount",
    "validity_from",
    "validity_to",
    "calculation_profile_id",
    "allocation_profile_id",
    "priority",
]
CalculationApplicationLevel = Literal["SHIPMENT", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
CalculationMethod = Literal["FLAT_AMOUNT", "RATE_TIMES_PRODUCT", "PERCENT_OF_REFERENCE"]
CalculationFactorResolver = Literal[
    "MANUAL",
    "TARGET_COUNT",
    "CONTAINER_COUNT",
    "HOUSE_COUNT",
    "PO_SCHEDULE_LINE_COUNT",
    "QUANTITY",
    "WEIGHT",
    "VOLUME",
    "CHARGEABLE_WEIGHT",
    "OCEAN_WM",
    "REFERENCE_AMOUNT",
    "DURATION_HOURS",
    "DURATION_DAYS",
    "FIXED_VALUE",
]

RATE_BOOK_ROW_ATTRIBUTE_KEYS = (
    "basis_override",
    "charge_context_override",
    "origin_code",
    "destination_code",
    "mode",
    "equipment_type",
    "commodity_code",
    "service_level",
    "scale_from",
    "scale_to",
    "minimum_amount",
    "maximum_amount",
    "validity_from",
    "validity_to",
    "calculation_profile_id",
    "allocation_profile_id",
    "priority",
)
ChargeTargetScopeMode = Literal["ALL_ELIGIBLE", "SELECTED_TARGETS"]
BusinessDatePurpose = Literal["EXCHANGE_RATE_DATE", "PAYMENT_BASELINE_DATE"]
BusinessDateType = Literal[
    "INVOICE_DATE",
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
    "ROAD_ACTUAL_PICKUP_DATE",
    "ROAD_PLANNED_PICKUP_DATE",
    "ROAD_ACTUAL_DELIVERY_DATE",
    "ROAD_PLANNED_DELIVERY_DATE",
    "CMR_ISSUE_DATE",
]


def _normalize_quote_component_inputs(
    value: Any,
) -> dict[str, dict[str, Any]]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("component_calculation_inputs must be an object keyed by component code")
    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_inputs in value.items():
        key = str(raw_key).strip().upper()
        if not key:
            raise ValueError("component_calculation_inputs keys must be non-empty component codes")
        if key in normalized and str(raw_key) != key:
            raise ValueError(f"Duplicate component_calculation_inputs key after normalization: {raw_key}")
        if raw_inputs in (None, ""):
            normalized[key] = {}
            continue
        if not isinstance(raw_inputs, dict):
            raise ValueError(f"component_calculation_inputs[{raw_key!r}] must be an object")
        normalized[key] = dict(raw_inputs)
    return normalized


def _validate_quote_date_values(values: list["BusinessDateValue"] | None) -> list["BusinessDateValue"] | None:
    if values is None:
        return None
    date_types = [item.date_type for item in values]
    if len(date_types) != len(set(date_types)):
        raise ValueError("date_values must contain at most one value for each date_type")
    return values


def _normalize_owner_type(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, str):
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("owner_type is required when owner_id is set")
        return cleaned
    return value


class ChargeComponent(ApiModel):
    id: int
    owner_type: Literal["GLOBAL", "FORWARDER"] = "GLOBAL"
    owner_id: int = Field(default=0, ge=0)
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
    default_calculation_profile_id: int | None = None
    manual_entry_enabled: bool = Field(
        default=False,
        description="Whether consuming adapters may offer this component for manual entry; authorization remains adapter owned.",
    )
    is_tax: bool = False
    is_active: bool = True

    @computed_field
    @property
    def default_side(self) -> Literal["PAYER", "PAYEE", "BOTH"]:
        return self.default_party_role

    @computed_field
    @property
    def default_relationship_role(self) -> Literal["PAYER", "PAYEE", "BOTH"]:
        return self.default_party_role

    @computed_field
    @property
    def default_allocation_profile_id(self) -> int | None:
        return self.allocation_profile_id


class ChargeComponentPayload(ApiModel):
    owner_type: Literal["GLOBAL", "FORWARDER"] | None = None
    owner_id: int | None = Field(default=None, ge=0)
    component_code: str
    component_name: str
    category: str = "ACCESSORIAL"
    default_party_role: Literal["PAYER", "PAYEE", "BOTH"] | None = None
    default_side: Literal["PAYER", "PAYEE", "BOTH"] | None = None
    default_relationship_role: Literal["PAYER", "PAYEE", "BOTH"] | None = None
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
    default_allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    default_calculation_profile_id: int | None = None
    manual_entry_enabled: bool = Field(
        default=False,
        description="Whether consuming adapters may offer this component for manual entry; authorization remains adapter owned.",
    )
    is_tax: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def normalize_flux_compatibility_fields(self) -> "ChargeComponentPayload":
        if (self.owner_type is None) != (self.owner_id is None):
            raise ValueError("Component owner type and ID must be provided together")
        if (self.owner_type == "GLOBAL" and self.owner_id != 0) or (
            self.owner_type == "FORWARDER" and (self.owner_id is None or self.owner_id <= 0)
        ):
            raise ValueError("Component owner must be GLOBAL/0 or FORWARDER with a positive ID")
        roles = {
            value
            for value in (
                self.default_party_role,
                self.default_side,
                self.default_relationship_role,
            )
            if value is not None
        }
        if len(roles) > 1:
            raise ValueError(
                "default_party_role, default_side, and default_relationship_role must agree"
            )
        resolved_role = next(iter(roles), "BOTH")
        self.default_party_role = resolved_role
        self.default_side = resolved_role
        self.default_relationship_role = resolved_role
        if (
            self.allocation_profile_id is not None
            and self.default_allocation_profile_id is not None
            and self.allocation_profile_id != self.default_allocation_profile_id
        ):
            raise ValueError(
                "allocation_profile_id and default_allocation_profile_id must agree"
            )
        resolved_profile_id = self.allocation_profile_id or self.default_allocation_profile_id
        self.allocation_profile_id = resolved_profile_id
        self.default_allocation_profile_id = resolved_profile_id
        return self


class ChargeComponentListResponse(ApiModel):
    items: list[ChargeComponent]
    total: int
    limit: int
    offset: int


class ChargeComponentAliasPayload(ApiModel):
    document_kind: str = "CHARGE_PROPOSAL"
    template_key: str | None = None
    source_section: str | None = None
    source_uom: str | None = None
    customer_id: int | None = None
    forwarder_id: int | None = None
    transport_mode: str | None = None
    raw_label: str
    charge_component_id: int
    default_calculation_basis: str = "DOCUMENT"
    default_charge_level: str = "SHIPMENT"
    default_allocation_basis: str | None = None
    default_calculation_profile_id: int | None = None
    default_calculation_profile_version_id: int | None = None
    container_house_allocation_basis: str | None = None
    house_item_allocation_basis: str | None = None
    final_posting_level: Literal["HOUSE", "PO_SCHEDULE_LINE"] | None = "PO_SCHEDULE_LINE"
    default_quantity_uom: str | None = None
    allocation_override_mode: Literal["INHERIT_PROFILE", "OVERRIDE_PROFILE", "NO_ALLOCATION"] = "OVERRIDE_PROFILE"
    override_allocation_profile_id: int | None = None
    override_allocation_profile_version_id: int | None = None
    override_calculation_profile_id: int | None = None
    override_calculation_profile_version_id: int | None = None
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
    effective_from: date | None = None
    effective_to: date | None = None
    source_level: Literal["SHIPMENT", "CONTAINER", "HOUSE", "DOCUMENT"]
    source_to_house_driver: str | None = None
    house_to_item_driver: str | None = None
    source_to_item_driver: str | None = None
    final_posting_level: Literal["HOUSE", "PO_SCHEDULE_LINE"]
    default_quantity_uom: str | None = None
    missing_driver_policy: Literal["BLOCK", "EQUAL"] = "BLOCK"
    settings_json: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_effective_period(self) -> "ChargeAllocationProfileVersionPayload":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_from > self.effective_to:
                raise ValueError("effective_from must be less than or equal to effective_to")
        return self


class ChargeAllocationProfileVersionCreate(ChargeAllocationProfileVersionPayload):
    expected_lock_version: int | None = Field(default=None, ge=1)


class OwnerScopedProfilePayload(ApiModel):
    owner_type: str = "SYSTEM"
    owner_id: int = Field(default=0, ge=0)

    @field_validator("owner_type", mode="before")
    @classmethod
    def normalize_owner_type(cls, value: Any) -> Any:
        return _normalize_owner_type(value)


class ChargeAllocationProfileCreate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str
    initial_version: ChargeAllocationProfileVersionCreate


class ChargeAllocationProfileUpdate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str


class ChargeAllocationProfileVersion(ChargeAllocationProfileVersionPayload):
    id: int
    profile_id: int
    version_number: int
    status: Literal["DRAFT", "PUBLISHED", "RETIRED"] = "DRAFT"
    lock_version: int = 1
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeAllocationProfile(ApiModel):
    id: int
    profile_code: str
    profile_name: str
    owner_type: str
    owner_id: int
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


class ChargeCalculationProfileFactorPayload(ApiModel):
    sequence: int
    factor_code: str
    factor_label: str
    resolver: CalculationFactorResolver
    uom: str | None = None
    is_required: bool = True
    default_value: Decimal | None = None


class ChargeCalculationProfileFactor(ChargeCalculationProfileFactorPayload):
    id: int
    profile_version_id: int


class ChargeCalculationProfileVersionPayload(ApiModel):
    effective_from: date | None = None
    effective_to: date | None = None
    application_level: CalculationApplicationLevel
    calculation_method: CalculationMethod = "RATE_TIMES_PRODUCT"
    rate_uom: str | None = None
    missing_factor_policy: Literal["BLOCK"] = "BLOCK"
    minimum_amount: Decimal | None = None
    maximum_amount: Decimal | None = None
    factors: list[ChargeCalculationProfileFactorPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_calculation_profile_bounds(self) -> "ChargeCalculationProfileVersionPayload":
        if self.minimum_amount is not None and self.maximum_amount is not None:
            if self.minimum_amount > self.maximum_amount:
                raise ValueError("minimum_amount must be less than or equal to maximum_amount")
        return self


class ChargeCalculationProfileVersionCreate(ChargeCalculationProfileVersionPayload):
    expected_lock_version: int | None = Field(default=None, ge=1)


class ChargeCalculationProfileVersion(ChargeCalculationProfileVersionPayload):
    id: int
    profile_id: int
    version_number: int
    status: CalculationProfileStatus = "DRAFT"
    lock_version: int = 1
    published_at: datetime | None = None
    published_by: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    factors: list[ChargeCalculationProfileFactor] = Field(default_factory=list)


class ChargeCalculationProfileCreate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str
    description: str | None = None
    is_active: bool = True
    initial_version: ChargeCalculationProfileVersionCreate


class ChargeCalculationProfileUpdate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str
    description: str | None = None
    is_active: bool = True


class ChargeCalculationProfile(ApiModel):
    id: int
    profile_code: str
    profile_name: str
    owner_type: str
    owner_id: int
    description: str | None = None
    is_active: bool = True
    published_version_id: int | None = None
    published_version_number: int | None = None
    versions: list[ChargeCalculationProfileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChargeCalculationProfileListResponse(ApiModel):
    items: list[ChargeCalculationProfile]
    total: int
    limit: int
    offset: int


class BusinessDateProfileStepPayload(ApiModel):
    step_number: int
    date_key: BusinessDateType = Field(
        description="Supported operational date identifier evaluated at this fallback position."
    )
    notes: str | None = None

    @field_validator("date_key", mode="before")
    @classmethod
    def normalize_date_key(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class BusinessDateProfileStepCreate(BusinessDateProfileStepPayload):
    pass


class BusinessDateProfileVersionPayload(ApiModel):
    steps: list[BusinessDateProfileStepCreate] = Field(default_factory=list)
    notes: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_effective_period(self) -> "BusinessDateProfileVersionPayload":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_from > self.effective_to:
                raise ValueError("effective_from must be less than or equal to effective_to")
        return self


class BusinessDateProfileVersionCreate(BusinessDateProfileVersionPayload):
    expected_lock_version: int | None = Field(default=None, ge=1)


class BusinessDateProfileCreate(OwnerScopedProfilePayload):
    business_purpose: BusinessDatePurpose = "EXCHANGE_RATE_DATE"
    profile_code: str = Field(
        validation_alias=AliasChoices("profile_code", "profile_key")
    )
    profile_name: str
    description: str | None = None
    initial_version: BusinessDateProfileVersionCreate | None = None
    event_codes: list[BusinessDateType] | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    @field_validator("event_codes", mode="before")
    @classmethod
    def normalize_event_codes(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return [item.strip().upper() if isinstance(item, str) else item for item in value]

    @model_validator(mode="after")
    def normalize_flat_version(self) -> "BusinessDateProfileCreate":
        if self.initial_version is None:
            if not self.event_codes:
                raise ValueError("initial_version or event_codes is required")
            self.initial_version = BusinessDateProfileVersionCreate(
                effective_from=self.effective_from,
                effective_to=self.effective_to,
                steps=[
                    BusinessDateProfileStepCreate(
                        step_number=index * 10,
                        date_key=event_code,
                    )
                    for index, event_code in enumerate(self.event_codes, start=1)
                ],
            )
        return self


class BusinessDateProfileUpdate(OwnerScopedProfilePayload):
    profile_code: str = Field(
        validation_alias=AliasChoices("profile_code", "profile_key")
    )
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
    lock_version: int = 1
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    steps: list[BusinessDateProfileStep] = Field(default_factory=list)

    @computed_field
    @property
    def event_codes(self) -> list[str]:
        return [
            step.date_key
            for step in sorted(self.steps, key=lambda item: (item.step_number, item.id))
        ]


class BusinessDateProfile(ApiModel):
    business_purpose: BusinessDatePurpose = "EXCHANGE_RATE_DATE"
    id: int
    profile_code: str
    profile_name: str
    owner_type: str
    owner_id: int
    description: str | None = None
    published_version_id: int | None = None
    published_version_number: int | None = None
    versions: list[BusinessDateProfileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @computed_field
    @property
    def profile_key(self) -> str:
        return self.profile_code


class FreeTimeRulePayload(ApiModel):
    sequence: int
    rule_code: str
    rule_name: str
    scope_type: str = "GLOBAL"
    scope_id: int | None = None
    event_type: str | None = None
    start_timestamp_key: str
    end_timestamp_key: str
    free_time_days: Decimal = Decimal("0")
    match_facts_json: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    notes: str | None = None
    is_active: bool = True

    @field_validator("scope_type", "event_type", "start_timestamp_key", "end_timestamp_key", mode="before")
    @classmethod
    def normalize_rule_strings(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str):
            cleaned = value.strip().upper()
            if not cleaned:
                raise ValueError("rule string values must not be blank")
            return cleaned
        return value


class FreeTimeRuleCreate(FreeTimeRulePayload):
    pass


class FreeTimeRule(FreeTimeRulePayload):
    id: int
    profile_version_id: int


class FreeTimeProfileVersionPayload(ApiModel):
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = None
    rules: list[FreeTimeRuleCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_effective_period(self) -> "FreeTimeProfileVersionPayload":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_from > self.effective_to:
                raise ValueError("effective_from must be less than or equal to effective_to")
        return self


class FreeTimeProfileVersionCreate(FreeTimeProfileVersionPayload):
    expected_lock_version: int | None = Field(default=None, ge=1)


class FreeTimeProfileCreate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str
    description: str | None = None
    initial_version: FreeTimeProfileVersionCreate


class FreeTimeProfileUpdate(OwnerScopedProfilePayload):
    profile_code: str
    profile_name: str
    description: str | None = None


class FreeTimeProfileVersion(FreeTimeProfileVersionPayload):
    id: int
    profile_id: int
    version_number: int
    status: Literal["DRAFT", "PUBLISHED", "RETIRED"] = "DRAFT"
    lock_version: int = 1
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    rules: list[FreeTimeRule] = Field(default_factory=list)


class FreeTimeProfile(ApiModel):
    id: int
    profile_code: str
    profile_name: str
    owner_type: str
    owner_id: int
    description: str | None = None
    published_version_id: int | None = None
    published_version_number: int | None = None
    versions: list[FreeTimeProfileVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class FreeTimeProfileListResponse(ApiModel):
    items: list[FreeTimeProfile]
    total: int
    limit: int
    offset: int


class FreeTimeDurationPreviewRequest(ApiModel):
    scope_type: str | None = None
    scope_id: int | None = None
    event_type: str | None = None
    event_facts: dict[str, Any] = Field(default_factory=dict)
    event_timestamps: dict[str, datetime] = Field(default_factory=dict)

    @field_validator("scope_type", "event_type", mode="before")
    @classmethod
    def normalize_preview_strings(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str):
            cleaned = value.strip().upper()
            return cleaned or None
        return value


class FreeTimeDurationPreviewResponse(ApiModel):
    profile_id: int
    profile_code: str
    profile_version_id: int
    rule_id: int
    rule_code: str
    rule_name: str
    scope_type: str
    scope_id: int | None = None
    event_type: str | None = None
    start_timestamp_key: str
    end_timestamp_key: str
    start_timestamp: datetime
    end_timestamp: datetime
    duration_basis: Literal["DURATION_DAYS"] = "DURATION_DAYS"
    duration_days: Decimal
    free_time_days: Decimal
    chargeable_days: Decimal
    event_facts: dict[str, Any] = Field(default_factory=dict)
    event_timestamps: dict[str, datetime] = Field(default_factory=dict)


class BusinessDateValue(ApiModel):
    date_type: BusinessDateType = Field(
        description=(
            "Supported operational date identifier. The API normalizes lowercase input to "
            "the documented uppercase value."
        )
    )
    date_value: date = Field(description="Caller-supplied date in ISO 8601 YYYY-MM-DD format.")

    @field_validator("date_type", mode="before")
    @classmethod
    def normalize_date_type(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class BusinessDateResolveRequest(ApiModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "profile_id": 1,
                    "date_values": [
                        {
                            "date_type": "SHIPMENT_ACTUAL_DEPARTURE_DATE",
                            "date_value": "2026-08-09",
                        },
                        {
                            "date_type": "DOCUMENT_DATE",
                            "date_value": "2026-08-10",
                        },
                    ],
                    "fallback_date": "2026-08-10",
                }
            ]
        },
    )

    profile_id: int | None = None
    profile_version_id: int | None = None
    date_values: list[BusinessDateValue] = Field(
        default_factory=list,
        description=(
            "Typed dates supplied by the caller. Date types must be unique and are "
            "evaluated in the order defined by the selected profile."
        ),
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        json_schema_extra={"deprecated": True},
        description=(
            "Deprecated untyped date context retained for backward compatibility. "
            "New integrations should send date_values."
        ),
    )
    fallback_date: date | None = None

    @model_validator(mode="after")
    def validate_profile_reference(self) -> "BusinessDateResolveRequest":
        if self.profile_id is None and self.profile_version_id is None:
            raise ValueError("profile_id or profile_version_id is required")
        date_types = [item.date_type for item in self.date_values]
        if len(date_types) != len(set(date_types)):
            raise ValueError("date_values must contain at most one value for each date_type")
        return self


class BusinessDateResolveResponse(ApiModel):
    profile_id: int
    profile_code: str
    profile_version_id: int
    version_number: int
    resolved_date: date
    selected_date_key: BusinessDateType | None = None
    fallback_applied: bool = False
    attempted_date_keys: list[BusinessDateType] = Field(default_factory=list)
    supplied_date_keys: list[BusinessDateType] = Field(default_factory=list)


class BusinessDateProfileListResponse(ApiModel):
    items: list[BusinessDateProfile]
    total: int
    limit: int
    offset: int


class BusinessDateProfileAssignmentPayload(ApiModel):
    scope_type: Literal["GLOBAL", "COMPANY", "CUSTOMER", "VENDOR", "FORWARDER", "CARRIER"]
    scope_id: int | None = None
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE", "ROAD_SHIPMENT"]
    business_purpose: BusinessDatePurpose = "EXCHANGE_RATE_DATE"
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


PricingDimensionDataType = Literal["STRING", "DECIMAL", "INTEGER", "BOOLEAN", "DATE"]


class PricingDimensionPayload(ApiModel):
    dimension_code: str
    dimension_name: str
    description: str | None = None
    data_type: PricingDimensionDataType = "STRING"
    allowed_values: list[str] = Field(default_factory=list)
    case_sensitive: bool = False
    is_active: bool = True


class PricingDimension(PricingDimensionPayload):
    id: int
    built_in_field: str | None = None
    is_system: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class PricingDimensionListResponse(ApiModel):
    items: list[PricingDimension]
    total: int
    limit: int
    offset: int


class CallerAttributeMapping(ApiModel):
    source_attribute: str
    dimension_code: str
    required: bool = False
    default_value: Any | None = None
    value_map: dict[str, Any] = Field(default_factory=dict)


class CallerMappingProfilePayload(ApiModel):
    profile_code: str
    profile_name: str
    caller_system_code: str
    schema_version: str = "1"
    description: str | None = None
    mappings: list[CallerAttributeMapping] = Field(default_factory=list)
    is_active: bool = True


class CallerMappingProfile(CallerMappingProfilePayload):
    id: int
    canonical_dimension_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CallerMappingProfileListResponse(ApiModel):
    items: list[CallerMappingProfile]
    total: int
    limit: int
    offset: int


class CallerMappingPreviewRequest(ApiModel):
    caller_attributes: dict[str, Any] = Field(default_factory=dict)


class CallerMappingPreviewResponse(ApiModel):
    profile_code: str
    caller_system_code: str
    schema_version: str
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    standard_fields: dict[str, Any] = Field(default_factory=dict)


class ChargeAllocationTargetInput(ApiModel):
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
    target_object_type: str
    target_object_id: str
    driver_value: Decimal = Field(default=Decimal("1"), ge=0)
    target_reference_snapshot_json: dict[str, Any] | None = None


class ChargeAllocationPreviewResult(ChargeAllocationTargetInput):
    allocation_ratio: Decimal
    allocated_amount: Decimal
    currency: str


class ChargeCalculationPreviewRequest(ApiModel):
    basis: str = "FLAT"
    rate_amount: Decimal | None = None
    rate_percent: Decimal | None = None
    quantity: Decimal = Field(default=Decimal("1"), ge=0)
    percentage_base_amount: Decimal | None = None
    minimum_amount: Decimal | None = None
    maximum_amount: Decimal | None = None
    source_currency: str = "USD"
    target_currency: str = "USD"
    rate_date: date | None = None
    fx_source_id: int | None = None
    fx_source_code: str | None = None
    fx_rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] = "MID"
    fx_conversion_method: str = "DIRECT"
    allow_inverse_fx: bool = True
    allow_prior_fx_date: bool = True
    calculation_profile_version_id: int | None = None
    calculation_inputs: dict[str, Any] = Field(default_factory=dict)
    calculation_context: dict[str, Any] = Field(default_factory=dict)
    allocation_profile_version_id: int | None = None
    allocation_targets: list[ChargeAllocationTargetInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_calculation_request(self) -> "ChargeCalculationPreviewRequest":
        basis = self.basis.strip().upper()
        if basis in {"PERCENT", "PERCENTAGE"}:
            if self.rate_percent is None:
                raise ValueError("rate_percent is required for percentage basis")
            if self.percentage_base_amount is None:
                raise ValueError("percentage_base_amount is required for percentage basis")
            if self.calculation_profile_version_id is not None:
                raise ValueError("percentage basis cannot be combined with a calculation profile")
        elif self.rate_amount is None:
            raise ValueError("rate_amount is required for non-percentage basis")
        if self.minimum_amount is not None and self.maximum_amount is not None:
            if self.minimum_amount > self.maximum_amount:
                raise ValueError("minimum_amount must be less than or equal to maximum_amount")
        return self


class ChargeCalculationPreviewResponse(ApiModel):
    basis: str
    calculation_method: str
    rate_amount: Decimal | None = None
    rate_percent: Decimal | None = None
    quantity: Decimal
    percentage_base_amount: Decimal | None = None
    source_amount: Decimal
    source_currency: str
    amount: Decimal
    currency: str
    minimum_applied: bool = False
    maximum_applied: bool = False
    calculation_profile_version_id: int | None = None
    calculation_config_snapshot_json: dict[str, Any] | None = None
    calculation_input_snapshot_json: dict[str, Any] | None = None
    calculation_audit_json: dict[str, Any]
    fx_resolution: FxRateResolution
    allocation_profile_version_id: int | None = None
    allocation_config_snapshot_json: dict[str, Any] | None = None
    allocations: list[ChargeAllocationPreviewResult] = Field(default_factory=list)
    allocated_amount: Decimal = Decimal("0")
    unallocated_amount: Decimal = Decimal("0")


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
        "DISTANCE",
        "PER_HOUR",
        "PER_LOADING_METER",
        "PER_PALLET",
        "PER_STOP",
        "PERCENTAGE",
    ]
    modes: list[str] = ["OCEAN", "AIR", "ROAD", "RAIL", "MULTIMODAL"]
    currencies: list[str] = ["USD", "EUR", "INR", "BRL", "GBP"]
    quotation_policies: list[str] = ["REQUIRED", "OPTIONAL", "DIRECT_ONLY"]
    quote_acceptance_modes: list[str] = ["AUTO_ACCEPT", "CUSTOMER_ACCEPTANCE"]
    charge_line_roles: list[str] = ["CALCULATION", "POSTING"]
    charge_target_levels: list[str] = ["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
    allocation_profile_source_levels: list[str] = ["SHIPMENT", "CONTAINER", "HOUSE", "DOCUMENT"]
    allocation_profile_final_posting_levels: list[str] = ["HOUSE", "PO_SCHEDULE_LINE"]
    allocation_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
    calculation_profile_application_levels: list[str] = ["SHIPMENT", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
    calculation_profile_methods: list[str] = ["FLAT_AMOUNT", "RATE_TIMES_PRODUCT", "PERCENT_OF_REFERENCE"]
    calculation_profile_factor_resolvers: list[str] = [
        "MANUAL",
        "TARGET_COUNT",
        "CONTAINER_COUNT",
        "HOUSE_COUNT",
        "PO_SCHEDULE_LINE_COUNT",
        "QUANTITY",
        "WEIGHT",
        "VOLUME",
        "CHARGEABLE_WEIGHT",
        "OCEAN_WM",
        "REFERENCE_AMOUNT",
        "DURATION_HOURS",
        "DURATION_DAYS",
        "FIXED_VALUE",
    ]
    calculation_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
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
    business_date_shipment_scopes: list[str] = [
        "OCEAN_HOUSE",
        "AIR_HOUSE",
        "ROAD_SHIPMENT",
    ]
    business_date_purposes: list[str] = ["EXCHANGE_RATE_DATE", "PAYMENT_BASELINE_DATE"]
    business_date_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
    free_time_profile_version_statuses: list[str] = ["DRAFT", "PUBLISHED", "RETIRED"]
    fx_rate_types: list[str] = ["MID", "BUY", "SELL", "CUSTOM"]
    business_date_keys: list[str] = [
        "INVOICE_DATE",
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
        "ROAD_ACTUAL_PICKUP_DATE",
        "ROAD_PLANNED_PICKUP_DATE",
        "ROAD_ACTUAL_DELIVERY_DATE",
        "ROAD_PLANNED_DELIVERY_DATE",
        "CMR_ISSUE_DATE",
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
    rate_amount: Decimal | None = None
    rate_percent: Decimal | None = None
    basis: str | None = None
    basis_override: str | None = None
    charge_context: str | None = None
    charge_context_override: str | None = None
    currency: str = "USD"
    calculation_profile_id: int | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    scale_from: Decimal | None = None
    scale_to: Decimal | None = None
    minimum_amount: Decimal | None = None
    maximum_amount: Decimal | None = None
    validity_from: date | None = None
    validity_to: date | None = None
    priority: int = 100
    is_active: bool = True

    @model_validator(mode="after")
    def validate_rate_entry(self) -> "RateBookEntryPayload":
        configured_basis = (
            self.basis_override
            if "basis_override" in self.model_fields_set
            else self.basis
        )
        if configured_basis is None:
            if self.rate_amount is None and self.rate_percent is None:
                raise ValueError("rate_amount or rate_percent is required")
        elif configured_basis.strip().upper() in {"PERCENT", "PERCENTAGE"}:
            if self.rate_percent is None:
                raise ValueError("rate_percent is required for percentage basis")
        elif self.rate_amount is None:
            raise ValueError("rate_amount is required for non-percentage basis")
        if self.scale_from is not None and self.scale_to is not None and self.scale_from > self.scale_to:
            raise ValueError("scale_from must be less than or equal to scale_to")
        if self.validity_from is not None and self.validity_to is not None and self.validity_from > self.validity_to:
            raise ValueError("validity_from must be less than or equal to validity_to")
        return self


class RateBookPayload(ApiModel):
    rate_book_code: str
    rate_book_name: str
    charge_component_code: str | None = None
    row_attribute_keys: list[RateBookRowAttributeKey] = Field(
        default_factory=list,
        description=(
            "Controlled applicability and override columns shared by every row in this "
            "rate-book version. Rate value, currency, component, and active state are core fields."
        ),
    )
    dimension_codes: list[str] = Field(
        default_factory=list,
        description=(
            "Canonical applicability dimensions shared by every row. Values are supplied "
            "in each entry's dimension_values object."
        ),
    )
    description: str | None = None
    currency: str = "USD"
    valid_from: date | None = None
    valid_to: date | None = None
    calculation_basis: str = "FLAT"
    status: str = "DRAFT"
    is_active: bool = True
    entries: list[RateBookEntryPayload] = Field(default_factory=list)
    expected_lock_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_validity(self) -> "RateBookPayload":
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be less than or equal to valid_to")
        normalized_keys: list[str] = []
        for raw_key in self.row_attribute_keys:
            key = raw_key.strip().lower()
            if key not in RATE_BOOK_ROW_ATTRIBUTE_KEYS:
                raise ValueError(f"Unsupported rate-book row attribute: {raw_key}")
            if key not in normalized_keys:
                normalized_keys.append(key)

        component_codes = {
            entry.charge_component_code.strip().upper()
            for entry in self.entries
            if entry.charge_component_code.strip()
        }
        component_code = self.charge_component_code.strip().upper() if self.charge_component_code else None
        if component_code is None and len(component_codes) == 1:
            component_code = next(iter(component_codes))
        if component_code is not None and any(code != component_code for code in component_codes):
            raise ValueError("All rate rows must use the rate book's charge_component_code")

        if "row_attribute_keys" not in self.model_fields_set:
            for entry in self.entries:
                if (
                    "basis" in entry.model_fields_set
                    and entry.basis not in (None, "")
                    and "basis_override" not in normalized_keys
                ):
                    normalized_keys.append("basis_override")
                if (
                    "charge_context" in entry.model_fields_set
                    and entry.charge_context not in (None, "")
                    and "charge_context_override" not in normalized_keys
                ):
                    normalized_keys.append("charge_context_override")
                for key in RATE_BOOK_ROW_ATTRIBUTE_KEYS:
                    value = getattr(entry, key)
                    if key in entry.model_fields_set and value not in (None, "") and key not in normalized_keys:
                        normalized_keys.append(key)
        else:
            selected = set(normalized_keys)
            for entry in self.entries:
                if (
                    "basis_override" not in selected
                    and "basis" in entry.model_fields_set
                    and entry.basis not in (None, "")
                ):
                    raise ValueError("Rate row basis is outside row_attribute_keys")
                if (
                    "charge_context_override" not in selected
                    and "charge_context" in entry.model_fields_set
                    and entry.charge_context not in (None, "")
                ):
                    raise ValueError("Rate row charge context is outside row_attribute_keys")
                hidden_values = [
                    key
                    for key in RATE_BOOK_ROW_ATTRIBUTE_KEYS
                    if key not in selected
                    and key in entry.model_fields_set
                    and getattr(entry, key) not in (None, "")
                ]
                if hidden_values:
                    raise ValueError(
                        "Rate row contains values outside row_attribute_keys: "
                        + ", ".join(hidden_values)
                    )
        self.charge_component_code = component_code
        self.row_attribute_keys = normalized_keys
        normalized_dimension_codes: list[str] = []
        for raw_code in self.dimension_codes:
            code = raw_code.strip().upper()
            if not code:
                raise ValueError("Rate-book dimension codes must not be blank")
            if code not in normalized_dimension_codes:
                normalized_dimension_codes.append(code)
        selected_dimensions = set(normalized_dimension_codes)
        for entry in self.entries:
            normalized_values = {
                str(raw_code).strip().upper(): value
                for raw_code, value in entry.dimension_values.items()
                if str(raw_code).strip()
            }
            outside_dimensions = sorted(set(normalized_values) - selected_dimensions)
            if outside_dimensions:
                raise ValueError(
                    "Rate row contains dimension values outside dimension_codes: "
                    + ", ".join(outside_dimensions)
                )
            entry.dimension_values = normalized_values
        self.dimension_codes = normalized_dimension_codes
        return self


class RateBookEntry(RateBookEntryPayload):
    id: int
    rate_book_id: int


class RateBook(ApiModel):
    id: int
    rate_book_code: str
    rate_book_name: str
    charge_component_code: str | None = None
    row_attribute_keys: list[RateBookRowAttributeKey] = Field(default_factory=list)
    dimension_codes: list[str] = Field(default_factory=list)
    description: str | None = None
    currency: str = "USD"
    valid_from: date | None = None
    valid_to: date | None = None
    calculation_basis: str = "FLAT"
    status: str = "DRAFT"
    version_number: int = 1
    supersedes_rate_book_id: int | None = None
    lock_version: int = 1
    published_at: datetime | None = None
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
    versions: list[RateBook] = Field(default_factory=list)


class CalculationTemplateStepPayload(ApiModel):
    step_number: int = Field(ge=1)
    charge_component_code: str
    relationship_role: Literal["PAYER", "PAYEE", "BOTH"] = "BOTH"
    subtotal_key: str | None = None
    accumulate_result_in_subtotal: bool = True
    is_statistical: bool = False
    precondition_key: str | None = None
    rate_book_id: int | None = None


class CalculationTemplatePayload(ApiModel):
    template_code: str
    template_name: str
    description: str | None = None
    status: CalculationTemplateStatus = "DRAFT"
    is_active: bool = True
    steps: list[CalculationTemplateStepPayload] = Field(default_factory=list)
    expected_lock_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_steps(self) -> "CalculationTemplatePayload":
        step_numbers = [step.step_number for step in self.steps]
        if len(step_numbers) != len(set(step_numbers)):
            raise ValueError("Calculation template step numbers must be unique")
        return self


class CalculationTemplateStep(CalculationTemplateStepPayload):
    id: int
    template_id: int
    rate_book_code: str | None = None
    rate_book_name: str | None = None


class CalculationTemplate(ApiModel):
    id: int
    template_code: str
    template_name: str
    description: str | None = None
    status: CalculationTemplateStatus = "DRAFT"
    is_active: bool = True
    steps: list[CalculationTemplateStep] = Field(default_factory=list)
    version_number: int = 1
    supersedes_calculation_template_id: int | None = None
    lock_version: int = 1
    published_at: datetime | None = None
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
    versions: list[CalculationTemplate] = Field(default_factory=list)


class ContractLinePayload(ApiModel):
    charge_component_code: str
    line_number: int | None = Field(default=None, ge=1)
    rate_book_id: int | None = None
    calculation_template_id: int | None = None
    calculation_profile_id: int | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    charge_context: str | None = None
    priority: int = 100
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_validity(self) -> "ContractLinePayload":
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be less than or equal to valid_to")
        return self


class ContractTemplateRoutePayload(ApiModel):
    route_number: int | None = Field(default=None, ge=1)
    calculation_template_id: int
    origin_code: str | None = None
    destination_code: str | None = None
    mode: str | None = None
    equipment_type: str | None = None
    commodity_code: str | None = None
    service_level: str | None = None
    charge_context: str | None = None
    priority: int = 100
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_validity(self) -> "ContractTemplateRoutePayload":
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be less than or equal to valid_to")
        return self


class RateContractPayload(ApiModel):
    contract_number: str
    contract_name: str
    contract_role: Literal["PAYER", "PAYEE"]
    description: str | None = None
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
    selection_priority: int = 100
    default_rate_book_id: int | None = None
    default_calculation_template_id: int | None = None
    margin_type: str | None = None
    margin_value: Decimal | None = None
    minimum_margin_amount: Decimal | None = None
    minimum_margin_percent: Decimal | None = None
    external_reference: str | None = None
    template_routes: list[ContractTemplateRoutePayload] = Field(default_factory=list)
    lines: list[ContractLinePayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_validity(self) -> "RateContractPayload":
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be less than or equal to valid_to")
        return self


class ContractLine(ContractLinePayload):
    id: int
    contract_id: int


class ContractTemplateRoute(ContractTemplateRoutePayload):
    id: int
    contract_id: int


class RateContract(RateContractPayload):
    id: int
    status: str = "DRAFT"
    template_routes: list[ContractTemplateRoute] = Field(default_factory=list)
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
    contract_number: str | None = None
    contract_name: str | None = None
    contract_role: Literal["PAYER", "PAYEE"] | None = None
    description: str | None = None
    payer_party_ref: str | None = None
    payee_party_ref: str | None = None
    party_role_ref: str | None = None
    status: str | None = None
    partner_id: int | None = None
    customer_id: int | None = None
    vendor_id: int | None = None
    forwarder_id: int | None = None
    carrier_id: int | None = None
    company_id: int | None = None
    currency: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    selection_priority: int | None = None
    default_rate_book_id: int | None = None
    default_calculation_template_id: int | None = None
    margin_type: str | None = None
    margin_value: Decimal | None = None
    minimum_margin_amount: Decimal | None = None
    minimum_margin_percent: Decimal | None = None
    external_reference: str | None = None
    template_routes: list[ContractTemplateRoutePayload] | None = None
    lines: list[ContractLinePayload] | None = None


class QuoteRequestCreate(ApiModel):
    request_number: str | None = None
    source_object_type: str = "MANUAL"
    source_object_id: str | None = None
    caller_system_code: str | None = None
    caller_schema_version: str | None = None
    caller_mapping_profile_code: str | None = None
    caller_attributes: dict[str, Any] = Field(default_factory=dict)
    dimension_values: dict[str, Any] = Field(default_factory=dict)
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
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    gross_weight: Decimal | None = Field(default=None, ge=0)
    chargeable_weight: Decimal | None = Field(default=None, ge=0)
    gross_volume_cbm: Decimal | None = Field(default=None, ge=0)
    container_count: Decimal | None = Field(default=None, ge=0)
    package_count: Decimal | None = Field(default=None, ge=0)
    package_type: str | None = None
    requested_service_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    expires_at: datetime | None = None
    margin_rules: dict[str, Any] = Field(default_factory=dict)
    charge_context: str | None = "TRANSPORT"
    context: dict[str, Any] = Field(default_factory=dict)
    calculation_inputs: dict[str, Any] = Field(default_factory=dict)
    component_calculation_inputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    date_values: list[BusinessDateValue] = Field(default_factory=list)

    @field_validator("component_calculation_inputs", mode="before")
    @classmethod
    def normalize_component_calculation_inputs(cls, value: Any) -> dict[str, dict[str, Any]]:
        return _normalize_quote_component_inputs(value)

    @model_validator(mode="after")
    def validate_date_values(self) -> "QuoteRequestCreate":
        _validate_quote_date_values(self.date_values)
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be less than or equal to valid_to")
        return self


class QuoteRequestWorkspaceUpdate(ApiModel):
    request_number: str | None = None
    status: str | None = None
    source_object_type: str | None = None
    source_object_id: str | None = None
    caller_system_code: str | None = None
    caller_schema_version: str | None = None
    caller_mapping_profile_code: str | None = None
    caller_attributes: dict[str, Any] | None = None
    dimension_values: dict[str, Any] | None = None
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
    quantity: Decimal | None = Field(default=None, gt=0)
    gross_weight: Decimal | None = Field(default=None, ge=0)
    chargeable_weight: Decimal | None = Field(default=None, ge=0)
    gross_volume_cbm: Decimal | None = Field(default=None, ge=0)
    container_count: Decimal | None = Field(default=None, ge=0)
    package_count: Decimal | None = Field(default=None, ge=0)
    package_type: str | None = None
    requested_service_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    expires_at: datetime | None = None
    margin_rules: dict[str, Any] | None = None
    charge_context: str | None = None
    context: dict[str, Any] | None = None
    calculation_inputs: dict[str, Any] | None = None
    component_calculation_inputs: dict[str, dict[str, Any]] | None = None
    date_values: list[BusinessDateValue] | None = None

    @field_validator("component_calculation_inputs", mode="before")
    @classmethod
    def normalize_component_calculation_inputs(cls, value: Any) -> dict[str, dict[str, Any]] | None:
        if value is None:
            return None
        return _normalize_quote_component_inputs(value)

    @model_validator(mode="after")
    def validate_date_values(self) -> "QuoteRequestWorkspaceUpdate":
        _validate_quote_date_values(self.date_values)
        return self


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
    source_currency: str | None = None
    source_amount: Decimal | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    fx_rate_id: int | None = None
    exchange_rate_source_code: str | None = None
    exchange_rate_type: Literal["MID", "BUY", "SELL", "CUSTOM"] | None = None
    exchange_rate_method: str | None = None
    quantity_uom: str | None = None
    rate_amount: Decimal | None = None
    quantity: Decimal = Decimal("1")
    calculation_profile_version_id: int | None = None
    calculation_mode: str = "DIRECT"
    calculation_status: str = "CALCULATED"
    calculation_config_snapshot_json: dict[str, Any] | None = None
    calculation_input_snapshot_json: dict[str, Any] | None = None
    allocation_basis: str | None = None
    allocation_profile_id: int | None = None
    allocation_profile_version_id: int | None = None
    allocation_mode: str = "NONE"
    allocation_status: str = "NOT_REQUIRED"
    allocation_config_snapshot_json: dict[str, Any] | None = None
    is_customer_visible: bool = True
    pinned_allocation_snapshot_json: dict[str, Any] | None = None
    effective_allocation_snapshot_json: dict[str, Any] | None = None
    source_contract_id: int | None = None
    source_contract_line_id: int | None = None
    source_contract_template_route_id: int | None = None
    source_rate_book_id: int | None = None
    source_rate_book_entry_id: int | None = None
    source_calculation_template_id: int | None = None
    source_calculation_template_step_id: int | None = None
    is_statistical: bool = False
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
    execution_source_system: str | None = None
    execution_plan_id: str | None = None
    execution_route_id: str | None = None
    execution_source_id: str | None = None
    execution_request_number: str | None = None

    @model_validator(mode="after")
    def validate_execution_identity(self) -> "QuoteAwardRequest":
        identity_values = (
            self.execution_source_system,
            self.execution_plan_id,
            self.execution_route_id,
            self.execution_source_id,
            self.execution_request_number,
        )
        if not any(value and value.strip() for value in identity_values):
            return self
        if not (self.execution_source_system or "").strip():
            raise ValueError("execution_source_system is required with execution identity")
        if not (self.execution_plan_id or "").strip():
            raise ValueError("execution_plan_id is required with execution identity")
        if not ((self.execution_route_id or "").strip() or (self.execution_source_id or "").strip()):
            raise ValueError("execution_route_id or execution_source_id is required")
        return self


class ChargeTargetReferenceSelection(ApiModel):
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"]
    target_object_type: str
    target_object_id: str
    target_reference_snapshot_json: dict[str, Any] | None = None


class ChargeDocumentLineCreate(ApiModel):
    source: str = "MANUAL"
    relationship_role: Literal["PAYER", "PAYEE"]
    line_number: int | None = None
    parent_line_number: int | None = None
    line_role: Literal["CALCULATION", "POSTING"] = "POSTING"
    target_scope_mode: ChargeTargetScopeMode = "ALL_ELIGIBLE"
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"] | None = None
    target_object_type: str | None = None
    target_object_id: str | None = None
    selected_target_references_json: list[ChargeTargetReferenceSelection] | None = None
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
    rate_amount: Decimal | None = None
    currency: str | None = None
    quantity_uom: str | None = None
    calculation_profile_version_id: int | None = None
    calculation_mode: str = "DIRECT"
    calculation_status: str = "CALCULATED"
    calculation_locked_at: datetime | None = None
    calculation_config_snapshot_json: dict[str, Any] | None = None
    calculation_input_snapshot_json: dict[str, Any] | None = None
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
    allocation_mode: str = "NONE"
    allocation_status: str = "NOT_REQUIRED"
    allocation_config_snapshot_json: dict[str, Any] | None = None
    allocation_locked_at: datetime | None = None
    is_customer_visible: bool = True
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
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE", "ROAD_SHIPMENT"] | None = None
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
    source: str = "MANUAL"
    status: str = "ESTIMATED"
    relationship_role: Literal["PAYER", "PAYEE"]
    line_number: int | None = None
    parent_line_id: int | None = None
    parent_line_number: int | None = None
    line_role: Literal["CALCULATION", "POSTING"] = "POSTING"
    target_scope_mode: ChargeTargetScopeMode = "ALL_ELIGIBLE"
    target_level: Literal["HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"] | None = None
    target_object_type: str | None = None
    target_object_id: str | None = None
    selected_target_references_json: list[ChargeTargetReferenceSelection] | None = None
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
    rate_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    approved_amount: Decimal | None = None
    currency: str
    quantity_uom: str | None = None
    calculation_profile_version_id: int | None = None
    calculation_mode: str = "DIRECT"
    calculation_status: str = "CALCULATED"
    calculation_locked_at: datetime | None = None
    calculation_config_snapshot_json: dict[str, Any] | None = None
    calculation_input_snapshot_json: dict[str, Any] | None = None
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
    allocation_mode: str = "NONE"
    allocation_status: str = "NOT_REQUIRED"
    allocation_config_snapshot_json: dict[str, Any] | None = None
    allocation_locked_at: datetime | None = None
    is_customer_visible: bool = True
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
    shipment_scope: Literal["OCEAN_HOUSE", "AIR_HOUSE", "ROAD_SHIPMENT"] | None = None
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


class ChargeDocumentApprovalCheck(ApiModel):
    code: str
    label: str
    passed: bool
    detail: str | None = None


class ChargeDocumentWorkspace(ApiModel):
    document: ChargeDocument
    invoices: list["ChargeInvoice"] = Field(default_factory=list)
    match_results: list["ChargeMatchResult"] = Field(default_factory=list)
    source_quote_option: QuoteOption | None = None
    approval_ready: bool = False
    approval_checks: list[ChargeDocumentApprovalCheck] = Field(default_factory=list)


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
    execution_identity: str | None = None
    execution_source_system: str | None = None
    execution_plan_id: str | None = None
    execution_route_id: str | None = None
    execution_source_id: str | None = None
    execution_request_number: str | None = None
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
    container_count: Decimal | None = Field(default=None, gt=0)
    package_count: Decimal | None = Field(default=None, gt=0)
    chargeable_weight: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    amount: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_idempotency_identity(self) -> "QuoteCommitmentConsumeRequest":
        if not self.source_object_type.strip():
            raise ValueError("source_object_type must not be blank")
        if not (self.source_object_id or "").strip() and not (self.reference_number or "").strip():
            raise ValueError("source_object_id or reference_number is required for idempotent consumption")
        return self


class QuoteCommitmentConsumeResponse(ApiModel):
    commitment: QuoteCommitment
    consumption: QuoteCommitmentConsumption


class QuoteCommitmentCancelRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=1000)


class QuoteCommitmentCancelResponse(ApiModel):
    commitment: QuoteCommitment
    charge_document: ChargeDocument


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
    currency: str | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)


class ChargeInvoiceWorkspaceUpdate(ApiModel):
    invoice_number: str | None = None
    invoice_type: Literal["SUPPLIER", "CUSTOMER"] | None = None
    invoice_date: date | None = None
    currency: str | None = None
    lines: list[dict[str, Any]] | None = None


class ChargeInvoice(ChargeInvoiceCreate):
    id: int
    currency: str = "USD"
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
