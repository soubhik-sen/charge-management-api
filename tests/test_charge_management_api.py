from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.charge_management import repository
from app.db.models import Base
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    repository.reset()


def test_requires_bearer_token() -> None:
    response = client.get("/api/v1/charge-management/initialization-data")
    assert response.status_code == 401


def test_initialization_data_has_seeded_components() -> None:
    response = client.get("/api/v1/charge-management/initialization-data", headers=AUTH)
    assert response.status_code == 200
    codes = {row["component_code"] for row in response.json()["components"]}
    assert "BASE_FREIGHT" in codes
    assert "MARGIN_MARKUP" in codes
    assert len(codes) == 32
    assert {row["charge_date_basis"] for row in response.json()["components"]} == {"DOCUMENT_DATE"}
    assert response.json()["settings"]["quotation_policy"] == "OPTIONAL"
    assert response.json()["settings"]["quote_acceptance_mode"] == "CUSTOMER_ACCEPTANCE"
    assert response.json()["settings"]["provider_cost_layer_enabled"] is False
    assert "REQUESTED" in response.json()["reference_data"]["quote_statuses"]
    assert "DIRECT_ONLY" in response.json()["reference_data"]["quotation_policies"]
    assert "AUTO_ACCEPT" in response.json()["reference_data"]["quote_acceptance_modes"]
    assert "PACKAGE" in response.json()["reference_data"]["bases"]
    assert "CALCULATION" in response.json()["reference_data"]["charge_line_roles"]
    assert "HOUSE" in response.json()["reference_data"]["charge_target_levels"]
    assert "PO_SCHEDULE_LINE" in response.json()["reference_data"]["charge_target_levels"]
    assert "HOUSE" in response.json()["reference_data"]["allocation_profile_source_levels"]
    assert "HOUSE" in response.json()["reference_data"]["allocation_profile_final_posting_levels"]
    assert response.json()["reference_data"]["allocation_profile_version_statuses"] == [
        "DRAFT",
        "PUBLISHED",
        "RETIRED",
    ]
    assert response.json()["reference_data"]["allocation_override_modes"] == [
        "INHERIT_PROFILE",
        "OVERRIDE_PROFILE",
        "NO_ALLOCATION",
    ]
    assert response.json()["reference_data"]["business_date_policy_modes"] == [
        "LEGACY_BASIS",
        "INHERIT_PROFILE",
        "PROFILE_OVERRIDE",
    ]
    assert "CUSTOMER" in response.json()["reference_data"]["business_date_assignment_scope_types"]
    assert response.json()["reference_data"]["business_date_shipment_scopes"] == ["OCEAN_HOUSE", "AIR_HOUSE"]
    assert response.json()["reference_data"]["business_date_purposes"] == ["EXCHANGE_RATE_DATE"]
    assert response.json()["reference_data"]["fx_rate_types"] == ["MID", "BUY", "SELL", "CUSTOM"]
    assert "SHIPPED_ON_BOARD_DATE" in response.json()["reference_data"]["business_date_keys"]


