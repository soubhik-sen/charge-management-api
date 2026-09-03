from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from app.infrastructure.sqlalchemy_repository import DatabaseRepositoryControl


ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = Path(__file__).resolve().parents[1] / "alembic"


def test_fresh_sqlite_database_migrates_to_calculation_profile_head(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "charge_management.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
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
    assert "charge_pricing_dimension" in tables
    assert "charge_caller_mapping_profile" in tables
    assert "charge_allocation_profile" in tables
    allocation_profile_columns = {column["name"] for column in inspector.get_columns("charge_allocation_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= allocation_profile_columns
    allocation_profile_columns = {column["name"] for column in inspector.get_columns("charge_allocation_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= allocation_profile_columns
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
    calculation_profile_columns = {column["name"] for column in inspector.get_columns("charge_calculation_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= calculation_profile_columns
    calculation_profile_columns = {column["name"] for column in inspector.get_columns("charge_calculation_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= calculation_profile_columns
    assert "charge_calculation_profile_version" in tables
    assert "charge_calculation_profile_factor" in tables
    assert "charge_business_date_profile" in tables
    business_date_profile_columns = {column["name"] for column in inspector.get_columns("charge_business_date_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= business_date_profile_columns
    business_date_profile_columns = {column["name"] for column in inspector.get_columns("charge_business_date_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= business_date_profile_columns
    business_date_version_columns = {
        column["name"]
        for column in inspector.get_columns("charge_business_date_profile_version")
    }
    assert {"effective_from", "effective_to", "lock_version"} <= business_date_version_columns
    assert "charge_free_time_profile" in tables
    free_time_profile_columns = {column["name"] for column in inspector.get_columns("charge_free_time_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= free_time_profile_columns
    assert "charge_free_time_profile_version" in tables
    free_time_version_columns = {column["name"] for column in inspector.get_columns("charge_free_time_profile_version")}
    assert {"effective_from", "effective_to", "lock_version", "status"} <= free_time_version_columns
    assert "charge_free_time_rule" in tables
    free_time_rule_columns = {column["name"] for column in inspector.get_columns("charge_free_time_rule")}
    assert {
        "version_id",
        "sequence",
        "rule_code",
        "rule_name",
        "scope_type",
        "start_timestamp_key",
        "end_timestamp_key",
        "free_time_days",
    } <= free_time_rule_columns
    assert "charge_free_time_profile" in tables
    free_time_profile_columns = {column["name"] for column in inspector.get_columns("charge_free_time_profile")}
    assert {"owner_type", "owner_id", "profile_code", "profile_name", "published_version_id"} <= free_time_profile_columns
    assert "charge_free_time_profile_version" in tables
    free_time_version_columns = {column["name"] for column in inspector.get_columns("charge_free_time_profile_version")}
    assert {"effective_from", "effective_to", "lock_version", "status"} <= free_time_version_columns
    assert "charge_free_time_rule" in tables
    free_time_rule_columns = {column["name"] for column in inspector.get_columns("charge_free_time_rule")}
    assert {
        "version_id",
        "sequence",
        "rule_code",
        "rule_name",
        "scope_type",
        "start_timestamp_key",
        "end_timestamp_key",
        "free_time_days",
    } <= free_time_rule_columns
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
        "source_contract_line_id",
        "source_contract_template_route_id",
        "source_rate_book_entry_id",
        "source_calculation_template_id",
        "source_calculation_template_step_id",
        "is_statistical",
    } <= quote_line_columns
    component_columns = {column["name"] for column in inspector.get_columns("charge_component")}
    assert "default_calculation_profile_id" in component_columns
    contract_line_columns = {column["name"] for column in inspector.get_columns("charge_contract_line")}
    assert {"calculation_profile_id", "line_number", "priority", "is_active", "charge_context"} <= contract_line_columns
    contract_columns = {column["name"] for column in inspector.get_columns("charge_rate_contract")}
    assert "selection_priority" in contract_columns
    assert "charge_contract_template_route" in tables
    template_route_columns = {
        column["name"] for column in inspector.get_columns("charge_contract_template_route")
    }
    assert {
        "contract_id",
        "calculation_template_id",
        "route_number",
        "priority",
        "origin_code",
        "destination_code",
        "mode",
    } <= template_route_columns
    rate_entry_columns = {column["name"] for column in inspector.get_columns("charge_rate_book_entry")}
    assert {
        "calculation_profile_id",
        "rate_percent",
        "priority",
        "is_active",
        "basis_override",
        "charge_context",
        "charge_context_override",
    } <= rate_entry_columns
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
        "charge_component_id",
        "row_attribute_keys_json",
        "dimension_codes_json",
    } <= rate_book_columns
    calculation_template_columns = {
        column["name"]
        for column in inspector.get_columns("charge_calculation_template")
    }
    assert {
        "version_number",
        "supersedes_calculation_template_id",
        "lock_version",
        "published_at",
    } <= calculation_template_columns
    calculation_template_step_columns = {
        column["name"]
        for column in inspector.get_columns("charge_calculation_template_step")
    }
    assert "accumulate_result_in_subtotal" in calculation_template_step_columns
    quote_request_columns = {column["name"] for column in inspector.get_columns("charge_quote_request")}
    assert {
        "request_number",
        "chargeable_weight",
        "charge_context",
        "calculation_inputs_json",
        "component_calculation_inputs_json",
        "date_values_json",
        "caller_system_code",
        "caller_schema_version",
        "caller_mapping_profile_code",
        "caller_attributes_json",
        "dimension_values_json",
    } <= quote_request_columns
    quote_commitment_columns = {
        column["name"] for column in inspector.get_columns("charge_quote_commitment")
    }
    assert {
        "execution_identity",
        "execution_source_system",
        "execution_plan_id",
        "execution_route_id",
        "execution_source_id",
        "execution_request_number",
    } <= quote_commitment_columns
    quote_commitment_indexes = {
        index["name"] for index in inspector.get_indexes("charge_quote_commitment")
    }
    assert {
        "uq_charge_quote_commitment_execution_identity",
        "ix_charge_quote_commitment_execution_route",
    } <= quote_commitment_indexes
    with engine.connect() as connection:
        version = connection.execute(text("select version_num from alembic_version")).scalar_one()
        source_code = connection.execute(
            text("select source_code from charge_fx_rate_source where source_code = 'MANUAL'")
        ).scalar_one()
        flat_count = connection.execute(
            text("select count(*) from charge_calculation_profile where profile_code = 'FLAT_AMOUNT'")
        ).scalar_one()
        road_component_count = connection.execute(
            text("select count(*) from charge_component where charge_context = 'ROAD'")
        ).scalar_one()
        road_calculation_count = connection.execute(
            text(
                "select count(*) from charge_calculation_profile "
                "where profile_code in ('PER_KILOMETER', 'PER_STOP', 'PER_PALLET', "
                "'PER_LOADING_METER', 'PER_HOUR')"
            )
        ).scalar_one()
        road_allocation_count = connection.execute(
            text("select count(*) from charge_allocation_profile where profile_code like 'ROAD_%'")
        ).scalar_one()
        road_date_count = connection.execute(
            text(
                "select count(*) from charge_business_date_profile "
                "where profile_code = 'ROAD_SHIPMENT_STANDARD'"
            )
        ).scalar_one()
        road_date_step_count = connection.execute(
            text(
                "select count(*) from charge_business_date_profile_step as step "
                "join charge_business_date_profile_version as version on version.id = step.version_id "
                "join charge_business_date_profile as profile on profile.id = version.profile_id "
                "where profile.profile_code = 'ROAD_SHIPMENT_STANDARD' "
                "and step.date_key in ('ROAD_ACTUAL_PICKUP_DATE', 'ROAD_PLANNED_PICKUP_DATE', "
                "'CMR_ISSUE_DATE', 'DOCUMENT_DATE')"
            )
        ).scalar_one()
        reusable_default_count = connection.execute(
            text(
                "select count(*) from charge_component as component "
                "join charge_calculation_profile as profile "
                "on profile.id = component.default_calculation_profile_id "
                "where (component.component_code in ('LINE_HAUL', 'ROAD_TOLL') "
                "and profile.profile_code = 'PER_KILOMETER') "
                "or (component.component_code in ('STORAGE', 'DEMURRAGE', 'DETENTION') "
                "and profile.profile_code = 'PER_DAY') "
                "or (component.component_code = 'WAITING_TIME' and profile.profile_code = 'PER_HOUR') "
                "or (component.component_code = 'PALLET_EXCHANGE' and profile.profile_code = 'PER_PALLET') "
                "or (component.component_code = 'MULTI_STOP_SURCHARGE' and profile.profile_code = 'PER_STOP')"
            )
        ).scalar_one()
        pricing_dimension_count = connection.execute(
            text("select count(*) from charge_pricing_dimension where is_system = true")
        ).scalar_one()
    assert version == "0032_owner_scoped_profiles_and_free_time_rules"
    assert source_code == "MANUAL"
    assert flat_count == 1
    assert road_component_count == 22
    assert road_calculation_count == 5
    assert road_allocation_count == 3
    assert road_date_count == 1
    assert road_date_step_count == 4
    assert reusable_default_count == 8
    assert pricing_dimension_count == 7

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
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))

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
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))

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
        connection.execute(
            text(
                "INSERT INTO charge_rate_book_entry "
                "(id, rate_book_id, charge_component_id, rate_amount, basis, "
                "currency, priority, is_active) "
                "SELECT 9002, 9001, id, 25, 'CONTAINER', 'USD', 100, 1 "
                "FROM charge_component WHERE component_code = 'BASE_FREIGHT'"
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
        migrated_entry = connection.execute(
            text(
                "SELECT basis, basis_override, charge_context, charge_context_override "
                "FROM charge_rate_book_entry WHERE id = 9002"
            )
        ).one()
    assert migrated.status == "PUBLISHED"
    assert migrated.version_number == 1
    assert migrated.published_at is not None
    assert migrated_entry.basis == "CONTAINER"
    assert migrated_entry.basis_override == "CONTAINER"
    assert migrated_entry.charge_context == "TRANSPORT"
    assert migrated_entry.charge_context_override is None
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
