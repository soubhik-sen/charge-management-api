from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from app.infrastructure.sqlalchemy_repository import DatabaseRepositoryControl


def test_fresh_sqlite_database_migrates_to_calculation_profile_head(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "charge_management.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _connection_record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "charge_id_sequence" in tables
    assert "charge_fx_rate_source" in tables
    assert "charge_fx_rate" in tables
    assert "charge_allocation_profile" in tables
    assert "charge_calculation_profile" in tables
    assert "charge_calculation_profile_version" in tables
    assert "charge_calculation_profile_factor" in tables
    assert "charge_business_date_profile" in tables
    line_column_metadata = {
        column["name"]: column for column in inspector.get_columns("charge_line")
    }
    line_columns = set(line_column_metadata)
    assert {
        "fx_rate_id",
        "exchange_rate_source_code",
        "exchange_rate_type",
        "exchange_rate_method",
        "rate_amount",
        "calculation_profile_version_id",
        "calculation_config_snapshot_json",
        "calculation_input_snapshot_json",
        "status",
        "source",
        "target_scope_mode",
        "selected_target_references_json",
    } <= line_columns
    assert line_column_metadata["status"]["nullable"] is False
    assert line_column_metadata["source"]["nullable"] is False
    quote_line_columns = {column["name"] for column in inspector.get_columns("charge_quote_option_line")}
    assert {
        "rate_amount",
        "quantity",
        "quantity_uom",
        "calculation_profile_version_id",
        "calculation_config_snapshot_json",
        "calculation_input_snapshot_json",
    } <= quote_line_columns
    component_columns = {column["name"] for column in inspector.get_columns("charge_component")}
    assert "default_calculation_profile_id" in component_columns
    contract_line_columns = {column["name"] for column in inspector.get_columns("charge_contract_line")}
    assert "calculation_profile_id" in contract_line_columns
    rate_entry_columns = {column["name"] for column in inspector.get_columns("charge_rate_book_entry")}
    assert "calculation_profile_id" in rate_entry_columns
    with engine.connect() as connection:
        version = connection.execute(text("select version_num from alembic_version")).scalar_one()
        source_code = connection.execute(
            text("select source_code from charge_fx_rate_source where source_code = 'MANUAL'")
        ).scalar_one()
        flat_count = connection.execute(
            text("select count(*) from charge_calculation_profile where profile_code = 'FLAT_AMOUNT'")
        ).scalar_one()
    assert version == "0015_charge_line_target_scope_subset"
    assert source_code == "MANUAL"
    assert flat_count == 1

    # Exercise cyclic profile/version references with immediate FK checks, which
    # is closer to PostgreSQL behavior than SQLite's default configuration.
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    control = DatabaseRepositoryControl(factory)
    control.reset()
    control.reset()
    engine.dispose()


def test_fx_migration_round_trip(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "charge_management_round_trip.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    command.downgrade(config, "0011_add_business_date_profiles")
    engine = create_engine(database_url)
    assert "charge_fx_rate" not in inspect(engine).get_table_names()
    assert "charge_calculation_profile" not in inspect(engine).get_table_names()
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert "charge_fx_rate" in inspect(engine).get_table_names()
    assert "charge_calculation_profile" in inspect(engine).get_table_names()
    engine.dispose()
