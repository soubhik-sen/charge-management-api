from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.charge_management import repository
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    repository.reset()


def _manual_fx_source_id() -> int:
    response = client.get(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    return next(row["id"] for row in response.json()["items"] if row["source_code"] == "MANUAL")


def _create_eur_usd_rate(rate: str = "1.2") -> int:
    response = client.post(
        "/api/v1/charge-management/fx-rates",
        headers=AUTH,
        json={
            "source_id": _manual_fx_source_id(),
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-06-01",
            "rate": rate,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_preview_calculates_percentage_and_allocates_exactly() -> None:
    profiles = client.get(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
    )
    assert profiles.status_code == 200, profiles.text
    profile = next(
        row
        for row in profiles.json()["items"]
        if row["profile_code"] == "DIRECT_HEADER_DEFAULT"
    )

    response = client.post(
        "/api/v1/charge-management/calculations/preview",
        headers=AUTH,
        json={
            "basis": "PERCENTAGE",
            "rate_percent": "12.5",
            "percentage_base_amount": "200",
            "source_currency": "USD",
            "target_currency": "USD",
            "allocation_profile_version_id": profile["published_version_id"],
            "allocation_targets": [
                {
                    "target_level": "HOUSE",
                    "target_object_type": "house",
                    "target_object_id": "H-1",
                    "driver_value": "1",
                },
                {
                    "target_level": "HOUSE",
                    "target_object_type": "house",
                    "target_object_id": "H-2",
                    "driver_value": "2",
                },
            ],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_amount"] == "25.00"
    assert payload["amount"] == "25.00"
    assert payload["allocated_amount"] == "25.00"
    assert payload["unallocated_amount"] == "0.00"
    assert [row["allocated_amount"] for row in payload["allocations"]] == ["8.33", "16.67"]
    assert payload["allocation_config_snapshot_json"]["profile_code"] == "DIRECT_HEADER_DEFAULT"


def test_allocation_profile_effectivity_equal_fallback_and_optimistic_lock() -> None:
    profiles = client.get(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
    ).json()["items"]
    profile = next(
        row for row in profiles if row["profile_code"] == "DIRECT_HEADER_DEFAULT"
    )
    created = client.post(
        f"/api/v1/charge-management/allocation-profiles/{profile['id']}/versions",
        headers=AUTH,
        json={
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "source_level": "HOUSE",
            "final_posting_level": "HOUSE",
            "missing_driver_policy": "EQUAL",
        },
    )
    assert created.status_code == 201, created.text
    version = max(created.json()["versions"], key=lambda row: row["version_number"])
    assert version["lock_version"] == 1

    stale = client.put(
        f"/api/v1/charge-management/allocation-profile-versions/{version['id']}",
        headers=AUTH,
        json={
            "source_level": "HOUSE",
            "final_posting_level": "HOUSE",
            "missing_driver_policy": "EQUAL",
            "expected_lock_version": 7,
        },
    )
    assert stale.status_code == 409
    updated = client.put(
        f"/api/v1/charge-management/allocation-profile-versions/{version['id']}",
        headers=AUTH,
        json={
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "source_level": "HOUSE",
            "final_posting_level": "HOUSE",
            "missing_driver_policy": "EQUAL",
            "expected_lock_version": 1,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["lock_version"] == 2

    preview = client.post(
        "/api/v1/charge-management/calculations/preview",
        headers=AUTH,
        json={
            "basis": "FLAT",
            "rate_amount": "10",
            "allocation_profile_version_id": version["id"],
            "allocation_targets": [
                {
                    "target_level": "HOUSE",
                    "target_object_type": "house",
                    "target_object_id": "H-1",
                    "driver_value": "0",
                },
                {
                    "target_level": "HOUSE",
                    "target_object_type": "house",
                    "target_object_id": "H-2",
                    "driver_value": "0",
                },
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    assert [row["allocated_amount"] for row in preview.json()["allocations"]] == ["5.00", "5.00"]


def test_preview_resolves_fx_and_returns_provenance() -> None:
    fx_rate_id = _create_eur_usd_rate()
    response = client.post(
        "/api/v1/charge-management/calculations/preview",
        headers=AUTH,
        json={
            "basis": "FLAT",
            "rate_amount": "100",
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-06-02",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_amount"] == "100.00"
    assert payload["amount"] == "120.00"
    assert payload["fx_resolution"]["rate"]["id"] == fx_rate_id
    assert payload["fx_resolution"]["selected_rate_date"] == "2026-06-01"
    assert payload["fx_resolution"]["effective_rate"] == "1.2000000000"


def test_flux_compatible_component_and_business_date_fields_round_trip() -> None:
    profiles = client.get(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
    ).json()["items"]
    allocation_profile_id = next(
        row["id"] for row in profiles if row["profile_code"] == "DIRECT_HEADER_DEFAULT"
    )
    component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "FLUX_COMPAT_TEST",
            "component_name": "Flux compatibility test",
            "default_side": "PAYEE",
            "default_allocation_profile_id": allocation_profile_id,
        },
    )
    assert component.status_code == 201, component.text
    component_payload = component.json()
    assert component_payload["default_party_role"] == "PAYEE"
    assert component_payload["default_side"] == "PAYEE"
    assert component_payload["default_relationship_role"] == "PAYEE"
    assert component_payload["allocation_profile_id"] == allocation_profile_id
    assert component_payload["default_allocation_profile_id"] == allocation_profile_id

    profile = client.post(
        "/api/v1/charge-management/business-date-profiles",
        headers=AUTH,
        json={
            "profile_key": "FLUX_DATE_COMPAT",
            "profile_name": "Flux date compatibility",
            "event_codes": ["SHIPMENT_ACTUAL_DEPARTURE_DATE", "DOCUMENT_DATE"],
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
        },
    )
    assert profile.status_code == 201, profile.text
    profile_payload = profile.json()
    assert profile_payload["profile_code"] == "FLUX_DATE_COMPAT"
    assert profile_payload["profile_key"] == "FLUX_DATE_COMPAT"
    version = profile_payload["versions"][0]
    assert version["event_codes"] == ["SHIPMENT_ACTUAL_DEPARTURE_DATE", "DOCUMENT_DATE"]
    assert version["effective_from"] == "2026-01-01"
    assert version["effective_to"] == "2026-12-31"
    published = client.post(
        f"/api/v1/charge-management/business-date-profile-versions/{version['id']}/publish",
        headers=AUTH,
    )
    assert published.status_code == 200, published.text

    resolved = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile_payload["id"],
            "date_values": [
                {
                    "date_type": "shipment_actual_departure_date",
                    "date_value": "2026-06-08",
                },
                {"date_type": "DOCUMENT_DATE", "date_value": "2026-06-10"},
            ],
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolved_date"] == "2026-06-08"
    assert resolved.json()["selected_date_key"] == "SHIPMENT_ACTUAL_DEPARTURE_DATE"
    assert resolved.json()["supplied_date_keys"] == [
        "SHIPMENT_ACTUAL_DEPARTURE_DATE",
        "DOCUMENT_DATE",
    ]

    legacy_context = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile_payload["id"],
            "context": {
                "SHIPMENT_ACTUAL_DEPARTURE_DATE": "2026-06-09",
                "DOCUMENT_DATE": "2026-06-10",
            },
        },
    )
    assert legacy_context.status_code == 200, legacy_context.text
    assert legacy_context.json()["resolved_date"] == "2026-06-09"
    assert legacy_context.json()["supplied_date_keys"] == []

    unsupported_date_type = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile_payload["id"],
            "date_values": [
                {"date_type": "CUSTOM_UNKNOWN_DATE", "date_value": "2026-06-08"}
            ],
        },
    )
    assert unsupported_date_type.status_code == 422

    duplicate_date_type = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile_payload["id"],
            "date_values": [
                {"date_type": "DOCUMENT_DATE", "date_value": "2026-06-08"},
                {"date_type": "document_date", "date_value": "2026-06-09"},
            ],
        },
    )
    assert duplicate_date_type.status_code == 422

    invalid_date_value = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile_payload["id"],
            "date_values": [
                {"date_type": "DOCUMENT_DATE", "date_value": "not-a-date"}
            ],
        },
    )
    assert invalid_date_value.status_code == 422


def test_seeded_road_business_date_profile_uses_explicit_pickup_dates() -> None:
    profiles = client.get(
        "/api/v1/charge-management/business-date-profiles",
        headers=AUTH,
    )
    assert profiles.status_code == 200, profiles.text
    profile = next(
        row
        for row in profiles.json()["items"]
        if row["profile_code"] == "ROAD_SHIPMENT_STANDARD"
    )
    published_version = next(
        version for version in profile["versions"] if version["status"] == "PUBLISHED"
    )
    assert [step["date_key"] for step in published_version["steps"]] == [
        "ROAD_ACTUAL_PICKUP_DATE",
        "ROAD_PLANNED_PICKUP_DATE",
        "CMR_ISSUE_DATE",
        "DOCUMENT_DATE",
    ]

    resolved = client.post(
        "/api/v1/charge-management/business-dates/resolve",
        headers=AUTH,
        json={
            "profile_id": profile["id"],
            "date_values": [
                {
                    "date_type": "ROAD_PLANNED_PICKUP_DATE",
                    "date_value": "2026-06-08",
                },
                {"date_type": "CMR_ISSUE_DATE", "date_value": "2026-06-09"},
                {"date_type": "DOCUMENT_DATE", "date_value": "2026-06-10"},
            ],
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolved_date"] == "2026-06-08"
    assert resolved.json()["selected_date_key"] == "ROAD_PLANNED_PICKUP_DATE"


def test_document_converts_foreign_lines_and_invoice_requires_document_currency() -> None:
    fx_rate_id = _create_eur_usd_rate()
    document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "document_date": "2026-06-02",
            "currency": "USD",
            "lines": [
                {
                    "relationship_role": "PAYER",
                    "charge_component_code": "BASE_FREIGHT",
                    "expected_amount": "100",
                    "currency": "EUR",
                }
            ],
        },
    )

    assert document.status_code == 201, document.text
    payload = document.json()
    assert payload["payer_total_amount"] == "120.00"
    assert payload["lines"][0]["currency"] == "USD"
    assert payload["lines"][0]["source_currency"] == "EUR"
    assert payload["lines"][0]["source_amount"] == "100.00"
    assert payload["lines"][0]["fx_rate_id"] == fx_rate_id

    invoice = client.post(
        "/api/v1/charge-management/invoices",
        headers=AUTH,
        json={
            "charge_document_id": payload["id"],
            "invoice_number": "INV-EUR-1",
            "currency": "EUR",
            "lines": [{"charge_component_code": "BASE_FREIGHT", "amount": "100"}],
        },
    )
    assert invoice.status_code == 422
    assert "must match charge document currency USD" in invoice.json()["detail"]


def test_quote_rating_executes_template_subtotals_and_percentage_steps() -> None:
    rate_book = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-TEMPLATE-BASE",
            "rate_book_name": "Template base rates",
            "charge_component_code": "BASE_FREIGHT",
            "row_attribute_keys": ["basis_override"],
            "status": "DRAFT",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "100",
                    "basis_override": "FLAT",
                }
            ],
        },
    )
    assert rate_book.status_code == 201, rate_book.text
    rate_book_id = rate_book.json()["id"]
    published_rate_book = client.post(
        f"/api/v1/charge-management/rate-books/{rate_book_id}/publish",
        headers=AUTH,
    )
    assert published_rate_book.status_code == 200, published_rate_book.text
    fuel_rate_book = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-TEMPLATE-FUEL",
            "rate_book_name": "Template fuel rates",
            "charge_component_code": "FUEL_SURCHARGE",
            "row_attribute_keys": ["basis_override"],
            "status": "DRAFT",
            "entries": [
                {
                    "charge_component_code": "FUEL_SURCHARGE",
                    "rate_percent": "10",
                    "basis_override": "PERCENTAGE",
                }
            ],
        },
    )
    assert fuel_rate_book.status_code == 201, fuel_rate_book.text
    fuel_rate_book_id = fuel_rate_book.json()["id"]
    published_fuel_rate_book = client.post(
        f"/api/v1/charge-management/rate-books/{fuel_rate_book_id}/publish",
        headers=AUTH,
    )
    assert published_fuel_rate_book.status_code == 200, published_fuel_rate_book.text
    template = client.post(
        "/api/v1/charge-management/calculation-templates",
        headers=AUTH,
        json={
            "template_code": "TPL-FREIGHT-SURCHARGE",
            "template_name": "Freight plus surcharge",
            "status": "DRAFT",
            "steps": [
                {
                    "step_number": 1,
                    "charge_component_code": "BASE_FREIGHT",
                    "relationship_role": "PAYEE",
                    "subtotal_key": "FREIGHT",
                    "rate_book_id": rate_book_id,
                },
                {
                    "step_number": 2,
                    "charge_component_code": "FUEL_SURCHARGE",
                    "relationship_role": "PAYEE",
                    "subtotal_key": "FREIGHT",
                    "rate_book_id": fuel_rate_book_id,
                },
            ],
        },
    )
    assert template.status_code == 201, template.text
    published_template = client.post(
        f"/api/v1/charge-management/calculation-templates/{template.json()['id']}/publish",
        headers=AUTH,
    )
    assert published_template.status_code == 200, published_template.text
    contract = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": "PAYEE-TEMPLATE-EXECUTION",
            "contract_name": "Payee template execution",
            "contract_role": "PAYEE",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
            "lines": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "calculation_template_id": template.json()["id"],
                }
            ],
        },
    )
    assert contract.status_code == 201, contract.text
    released = client.post(
        f"/api/v1/charge-management/contracts/{contract.json()['id']}/release",
        headers=AUTH,
    )
    assert released.status_code == 200, released.text
    quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={"company_id": 10, "customer_id": 20, "currency": "USD"},
    )
    assert quote.status_code == 201, quote.text
    submitted = client.put(
        f"/api/v1/charge-management/quote-requests/{quote.json()['id']}/workspace",
        headers=AUTH,
        json={"status": "REQUESTED"},
    )
    assert submitted.status_code == 200, submitted.text
    rated = client.post(
        f"/api/v1/charge-management/quote-requests/{quote.json()['id']}/rate",
        headers=AUTH,
    )

    assert rated.status_code == 200, rated.text
    option = rated.json()["options"][0]
    assert option["payee_total_amount"] == "110.00"
    assert [line["amount"] for line in option["lines"]] == ["100.00", "10.00"]
    assert option["lines"][1]["calculation_input_snapshot_json"]["percentage_base_amount"] == "100.00"
    assert all(line["source_rate_book_entry_id"] is not None for line in option["lines"])


