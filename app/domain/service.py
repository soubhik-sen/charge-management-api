from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import unicodedata

from fastapi import HTTPException, status

from app.domain.models import (
    ChargeActionResponse,
    ChargeAllocationProfile,
    ChargeAllocationProfileCreate,
    ChargeAllocationProfileListResponse,
    ChargeAllocationProfileUpdate,
    ChargeAllocationProfileVersion,
    ChargeAllocationProfileVersionCreate,
    BusinessDateProfile,
    BusinessDateProfileAssignment,
    BusinessDateProfileAssignmentCreate,
    BusinessDateProfileAssignmentListResponse,
    BusinessDateProfileAssignmentPayload,
    BusinessDateProfileCreate,
    BusinessDateProfileListResponse,
    BusinessDateProfileUpdate,
    BusinessDateProfileStep,
    BusinessDateProfileStepCreate,
    BusinessDateProfileStepPayload,
    BusinessDateProfileVersion,
    BusinessDateProfileVersionCreate,
    BusinessDateProfileVersionPayload,
    ChargeComponent,
    ChargeComponentAlias,
    ChargeComponentAliasListResponse,
    ChargeComponentAliasPayload,
    ChargeComponentListResponse,
    ChargeComponentPayload,
    ChargeDocument,
    ChargeDocumentCreate,
    ChargeDocumentListResponse,
    ChargeDocumentWorkspace,
    ChargeDocumentWorkspaceUpdate,
    ChargeExportResponse,
    ChargeInitializationData,
    ChargeInvoice,
    ChargeInvoiceCreate,
    ChargeInvoiceListResponse,
    ChargeInvoiceWorkspace,
    ChargeInvoiceWorkspaceUpdate,
    ChargeLine,
    ChargeManagementSettings,
    ChargeMatchResult,
    CalculationTemplate,
    CalculationTemplateListResponse,
    CalculationTemplatePayload,
    CalculationTemplateStep,
    CalculationTemplateWorkspace,
    ContractDeterminationResponse,
    ContractLine,
    ContractWorkspace,
    InvoiceMatchResponse,
    QuoteAwardRequest,
    QuoteAwardResponse,
    QuoteOffer,
    QuoteOfferCreate,
    QuoteOfferWithdrawRequest,
    QuoteOfferWorkspace,
    QuoteOfferWorkspaceUpdate,
    QuoteCommitment,
    QuoteCommitmentConsumeRequest,
    QuoteCommitmentConsumeResponse,
    QuoteCommitmentConsumption,
    QuoteCommitmentConsumptionReverseRequest,
    QuoteCommitmentMatchRequest,
    QuoteCommitmentMatchResponse,
    QuoteOption,
    QuoteOptionLine,
    QuoteRequest,
    QuoteRequestCreate,
    QuoteRequestListResponse,
    QuoteRequestWorkspace,
    QuoteRequestWorkspaceUpdate,
    RankResponse,
    RateBook,
    RateBookEntry,
    RateBookListResponse,
    RateBookPayload,
    RateBookWorkspace,
    RateContract,
    RateContractListResponse,
    RateContractPayload,
    RateContractUpdate,
    RateResponse,
    utcnow,
)
from app.domain.seeds import COMMON_BUSINESS_DATE_PROFILES, COMMON_CHARGE_ALLOCATION_PROFILES, COMMON_CHARGE_COMPONENTS

MONEY = Decimal("0.01")
CHARGE_TARGET_LEVELS = {"HEADER", "ITEM", "CONTAINER", "HOUSE", "PO_SCHEDULE_LINE"}
ALLOCATION_PROFILE_SOURCE_LEVELS = {"SHIPMENT", "CONTAINER", "HOUSE"}
ALLOCATION_PROFILE_FINAL_POSTING_LEVELS = {"HOUSE", "PO_SCHEDULE_LINE"}
ALLOCATION_PROFILE_VERSION_STATUSES = {"DRAFT", "PUBLISHED", "RETIRED"}
ALLOCATION_OVERRIDE_MODES = {"INHERIT_PROFILE", "OVERRIDE_PROFILE", "NO_ALLOCATION"}
BUSINESS_DATE_POLICY_MODES = {"LEGACY_BASIS", "INHERIT_PROFILE", "PROFILE_OVERRIDE"}
BUSINESS_DATE_PROFILE_VERSION_STATUSES = {"DRAFT", "PUBLISHED", "RETIRED"}
BUSINESS_DATE_ASSIGNMENT_SCOPE_TYPES = {"GLOBAL", "COMPANY", "CUSTOMER", "VENDOR", "FORWARDER", "CARRIER"}
BUSINESS_DATE_SHIPMENT_SCOPES = {"OCEAN_HOUSE", "AIR_HOUSE"}
BUSINESS_DATE_PURPOSES = {"EXCHANGE_RATE_DATE"}
BUSINESS_DATE_BASIS_KEYS = {
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
}
BUSINESS_DATE_BASIS_KEY_CANDIDATES: dict[str, tuple[str, ...]] = {
    "DOCUMENT_DATE": ("document_date", "charge_date"),
    "MANUAL_LINE_DATE": ("charge_date",),
    "SHIPPED_ON_BOARD_DATE": (
        "shipped_on_board_date",
        "shipped_on_board_at",
        "loaded_on_vessel_date",
        "loaded_on_board_date",
        "business_dates.shipped_on_board_date",
        "shipment_business_dates.shipped_on_board_date",
    ),
    "SHIPMENT_ACTUAL_DEPARTURE_DATE": (
        "shipment_actual_departure_date",
        "actual_departure_date",
        "departure_date",
        "departure_at",
        "business_dates.shipment_actual_departure_date",
        "shipment_business_dates.shipment_actual_departure_date",
    ),
    "SHIPMENT_PLANNED_DEPARTURE_DATE": (
        "shipment_planned_departure_date",
        "estimated_departure_date",
        "planned_departure_date",
        "business_dates.shipment_planned_departure_date",
        "shipment_business_dates.shipment_planned_departure_date",
    ),
    "SHIPMENT_ARRIVAL_DATE": (
        "shipment_arrival_date",
        "arrival_date",
        "actual_arrival_date",
        "estimated_arrival_date",
        "business_dates.shipment_arrival_date",
        "shipment_business_dates.shipment_arrival_date",
    ),
    "HOUSE_BILL_ISSUE_DATE": (
        "house_bill_issue_date",
        "awb_execution_date",
        "awb_executed_date",
        "business_dates.house_bill_issue_date",
        "house_bill_business_dates.house_bill_issue_date",
    ),
    "ACTUAL_FLIGHT_DEPARTURE_DATE": (
        "actual_flight_departure_date",
        "flight_departure_date",
        "departure_date",
        "departure_at",
        "business_dates.actual_flight_departure_date",
        "shipment_business_dates.actual_flight_departure_date",
    ),
    "AWB_EXECUTION_DATE": (
        "awb_execution_date",
        "awb_executed_date",
        "air_waybill_execution_date",
        "business_dates.awb_execution_date",
        "shipment_business_dates.awb_execution_date",
    ),
    "ESTIMATED_FLIGHT_DEPARTURE_DATE": (
        "estimated_flight_departure_date",
        "planned_flight_departure_date",
        "estimated_departure_date",
        "business_dates.estimated_flight_departure_date",
        "shipment_business_dates.estimated_flight_departure_date",
    ),
}
LEGACY_BASIS_TO_BUSINESS_KEYS: dict[str, tuple[str, ...]] = {
    "DOCUMENT_DATE": ("DOCUMENT_DATE",),
    "SHIPMENT_DEPARTURE_DATE": ("SHIPMENT_ACTUAL_DEPARTURE_DATE", "SHIPMENT_PLANNED_DEPARTURE_DATE"),
    "SHIPMENT_ARRIVAL_DATE": ("SHIPMENT_ARRIVAL_DATE",),
    "HOUSE_BILL_ISSUE_DATE": ("HOUSE_BILL_ISSUE_DATE",),
    "MANUAL": ("MANUAL_LINE_DATE",),
}


def money(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(MONEY, rounding=ROUND_HALF_UP)


def dec(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or "0"))


def _clean_optional(value: str | None) -> str | None:
    cleaned = value.strip() if isinstance(value, str) else value
    return cleaned or None


def _charge_date_basis(value: Any) -> str:
    cleaned = value.strip().upper() if isinstance(value, str) else ""
    return cleaned or "DOCUMENT_DATE"


def _business_date_policy_mode(value: Any) -> str:
    cleaned = value.strip().upper() if isinstance(value, str) else ""
    return cleaned if cleaned in BUSINESS_DATE_POLICY_MODES else "LEGACY_BASIS"


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return date.fromisoformat(cleaned[:10])
        except ValueError:
            return None
    return None


def _alias_normalized_label(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(
        "".join(char if char.isalnum() else " " for char in without_marks.upper()).split()
    )


def _payload_line_number(payload: Any, *, default: int) -> int:
    line_number = getattr(payload, "line_number", None) or default
    line_number = int(line_number)
    if line_number <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Charge line_number must be greater than zero.")
    return line_number


def _validate_target_payload(payload: Any) -> None:
    target_level = _clean_optional(getattr(payload, "target_level", None))
    target_object_type = _clean_optional(getattr(payload, "target_object_type", None))
    target_object_id = _clean_optional(getattr(payload, "target_object_id", None))
    has_target_object = target_object_type is not None or target_object_id is not None
    if target_level is not None and target_level not in CHARGE_TARGET_LEVELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported charge target_level: {target_level}")
    if target_level is not None and (target_object_type is None or target_object_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Charge target_level requires target_object_type and target_object_id.",
        )
    if has_target_object and target_level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Charge target_object_type and target_object_id require target_level.",
        )


def _charge_line_sort_key(line: ChargeLine) -> tuple[int, int, int]:
    return (1 if line.line_number is None else 0, int(line.line_number or 0), int(line.id))


def _document_totals(lines: list[ChargeLine]) -> tuple[Decimal, Decimal]:
    posting_lines = [line for line in lines if line.line_role == "POSTING"]
    payer_total = money(
        sum((line.expected_amount for line in posting_lines if line.relationship_role == "PAYER"), Decimal("0"))
    )
    payee_total = money(
        sum((line.expected_amount for line in posting_lines if line.relationship_role == "PAYEE"), Decimal("0"))
    )
    return payer_total, payee_total


class InMemoryChargeRepository:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._ids: defaultdict[str, int] = defaultdict(int)
        self.allocation_profiles: dict[int, ChargeAllocationProfile] = {}
        self.allocation_profile_versions: dict[int, ChargeAllocationProfileVersion] = {}
        self.business_date_profiles: dict[int, BusinessDateProfile] = {}
        self.business_date_profile_versions: dict[int, BusinessDateProfileVersion] = {}
        self.business_date_profile_assignments: dict[int, BusinessDateProfileAssignment] = {}
        self.components: dict[int, ChargeComponent] = {}
        self.components_by_code: dict[str, ChargeComponent] = {}
        self.component_aliases: dict[int, ChargeComponentAlias] = {}
        self.rate_books: dict[int, RateBook] = {}
        self.calculation_templates: dict[int, CalculationTemplate] = {}
        self.contracts: dict[int, RateContract] = {}
        self.quote_requests: dict[int, QuoteRequest] = {}
        self.quote_offers: dict[int, QuoteOffer] = {}
        self.quote_options: dict[int, QuoteOption] = {}
        self.quote_commitments: dict[int, QuoteCommitment] = {}
        self.quote_commitment_consumptions: dict[int, QuoteCommitmentConsumption] = {}
        self.documents: dict[int, ChargeDocument] = {}
        self.invoices: dict[int, ChargeInvoice] = {}
        self.match_results: dict[int, ChargeMatchResult] = {}
        self.exports: dict[str, ChargeExportResponse] = {}
        self.quotation_policy = "OPTIONAL"
        self.quote_acceptance_mode = "CUSTOMER_ACCEPTANCE"
        self.provider_cost_layer_enabled = False
        self.seed_business_date_profiles()
        self.seed_allocation_profiles()
        self.seed_components()

    def next_id(self, bucket: str) -> int:
        self._ids[bucket] += 1
        return self._ids[bucket]

    def seed_components(self) -> None:
        for row in COMMON_CHARGE_COMPONENTS:
            code = str(row["component_code"])
            component = ChargeComponent(
                id=self.next_id("component"),
                component_code=code,
                component_name=str(row["component_name"]),
                category=str(row["category"]),
                default_party_role=str(row["default_party_role"]),  # type: ignore[arg-type]
                charge_context=str(row["charge_context"]),
                calculation_basis=str(row["calculation_basis"]),
                charge_date_basis=_charge_date_basis(row.get("charge_date_basis")),
                business_date_policy_mode="LEGACY_BASIS",
                is_tax=bool(row.get("is_tax", False)),
            )
            self.components[component.id] = component
            self.components_by_code[code] = component

    def seed_business_date_profiles(self) -> None:
        for row in COMMON_BUSINESS_DATE_PROFILES:
            profile_id = self.next_id("business_date_profile")
            version_id = self.next_id("business_date_profile_version")
            steps: list[BusinessDateProfileStep] = []
            for step in row.get("steps", ()):  # type: ignore[assignment]
                step_id = self.next_id("business_date_profile_step")
                steps.append(
                    BusinessDateProfileStep(
                        id=step_id,
                        version_id=version_id,
                        step_number=int(step["step_number"]),
                        date_key=str(step["date_key"]).strip().upper(),
                        notes=_clean_optional(step.get("notes")),  # type: ignore[arg-type]
                    )
                )
            version = BusinessDateProfileVersion(
                id=version_id,
                profile_id=profile_id,
                version_number=int(row.get("version_number", 1)),
                status="PUBLISHED",
                notes=_clean_optional(row.get("description")),  # type: ignore[arg-type]
                published_at=utcnow(),
                steps=sorted(steps, key=lambda item: (item.step_number, item.id)),
            )
            profile = BusinessDateProfile(
                id=profile_id,
                profile_code=str(row["profile_code"]),
                profile_name=str(row["profile_name"]),
                description=_clean_optional(row.get("description")),  # type: ignore[arg-type]
                published_version_id=version.id,
                published_version_number=version.version_number,
                versions=[version],
            )
            self.business_date_profiles[profile.id] = profile
            self.business_date_profile_versions[version.id] = version

    def seed_allocation_profiles(self) -> None:
        for row in COMMON_CHARGE_ALLOCATION_PROFILES:
            profile_id = self.next_id("allocation_profile")
            version_id = self.next_id("allocation_profile_version")
            version = ChargeAllocationProfileVersion(
                id=version_id,
                profile_id=profile_id,
                version_number=int(row["version_number"]),
                status="PUBLISHED",
                source_level=str(row["source_level"]),
                source_to_house_driver=_clean_optional(row.get("source_to_house_driver")),  # type: ignore[arg-type]
                house_to_item_driver=_clean_optional(row.get("house_to_item_driver")),  # type: ignore[arg-type]
                final_posting_level=str(row["final_posting_level"]),
                default_quantity_uom=_clean_optional(row.get("default_quantity_uom")),  # type: ignore[arg-type]
                settings_json=dict(row.get("settings_json") or {}),
                notes=_clean_optional(row.get("notes")),  # type: ignore[arg-type]
                published_at=utcnow(),
            )
            profile = ChargeAllocationProfile(
                id=profile_id,
                profile_code=str(row["profile_code"]),
                profile_name=str(row["profile_name"]),
                published_version_id=version.id,
                published_version_number=version.version_number,
                versions=[version],
            )
            self.allocation_profiles[profile.id] = profile
            self.allocation_profile_versions[version.id] = version