def test_charge_component_crud_and_search() -> None:
    created = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "PORT_SECURITY",
            "component_name": "Port Security",
            "category": "SURCHARGE",
            "default_party_role": "BOTH",
            "charge_context": "PORT",
            "calculation_basis": "PER_CONTAINER",
            "charge_date_basis": "MANUAL",
        },
    )
    assert created.status_code == 201, created.text
    component = created.json()
    assert component["component_code"] == "PORT_SECURITY"
    assert component["is_active"] is True
    assert component["charge_date_basis"] == "MANUAL"

    duplicate = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={**component, "component_name": "Duplicate Port Security"},
    )
    assert duplicate.status_code == 409

    listed = client.get(
        "/api/v1/charge-management/components?q=PORT_SECURITY&category=SURCHARGE",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == component["id"]

    updated = client.put(
        f"/api/v1/charge-management/components/{component['id']}",
        headers=AUTH,
        json={
            "component_code": "PORT_SECURITY_FEE",
            "component_name": "Port Security Fee",
            "category": "SURCHARGE",
            "default_party_role": "PAYEE",
            "charge_context": "PORT",
            "calculation_basis": "FLAT",
            "charge_date_basis": "SHIPMENT_DEPARTURE_DATE",
            "is_tax": False,
            "is_active": True,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["component_code"] == "PORT_SECURITY_FEE"
    assert updated.json()["default_party_role"] == "PAYEE"
    assert updated.json()["calculation_basis"] == "FLAT"
    assert updated.json()["charge_date_basis"] == "SHIPMENT_DEPARTURE_DATE"

    deleted = client.delete(
        f"/api/v1/charge-management/components/{component['id']}",
        headers=AUTH,
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_active"] is False

    active_only = client.get(
        "/api/v1/charge-management/components?active_only=true&q=PORT_SECURITY_FEE",
        headers=AUTH,
    )
    assert active_only.status_code == 200, active_only.text
    assert active_only.json()["total"] == 0


def test_component_alias_crud_and_search() -> None:
    init = client.get("/api/v1/charge-management/initialization-data", headers=AUTH)
    component_id = next(
        row["id"]
        for row in init.json()["components"]
        if row["component_code"] == "BASE_FREIGHT"
    )

    created = client.post(
        "/api/v1/charge-management/component-aliases",
        headers=AUTH,
        json={
            "document_kind": "CHARGE_PROPOSAL",
            "template_key": "GENERIC_PROPOSAL_V1",
            "source_section": "Ocean",
            "raw_label": "Frete Internacional",
            "charge_component_id": component_id,
            "default_calculation_basis": "PER_CONTAINER",
            "default_charge_level": "CONTAINER",
            "default_allocation_basis": "CBM",
            "container_house_allocation_basis": "CBM",
            "house_item_allocation_basis": "OCEAN_WM",
            "final_posting_level": "HOUSE",
            "default_quantity_uom": "CBM",
            "allocation_override_mode": "OVERRIDE_PROFILE",
            "override_charge_level": "CONTAINER",
            "override_allocation_basis": "CBM",
            "override_container_house_allocation_basis": "CBM",
            "override_house_item_allocation_basis": "WEIGHT",
            "override_final_posting_level": "PO_SCHEDULE_LINE",
            "override_quantity_uom": "CBM",
            "customer_id": 101,
            "forwarder_id": 202,
            "transport_mode": "OCEAN",
        },
    )
    assert created.status_code == 201, created.text
    alias = created.json()
    assert alias["normalized_label"] == "FRETE INTERNACIONAL"
    assert alias["component_code"] == "BASE_FREIGHT"
    assert alias["customer_id"] == 101
    assert alias["forwarder_id"] == 202
    assert alias["transport_mode"] == "OCEAN"
    assert alias["container_house_allocation_basis"] == "CBM"
    assert alias["house_item_allocation_basis"] == "OCEAN_WM"
    assert alias["final_posting_level"] == "HOUSE"
    assert alias["allocation_override_mode"] == "OVERRIDE_PROFILE"
    assert alias["override_house_item_allocation_basis"] == "WEIGHT"
    assert alias["override_final_posting_level"] == "PO_SCHEDULE_LINE"

    duplicate = client.post(
        "/api/v1/charge-management/component-aliases",
        headers=AUTH,
        json={
            **created.json(),
            "raw_label": "Frete Internacional",
            "charge_component_id": component_id,
        },
    )
    assert duplicate.status_code == 409

    scoped_sibling = client.post(
        "/api/v1/charge-management/component-aliases",
        headers=AUTH,
        json={
            **created.json(),
            "raw_label": "Frete Internacional",
            "charge_component_id": component_id,
            "forwarder_id": 203,
            "transport_mode": "AIR",
        },
    )
    assert scoped_sibling.status_code == 201, scoped_sibling.text

    listed = client.get(
        "/api/v1/charge-management/component-aliases?q=frete&forwarder_id=202&transport_mode=OCEAN",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == alias["id"]

    updated = client.put(
        f"/api/v1/charge-management/component-aliases/{alias['id']}",
        headers=AUTH,
        json={
            "document_kind": "CHARGE_PROPOSAL",
            "template_key": "GENERIC_PROPOSAL_V1",
            "source_section": "Ocean",
            "raw_label": "International Freight",
            "charge_component_id": component_id,
            "default_calculation_basis": "PER_CONTAINER",
            "default_charge_level": "CONTAINER",
            "default_allocation_basis": "CBM",
            "container_house_allocation_basis": "CBM",
            "house_item_allocation_basis": "KG",
            "final_posting_level": "PO_SCHEDULE_LINE",
            "default_quantity_uom": "CBM",
            "allocation_override_mode": "NO_ALLOCATION",
            "override_charge_level": None,
            "override_allocation_basis": None,
            "override_container_house_allocation_basis": None,
            "override_house_item_allocation_basis": None,
            "override_final_posting_level": None,
            "override_quantity_uom": None,
            "priority": 10,
            "is_active": True,
            "customer_id": 101,
            "forwarder_id": 202,
            "transport_mode": "OCEAN",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["raw_label"] == "International Freight"
    assert updated.json()["priority"] == 10
    assert updated.json()["house_item_allocation_basis"] == "KG"
    assert updated.json()["final_posting_level"] == "PO_SCHEDULE_LINE"
    assert updated.json()["allocation_override_mode"] == "NO_ALLOCATION"

    deleted = client.delete(
        f"/api/v1/charge-management/component-aliases/{alias['id']}",
        headers=AUTH,
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_active"] is False

    active_only = client.get(
        "/api/v1/charge-management/component-aliases?active_only=true&forwarder_id=202",
        headers=AUTH,
    )
    assert active_only.status_code == 200, active_only.text
    assert active_only.json()["total"] == 0


def test_allocation_profile_lifecycle_and_component_propagation() -> None:
    seeded = client.get("/api/v1/charge-management/allocation-profiles", headers=AUTH)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["total"] == 3
    assert {
        (
            row["versions"][0]["source_level"],
            row["versions"][0]["final_posting_level"],
        )
        for row in seeded.json()["items"]
    } == {
        ("HOUSE", "HOUSE"),
        ("CONTAINER", "PO_SCHEDULE_LINE"),
        ("SHIPMENT", "PO_SCHEDULE_LINE"),
    }

    created = client.post(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
        json={
            "profile_code": "ITEM_WEIGHT_DEFAULT",
            "profile_name": "Item Weight Default",
            "initial_version": {
                "source_level": "HOUSE",
                "house_to_item_driver": "WEIGHT",
                "final_posting_level": "PO_SCHEDULE_LINE",
                "default_quantity_uom": "KG",
                "notes": "Draft item weight profile",
            },
        },
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    assert profile["profile_code"] == "ITEM_WEIGHT_DEFAULT"
    assert profile["published_version_id"] is None
    assert profile["versions"][0]["status"] == "DRAFT"
    version_id = profile["versions"][0]["id"]

    reopened_profile = client.get(
        f"/api/v1/charge-management/allocation-profiles/{profile['id']}",
        headers=AUTH,
    )
    assert reopened_profile.status_code == 200, reopened_profile.text
    assert reopened_profile.json()["versions"][0]["id"] == version_id

    updated_profile = client.put(
        f"/api/v1/charge-management/allocation-profiles/{profile['id']}",
        headers=AUTH,
        json={"profile_code": "ITEM_WEIGHT_DEFAULT", "profile_name": "Item Weight Allocation"},
    )
    assert updated_profile.status_code == 200, updated_profile.text
    assert updated_profile.json()["profile_name"] == "Item Weight Allocation"

    updated_version = client.put(
        f"/api/v1/charge-management/allocation-profile-versions/{version_id}",
        headers=AUTH,
        json={
            "source_level": "HOUSE",
            "house_to_item_driver": "WEIGHT",
            "final_posting_level": "PO_SCHEDULE_LINE",
            "default_quantity_uom": "KG",
            "notes": "Published item weight profile",
        },
    )
    assert updated_version.status_code == 200, updated_version.text
    assert updated_version.json()["notes"] == "Published item weight profile"

    published = client.post(
        f"/api/v1/charge-management/allocation-profile-versions/{version_id}/publish",
        headers=AUTH,
    )
    assert published.status_code == 200, published.text
    published_profile = published.json()
    assert published_profile["published_version_id"] == version_id
    assert published_profile["published_version_number"] == 1
    assert published_profile["versions"][0]["status"] == "PUBLISHED"

    component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "PROFILED_WEIGHT_CHARGE",
            "component_name": "Profiled Weight Charge",
            "category": "SURCHARGE",
            "default_party_role": "PAYEE",
            "charge_context": "TRANSPORT",
            "calculation_basis": "WEIGHT",
            "allocation_profile_id": profile["id"],
        },
    )
    assert component.status_code == 201, component.text
    assert component.json()["allocation_profile_id"] == profile["id"]
    assert component.json()["allocation_profile_version_id"] == version_id

    document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-PROFILE-001",
            "currency": "USD",
            "lines": [
                {
                    "relationship_role": "PAYEE",
                    "charge_component_code": "PROFILED_WEIGHT_CHARGE",
                    "description": "Component-driven profile propagation",
                    "expected_amount": "55.00",
                    "currency": "USD",
                    "basis": "WEIGHT",
                }
            ],
        },
    )
    assert document.status_code == 201, document.text
    line = document.json()["lines"][0]
    assert line["allocation_profile_id"] == profile["id"]
    assert line["allocation_profile_version_id"] == version_id
    assert line["allocation_basis"] == "WEIGHT"
    assert line["quantity_uom"] == "KG"
    assert line["pinned_allocation_snapshot_json"]["profile_code"] == "ITEM_WEIGHT_DEFAULT"
    assert line["pinned_allocation_snapshot_json"]["source_level"] == "HOUSE"
    assert line["effective_allocation_snapshot_json"]["default_quantity_uom"] == "KG"
    assert line["effective_allocation_snapshot_json"]["house_to_item_driver"] == "WEIGHT"


def test_business_date_profile_lifecycle_assignment_and_resolution() -> None:
    seeded = client.get("/api/v1/charge-management/business-date-profiles", headers=AUTH)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["total"] == 2
    assert {
        row["profile_code"] for row in seeded.json()["items"]
    } == {"OCEAN_HOUSE_STANDARD", "AIR_HOUSE_STANDARD"}

    created = client.post(
        "/api/v1/charge-management/business-date-profiles",
        headers=AUTH,
        json={
            "profile_code": "OCEAN_CUSTOM_OVERRIDE",
            "profile_name": "Ocean Custom Override",
            "description": "Fallback chain for a custom ocean house profile",
            "initial_version": {
                "notes": "Draft custom profile",
                "steps": [
                    {
                        "step_number": 10,
                        "date_key": "SHIPPED_ON_BOARD_DATE",
                        "notes": "Prefer shipped on board",
                    },
                    {
                        "step_number": 20,
                        "date_key": "SHIPMENT_PLANNED_DEPARTURE_DATE",
                        "notes": "Fallback to planned departure",
                    },
                ],
            },
        },
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    version_id = profile["versions"][0]["id"]

    updated_profile = client.put(
        f"/api/v1/charge-management/business-date-profiles/{profile['id']}",
        headers=AUTH,
        json={
            "profile_code": "OCEAN_CUSTOM_OVERRIDE",
            "profile_name": "Ocean Custom Date Basis",
            "description": "Updated reusable date-basis profile",
        },
    )
    assert updated_profile.status_code == 200, updated_profile.text
    assert updated_profile.json()["profile_name"] == "Ocean Custom Date Basis"

    updated_version = client.put(
        f"/api/v1/charge-management/business-date-profile-versions/{version_id}",
        headers=AUTH,
        json={
            "notes": "Updated custom profile",
            "steps": [
                {
                    "step_number": 10,
                    "date_key": "SHIPPED_ON_BOARD_DATE",
                    "notes": "Prefer shipped on board",
                },
                {
                    "step_number": 20,
                    "date_key": "SHIPMENT_PLANNED_DEPARTURE_DATE",
                    "notes": "Fallback to planned departure",
                },
            ],
        },
    )
    assert updated_version.status_code == 200, updated_version.text
    assert updated_version.json()["notes"] == "Updated custom profile"

    published = client.post(
        f"/api/v1/charge-management/business-date-profile-versions/{version_id}/publish",
        headers=AUTH,
    )
    assert published.status_code == 200, published.text
    assert published.json()["published_version_id"] == version_id
    assert published.json()["published_version_number"] == 1

    created_assignment = client.post(
        "/api/v1/charge-management/business-date-profiles/2/assignments",
        headers=AUTH,
        json={
            "scope_type": "CUSTOMER",
            "scope_id": 20,
            "shipment_scope": "AIR_HOUSE",
            "business_purpose": "EXCHANGE_RATE_DATE",
            "priority": 50,
            "is_active": True,
        },
    )
    assert created_assignment.status_code == 201, created_assignment.text
    assignment_id = created_assignment.json()["id"]
    assert created_assignment.json()["profile_id"] == 2
    assert created_assignment.json()["scope_type"] == "CUSTOMER"
    assert created_assignment.json()["owner_scope_key"] == "CUSTOMER:20"
    assert created_assignment.json()["shipment_scope"] == "AIR_HOUSE"

    ambiguous_assignment = client.post(
        "/api/v1/charge-management/business-date-profiles/1/assignments",
        headers=AUTH,
        json={
            "scope_type": "CUSTOMER",
            "scope_id": 20,
            "shipment_scope": "AIR_HOUSE",
            "business_purpose": "EXCHANGE_RATE_DATE",
        },
    )
    assert ambiguous_assignment.status_code == 409, ambiguous_assignment.text

    ocean_assignment = client.post(
        "/api/v1/charge-management/business-date-profiles/1/assignments",
        headers=AUTH,
        json={
            "scope_type": "CUSTOMER",
            "scope_id": 20,
            "shipment_scope": "OCEAN_HOUSE",
            "business_purpose": "EXCHANGE_RATE_DATE",
        },
    )
    assert ocean_assignment.status_code == 201, ocean_assignment.text

    updated_assignment = client.put(
        f"/api/v1/charge-management/business-date-profile-assignments/{assignment_id}",
        headers=AUTH,
        json={
            "scope_type": "CUSTOMER",
            "scope_id": 20,
            "shipment_scope": "AIR_HOUSE",
            "business_purpose": "EXCHANGE_RATE_DATE",
            "priority": 25,
            "is_active": True,
        },
    )
    assert updated_assignment.status_code == 200, updated_assignment.text
    assert updated_assignment.json()["priority"] == 25

    listed_assignments = client.get(
        "/api/v1/charge-management/business-date-profiles/2/assignments"
        "?scope_type=CUSTOMER&scope_id=20&shipment_scope=AIR_HOUSE&business_purpose=EXCHANGE_RATE_DATE",
        headers=AUTH,
    )
    assert listed_assignments.status_code == 200, listed_assignments.text
    assert listed_assignments.json()["total"] == 1

    override_component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "OCEAN_CUSTOM_DUE",
            "component_name": "Ocean Custom Due",
            "category": "ACCESSORIAL",
            "default_party_role": "BOTH",
            "charge_context": "TRANSPORT",
            "calculation_basis": "FLAT",
            "business_date_policy_mode": "PROFILE_OVERRIDE",
            "business_date_profile_id": profile["id"],
        },
    )
    assert override_component.status_code == 201, override_component.text
    assert override_component.json()["business_date_policy_mode"] == "PROFILE_OVERRIDE"
    assert override_component.json()["business_date_profile_id"] == profile["id"]

    inherited_component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "AIR_CUSTOM_DUE",
            "component_name": "Air Custom Due",
            "category": "ACCESSORIAL",
            "default_party_role": "BOTH",
            "charge_context": "TRANSPORT",
            "calculation_basis": "FLAT",
            "business_date_policy_mode": "INHERIT_PROFILE",
        },
    )
    assert inherited_component.status_code == 201, inherited_component.text
    assert inherited_component.json()["business_date_policy_mode"] == "INHERIT_PROFILE"

    override_document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-BDP-001",
            "customer_id": 99,
            "currency": "USD",
            "source_reference_snapshot_json": {
                "business_dates": {
                    "shipped_on_board_date": "2026-06-29",
                }
            },
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "OCEAN_CUSTOM_DUE",
                    "description": "Profile override resolution",
                    "expected_amount": "10.00",
                    "currency": "USD",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert override_document.status_code == 201, override_document.text
    assert override_document.json()["lines"][0]["exchange_rate_date"] == "2026-06-29"

    inherited_document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-BDP-002",
            "customer_id": 20,
            "shipment_scope": "AIR_HOUSE",
            "currency": "USD",
            "source_reference_snapshot_json": {
                "business_dates": {
                    "awb_execution_date": "2026-06-30",
                    "shipped_on_board_date": "2026-06-28",
                }
            },
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "AIR_CUSTOM_DUE",
                    "description": "Inherited assignment resolution",
                    "expected_amount": "20.00",
                    "currency": "USD",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert inherited_document.status_code == 201, inherited_document.text
    assert inherited_document.json()["shipment_scope"] == "AIR_HOUSE"
    assert inherited_document.json()["lines"][0]["exchange_rate_date"] == "2026-06-30"

    ocean_document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-BDP-003",
            "customer_id": 20,
            "shipment_scope": "OCEAN_HOUSE",
            "document_date": "2026-07-01",
            "currency": "USD",
            "source_reference_snapshot_json": {
                "business_dates": {
                    "awb_execution_date": "2026-06-30",
                    "shipped_on_board_date": "2026-06-28",
                }
            },
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "AIR_CUSTOM_DUE",
                    "description": "Exact shipment scope assignment resolution",
                    "expected_amount": "20.00",
                    "currency": "USD",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert ocean_document.status_code == 201, ocean_document.text
    assert ocean_document.json()["lines"][0]["exchange_rate_date"] == "2026-06-28"

    deleted_assignment = client.delete(
        f"/api/v1/charge-management/business-date-profile-assignments/{assignment_id}",
        headers=AUTH,
    )
    assert deleted_assignment.status_code == 200, deleted_assignment.text
    assert deleted_assignment.json()["id"] == assignment_id


def test_charge_line_date_basis_override_precedence() -> None:
    component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "DATE_OVERRIDE_TEST",
            "component_name": "Date Override Test",
            "category": "ACCESSORIAL",
            "default_party_role": "BOTH",
            "charge_context": "TRANSPORT",
            "calculation_basis": "FLAT",
            "business_date_policy_mode": "PROFILE_OVERRIDE",
            "business_date_profile_id": 1,
        },
    )
    assert component.status_code == 201, component.text

    document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-LINE-DATE-001",
            "shipment_scope": "OCEAN_HOUSE",
            "document_date": "2026-07-01",
            "currency": "USD",
            "source_reference_snapshot_json": {
                "business_dates": {
                    "shipped_on_board_date": "2026-06-28",
                    "shipment_arrival_date": "2026-07-05",
                }
            },
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "DATE_OVERRIDE_TEST",
                    "description": "Explicit exchange-rate date",
                    "charge_date": "2026-07-06",
                    "charge_date_basis": "SHIPMENT_ARRIVAL_DATE",
                    "exchange_rate_date": "2026-07-07",
                    "expected_amount": "10.00",
                },
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "DATE_OVERRIDE_TEST",
                    "description": "Explicit manual date",
                    "charge_date": "2026-07-06",
                    "charge_date_basis": "SHIPMENT_ARRIVAL_DATE",
                    "expected_amount": "10.00",
                },
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "DATE_OVERRIDE_TEST",
                    "description": "Line basis override",
                    "charge_date_basis": "SHIPMENT_ARRIVAL_DATE",
                    "expected_amount": "10.00",
                },
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "DATE_OVERRIDE_TEST",
                    "description": "Component profile",
                    "expected_amount": "10.00",
                },
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "DATE_OVERRIDE_TEST",
                    "description": "Missing line event uses document fallback",
                    "charge_date_basis": "HOUSE_BILL_ISSUE_DATE",
                    "expected_amount": "10.00",
                },
            ],
        },
    )
    assert document.status_code == 201, document.text
    lines = document.json()["lines"]
    assert [line["exchange_rate_date"] for line in lines] == [
        "2026-07-07",
        "2026-07-06",
        "2026-07-05",
        "2026-06-28",
        "2026-07-01",
    ]
    assert lines[2]["charge_date_basis"] == "SHIPMENT_ARRIVAL_DATE"
    assert lines[3]["charge_date_basis"] is None


