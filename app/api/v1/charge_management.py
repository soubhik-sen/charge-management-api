from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.domain.models import (
    ChargeActionResponse,
    ChargeAllocationProfile,
    ChargeAllocationProfileCreate,
    ChargeAllocationProfileListResponse,
    ChargeAllocationProfileVersion,
    ChargeAllocationProfileVersionCreate,
    BusinessDateProfile,
    BusinessDateProfileAssignment,
    BusinessDateProfileAssignmentCreate,
    BusinessDateProfileAssignmentListResponse,
    BusinessDateProfileCreate,
    BusinessDateProfileListResponse,
    BusinessDateProfileVersion,
    BusinessDateProfileVersionCreate,
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
    ChargeReverseRequest,
    CalculationTemplate,
    CalculationTemplateListResponse,
    CalculationTemplatePayload,
    CalculationTemplateWorkspace,
    ContractDeterminationResponse,
    ContractWorkspace,
    InvoiceMatchResponse,
    QuoteAwardRequest,
    QuoteAwardResponse,
    QuoteCommitmentConsumeRequest,
    QuoteCommitmentConsumeResponse,
    QuoteCommitmentConsumptionReverseRequest,
    QuoteCommitmentMatchRequest,
    QuoteCommitmentMatchResponse,
    QuoteOffer,
    QuoteOfferCreate,
    QuoteOfferWithdrawRequest,
    QuoteOfferWorkspace,
    QuoteOfferWorkspaceUpdate,
    QuoteRequest,
    QuoteRequestCreate,
    QuoteRequestListResponse,
    QuoteRequestWorkspace,
    QuoteRequestWorkspaceUpdate,
    RankResponse,
    RateBook,
    RateBookListResponse,
    RateBookPayload,
    RateBookWorkspace,
    RateContract,
    RateContractListResponse,
    RateContractPayload,
    RateContractUpdate,
    RateResponse,
)
from app.domain.service import ChargeManagementService, InMemoryChargeRepository
from app.infrastructure.adapters import DefaultPolicyAdapter, Principal, require_bearer_principal

router = APIRouter()

repository = InMemoryChargeRepository()
service = ChargeManagementService(repository)
policy = DefaultPolicyAdapter()


def _scope_from_payload(payload: object | None = None) -> dict[str, int | None]:
    if payload is None:
        return {}
    return {
        key: getattr(payload, key, None)
        for key in ("company_id", "customer_id", "vendor_id", "forwarder_id", "carrier_id")
        if hasattr(payload, key)
    }


def _allow(principal: Principal, action: str, scope: dict[str, int | None] | None = None) -> None:
    policy.assert_allowed(principal, action, scope or {})


