from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Base, ChargeFxRateRow, ChargeFxRateSourceRow
from app.db.session import engine
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.execute(delete(ChargeFxRateRow))
        db.execute(delete(ChargeFxRateSourceRow))
        db.commit()


def test_fx_source_and_rate_maintenance_persists_between_requests() -> None:
    source_response = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={
            "source_code": "ECB",
            "source_name": "European Central Bank",
            "provider_url": "https://example.test/rates",
            "timezone": "Europe/Brussels",
            "priority": 10,
        },
    )
    assert source_response.status_code == 201, source_response.text
    source = source_response.json()

    listed_sources = client.get(
        "/api/v1/charge-management/fx-rate-sources?q=ecb&active_only=true",
        headers=AUTH,
    )
    assert listed_sources.status_code == 200, listed_sources.text
    assert listed_sources.json()["total"] == 1
    assert listed_sources.json()["items"][0]["id"] == source["id"]

    rate_response = client.post(
        "/api/v1/charge-management/fx-rates",
        headers=AUTH,
        json={
            "source_id": source["id"],
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-07-20",
            "rate": "1.1500000000",
            "rate_type": "MID",
            "conversion_method": "DIRECT",
        },
    )
    assert rate_response.status_code == 201, rate_response.text
    rate = rate_response.json()

    reopened = client.get(
        f"/api/v1/charge-management/fx-rates/{rate['id']}",
        headers=AUTH,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["source_code"] == "ECB"
    assert reopened.json()["rate"] == "1.1500000000"


def test_fx_resolution_supports_prior_date_and_inverse_pair() -> None:
    source = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={"source_code": "MANUAL", "source_name": "Manual", "priority": 100},
    ).json()
    created = client.post(
        "/api/v1/charge-management/fx-rates",
        headers=AUTH,
        json={
            "source_id": source["id"],
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-07-20",
            "rate": "1.15",
            "rate_type": "MID",
            "conversion_method": "DIRECT",
        },
    )
    assert created.status_code == 201, created.text

    direct = client.post(
        "/api/v1/charge-management/fx-rates/resolve",
        headers=AUTH,
        json={
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-07-21",
            "amount": "100",
            "source_code": "MANUAL",
        },
    )
    assert direct.status_code == 200, direct.text
    assert direct.json()["selected_rate_date"] == "2026-07-20"
    assert direct.json()["converted_amount"] == "115.0000000000"
    assert direct.json()["inverse_applied"] is False

    inverse = client.post(
        "/api/v1/charge-management/fx-rates/resolve",
        headers=AUTH,
        json={
            "source_currency": "USD",
            "target_currency": "EUR",
            "rate_date": "2026-07-21",
            "amount": "115",
            "source_code": "MANUAL",
        },
    )
    assert inverse.status_code == 200, inverse.text
    assert Decimal(inverse.json()["converted_amount"]) == Decimal("100")
    assert inverse.json()["inverse_applied"] is True


def test_fx_resolution_uses_direct_method_unless_requested_otherwise() -> None:
    source = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={"source_code": "MULTI_METHOD", "source_name": "Multiple Methods"},
    ).json()
    for method, rate in (("DIRECT", "1.10"), ("TREASURY", "1.25")):
        response = client.post(
            "/api/v1/charge-management/fx-rates",
            headers=AUTH,
            json={
                "source_id": source["id"],
                "source_currency": "EUR",
                "target_currency": "USD",
                "rate_date": "2026-07-21",
                "rate": rate,
                "conversion_method": method,
            },
        )
        assert response.status_code == 201, response.text

    default_resolution = client.post(
        "/api/v1/charge-management/fx-rates/resolve",
        headers=AUTH,
        json={
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-07-21",
            "source_code": "MULTI_METHOD",
        },
    )
    treasury_resolution = client.post(
        "/api/v1/charge-management/fx-rates/resolve",
        headers=AUTH,
        json={
            "source_currency": "EUR",
            "target_currency": "USD",
            "rate_date": "2026-07-21",
            "source_code": "MULTI_METHOD",
            "conversion_method": "TREASURY",
        },
    )

    assert default_resolution.status_code == 200, default_resolution.text
    assert default_resolution.json()["effective_rate"] == "1.1000000000"
    assert treasury_resolution.status_code == 200, treasury_resolution.text
    assert treasury_resolution.json()["effective_rate"] == "1.2500000000"


def test_fx_rate_uniqueness_and_soft_deactivation() -> None:
    source = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={"source_code": "BANK", "source_name": "Bank Feed"},
    ).json()
    payload = {
        "source_id": source["id"],
        "source_currency": "GBP",
        "target_currency": "EUR",
        "rate_date": "2026-07-21",
        "rate": "1.18",
        "rate_type": "SELL",
        "conversion_method": "PUBLISHED",
    }
    created = client.post("/api/v1/charge-management/fx-rates", headers=AUTH, json=payload)
    assert created.status_code == 201, created.text

    duplicate = client.post("/api/v1/charge-management/fx-rates", headers=AUTH, json=payload)
    assert duplicate.status_code == 409

    deactivated = client.delete(
        f"/api/v1/charge-management/fx-rates/{created.json()['id']}",
        headers=AUTH,
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    missing = client.post(
        "/api/v1/charge-management/fx-rates/resolve",
        headers=AUTH,
        json={
            "source_currency": "GBP",
            "target_currency": "EUR",
            "rate_date": "2026-07-21",
            "rate_type": "SELL",
            "conversion_method": "PUBLISHED",
        },
    )
    assert missing.status_code == 404


def test_active_rate_list_excludes_rates_from_inactive_sources() -> None:
    source = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={"source_code": "OLD_FEED", "source_name": "Old Feed"},
    ).json()
    rate = client.post(
        "/api/v1/charge-management/fx-rates",
        headers=AUTH,
        json={
            "source_id": source["id"],
            "source_currency": "USD",
            "target_currency": "EUR",
            "rate_date": "2026-07-21",
            "rate": "0.92",
        },
    )
    assert rate.status_code == 201, rate.text

    deactivated = client.delete(
        f"/api/v1/charge-management/fx-rate-sources/{source['id']}",
        headers=AUTH,
    )
    assert deactivated.status_code == 200, deactivated.text

    listed = client.get(
        "/api/v1/charge-management/fx-rates?active_only=true",
        headers=AUTH,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 0