def test_rate_book_list_workspace_and_update_contract() -> None:
    rate_book_id = _create_rate_book()

    listed = client.get(
        "/api/v1/charge-management/rate-books?q=OCEAN",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == rate_book_id

    workspace = client.get(
        f"/api/v1/charge-management/rate-books/{rate_book_id}/workspace",
        headers=AUTH,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["rate_book"]["id"] == rate_book_id
    assert workspace.json()["entries"][0]["charge_component_code"] == "BASE_FREIGHT"

    updated = client.put(
        f"/api/v1/charge-management/rate-books/{rate_book_id}/workspace",
        headers=AUTH,
        json={
            "rate_book_code": "RB-OCEAN-001",
            "rate_book_name": "Updated ocean rates",
            "currency": "USD",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "1750.00",
                    "basis": "CONTAINER",
                    "currency": "USD",
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                }
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["rate_book"]["rate_book_name"] == "Updated ocean rates"
    assert updated.json()["entries"][0]["rate_amount"] == "1750.00"


def test_charge_document_line_calculation_audit_roundtrip() -> None:
    created = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_number": "CHG-AUDIT-001",
            "currency": "USD",
            "lines": [
                {
                    "line_number": 1,
                    "relationship_role": "PAYEE",
                    "charge_component_code": "BASE_FREIGHT",
                    "description": "Allocated freight",
                    "expected_amount": "123.45",
                    "currency": "USD",
                    "basis": "CONTAINER",
                    "target_level": "CONTAINER",
                    "target_object_type": "container",
                    "target_object_id": "ABC",
                    "allocation_basis": "CBM",
                    "allocation_ratio": "0.25000000",
                    "allocation_driver_value": "2.5",
                    "calculation_audit_json": {
                        "source_row": 1,
                        "basis": "CBM",
                        "pool_amount": "493.80",
                        "ratio": "0.25",
                    },
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    line = created.json()["lines"][0]
    assert line["calculation_audit_json"]["pool_amount"] == "493.80"
    assert line["allocation_basis"] == "CBM"


def test_calculation_template_list_workspace_and_update_contract() -> None:
    rate_book_id = _create_rate_book()
    created = client.post(
        "/api/v1/charge-management/calculation-templates",
        headers=AUTH,
        json={
            "template_code": "CT-OCEAN-001",
            "template_name": "Ocean charge build",
            "description": "Base freight plus optional subtotals",
            "status": "DRAFT",
            "steps": [
                {
                    "step_number": 10,
                    "charge_component_code": "BASE_FREIGHT",
                    "relationship_role": "BOTH",
                    "subtotal_key": "BASE",
                    "rate_book_id": rate_book_id,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]

    listed = client.get(
        "/api/v1/charge-management/calculation-templates?q=OCEAN",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == template_id

    workspace = client.get(
        f"/api/v1/charge-management/calculation-templates/{template_id}/workspace",
        headers=AUTH,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["template"]["id"] == template_id
    assert workspace.json()["steps"][0]["charge_component_code"] == "BASE_FREIGHT"
    assert workspace.json()["steps"][0]["rate_book_code"] == "RB-OCEAN-001"

    updated = client.put(
        f"/api/v1/charge-management/calculation-templates/{template_id}/workspace",
        headers=AUTH,
        json={
            "template_code": "CT-OCEAN-001",
            "template_name": "Updated ocean charge build",
            "status": "RELEASED",
            "steps": [
                {
                    "step_number": 10,
                    "charge_component_code": "BASE_FREIGHT",
                    "relationship_role": "PAYER",
                    "subtotal_key": "PROVIDER_COST",
                    "rate_book_id": rate_book_id,
                }
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["template"]["template_name"] == "Updated ocean charge build"
    assert updated.json()["template"]["status"] == "RELEASED"
    assert updated.json()["steps"][0]["relationship_role"] == "PAYER"


def test_contract_release_requires_rate_source_line() -> None:
    empty_contract = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": "PAYER-EMPTY",
            "contract_name": "Payer empty contract",
            "contract_role": "PAYER",
            "payer_party_ref": "party:platform:10",
            "payee_party_ref": "party:carrier:1",
            "party_role_ref": "PAYER",
            "company_id": 10,
            "currency": "USD",
            "lines": [],
        },
    )
    assert empty_contract.status_code == 201, empty_contract.text
    empty_release = client.post(
        f"/api/v1/charge-management/contracts/{empty_contract.json()['id']}/release",
        headers=AUTH,
    )
    assert empty_release.status_code == 409

    contract = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": "PAYER-NO-RATE",
            "contract_name": "Payer no rate source",
            "contract_role": "PAYER",
            "payer_party_ref": "party:platform:10",
            "payee_party_ref": "party:carrier:1",
            "party_role_ref": "PAYER",
            "company_id": 10,
            "currency": "USD",
            "lines": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                }
            ],
        },
    )
    assert contract.status_code == 201, contract.text
    contract_id = contract.json()["id"]

    no_rate_release = client.post(
        f"/api/v1/charge-management/contracts/{contract_id}/release",
        headers=AUTH,
    )
    assert no_rate_release.status_code == 409

    rate_book_id = _create_rate_book()
    updated = client.put(
        f"/api/v1/charge-management/contracts/{contract_id}/workspace",
        headers=AUTH,
        json={"default_rate_book_id": rate_book_id},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["contract"]["default_rate_book_id"] == rate_book_id
    assert updated.json()["contract"]["lines"][0]["rate_book_id"] is None

    released = client.post(
        f"/api/v1/charge-management/contracts/{contract_id}/release",
        headers=AUTH,
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "RELEASED"


def test_rated_option_and_awarded_document_propagate_allocation_profile_snapshots() -> None:
    created = client.post(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
        json={
            "profile_code": "STAGED_PROPAGATION",
            "profile_name": "Staged Propagation",
            "initial_version": {
                "source_level": "CONTAINER",
                "source_to_house_driver": "CBM",
                "house_to_item_driver": "WEIGHT",
                "final_posting_level": "PO_SCHEDULE_LINE",
                "default_quantity_uom": "CBM",
            },
        },
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    version_id = profile["versions"][0]["id"]
    published = client.post(
        f"/api/v1/charge-management/allocation-profile-versions/{version_id}/publish",
        headers=AUTH,
    )
    assert published.status_code == 200, published.text

    rate_book = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-PROFILE-001",
            "rate_book_name": "Profile propagation rates",
            "currency": "USD",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "1500.00",
                    "basis": "CONTAINER",
                    "currency": "USD",
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                    "allocation_profile_id": profile["id"],
                }
            ],
        },
    )
    assert rate_book.status_code == 201, rate_book.text
    rate_book_id = rate_book.json()["id"]
    assert rate_book.json()["entries"][0]["allocation_profile_version_id"] == version_id

    contract = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": "PAYEE-PROFILE-001",
            "contract_name": "Payee Profile Contract",
            "contract_role": "PAYEE",
            "payer_party_ref": "party:customer:20",
            "payee_party_ref": "party:platform:10",
            "party_role_ref": "PAYEE",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
            "lines": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_book_id": rate_book_id,
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                    "allocation_profile_id": profile["id"],
                }
            ],
        },
    )
    assert contract.status_code == 201, contract.text
    contract_id = contract.json()["id"]
    assert contract.json()["lines"][0]["allocation_profile_version_id"] == version_id

    release = client.post(
        f"/api/v1/charge-management/contracts/{contract_id}/release",
        headers=AUTH,
    )
    assert release.status_code == 200, release.text

    quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "origin_code": "BRSSZ",
            "destination_code": "USNYC",
            "mode": "OCEAN",
            "currency": "USD",
            "container_count": "1",
        },
    )
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]
    _submit_quote(quote_id)

    rated = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/rate",
        headers=AUTH,
    )
    assert rated.status_code == 200, rated.text
    option_line = rated.json()["options"][0]["lines"][0]
    assert option_line["allocation_profile_id"] == profile["id"]
    assert option_line["allocation_profile_version_id"] == version_id
    assert option_line["allocation_basis"] == "WEIGHT"
    assert option_line["pinned_allocation_snapshot_json"]["source_level"] == "CONTAINER"
    assert option_line["pinned_allocation_snapshot_json"]["source_to_house_driver"] == "CBM"

    awarded = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/award",
        headers=AUTH,
        json={"quote_option_id": rated.json()["options"][0]["id"]},
    )
    assert awarded.status_code == 200, awarded.text
    awarded_line = awarded.json()["charge_document"]["lines"][0]
    assert awarded_line["allocation_profile_id"] == profile["id"]
    assert awarded_line["allocation_profile_version_id"] == version_id
    assert awarded_line["allocation_basis"] == "WEIGHT"
    assert awarded_line["effective_allocation_snapshot_json"]["house_to_item_driver"] == "WEIGHT"


