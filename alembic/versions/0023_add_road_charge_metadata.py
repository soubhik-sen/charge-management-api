"""Add reusable road and land charge metadata.

Revision ID: 0023_road_charge_metadata
Revises: 0022_rate_entry_defaults
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0023_road_charge_metadata"
down_revision = "0022_rate_entry_defaults"
branch_labels = None
depends_on = None


CALCULATION_PROFILES = (
    ("PER_KILOMETER", "Rate per kilometer", "KM", "DISTANCE_KM", "Distance", "MANUAL", "KM"),
    ("PER_STOP", "Rate per stop", "STOP", "STOP_COUNT", "Stops", "MANUAL", "STOP"),
    ("PER_PALLET", "Rate per pallet", "PALLET", "PALLET_COUNT", "Pallets", "MANUAL", "PALLET"),
    ("PER_LOADING_METER", "Rate per loading meter", "LDM", "LOADING_METERS", "Loading meters", "MANUAL", "LDM"),
    ("PER_HOUR", "Rate per hour", "HOUR", "DURATION_HOURS", "Duration hours", "DURATION_HOURS", "HOUR"),
)

ALLOCATION_PROFILES = (
    ("ROAD_WEIGHT_TO_ITEM", "Road charge by weight", "WEIGHT", "WEIGHT", "KG"),
    ("ROAD_VOLUME_TO_ITEM", "Road charge by volume", "CBM", "CBM", "CBM"),
    ("ROAD_EQUAL_TO_ITEM", "Road charge equally by item", "COUNT", "COUNT", "EA"),
)

ROAD_COMPONENTS = (
    ("ROAD_FREIGHT_FTL", "Road Freight - Full Truckload", "FREIGHT", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("ROAD_FREIGHT_LTL", "Road Freight - Less Than Truckload", "FREIGHT", "WEIGHT", "WEIGHT", "ROAD_WEIGHT_TO_ITEM"),
    ("ROAD_FUEL_SURCHARGE", "Road Fuel Surcharge", "SURCHARGE", "PERCENTAGE", None, "ROAD_WEIGHT_TO_ITEM"),
    ("ROAD_TOLL", "Road Toll", "ACCESSORIAL", "DISTANCE", None, "ROAD_WEIGHT_TO_ITEM"),
    ("ROAD_CONGESTION_SURCHARGE", "Road Congestion Surcharge", "SURCHARGE", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("LOW_EMISSION_ZONE_SURCHARGE", "Low Emission Zone Surcharge", "SURCHARGE", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("WAITING_TIME", "Waiting Time", "TIME_BASED", "PER_HOUR", None, None),
    ("LOADING_SERVICE", "Loading Service", "HANDLING", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("UNLOADING_SERVICE", "Unloading Service", "HANDLING", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("TAIL_LIFT_SERVICE", "Tail Lift Service", "ACCESSORIAL", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("ADR_DANGEROUS_GOODS", "ADR Dangerous Goods Surcharge", "COMPLIANCE", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("TEMPERATURE_CONTROL", "Temperature Controlled Transport", "ACCESSORIAL", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("PALLET_EXCHANGE", "Pallet Exchange", "EQUIPMENT", "PER_PALLET", None, None),
    ("MULTI_STOP_SURCHARGE", "Multi-stop Surcharge", "ACCESSORIAL", "PER_STOP", None, None),
    ("REDELIVERY", "Redelivery", "ACCESSORIAL", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("FAILED_COLLECTION", "Failed Collection", "ACCESSORIAL", "FLAT", "FLAT_AMOUNT", None),
    ("DELIVERY_APPOINTMENT", "Delivery Appointment", "ACCESSORIAL", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("REMOTE_AREA_SURCHARGE", "Remote Area Surcharge", "SURCHARGE", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("OVERWEIGHT_SURCHARGE", "Overweight Surcharge", "SURCHARGE", "WEIGHT", "WEIGHT", "ROAD_WEIGHT_TO_ITEM"),
    ("OVERSIZE_SURCHARGE", "Oversize Surcharge", "SURCHARGE", "FLAT", "FLAT_AMOUNT", "ROAD_VOLUME_TO_ITEM"),
    ("SPECIAL_TRANSPORT_PERMIT", "Special Transport Permit", "COMPLIANCE", "FLAT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
    ("CMR_DOCUMENTATION", "CMR Documentation", "DOCUMENTATION", "DOCUMENT", "FLAT_AMOUNT", "ROAD_WEIGHT_TO_ITEM"),
)


def _next_id(bind: sa.engine.Connection, table: str) -> int:
    return int(bind.execute(sa.text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}")).scalar_one())


def _id_for(bind: sa.engine.Connection, table: str, key_column: str, key: str) -> int | None:
    value = bind.execute(
        sa.text(f"SELECT id FROM {table} WHERE {key_column} = :key"),
        {"key": key},
    ).scalar_one_or_none()
    return int(value) if value is not None else None


def _replace_check(table: str, name: str, expression: str) -> None:
    if not inspect(op.get_bind()).has_table(table):
        return
    checks = {item.get("name") for item in inspect(op.get_bind()).get_check_constraints(table)}
    with op.batch_alter_table(table) as batch_op:
        if name in checks:
            batch_op.drop_constraint(name, type_="check")
        batch_op.create_check_constraint(name, expression)


def _seed_calculation_profiles(bind: sa.engine.Connection) -> None:
    for code, name, rate_uom, factor_code, factor_label, resolver, factor_uom in CALCULATION_PROFILES:
        profile_id = _id_for(bind, "charge_calculation_profile", "profile_code", code)
        if profile_id is None:
            profile_id = _next_id(bind, "charge_calculation_profile")
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_calculation_profile
                        (id, profile_code, profile_name, description, is_active,
                         published_version_id, created_at, updated_at)
                    VALUES (:id, :code, :name,
                            'Reusable road and land calculation behavior.', true,
                            NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": profile_id, "code": code, "name": name},
            )
        version_id = bind.execute(
            sa.text(
                "SELECT id FROM charge_calculation_profile_version "
                "WHERE profile_id = :profile_id AND version_number = 1"
            ),
            {"profile_id": profile_id},
        ).scalar_one_or_none()
        if version_id is None:
            version_id = _next_id(bind, "charge_calculation_profile_version")
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_calculation_profile_version
                        (id, profile_id, version_number, status, application_level,
                         calculation_method, rate_uom, missing_factor_policy,
                         lock_version, published_at, published_by, created_at, updated_at)
                    VALUES (:id, :profile_id, 1, 'PUBLISHED', 'SHIPMENT',
                            'RATE_TIMES_PRODUCT', :rate_uom, 'BLOCK', 1,
                            CURRENT_TIMESTAMP, 'SYSTEM', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": version_id, "profile_id": profile_id, "rate_uom": rate_uom},
            )
        factor_exists = bind.execute(
            sa.text(
                "SELECT 1 FROM charge_calculation_profile_factor "
                "WHERE profile_version_id = :version_id AND factor_code = :factor_code"
            ),
            {"version_id": int(version_id), "factor_code": factor_code},
        ).scalar_one_or_none()
        if factor_exists is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_calculation_profile_factor
                        (id, profile_version_id, sequence, factor_code, factor_label,
                         resolver, uom, is_required, default_value, created_at, updated_at)
                    VALUES (:id, :version_id, 1, :factor_code, :factor_label,
                            :resolver, :factor_uom, true, NULL,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id": _next_id(bind, "charge_calculation_profile_factor"),
                    "version_id": int(version_id),
                    "factor_code": factor_code,
                    "factor_label": factor_label,
                    "resolver": resolver,
                    "factor_uom": factor_uom,
                },
            )
        bind.execute(
            sa.text(
                "UPDATE charge_calculation_profile SET published_version_id = :version_id "
                "WHERE id = :profile_id"
            ),
            {"version_id": int(version_id), "profile_id": profile_id},
        )


def _seed_allocation_profiles(bind: sa.engine.Connection) -> None:
    for code, name, first_driver, second_driver, default_uom in ALLOCATION_PROFILES:
        profile_id = _id_for(bind, "charge_allocation_profile", "profile_code", code)
        if profile_id is None:
            profile_id = _next_id(bind, "charge_allocation_profile")
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_allocation_profile
                        (id, profile_code, profile_name, published_version_id,
                         created_at, updated_at)
                    VALUES (:id, :code, :name, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": profile_id, "code": code, "name": name},
            )
        version_id = bind.execute(
            sa.text(
                "SELECT id FROM charge_allocation_profile_version "
                "WHERE profile_id = :profile_id AND version_number = 1"
            ),
            {"profile_id": profile_id},
        ).scalar_one_or_none()
        if version_id is None:
            version_id = _next_id(bind, "charge_allocation_profile_version")
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_allocation_profile_version
                        (id, profile_id, version_number, status, source_level,
                         source_to_house_driver, house_to_item_driver,
                         final_posting_level, default_quantity_uom,
                         missing_driver_policy, lock_version, settings_json, notes,
                         published_at, created_at, updated_at)
                    VALUES (:id, :profile_id, 1, 'PUBLISHED', 'SHIPMENT',
                            :first_driver, :second_driver, 'PO_SCHEDULE_LINE',
                            :default_uom, 'BLOCK', 1, NULL,
                            'Reusable road and land item-cost allocation behavior.',
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id": version_id,
                    "profile_id": profile_id,
                    "first_driver": first_driver,
                    "second_driver": second_driver,
                    "default_uom": default_uom,
                },
            )
        bind.execute(
            sa.text(
                "UPDATE charge_allocation_profile SET published_version_id = :version_id "
                "WHERE id = :profile_id"
            ),
            {"version_id": int(version_id), "profile_id": profile_id},
        )


def _seed_business_date_profile(bind: sa.engine.Connection) -> int:
    code = "ROAD_SHIPMENT_STANDARD"
    profile_id = _id_for(bind, "charge_business_date_profile", "profile_code", code)
    if profile_id is None:
        profile_id = _next_id(bind, "charge_business_date_profile")
        bind.execute(
            sa.text(
                """
                INSERT INTO charge_business_date_profile
                    (id, profile_code, profile_name, description,
                     published_version_id, created_at, updated_at)
                VALUES (:id, :code, 'Road Shipment Exchange Rate Policy',
                        'Actual pickup/departure, planned pickup/departure, then document date.',
                        NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": profile_id, "code": code},
        )
    version_id = bind.execute(
        sa.text(
            "SELECT id FROM charge_business_date_profile_version "
            "WHERE profile_id = :profile_id AND version_number = 1"
        ),
        {"profile_id": profile_id},
    ).scalar_one_or_none()
    if version_id is None:
        version_id = _next_id(bind, "charge_business_date_profile_version")
        bind.execute(
            sa.text(
                """
                INSERT INTO charge_business_date_profile_version
                    (id, profile_id, version_number, status, notes,
                     lock_version, published_at, created_at, updated_at)
                VALUES (:id, :profile_id, 1, 'PUBLISHED',
                        'Standard road shipment FX date fallback chain.', 1,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": version_id, "profile_id": profile_id},
        )
    steps = (
        (10, "SHIPMENT_ACTUAL_DEPARTURE_DATE", "Actual pickup or dispatch date."),
        (20, "SHIPMENT_PLANNED_DEPARTURE_DATE", "Planned pickup or dispatch date."),
        (30, "DOCUMENT_DATE", "Charge document date."),
    )
    for step_number, date_key, notes in steps:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM charge_business_date_profile_step "
                "WHERE version_id = :version_id AND step_number = :step_number"
            ),
            {"version_id": int(version_id), "step_number": step_number},
        ).scalar_one_or_none()
        if exists is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO charge_business_date_profile_step
                        (id, version_id, step_number, date_key, notes)
                    VALUES (:id, :version_id, :step_number, :date_key, :notes)
                    """
                ),
                {
                    "id": _next_id(bind, "charge_business_date_profile_step"),
                    "version_id": int(version_id),
                    "step_number": step_number,
                    "date_key": date_key,
                    "notes": notes,
                },
            )
    bind.execute(
        sa.text(
            "UPDATE charge_business_date_profile SET published_version_id = :version_id "
            "WHERE id = :profile_id"
        ),
        {"version_id": int(version_id), "profile_id": profile_id},
    )
    return profile_id