def test_rate_books_use_immutable_published_versions() -> None:
    invalid_initial_status = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-INVALID-ACTIVE",
            "rate_book_name": "Invalid direct activation",
            "status": "ACTIVE",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "100",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert invalid_initial_status.status_code == 422

    created = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RB-VERSIONED",
            "rate_book_name": "Versioned rates",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "100",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    first = created.json()
    assert first["version_number"] == 1
    assert first["lock_version"] == 1
    bypass_publish = client.put(
        f"/api/v1/charge-management/rate-books/{first['id']}/workspace",
        headers=AUTH,
        json={
            "rate_book_code": "RB-VERSIONED",
            "rate_book_name": "Versioned rates",
            "status": "PUBLISHED",
            "expected_lock_version": 1,
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "100",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert bypass_publish.status_code == 422
    published_first = client.post(
        f"/api/v1/charge-management/rate-books/{first['id']}/publish",
        headers=AUTH,
    )
    assert published_first.status_code == 200, published_first.text
    assert published_first.json()["rate_book"]["status"] == "PUBLISHED"

    immutable_update = client.put(
        f"/api/v1/charge-management/rate-books/{first['id']}/workspace",
        headers=AUTH,
        json={
            "rate_book_code": "RB-VERSIONED",
            "rate_book_name": "Unsafe overwrite",
            "entries": [],
        },
    )
    assert immutable_update.status_code == 409

    second = client.post(
        f"/api/v1/charge-management/rate-books/{first['id']}/versions",
        headers=AUTH,
        json={
            "rate_book_code": "RB-VERSIONED",
            "rate_book_name": "Versioned rates v2",
            "status": "DRAFT",
            "entries": [
                {
                    "charge_component_code": "BASE_FREIGHT",
                    "rate_amount": "125",
                    "basis": "FLAT",
                }
            ],
        },
    )
    assert second.status_code == 201, second.text
    second_book = second.json()["rate_book"]
    assert second_book["version_number"] == 2
    assert second_book["supersedes_rate_book_id"] == first["id"]
    published_second = client.post(
        f"/api/v1/charge-management/rate-books/{second_book['id']}/publish",
        headers=AUTH,
    )
    assert published_second.status_code == 200, published_second.text
    versions = published_second.json()["versions"]
    assert [row["version_number"] for row in versions] == [2, 1]
    assert versions[0]["status"] == "PUBLISHED"
    assert versions[1]["status"] == "RETIRED"
