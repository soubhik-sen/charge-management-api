"""Seed a rerunnable road-freight pricing study through LedgerFlow's public API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = os.getenv("LEDGERFLOW_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.getenv("LEDGERFLOW_SERVICE_TOKEN", "local-dev-token")
API = "/api/v1/charge-management"
COMPANY_ID = int(os.getenv("LEDGERFLOW_STUDY_COMPANY_ID", "1001"))
CUSTOMER_ID = int(os.getenv("LEDGERFLOW_STUDY_CUSTOMER_ID", "2001"))
TEMPLATE_CODE = "TC-DEMO-ROAD-CUSTOMER"
CONTRACT_NUMBER = "TC-DEMO-PAYEE-2001"
STUDY_MARKER = "[ledgerflow-road-study:v1]"


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "X-Subject": "ledgerflow-road-study-bootstrap",
        "X-Roles": "administrator,charge_admin",
    }
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                f"{BASE_URL}{path}",
                data=body,
                headers=headers,
                method=method,
            ),
            timeout=12,
        ) as response:
            response_body = response.read()
            return response.status, json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read()
        return exc.code, json.loads(response_body) if response_body else {}


def require(status: int, expected: set[int], payload: Any, label: str) -> Any:
    if status not in expected:
        raise RuntimeError(f"{label}: HTTP {status} {payload}")
    return payload


def wait_until_ready() -> None:
    for _ in range(40):
        try:
            status, _ = request("GET", "/health")
            if status == 200:
                return
        except (OSError, TimeoutError, urllib.error.URLError):
            pass
        time.sleep(1)
    raise RuntimeError("LedgerFlow did not become ready")


def list_exact(path: str, field: str, value: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"q": value, "limit": 200})
    status, result = request("GET", f"{API}/{path}?{query}")
    require(status, {200}, result, f"list {path}")
    normalized = value.strip().upper()
    return [
        item
        for item in result.get("items", [])
        if str(item.get(field, "")).strip().upper() == normalized
    ]


def require_reference(path: str, field: str, code: str) -> dict[str, Any]:
    matches = list_exact(path, field, code)
    if not matches:
        raise RuntimeError(f"Required LedgerFlow reference {code} was not found in {path}")
    return matches[0]


def ensure_statistical_component() -> dict[str, Any]:
    code = "ROAD_INTERNAL_COST_REFERENCE"
    existing = list_exact("components", "component_code", code)
    if existing:
        return existing[0]

    calculation_profile = require_reference(
        "calculation-profiles",
        "profile_code",
        "PER_KILOMETER",
    )
    allocation_profile = require_reference(
        "allocation-profiles",
        "profile_code",
        "ROAD_WEIGHT_TO_ITEM",
    )
    date_profile = require_reference(
        "business-date-profiles",
        "profile_code",
        "ROAD_SHIPMENT_STANDARD",
    )
    status, component = request(
        "POST",
        f"{API}/components",
        {
            "component_code": code,
            "component_name": "Road Internal Cost Reference",
            "category": "STATISTICAL",
            "default_party_role": "PAYEE",
            "charge_context": "ROAD",
            "calculation_basis": "DISTANCE",
            "business_date_policy_mode": "PROFILE_OVERRIDE",
            "business_date_profile_id": date_profile["id"],
            "allocation_profile_id": allocation_profile["id"],
            "allocation_profile_version_id": allocation_profile["published_version_id"],
            "default_calculation_profile_id": calculation_profile["id"],
            "is_tax": False,
            "is_active": True,
        },
    )
    return require(status, {201}, component, "create statistical component")


def rate_book_specs() -> list[dict[str, Any]]:
    common = {
        "currency": "EUR",
        "valid_from": "2026-01-01",
        "valid_to": "2027-12-31",
        "status": "DRAFT",
        "is_active": True,
    }
    return [
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-EUR",
            "rate_book_name": "Road study - FTL linehaul",
            "charge_component_code": "ROAD_FREIGHT_FTL",
            "row_attribute_keys": [
                "origin_code",
                "destination_code",
                "mode",
                "equipment_type",
                "service_level",
                "priority",
            ],
            "description": f"{STUDY_MARKER} Customer linehaul with lane and service fallbacks.",
            "calculation_basis": "FLAT",
            "entries": [
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "450.00",
                    "currency": "EUR",
                    "origin_code": "ESBCN",
                    "destination_code": "ESMAD",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "service_level": "STANDARD",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "520.00",
                    "currency": "EUR",
                    "origin_code": "ESBCN",
                    "destination_code": "ESMAD",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "service_level": "EXPRESS",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "395.00",
                    "currency": "EUR",
                    "origin_code": "ESBCN",
                    "destination_code": "ESVLC",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "service_level": "STANDARD",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_FREIGHT_FTL",
                    "rate_amount": "475.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-FUEL-PCT",
            "rate_book_name": "Road study - fuel surcharge",
            "charge_component_code": "ROAD_FUEL_SURCHARGE",
            "row_attribute_keys": ["mode", "service_level", "priority"],
            "description": f"{STUDY_MARKER} Fuel percentages by service level.",
            "calculation_basis": "PERCENTAGE",
            "entries": [
                {
                    "charge_component_code": "ROAD_FUEL_SURCHARGE",
                    "rate_percent": "12.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "service_level": "STANDARD",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_FUEL_SURCHARGE",
                    "rate_percent": "13.50",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "service_level": "EXPRESS",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_FUEL_SURCHARGE",
                    "rate_percent": "12.50",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-TOLL-EUR",
            "rate_book_name": "Road study - toll per kilometer",
            "charge_component_code": "ROAD_TOLL",
            "row_attribute_keys": ["mode", "equipment_type", "priority"],
            "description": f"{STUDY_MARKER} Distance toll rates by equipment.",
            "calculation_basis": "DISTANCE",
            "entries": [
                {
                    "charge_component_code": "ROAD_TOLL",
                    "rate_amount": "0.18",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_TOLL",
                    "rate_amount": "0.21",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "REEFER",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_TOLL",
                    "rate_amount": "0.19",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-TAIL-LIFT-EUR",
            "rate_book_name": "Road study - tail-lift service",
            "charge_component_code": "TAIL_LIFT_SERVICE",
            "row_attribute_keys": ["mode", "equipment_type", "priority"],
            "description": f"{STUDY_MARKER} Conditional tail-lift charges by equipment.",
            "calculation_basis": "FLAT",
            "entries": [
                {
                    "charge_component_code": "TAIL_LIFT_SERVICE",
                    "rate_amount": "35.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "priority": 10,
                },
                {
                    "charge_component_code": "TAIL_LIFT_SERVICE",
                    "rate_amount": "28.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "BOX_TRUCK",
                    "priority": 10,
                },
                {
                    "charge_component_code": "TAIL_LIFT_SERVICE",
                    "rate_amount": "32.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-WAITING-EUR",
            "rate_book_name": "Road study - waiting time",
            "charge_component_code": "WAITING_TIME",
            "row_attribute_keys": ["mode", "service_level", "priority"],
            "description": f"{STUDY_MARKER} Conditional waiting rates per billable hour.",
            "calculation_basis": "PER_HOUR",
            "entries": [
                {
                    "charge_component_code": "WAITING_TIME",
                    "rate_amount": "28.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "service_level": "STANDARD",
                    "priority": 10,
                },
                {
                    "charge_component_code": "WAITING_TIME",
                    "rate_amount": "35.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "service_level": "EXPRESS",
                    "priority": 10,
                },
                {
                    "charge_component_code": "WAITING_TIME",
                    "rate_amount": "30.00",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
        {
            **common,
            "rate_book_code": "TC-DEMO-ROAD-INTERNAL-COST",
            "rate_book_name": "Road study - internal cost benchmark",
            "charge_component_code": "ROAD_INTERNAL_COST_REFERENCE",
            "row_attribute_keys": ["mode", "equipment_type", "priority"],
            "description": f"{STUDY_MARKER} Non-commercial linehaul cost benchmark per kilometer.",
            "calculation_basis": "DISTANCE",
            "entries": [
                {
                    "charge_component_code": "ROAD_INTERNAL_COST_REFERENCE",
                    "rate_amount": "0.62",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "CURTAINSIDER",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_INTERNAL_COST_REFERENCE",
                    "rate_amount": "0.74",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "equipment_type": "REEFER",
                    "priority": 10,
                },
                {
                    "charge_component_code": "ROAD_INTERNAL_COST_REFERENCE",
                    "rate_amount": "0.65",
                    "currency": "EUR",
                    "mode": "ROAD",
                    "priority": 900,
                },
            ],
        },
    ]


def ensure_rate_book(spec: dict[str, Any]) -> dict[str, Any]:
    versions = list_exact("rate-books", "rate_book_code", spec["rate_book_code"])
    published_study_versions = [
        row
        for row in versions
        if row.get("status") == "PUBLISHED" and STUDY_MARKER in (row.get("description") or "")
    ]
    if published_study_versions:
        return max(published_study_versions, key=lambda row: (row["version_number"], row["id"]))

    latest = max(versions, key=lambda row: (row["version_number"], row["id"])) if versions else None
    if latest is None:
        status, rate_book = request("POST", f"{API}/rate-books", spec)
        rate_book = require(status, {201}, rate_book, f"create {spec['rate_book_code']}")
    elif latest.get("status") == "DRAFT":
        update = {**spec, "expected_lock_version": latest["lock_version"]}
        status, workspace = request(
            "PUT",
            f"{API}/rate-books/{latest['id']}/workspace",
            update,
        )
        workspace = require(status, {200}, workspace, f"update {spec['rate_book_code']}")
        rate_book = workspace["rate_book"]
    else:
        status, workspace = request(
            "POST",
            f"{API}/rate-books/{latest['id']}/versions",
            spec,
        )
        workspace = require(status, {201}, workspace, f"version {spec['rate_book_code']}")
        rate_book = workspace["rate_book"]

    status, workspace = request("POST", f"{API}/rate-books/{rate_book['id']}/publish")
    workspace = require(status, {200}, workspace, f"publish {spec['rate_book_code']}")
    return workspace["rate_book"]


def template_payload(rate_books: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "template_code": TEMPLATE_CODE,
        "template_name": "Road customer pricing study",
        "description": (
            f"{STUDY_MARKER} Linehaul, subtotal-derived fuel, distance and conditional "
            "accessorials, plus a non-commercial benchmark."
        ),
        "status": "DRAFT",
        "is_active": True,
        "steps": [
            {
                "step_number": 10,
                "charge_component_code": "ROAD_FREIGHT_FTL",
                "relationship_role": "PAYEE",
                "subtotal_key": "BASE_TRANSPORT",
                "accumulate_result_in_subtotal": True,
                "rate_book_id": rate_books["TC-DEMO-ROAD-EUR"]["id"],
            },
            {
                "step_number": 20,
                "charge_component_code": "ROAD_FUEL_SURCHARGE",
                "relationship_role": "PAYEE",
                "subtotal_key": "BASE_TRANSPORT",
                "accumulate_result_in_subtotal": False,
                "rate_book_id": rate_books["TC-DEMO-ROAD-FUEL-PCT"]["id"],
            },
            {
                "step_number": 30,
                "charge_component_code": "ROAD_TOLL",
                "relationship_role": "PAYEE",
                "rate_book_id": rate_books["TC-DEMO-ROAD-TOLL-EUR"]["id"],
            },
            {
                "step_number": 40,
                "charge_component_code": "TAIL_LIFT_SERVICE",
                "relationship_role": "PAYEE",
                "precondition_key": "requires_tail_lift",
                "rate_book_id": rate_books["TC-DEMO-ROAD-TAIL-LIFT-EUR"]["id"],
            },
            {
                "step_number": 50,
                "charge_component_code": "WAITING_TIME",
                "relationship_role": "PAYEE",
                "precondition_key": "charge_waiting_time",
                "rate_book_id": rate_books["TC-DEMO-ROAD-WAITING-EUR"]["id"],
            },
            {
                "step_number": 90,
                "charge_component_code": "ROAD_INTERNAL_COST_REFERENCE",
                "relationship_role": "PAYEE",
                "accumulate_result_in_subtotal": False,
                "is_statistical": True,
                "rate_book_id": rate_books["TC-DEMO-ROAD-INTERNAL-COST"]["id"],
            },
        ],
    }


def ensure_template(payload: dict[str, Any]) -> dict[str, Any]:
    versions = list_exact("calculation-templates", "template_code", TEMPLATE_CODE)
    expected_steps = [
        (
            step["step_number"],
            step["charge_component_code"],
            step.get("relationship_role", "BOTH"),
            step.get("subtotal_key"),
            step.get("accumulate_result_in_subtotal", True),
            step.get("is_statistical", False),
            step.get("precondition_key"),
            step.get("rate_book_id"),
        )
        for step in payload["steps"]
    ]

    def has_expected_steps(template: dict[str, Any]) -> bool:
        actual_steps = [
            (
                step["step_number"],
                step["charge_component_code"],
                step.get("relationship_role", "BOTH"),
                step.get("subtotal_key"),
                step.get("accumulate_result_in_subtotal", True),
                step.get("is_statistical", False),
                step.get("precondition_key"),
                step.get("rate_book_id"),
            )
            for step in template.get("steps", [])
        ]
        return actual_steps == expected_steps

    published_study_versions = [
        row
        for row in versions
        if row.get("status") == "PUBLISHED"
        and STUDY_MARKER in (row.get("description") or "")
        and has_expected_steps(row)
    ]
    if published_study_versions:
        return max(published_study_versions, key=lambda row: (row["version_number"], row["id"]))

    latest = max(versions, key=lambda row: (row["version_number"], row["id"])) if versions else None
    if latest is None:
        status, template = request("POST", f"{API}/calculation-templates", payload)
        template = require(status, {201}, template, "create calculation template")
    elif latest.get("status") == "DRAFT":
        update = {**payload, "expected_lock_version": latest["lock_version"]}
        status, workspace = request(
            "PUT",
            f"{API}/calculation-templates/{latest['id']}/workspace",
            update,
        )
        workspace = require(status, {200}, workspace, "update calculation template")
        template = workspace["template"]
    else:
        status, workspace = request(
            "POST",
            f"{API}/calculation-templates/{latest['id']}/versions",
            payload,
        )
        workspace = require(status, {201}, workspace, "version calculation template")
        template = workspace["template"]

    status, workspace = request(
        "POST",
        f"{API}/calculation-templates/{template['id']}/publish",
    )
    workspace = require(status, {200}, workspace, "publish calculation template")
    return workspace["template"]


def contract_payload(number: str, template: dict[str, Any], priority: int) -> dict[str, Any]:
    return {
        "contract_number": number,
        "contract_name": "Guadalajara Retail road pricing study",
        "contract_role": "PAYEE",
        "description": f"{STUDY_MARKER} Released customer contract for the road study.",
        "payer_party_ref": f"party:customer:{CUSTOMER_ID}",
        "payee_party_ref": f"party:company:{COMPANY_ID}",
        "party_role_ref": "PAYEE",
        "company_id": COMPANY_ID,
        "customer_id": CUSTOMER_ID,
        "currency": "EUR",
        "valid_from": "2026-01-01",
        "valid_to": "2027-12-31",
        "selection_priority": priority,
        "default_calculation_template_id": template["id"],
        "external_reference": "TC-DEMO-CUSTOMER-GDL",
        "lines": [],
        "template_routes": [],
    }


def ensure_contract(template: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    query = urllib.parse.urlencode(
        {"contract_role": "PAYEE", "customer_id": CUSTOMER_ID, "limit": 200}
    )
    status, result = request("GET", f"{API}/contracts?{query}")
    require(status, {200}, result, "list customer contracts")
    contracts = result.get("items", [])
    primary = next(
        (row for row in contracts if row["contract_number"] == CONTRACT_NUMBER),
        None,
    )
    if primary is None:
        number = CONTRACT_NUMBER
        priority = 10
        existing = None
        replaced_immutable_contract = False
    elif (
        primary.get("status") == "RELEASED"
        and primary.get("default_calculation_template_id") == template["id"]
    ):
        return primary, False
    elif primary.get("status") == "DRAFT":
        number = CONTRACT_NUMBER
        priority = 10
        existing = primary
        replaced_immutable_contract = False
    else:
        number = f"{CONTRACT_NUMBER}-V{template['version_number']}"
        existing = next(
            (row for row in contracts if row["contract_number"] == number),
            None,
        )
        if existing is not None and existing.get("status") == "RELEASED":
            if existing.get("default_calculation_template_id") == template["id"]:
                return existing, True
            number = f"{number}-T{template['id']}"
            existing = next(
                (row for row in contracts if row["contract_number"] == number),
                None,
            )
        priority = 10 - int(template["version_number"])
        replaced_immutable_contract = True

    payload = contract_payload(number, template, priority)
    if existing is None:
        status, contract = request("POST", f"{API}/contracts", payload)
        contract = require(status, {201}, contract, f"create contract {number}")
    elif existing.get("status") == "DRAFT":
        status, workspace = request(
            "PUT",
            f"{API}/contracts/{existing['id']}/workspace",
            payload,
        )
        workspace = require(status, {200}, workspace, f"update contract {number}")
        contract = workspace["contract"]
    else:
        raise RuntimeError(f"Released study contract {number} references an unexpected template")

    status, contract = request("POST", f"{API}/contracts/{contract['id']}/release")
    contract = require(status, {200}, contract, f"release contract {number}")
    return contract, replaced_immutable_contract


def main() -> None:
    wait_until_ready()
    component = ensure_statistical_component()
    rate_books = {
        spec["rate_book_code"]: ensure_rate_book(spec)
        for spec in rate_book_specs()
    }
    template = ensure_template(template_payload(rate_books))
    contract, replaced_contract = ensure_contract(template)
    print(
        json.dumps(
            {
                "study_revision": STUDY_MARKER,
                "statistical_component": {
                    "id": component["id"],
                    "code": component["component_code"],
                },
                "rate_books": [
                    {
                        "id": book["id"],
                        "code": book["rate_book_code"],
                        "version": book["version_number"],
                        "status": book["status"],
                        "rows": len(book.get("entries", [])),
                    }
                    for book in rate_books.values()
                ],
                "calculation_template": {
                    "id": template["id"],
                    "code": template["template_code"],
                    "version": template["version_number"],
                    "status": template["status"],
                    "steps": len(template.get("steps", [])),
                },
                "contract": {
                    "id": contract["id"],
                    "number": contract["contract_number"],
                    "status": contract["status"],
                    "replaces_immutable_demo_contract": replaced_contract,
                },
                "company_id": COMPANY_ID,
                "customer_id": CUSTOMER_ID,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
