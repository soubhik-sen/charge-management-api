from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, update
from sqlalchemy.orm import sessionmaker

from app.api.v1.charge_management import repository
from app.db.base import Base
from app.db.models import ChargeIdSequenceRow
from app.db.session import SessionLocal
from app.domain.fx_service import FxRateService
from app.domain.service import ChargeManagementService
from app.infrastructure.sqlalchemy_repository import SqlAlchemyChargeRepository
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}


def setup_function() -> None:
    repository.reset()


def test_automatic_document_numbers_survive_deletion_and_repository_reload() -> None:
    path = "/api/v1/charge-management/charge-documents"
    first = client.post(path, headers=AUTH, json={"currency": "USD"})
    second = client.post(path, headers=AUTH, json={"currency": "USD"})
    assert first.status_code == second.status_code == 201
    for response in [first, second]:
        deleted = client.delete(f"{path}/{response.json()['id']}", headers=AUTH)
        assert deleted.status_code == 200, deleted.text
    # Each API call constructs a fresh SQLAlchemy repository.
    third = client.post(path, headers=AUTH, json={"currency": "USD"})
    assert third.status_code == 201, third.text
    assert int(third.json()["document_number"].split("-")[-1]) > int(second.json()["document_number"].split("-")[-1])


def test_next_id_recovers_when_persisted_sequence_trails_seeded_rows() -> None:
    with SessionLocal() as db:
        db.execute(
            update(ChargeIdSequenceRow)
            .where(ChargeIdSequenceRow.bucket == "calculation_profile")
            .values(last_value=0)
        )
        db.commit()

    with SessionLocal() as db:
        fresh_repository = SqlAlchemyChargeRepository(db)
        existing_ids = set(fresh_repository.calculation_profiles)

        next_profile_id = fresh_repository.next_id("calculation_profile")

    assert next_profile_id == max(existing_ids) + 1
    assert next_profile_id not in existing_ids


