from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.charge_management import repository
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    repository.reset()


def _create_zone_dimension() -> dict:
    response = client.post(
        "/api/v1/charge-management/pricing-dimensions",
        headers=AUTH,
        json={
            "dimension_code": "DELIVERY_ZONE",
            "dimension_name": "Delivery zone",
            "description": "Caller-neutral road delivery tariff zone.",
            "data_type": "STRING",
            "allowed_values": ["ZONE_A", "ZONE_B"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_mapping_profile() -> dict:
    response = client.post(
        "/api/v1/charge-management/caller-mapping-profiles",
        headers=AUTH,
        json={
            "profile_code": "ROAD_TMS_V1",
            "profile_name": "Road TMS schema v1",
            "caller_system_code": "ROAD_TMS",
            "schema_version": "1.0",
            "mappings": [
                {
                    "source_attribute": "shipment.deliveryZone",
                    "dimension_code": "DELIVERY_ZONE",
                    "required": True,
                    "value_map": {"central": "ZONE_A", "remote": "ZONE_B"},
                },
                {
                    "source_attribute": "shipment.serviceTier",
                    "dimension_code": "SERVICE_LEVEL",
                    "required": True,
                    "value_map": {"standard": "STANDARD", "priority": "EXPRESS"},
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_system_and_custom_dimensions_are_discoverable_and_guarded() -> None:
    listed = client.get(
        "/api/v1/charge-management/pricing-dimensions?active_only=true",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    system = {item["dimension_code"]: item for item in listed.json()["items"]}
    assert {
        "ORIGIN_CODE",
        "DESTINATION_CODE",
        "TRANSPORT_MODE",
        "EQUIPMENT_TYPE",
        "COMMODITY_CODE",
        "SERVICE_LEVEL",
        "CHARGE_CONTEXT",
    } <= set(system)
    assert system["SERVICE_LEVEL"]["built_in_field"] == "service_level"
    assert system["SERVICE_LEVEL"]["is_system"] is True

    custom = _create_zone_dimension()
    assert custom["dimension_code"] == "DELIVERY_ZONE"
    assert custom["allowed_values"] == ["ZONE_A", "ZONE_B"]

    duplicate = client.post(
        "/api/v1/charge-management/pricing-dimensions",
        headers=AUTH,
        json={
            "dimension_code": "delivery_zone",
            "dimension_name": "Duplicate",
        },
    )
    assert duplicate.status_code == 409

    protected = client.delete(
        f"/api/v1/charge-management/pricing-dimensions/{system['SERVICE_LEVEL']['id']}",
        headers=AUTH,
    )
    assert protected.status_code == 409


def test_caller_profile_maps_nested_attributes_and_validates_contract() -> None:
    _create_zone_dimension()
    profile = _create_mapping_profile()
    assert profile["caller_system_code"] == "ROAD_TMS"
    assert profile["schema_version"] == "1.0"
    assert profile["canonical_dimension_codes"] == ["DELIVERY_ZONE", "SERVICE_LEVEL"]

    preview = client.post(
        f"/api/v1/charge-management/caller-mapping-profiles/{profile['id']}/preview",
        headers=AUTH,
        json={
            "caller_attributes": {
                "shipment": {"deliveryZone": "central", "serviceTier": "priority"}
            }
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["dimension_values"] == {
        "DELIVERY_ZONE": "ZONE_A",
        "SERVICE_LEVEL": "EXPRESS",
    }
    assert preview.json()["standard_fields"] == {"service_level": "EXPRESS"}

    missing = client.post(
        f"/api/v1/charge-management/caller-mapping-profiles/{profile['id']}/preview",
        headers=AUTH,
        json={"caller_attributes": {"shipment": {"deliveryZone": "central"}}},
    )
    assert missing.status_code == 422
    assert "shipment.serviceTier" in missing.text

    mismatch = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "caller_mapping_profile_code": "ROAD_TMS_V1",
            "caller_system_code": "OTHER_TMS",
            "caller_attributes": {
                "shipment": {"deliveryZone": "central", "serviceTier": "standard"}
            },
        },
    )
    assert mismatch.status_code == 422

    incomplete_identity = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={"caller_system_code": "another_tms"},
    )
    assert incomplete_identity.status_code == 422

    canonical_caller = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "caller_system_code": "another_tms",
            "caller_schema_version": "2026-08",
            "service_level": "express",
        },
    )
    assert canonical_caller.status_code == 201, canonical_caller.text
    assert canonical_caller.json()["caller_system_code"] == "ANOTHER_TMS"
    assert canonical_caller.json()["dimension_values"]["SERVICE_LEVEL"] == "EXPRESS"
    cleared = client.put(
        f"/api/v1/charge-management/quote-requests/{canonical_caller.json()['id']}/workspace",
        headers=AUTH,
        json={"service_level": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["quote_request"]["service_level"] is None
    assert "SERVICE_LEVEL" not in cleared.json()["quote_request"]["dimension_values"]


def test_custom_dimension_selects_rate_for_mapped_caller_request() -> None:
    dimension = _create_zone_dimension()
    profile = _create_mapping_profile()

    book = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "ROAD-ZONE-RATES",
            "rate_book_name": "Road zone rates",
            "charge_component_code": "ROAD_FREIGHT_FTL",
            "dimension_codes": ["DELIVERY_ZONE"],
            "currency": "EUR",
            "entries": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "125.00",
                    "currency": "EUR",
                    "dimension_values": {"DELIVERY_ZONE": "ZONE_A"},
                },
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "225.00",
                    "currency": "EUR",
                    "dimension_values": {"DELIVERY_ZONE": "ZONE_B"},
                },
            ],
        },
    )
    assert book.status_code == 201, book.text
    assert book.json()["dimension_codes"] == ["DELIVERY_ZONE"]
    assert book.json()["entries"][0]["dimension_values"] == {"DELIVERY_ZONE": "ZONE_A"}
    published = client.post(
        f"/api/v1/charge-management/rate-books/{book.json()['id']}/publish",
        headers=AUTH,
    )
    assert published.status_code == 200, published.text

    contract = client.post(
        "/api/v1/charge-management/contracts",
        headers=AUTH,
        json={
            "contract_number": "ROAD-ZONE-CONTRACT",
            "contract_name": "Road zone contract",
            "contract_role": "PAYEE",
            "company_id": 1001,
            "customer_id": 2001,
            "currency": "EUR",
            "lines": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_book_id": book.json()["id"],
                    "charge_context": "ROAD",
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
        json={
            "request_number": "ROAD-TMS-QUOTE-1",
            "source_object_type": "ROAD_SHIPMENT",
            "company_id": 1001,
            "customer_id": 2001,
            "currency": "EUR",
            "charge_context": "ROAD",
            "caller_mapping_profile_code": "ROAD_TMS_V1",
            "caller_attributes": {
                "shipment": {"deliveryZone": "Central", "serviceTier": "standard"}
            },
        },
    )
    assert quote.status_code == 201, quote.text
    assert quote.json()["caller_system_code"] == "ROAD_TMS"
    assert quote.json()["caller_schema_version"] == "1.0"
    assert quote.json()["service_level"] == "STANDARD"
    assert quote.json()["dimension_values"]["DELIVERY_ZONE"] == "ZONE_A"
    assert quote.json()["dimension_values"]["CHARGE_CONTEXT"] == "ROAD"

    submitted = client.put(
        f"/api/v1/charge-management/quote-requests/{quote.json()['id']}/workspace",
        headers=AUTH,
        json={"status": "REQUESTED"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["quote_request"]["dimension_values"]["DELIVERY_ZONE"] == "ZONE_A"

    rated = client.post(
        f"/api/v1/charge-management/quote-requests/{quote.json()['id']}/rate",
        headers=AUTH,
    )
    assert rated.status_code == 200, rated.text
    lines = [line for option in rated.json()["options"] for line in option["lines"]]
    assert len(lines) == 1
    assert lines[0]["rate_amount"] == "125.000000"
    assert lines[0]["amount"] == "125.00"

    dimension_in_use = client.delete(
        f"/api/v1/charge-management/pricing-dimensions/{dimension['id']}",
        headers=AUTH,
    )
    assert dimension_in_use.status_code == 409

    changed_profile = client.put(
        f"/api/v1/charge-management/caller-mapping-profiles/{profile['id']}",
        headers=AUTH,
        json={
            "profile_code": "ROAD_TMS_V1",
            "profile_name": "Road TMS schema v1",
            "caller_system_code": "ROAD_TMS",
            "schema_version": "1.0",
            "mappings": [
                {
                    "source_attribute": "shipment.newDeliveryZone",
                    "dimension_code": "DELIVERY_ZONE",
                    "required": True,
                }
            ],
        },
    )
    assert changed_profile.status_code == 409
    assert "immutable" in changed_profile.text


def test_rate_row_rejects_unselected_unknown_or_invalid_dimensions() -> None:
    _create_zone_dimension()
    unselected = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "INVALID-DIMENSION-BOOK",
            "rate_book_name": "Invalid dimension book",
            "charge_component_code": "ROAD_FREIGHT_FTL",
            "entries": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "10",
                    "dimension_values": {"DELIVERY_ZONE": "ZONE_A"},
                }
            ],
        },
    )
    assert unselected.status_code == 422

    invalid_value = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "INVALID-DIMENSION-VALUE",
            "rate_book_name": "Invalid dimension value",
            "charge_component_code": "ROAD_FREIGHT_FTL",
            "dimension_codes": ["DELIVERY_ZONE"],
            "entries": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "10",
                    "dimension_values": {"DELIVERY_ZONE": "UNKNOWN"},
                }
            ],
        },
    )
    assert invalid_value.status_code == 422
    assert "allowed_values" in invalid_value.text

    duplicated_builtin = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "DUPLICATED-BUILTIN-DIMENSION",
            "rate_book_name": "Duplicated built-in dimension",
            "charge_component_code": "ROAD_FREIGHT_FTL",
            "dimension_codes": ["ORIGIN_CODE"],
            "entries": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "10",
                    "dimension_values": {"ORIGIN_CODE": "ESBCN"},
                }
            ],
        },
    )
    assert duplicated_builtin.status_code == 422
    assert "row_attribute_keys" in duplicated_builtin.text
