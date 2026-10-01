from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db.models import Base
from app.domain.models import ChargeCalculationProfile, ChargeComponentAliasPayload, ChargeComponentPayload
from app.domain.service import ChargeManagementService, InMemoryChargeRepository
from app.infrastructure.sqlalchemy_repository import SqlAlchemyChargeRepository
from app.main import create_app


def _payload(owner_id: int | None, *, code: str = "REEFER") -> ChargeComponentPayload:
    return ChargeComponentPayload(
        component_code=code, component_name=code,
        **({"owner_type": "FORWARDER", "owner_id": owner_id} if owner_id is not None else {}),
    )


def test_component_code_uniqueness_and_global_code_lookup_are_owner_safe():
    service = ChargeManagementService(InMemoryChargeRepository())
    global_row = service.create_component(_payload(None))
    own = service.create_component(_payload(101))
    other = service.create_component(_payload(202))
    assert {row.id for row in (global_row, own, other)} == {global_row.id, own.id, other.id}
    assert service.repository.components_by_code["REEFER"].id == global_row.id
    assert service.get_component(own.id).owner_id == 101
    with pytest.raises(HTTPException) as error:
        service.create_component(_payload(101))
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        service.update_component(own.id, ChargeComponentPayload(
            component_code="REEFER", component_name="Reefer", owner_type="FORWARDER", owner_id=202,
        ))
    assert error.value.status_code == 422
    assert service.update_component(own.id, _payload(None)).owner_id == 101


def test_component_rejects_cross_owner_calculation_profile():
    service = ChargeManagementService(InMemoryChargeRepository())
    foreign = ChargeCalculationProfile(
        id=service.repository.next_id("calculation_profile"),
        profile_code="FOREIGN", profile_name="Foreign", owner_type="FORWARDER", owner_id=202,
    )
    service.repository.calculation_profiles[foreign.id] = foreign
    with pytest.raises(HTTPException) as error:
        service.create_component(ChargeComponentPayload(
            component_code="WRONG", component_name="Wrong", owner_type="FORWARDER", owner_id=101,
            default_calculation_profile_id=foreign.id,
        ))
    assert error.value.status_code == 422


def test_scoped_component_alias_requires_matching_business_forwarder():
    service = ChargeManagementService(InMemoryChargeRepository())
    component = service.create_component(_payload(101))
    with pytest.raises(HTTPException) as error:
        service.create_component_alias(ChargeComponentAliasPayload(
            raw_label="Foreign reefer", charge_component_id=component.id,
            forwarder_id=202,
        ))
    assert error.value.status_code == 422
    alias = service.create_component_alias(ChargeComponentAliasPayload(
        raw_label="Owned reefer", charge_component_id=component.id,
        forwarder_id=101,
    ))
    assert alias.charge_component_id == component.id


def test_component_owner_survives_sqlalchemy_reload():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            service = ChargeManagementService(SqlAlchemyChargeRepository(db))
            global_row = service.create_component(_payload(None))
            own = service.create_component(_payload(101))
            other = service.create_component(_payload(202))
            ids = {global_row.id, own.id, other.id}
            service.repository.flush()
            db.commit()
        with Session(engine) as db:
            reloaded = ChargeManagementService(SqlAlchemyChargeRepository(db))
            rows = [row for row in reloaded.list_components(limit=500, offset=0).items if row.id in ids]
            assert {(row.owner_type, row.owner_id, row.component_code) for row in rows} == {
                ("GLOBAL", 0, "REEFER"), ("FORWARDER", 101, "REEFER"),
                ("FORWARDER", 202, "REEFER"),
            }
            assert reloaded.repository.components_by_code["REEFER"].id == global_row.id
    finally:
        engine.dispose()


def test_component_detail_contract_is_registered():
    path = create_app().openapi()["paths"]["/api/v1/charge-management/components/{component_id}"]
    assert "get" in path
    assert "put" in path and "delete" in path


def test_component_owner_migration_preserves_global_rows_and_allows_scoped_code():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0037_component_ownership.py"
    spec = importlib.util.spec_from_file_location("component_owner_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE charge_component (id INTEGER PRIMARY KEY, component_code VARCHAR(60) NOT NULL, "
                "CONSTRAINT uq_charge_component_code UNIQUE (component_code))"
            )
            connection.exec_driver_sql("INSERT INTO charge_component (id, component_code) VALUES (1, 'BASE_FREIGHT')")
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            assert connection.execute(text(
                "SELECT owner_type, owner_id FROM charge_component WHERE id = 1"
            )).one() == ("GLOBAL", 0)
            connection.exec_driver_sql(
                "INSERT INTO charge_component (id, component_code, owner_type, owner_id) "
                "VALUES (2, 'BASE_FREIGHT', 'FORWARDER', 101)"
            )
            with pytest.raises(RuntimeError, match="codes repeat"):
                migration.downgrade()
            connection.exec_driver_sql("DELETE FROM charge_component WHERE id = 2")
            migration.downgrade()
            assert connection.execute(text(
                "SELECT id, component_code FROM charge_component WHERE id = 1"
            )).one() == (1, "BASE_FREIGHT")
    finally:
        engine.dispose()
