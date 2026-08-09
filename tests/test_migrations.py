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
    allocation_version_columns = {
        column["name"]
        for column in inspector.get_columns("charge_allocation_profile_version")
    }
    assert {
        "effective_from",
        "effective_to",
        "missing_driver_policy",
        "lock_version",
    } <= allocation_version_columns
    assert "charge_calculation_profile" in tables
    assert "charge_calculation_profile_version" in tables
    assert "charge_calculation_profile_factor" in tables
    assert "charge_business_date_profile" in tables
    business_date_version_columns = {
        column["name"]
        for column in inspector.get_columns("charge_business_date_profile_version")
    }
    assert {"effective_from", "effective_to", "lock_version"} <= business_date_version_columns
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
        "calculation_mode",
        "calculation_status",
        "allocation_mode",
        "allocation_status",
        "allocation_config_snapshot_json",
        "is_customer_visible",
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
        "calculation_mode",
        "calculation_status",
        "allocation_mode",
        "allocation_status",
        "allocation_config_snapshot_json",
        "is_customer_visible",
        "source_currency",
        "source_amount",
        "exchange_rate",
        "exchange_rate_date",
        "fx_rate_id",
        "exchange_rate_source_code",
        "exchange_rate_type",
        "exchange_rate_method",
        "source_rate_book_entry_id",
        "is_statistical",
    } <= quote_line_columns
    component_columns = {column["name"] for column in inspector.get_columns("charge_component")}
    assert "default_calculation_profile_id" in component_columns
    contract_line_columns = {column["name"] for column in inspector.get_columns("charge_contract_line")}
    assert {"calculation_profile_id", "line_number", "priority", "is_active", "charge_context"} <= contract_line_columns
    rate_entry_columns = {column["name"] for column in inspector.get_columns("charge_rate_book_entry")}
    assert {"calculation_profile_id", "rate_percent", "priority", "is_active"} <= rate_entry_columns
    rate_book_columns = {column["name"] for column in inspector.get_columns("charge_rate_book")}
    assert {
        "description",
        "valid_from",
        "valid_to",
        "calculation_basis",
        "status",
        "version_number",
        "supersedes_rate_book_id",
        "lock_version",
        "published_at",
    } <= rate_book_columns
    quote_request_columns = {column["name"] for column in inspector.get_columns("charge_quote_request")}
    assert {"request_number", "chargeable_weight", "charge_context"} <= quote_request_columns
    with engine.connect() as connection:
        version = connection.execute(text("select version_num from alembic_version")).scalar_one()
        source_code = connection.execute(
            text("select source_code from charge_fx_rate_source where source_code = 'MANUAL'")
        ).scalar_one()
        flat_count = connection.execute(
            text("select count(*) from charge_calculation_profile where profile_code = 'FLAT_AMOUNT'")
        ).scalar_one()
    assert version == "0021_version_rate_books"
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


def test_rate_book_migration_promotes_legacy_active_rows(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "charge_management_rate_book_upgrade.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "0020_business_date_lock_version")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO charge_rate_book "
                "(id, rate_book_code, rate_book_name, currency, calculation_basis, "
                "status, is_active, created_at, updated_at) "
                "VALUES (9001, 'LEGACY_ACTIVE', 'Legacy active rates', 'USD', "
                "'FLAT', 'ACTIVE', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                "SELECT status, version_number, published_at "
                "FROM charge_rate_book WHERE id = 9001"
            )
        ).one()
    assert migrated.status == "PUBLISHED"
    assert migrated.version_number == 1
    assert migrated.published_at is not None
    engine.dispose()

    command.downgrade(config, "0020_business_date_lock_version")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        downgraded_status = connection.execute(
            text("SELECT status FROM charge_rate_book WHERE id = 9001")
        ).scalar_one()
    assert downgraded_status == "ACTIVE"
    assert "version_number" not in {
        column["name"] for column in inspect(engine).get_columns("charge_rate_book")
    }
    engine.dispose()