class ChargeManagementService:
    def __init__(self, repository: InMemoryChargeRepository | None = None) -> None:
        self.repository = repository or InMemoryChargeRepository()

    def initialization_data(self) -> ChargeInitializationData:
        return ChargeInitializationData(
            components=sorted(
                self.repository.components.values(),
                key=lambda row: row.component_code,
            ),
            settings=ChargeManagementSettings(
                quotation_policy=self.repository.quotation_policy,  # type: ignore[arg-type]
                quote_acceptance_mode=self.repository.quote_acceptance_mode,  # type: ignore[arg-type]
                provider_cost_layer_enabled=self.repository.provider_cost_layer_enabled,
            ),
        )

    def list_allocation_profiles(
        self,
        *,
        search: str | None = None,
        source_level: str | None = None,
        status_filter: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChargeAllocationProfileListResponse:
        rows = list(self.repository.allocation_profiles.values())
        if source_level:
            normalized_shape = source_level.strip().upper()
            rows = [
                row
                for row in rows
                if any(version.source_level == normalized_shape for version in row.versions)
            ]
        if status_filter:
            normalized_status = status_filter.strip().upper()
            rows = [
                row
                for row in rows
                if any(version.status == normalized_status for version in row.versions)
            ]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.profile_code.upper()
                or normalized in row.profile_name.upper()
                or any(normalized in version.source_level.upper() for version in row.versions)
            ]
        rows.sort(key=lambda row: (row.profile_code, row.id))
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return ChargeAllocationProfileListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_allocation_profile(self, profile_id: int) -> ChargeAllocationProfile:
        return self._require_allocation_profile(profile_id)

    def update_allocation_profile(
        self,
        profile_id: int,
        payload: ChargeAllocationProfileUpdate,
    ) -> ChargeAllocationProfile:
        profile = self._require_allocation_profile(profile_id)
        code = payload.profile_code.strip().upper()
        name = payload.profile_name.strip()
        if not code or not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Allocation profile_code and profile_name are required.",
            )
        if any(
            row.profile_code == code and row.id != profile.id
            for row in self.repository.allocation_profiles.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Allocation profile_code already exists.",
            )
        profile.profile_code = code
        profile.profile_name = name
        profile.updated_at = utcnow()
        return profile

    def create_allocation_profile(self, payload: ChargeAllocationProfileCreate) -> ChargeAllocationProfile:
        code = payload.profile_code.strip().upper()
        name = payload.profile_name.strip()
        if not code or not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="profile_code and profile_name are required",
            )
        if any(row.profile_code == code for row in self.repository.allocation_profiles.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charge allocation profile code already exists",
            )
        profile_id = self.repository.next_id("allocation_profile")
        version = self._allocation_profile_version_from_payload(
            profile_id=profile_id,
            payload=payload.initial_version,
            version_number=1,
        )
        profile = ChargeAllocationProfile(
            id=profile_id,
            profile_code=code,
            profile_name=name,
            versions=[version],
        )
        self.repository.allocation_profiles[profile.id] = profile
        self.repository.allocation_profile_versions[version.id] = version
        return profile

    def create_allocation_profile_version(
        self,
        profile_id: int,
        payload: ChargeAllocationProfileVersionCreate,
    ) -> ChargeAllocationProfile:
        profile = self._require_allocation_profile(profile_id)
        next_version_number = max((row.version_number for row in profile.versions), default=0) + 1
        version = self._allocation_profile_version_from_payload(
            profile_id=profile.id,
            payload=payload,
            version_number=next_version_number,
        )
        profile.versions = sorted([*profile.versions, version], key=lambda row: (row.version_number, row.id))
        profile.updated_at = utcnow()
        self.repository.allocation_profile_versions[version.id] = version
        return profile

    def update_allocation_profile_version(
        self,
        version_id: int,
        payload: ChargeAllocationProfileVersionCreate,
    ) -> ChargeAllocationProfileVersion:
        version = self._require_allocation_profile_version(version_id)
        if version.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Published allocation profile versions are immutable; create a new version instead.",
            )
        normalized = self._normalized_allocation_profile_version_payload(payload)
        for key, value in normalized.items():
            setattr(version, key, value)
        version.updated_at = utcnow()
        profile = self._require_allocation_profile(version.profile_id)
        profile.updated_at = utcnow()
        return version

    def publish_allocation_profile_version(self, version_id: int) -> ChargeAllocationProfile:
        version = self._require_allocation_profile_version(version_id)
        profile = self._require_allocation_profile(version.profile_id)
        for existing in profile.versions:
            if existing.id == version.id:
                existing.status = "PUBLISHED"
                existing.published_at = utcnow()
                existing.updated_at = utcnow()
            elif existing.status == "PUBLISHED":
                existing.status = "RETIRED"
                existing.updated_at = utcnow()
        profile.published_version_id = version.id
        profile.published_version_number = version.version_number
        profile.updated_at = utcnow()
        return profile

    def list_business_date_profiles(
        self,
        *,
        search: str | None = None,
        status_filter: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> BusinessDateProfileListResponse:
        rows = list(self.repository.business_date_profiles.values())
        if status_filter:
            normalized_status = status_filter.strip().upper()
            rows = [
                row
                for row in rows
                if any(version.status == normalized_status for version in row.versions)
            ]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.profile_code.upper()
                or normalized in row.profile_name.upper()
                or (row.description is not None and normalized in row.description.upper())
                or any(normalized in version.notes.upper() for version in row.versions if version.notes)
                or any(normalized in step.date_key.upper() for version in row.versions for step in version.steps)
            ]
        rows.sort(key=lambda row: (row.profile_code, row.id))
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return BusinessDateProfileListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_business_date_profile(self, profile_id: int) -> BusinessDateProfile:
        return self._require_business_date_profile(profile_id)

    def create_business_date_profile(self, payload: BusinessDateProfileCreate) -> BusinessDateProfile:
        code = payload.profile_code.strip().upper()
        name = payload.profile_name.strip()
        if not code or not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="profile_code and profile_name are required")
        if any(row.profile_code == code for row in self.repository.business_date_profiles.values()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business date profile code already exists")
        profile_id = self.repository.next_id("business_date_profile")
        version = self._business_date_profile_version_from_payload(
            profile_id=profile_id,
            payload=payload.initial_version,
            version_number=1,
        )
        profile = BusinessDateProfile(
            id=profile_id,
            profile_code=code,
            profile_name=name,
            description=_clean_optional(payload.description),
            versions=[version],
        )
        self.repository.business_date_profiles[profile.id] = profile
        self.repository.business_date_profile_versions[version.id] = version
        return profile

    def update_business_date_profile(
        self,
        profile_id: int,
        payload: BusinessDateProfileUpdate,
    ) -> BusinessDateProfile:
        profile = self._require_business_date_profile(profile_id)
        code = payload.profile_code.strip().upper()
        name = payload.profile_name.strip()
        if not code or not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="profile_code and profile_name are required")
        if any(row.profile_code == code and row.id != profile.id for row in self.repository.business_date_profiles.values()):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business date profile code already exists")
        profile.profile_code = code
        profile.profile_name = name
        profile.description = _clean_optional(payload.description)
        profile.updated_at = utcnow()
        return profile

    def create_business_date_profile_version(
        self,
        profile_id: int,
        payload: BusinessDateProfileVersionCreate,
    ) -> BusinessDateProfile:
        profile = self._require_business_date_profile(profile_id)
        next_version_number = max((row.version_number for row in profile.versions), default=0) + 1
        version = self._business_date_profile_version_from_payload(
            profile_id=profile.id,
            payload=payload,
            version_number=next_version_number,
        )
        profile.versions = sorted([*profile.versions, version], key=lambda row: (row.version_number, row.id))
        profile.updated_at = utcnow()
        self.repository.business_date_profile_versions[version.id] = version
        return profile

    def update_business_date_profile_version(
        self,
        version_id: int,
        payload: BusinessDateProfileVersionCreate,
    ) -> BusinessDateProfileVersion:
        version = self._require_business_date_profile_version(version_id)
        if version.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Published business date profile versions are immutable; create a new version instead.",
            )
        normalized = self._normalized_business_date_profile_version_payload(payload)
        version.notes = normalized["notes"]
        version.steps = [
            BusinessDateProfileStep(
                id=self.repository.next_id("business_date_profile_step"),
                version_id=version.id,
                step_number=int(step_payload["step_number"]),
                date_key=str(step_payload["date_key"]),
                notes=_clean_optional(step_payload.get("notes")),
            )
            for step_payload in normalized["steps"]
        ]
        version.updated_at = utcnow()
        profile = self._require_business_date_profile(version.profile_id)
        profile.updated_at = utcnow()
        return version

    def publish_business_date_profile_version(self, version_id: int) -> BusinessDateProfile:
        version = self._require_business_date_profile_version(version_id)
        profile = self._require_business_date_profile(version.profile_id)
        for existing in profile.versions:
            if existing.id == version.id:
                existing.status = "PUBLISHED"
                existing.published_at = utcnow()
                existing.updated_at = utcnow()
            elif existing.status == "PUBLISHED":
                existing.status = "RETIRED"
                existing.updated_at = utcnow()
        profile.published_version_id = version.id
        profile.published_version_number = version.version_number
        profile.updated_at = utcnow()
        return profile

    def list_business_date_profile_assignments(
        self,
        profile_id: int,
        *,
        scope_type: str | None = None,
        scope_id: int | None = None,
        shipment_scope: str | None = None,
        business_purpose: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> BusinessDateProfileAssignmentListResponse:
        profile = self._require_business_date_profile(profile_id)
        rows = [row for row in self.repository.business_date_profile_assignments.values() if row.profile_id == profile.id]
        if scope_type:
            normalized_scope_type = scope_type.strip().upper()
            rows = [row for row in rows if row.scope_type == normalized_scope_type]
        if scope_id is not None:
            rows = [row for row in rows if row.scope_id == int(scope_id)]
        if shipment_scope:
            normalized_shipment_scope = shipment_scope.strip().upper()
            rows = [row for row in rows if row.shipment_scope == normalized_shipment_scope]
        if business_purpose:
            normalized_business_purpose = business_purpose.strip().upper()
            rows = [row for row in rows if row.business_purpose == normalized_business_purpose]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        rows.sort(
            key=lambda row: (
                row.priority,
                row.scope_type,
                -1 if row.scope_id is None else int(row.scope_id),
                row.shipment_scope,
                row.business_purpose,
                row.id,
            )
        )
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return BusinessDateProfileAssignmentListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def create_business_date_profile_assignment(
        self,
        profile_id: int,
        payload: BusinessDateProfileAssignmentCreate,
    ) -> BusinessDateProfileAssignment:
        profile = self._require_business_date_profile(profile_id)
        self._require_published_business_date_profile_version(profile)
        assignment = self._business_date_profile_assignment_from_payload(
            profile_id=profile.id,
            payload=payload,
            assignment_id=self.repository.next_id("business_date_profile_assignment"),
        )
        if self._business_date_profile_assignment_exists(assignment):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A business date profile assignment already exists for that owner, shipment scope, and purpose.",
            )
        self.repository.business_date_profile_assignments[assignment.id] = assignment
        profile.updated_at = utcnow()
        return assignment

    def update_business_date_profile_assignment(
        self,
        assignment_id: int,
        payload: BusinessDateProfileAssignmentCreate,
    ) -> BusinessDateProfileAssignment:
        assignment = self._require_business_date_profile_assignment(assignment_id)
        profile = self._require_business_date_profile(assignment.profile_id)
        self._require_published_business_date_profile_version(profile)
        updated = self._business_date_profile_assignment_from_payload(
            profile_id=assignment.profile_id,
            payload=payload,
            assignment_id=assignment.id,
        )
        if self._business_date_profile_assignment_exists(updated, ignore_assignment_id=assignment.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A business date profile assignment already exists for that owner, shipment scope, and purpose.",
            )
        for key, value in updated.model_dump().items():
            if key in {"id", "profile_id", "created_at"}:
                continue
            setattr(assignment, key, value)
        assignment.updated_at = utcnow()
        profile.updated_at = utcnow()
        return assignment

    def delete_business_date_profile_assignment(self, assignment_id: int) -> BusinessDateProfileAssignment:
        assignment = self._require_business_date_profile_assignment(assignment_id)
        deleted = assignment.model_copy(deep=True)
        self.repository.business_date_profile_assignments.pop(assignment.id, None)
        profile = self.repository.business_date_profiles.get(assignment.profile_id)
        if profile is not None:
            profile.updated_at = utcnow()
        return deleted

    def list_components(
        self,
        *,
        active_only: bool | None = None,
        category: str | None = None,
        calculation_basis: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChargeComponentListResponse:
        rows = list(self.repository.components.values())
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if category:
            normalized_category = category.strip().upper()
            rows = [row for row in rows if row.category.upper() == normalized_category]
        if calculation_basis:
            normalized_basis = calculation_basis.strip().upper()
            rows = [row for row in rows if row.calculation_basis.upper() == normalized_basis]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.component_code.upper()
                or normalized in row.component_name.upper()
                or normalized in row.category.upper()
            ]
        rows.sort(key=lambda row: (row.category, row.component_name, row.component_code, row.id))
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 500)
        return ChargeComponentListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def create_component(self, payload: ChargeComponentPayload) -> ChargeComponent:
        code = payload.component_code.strip().upper()
        if not code or not payload.component_name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="component_code and component_name are required")
        if code in self.repository.components_by_code:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Charge component code already exists")
        business_date_policy_mode, business_date_profile_id = self._resolve_business_date_component_reference(
            payload.business_date_policy_mode,
            payload.business_date_profile_id,
        )
        allocation_profile_id, allocation_profile_version_id, _, _ = self._resolve_allocation_profile_reference(
            payload.allocation_profile_id,
            payload.allocation_profile_version_id,
        )
        component = ChargeComponent(
            **payload.model_dump(
                exclude={
                    "component_code",
                    "component_name",
                    "category",
                    "charge_context",
                    "calculation_basis",
                    "charge_date_basis",
                    "business_date_policy_mode",
                    "business_date_profile_id",
                    "allocation_profile_id",
                    "allocation_profile_version_id",
                }
            ),
            id=self.repository.next_id("component"),
            component_code=code,
            component_name=payload.component_name.strip(),
            category=payload.category.strip().upper() or "ACCESSORIAL",
            charge_context=payload.charge_context.strip().upper() or "TRANSPORT",
            calculation_basis=payload.calculation_basis.strip().upper() or "FLAT",
            charge_date_basis=_charge_date_basis(payload.charge_date_basis),
            business_date_policy_mode=business_date_policy_mode,
            business_date_profile_id=business_date_profile_id,
            allocation_profile_id=allocation_profile_id,
            allocation_profile_version_id=allocation_profile_version_id,
        )
        self.repository.components[component.id] = component
        self.repository.components_by_code[component.component_code] = component
        return component

    def update_component(self, component_id: int, payload: ChargeComponentPayload) -> ChargeComponent:
        existing = self._require_component_by_id(component_id)
        code = payload.component_code.strip().upper()
        if not code or not payload.component_name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="component_code and component_name are required")
        duplicate = self.repository.components_by_code.get(code)
        if duplicate is not None and duplicate.id != existing.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Charge component code already exists")
        business_date_policy_mode, business_date_profile_id = self._resolve_business_date_component_reference(
            payload.business_date_policy_mode,
            payload.business_date_profile_id,
        )
        if existing.component_code != code:
            self.repository.components_by_code.pop(existing.component_code, None)
        existing.component_code = code
        existing.component_name = payload.component_name.strip()
        existing.category = payload.category.strip().upper() or "ACCESSORIAL"
        existing.default_party_role = payload.default_party_role
        existing.charge_context = payload.charge_context.strip().upper() or "TRANSPORT"
        existing.calculation_basis = payload.calculation_basis.strip().upper() or "FLAT"
        existing.charge_date_basis = _charge_date_basis(payload.charge_date_basis)
        existing.business_date_policy_mode = business_date_policy_mode
        existing.business_date_profile_id = business_date_profile_id
        (
            existing.allocation_profile_id,
            existing.allocation_profile_version_id,
            _,
            _,
        ) = self._resolve_allocation_profile_reference(
            payload.allocation_profile_id,
            payload.allocation_profile_version_id,
        )
        existing.is_tax = bool(payload.is_tax)
        existing.is_active = bool(payload.is_active)
        self.repository.components_by_code[existing.component_code] = existing
        return existing

    def delete_component(self, component_id: int) -> ChargeComponent:
        existing = self._require_component_by_id(component_id)
        existing.is_active = False
        return existing

    def list_component_aliases(
        self,
        *,
        document_kind: str | None = None,
        template_key: str | None = None,
        customer_id: int | None = None,
        forwarder_id: int | None = None,
        transport_mode: str | None = None,
        charge_component_id: int | None = None,
        active_only: bool | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChargeComponentAliasListResponse:
        rows = list(self.repository.component_aliases.values())
        if document_kind:
            normalized_kind = document_kind.strip().upper()
            rows = [row for row in rows if row.document_kind.upper() == normalized_kind]
        if template_key is not None:
            normalized_template = _clean_optional(template_key)
            rows = [row for row in rows if row.template_key == normalized_template]
        if customer_id is not None:
            rows = [row for row in rows if row.customer_id == int(customer_id)]
        if forwarder_id is not None:
            rows = [row for row in rows if row.forwarder_id == int(forwarder_id)]
        if transport_mode:
            normalized_mode = transport_mode.strip().upper()
            rows = [row for row in rows if row.transport_mode == normalized_mode]
        if charge_component_id is not None:
            rows = [row for row in rows if row.charge_component_id == int(charge_component_id)]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if search:
            normalized = _alias_normalized_label(search)
            raw = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.normalized_label
                or raw in row.raw_label.upper()
                or raw in row.component_code.upper()
                or raw in row.component_name.upper()
            ]
        rows.sort(
            key=lambda row: (
                row.document_kind,
                row.template_key or "",
                row.customer_id or 0,
                row.forwarder_id or 0,
                row.transport_mode or "",
                row.priority,
                row.raw_label,
                row.id,
            )
        )
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return ChargeComponentAliasListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def create_component_alias(self, payload: ChargeComponentAliasPayload) -> ChargeComponentAlias:
        component = self._require_component_by_id(payload.charge_component_id)
        alias = self._alias_from_payload(payload, component=component, alias_id=self.repository.next_id("component_alias"))
        if self._alias_key_exists(alias):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Charge component alias already exists")
        self.repository.component_aliases[alias.id] = alias
        return alias

    def update_component_alias(
        self,
        alias_id: int,
        payload: ChargeComponentAliasPayload,
    ) -> ChargeComponentAlias:
        existing = self._require_component_alias(alias_id)
        component = self._require_component_by_id(payload.charge_component_id)
        updated = self._alias_from_payload(payload, component=component, alias_id=existing.id)
        updated.created_at = existing.created_at
        updated.updated_at = utcnow()
        if self._alias_key_exists(updated, ignore_alias_id=existing.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Charge component alias already exists")
        self.repository.component_aliases[existing.id] = updated
        return updated

    def delete_component_alias(self, alias_id: int) -> ChargeComponentAlias:
        alias = self._require_component_alias(alias_id)
        alias.is_active = False
        alias.updated_at = utcnow()
        return alias

    def create_rate_book(self, payload: RateBookPayload) -> RateBook:
        rate_book_id = self.repository.next_id("rate_book")
        entries: list[RateBookEntry] = []
        for entry in payload.entries:
            self._require_component(entry.charge_component_code)
            allocation_profile_id, allocation_profile_version_id, _, _ = self._resolve_allocation_profile_reference(
                entry.allocation_profile_id,
                entry.allocation_profile_version_id,
            )
            entries.append(
                RateBookEntry(
                    **entry.model_dump(exclude={"allocation_profile_id", "allocation_profile_version_id"}),
                    id=self.repository.next_id("rate_book_entry"),
                    rate_book_id=rate_book_id,
                    allocation_profile_id=allocation_profile_id,
                    allocation_profile_version_id=allocation_profile_version_id,
                )
            )
        row = RateBook(
            id=rate_book_id,
            rate_book_code=payload.rate_book_code,
            rate_book_name=payload.rate_book_name,
            currency=payload.currency,
            entries=entries,
        )
        self.repository.rate_books[row.id] = row
        return row

    def list_rate_books(
        self,
        *,
        search: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> RateBookListResponse:
        rows = list(self.repository.rate_books.values())
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.rate_book_code.upper()
                or normalized in row.rate_book_name.upper()
                or normalized in row.currency.upper()
            ]
        rows.sort(key=lambda row: (row.rate_book_code, row.id))
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return RateBookListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_rate_book_workspace(self, rate_book_id: int) -> RateBookWorkspace:
        rate_book = self._require_rate_book(rate_book_id)
        return RateBookWorkspace(rate_book=rate_book, entries=rate_book.entries)

    def update_rate_book_workspace(
        self,
        rate_book_id: int,
        payload: RateBookPayload,
    ) -> RateBookWorkspace:
        row = self._require_rate_book(rate_book_id)
        entries: list[RateBookEntry] = []
        for entry in payload.entries:
            self._require_component(entry.charge_component_code)
            allocation_profile_id, allocation_profile_version_id, _, _ = self._resolve_allocation_profile_reference(
                entry.allocation_profile_id,
                entry.allocation_profile_version_id,
            )
            entries.append(
                RateBookEntry(
                    **entry.model_dump(exclude={"allocation_profile_id", "allocation_profile_version_id"}),
                    id=self.repository.next_id("rate_book_entry"),
                    rate_book_id=row.id,
                    allocation_profile_id=allocation_profile_id,
                    allocation_profile_version_id=allocation_profile_version_id,
                )
            )
        row.rate_book_code = payload.rate_book_code
        row.rate_book_name = payload.rate_book_name
        row.currency = payload.currency
        row.entries = entries
        return self.get_rate_book_workspace(rate_book_id)

    def create_calculation_template(
        self,
        payload: CalculationTemplatePayload,
    ) -> CalculationTemplate:
        if any(
            row.template_code.upper() == payload.template_code.upper()
            for row in self.repository.calculation_templates.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Calculation template code already exists",
            )
        template_id = self.repository.next_id("calculation_template")
        steps = self._template_steps_from_payload(template_id, payload)
        row = CalculationTemplate(
            **payload.model_dump(exclude={"steps", "template_code"}),
            id=template_id,
            template_code=payload.template_code.upper(),
            steps=steps,
        )
        self.repository.calculation_templates[row.id] = row
        return row

    def list_calculation_templates(
        self,
        *,
        status_filter: str | None = None,
        search: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CalculationTemplateListResponse:
        rows = list(self.repository.calculation_templates.values())
        if status_filter:
            rows = [
                row
                for row in rows
                if row.status.upper() == status_filter.upper()
            ]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.template_code.upper()
                or normalized in row.template_name.upper()
                or normalized in row.status.upper()
            ]
        rows.sort(key=lambda row: (row.template_code, row.id))
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return CalculationTemplateListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_calculation_template_workspace(
        self,
        calculation_template_id: int,
    ) -> CalculationTemplateWorkspace:
        template = self._require_calculation_template(calculation_template_id)
        return CalculationTemplateWorkspace(template=template, steps=template.steps)

    def update_calculation_template_workspace(
        self,
        calculation_template_id: int,
        payload: CalculationTemplatePayload,
    ) -> CalculationTemplateWorkspace:
        row = self._require_calculation_template(calculation_template_id)
        if any(
            other.id != row.id
            and other.template_code.upper() == payload.template_code.upper()
            for other in self.repository.calculation_templates.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Calculation template code already exists",
            )
        row.template_code = payload.template_code.upper()
        row.template_name = payload.template_name
        row.description = payload.description
        row.status = payload.status
        row.is_active = payload.is_active
        row.steps = self._template_steps_from_payload(row.id, payload)
        row.updated_at = utcnow()
        return self.get_calculation_template_workspace(calculation_template_id)

    def create_contract(self, payload: RateContractPayload) -> RateContract:
        contract_id = self.repository.next_id("contract")
        if payload.default_rate_book_id is not None:
            self._require_rate_book(payload.default_rate_book_id)
        if payload.default_calculation_template_id is not None:
            self._require_calculation_template(payload.default_calculation_template_id)
        lines = [
            self._contract_line_from_payload(contract_id=contract_id, line_payload=line)
            for line in payload.lines
        ]
        for line in lines:
            self._require_component(line.charge_component_code)
            if line.rate_book_id is not None:
                self._require_rate_book(line.rate_book_id)
            if line.calculation_template_id is not None:
                self._require_calculation_template(line.calculation_template_id)
        row = RateContract(
            **payload.model_dump(exclude={"lines"}),
            id=contract_id,
            lines=lines,
        )
        self.repository.contracts[row.id] = row
        return row

    def list_contracts(
        self,
        *,
        contract_role: str | None = None,
        status_filter: str | None = None,
        customer_id: int | None = None,
        forwarder_id: int | None = None,
        carrier_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> RateContractListResponse:
        rows = list(self.repository.contracts.values())
        if contract_role:
            rows = [
                row
                for row in rows
                if row.contract_role.upper() == contract_role.upper()
            ]
        if status_filter:
            rows = [
                row
                for row in rows
                if row.status.upper() == status_filter.upper()
            ]
        if customer_id is not None:
            rows = [row for row in rows if row.customer_id == customer_id]
        if forwarder_id is not None:
            rows = [row for row in rows if row.forwarder_id == forwarder_id]
        if carrier_id is not None:
            rows = [row for row in rows if row.carrier_id == carrier_id]
        rows.sort(key=lambda row: (row.updated_at, row.id), reverse=True)
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return RateContractListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_contract_workspace(self, contract_id: int) -> ContractWorkspace:
        contract = self._require_contract(contract_id)
        return ContractWorkspace(
            contract=contract,
            rate_books=sorted(
                self.repository.rate_books.values(),
                key=lambda row: row.id,
            ),
        )

    def update_contract_workspace(
        self,
        contract_id: int,
        payload: RateContractUpdate,
    ) -> ContractWorkspace:
        contract = self._require_contract(contract_id)
        updates = payload.model_dump(exclude_unset=True)
        if payload.default_rate_book_id is not None:
            self._require_rate_book(payload.default_rate_book_id)
        if payload.default_calculation_template_id is not None:
            self._require_calculation_template(payload.default_calculation_template_id)
        line_payloads = updates.pop("lines", None)
        for key, value in updates.items():
            setattr(contract, key, value)
        if line_payloads is not None:
            next_lines = [
                self._contract_line_from_payload(contract_id=contract.id, line_payload=line)
                for line in payload.lines or []
            ]
            for line in next_lines:
                self._require_component(line.charge_component_code)
                if line.rate_book_id is not None:
                    self._require_rate_book(line.rate_book_id)
                if line.calculation_template_id is not None:
                    self._require_calculation_template(line.calculation_template_id)
            contract.lines = next_lines
        contract.updated_at = utcnow()
        return self.get_contract_workspace(contract_id)

    def release_contract(self, contract_id: int) -> RateContract:
        contract = self._require_contract(contract_id)
        if not contract.lines:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one contract line is required before release.",
            )
        has_rate_source = any(
            line.rate_book_id is not None
            or line.calculation_template_id is not None
            or contract.default_rate_book_id is not None
            or contract.default_calculation_template_id is not None
            for line in contract.lines
        )
        if not has_rate_source:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one contract line must reference a rate book or calculation template before release.",
            )
        contract.status = "RELEASED"
        contract.updated_at = utcnow()
        return contract

    def create_quote_request(self, payload: QuoteRequestCreate) -> QuoteRequest:
        if self.repository.quotation_policy == "DIRECT_ONLY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation is disabled by charge management setup; create a direct charge document instead.",
            )
        row = QuoteRequest(
            **payload.model_dump(),
            id=self.repository.next_id("quote_request"),
            quotation_policy_snapshot=self.repository.quotation_policy,  # type: ignore[arg-type]
        )
        self.repository.quote_requests[row.id] = row
        return row

    def create_quote_offer(self, quote_request_id: int, payload: QuoteOfferCreate) -> QuoteOffer:
        quote = self._require_quote_request(quote_request_id)
        if quote.status.upper() not in {"REQUESTED", "RATED", "RANKED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider offers can only be submitted after the RFQ is submitted.",
            )
        offer_id = self.repository.next_id("quote_offer")
        offer = QuoteOffer(
            **payload.model_dump(),
            id=offer_id,
            quote_request_id=quote.id,
            status="SUBMITTED",
        )
        self.repository.quote_offers[offer.id] = offer
        self._create_offer_option(quote=quote, offer=offer)
        quote.status = "RATED"
        quote.updated_at = utcnow()
        return offer

    def get_quote_offer_workspace(self, offer_id: int) -> QuoteOfferWorkspace:
        offer = self._require_quote_offer(offer_id)
        quote = self._require_quote_request(offer.quote_request_id)
        option = self._option_for_offer(offer.id)
        return QuoteOfferWorkspace(offer=offer, quote_request=quote, quote_option=option)

    def update_quote_offer_workspace(
        self,
        offer_id: int,
        payload: QuoteOfferWorkspaceUpdate,
    ) -> QuoteOfferWorkspace:
        offer = self._require_quote_offer(offer_id)
        quote = self._require_quote_request(offer.quote_request_id)
        option = self._option_for_offer(offer.id)
        self._assert_offer_can_change(quote, offer, option)
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if field == "currency" and value is not None:
                value = str(value).upper()
            if field == "source" and value is not None:
                value = str(value).upper()
            if field == "amount" and value is not None:
                value = money(value)
            setattr(offer, field, value)
        offer.updated_at = utcnow()
        self._sync_offer_option(offer, option)
        quote.status = "RATED"
        quote.updated_at = utcnow()
        return self.get_quote_offer_workspace(offer.id)

    def withdraw_quote_offer(
        self,
        offer_id: int,
        payload: QuoteOfferWithdrawRequest,
    ) -> QuoteOfferWorkspace:
        offer = self._require_quote_offer(offer_id)
        quote = self._require_quote_request(offer.quote_request_id)
        option = self._option_for_offer(offer.id)
        self._assert_offer_can_change(quote, offer, option)
        offer.status = "WITHDRAWN"
        reason = (payload.reason or "").strip()
        if reason:
            offer.notes = f"{offer.notes}\nWithdrawn: {reason}" if offer.notes else f"Withdrawn: {reason}"
        offer.updated_at = utcnow()
        if option is not None:
            option.rank = None
            option.score = None
        quote.updated_at = utcnow()
        return self.get_quote_offer_workspace(offer.id)

    def list_quote_requests(
        self,
        *,
        status_filter: str | None = None,
        mode: str | None = None,
        customer_id: int | None = None,
        forwarder_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> QuoteRequestListResponse:
        rows = list(self.repository.quote_requests.values())
        if status_filter:
            rows = [row for row in rows if row.status.upper() == status_filter.upper()]
        if mode:
            rows = [row for row in rows if (row.mode or "").upper() == mode.upper()]
        if customer_id is not None:
            rows = [row for row in rows if row.customer_id == customer_id]
        if forwarder_id is not None:
            rows = [row for row in rows if row.forwarder_id == forwarder_id]
        rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return QuoteRequestListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_quote_request_workspace(self, quote_request_id: int) -> QuoteRequestWorkspace:
        quote = self._require_quote_request(quote_request_id)
        options = self._quote_options_for_request(quote.id)
        offers = [
            offer
            for offer in self.repository.quote_offers.values()
            if offer.quote_request_id == quote.id
        ]
        offers.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        commitments = [
            self._with_commitment_remaining(commitment)
            for commitment in self.repository.quote_commitments.values()
            if commitment.quote_request_id == quote.id
        ]
        commitments.sort(key=lambda row: (row.created_at, row.id))
        documents = [
            document
            for document in self.repository.documents.values()
            if document.quote_request_id == quote.id
        ]
        documents.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        return QuoteRequestWorkspace(
            quote_request=quote,
            options=options,
            offers=offers,
            commitments=commitments,
            charge_documents=documents,
        )

    def update_quote_request_workspace(
        self,
        quote_request_id: int,
        payload: QuoteRequestWorkspaceUpdate,
    ) -> QuoteRequestWorkspace:
        quote = self._require_quote_request(quote_request_id)
        if quote.status.upper() != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote request can only be updated while it is in DRAFT status.",
            )
        if (
            self._quote_options_for_request(quote.id)
            or any(offer.quote_request_id == quote.id for offer in self.repository.quote_offers.values())
            or any(commitment.quote_request_id == quote.id for commitment in self.repository.quote_commitments.values())
            or any(document.quote_request_id == quote.id for document in self.repository.documents.values())
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote request cannot be updated after offers, rated options, commitments, or charge documents exist.",
            )
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if field == "status":
                value = str(value or "").upper()
                if value not in {"DRAFT", "REQUESTED"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Draft quote requests can only move to REQUESTED from this workspace.",
                    )
            if field == "currency" and value is not None:
                value = str(value).upper()
            setattr(quote, field, value)
        quote.updated_at = utcnow()
        return self.get_quote_request_workspace(quote.id)

    def determine_contracts(self, quote_request_id: int) -> ContractDeterminationResponse:
        quote = self._require_quote_request(quote_request_id)
        if quote.status.upper() not in {"REQUESTED", "RATED", "RANKED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contracts can only be determined after the RFQ is submitted.",
            )
        payer = self._matching_contracts(quote, contract_role="PAYER")
        payee = self._matching_contracts(quote, contract_role="PAYEE")
        return ContractDeterminationResponse(
            quote_request_id=quote_request_id,
            payer_contracts=payer,
            payee_contracts=payee,
        )

    def rate_quote_request(self, quote_request_id: int) -> RateResponse:
        quote = self._require_quote_request(quote_request_id)
        determination = self.determine_contracts(quote.id)
        payer_contracts = determination.payer_contracts
        payee_contracts = determination.payee_contracts
        if not self.repository.provider_cost_layer_enabled:
            if not payee_contracts:
                existing_options = self._quote_options_for_request(quote.id)
                if existing_options:
                    quote.status = "RATED"
                    quote.updated_at = utcnow()
                    return RateResponse(quote_request=quote, options=existing_options)
                raise HTTPException(
                    status_code=422,
                    detail="No released payee contract matched the quote request.",
                )
            self._delete_contract_options_for_quote(quote.id)
            for payee_contract in payee_contracts:
                payee_lines = self._rate_contract(quote, payee_contract, relationship_role="PAYEE")
                self._create_customer_pricing_option(
                    quote=quote,
                    payee_contract=payee_contract,
                    payee_lines=payee_lines,
                )
            quote.status = "RATED"
            quote.updated_at = utcnow()
            return RateResponse(quote_request=quote, options=self._quote_options_for_request(quote.id))

        if not payer_contracts:
            existing_options = self._quote_options_for_request(quote.id)
            if existing_options:
                quote.status = "RATED"
                quote.updated_at = utcnow()
                return RateResponse(quote_request=quote, options=existing_options)
            raise HTTPException(
                status_code=422,
                detail="No released payer contract matched the quote request.",
            )

        self._delete_contract_options_for_quote(quote.id)
        options: list[QuoteOption] = []
        for payer_contract in payer_contracts:
            payee_contract = payee_contracts[0] if payee_contracts else None
            payer_lines = self._rate_contract(quote, payer_contract, relationship_role="PAYER")
            payee_lines = (
                self._rate_contract(quote, payee_contract, relationship_role="PAYEE")
                if payee_contract is not None
                else self._derive_payee_lines_from_margin(quote, payer_lines)
            )
            option = self._create_option(
                quote=quote,
                payer_contract=payer_contract,
                payee_contract=payee_contract,
                payer_lines=payer_lines,
                payee_lines=payee_lines,
            )
            options.append(option)
        quote.status = "RATED"
        quote.updated_at = utcnow()
        return RateResponse(quote_request=quote, options=self._quote_options_for_request(quote.id))

    def rank_quote_request(self, quote_request_id: int) -> RankResponse:
        quote = self._require_quote_request(quote_request_id)
        options = self._quote_options_for_request(quote.id)
        if not options:
            options = self.rate_quote_request(quote_request_id).options
        ranked = sorted(options, key=self._ranking_key)
        for idx, option in enumerate(ranked, start=1):
            option.rank = idx
            option.score = self._score_option(option)
        quote.status = "RANKED"
        quote.updated_at = utcnow()
        return RankResponse(quote_request_id=quote.id, options=ranked)

    def award_quote_request(
        self,
        quote_request_id: int,
        payload: QuoteAwardRequest,
    ) -> QuoteAwardResponse:
        quote = self._require_quote_request(quote_request_id)
        if quote.quotation_policy_snapshot == "DIRECT_ONLY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation award is disabled by the charge document quotation-policy snapshot.",
            )
        option = self._require_quote_option(payload.quote_option_id)
        if option.quote_request_id != quote.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Option does not belong to quote")
        if not self._quote_option_is_available(option):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote option is not available for award.",
            )

        document_id = self.repository.next_id("document")
        document = ChargeDocument(
            id=document_id,
            document_number=f"CHG-{document_id:08d}",
            quote_request_id=quote.id,
            quote_option_id=option.id,
            quotation_policy_snapshot=quote.quotation_policy_snapshot,
            source_object_type=quote.source_object_type,
            source_object_id=quote.source_object_id,
            company_id=quote.company_id,
            customer_id=quote.customer_id,
            vendor_id=quote.vendor_id,
            forwarder_id=quote.forwarder_id,
            carrier_id=quote.carrier_id,
            currency=quote.currency,
            payer_total_amount=option.payer_total_amount,
            payee_total_amount=option.payee_total_amount,
            margin_amount=option.margin_amount,
            lines=[
                ChargeLine(
                    id=self.repository.next_id("charge_line"),
                    charge_document_id=document_id,
                    line_number=index,
                    line_role="POSTING",
                    relationship_role=line.relationship_role,
                    payer_party_ref=line.payer_party_ref,
                    payee_party_ref=line.payee_party_ref,
                    party_role_ref=line.party_role_ref,
                    charge_component_code=line.charge_component_code,
                    description=line.description,
                    expected_amount=line.amount,
                    currency=line.currency,
                    quantity_uom=line.quantity_uom,
                    allocation_profile_id=line.allocation_profile_id,
                    allocation_profile_version_id=line.allocation_profile_version_id,
                    pinned_allocation_snapshot_json=line.pinned_allocation_snapshot_json,
                    effective_allocation_snapshot_json=line.effective_allocation_snapshot_json,
                    allocation_basis=line.allocation_basis
                    or self._effective_allocation_basis(line.effective_allocation_snapshot_json),
                    basis=line.basis,
                    source_quote_option_line_id=line.id,
                )
                for index, line in enumerate(option.lines, start=1)
            ],
        )
        quote.status = "AWARDED"
        quote.awarded_option_id = option.id
        quote.updated_at = utcnow()
        self.repository.documents[document.id] = document
        commitment = self._ensure_quote_commitment(
            quote=quote,
            option=option,
            document=document,
        )
        return QuoteAwardResponse(
            quote_request=quote,
            awarded_option=option,
            charge_document=document,
            quote_commitment=commitment,
        )

    def match_quote_commitments(
        self,
        payload: QuoteCommitmentMatchRequest,
    ) -> QuoteCommitmentMatchResponse:
        matches = [
            self._with_commitment_remaining(row)
            for row in self.repository.quote_commitments.values()
            if row.status == "ACTIVE"
            and self._commitment_matches_payload(row, payload)
            and self._commitment_has_capacity(row, payload)
        ]
        matches.sort(
            key=lambda row: (
                -self._commitment_specificity(row),
                row.valid_to or date.max,
                row.id,
            )
        )
        return QuoteCommitmentMatchResponse(matches=matches)

    def consume_quote_commitment(
        self,
        commitment_id: int,
        payload: QuoteCommitmentConsumeRequest,
    ) -> QuoteCommitmentConsumeResponse:
        commitment = self._require_quote_commitment(commitment_id)
        if commitment.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quote commitment is not active")
        if not self._payload_has_consumption(payload):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one quantity, weight, or amount must be consumed",
            )
        if not self._commitment_has_capacity(commitment, payload):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote commitment does not have enough remaining capacity",
            )
        amount = payload.amount if payload.amount is not None else self._proportional_amount(commitment, payload)
        if amount is not None and money(amount) > self._remaining_amount(commitment):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote commitment does not have enough remaining amount",
            )
        consumption = QuoteCommitmentConsumption(
            id=self.repository.next_id("quote_commitment_consumption"),
            commitment_id=commitment.id,
            source_object_type=payload.source_object_type,
            source_object_id=payload.source_object_id,
            reference_number=payload.reference_number,
            container_count=payload.container_count,
            package_count=payload.package_count,
            chargeable_weight=payload.chargeable_weight,
            quantity=payload.quantity,
            amount=money(amount) if amount is not None else None,
        )
        self.repository.quote_commitment_consumptions[consumption.id] = consumption
        self._apply_consumption(commitment, consumption)
        commitment.updated_at = utcnow()
        if self._commitment_fully_consumed(commitment):
            commitment.status = "CONSUMED"
        return QuoteCommitmentConsumeResponse(
            commitment=self._with_commitment_remaining(commitment),
            consumption=consumption,
        )

    def reverse_quote_commitment_consumption(
        self,
        consumption_id: int,
        payload: QuoteCommitmentConsumptionReverseRequest,
    ) -> QuoteCommitmentConsumeResponse:
        consumption = self._require_quote_commitment_consumption(consumption_id)
        commitment = self._require_quote_commitment(consumption.commitment_id)
        if consumption.status == "REVERSED":
            return QuoteCommitmentConsumeResponse(
                commitment=self._with_commitment_remaining(commitment),
                consumption=consumption,
            )
        self._reverse_consumption_balance(commitment, consumption)
        consumption.status = "REVERSED"
        consumption.reversed_at = utcnow()
        consumption.reversal_reason = payload.reason
        commitment.updated_at = utcnow()
        if commitment.status == "CONSUMED" and self._any_remaining(commitment):
            commitment.status = "ACTIVE"
        return QuoteCommitmentConsumeResponse(
            commitment=self._with_commitment_remaining(commitment),
            consumption=consumption,
        )

    def create_charge_document(self, payload: ChargeDocumentCreate) -> ChargeDocument:
        if self.repository.quotation_policy == "REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation is required by charge management setup before creating a charge document.",
            )
        document_id = self.repository.next_id("document")
        document_context = ChargeDocument(
            id=document_id,
            document_number=payload.document_number or f"CHG-{document_id:08d}",
            quote_request_id=None,
            quote_option_id=None,
            quotation_policy_snapshot=self.repository.quotation_policy,  # type: ignore[arg-type]
            source_object_type=payload.source_object_type,
            source_object_id=payload.source_object_id,
            document_scope_level=_clean_optional(payload.document_scope_level),
            shipment_scope=payload.shipment_scope,
            document_date=payload.document_date,
            source_reference_snapshot_json=payload.source_reference_snapshot_json,
            company_id=payload.company_id,
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            forwarder_id=payload.forwarder_id,
            carrier_id=payload.carrier_id,
            currency=payload.currency,
            payer_total_amount=Decimal("0"),
            payee_total_amount=Decimal("0"),
            margin_amount=Decimal("0"),
            lines=[],
        )
        lines = self._charge_lines_from_payloads(document_context, payload.lines)
        payer_total, payee_total = _document_totals(lines)
        document = document_context.model_copy(
            update={
                "payer_total_amount": payer_total,
                "payee_total_amount": payee_total,
                "margin_amount": money(payee_total - payer_total),
                "lines": lines,
            }
        )
        self.repository.documents[document.id] = document
        return document

    def _charge_lines_from_payloads(self, document: ChargeDocument, line_payloads: list[Any]) -> list[ChargeLine]:
        lines: list[ChargeLine] = []
        lines_by_number: dict[int, ChargeLine] = {}
        payloads_by_line_id: dict[int, Any] = {}
        for index, line_payload in enumerate(line_payloads, start=1):
            component = self._require_component(line_payload.charge_component_code)
            line_number = _payload_line_number(line_payload, default=index)
            if line_number in lines_by_number:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Duplicate charge line_number: {line_number}")
            _validate_target_payload(line_payload)
            (
                allocation_profile_id,
                allocation_profile_version_id,
                pinned_allocation_snapshot_json,
                effective_allocation_snapshot_json,
            ) = self._resolve_effective_allocation(
                component=component,
                allocation_profile_id=getattr(line_payload, "allocation_profile_id", None),
                allocation_profile_version_id=getattr(line_payload, "allocation_profile_version_id", None),
            )
            effective_allocation_basis = self._effective_allocation_basis(
                effective_allocation_snapshot_json
            )
            effective_quantity_uom = self._effective_allocation_value(
                effective_allocation_snapshot_json,
                "default_quantity_uom",
            )
            resolved_exchange_rate_date = self._resolve_business_date_date(
                component=component,
                document=document,
                line_payload=line_payload,
            )
            line = ChargeLine(
                id=self.repository.next_id("charge_line"),
                charge_document_id=document.id,
                relationship_role=line_payload.relationship_role,
                line_number=line_number,
                line_role=line_payload.line_role,
                target_level=_clean_optional(line_payload.target_level),
                target_object_type=_clean_optional(line_payload.target_object_type),
                target_object_id=_clean_optional(line_payload.target_object_id),
                payer_party_ref=line_payload.payer_party_ref,
                payee_party_ref=line_payload.payee_party_ref,
                party_role_ref=line_payload.party_role_ref,
                charge_component_code=line_payload.charge_component_code,
                description=line_payload.description or component.component_name,
                charge_date=line_payload.charge_date,
                charge_date_basis=getattr(line_payload, "charge_date_basis", None),
                expected_amount=money(line_payload.expected_amount),
                currency=line_payload.currency.upper(),
                quantity_uom=_clean_optional(line_payload.quantity_uom) or effective_quantity_uom,
                source_currency=line_payload.source_currency.upper() if line_payload.source_currency else None,
                source_amount=money(line_payload.source_amount) if line_payload.source_amount is not None else None,
                exchange_rate=line_payload.exchange_rate,
                exchange_rate_date=resolved_exchange_rate_date,
                fx_rate_id=getattr(line_payload, "fx_rate_id", None),
                exchange_rate_source_code=(
                    line_payload.exchange_rate_source_code.strip().upper()
                    if getattr(line_payload, "exchange_rate_source_code", None)
                    else None
                ),
                exchange_rate_type=(
                    line_payload.exchange_rate_type.strip().upper()
                    if getattr(line_payload, "exchange_rate_type", None)
                    else None
                ),
                exchange_rate_method=(
                    line_payload.exchange_rate_method.strip().upper()
                    if getattr(line_payload, "exchange_rate_method", None)
                    else None
                ),
                allocation_profile_id=allocation_profile_id,
                allocation_profile_version_id=allocation_profile_version_id,
                pinned_allocation_snapshot_json=pinned_allocation_snapshot_json,
                effective_allocation_snapshot_json=effective_allocation_snapshot_json,
                charge_text_snapshot=_clean_optional(line_payload.charge_text_snapshot),
                allocation_basis=_clean_optional(line_payload.allocation_basis) or effective_allocation_basis,
                allocation_ratio=line_payload.allocation_ratio,
                allocation_driver_value=line_payload.allocation_driver_value,
                target_reference_snapshot_json=line_payload.target_reference_snapshot_json,
                calculation_audit_json=line_payload.calculation_audit_json,
                basis=line_payload.basis,
            )
            lines.append(line)
            lines_by_number[line_number] = line
            payloads_by_line_id[line.id] = line_payload
        for line in lines:
            parent_line_number = getattr(payloads_by_line_id[line.id], "parent_line_number", None)
            if parent_line_number is None:
                continue
            parent_line = lines_by_number.get(int(parent_line_number))
            if parent_line is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown parent_line_number for charge line {line.line_number}: {parent_line_number}",
                )
            if parent_line.id == line.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A charge line cannot be its own parent.")
            if parent_line.line_role != "CALCULATION":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Charge line parents must use line_role CALCULATION.")
            line.parent_line_id = parent_line.id
            line.parent_line_number = parent_line.line_number
        return sorted(lines, key=_charge_line_sort_key)

    def list_charge_documents(
        self,
        *,
        status_filter: str | None = None,
        source_object_type: str | None = None,
        customer_id: int | None = None,
        forwarder_id: int | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChargeDocumentListResponse:
        rows = list(self.repository.documents.values())
        if status_filter:
            rows = [
                row
                for row in rows
                if row.status.upper() == status_filter.upper()
            ]
        if source_object_type:
            rows = [
                row
                for row in rows
                if row.source_object_type.upper() == source_object_type.upper()
            ]
        if customer_id is not None:
            rows = [row for row in rows if row.customer_id == customer_id]
        if forwarder_id is not None:
            rows = [row for row in rows if row.forwarder_id == forwarder_id]
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.document_number.upper()
                or normalized in row.status.upper()
                or normalized in row.source_object_type.upper()
            ]
        rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return ChargeDocumentListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_charge_document_workspace(self, charge_document_id: int) -> ChargeDocumentWorkspace:
        document = self._require_document(charge_document_id)
        invoices = [
            invoice
            for invoice in self.repository.invoices.values()
            if invoice.charge_document_id == document.id
        ]
        matches = [
            result
            for result in self.repository.match_results.values()
            if result.charge_document_id == document.id
        ]
        return ChargeDocumentWorkspace(document=document, invoices=invoices, match_results=matches)

    def delete_charge_document(self, charge_document_id: int) -> ChargeActionResponse:
        document = self._require_document(charge_document_id)
        if document.status.upper() in {"APPROVED", "EXPORTED", "REVERSED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charge document cannot be deleted after approval, export, or reversal.",
            )
        if document.quote_request_id is not None or document.quote_option_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote-awarded charge documents cannot be deleted from the workspace.",
            )
        if any(invoice.charge_document_id == document.id for invoice in self.repository.invoices.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charge document cannot be deleted after invoices are captured.",
            )
        if any(response.document.id == document.id for response in self.repository.exports.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charge document cannot be deleted after export batches exist.",
            )
        if any(commitment.charge_document_id == document.id for commitment in self.repository.quote_commitments.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charge document cannot be deleted while quote commitments are linked.",
            )
        deleted = document.model_copy(deep=True)
        self.repository.documents.pop(document.id, None)
        return ChargeActionResponse(document=deleted)

    def update_charge_document_workspace(
        self,
        charge_document_id: int,
        payload: ChargeDocumentWorkspaceUpdate,
    ) -> ChargeDocumentWorkspace:
        document = self._require_document(charge_document_id)
        if payload.status is not None:
            next_status = payload.status.upper()
            if next_status not in {"ESTIMATED", "ACCRUED", "ACTUAL", "DISPUTED"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workspace status update is limited to ESTIMATED, ACCRUED, ACTUAL, or DISPUTED.",
                )
            document.status = next_status
        if payload.lines is not None:
            if document.status.upper() in {"APPROVED", "EXPORTED", "REVERSED"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Charge document lines cannot be updated after approval, export, or reversal.",
                )
            if document.quote_request_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Quote-awarded charge document lines are controlled by the awarded quote and cannot be edited here.",
                )
            if any(invoice.charge_document_id == document.id for invoice in self.repository.invoices.values()):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Charge document lines cannot be updated after invoices are captured.",
                )
            document.lines = self._charge_lines_from_payloads(document, payload.lines)
        document.payer_total_amount, document.payee_total_amount = _document_totals(document.lines)
        document.margin_amount = money(document.payee_total_amount - document.payer_total_amount)
        return self.get_charge_document_workspace(charge_document_id)

    def create_invoice(self, payload: ChargeInvoiceCreate) -> ChargeInvoice:
        document = self._require_document(payload.charge_document_id)
        total = money(sum((Decimal(str(line.get("amount", "0"))) for line in payload.lines), Decimal("0")))
        invoice = ChargeInvoice(
            **payload.model_dump(),
            id=self.repository.next_id("invoice"),
            charge_document_number=document.document_number,
            charge_document_status=document.status,
            total_amount=total,
        )
        self.repository.invoices[invoice.id] = invoice
        return invoice

    def list_invoices(
        self,
        *,
        charge_document_id: int | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ChargeInvoiceListResponse:
        rows = list(self.repository.invoices.values())
        if charge_document_id is not None:
            rows = [row for row in rows if row.charge_document_id == charge_document_id]
        if status_filter:
            rows = [row for row in rows if row.status.upper() == status_filter.upper()]
        for row in rows:
            self._sync_invoice_document_summary(row)
        if search:
            normalized = search.strip().upper()
            rows = [
                row
                for row in rows
                if normalized in row.invoice_number.upper()
                or normalized in row.status.upper()
                or normalized in row.invoice_type.upper()
                or normalized in row.currency.upper()
                or normalized in (row.charge_document_number or "").upper()
                or normalized in (row.charge_document_status or "").upper()
            ]
        rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        safe_offset = max(int(offset), 0)
        safe_limit = min(max(int(limit), 1), 200)
        return ChargeInvoiceListResponse(
            items=rows[safe_offset : safe_offset + safe_limit],
            total=len(rows),
            limit=safe_limit,
            offset=safe_offset,
        )

    def get_invoice_workspace(self, invoice_id: int) -> ChargeInvoiceWorkspace:
        invoice = self._require_invoice(invoice_id)
        document = self._require_document(invoice.charge_document_id)
        self._sync_invoice_document_summary(invoice)
        matches = [
            result
            for result in self.repository.match_results.values()
            if result.invoice_id == invoice.id
        ]
        matches.sort(key=lambda row: row.id)
        return ChargeInvoiceWorkspace(
            invoice=invoice,
            charge_document=document,
            match_results=matches,
        )

    def update_invoice_workspace(
        self,
        invoice_id: int,
        payload: ChargeInvoiceWorkspaceUpdate,
    ) -> ChargeInvoiceWorkspace:
        invoice = self._require_invoice(invoice_id)
        document = self._require_document(invoice.charge_document_id)
        if document.status in {"APPROVED", "EXPORTED", "REVERSED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invoice cannot be updated after its charge document is approved, exported, or reversed.",
            )
        if payload.invoice_number is not None:
            invoice.invoice_number = payload.invoice_number
        if payload.invoice_type is not None:
            invoice.invoice_type = payload.invoice_type
        if payload.invoice_date is not None:
            invoice.invoice_date = payload.invoice_date
        if payload.currency is not None:
            invoice.currency = payload.currency
        if payload.lines is not None:
            invoice.lines = payload.lines
            invoice.total_amount = money(
                sum((Decimal(str(line.get("amount", "0"))) for line in invoice.lines), Decimal("0"))
            )
        for result_id, result in list(self.repository.match_results.items()):
            if result.invoice_id == invoice.id:
                del self.repository.match_results[result_id]
        invoice.status = "CAPTURED"
        invoice.updated_at = utcnow()
        self._sync_invoice_document_summary(invoice)
        return self.get_invoice_workspace(invoice_id)

    def match_invoice(self, invoice_id: int) -> InvoiceMatchResponse:
        invoice = self._require_invoice(invoice_id)
        document = self._require_document(invoice.charge_document_id)
        for result_id, result in list(self.repository.match_results.items()):
            if result.invoice_id == invoice.id:
                del self.repository.match_results[result_id]

        expected_by_component = {line.charge_component_code: line for line in document.lines}
        results: list[ChargeMatchResult] = []
        for raw_line in invoice.lines:
            component_code = str(raw_line.get("charge_component_code") or "").strip()
            invoice_amount = money(raw_line.get("amount"))
            expected_line = expected_by_component.get(component_code)
            expected_amount = money(expected_line.expected_amount if expected_line else 0)
            variance = money(invoice_amount - expected_amount)
            variance_percent = (
                money((variance / expected_amount) * Decimal("100"))
                if expected_amount != 0
                else Decimal("0.00")
            )
            match_status_value = (
                "UNEXPECTED"
                if expected_line is None
                else ("MATCHED" if abs(variance) <= Decimal("0.01") else "VARIANCE")
            )
            result = ChargeMatchResult(
                id=self.repository.next_id("match_result"),
                invoice_id=invoice.id,
                charge_document_id=document.id,
                charge_line_id=expected_line.id if expected_line else None,
                charge_component_code=component_code,
                expected_amount=expected_amount,
                invoice_amount=invoice_amount,
                variance_amount=variance,
                variance_percent=variance_percent,
                match_status=match_status_value,
            )
            self.repository.match_results[result.id] = result
            results.append(result)
        invoice.status = "MATCHED" if all(row.match_status == "MATCHED" for row in results) else "VARIANCE"
        invoice.updated_at = utcnow()
        self._sync_invoice_document_summary(invoice)
        return InvoiceMatchResponse(invoice=invoice, results=results)

    def approve_document(self, charge_document_id: int) -> ChargeActionResponse:
        document = self._require_document(charge_document_id)
        document.status = "APPROVED"
        document.approved_at = utcnow()
        for line in document.lines:
            line.approved_amount = line.actual_amount or line.expected_amount
        return ChargeActionResponse(document=document)

    def post_export(self, charge_document_id: int) -> ChargeExportResponse:
        document = self._require_document(charge_document_id)
        if document.status not in {"APPROVED", "EXPORTED"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document must be approved first")
        document.status = "EXPORTED"
        document.exported_at = utcnow()
        export_number = f"EXP-{self.repository.next_id('export'):08d}"
        response = ChargeExportResponse(
            document=document,
            export_number=export_number,
            target_system="INTERNAL_LEDGER",
            status="POSTED",
            payload_json=document.model_dump(mode="json"),
        )
        self.repository.exports[export_number] = response
        return response

    def reverse_document(self, charge_document_id: int, reason: str) -> ChargeActionResponse:
        document = self._require_document(charge_document_id)
        if document.status not in {"APPROVED", "EXPORTED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only approved or exported documents can be reversed",
            )
        document.status = "REVERSED"
        document.reversed_at = utcnow()
        document.reversal_reason = reason
        return ChargeActionResponse(document=document)

    def _ensure_quote_commitment(
        self,
        *,
        quote: QuoteRequest,
        option: QuoteOption,
        document: ChargeDocument,
    ) -> QuoteCommitment:
        for existing in self.repository.quote_commitments.values():
            if existing.quote_option_id == option.id:
                return self._with_commitment_remaining(existing)
        self._assert_no_overlapping_commitment(quote=quote, option=option)
        commitment_id = self.repository.next_id("quote_commitment")
        committed_amount = money(option.payee_total_amount or option.payer_total_amount)
        commitment = QuoteCommitment(
            id=commitment_id,
            commitment_number=f"QCM-{quote.id:08d}-{option.id:08d}",
            quote_request_id=quote.id,
            quote_option_id=option.id,
            charge_document_id=document.id,
            company_id=quote.company_id,
            customer_id=quote.customer_id,
            vendor_id=quote.vendor_id,
            forwarder_id=quote.forwarder_id,
            carrier_id=quote.carrier_id,
            origin_code=quote.origin_code,
            destination_code=quote.destination_code,
            mode=quote.mode,
            equipment_type=quote.equipment_type,
            commodity_code=quote.commodity_code,
            service_level=quote.service_level,
            package_type=quote.package_type,
            requested_service_date=quote.requested_service_date,
            valid_from=quote.valid_from or quote.requested_service_date or date.today(),
            valid_to=quote.valid_to or (quote.expires_at.date() if quote.expires_at else None),
            committed_container_count=quote.container_count,
            committed_package_count=quote.package_count,
            committed_chargeable_weight=quote.gross_weight,
            committed_quantity=quote.quantity,
            committed_amount=committed_amount,
            remaining_amount=committed_amount,
            currency=quote.currency,
        )
        self.repository.quote_commitments[commitment.id] = commitment
        return self._with_commitment_remaining(commitment)

    def _assert_no_overlapping_commitment(
        self,
        *,
        quote: QuoteRequest,
        option: QuoteOption,
    ) -> None:
        target_valid_from = quote.valid_from or quote.requested_service_date or date.today()
        target_valid_to = quote.valid_to or (quote.expires_at.date() if quote.expires_at else None)
        for existing in self.repository.quote_commitments.values():
            if existing.status != "ACTIVE" or existing.quote_option_id == option.id:
                continue
            if not self._same_commitment_scope(existing, quote):
                continue
            if not self._validity_overlaps(
                existing.valid_from,
                existing.valid_to,
                target_valid_from,
                target_valid_to,
            ):
                continue
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Active quote commitment already exists for the same commercial "
                    f"scope and overlapping validity: {existing.commitment_number}"
                ),
            )

    def _same_commitment_scope(
        self,
        commitment: QuoteCommitment,
        quote: QuoteRequest,
    ) -> bool:
        for field in ("company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"):
            if getattr(commitment, field, None) != getattr(quote, field, None):
                return False
        for field in ("origin_code", "destination_code", "mode", "equipment_type", "commodity_code", "service_level", "package_type"):
            left = getattr(commitment, field, None)
            right = getattr(quote, field, None)
            if (str(left).strip().upper() if left else None) != (str(right).strip().upper() if right else None):
                return False
        return True

    def _validity_overlaps(
        self,
        start_a: date | None,
        end_a: date | None,
        start_b: date | None,
        end_b: date | None,
    ) -> bool:
        left_start = start_a or date.min
        left_end = end_a or date.max
        right_start = start_b or date.min
        right_end = end_b or date.max
        return left_start <= right_end and right_start <= left_end

    def _with_commitment_remaining(self, row: QuoteCommitment) -> QuoteCommitment:
        row.remaining_container_count = self._remaining(row.committed_container_count, row.consumed_container_count)
        row.remaining_package_count = self._remaining(row.committed_package_count, row.consumed_package_count)
        row.remaining_chargeable_weight = self._remaining(
            row.committed_chargeable_weight,
            row.consumed_chargeable_weight,
        )
        row.remaining_quantity = dec(row.committed_quantity) - dec(row.consumed_quantity)
        row.remaining_amount = money(dec(row.committed_amount) - dec(row.consumed_amount))
        row.consumptions = sorted(
            [
                consumption
                for consumption in self.repository.quote_commitment_consumptions.values()
                if consumption.commitment_id == row.id
            ],
            key=lambda item: (item.consumed_at, item.id),
            reverse=True,
        )
        return row

    def _commitment_matches_payload(
        self,
        commitment: QuoteCommitment,
        payload: QuoteCommitmentMatchRequest | QuoteCommitmentConsumeRequest,
    ) -> bool:
        requested_date = getattr(payload, "requested_service_date", None) or date.today()
        if commitment.valid_from and requested_date < commitment.valid_from:
            return False
        if commitment.valid_to and requested_date > commitment.valid_to:
            return False
        for field in ("company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"):
            expected = getattr(commitment, field, None)
            actual = getattr(payload, field, None)
            if expected is not None and actual is not None and int(expected) != int(actual):
                return False
        for field in ("origin_code", "destination_code", "mode", "equipment_type", "commodity_code", "service_level", "package_type"):
            expected = getattr(commitment, field, None)
            actual = getattr(payload, field, None)
            if expected and actual and str(expected).upper() != str(actual).upper():
                return False
        return True

    def _commitment_has_capacity(
        self,
        commitment: QuoteCommitment,
        payload: QuoteCommitmentMatchRequest | QuoteCommitmentConsumeRequest,
    ) -> bool:
        checks: list[bool] = []
        if dec(payload.container_count) > 0:
            committed = commitment.committed_container_count or commitment.committed_quantity
            consumed = commitment.consumed_container_count if commitment.committed_container_count is not None else commitment.consumed_quantity
            checks.append(self._capacity_ok(committed, consumed, payload.container_count))
        if dec(payload.package_count) > 0:
            committed = commitment.committed_package_count or commitment.committed_quantity
            consumed = commitment.consumed_package_count if commitment.committed_package_count is not None else commitment.consumed_quantity
            checks.append(self._capacity_ok(committed, consumed, payload.package_count))
        if dec(payload.chargeable_weight) > 0:
            checks.append(
                self._capacity_ok(
                    commitment.committed_chargeable_weight,
                    commitment.consumed_chargeable_weight,
                    payload.chargeable_weight,
                )
            )
        if dec(payload.quantity) > 0:
            checks.append(self._capacity_ok(commitment.committed_quantity, commitment.consumed_quantity, payload.quantity))
        if dec(getattr(payload, "amount", None)) > 0:
            checks.append(self._remaining_amount(commitment) >= money(getattr(payload, "amount", None)))
        if checks:
            return all(checks)
        return self._any_remaining(commitment)

    def _capacity_ok(
        self,
        committed: Decimal | None,
        consumed: Decimal | None,
        requested: Decimal | None,
    ) -> bool:
        if requested is None or dec(requested) <= 0:
            return True
        if committed is None:
            return False
        return dec(committed) - dec(consumed) >= dec(requested)

    def _payload_has_consumption(self, payload: QuoteCommitmentConsumeRequest) -> bool:
        return any(
            dec(getattr(payload, field, None)) > 0
            for field in ("container_count", "package_count", "chargeable_weight", "quantity", "amount")
        )

    def _apply_consumption(
        self,
        commitment: QuoteCommitment,
        consumption: QuoteCommitmentConsumption,
    ) -> None:
        if consumption.container_count is not None:
            commitment.consumed_container_count = dec(commitment.consumed_container_count) + dec(consumption.container_count)
        if consumption.package_count is not None:
            commitment.consumed_package_count = dec(commitment.consumed_package_count) + dec(consumption.package_count)
        if consumption.chargeable_weight is not None:
            commitment.consumed_chargeable_weight = dec(commitment.consumed_chargeable_weight) + dec(consumption.chargeable_weight)
        if consumption.quantity is not None:
            commitment.consumed_quantity = dec(commitment.consumed_quantity) + dec(consumption.quantity)
        if consumption.amount is not None:
            commitment.consumed_amount = money(dec(commitment.consumed_amount) + dec(consumption.amount))
        self._with_commitment_remaining(commitment)

    def _reverse_consumption_balance(
        self,
        commitment: QuoteCommitment,
        consumption: QuoteCommitmentConsumption,
    ) -> None:
        if consumption.container_count is not None:
            commitment.consumed_container_count = max(
                Decimal("0"),
                dec(commitment.consumed_container_count) - dec(consumption.container_count),
            )
        if consumption.package_count is not None:
            commitment.consumed_package_count = max(
                Decimal("0"),
                dec(commitment.consumed_package_count) - dec(consumption.package_count),
            )
        if consumption.chargeable_weight is not None:
            commitment.consumed_chargeable_weight = max(
                Decimal("0"),
                dec(commitment.consumed_chargeable_weight) - dec(consumption.chargeable_weight),
            )
        if consumption.quantity is not None:
            commitment.consumed_quantity = max(
                Decimal("0"),
                dec(commitment.consumed_quantity) - dec(consumption.quantity),
            )
        if consumption.amount is not None:
            commitment.consumed_amount = money(
                max(Decimal("0"), dec(commitment.consumed_amount) - dec(consumption.amount))
            )
        self._with_commitment_remaining(commitment)

    def _commitment_fully_consumed(self, commitment: QuoteCommitment) -> bool:
        specific_balances = [
            self._remaining(commitment.committed_container_count, commitment.consumed_container_count),
            self._remaining(commitment.committed_package_count, commitment.consumed_package_count),
            self._remaining(commitment.committed_chargeable_weight, commitment.consumed_chargeable_weight),
        ]
        active_balances = [value for value in specific_balances if value is not None]
        if active_balances:
            return all(value <= 0 for value in active_balances)
        if dec(commitment.committed_quantity) > 0:
            return dec(commitment.committed_quantity) - dec(commitment.consumed_quantity) <= 0
        return self._remaining_amount(commitment) <= 0

    def _proportional_amount(
        self,
        commitment: QuoteCommitment,
        payload: QuoteCommitmentConsumeRequest,
    ) -> Decimal | None:
        remaining_amount = self._remaining_amount(commitment)
        for requested, committed, consumed in (
            (payload.container_count, commitment.committed_container_count, commitment.consumed_container_count),
            (payload.package_count, commitment.committed_package_count, commitment.consumed_package_count),
            (payload.chargeable_weight, commitment.committed_chargeable_weight, commitment.consumed_chargeable_weight),
            (payload.quantity, commitment.committed_quantity, commitment.consumed_quantity),
        ):
            if dec(requested) <= 0 or committed is None or dec(committed) <= 0:
                continue
            remaining_basis = dec(committed) - dec(consumed)
            if dec(requested) >= remaining_basis:
                return remaining_amount
            return money(dec(commitment.committed_amount) * dec(requested) / dec(committed))
        return None

    def _remaining(self, committed: Decimal | None, consumed: Decimal | None) -> Decimal | None:
        if committed is None:
            return None
        return dec(committed) - dec(consumed)

    def _remaining_amount(self, commitment: QuoteCommitment) -> Decimal:
        return money(dec(commitment.committed_amount) - dec(commitment.consumed_amount))

    def _any_remaining(self, commitment: QuoteCommitment) -> bool:
        for remaining in (
            self._remaining(commitment.committed_container_count, commitment.consumed_container_count),
            self._remaining(commitment.committed_package_count, commitment.consumed_package_count),
            self._remaining(commitment.committed_chargeable_weight, commitment.consumed_chargeable_weight),
        ):
            if remaining is not None and remaining > 0:
                return True
        return dec(commitment.committed_quantity) - dec(commitment.consumed_quantity) > 0 or self._remaining_amount(commitment) > 0

    def _commitment_specificity(self, commitment: QuoteCommitment) -> int:
        return sum(
            1
            for value in (
                commitment.company_id,
                commitment.customer_id,
                commitment.vendor_id,
                commitment.forwarder_id,
                commitment.carrier_id,
                commitment.origin_code,
                commitment.destination_code,
                commitment.mode,
                commitment.equipment_type,
                commitment.commodity_code,
                commitment.service_level,
                commitment.package_type,
            )
            if value is not None
        )

    def _create_option(
        self,
        *,
        quote: QuoteRequest,
        payer_contract: RateContract,
        payee_contract: RateContract | None,
        payer_lines: list[QuoteOptionLine],
        payee_lines: list[QuoteOptionLine],
    ) -> QuoteOption:
        option_id = self.repository.next_id("quote_option")
        all_lines = []
        for line in [*payer_lines, *payee_lines]:
            line.quote_option_id = option_id
            all_lines.append(line)
        payer_total = money(sum((line.amount for line in payer_lines), Decimal("0")))
        payee_total = money(sum((line.amount for line in payee_lines), Decimal("0")))
        margin_amount = money(payee_total - payer_total)
        margin_percent = money((margin_amount / payer_total) * Decimal("100")) if payer_total else Decimal("0.00")
        option = QuoteOption(
            id=option_id,
            quote_request_id=quote.id,
            option_name=f"{payer_contract.contract_name} option",
            payer_contract_id=payer_contract.id,
            payee_contract_id=payee_contract.id if payee_contract else None,
            payer_total_amount=payer_total,
            payee_total_amount=payee_total,
            margin_amount=margin_amount,
            margin_percent=margin_percent,
            lines=all_lines,
            transit_time_days=int(quote.context.get("transit_time_days") or 0) or None,
            service_level_score=Decimal(str(quote.context.get("service_level_score") or "0")),
            policy_compliant=bool(quote.context.get("policy_compliant", True)),
        )
        self.repository.quote_options[option.id] = option
        return option

    def _create_customer_pricing_option(
        self,
        *,
        quote: QuoteRequest,
        payee_contract: RateContract,
        payee_lines: list[QuoteOptionLine],
    ) -> QuoteOption:
        option_id = self.repository.next_id("quote_option")
        for line in payee_lines:
            line.quote_option_id = option_id
        payee_total = money(sum((line.amount for line in payee_lines), Decimal("0")))
        option = QuoteOption(
            id=option_id,
            quote_request_id=quote.id,
            option_name=f"{payee_contract.contract_name} option",
            payer_contract_id=None,
            payee_contract_id=payee_contract.id,
            payer_total_amount=Decimal("0.00"),
            payee_total_amount=payee_total,
            margin_amount=Decimal("0.00"),
            margin_percent=Decimal("0.00"),
            lines=payee_lines,
            transit_time_days=int(quote.context.get("transit_time_days") or 0) or None,
            service_level_score=Decimal(str(quote.context.get("service_level_score") or "0")),
            policy_compliant=bool(quote.context.get("policy_compliant", True)),
        )
        self.repository.quote_options[option.id] = option
        return option

    def _create_offer_option(self, *, quote: QuoteRequest, offer: QuoteOffer) -> QuoteOption:
        option_id = self.repository.next_id("quote_option")
        option = QuoteOption(
            id=option_id,
            quote_request_id=quote.id,
            option_name=offer.offer_number or f"{quote.id:08d}-{offer.id:08d}",
            source_offer_id=offer.id,
            payer_total_amount=money(offer.amount),
            payee_total_amount=money(offer.amount),
            margin_amount=Decimal("0.00"),
            margin_percent=Decimal("0.00"),
            transit_time_days=offer.transit_time_days,
            service_level_score=dec(offer.performance_score),
            policy_compliant=True,
            expires_at=offer.expires_at,
            lines=[
                QuoteOptionLine(
                    id=self.repository.next_id("quote_option_line"),
                    quote_option_id=option_id,
                    relationship_role="PAYEE",
                    payer_party_ref=None,
                    payee_party_ref=offer.provider_party_ref,
                    party_role_ref=offer.provider_role_ref,
                    charge_component_code="QUOTE_OFFER_TOTAL",
                    description=offer.offer_number or "Provider Offer Total",
                    amount=money(offer.amount),
                    currency=offer.currency,
                    basis="FLAT",
                )
            ],
        )
        self.repository.quote_options[option.id] = option
        return option

    def _rate_contract(
        self,
        quote: QuoteRequest,
        contract: RateContract,
        *,
        relationship_role: str,
    ) -> list[QuoteOptionLine]:
        lines: list[QuoteOptionLine] = []
        for contract_line in contract.lines:
            rate_book = self.repository.rate_books.get(
                contract_line.rate_book_id or contract.default_rate_book_id or 0
            )
            if rate_book is None:
                continue
            for entry in rate_book.entries:
                if entry.charge_component_code != contract_line.charge_component_code:
                    continue
                if not self._entry_matches_quote(entry.model_dump(), quote):
                    continue
                component = self._require_component(entry.charge_component_code)
                (
                    allocation_profile_id,
                    allocation_profile_version_id,
                    pinned_allocation_snapshot_json,
                    effective_allocation_snapshot_json,
                ) = self._resolve_effective_allocation(
                    component=component,
                    allocation_profile_id=contract_line.allocation_profile_id
                    or entry.allocation_profile_id,
                    allocation_profile_version_id=contract_line.allocation_profile_version_id
                    or entry.allocation_profile_version_id,
                )
                amount = self._calculate_amount(entry, quote)
                lines.append(
                    QuoteOptionLine(
                        id=self.repository.next_id("quote_option_line"),
                        quote_option_id=0,
                        relationship_role=relationship_role,  # type: ignore[arg-type]
                        payer_party_ref=contract.payer_party_ref,
                        payee_party_ref=contract.payee_party_ref,
                        party_role_ref=contract.party_role_ref,
                        charge_component_code=entry.charge_component_code,
                        description=component.component_name,
                        amount=amount,
                        currency=entry.currency or quote.currency,
                        basis=entry.basis,
                        quantity_uom=self._effective_allocation_value(
                            effective_allocation_snapshot_json,
                            "default_quantity_uom",
                        ),
                        allocation_basis=self._effective_allocation_basis(
                            effective_allocation_snapshot_json
                        ),
                        allocation_profile_id=allocation_profile_id,
                        allocation_profile_version_id=allocation_profile_version_id,
                        pinned_allocation_snapshot_json=pinned_allocation_snapshot_json,
                        effective_allocation_snapshot_json=effective_allocation_snapshot_json,
                        source_contract_id=contract.id,
                        source_rate_book_id=rate_book.id,
                    )
                )
        return lines

    def _derive_payee_lines_from_margin(
        self,
        quote: QuoteRequest,
        payer_lines: list[QuoteOptionLine],
    ) -> list[QuoteOptionLine]:
        margin_rules = quote.margin_rules or {}
        fixed_amount = Decimal(str(margin_rules.get("fixed_amount") or "0"))
        percent = Decimal(str(margin_rules.get("percentage") or "0"))
        per_container = Decimal(str(margin_rules.get("per_container") or "0"))
        min_margin = Decimal(str(margin_rules.get("minimum_margin") or "0"))
        container_count = quote.container_count or Decimal("0")
        payer_total = sum((line.amount for line in payer_lines), Decimal("0"))
        margin = fixed_amount + ((payer_total * percent) / Decimal("100")) + (per_container * container_count)
        if margin < min_margin:
            margin = min_margin
        payee_lines = [
            line.model_copy(
                update={
                    "id": self.repository.next_id("quote_option_line"),
                    "relationship_role": "PAYEE",
                    "amount": line.amount,
                }
            )
            for line in payer_lines
        ]
        if margin:
            payee_lines.append(
                QuoteOptionLine(
                    id=self.repository.next_id("quote_option_line"),
                    quote_option_id=0,
                    relationship_role="PAYEE",
                    charge_component_code="MARGIN_MARKUP",
                    description="Margin Markup",
                    amount=money(margin),
                    currency=quote.currency,
                    basis="FLAT",
                    is_margin_line=True,
                )
            )
        return payee_lines

    def _calculate_amount(self, entry: RateBookEntry, quote: QuoteRequest) -> Decimal:
        basis = entry.basis.upper()
        if basis == "WEIGHT":
            amount = entry.rate_amount * (quote.gross_weight or Decimal("0"))
        elif basis == "VOLUME":
            amount = entry.rate_amount * (quote.gross_volume_cbm or Decimal("0"))
        elif basis == "CONTAINER":
            amount = entry.rate_amount * (quote.container_count or Decimal("0"))
        elif basis == "PACKAGE":
            amount = entry.rate_amount * (quote.package_count or Decimal("0"))
        elif basis == "PERCENTAGE":
            amount = entry.rate_amount
        else:
            amount = entry.rate_amount
        if entry.minimum_amount is not None:
            amount = max(amount, entry.minimum_amount)
        if entry.maximum_amount is not None:
            amount = min(amount, entry.maximum_amount)
        return money(amount)

    def _matching_contracts(self, quote: QuoteRequest, *, contract_role: str) -> list[RateContract]:
        return [
            contract
            for contract in self.repository.contracts.values()
            if contract.contract_role == contract_role
            and contract.status == "RELEASED"
            and self._contract_matches_quote(contract, quote)
        ]

    def _contract_matches_quote(self, contract: RateContract, quote: QuoteRequest) -> bool:
        for field in ("company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id"):
            expected = getattr(contract, field)
            actual = getattr(quote, field)
            if expected is not None and actual is not None and expected != actual:
                return False
        return any(self._entry_matches_quote(line.model_dump(), quote) for line in contract.lines)

    def _entry_matches_quote(self, row: dict[str, Any], quote: QuoteRequest) -> bool:
        for field in ("origin_code", "destination_code", "mode", "equipment_type", "commodity_code", "service_level"):
            expected = row.get(field)
            actual = getattr(quote, field)
            if expected and actual and str(expected).upper() != str(actual).upper():
                return False
        return True

    def _ranking_key(self, option: QuoteOption) -> tuple[int, Decimal, Decimal, int]:
        return (
            0 if option.policy_compliant else 1,
            -option.margin_percent,
            option.payer_total_amount,
            option.transit_time_days or 9999,
        )

    def _score_option(self, option: QuoteOption) -> Decimal:
        score = Decimal("100")
        score += option.margin_percent
        score -= option.payer_total_amount / Decimal("1000")
        if option.transit_time_days:
            score -= Decimal(option.transit_time_days)
        score += option.service_level_score
        if not option.policy_compliant:
            score -= Decimal("100")
        return money(score)

    def _quote_options_for_request(self, quote_request_id: int) -> list[QuoteOption]:
        rows = [
            option
            for option in self.repository.quote_options.values()
            if option.quote_request_id == quote_request_id
            and self._quote_option_is_available(option)
        ]
        rows.sort(key=lambda row: (row.rank if row.rank is not None else 999999, row.id))
        return rows

    def _delete_contract_options_for_quote(self, quote_request_id: int) -> None:
        for option_id, option in list(self.repository.quote_options.items()):
            if option.quote_request_id == quote_request_id and option.source_offer_id is None:
                del self.repository.quote_options[option_id]

    def _normalized_allocation_profile_version_payload(
        self,
        payload: ChargeAllocationProfileVersionCreate,
    ) -> dict[str, Any]:
        source_level = (payload.source_level or "").strip().upper()
        if source_level not in ALLOCATION_PROFILE_SOURCE_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported allocation profile source_level: {payload.source_level}",
            )
        source_to_house_driver = _clean_optional(
            payload.source_to_house_driver.upper() if payload.source_to_house_driver else None
        )
        house_to_item_driver = _clean_optional(
            payload.house_to_item_driver.upper() if payload.house_to_item_driver else None
        )
        final_posting_level = (payload.final_posting_level or "").strip().upper()
        if final_posting_level not in ALLOCATION_PROFILE_FINAL_POSTING_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported allocation profile final_posting_level: {payload.final_posting_level}",
            )
        if source_level == "HOUSE":
            source_to_house_driver = None
        elif source_to_house_driver is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_to_house_driver is required for SHIPMENT or CONTAINER source allocation.",
            )
        if final_posting_level == "HOUSE":
            house_to_item_driver = None
        elif house_to_item_driver is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="house_to_item_driver is required for PO_SCHEDULE_LINE posting.",
            )
        default_quantity_uom = _clean_optional(payload.default_quantity_uom.upper() if payload.default_quantity_uom else None)
        return {
            "source_level": source_level,
            "source_to_house_driver": source_to_house_driver,
            "house_to_item_driver": house_to_item_driver,
            "final_posting_level": final_posting_level,
            "default_quantity_uom": default_quantity_uom,
            "settings_json": dict(payload.settings_json or {}),
            "notes": _clean_optional(payload.notes),
        }

    def _allocation_profile_version_from_payload(
        self,
        *,
        profile_id: int,
        payload: ChargeAllocationProfileVersionCreate,
        version_number: int,
    ) -> ChargeAllocationProfileVersion:
        normalized = self._normalized_allocation_profile_version_payload(payload)
        return ChargeAllocationProfileVersion(
            id=self.repository.next_id("allocation_profile_version"),
            profile_id=profile_id,
            version_number=version_number,
            **normalized,
        )

    def _contract_line_from_payload(self, *, contract_id: int, line_payload: Any) -> ContractLine:
        allocation_profile_id, allocation_profile_version_id, _, _ = self._resolve_allocation_profile_reference(
            getattr(line_payload, "allocation_profile_id", None),
            getattr(line_payload, "allocation_profile_version_id", None),
        )
        return ContractLine(
            **line_payload.model_dump(exclude={"allocation_profile_id", "allocation_profile_version_id"}),
            id=self.repository.next_id("contract_line"),
            contract_id=contract_id,
            allocation_profile_id=allocation_profile_id,
            allocation_profile_version_id=allocation_profile_version_id,
        )

    def _resolve_effective_allocation(
        self,
        *,
        component: ChargeComponent,
        allocation_profile_id: int | None = None,
        allocation_profile_version_id: int | None = None,
    ) -> tuple[int | None, int | None, dict[str, Any] | None, dict[str, Any] | None]:
        profile_id = allocation_profile_id if allocation_profile_id is not None else component.allocation_profile_id
        version_id = (
            allocation_profile_version_id
            if allocation_profile_version_id is not None
            else component.allocation_profile_version_id
        )
        resolved_profile_id, resolved_version_id, profile, version = self._resolve_allocation_profile_reference(
            profile_id,
            version_id,
        )
        if profile is None or version is None:
            return None, None, None, None
        snapshot = self._allocation_snapshot(profile, version)
        return resolved_profile_id, resolved_version_id, snapshot, dict(snapshot)

    def _effective_allocation_value(
        self,
        snapshot: dict[str, Any] | None,
        key: str,
    ) -> str | None:
        value = (snapshot or {}).get(key)
        return _clean_optional(str(value)) if value is not None else None

    def _effective_allocation_basis(self, snapshot: dict[str, Any] | None) -> str | None:
        row = snapshot or {}
        return self._effective_allocation_value(row, "house_to_item_driver") or self._effective_allocation_value(
            row,
            "source_to_house_driver",
        )

    def _flatten_json_paths(self, value: Any, prefix: str = "") -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        flattened: dict[str, Any] = {}
        for key, nested_value in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(nested_value, dict):
                flattened.update(self._flatten_json_paths(nested_value, path))
            else:
                flattened[path] = nested_value
        return flattened

    def _business_date_context(self, document: ChargeDocument, line_payload: Any) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if document.document_date is not None:
            context["document_date"] = document.document_date
        charge_date = getattr(line_payload, "charge_date", None)
        if charge_date is not None:
            context["charge_date"] = charge_date
        context.update(self._flatten_json_paths(document.source_reference_snapshot_json or {}))
        context.update(self._flatten_json_paths(getattr(line_payload, "target_reference_snapshot_json", None) or {}))
        return context

    def _resolve_business_date_value(self, date_key: str, context: dict[str, Any]) -> date | None:
        normalized_key = (date_key or "").strip().upper()
        candidate_paths = BUSINESS_DATE_BASIS_KEY_CANDIDATES.get(normalized_key, ())
        for candidate in candidate_paths:
            value = context.get(candidate)
            if value is None and candidate.lower() != candidate:
                value = context.get(candidate.lower())
            resolved = _coerce_date(value)
            if resolved is not None:
                return resolved
        direct = _coerce_date(context.get(normalized_key.lower()))
        if direct is not None:
            return direct
        if normalized_key == "DOCUMENT_DATE":
            return _coerce_date(context.get("document_date"))
        if normalized_key == "MANUAL_LINE_DATE":
            return _coerce_date(context.get("charge_date"))
        return None

    def _resolve_business_date_component_reference(
        self,
        policy_mode: Any,
        profile_id: int | None,
    ) -> tuple[str, int | None]:
        normalized_mode = _business_date_policy_mode(policy_mode)
        resolved_profile_id = None if profile_id in (None, "", 0) else int(profile_id)
        if normalized_mode == "LEGACY_BASIS":
            if resolved_profile_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="business_date_profile_id is not allowed when business_date_policy_mode is LEGACY_BASIS.",
                )
            return normalized_mode, None
        if normalized_mode == "INHERIT_PROFILE":
            if resolved_profile_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="business_date_profile_id is not allowed when business_date_policy_mode is INHERIT_PROFILE.",
                )
            return normalized_mode, None
        if resolved_profile_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="business_date_profile_id is required when business_date_policy_mode is PROFILE_OVERRIDE.",
            )
        profile = self._require_business_date_profile(resolved_profile_id)
        self._require_published_business_date_profile_version(profile)
        return normalized_mode, resolved_profile_id

    def _resolve_business_date_profile_assignment_for_document(
        self,
        document: ChargeDocument,
        *,
        business_purpose: str = "EXCHANGE_RATE_DATE",
    ) -> BusinessDateProfileAssignment | None:
        if document.shipment_scope is None:
            return None
        candidates: list[tuple[str, int | None]] = []
        if document.customer_id is not None:
            candidates.append(("CUSTOMER", document.customer_id))
        if document.company_id is not None:
            candidates.append(("COMPANY", document.company_id))
        if document.forwarder_id is not None:
            candidates.append(("FORWARDER", document.forwarder_id))
        if document.carrier_id is not None:
            candidates.append(("CARRIER", document.carrier_id))
        if document.vendor_id is not None:
            candidates.append(("VENDOR", document.vendor_id))
        candidates.append(("GLOBAL", None))
        for scope_type, scope_id in candidates:
            matches = [
                assignment
                for assignment in self.repository.business_date_profile_assignments.values()
                if assignment.is_active
                and assignment.scope_type == scope_type
                and assignment.scope_id == scope_id
                and assignment.shipment_scope == document.shipment_scope
                and assignment.business_purpose == business_purpose
            ]
            if matches:
                return sorted(matches, key=lambda row: (row.priority, row.id))[0]
        return None

    def _resolve_business_date_date(
        self,
        *,
        component: ChargeComponent,
        document: ChargeDocument,
        line_payload: Any,
    ) -> date | None:
        context = self._business_date_context(document, line_payload)
        if getattr(line_payload, "exchange_rate_date", None) is not None:
            return _coerce_date(line_payload.exchange_rate_date)
        if getattr(line_payload, "charge_date", None) is not None:
            return _coerce_date(line_payload.charge_date)

        line_charge_date_basis = getattr(line_payload, "charge_date_basis", None)
        if line_charge_date_basis is not None:
            line_candidate_keys = LEGACY_BASIS_TO_BUSINESS_KEYS.get(
                str(line_charge_date_basis).strip().upper(),
                (),
            )
            for candidate_key in line_candidate_keys:
                resolved = self._resolve_business_date_value(candidate_key, context)
                if resolved is not None:
                    return resolved
            return _coerce_date(context.get("document_date"))

        candidate_keys: list[str] = []
        component_candidate_keys: list[str] = []
        if component.business_date_policy_mode == "PROFILE_OVERRIDE" and component.business_date_profile_id is not None:
            profile = self._require_business_date_profile(component.business_date_profile_id)
            version = self._require_published_business_date_profile_version(profile)
            component_candidate_keys.extend(step.date_key for step in version.steps)
        elif component.business_date_policy_mode == "INHERIT_PROFILE":
            assignment = self._resolve_business_date_profile_assignment_for_document(document)
            if assignment is not None:
                profile = self._require_business_date_profile(assignment.profile_id)
                version = self._require_published_business_date_profile_version(profile)
                component_candidate_keys.extend(step.date_key for step in version.steps)
        if component_candidate_keys:
            candidate_keys.extend(component_candidate_keys)
        else:
            candidate_keys.extend(LEGACY_BASIS_TO_BUSINESS_KEYS.get(component.charge_date_basis, ()))
        if not candidate_keys:
            candidate_keys.extend(("MANUAL_LINE_DATE", "DOCUMENT_DATE"))
        for candidate_key in candidate_keys:
            resolved = self._resolve_business_date_value(candidate_key, context)
            if resolved is not None:
                return resolved
        return _coerce_date(context.get("charge_date")) or _coerce_date(context.get("document_date"))

    def _published_business_date_profile_versions(
        self,
        profile: BusinessDateProfile,
    ) -> list[BusinessDateProfileVersion]:
        versions = [version for version in profile.versions if version.status == "PUBLISHED"]
        return sorted(versions, key=lambda row: (row.version_number, row.id))

    def _require_published_business_date_profile_version(
        self,
        profile: BusinessDateProfile,
    ) -> BusinessDateProfileVersion:
        versions = self._published_business_date_profile_versions(profile)
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Business date profile does not have a published version.",
            )
        return versions[-1]

    def _normalized_business_date_profile_version_payload(
        self,
        payload: BusinessDateProfileVersionCreate,
    ) -> dict[str, Any]:
        steps: list[BusinessDateProfileStep] = []
        normalized_steps: list[dict[str, Any]] = []
        seen_step_numbers: set[int] = set()
        if not payload.steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one business date profile step is required.",
            )
        for step in payload.steps:
            step_number = int(step.step_number)
            if step_number <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Business date profile step_number must be greater than zero.",
                )
            if step_number in seen_step_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate business date profile step_number: {step_number}",
                )
            seen_step_numbers.add(step_number)
            date_key = step.date_key.strip().upper()
            if date_key not in BUSINESS_DATE_BASIS_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported business date profile date_key: {step.date_key}",
                )
            normalized_steps.append(
                {
                    "step_number": step_number,
                    "date_key": date_key,
                    "notes": _clean_optional(step.notes),
                }
            )
        normalized_steps.sort(key=lambda row: row["step_number"])
        return {
            "steps": normalized_steps,
            "notes": _clean_optional(payload.notes),
        }

    def _business_date_profile_version_from_payload(
        self,
        *,
        profile_id: int,
        payload: BusinessDateProfileVersionCreate,
        version_number: int,
    ) -> BusinessDateProfileVersion:
        normalized = self._normalized_business_date_profile_version_payload(payload)
        steps: list[BusinessDateProfileStep] = []
        version_id = self.repository.next_id("business_date_profile_version")
        for step_payload in normalized["steps"]:
            steps.append(
                BusinessDateProfileStep(
                    id=self.repository.next_id("business_date_profile_step"),
                    version_id=version_id,
                    step_number=int(step_payload["step_number"]),
                    date_key=str(step_payload["date_key"]),
                    notes=_clean_optional(step_payload.get("notes")),
                )
            )
        return BusinessDateProfileVersion(
            id=version_id,
            profile_id=profile_id,
            version_number=version_number,
            steps=steps,
            **{key: value for key, value in normalized.items() if key != "steps"},
        )

    def _business_date_profile_assignment_from_payload(
        self,
        *,
        profile_id: int,
        payload: BusinessDateProfileAssignmentCreate,
        assignment_id: int,
    ) -> BusinessDateProfileAssignment:
        scope_type = payload.scope_type.strip().upper()
        if scope_type not in BUSINESS_DATE_ASSIGNMENT_SCOPE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported business date assignment scope_type: {payload.scope_type}",
            )
        scope_id = None if scope_type == "GLOBAL" else payload.scope_id
        if scope_type != "GLOBAL" and scope_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id is required for non-global business date profile assignments.",
            )
        if scope_type == "GLOBAL" and scope_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id must be omitted for global business date profile assignments.",
            )
        shipment_scope = payload.shipment_scope.strip().upper()
        if shipment_scope not in BUSINESS_DATE_SHIPMENT_SCOPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported business date assignment shipment_scope: {payload.shipment_scope}",
            )
        business_purpose = payload.business_purpose.strip().upper()
        if business_purpose not in BUSINESS_DATE_PURPOSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported business date assignment business_purpose: {payload.business_purpose}",
            )
        return BusinessDateProfileAssignment(
            id=assignment_id,
            profile_id=profile_id,
            scope_type=scope_type,  # type: ignore[arg-type]
            scope_id=int(scope_id) if scope_id is not None else None,
            owner_scope_key=scope_type if scope_id is None else f"{scope_type}:{int(scope_id)}",
            shipment_scope=shipment_scope,  # type: ignore[arg-type]
            business_purpose=business_purpose,  # type: ignore[arg-type]
            priority=int(payload.priority),
            is_active=bool(payload.is_active),
        )

    def _business_date_profile_assignment_exists(
        self,
        assignment: BusinessDateProfileAssignment,
        *,
        ignore_assignment_id: int | None = None,
    ) -> bool:
        for existing in self.repository.business_date_profile_assignments.values():
            if ignore_assignment_id is not None and existing.id == ignore_assignment_id:
                continue
            if (
                existing.owner_scope_key == assignment.owner_scope_key
                and existing.shipment_scope == assignment.shipment_scope
                and existing.business_purpose == assignment.business_purpose
            ):
                return True
        return False

    def _require_business_date_profile(self, profile_id: int) -> BusinessDateProfile:
        profile = self.repository.business_date_profiles.get(int(profile_id))
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown business date profile id: {profile_id}",
            )
        return profile

    def _require_business_date_profile_version(self, version_id: int) -> BusinessDateProfileVersion:
        version = self.repository.business_date_profile_versions.get(int(version_id))
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown business date profile version id: {version_id}",
            )
        if version.status not in BUSINESS_DATE_PROFILE_VERSION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unsupported business date profile version status: {version.status}",
            )
        return version

    def _require_business_date_profile_assignment(self, assignment_id: int) -> BusinessDateProfileAssignment:
        assignment = self.repository.business_date_profile_assignments.get(int(assignment_id))
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown business date profile assignment id: {assignment_id}",
            )
        return assignment

    def _template_steps_from_payload(
        self,
        template_id: int,
        payload: CalculationTemplatePayload,
    ) -> list[CalculationTemplateStep]:
        steps: list[CalculationTemplateStep] = []
        for step in payload.steps:
            self._require_component(step.charge_component_code)
            rate_book = (
                self._require_rate_book(step.rate_book_id)
                if step.rate_book_id is not None
                else None
            )
            steps.append(
                CalculationTemplateStep(
                    **step.model_dump(exclude={"charge_component_code"}),
                    id=self.repository.next_id("calculation_template_step"),
                    template_id=template_id,
                    charge_component_code=step.charge_component_code.upper(),
                    rate_book_code=rate_book.rate_book_code if rate_book else None,
                    rate_book_name=rate_book.rate_book_name if rate_book else None,
                )
            )
        steps.sort(key=lambda row: (row.step_number, row.id))
        return steps

    def _allocation_snapshot(
        self,
        profile: ChargeAllocationProfile,
        version: ChargeAllocationProfileVersion,
    ) -> dict[str, Any]:
        return {
            "profile_id": profile.id,
            "profile_code": profile.profile_code,
            "profile_name": profile.profile_name,
            "profile_version_id": version.id,
            "profile_version_number": version.version_number,
            "source_level": version.source_level,
            "source_to_house_driver": version.source_to_house_driver,
            "house_to_item_driver": version.house_to_item_driver,
            "final_posting_level": version.final_posting_level,
            "default_quantity_uom": version.default_quantity_uom,
            "settings_json": dict(version.settings_json or {}),
            "notes": version.notes,
        }

    def _require_component(self, component_code: str) -> ChargeComponent:
        component = self.repository.components_by_code.get(component_code)
        if component is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown charge component: {component_code}")
        return component

    def _require_component_by_id(self, component_id: int) -> ChargeComponent:
        component = self.repository.components.get(int(component_id))
        if component is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown charge component id: {component_id}")
        return component

    def _require_component_alias(self, alias_id: int) -> ChargeComponentAlias:
        alias = self.repository.component_aliases.get(int(alias_id))
        if alias is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown charge component alias: {alias_id}")
        return alias

    def _require_allocation_profile(self, profile_id: int) -> ChargeAllocationProfile:
        profile = self.repository.allocation_profiles.get(int(profile_id))
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown charge allocation profile id: {profile_id}",
            )
        return profile

    def _require_allocation_profile_version(self, version_id: int) -> ChargeAllocationProfileVersion:
        version = self.repository.allocation_profile_versions.get(int(version_id))
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown charge allocation profile version id: {version_id}",
            )
        if version.status not in ALLOCATION_PROFILE_VERSION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unsupported charge allocation profile version status: {version.status}",
            )
        return version

    def _resolve_allocation_profile_reference(
        self,
        profile_id: int | None,
        version_id: int | None,
    ) -> tuple[int | None, int | None, ChargeAllocationProfile | None, ChargeAllocationProfileVersion | None]:
        if profile_id is None and version_id is None:
            return None, None, None, None
        profile: ChargeAllocationProfile | None = None
        version: ChargeAllocationProfileVersion | None = None
        if version_id is not None:
            version = self._require_allocation_profile_version(version_id)
            profile = self._require_allocation_profile(version.profile_id)
        if profile_id is not None:
            profile = self._require_allocation_profile(profile_id)
        if profile is None:
            return None, None, None, None
        if version is not None and version.profile_id != profile.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="allocation_profile_version_id does not belong to allocation_profile_id.",
            )
        if version is None:
            if profile.published_version_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Charge allocation profile does not have a published version.",
                )
            version = self._require_allocation_profile_version(profile.published_version_id)
        return profile.id, version.id, profile, version

    def _alias_from_payload(
        self,
        payload: ChargeComponentAliasPayload,
        *,
        component: ChargeComponent,
        alias_id: int,
    ) -> ChargeComponentAlias:
        raw_label = payload.raw_label.strip()
        if not raw_label:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="raw_label is required")
        allocation_override_mode = (payload.allocation_override_mode or "OVERRIDE_PROFILE").strip().upper()
        if allocation_override_mode not in ALLOCATION_OVERRIDE_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported allocation_override_mode: {payload.allocation_override_mode}",
            )
        final_posting_level = _clean_optional(
            payload.final_posting_level.upper() if payload.final_posting_level else None
        ) or "PO_SCHEDULE_LINE"
        if final_posting_level not in ALLOCATION_PROFILE_FINAL_POSTING_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported final_posting_level: {payload.final_posting_level}",
            )
        override_final_posting_level = _clean_optional(
            payload.override_final_posting_level.upper()
            if payload.override_final_posting_level
            else None
        )
        if (
            override_final_posting_level is not None
            and override_final_posting_level not in ALLOCATION_PROFILE_FINAL_POSTING_LEVELS
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported override_final_posting_level: {payload.override_final_posting_level}",
            )
        (
            override_allocation_profile_id,
            override_allocation_profile_version_id,
            _,
            _,
        ) = self._resolve_allocation_profile_reference(
            payload.override_allocation_profile_id,
            payload.override_allocation_profile_version_id,
        )
        return ChargeComponentAlias(
            id=alias_id,
            raw_label=raw_label,
            normalized_label=_alias_normalized_label(raw_label),
            charge_component_id=component.id,
            document_kind=payload.document_kind.strip().upper() or "CHARGE_PROPOSAL",
            template_key=_clean_optional(payload.template_key),
            source_section=_clean_optional(payload.source_section),
            customer_id=payload.customer_id,
            forwarder_id=payload.forwarder_id,
            transport_mode=payload.transport_mode.strip().upper() if payload.transport_mode else None,
            default_calculation_basis=payload.default_calculation_basis.strip().upper() or "DOCUMENT",
            default_charge_level=payload.default_charge_level.strip().upper() or "SHIPMENT",
            default_allocation_basis=payload.default_allocation_basis.strip().upper() if payload.default_allocation_basis else None,
            container_house_allocation_basis=(
                payload.container_house_allocation_basis.strip().upper()
                if payload.container_house_allocation_basis
                else (payload.default_allocation_basis.strip().upper() if payload.default_allocation_basis else None)
            ),
            house_item_allocation_basis=(
                payload.house_item_allocation_basis.strip().upper()
                if payload.house_item_allocation_basis
                else (payload.default_allocation_basis.strip().upper() if payload.default_allocation_basis else None)
            ),
            final_posting_level=final_posting_level,
            default_quantity_uom=payload.default_quantity_uom.strip().upper() if payload.default_quantity_uom else None,
            allocation_override_mode=allocation_override_mode,  # type: ignore[arg-type]
            override_allocation_profile_id=override_allocation_profile_id,
            override_allocation_profile_version_id=override_allocation_profile_version_id,
            override_charge_level=_clean_optional(payload.override_charge_level.upper() if payload.override_charge_level else None),
            override_allocation_basis=_clean_optional(
                payload.override_allocation_basis.upper() if payload.override_allocation_basis else None
            ),
            override_container_house_allocation_basis=_clean_optional(
                payload.override_container_house_allocation_basis.upper()
                if payload.override_container_house_allocation_basis
                else None
            ),
            override_house_item_allocation_basis=_clean_optional(
                payload.override_house_item_allocation_basis.upper()
                if payload.override_house_item_allocation_basis
                else None
            ),
            override_final_posting_level=override_final_posting_level,
            override_quantity_uom=_clean_optional(payload.override_quantity_uom.upper() if payload.override_quantity_uom else None),
            priority=payload.priority,
            is_active=payload.is_active,
            component_code=component.component_code,
            component_name=component.component_name,
        )

    def _alias_key_exists(
        self,
        alias: ChargeComponentAlias,
        *,
        ignore_alias_id: int | None = None,
    ) -> bool:
        for existing in self.repository.component_aliases.values():
            if ignore_alias_id is not None and existing.id == ignore_alias_id:
                continue
            if (
                existing.document_kind == alias.document_kind
                and existing.template_key == alias.template_key
                and existing.source_section == alias.source_section
                and existing.normalized_label == alias.normalized_label
                and existing.customer_id == alias.customer_id
                and existing.forwarder_id == alias.forwarder_id
                and existing.transport_mode == alias.transport_mode
            ):
                return True
        return False

    def _require_rate_book(self, rate_book_id: int) -> RateBook:
        row = self.repository.rate_books.get(rate_book_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate book not found")
        return row

    def _require_calculation_template(
        self,
        calculation_template_id: int,
    ) -> CalculationTemplate:
        row = self.repository.calculation_templates.get(calculation_template_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation template not found")
        return row

    def _require_contract(self, contract_id: int) -> RateContract:
        row = self.repository.contracts.get(contract_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
        return row

    def _require_quote_request(self, quote_request_id: int) -> QuoteRequest:
        row = self.repository.quote_requests.get(quote_request_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote request not found")
        return row

    def _require_quote_option(self, quote_option_id: int) -> QuoteOption:
        row = self.repository.quote_options.get(quote_option_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote option not found")
        return row

    def _require_quote_offer(self, quote_offer_id: int) -> QuoteOffer:
        row = self.repository.quote_offers.get(quote_offer_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote offer not found")
        return row

    def _option_for_offer(self, quote_offer_id: int) -> QuoteOption | None:
        for option in self.repository.quote_options.values():
            if option.source_offer_id == quote_offer_id:
                return option
        return None

    def _quote_option_is_available(self, option: QuoteOption) -> bool:
        if option.source_offer_id is None:
            return True
        offer = self.repository.quote_offers.get(option.source_offer_id)
        return offer is not None and offer.status.upper() == "SUBMITTED"

    def _assert_offer_can_change(
        self,
        quote: QuoteRequest,
        offer: QuoteOffer,
        option: QuoteOption | None,
    ) -> None:
        if quote.status.upper() in {"AWARDED", "CANCELLED", "EXPIRED"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quote offer cannot be changed after the quote is closed.",
            )
        if offer.status.upper() != "SUBMITTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only submitted quote offers can be changed.",
            )
        if option is not None and any(document.quote_option_id == option.id for document in self.repository.documents.values()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Awarded quote offer options cannot be changed.",
            )

    def _sync_offer_option(self, offer: QuoteOffer, option: QuoteOption | None) -> None:
        if option is None:
            return
        amount = money(offer.amount)
        option.option_name = offer.offer_number or option.option_name
        option.payer_total_amount = amount
        option.payee_total_amount = amount
        option.margin_amount = Decimal("0.00")
        option.margin_percent = Decimal("0.00")
        option.transit_time_days = offer.transit_time_days
        option.service_level_score = dec(offer.performance_score)
        option.expires_at = offer.expires_at
        option.rank = None
        option.score = None
        for line in option.lines:
            line.payee_party_ref = offer.provider_party_ref
            line.party_role_ref = offer.provider_role_ref
            line.description = offer.offer_number or "Provider Offer Total"
            line.amount = amount
            line.currency = offer.currency

    def _require_quote_commitment(self, commitment_id: int) -> QuoteCommitment:
        row = self.repository.quote_commitments.get(commitment_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote commitment not found")
        return row

    def _require_quote_commitment_consumption(self, consumption_id: int) -> QuoteCommitmentConsumption:
        row = self.repository.quote_commitment_consumptions.get(consumption_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote commitment consumption not found")
        return row

    def _require_document(self, charge_document_id: int) -> ChargeDocument:
        row = self.repository.documents.get(charge_document_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge document not found")
        return row

    def _require_invoice(self, invoice_id: int) -> ChargeInvoice:
        row = self.repository.invoices.get(invoice_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return row

    def _sync_invoice_document_summary(self, invoice: ChargeInvoice) -> None:
        document = self.repository.documents.get(invoice.charge_document_id)
        if document is None:
            return
        invoice.charge_document_number = document.document_number
        invoice.charge_document_status = document.status