def test_quote_request_accepts_ocean_and_air_rfq_cargo_fields() -> None:
    ocean = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "mode": "OCEAN",
            "container_count": "3",
            "equipment_type": "40HQ",
            "valid_from": "2026-06-01",
            "valid_to": "2026-06-30",
            "currency": "USD",
        },
    )
    assert ocean.status_code == 201, ocean.text
    assert ocean.json()["container_count"] == "3"
    assert ocean.json()["requested_service_date"] is None
    assert ocean.json()["valid_from"] == "2026-06-01"
    assert ocean.json()["valid_to"] == "2026-06-30"

    air = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "mode": "AIR",
            "package_count": "12",
            "package_type": "CARTON",
            "gross_weight": "250",
            "gross_volume_cbm": "1.5",
            "currency": "USD",
        },
    )
    assert air.status_code == 201, air.text
    assert air.json()["package_count"] == "12"
    assert air.json()["package_type"] == "CARTON"

    listed = client.get("/api/v1/charge-management/quote-requests", headers=AUTH)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 2
    assert listed.json()["items"][0]["id"] == air.json()["id"]

    workspace = client.get(
        f"/api/v1/charge-management/quote-requests/{ocean.json()['id']}/workspace",
        headers=AUTH,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["quote_request"]["id"] == ocean.json()["id"]
    assert workspace.json()["options"] == []

    updated = client.put(
        f"/api/v1/charge-management/quote-requests/{ocean.json()['id']}/workspace",
        headers=AUTH,
        json={
            "company_id": 10,
            "customer_id": 20,
            "mode": "OCEAN",
            "container_count": "4",
            "equipment_type": "40HQ",
            "commodity_code": "GEN",
            "currency": "usd",
            "valid_from": "2026-06-01",
            "valid_to": "2026-06-30",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["quote_request"]["container_count"] == "4"
    assert updated.json()["quote_request"]["commodity_code"] == "GEN"
    assert updated.json()["quote_request"]["currency"] == "USD"


def test_quote_offer_is_visible_in_workspace_and_rankable() -> None:
    quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "mode": "OCEAN",
            "currency": "USD",
            "container_count": "1",
        },
    )
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]
    draft_offer = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/offers",
        headers=AUTH,
        json={
            "provider_party_ref": "party:provider:77",
            "provider_role_ref": "provider-role:77",
            "offer_number": "OFF-DRAFT-BLOCKED",
            "source": "MANUAL",
            "amount": "1450.00",
            "currency": "USD",
        },
    )
    assert draft_offer.status_code == 409
    _submit_quote(quote_id)

    offer = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/offers",
        headers=AUTH,
        json={
            "provider_party_ref": "party:provider:77",
            "provider_role_ref": "provider-role:77",
            "offer_number": "OFF-2026-0001",
            "source": "MANUAL",
            "amount": "1450.00",
            "currency": "USD",
            "is_sealed": True,
            "transit_time_days": 6,
            "service_level": "STANDARD",
            "performance_score": "9.2500",
        },
    )
    assert offer.status_code == 201, offer.text
    assert offer.json()["quote_request_id"] == quote_id
    assert offer.json()["status"] == "SUBMITTED"
    assert offer.json()["is_sealed"] is True

    listed = client.get("/api/v1/charge-management/quote-requests", headers=AUTH)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == quote_id

    workspace = client.get(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["quote_request"]["id"] == quote_id
    assert workspace.json()["offers"][0]["id"] == offer.json()["id"]
    assert workspace.json()["offers"][0]["provider_party_ref"] == "party:provider:77"
    assert workspace.json()["options"][0]["source_offer_id"] == offer.json()["id"]

    offer_workspace = client.get(
        f"/api/v1/charge-management/quote-offers/{offer.json()['id']}/workspace",
        headers=AUTH,
    )
    assert offer_workspace.status_code == 200, offer_workspace.text
    assert offer_workspace.json()["offer"]["id"] == offer.json()["id"]
    assert offer_workspace.json()["quote_request"]["id"] == quote_id
    assert offer_workspace.json()["quote_option"]["source_offer_id"] == offer.json()["id"]

    updated_offer = client.put(
        f"/api/v1/charge-management/quote-offers/{offer.json()['id']}/workspace",
        headers=AUTH,
        json={
            "amount": "1550.00",
            "currency": "USD",
            "transit_time_days": 5,
            "service_level": "EXPEDITED",
            "performance_score": "9.5000",
            "notes": "Corrected offer",
        },
    )
    assert updated_offer.status_code == 200, updated_offer.text
    assert updated_offer.json()["offer"]["amount"] == "1550.00"
    assert updated_offer.json()["quote_option"]["payer_total_amount"] == "1550.00"
    assert updated_offer.json()["quote_option"]["payee_total_amount"] == "1550.00"
    assert updated_offer.json()["quote_option"]["transit_time_days"] == 5

    locked_update = client.put(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
        json={"commodity_code": "LOCKED"},
    )
    assert locked_update.status_code == 409

    rated = client.post(f"/api/v1/charge-management/quote-requests/{quote_id}/rate", headers=AUTH)
    assert rated.status_code == 200, rated.text
    assert rated.json()["options"][0]["source_offer_id"] == offer.json()["id"]

    ranked = client.post(f"/api/v1/charge-management/quote-requests/{quote_id}/rank", headers=AUTH)
    assert ranked.status_code == 200, ranked.text
    assert ranked.json()["options"][0]["rank"] == 1
    assert ranked.json()["options"][0]["source_offer_id"] == offer.json()["id"]

    withdrawn = client.post(
        f"/api/v1/charge-management/quote-offers/{offer.json()['id']}/withdraw",
        headers=AUTH,
        json={"reason": "Capacity no longer available"},
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["offer"]["status"] == "WITHDRAWN"

    workspace_after_withdraw = client.get(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
    )
    assert workspace_after_withdraw.status_code == 200
    assert workspace_after_withdraw.json()["offers"][0]["status"] == "WITHDRAWN"
    assert workspace_after_withdraw.json()["options"] == []

    rank_after_withdraw = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/rank",
        headers=AUTH,
    )
    assert rank_after_withdraw.status_code == 422

    award_withdrawn = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/award",
        headers=AUTH,
        json={"quote_option_id": offer_workspace.json()["quote_option"]["id"]},
    )
    assert award_withdrawn.status_code == 409