def _seed_components(bind: sa.engine.Connection, business_date_profile_id: int) -> None:
    for code, name, category, basis, calculation_code, allocation_code in ROAD_COMPONENTS:
        if _id_for(bind, "charge_component", "component_code", code) is not None:
            continue
        calculation_id = (
            _id_for(bind, "charge_calculation_profile", "profile_code", calculation_code)
            if calculation_code
            else None
        )
        allocation_id = (
            _id_for(bind, "charge_allocation_profile", "profile_code", allocation_code)
            if allocation_code
            else None
        )
        allocation_version_id = None
        if allocation_id is not None:
            value = bind.execute(
                sa.text("SELECT published_version_id FROM charge_allocation_profile WHERE id = :id"),
                {"id": allocation_id},
            ).scalar_one_or_none()
            allocation_version_id = int(value) if value is not None else None
        bind.execute(
            sa.text(
                """
                INSERT INTO charge_component
                    (id, component_code, component_name, category, default_party_role,
                     charge_context, calculation_basis, charge_date_basis,
                     business_date_policy_mode, business_date_profile_id,
                     allocation_profile_id, allocation_profile_version_id,
                     default_calculation_profile_id, is_tax, is_active)
                VALUES (:id, :code, :name, :category, 'BOTH', 'ROAD', :basis,
                        'DOCUMENT_DATE', 'PROFILE_OVERRIDE', :business_date_profile_id,
                        :allocation_profile_id, :allocation_profile_version_id,
                        :calculation_profile_id, false, true)
                """
            ),
            {
                "id": _next_id(bind, "charge_component"),
                "code": code,
                "name": name,
                "category": category,
                "basis": basis,
                "business_date_profile_id": business_date_profile_id,
                "allocation_profile_id": allocation_id,
                "allocation_profile_version_id": allocation_version_id,
                "calculation_profile_id": calculation_id,
            },
        )


