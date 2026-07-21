from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.charge_management import repository
from app.db.session import SessionLocal
from app.domain.fx_service import FxRateService
from app.domain.service import ChargeManagementService
from app.infrastructure.sqlalchemy_repository import SqlAlchemyChargeRepository
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    repository.reset()


def test_master_data_survives_fresh_repository_and_service_instances() -> None:
    seeded_sources = client.get(
        "/api/v1/charge-management/fx-rate-sources?active_only=true",
        headers=AUTH,
    )
    assert seeded_sources.status_code == 200, seeded_sources.text
    assert seeded_sources.json()["items"][0]["source_code"] == "MANUAL"

    allocation = client.post(
        "/api/v1/charge-management/allocation-profiles",
        headers=AUTH,
        json={
            "profile_code": "RESTART_WEIGHT",
            "profile_name": "Restart Weight Allocation",
            "initial_version": {
                "source_level": "HOUSE",
                "house_to_item_driver": "WEIGHT",
                "final_posting_level": "PO_SCHEDULE_LINE",
                "default_quantity_uom": "KG",
            },
        },
    )
    assert allocation.status_code == 201, allocation.text

    date_profile = client.post(
        "/api/v1/charge-management/business-date-profiles",
        headers=AUTH,
        json={
            "profile_code": "RESTART_DATE",
            "profile_name": "Restart Date Basis",
            "initial_version": {
                "steps": [
                    {"step_number": 10, "date_key": "SHIPPED_ON_BOARD_DATE"},
                    {"step_number": 20, "date_key": "DOCUMENT_DATE"},
                ]
            },
        },
    )
    assert date_profile.status_code == 201, date_profile.text

    source = client.post(
        "/api/v1/charge-management/fx-rate-sources",
        headers=AUTH,
        json={"source_code": "RESTART_BANK", "source_name": "Restart Bank"},
    )
    assert source.status_code == 201, source.text
    rate = client.post(
        "/api/v1/charge-management/fx-rates",
        headers=AUTH,
        json={
            "source_id": source.json()["id"],
            "source_currency": "EUR",
            "target_currency": "GBP",
            "rate_date": "2026-07-21",
            "rate": "0.8600000000",
        },
    )
    assert rate.status_code == 201, rate.text

    # A write through the aggregate-domain adapter must not replace or erase FX
    # rows maintained by the dedicated relational FX service.
    allocation_update = client.put(
        f"/api/v1/charge-management/allocation-profiles/{allocation.json()['id']}",
        headers=AUTH,
        json={
            "profile_code": "RESTART_WEIGHT",
            "profile_name": "Restart Weight Allocation Updated",
        },
    )
    assert allocation_update.status_code == 200, allocation_update.text

    # A fresh session and fresh services simulate process reconstruction: no
    # in-memory state from the API calls is available to these instances.
    with SessionLocal() as db:
        domain_service = ChargeManagementService(SqlAlchemyChargeRepository(db))
        reloaded_allocation = domain_service.get_allocation_profile(allocation.json()["id"])
        reloaded_date_profile = domain_service.get_business_date_profile(date_profile.json()["id"])
        reloaded_rate = FxRateService(db).get_rate(rate.json()["id"])

    assert reloaded_allocation.profile_name == "Restart Weight Allocation Updated"
    assert reloaded_allocation.versions[0].house_to_item_driver == "WEIGHT"
    assert reloaded_date_profile.profile_code == "RESTART_DATE"
    assert [step.date_key for step in reloaded_date_profile.versions[0].steps] == [
        "SHIPPED_ON_BOARD_DATE",
        "DOCUMENT_DATE",
    ]
    assert reloaded_rate.source_code == "RESTART_BANK"
    assert str(reloaded_rate.rate) == "0.8600000000"