def test_db_metadata_contains_quote_offer_schema() -> None:
    tables = Base.metadata.tables
    assert "charge_id_sequence" in tables
    assert "charge_fx_rate_source" in tables
    assert "charge_fx_rate" in tables
    assert "charge_allocation_profile" in tables
    assert "charge_allocation_profile_version" in tables
    assert "charge_business_date_profile" in tables
    assert "charge_business_date_profile_version" in tables
    assert "charge_business_date_profile_step" in tables
    assert "charge_business_date_profile_assignment" in tables
    assert "charge_quote_offer" in tables
    assert "valid_from" in tables["charge_quote_request"].c
    assert "valid_to" in tables["charge_quote_request"].c
    assert "source_offer_id" in tables["charge_quote_option"].c
    allocation_profile_columns = tables["charge_allocation_profile"].c
    assert "published_version_id" in allocation_profile_columns
    allocation_profile_version_columns = tables["charge_allocation_profile_version"].c
    assert "source_level" in allocation_profile_version_columns
    assert "source_to_house_driver" in allocation_profile_version_columns
    assert "house_to_item_driver" in allocation_profile_version_columns
    assert "final_posting_level" in allocation_profile_version_columns
    offer_columns = tables["charge_quote_offer"].c
    assert "provider_party_ref" in offer_columns
    assert "provider_role_ref" in offer_columns
    assert "amount" in offer_columns
    component_columns = tables["charge_component"].c
    assert "allocation_profile_id" in component_columns
    assert "allocation_profile_version_id" in component_columns
    assert "business_date_policy_mode" in component_columns
    assert "business_date_profile_id" in component_columns
    assignment_table = tables["charge_business_date_profile_assignment"]
    assert "owner_scope_key" in assignment_table.c
    assert "shipment_scope" in assignment_table.c
    assert "business_purpose" in assignment_table.c
    effective_scope_constraint = next(
        constraint
        for constraint in assignment_table.constraints
        if constraint.name == "uq_charge_business_date_profile_assignment_effective_scope"
    )
    assert {column.name for column in effective_scope_constraint.columns} == {
        "owner_scope_key",
        "shipment_scope",
        "business_purpose",
    }
    alias_columns = tables["charge_component_alias"].c
    assert "final_posting_level" in alias_columns
    assert "override_final_posting_level" in alias_columns
    document_columns = tables["charge_document"].c
    assert "document_scope_level" in document_columns
    assert "shipment_scope" in document_columns
    assert "document_date" in document_columns
    assert "source_reference_snapshot_json" in document_columns
    option_line_columns = tables["charge_quote_option_line"].c
    assert "allocation_profile_id" in option_line_columns
    assert "effective_allocation_snapshot_json" in option_line_columns
    line_columns = tables["charge_line"].c
    assert "line_number" in line_columns
    assert "parent_line_id" in line_columns
    assert "line_role" in line_columns
    assert "target_level" in line_columns
    assert "target_object_type" in line_columns
    assert "charge_date_basis" in line_columns
    assert "target_reference_snapshot_json" in line_columns
    assert "allocation_profile_id" in line_columns
    assert "pinned_allocation_snapshot_json" in line_columns
    assert "fx_rate_id" in line_columns
    assert "exchange_rate_source_code" in line_columns
    assert "exchange_rate_type" in line_columns
    assert "exchange_rate_method" in line_columns