def upgrade() -> None:
    _replace_check(
        "charge_business_date_profile_assignment",
        "ck_charge_business_date_profile_assignment_shipment_scope",
        "shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE', 'ROAD_SHIPMENT')",
    )
    _replace_check(
        "charge_document",
        "ck_charge_document_shipment_scope",
        "shipment_scope is null or shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE', 'ROAD_SHIPMENT')",
    )
    bind = op.get_bind()
    _seed_calculation_profiles(bind)
    _seed_allocation_profiles(bind)
    business_date_profile_id = _seed_business_date_profile(bind)
    _seed_components(bind, business_date_profile_id)


def downgrade() -> None:
    bind = op.get_bind()
    component_codes = ", ".join(f"'{row[0]}'" for row in ROAD_COMPONENTS)
    bind.execute(sa.text(f"DELETE FROM charge_component WHERE component_code IN ({component_codes})"))
    bind.execute(
        sa.text(
            "DELETE FROM charge_business_date_profile_assignment "
            "WHERE shipment_scope = 'ROAD_SHIPMENT'"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM charge_business_date_profile "
            "WHERE profile_code = 'ROAD_SHIPMENT_STANDARD'"
        )
    )
    allocation_codes = ", ".join(f"'{row[0]}'" for row in ALLOCATION_PROFILES)
    calculation_codes = ", ".join(f"'{row[0]}'" for row in CALCULATION_PROFILES)
    bind.execute(sa.text(f"DELETE FROM charge_allocation_profile WHERE profile_code IN ({allocation_codes})"))
    bind.execute(sa.text(f"DELETE FROM charge_calculation_profile WHERE profile_code IN ({calculation_codes})"))
    _replace_check(
        "charge_business_date_profile_assignment",
        "ck_charge_business_date_profile_assignment_shipment_scope",
        "shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
    )
    _replace_check(
        "charge_document",
        "ck_charge_document_shipment_scope",
        "shipment_scope is null or shipment_scope in ('OCEAN_HOUSE', 'AIR_HOUSE')",
    )