@router.get("/initialization-data", response_model=ChargeInitializationData)
def get_initialization_data(
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeInitializationData:
    _allow(principal, "charge.initialization_data")
    return service.initialization_data()


@router.get("/allocation-profiles", response_model=ChargeAllocationProfileListResponse)
def list_allocation_profiles(
    q: str | None = Query(default=None),
    source_level: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeAllocationProfileListResponse:
    _allow(principal, "charge.allocation_profiles.list")
    return service.list_allocation_profiles(
        search=q,
        source_level=source_level,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/allocation-profiles", response_model=ChargeAllocationProfile, status_code=201)
def create_allocation_profile(
    payload: ChargeAllocationProfileCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeAllocationProfile:
    _allow(principal, "charge.allocation_profiles.create")
    return service.create_allocation_profile(payload)


@router.post("/allocation-profiles/{profile_id}/versions", response_model=ChargeAllocationProfile, status_code=201)
def create_allocation_profile_version(
    profile_id: int,
    payload: ChargeAllocationProfileVersionCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeAllocationProfile:
    _allow(principal, "charge.allocation_profiles.versions.create")
    return service.create_allocation_profile_version(profile_id, payload)


@router.put("/allocation-profile-versions/{version_id}", response_model=ChargeAllocationProfileVersion)
def update_allocation_profile_version(
    version_id: int,
    payload: ChargeAllocationProfileVersionCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeAllocationProfileVersion:
    _allow(principal, "charge.allocation_profiles.versions.update")
    return service.update_allocation_profile_version(version_id, payload)


@router.post("/allocation-profile-versions/{version_id}/publish", response_model=ChargeAllocationProfile)
def publish_allocation_profile_version(
    version_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeAllocationProfile:
    _allow(principal, "charge.allocation_profiles.versions.publish")
    return service.publish_allocation_profile_version(version_id)


@router.get("/business-date-profiles", response_model=BusinessDateProfileListResponse)
def list_business_date_profiles(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileListResponse:
    _allow(principal, "charge.business_date_profiles.list")
    return service.list_business_date_profiles(
        search=q,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("/business-date-profiles", response_model=BusinessDateProfile, status_code=201)
def create_business_date_profile(
    payload: BusinessDateProfileCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfile:
    _allow(principal, "charge.business_date_profiles.create")
    return service.create_business_date_profile(payload)


@router.get("/business-date-profiles/{profile_id}", response_model=BusinessDateProfile)
def get_business_date_profile(
    profile_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfile:
    _allow(principal, "charge.business_date_profiles.read")
    return service.get_business_date_profile(profile_id)


@router.put("/business-date-profiles/{profile_id}", response_model=BusinessDateProfile)
def update_business_date_profile(
    profile_id: int,
    payload: BusinessDateProfileCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfile:
    _allow(principal, "charge.business_date_profiles.update")
    return service.update_business_date_profile(profile_id, payload)


@router.post("/business-date-profiles/{profile_id}/versions", response_model=BusinessDateProfile, status_code=201)
def create_business_date_profile_version(
    profile_id: int,
    payload: BusinessDateProfileVersionCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfile:
    _allow(principal, "charge.business_date_profiles.versions.create")
    return service.create_business_date_profile_version(profile_id, payload)


@router.put("/business-date-profile-versions/{version_id}", response_model=BusinessDateProfileVersion)
def update_business_date_profile_version(
    version_id: int,
    payload: BusinessDateProfileVersionCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileVersion:
    _allow(principal, "charge.business_date_profiles.versions.update")
    return service.update_business_date_profile_version(version_id, payload)


@router.post("/business-date-profile-versions/{version_id}/publish", response_model=BusinessDateProfile)
def publish_business_date_profile_version(
    version_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfile:
    _allow(principal, "charge.business_date_profiles.versions.publish")
    return service.publish_business_date_profile_version(version_id)


@router.get("/business-date-profiles/{profile_id}/assignments", response_model=BusinessDateProfileAssignmentListResponse)
def list_business_date_profile_assignments(
    profile_id: int,
    scope_type: str | None = Query(default=None),
    scope_id: int | None = Query(default=None),
    shipment_scope: str | None = Query(default=None),
    business_purpose: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileAssignmentListResponse:
    _allow(principal, "charge.business_date_profiles.assignments.list")
    return service.list_business_date_profile_assignments(
        profile_id,
        scope_type=scope_type,
        scope_id=scope_id,
        shipment_scope=shipment_scope,
        business_purpose=business_purpose,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.post("/business-date-profiles/{profile_id}/assignments", response_model=BusinessDateProfileAssignment, status_code=201)
def create_business_date_profile_assignment(
    profile_id: int,
    payload: BusinessDateProfileAssignmentCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileAssignment:
    _allow(principal, "charge.business_date_profiles.assignments.create")
    return service.create_business_date_profile_assignment(profile_id, payload)


@router.put("/business-date-profile-assignments/{assignment_id}", response_model=BusinessDateProfileAssignment)
def update_business_date_profile_assignment(
    assignment_id: int,
    payload: BusinessDateProfileAssignmentCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileAssignment:
    _allow(principal, "charge.business_date_profiles.assignments.update")
    return service.update_business_date_profile_assignment(assignment_id, payload)


@router.delete("/business-date-profile-assignments/{assignment_id}", response_model=BusinessDateProfileAssignment)
def delete_business_date_profile_assignment(
    assignment_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> BusinessDateProfileAssignment:
    _allow(principal, "charge.business_date_profiles.assignments.delete")
    return service.delete_business_date_profile_assignment(assignment_id)


@router.get("/components", response_model=ChargeComponentListResponse)
def list_components(
    active_only: bool | None = Query(default=None),
    category: str | None = Query(default=None),
    calculation_basis: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponentListResponse:
    _allow(principal, "charge.components.list")
    return service.list_components(
        active_only=active_only,
        category=category,
        calculation_basis=calculation_basis,
        search=q,
        limit=limit,
        offset=offset,
    )


@router.post("/components", response_model=ChargeComponent, status_code=201)
def create_component(
    payload: ChargeComponentPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponent:
    _allow(principal, "charge.components.create")
    return service.create_component(payload)


@router.put("/components/{component_id}", response_model=ChargeComponent)
def update_component(
    component_id: int,
    payload: ChargeComponentPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponent:
    _allow(principal, "charge.components.update")
    return service.update_component(component_id, payload)


@router.delete("/components/{component_id}", response_model=ChargeComponent)
def delete_component(
    component_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponent:
    _allow(principal, "charge.components.delete")
    return service.delete_component(component_id)


@router.get("/component-aliases", response_model=ChargeComponentAliasListResponse)
def list_component_aliases(
    document_kind: str | None = Query(default=None),
    template_key: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    forwarder_id: int | None = Query(default=None),
    transport_mode: str | None = Query(default=None),
    charge_component_id: int | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponentAliasListResponse:
    _allow(principal, "charge.component_aliases.list")
    return service.list_component_aliases(
        document_kind=document_kind,
        template_key=template_key,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        transport_mode=transport_mode,
        charge_component_id=charge_component_id,
        active_only=active_only,
        search=q,
        limit=limit,
        offset=offset,
    )


@router.post("/component-aliases", response_model=ChargeComponentAlias, status_code=201)
def create_component_alias(
    payload: ChargeComponentAliasPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponentAlias:
    _allow(principal, "charge.component_aliases.create")
    return service.create_component_alias(payload)


@router.put("/component-aliases/{alias_id}", response_model=ChargeComponentAlias)
def update_component_alias(
    alias_id: int,
    payload: ChargeComponentAliasPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponentAlias:
    _allow(principal, "charge.component_aliases.update")
    return service.update_component_alias(alias_id, payload)


@router.delete("/component-aliases/{alias_id}", response_model=ChargeComponentAlias)
def delete_component_alias(
    alias_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeComponentAlias:
    _allow(principal, "charge.component_aliases.delete")
    return service.delete_component_alias(alias_id)


@router.post("/rate-books", response_model=RateBook, status_code=201)
def create_rate_book(
    payload: RateBookPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> RateBook:
    _allow(principal, "charge.rate_books.create")
    return service.create_rate_book(payload)


@router.get("/rate-books", response_model=RateBookListResponse)
def list_rate_books(
    q: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> RateBookListResponse:
    _allow(principal, "charge.rate_books.list")
    return service.list_rate_books(
        search=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get("/rate-books/{rate_book_id}/workspace", response_model=RateBookWorkspace)
def get_rate_book_workspace(
    rate_book_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> RateBookWorkspace:
    _allow(principal, "charge.rate_books.workspace.read")
    return service.get_rate_book_workspace(rate_book_id)


@router.put("/rate-books/{rate_book_id}/workspace", response_model=RateBookWorkspace)
def update_rate_book_workspace(
    rate_book_id: int,
    payload: RateBookPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> RateBookWorkspace:
    _allow(principal, "charge.rate_books.workspace.update")
    return service.update_rate_book_workspace(rate_book_id, payload)


@router.post("/calculation-templates", response_model=CalculationTemplate, status_code=201)
def create_calculation_template(
    payload: CalculationTemplatePayload,
    principal: Principal = Depends(require_bearer_principal),
) -> CalculationTemplate:
    _allow(principal, "charge.calculation_templates.create")
    return service.create_calculation_template(payload)


@router.get("/calculation-templates", response_model=CalculationTemplateListResponse)
def list_calculation_templates(
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    active_only: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> CalculationTemplateListResponse:
    _allow(principal, "charge.calculation_templates.list")
    return service.list_calculation_templates(
        status_filter=status_filter,
        search=q,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/calculation-templates/{calculation_template_id}/workspace",
    response_model=CalculationTemplateWorkspace,
)
def get_calculation_template_workspace(
    calculation_template_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> CalculationTemplateWorkspace:
    _allow(principal, "charge.calculation_templates.workspace.read")
    return service.get_calculation_template_workspace(calculation_template_id)


@router.put(
    "/calculation-templates/{calculation_template_id}/workspace",
    response_model=CalculationTemplateWorkspace,
)
def update_calculation_template_workspace(
    calculation_template_id: int,
    payload: CalculationTemplatePayload,
    principal: Principal = Depends(require_bearer_principal),
) -> CalculationTemplateWorkspace:
    _allow(principal, "charge.calculation_templates.workspace.update")
    return service.update_calculation_template_workspace(
        calculation_template_id,
        payload,
    )


@router.post("/contracts", response_model=RateContract, status_code=201)
def create_contract(
    payload: RateContractPayload,
    principal: Principal = Depends(require_bearer_principal),
) -> RateContract:
    _allow(principal, "charge.contracts.create", _scope_from_payload(payload))
    return service.create_contract(payload)


@router.get("/contracts", response_model=RateContractListResponse)
def list_contracts(
    contract_role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None),
    forwarder_id: int | None = Query(default=None),
    carrier_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> RateContractListResponse:
    _allow(principal, "charge.contracts.list")
    return service.list_contracts(
        contract_role=contract_role,
        status_filter=status_filter,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        carrier_id=carrier_id,
        limit=limit,
        offset=offset,
    )


@router.post("/quote-requests", response_model=QuoteRequest, status_code=201)
def create_quote_request(
    payload: QuoteRequestCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteRequest:
    _allow(principal, "charge.quote_requests.create", _scope_from_payload(payload))
    return service.create_quote_request(payload)


@router.post("/quote-requests/{quote_request_id}/offers", response_model=QuoteOffer, status_code=201)
def create_quote_offer(
    quote_request_id: int,
    payload: QuoteOfferCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteOffer:
    _allow(principal, "charge.quote_requests.offers.create")
    return service.create_quote_offer(quote_request_id, payload)


@router.get("/quote-offers/{offer_id}/workspace", response_model=QuoteOfferWorkspace)
def get_quote_offer_workspace(
    offer_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteOfferWorkspace:
    _allow(principal, "charge.quote_offers.workspace.read")
    return service.get_quote_offer_workspace(offer_id)


@router.put("/quote-offers/{offer_id}/workspace", response_model=QuoteOfferWorkspace)
def update_quote_offer_workspace(
    offer_id: int,
    payload: QuoteOfferWorkspaceUpdate,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteOfferWorkspace:
    _allow(principal, "charge.quote_offers.workspace.update")
    return service.update_quote_offer_workspace(offer_id, payload)


@router.post("/quote-offers/{offer_id}/withdraw", response_model=QuoteOfferWorkspace)
def withdraw_quote_offer(
    offer_id: int,
    payload: QuoteOfferWithdrawRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteOfferWorkspace:
    _allow(principal, "charge.quote_offers.withdraw")
    return service.withdraw_quote_offer(offer_id, payload)


@router.get("/quote-requests", response_model=QuoteRequestListResponse)
def list_quote_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    mode: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    forwarder_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteRequestListResponse:
    _allow(principal, "charge.quote_requests.list")
    return service.list_quote_requests(
        status_filter=status_filter,
        mode=mode,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        limit=limit,
        offset=offset,
    )


@router.get("/quote-requests/{quote_request_id}/workspace", response_model=QuoteRequestWorkspace)
def get_quote_request_workspace(
    quote_request_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteRequestWorkspace:
    _allow(principal, "charge.quote_requests.workspace.read")
    return service.get_quote_request_workspace(quote_request_id)


@router.put("/quote-requests/{quote_request_id}/workspace", response_model=QuoteRequestWorkspace)
def update_quote_request_workspace(
    quote_request_id: int,
    payload: QuoteRequestWorkspaceUpdate,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteRequestWorkspace:
    _allow(principal, "charge.quote_requests.workspace.update", _scope_from_payload(payload))
    return service.update_quote_request_workspace(quote_request_id, payload)


@router.post(
    "/quote-requests/{quote_request_id}/determine-contracts",
    response_model=ContractDeterminationResponse,
)
def determine_contracts(
    quote_request_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ContractDeterminationResponse:
    _allow(principal, "charge.quote_requests.determine_contracts")
    return service.determine_contracts(quote_request_id)


@router.post("/quote-requests/{quote_request_id}/rate", response_model=RateResponse)
def rate_quote_request(
    quote_request_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> RateResponse:
    _allow(principal, "charge.quote_requests.rate")
    return service.rate_quote_request(quote_request_id)


@router.post("/quote-requests/{quote_request_id}/rank", response_model=RankResponse)
def rank_quote_request(
    quote_request_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> RankResponse:
    _allow(principal, "charge.quote_requests.rank")
    return service.rank_quote_request(quote_request_id)


@router.post("/quote-requests/{quote_request_id}/award", response_model=QuoteAwardResponse)
def award_quote_request(
    quote_request_id: int,
    payload: QuoteAwardRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteAwardResponse:
    _allow(principal, "charge.quote_requests.award")
    return service.award_quote_request(quote_request_id, payload)


@router.post("/quote-commitments/match", response_model=QuoteCommitmentMatchResponse)
def match_quote_commitments(
    payload: QuoteCommitmentMatchRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteCommitmentMatchResponse:
    _allow(principal, "charge.quote_commitments.match", _scope_from_payload(payload))
    return service.match_quote_commitments(payload)


@router.post("/quote-commitments/{commitment_id}/consume", response_model=QuoteCommitmentConsumeResponse)
def consume_quote_commitment(
    commitment_id: int,
    payload: QuoteCommitmentConsumeRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteCommitmentConsumeResponse:
    _allow(principal, "charge.quote_commitments.consume")
    return service.consume_quote_commitment(commitment_id, payload)


@router.post("/quote-commitment-consumptions/{consumption_id}/reverse", response_model=QuoteCommitmentConsumeResponse)
def reverse_quote_commitment_consumption(
    consumption_id: int,
    payload: QuoteCommitmentConsumptionReverseRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> QuoteCommitmentConsumeResponse:
    _allow(principal, "charge.quote_commitment_consumptions.reverse")
    return service.reverse_quote_commitment_consumption(consumption_id, payload)


@router.get("/contracts/{contract_id}/workspace", response_model=ContractWorkspace)
def get_contract_workspace(
    contract_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ContractWorkspace:
    _allow(principal, "charge.contracts.workspace.read")
    return service.get_contract_workspace(contract_id)


@router.put("/contracts/{contract_id}/workspace", response_model=ContractWorkspace)
def update_contract_workspace(
    contract_id: int,
    payload: RateContractUpdate,
    principal: Principal = Depends(require_bearer_principal),
) -> ContractWorkspace:
    _allow(principal, "charge.contracts.workspace.update")
    return service.update_contract_workspace(contract_id, payload)


@router.post("/contracts/{contract_id}/release", response_model=RateContract)
def release_contract(
    contract_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> RateContract:
    _allow(principal, "charge.contracts.release")
    return service.release_contract(contract_id)


@router.post("/charge-documents", response_model=ChargeDocument, status_code=201)
def create_charge_document(
    payload: ChargeDocumentCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeDocument:
    _allow(principal, "charge.charge_documents.create", _scope_from_payload(payload))
    return service.create_charge_document(payload)


@router.get("/charge-documents", response_model=ChargeDocumentListResponse)
def list_charge_documents(
    status_filter: str | None = Query(default=None, alias="status"),
    source_object_type: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    forwarder_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeDocumentListResponse:
    _allow(principal, "charge.charge_documents.list")
    return service.list_charge_documents(
        status_filter=status_filter,
        source_object_type=source_object_type,
        customer_id=customer_id,
        forwarder_id=forwarder_id,
        search=q,
        limit=limit,
        offset=offset,
    )


@router.delete("/charge-documents/{charge_document_id}", response_model=ChargeActionResponse)
def delete_charge_document(
    charge_document_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeActionResponse:
    _allow(principal, "charge.charge_documents.delete")
    return service.delete_charge_document(charge_document_id)


@router.get("/charge-documents/{charge_document_id}/workspace", response_model=ChargeDocumentWorkspace)
def get_charge_document_workspace(
    charge_document_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeDocumentWorkspace:
    _allow(principal, "charge.charge_documents.workspace.read")
    return service.get_charge_document_workspace(charge_document_id)


@router.put("/charge-documents/{charge_document_id}/workspace", response_model=ChargeDocumentWorkspace)
def update_charge_document_workspace(
    charge_document_id: int,
    payload: ChargeDocumentWorkspaceUpdate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeDocumentWorkspace:
    _allow(principal, "charge.charge_documents.workspace.update")
    return service.update_charge_document_workspace(charge_document_id, payload)


@router.post("/invoices", response_model=ChargeInvoice, status_code=201)
def create_invoice(
    payload: ChargeInvoiceCreate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeInvoice:
    _allow(principal, "charge.invoices.create")
    return service.create_invoice(payload)


@router.get("/invoices", response_model=ChargeInvoiceListResponse)
def list_invoices(
    charge_document_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeInvoiceListResponse:
    _allow(principal, "charge.invoices.list")
    return service.list_invoices(
        charge_document_id=charge_document_id,
        status_filter=status_filter,
        search=q,
        limit=limit,
        offset=offset,
    )


@router.get("/invoices/{invoice_id}/workspace", response_model=ChargeInvoiceWorkspace)
def get_invoice_workspace(
    invoice_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeInvoiceWorkspace:
    _allow(principal, "charge.invoices.workspace.read")
    return service.get_invoice_workspace(invoice_id)


@router.put("/invoices/{invoice_id}/workspace", response_model=ChargeInvoiceWorkspace)
def update_invoice_workspace(
    invoice_id: int,
    payload: ChargeInvoiceWorkspaceUpdate,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeInvoiceWorkspace:
    _allow(principal, "charge.invoices.workspace.update")
    return service.update_invoice_workspace(invoice_id, payload)


@router.post("/invoices/{invoice_id}/match", response_model=InvoiceMatchResponse)
def match_invoice(
    invoice_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> InvoiceMatchResponse:
    _allow(principal, "charge.invoices.match")
    return service.match_invoice(invoice_id)


@router.post("/charge-documents/{charge_document_id}/approve", response_model=ChargeActionResponse)
def approve_document(
    charge_document_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeActionResponse:
    _allow(principal, "charge.charge_documents.approve")
    return service.approve_document(charge_document_id)


@router.post("/charge-documents/{charge_document_id}/post-export", response_model=ChargeExportResponse)
def post_export(
    charge_document_id: int,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeExportResponse:
    _allow(principal, "charge.charge_documents.post_export")
    return service.post_export(charge_document_id)


@router.post("/charge-documents/{charge_document_id}/reverse", response_model=ChargeActionResponse)
def reverse_document(
    charge_document_id: int,
    payload: ChargeReverseRequest,
    principal: Principal = Depends(require_bearer_principal),
) -> ChargeActionResponse:
    _allow(principal, "charge.charge_documents.reverse")
    return service.reverse_document(charge_document_id, payload.reason)