def test_direct_charge_document_respects_quotation_policy() -> None:
    response = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-1",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "125.00",
                    "currency": "USD",
                    "basis": "SHIPMENT",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quote_request_id"] is None
    assert body["quotation_policy_snapshot"] == "OPTIONAL"
    assert body["payer_total_amount"] == "125.00"

    listed = client.get(
        "/api/v1/charge-management/charge-documents?q=CHG",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == body["id"]

    workspace_update = client.put(
        f"/api/v1/charge-management/charge-documents/{body['id']}/workspace",
        headers=AUTH,
        json={
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "150.00",
                    "currency": "USD",
                    "basis": "SHIPMENT",
                },
                {
                    "relationship_role": "PAYEE",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "210.00",
                    "currency": "USD",
                    "basis": "SHIPMENT",
                },
            ]
        },
    )
    assert workspace_update.status_code == 200, workspace_update.text
    updated_document = workspace_update.json()["document"]
    assert updated_document["payer_total_amount"] == "150.00"
    assert updated_document["payee_total_amount"] == "210.00"
    assert updated_document["margin_amount"] == "60.00"
    assert len(updated_document["lines"]) == 2

    invoice = client.post(
        "/api/v1/charge-management/invoices",
        headers=AUTH,
        json={
            "charge_document_id": body["id"],
            "invoice_number": "DIR-INV-001",
            "invoice_type": "SUPPLIER",
            "currency": "USD",
            "lines": [{"charge_component_code": "BASE_FREIGHT", "amount": "150.00"}],
        },
    )
    assert invoice.status_code == 201, invoice.text
    locked_update = client.put(
        f"/api/v1/charge-management/charge-documents/{body['id']}/workspace",
        headers=AUTH,
        json={
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "175.00",
                    "currency": "USD",
                }
            ]
        },
    )
    assert locked_update.status_code == 409

    repository.quotation_policy = "REQUIRED"
    blocked = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={"company_id": 10, "customer_id": 20},
    )
    assert blocked.status_code == 400
    assert "Quotation is required" in blocked.text


def test_direct_charge_document_can_be_deleted_before_lifecycle_lock() -> None:
    response = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-DELETE",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    deleted = client.delete(
        f"/api/v1/charge-management/charge-documents/{document_id}",
        headers=AUTH,
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["document"]["id"] == document_id
    workspace = client.get(
        f"/api/v1/charge-management/charge-documents/{document_id}/workspace",
        headers=AUTH,
    )
    assert workspace.status_code == 404


def test_direct_charge_document_delete_blocks_after_approval() -> None:
    response = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-APPROVED",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    approved = client.post(
        f"/api/v1/charge-management/charge-documents/{document_id}/approve",
        headers=AUTH,
    )
    assert approved.status_code == 200, approved.text

    deleted = client.delete(
        f"/api/v1/charge-management/charge-documents/{document_id}",
        headers=AUTH,
    )

    assert deleted.status_code == 409