def test_fresh_repository_populates_manual_fx_source_cache_immediately(tmp_path) -> None:
    database_path = tmp_path / "charge_management_fx_cache.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _connection_record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with factory() as db:
            fresh_repository = SqlAlchemyChargeRepository(db)

            assert 1 in fresh_repository._fx_sources
            assert fresh_repository._fx_sources[1].source_code == "MANUAL"
            assert fresh_repository._fx_sources[1].source_name == "Manual Rate Maintenance"

            fresh_repository.reset()

            assert 1 in fresh_repository._fx_sources
            assert fresh_repository._fx_sources[1].source_code == "MANUAL"
            assert fresh_repository._fx_sources[1].source_name == "Manual Rate Maintenance"
    finally:
        engine.dispose()


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

    calculation = client.post(
        "/api/v1/charge-management/calculation-profiles",
        headers=AUTH,
        json={
            "profile_code": "RESTART_PER_CONTAINER",
            "profile_name": "Restart Per Container",
            "initial_version": {
                "application_level": "CONTAINER",
                "calculation_method": "RATE_TIMES_PRODUCT",
                "rate_uom": "USD",
                "factors": [
                    {
                        "sequence": 10,
                        "factor_code": "CONTAINER_COUNT",
                        "factor_label": "Container count",
                        "resolver": "CONTAINER_COUNT",
                        "uom": "EA",
                    }
                ],
            },
        },
    )
    assert calculation.status_code == 201, calculation.text
    calculation_profile = calculation.json()
    calculation_version_id = calculation_profile["versions"][0]["id"]
    seeded_calculation_profiles = client.get(
        "/api/v1/charge-management/calculation-profiles",
        headers=AUTH,
    )
    assert seeded_calculation_profiles.status_code == 200, seeded_calculation_profiles.text
    seeded_profiles_by_code = {
        row["profile_code"]: row for row in seeded_calculation_profiles.json()["items"]
    }

    calculation_publish = client.post(
        f"/api/v1/charge-management/calculation-profile-versions/{calculation_version_id}/publish",
        headers=AUTH,
    )
    assert calculation_publish.status_code == 200, calculation_publish.text

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

    component = client.post(
        "/api/v1/charge-management/components",
        headers=AUTH,
        json={
            "component_code": "RESTART_COMPONENT",
            "component_name": "Restart Component",
            "category": "FREIGHT",
            "default_party_role": "PAYEE",
            "charge_context": "TRANSPORT",
            "calculation_basis": "PER_CONTAINER",
            "default_calculation_profile_id": calculation_profile["id"],
            "manual_entry_enabled": True,
        },
    )
    assert component.status_code == 201, component.text

    alias = client.post(
        "/api/v1/charge-management/component-aliases",
        headers=AUTH,
        json={
            "document_kind": "CHARGE_PROPOSAL",
            "source_section": "Ocean",
            "source_uom": "OCEAN_WM",
            "raw_label": "Restart Freight",
            "charge_component_id": component.json()["id"],
            "default_calculation_basis": "PER_CONTAINER",
            "default_charge_level": "CONTAINER",
            "default_allocation_basis": "CBM",
            "default_calculation_profile_id": calculation_profile["id"],
            "default_calculation_profile_version_id": calculation_version_id,
            "final_posting_level": "PO_SCHEDULE_LINE",
            "allocation_override_mode": "OVERRIDE_PROFILE",
            "override_calculation_profile_id": seeded_profiles_by_code["OCEAN_WM"]["id"],
            "override_calculation_profile_version_id": seeded_profiles_by_code["OCEAN_WM"][
                "versions"
            ][0]["id"],
            "customer_id": 20,
            "forwarder_id": 202,
            "transport_mode": "OCEAN",
        },
    )
    assert alias.status_code == 201, alias.text

    rate_book = client.post(
        "/api/v1/charge-management/rate-books",
        headers=AUTH,
        json={
            "rate_book_code": "RESTART_RATE_BOOK",
            "rate_book_name": "Restart Rate Book",
            "entries": [
                {
                    "charge_component_code": "RESTART_COMPONENT",
                    "basis_override": "WEIGHT",
                    "charge_context_override": "DESTINATION",
                    "rate_amount": "2.50",
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

    template = client.post(
        "/api/v1/charge-management/calculation-templates",
        headers=AUTH,
        json={
            "template_code": "RESTART_TEMPLATE",
            "template_name": "Restart Template",
            "status": "DRAFT",
            "steps": [
                {
                    "step_number": 10,
                    "charge_component_code": "RESTART_COMPONENT",
                    "relationship_role": "BOTH",
                    "subtotal_key": "RESTART_BASE",
                    "accumulate_result_in_subtotal": False,
                    "rate_book_id": rate_book_id,
                }
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
            "contract_number": "RESTART_CONTRACT",
            "contract_name": "Restart contract",
            "contract_role": "PAYEE",
            "customer_id": 20,
            "selection_priority": 15,
            "default_calculation_template_id": template.json()["id"],
            "template_routes": [
                {
                    "route_number": 10,
                    "calculation_template_id": template.json()["id"],
                    "mode": "ROAD",
                    "priority": 5,
                }
            ],
            "lines": [],
        },
    )
    assert contract.status_code == 201, contract.text

    # A fresh session and fresh services simulate process reconstruction: no
    # in-memory state from the API calls is available to these instances.
    with SessionLocal() as db:
        domain_service = ChargeManagementService(SqlAlchemyChargeRepository(db))
        reloaded_allocation = domain_service.get_allocation_profile(allocation.json()["id"])
        reloaded_calculation = domain_service.get_calculation_profile(calculation_profile["id"])
        reloaded_date_profile = domain_service.get_business_date_profile(date_profile.json()["id"])
        reloaded_component = next(
            item for item in domain_service.list_components(limit=200, offset=0).items if item.id == component.json()["id"]
        )
        reloaded_rate_book = domain_service.repository.rate_books[rate_book.json()["id"]]
        reloaded_template = domain_service.repository.calculation_templates[
            template.json()["id"]
        ]
        reloaded_contract = domain_service.repository.contracts[contract.json()["id"]]
        reloaded_rate = FxRateService(db).get_rate(rate.json()["id"])

    assert reloaded_allocation.profile_name == "Restart Weight Allocation Updated"
    assert reloaded_allocation.versions[0].house_to_item_driver == "WEIGHT"
    assert reloaded_calculation.profile_code == "RESTART_PER_CONTAINER"
    assert reloaded_calculation.published_version_id == calculation_version_id
    assert reloaded_calculation.versions[0].factors[0].resolver == "CONTAINER_COUNT"
    assert reloaded_date_profile.profile_code == "RESTART_DATE"
    assert [step.date_key for step in reloaded_date_profile.versions[0].steps] == [
        "SHIPPED_ON_BOARD_DATE",
        "DOCUMENT_DATE",
    ]
    assert reloaded_component.default_calculation_profile_id == calculation_profile["id"]
    assert reloaded_component.manual_entry_enabled is True
    reloaded_alias = next(
        item
        for item in domain_service.list_component_aliases(limit=200, offset=0).items
        if item.id == alias.json()["id"]
    )
    assert reloaded_alias.default_calculation_profile_id == calculation_profile["id"]
    assert reloaded_alias.default_calculation_profile_version_id == calculation_version_id
    assert (
        reloaded_alias.override_calculation_profile_id == seeded_profiles_by_code["OCEAN_WM"]["id"]
    )
    assert reloaded_alias.source_uom == "OCEAN_WM"
    assert (
        reloaded_alias.override_calculation_profile_version_id
        == seeded_profiles_by_code["OCEAN_WM"]["versions"][0]["id"]
    )
    assert reloaded_rate_book.charge_component_code == "RESTART_COMPONENT"
    assert reloaded_rate_book.row_attribute_keys == [
        "basis_override",
        "charge_context_override",
    ]
    assert reloaded_rate_book.status == "PUBLISHED"
    assert reloaded_rate_book.entries[0].basis == "WEIGHT"
    assert reloaded_rate_book.entries[0].basis_override == "WEIGHT"
    assert reloaded_rate_book.entries[0].charge_context == "DESTINATION"
    assert reloaded_rate_book.entries[0].charge_context_override == "DESTINATION"
    assert reloaded_template.status == "PUBLISHED"
    assert reloaded_template.version_number == 1
    assert reloaded_template.lock_version == 2
    assert reloaded_template.steps[0].rate_book_id == rate_book_id
    assert reloaded_template.steps[0].subtotal_key == "RESTART_BASE"
    assert reloaded_template.steps[0].accumulate_result_in_subtotal is False
    assert reloaded_contract.selection_priority == 15
    assert reloaded_contract.lines == []
    assert reloaded_contract.template_routes[0].route_number == 10
    assert reloaded_contract.template_routes[0].calculation_template_id == template.json()["id"]
    assert reloaded_contract.template_routes[0].mode == "ROAD"
    assert reloaded_rate.source_code == "RESTART_BANK"
    assert str(reloaded_rate.rate) == "0.8600000000"


def test_quote_request_inputs_and_date_values_reload_from_database() -> None:
    quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "request_number": "Q-PERSIST-001",
            "company_id": 10,
            "customer_id": 20,
            "mode": "ROAD",
            "currency": "USD",
            "calculation_inputs": {"DISTANCE_KM": "480", "STOP_COUNT": "3"},
            "component_calculation_inputs": {
                "road_toll": {"DISTANCE_KM": "500"},
                "WAITING_TIME": {"DURATION_HOURS": "2.5"},
            },
            "date_values": [
                {"date_type": "ROAD_ACTUAL_PICKUP_DATE", "date_value": "2026-07-21"},
                {"date_type": "DOCUMENT_DATE", "date_value": "2026-07-20"},
            ],
        },
    )
    assert quote.status_code == 201, quote.text

    with SessionLocal() as db:
        reloaded_repository = SqlAlchemyChargeRepository(db)
        reloaded_quote = reloaded_repository.quote_requests[quote.json()["id"]]

    assert reloaded_quote.calculation_inputs == {
        "DISTANCE_KM": "480",
        "STOP_COUNT": "3",
    }
    assert reloaded_quote.component_calculation_inputs == {
        "ROAD_TOLL": {"DISTANCE_KM": "500"},
        "WAITING_TIME": {"DURATION_HOURS": "2.5"},
    }
    assert [value.date_type for value in reloaded_quote.date_values] == [
        "ROAD_ACTUAL_PICKUP_DATE",
        "DOCUMENT_DATE",
    ]
    assert [str(value.date_value) for value in reloaded_quote.date_values] == [
        "2026-07-21",
        "2026-07-20",
    ]


def test_invoice_delete_is_removed_from_database() -> None:
    document = client.post(
        "/api/v1/charge-management/charge-documents",
        headers=AUTH,
        json={
            "source_object_type": "SHIPMENT",
            "source_object_id": "SHP-PERSIST-INVOICE-DELETE",
            "company_id": 10,
            "customer_id": 20,
            "currency": "USD",
        },
    )
    assert document.status_code == 201, document.text
    invoice = client.post(
        "/api/v1/charge-management/invoices",
        headers=AUTH,
        json={
            "charge_document_id": document.json()["id"],
            "invoice_number": "INV-PERSIST-DELETE",
            "invoice_type": "SUPPLIER",
            "currency": "USD",
            "lines": [],
        },
    )
    assert invoice.status_code == 201, invoice.text
    invoice_id = invoice.json()["id"]

    deleted = client.delete(
        f"/api/v1/charge-management/invoices/{invoice_id}",
        headers=AUTH,
    )
    assert deleted.status_code == 200, deleted.text

    with SessionLocal() as db:
        reloaded_repository = SqlAlchemyChargeRepository(db)
        assert invoice_id not in reloaded_repository.invoices


def test_quote_delete_removes_complete_aggregate_from_database() -> None:
    quote = client.post(
        "/api/v1/charge-management/quote-requests",
        headers=AUTH,
        json={
            "request_number": "Q-PERSIST-DELETE",
            "company_id": 10,
            "customer_id": 20,
            "mode": "ROAD",
            "currency": "USD",
        },
    )
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]
    submitted = client.put(
        f"/api/v1/charge-management/quote-requests/{quote_id}/workspace",
        headers=AUTH,
        json={"status": "REQUESTED"},
    )
    assert submitted.status_code == 200, submitted.text
    offer = client.post(
        f"/api/v1/charge-management/quote-requests/{quote_id}/offers",
        headers=AUTH,
        json={"offer_number": "OFF-PERSIST-DELETE", "amount": "500", "currency": "USD"},
    )
    assert offer.status_code == 201, offer.text
    offer_id = offer.json()["id"]

    deleted = client.delete(
        f"/api/v1/charge-management/quote-requests/{quote_id}",
        headers=AUTH,
    )
    assert deleted.status_code == 200, deleted.text

    with SessionLocal() as db:
        reloaded_repository = SqlAlchemyChargeRepository(db)
        assert quote_id not in reloaded_repository.quote_requests
        assert offer_id not in reloaded_repository.quote_offers
        assert all(
            option.quote_request_id != quote_id
            for option in reloaded_repository.quote_options.values()
        )