def test_direct_charge_document_supports_generic_line_hierarchy_and_targets() -> None:
    response = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT_V2",
            "source_object_id": "SV2-1",
            "document_scope_level": "HEADER",
            "document_date": "2026-06-29",
            "source_reference_snapshot_json": {"shipment_number": "SV2-1"},
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
            "lines": [
                {
                    "relationship_role": "PAYEE",
                    "line_number": 10,
                    "line_role": "CALCULATION",
                    "target_level": "HEADER",
                    "target_object_type": "SHIPMENT_V2",
                    "target_object_id": "SV2-1",
                    "charge_component_code": "BASE_FREIGHT",
                    "description": "Header charge before allocation",
                    "expected_amount": "700.00",
                    "currency": "USD",
                    "basis": "SHIPMENT",
                    "allocation_basis": "WEIGHT",
                    "allocation_driver_value": "1000.000000",
                },
                {
                    "relationship_role": "PAYEE",
                    "line_number": 20,
                    "parent_line_number": 10,
                    "line_role": "POSTING",
                    "target_level": "CONTAINER",
                    "target_object_type": "CONTAINER",
                    "target_object_id": "CONT-1",
                    "charge_component_code": "BASE_FREIGHT",
                    "description": "Allocated container charge",
                    "charge_date": "2026-06-29",
                    "expected_amount": "200.00",
                    "currency": "USD",
                    "quantity_uom": "KG",
                    "source_currency": "EUR",
                    "source_amount": "180.00",
                    "exchange_rate": "1.11111111",
                    "exchange_rate_date": "2026-06-29",
                    "charge_text_snapshot": "Allocated freight charge",
                    "basis": "WEIGHT",
                    "allocation_basis": "WEIGHT",
                    "allocation_ratio": "0.40000000",
                    "allocation_driver_value": "400.000000",
                    "target_reference_snapshot_json": {"container_number": "CONT-1"},
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document_scope_level"] == "HEADER"
    assert body["document_date"] == "2026-06-29"
    assert body["payee_total_amount"] == "200.00"
    assert body["margin_amount"] == "200.00"
    assert [line["line_number"] for line in body["lines"]] == [10, 20]
    assert body["lines"][0]["line_role"] == "CALCULATION"
    assert body["lines"][1]["line_role"] == "POSTING"
    assert body["lines"][1]["parent_line_number"] == 10
    assert body["lines"][1]["target_level"] == "CONTAINER"
    assert body["lines"][1]["target_object_type"] == "CONTAINER"
    assert body["lines"][1]["source_currency"] == "EUR"
    assert body["lines"][1]["target_reference_snapshot_json"] == {"container_number": "CONT-1"}


def test_direct_only_quotation_policy_blocks_quote_request() -> None:
    repository.quotation_policy = "DIRECT_ONLY"

    response = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={"company_id": 10, "customer_id": 20, "currency": "USD"},
    )

    assert response.status_code == 400
    assert "Quotation is disabled" in response.text


def test_quote_to_export_and_reverse_lifecycle() -> None:
    repository.provider_cost_layer_enabled = True
    rate_book_id = _create_rate_book()
    payer_contract_id = _create_contract("PAYER-001", "PAYER", rate_book_id)
    _create_contract("PAYEE-001", "PAYEE", rate_book_id)

    listed_contracts = client.get(
        "/api/v1/charge-management/contracts?contract_role=PAYER",
        headers=AUTH,
    )
    assert listed_contracts.status_code == 200, listed_contracts.text
    assert listed_contracts.json()["total"] == 1
    assert listed_contracts.json()["items"][0]["id"] == payer_contract_id

    release = client.post(
        f"/api/v1/charge-management/contracts/{payer_contract_id}/release",
        headers=AUTH,
    )
    assert release.status_code == 200
    payee_release = client.post("/api/v1/charge-management/contracts/2/release", headers=AUTH)
    assert payee_release.status_code == 200

    quote_response = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "origin_code": "BRSSZ",
            "destination_code": "USNYC",
            "mode": "OCEAN",
            "currency": "USD",
            "container_count": "2",
            "margin_rules": {"percentage": "15", "minimum_margin": "100"},
        },
    )
    assert quote_response.status_code == 201, quote_response.text
    quote_id = quote_response.json()["id"]
    _submit_quote(quote_id)

    determined = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/determine-contracts",
        headers=AUTH,
    )
    assert determined.status_code == 200
    assert len(determined.json()["payer_contracts"]) == 1
    assert len(determined.json()["payee_contracts"]) == 1

    rated = client.post(f"/api/v1/charge-management/quote-requests/{quote_id}/rate", headers=AUTH)
    assert rated.status_code == 200, rated.text
    option = rated.json()["options"][0]
    assert option["payer_total_amount"] == "3000.00"

    ranked = client.post(f"/api/v1/charge-management/quote-requests/{quote_id}/rank", headers=AUTH)
    assert ranked.status_code == 200
    assert ranked.json()["options"][0]["rank"] == 1

    awarded = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/award",
        headers=AUTH,
        json={"quote_option_id": option["id"]},
    )
    assert awarded.status_code == 200, awarded.text
    document_id = awarded.json()["charge_document"]["id"]
    commitment = awarded.json()["quote_commitment"]
    assert commitment["committed_container_count"] == "2"
    assert commitment["status"] == "ACTIVE"
    awarded_workspace = client.get(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
    )
    assert awarded_workspace.status_code == 200, awarded_workspace.text
    assert awarded_workspace.json()["commitments"][0]["id"] == commitment["id"]
    assert awarded_workspace.json()["commitments"][0]["consumptions"] == []
    quote_document_line_update = client.put(
        f"/api/v1/charge-management/charge-documents/{document_id}/workspace",
        headers=AUTH,
        json={
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "175.00",
                    "currency": "USD",
                }
            ]
        },
    )
    assert quote_document_line_update.status_code == 409

    duplicate_quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "origin_code": "BRSSZ",
            "destination_code": "USNYC",
            "mode": "OCEAN",
            "currency": "USD",
            "container_count": "1",
        },
    )
    assert duplicate_quote.status_code == 201, duplicate_quote.text
    duplicate_quote_id = duplicate_quote.json()["id"]
    _submit_quote(duplicate_quote_id)
    duplicate_rated = client.post(
        f"/api/v1/charge-management/quote-requests/{duplicate_quote_id}/rate",
        headers=AUTH,
    )
    assert duplicate_rated.status_code == 200, duplicate_rated.text
    duplicate_award = client.post(
        f"/api/v1/charge-management/quote-requests/{duplicate_quote_id}/award",
        headers=AUTH,
        json={"quote_option_id": duplicate_rated.json()["options"][0]["id"]},
    )
    assert duplicate_award.status_code == 409
    assert "same commercial scope" in duplicate_award.text

    matched_commitments = client.post(
        "/api/v1/charge-management/quote-commitments/match",
        headers=AUTH,
        json={
            "company_id": 10,
            "customer_id": 20,
            "origin_code": "BRSSZ",
            "destination_code": "USNYC",
            "mode": "OCEAN",
            "container_count": "1",
        },
    )
    assert matched_commitments.status_code == 200, matched_commitments.text
    assert matched_commitments.json()["matches"][0]["id"] == commitment["id"]

    consumed = client.post(
        f"/api/v1/charge-management/quote-commitments/{commitment['id']}/consume",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-100",
            "reference_number": "MBL-001",
            "container_count": "1",
        },
    )
    assert consumed.status_code == 200, consumed.text
    assert consumed.json()["commitment"]["remaining_container_count"] == "1"
    assert consumed.json()["consumption"]["reference_number"] == "MBL-001"

    second_consumed = client.post(
        f"/api/v1/charge-management/quote-commitments/{commitment['id']}/consume",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-101",
            "reference_number": "MBL-002",
            "container_count": "1",
        },
    )
    assert second_consumed.status_code == 200, second_consumed.text
    assert second_consumed.json()["commitment"]["status"] == "CONSUMED"

    reversed_consumption = client.post(
        "/api/v1/charge-management/quote-commitment-consumptions/"
        f"{second_consumed.json()['consumption']['id']}/reverse",
        headers=AUTH,
        json={"reason": "Container marked for deletion"},
    )
    assert reversed_consumption.status_code == 200, reversed_consumption.text
    assert reversed_consumption.json()["commitment"]["status"] == "ACTIVE"
    assert reversed_consumption.json()["commitment"]["remaining_container_count"] == "1"
    assert reversed_consumption.json()["consumption"]["status"] == "REVERSED"
    consumed_workspace = client.get(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
    )
    assert consumed_workspace.status_code == 200, consumed_workspace.text
    workspace_commitment = consumed_workspace.json()["commitments"][0]
    consumptions_by_reference = {
        row["reference_number"]: row for row in workspace_commitment["consumptions"]
    }
    assert workspace_commitment["remaining_container_count"] == "1"
    assert set(consumptions_by_reference) == {"MBL-001", "MBL-002"}
    assert consumptions_by_reference["MBL-001"]["status"] == "ACTIVE"
    assert consumptions_by_reference["MBL-002"]["status"] == "REVERSED"
    assert (
        consumptions_by_reference["MBL-002"]["reversal_reason"]
        == "Container marked for deletion"
    )

    invoice = client.post(
        "/api/v1/charge-management/invoices",
        headers=AUTH,
        json={
            "charge_document_id": document_id,
            "invoice_number": "INV-001",
            "invoice_type": "SUPPLIER",
            "currency": "USD",
            "lines": [{"charge_component_code": "BASE_FREIGHT", "amount": "2990.00"}],
        },
    )
    assert invoice.status_code == 201, invoice.text
    invoice_id = invoice.json()["id"]
    assert invoice.json()["charge_document_number"].startswith("CHG-")

    listed_invoices = client.get(
        "/api/v1/charge-management/invoices?q=INV-001",
        headers=AUTH,
    )
    assert listed_invoices.status_code == 200, listed_invoices.text
    assert listed_invoices.json()["total"] == 1
    assert listed_invoices.json()["items"][0]["id"] == invoice_id

    invoice_workspace = client.get(
        f"/api/v1/charge-management/invoices/{invoice_id}/workspace",
        headers=AUTH,
    )
    assert invoice_workspace.status_code == 200, invoice_workspace.text
    assert invoice_workspace.json()["invoice"]["id"] == invoice_id
    assert invoice_workspace.json()["charge_document"]["id"] == document_id
    assert invoice_workspace.json()["match_results"] == []

    updated_invoice = client.put(
        f"/api/v1/charge-management/invoices/{invoice_id}/workspace",
        headers=AUTH,
        json={
            "invoice_number": "INV-001-CORRECTED",
            "currency": "USD",
            "lines": [{"charge_component_code": "BASE_FREIGHT", "amount": "3000.00"}],
        },
    )
    assert updated_invoice.status_code == 200, updated_invoice.text
    assert updated_invoice.json()["invoice"]["invoice_number"] == "INV-001-CORRECTED"
    assert updated_invoice.json()["invoice"]["status"] == "CAPTURED"
    assert updated_invoice.json()["match_results"] == []

    matched = client.post(f"/api/v1/charge-management/invoices/{invoice_id}/match", headers=AUTH)
    assert matched.status_code == 200
    assert matched.json()["results"][0]["match_status"] == "MATCHED"

    matched_workspace = client.get(
        f"/api/v1/charge-management/invoices/{invoice_id}/workspace",
        headers=AUTH,
    )
    assert matched_workspace.status_code == 200, matched_workspace.text
    assert matched_workspace.json()["match_results"][0]["match_status"] == "MATCHED"

    approved = client.post(
        f"/api/v1/charge-management/charge-documents/{document_id}/approve",
        headers=AUTH,
    )
    assert approved.status_code == 200
    assert approved.json()["document"]["status"] == "APPROVED"

    exported = client.post(
        f"/api/v1/charge-management/charge-documents/{document_id}/post-export",
        headers=AUTH,
    )
    assert exported.status_code == 200
    assert exported.json()["status"] == "POSTED"

    reversed_response = client.post(
        f"/api/v1/charge-management/charge-documents/{document_id}/reverse",
        headers=AUTH,
        json={"reason": "Contract correction"},
    )
    assert reversed_response.status_code == 200
    assert reversed_response.json()["document"]["status"] == "REVERSED"


def test_default_customer_pricing_rates_without_provider_cost_layer() -> None:
    rate_book_id = _create_rate_book()
    payee_contract_id = _create_contract("CUSTOMER-PRICING-001", "PAYEE", rate_book_id)
    payee_release = client.post(
        f"/api/v1/charge-management/contracts/{payee_contract_id}/release",
        headers=AUTH,
    )
    assert payee_release.status_code == 200, payee_release.text

    quote_response = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "source_object_type": "MANUAL",
            "company_id": 10,
            "customer_id": 20,
            "origin_code": "BRSSZ",
            "destination_code": "USNYC",
            "mode": "OCEAN",
            "currency": "USD",
            "container_count": "2",
        },
    )
    assert quote_response.status_code == 201, quote_response.text
    quote_id = quote_response.json()["id"]
    _submit_quote(quote_id)

    determined = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/determine-contracts",
        headers=AUTH,
    )
    assert determined.status_code == 200, determined.text
    assert determined.json()["payer_contracts"] == []
    assert len(determined.json()["payee_contracts"]) == 1

    rated = client.post(f"/api/v1/charge-management/quote-requests/{quote_id}/rate", headers=AUTH)
    assert rated.status_code == 200, rated.text
    option = rated.json()["options"][0]
    assert option["payer_contract_id"] is None
    assert option["payee_contract_id"] == payee_contract_id
    assert option["payer_total_amount"] == "0.00"
    assert option["payee_total_amount"] == "3000.00"
    assert option["margin_amount"] == "0.00"
    assert {line["relationship_role"] for line in option["lines"]} == {"PAYEE"}

    awarded = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/award",
        headers=AUTH,
        json={"quote_option_id": option["id"]},
    )
    assert awarded.status_code == 200, awarded.text
    assert awarded.json()["charge_document"]["payer_total_amount"] == "0.00"
    assert awarded.json()["charge_document"]["payee_total_amount"] == "3000.00"


def test_openapi_exposes_core_paths() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/charge-management/allocation-profiles" in paths
    assert "post" in paths["/api/v1/charge-management/allocation-profiles"]
    assert "/api/v1/charge-management/allocation-profiles/{profile_id}/versions" in paths
    assert "/api/v1/charge-management/allocation-profile-versions/{version_id}" in paths
    assert "/api/v1/charge-management/allocation-profile-versions/{version_id}/publish" in paths
    assert "/api/v1/charge-management/business-date-profiles" in paths
    assert "post" in paths["/api/v1/charge-management/business-date-profiles"]
    assert "/api/v1/charge-management/business-date-profiles/{profile_id}" in paths
    assert "/api/v1/charge-management/business-date-profiles/{profile_id}/versions" in paths
    assert "/api/v1/charge-management/business-date-profile-versions/{version_id}" in paths
    assert "/api/v1/charge-management/business-date-profile-versions/{version_id}/publish" in paths
    assert "/api/v1/charge-management/business-date-profiles/{profile_id}/assignments" in paths
    assert "/api/v1/charge-management/business-date-profile-assignments/{assignment_id}" in paths
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/rate" in paths
    assert "/api/v1/charge-management/rate-books" in paths
    assert "get" in paths["/api/v1/charge-management/rate-books"]
    assert "/api/v1/charge-management/rate-books/{rate_book_id}/workspace" in paths
    assert "/api/v1/charge-management/calculation-templates" in paths
    assert "get" in paths["/api/v1/charge-management/calculation-templates"]
    assert "/api/v1/charge-management/calculation-templates/{calculation_template_id}/workspace" in paths
    assert "/api/v1/charge-management/contracts" in paths
    assert "/api/v1/charge-management/quote-requests" in paths
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/workspace" in paths
    assert "put" in paths["/api/v1/charge-management/quote-requests/{quote_request_id}/workspace"]
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/offers" in paths
    assert "/api/v1/charge-management/quote-offers/{offer_id}/workspace" in paths
    assert "put" in paths["/api/v1/charge-management/quote-offers/{offer_id}/workspace"]
    assert "/api/v1/charge-management/quote-offers/{offer_id}/withdraw" in paths
    assert "/api/v1/charge-management/quote-commitments/match" in paths
    assert "/api/v1/charge-management/quote-commitments/{commitment_id}/consume" in paths
    assert "/api/v1/charge-management/quote-commitment-consumptions/{consumption_id}/reverse" in paths
    assert "/api/v1/charge-management/charge-documents" in paths
    assert "get" in paths["/api/v1/charge-management/charge-documents"]
    assert "/api/v1/charge-management/charge-documents/{charge_document_id}" in paths
    assert "delete" in paths["/api/v1/charge-management/charge-documents/{charge_document_id}"]
    assert "/api/v1/charge-management/invoices" in paths
    assert "get" in paths["/api/v1/charge-management/invoices"]
    assert "/api/v1/charge-management/invoices/{invoice_id}/workspace" in paths
    assert "put" in paths["/api/v1/charge-management/invoices/{invoice_id}/workspace"]
    assert "/api/v1/charge-management/charge-documents/{charge_document_id}/post-export" in paths

    contract_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "contracts"
        / "charge-management-api.openapi.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert contract["info"]["title"] == "Charge Management API"
    assert "/api/v1/charge-management/rate-books" in contract["paths"]
    assert "/api/v1/charge-management/allocation-profiles" in contract["paths"]
    assert "/api/v1/charge-management/business-date-profiles" in contract["paths"]
    assert "get" in contract["paths"]["/api/v1/charge-management/rate-books"]
    assert "/api/v1/charge-management/rate-books/{rate_book_id}/workspace" in contract["paths"]
    assert "/api/v1/charge-management/calculation-templates" in contract["paths"]
    assert "get" in contract["paths"]["/api/v1/charge-management/calculation-templates"]
    assert "/api/v1/charge-management/calculation-templates/{calculation_template_id}/workspace" in contract["paths"]
    assert "/api/v1/charge-management/contracts" in contract["paths"]
    assert "/api/v1/charge-management/charge-documents" in contract["paths"]
    assert "get" in contract["paths"]["/api/v1/charge-management/charge-documents"]
    assert "/api/v1/charge-management/charge-documents/{charge_document_id}" in contract["paths"]
    assert "delete" in contract["paths"]["/api/v1/charge-management/charge-documents/{charge_document_id}"]
    assert "/api/v1/charge-management/invoices" in contract["paths"]
    assert "get" in contract["paths"]["/api/v1/charge-management/invoices"]
    assert "/api/v1/charge-management/invoices/{invoice_id}/workspace" in contract["paths"]
    assert "put" in contract["paths"]["/api/v1/charge-management/invoices/{invoice_id}/workspace"]
    assert "/api/v1/charge-management/quote-requests" in contract["paths"]
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/workspace" in contract["paths"]
    assert "put" in contract["paths"]["/api/v1/charge-management/quote-requests/{quote_request_id}/workspace"]
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/offers" in contract["paths"]
    assert "/api/v1/charge-management/quote-offers/{offer_id}/workspace" in contract["paths"]
    assert "put" in contract["paths"]["/api/v1/charge-management/quote-offers/{offer_id}/workspace"]
    assert "/api/v1/charge-management/quote-offers/{offer_id}/withdraw" in contract["paths"]
    assert "/api/v1/charge-management/quote-requests/{quote_request_id}/award" in contract["paths"]
    assert "/api/v1/charge-management/quote-commitments/match" in contract["paths"]
    assert "/api/v1/charge-management/quote-commitment-consumptions/{consumption_id}/reverse" in contract["paths"]
    assert "charge_date_basis" in contract["components"]["schemas"]["ChargeComponent"]["properties"]
    assert "charge_date_basis" in contract["components"]["schemas"]["ChargeComponentPayload"]["properties"]
    assert "allocation_profile_id" in contract["components"]["schemas"]["ChargeComponent"]["properties"]
    assert "business_date_policy_mode" in contract["components"]["schemas"]["ChargeComponent"]["properties"]
    assert "business_date_profile_id" in contract["components"]["schemas"]["ChargeComponent"]["properties"]
    assert "allocation_override_mode" in contract["components"]["schemas"]["ChargeComponentAlias"]["properties"]
    assert "final_posting_level" in contract["components"]["schemas"]["ChargeComponentAlias"]["properties"]
    assert "override_final_posting_level" in contract["components"]["schemas"]["ChargeComponentAlias"]["properties"]
    assert "source_level" in contract["components"]["schemas"]["ChargeAllocationProfileVersion"]["properties"]
    assert "final_posting_level" in contract["components"]["schemas"]["ChargeAllocationProfileVersion"]["properties"]
    assert "profile_code" in contract["components"]["schemas"]["BusinessDateProfile"]["properties"]
    assert "steps" in contract["components"]["schemas"]["BusinessDateProfileVersion"]["properties"]
    assert "scope_type" in contract["components"]["schemas"]["BusinessDateProfileAssignment"]["properties"]
    assert "shipment_scope" in contract["components"]["schemas"]["BusinessDateProfileAssignment"]["properties"]
    assert "business_purpose" in contract["components"]["schemas"]["BusinessDateProfileAssignment"]["properties"]
    assert "shipment_scope" in contract["components"]["schemas"]["ChargeDocumentCreate"]["properties"]
    assert "shipment_scope" in contract["components"]["schemas"]["ChargeDocument"]["properties"]
    assert "charge_date_basis" in contract["components"]["schemas"]["ChargeDocumentLineCreate"]["properties"]
    assert "charge_date_basis" in contract["components"]["schemas"]["ChargeLine"]["properties"]
    assert "pinned_allocation_snapshot_json" in contract["components"]["schemas"]["ChargeLine"]["properties"]


def _submit_quote(quote_request_id: int) -> dict:
    response = client.put(
        f"/api/v1/charge-management/quote-requests/{quote_request_id}/workspace",
        headers=AUTH,
        json={"status": "REQUESTED"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["quote_request"]["status"] == "REQUESTED"
    return payload


def _create_rate_book() -> int:
    response = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-OCEAN-001",
            "rate_book_name": "Ocean base rates",
            "currency": "USD",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "1500.00",
                    "basis": "CONTAINER",
                    "currency": "USD",
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _create_contract(contract_number: str, contract_role: str, rate_book_id: int) -> int:
    response = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": contract_number,
            "contract_name": contract_number,
            "contract_role": contract_role,
            "payer_party_ref": "party:customer:20" if contract_role == "PAYEE" else "party:platform:10",
            "payee_party_ref": "party:platform:10" if contract_role == "PAYEE" else "party:carrier:1",
            "party_role_ref": contract_role,
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
            "lines": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_book_id": rate_book_id,
                    "origin_code": "BRSSZ",
                    "destination_code": "USNYC",
                    "mode": "OCEAN",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])
