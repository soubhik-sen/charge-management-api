from __future__ import annotations

COMMON_CHARGE_COMPONENTS: tuple[dict[str, str | bool], ...] = (
    {"component_code": "BASE_FREIGHT", "component_name": "Base Freight", "category": "FREIGHT", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "SHIPMENT"},
    {"component_code": "AIR_FREIGHT", "component_name": "Air Freight", "category": "FREIGHT", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "WEIGHT"},
    {"component_code": "LINE_HAUL", "component_name": "Line Haul", "category": "FREIGHT", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "DISTANCE"},
    {"component_code": "DRAYAGE", "component_name": "Drayage", "category": "FREIGHT", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "CONTAINER"},
    {"component_code": "PICKUP", "component_name": "Pickup", "category": "ORIGIN", "default_party_role": "BOTH", "charge_context": "ORIGIN", "calculation_basis": "SHIPMENT"},
    {"component_code": "ORIGIN_HANDLING", "component_name": "Origin Handling", "category": "HANDLING", "default_party_role": "BOTH", "charge_context": "ORIGIN", "calculation_basis": "CONTAINER"},
    {"component_code": "DESTINATION_HANDLING", "component_name": "Destination Handling", "category": "HANDLING", "default_party_role": "BOTH", "charge_context": "DESTINATION", "calculation_basis": "CONTAINER"},
    {"component_code": "EXPORT_CUSTOMS_CLEARANCE", "component_name": "Export Customs Clearance", "category": "CUSTOMS", "default_party_role": "BOTH", "charge_context": "ORIGIN", "calculation_basis": "SHIPMENT"},
    {"component_code": "IMPORT_CUSTOMS_CLEARANCE", "component_name": "Import Customs Clearance", "category": "CUSTOMS", "default_party_role": "BOTH", "charge_context": "DESTINATION", "calculation_basis": "SHIPMENT"},
    {"component_code": "CUSTOMS_EXAM", "component_name": "Customs Exam", "category": "CUSTOMS", "default_party_role": "BOTH", "charge_context": "CUSTOMS", "calculation_basis": "SHIPMENT"},
    {"component_code": "DUTY", "component_name": "Duty", "category": "TAX", "default_party_role": "PAYER", "charge_context": "CUSTOMS", "calculation_basis": "PERCENTAGE", "is_tax": True},
    {"component_code": "VAT_GST_TAX", "component_name": "VAT/GST Tax", "category": "TAX", "default_party_role": "PAYER", "charge_context": "TAX", "calculation_basis": "PERCENTAGE", "is_tax": True},
    {"component_code": "INSURANCE", "component_name": "Insurance", "category": "INSURANCE", "default_party_role": "BOTH", "charge_context": "COMMERCIAL", "calculation_basis": "PERCENTAGE"},
    {"component_code": "FUEL_SURCHARGE", "component_name": "Fuel Surcharge", "category": "SURCHARGE", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "PERCENTAGE"},
    {"component_code": "CURRENCY_ADJUSTMENT", "component_name": "Currency Adjustment", "category": "SURCHARGE", "default_party_role": "BOTH", "charge_context": "COMMERCIAL", "calculation_basis": "PERCENTAGE"},
    {"component_code": "SECURITY_SURCHARGE", "component_name": "Security Surcharge", "category": "SURCHARGE", "default_party_role": "BOTH", "charge_context": "COMPLIANCE", "calculation_basis": "SHIPMENT"},
    {"component_code": "PEAK_SEASON_SURCHARGE", "component_name": "Peak Season Surcharge", "category": "SURCHARGE", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "CONTAINER"},
    {"component_code": "PORT_CONGESTION", "component_name": "Port Congestion", "category": "SURCHARGE", "default_party_role": "BOTH", "charge_context": "PORT", "calculation_basis": "CONTAINER"},
    {"component_code": "TOLL", "component_name": "Toll", "category": "ACCESSORIAL", "default_party_role": "BOTH", "charge_context": "TRANSPORT", "calculation_basis": "SHIPMENT"},
    {"component_code": "LIFT_ON_LIFT_OFF", "component_name": "Lift On Lift Off", "category": "ACCESSORIAL", "default_party_role": "BOTH", "charge_context": "PORT", "calculation_basis": "CONTAINER"},
    {"component_code": "REEFER_SURCHARGE", "component_name": "Reefer Surcharge", "category": "ACCESSORIAL", "default_party_role": "BOTH", "charge_context": "EQUIPMENT", "calculation_basis": "CONTAINER"},
    {"component_code": "HAZMAT_SURCHARGE", "component_name": "Hazmat Surcharge", "category": "ACCESSORIAL", "default_party_role": "BOTH", "charge_context": "COMMODITY", "calculation_basis": "SHIPMENT"},
    {"component_code": "STORAGE", "component_name": "Storage", "category": "TIME_BASED", "default_party_role": "BOTH", "charge_context": "WAREHOUSE", "calculation_basis": "DAY"},
    {"component_code": "DEMURRAGE", "component_name": "Demurrage", "category": "TIME_BASED", "default_party_role": "BOTH", "charge_context": "PORT", "calculation_basis": "DAY"},
    {"component_code": "DETENTION", "component_name": "Detention", "category": "TIME_BASED", "default_party_role": "BOTH", "charge_context": "EQUIPMENT", "calculation_basis": "DAY"},
    {"component_code": "ORIGIN_DOCUMENTATION", "component_name": "Origin Documentation", "category": "DOCUMENTATION", "default_party_role": "BOTH", "charge_context": "ORIGIN", "calculation_basis": "DOCUMENT"},
    {"component_code": "AWB_DOCUMENTATION", "component_name": "AWB Documentation", "category": "DOCUMENTATION", "default_party_role": "BOTH", "charge_context": "AIR", "calculation_basis": "DOCUMENT"},
    {"component_code": "WEIGHBRIDGE_VGM", "component_name": "Weighbridge/VGM", "category": "DOCUMENTATION", "default_party_role": "BOTH", "charge_context": "COMPLIANCE", "calculation_basis": "CONTAINER"},
    {"component_code": "SCREENING", "component_name": "Screening", "category": "COMPLIANCE", "default_party_role": "BOTH", "charge_context": "SECURITY", "calculation_basis": "SHIPMENT"},
    {"component_code": "ROUNDING_ADJUSTMENT", "component_name": "Rounding Adjustment", "category": "ADJUSTMENT", "default_party_role": "BOTH", "charge_context": "FINANCE", "calculation_basis": "FLAT"},
    {"component_code": "MANUAL_ADJUSTMENT", "component_name": "Manual Adjustment", "category": "ADJUSTMENT", "default_party_role": "BOTH", "charge_context": "FINANCE", "calculation_basis": "FLAT"},
    {"component_code": "MARGIN_MARKUP", "component_name": "Margin Markup", "category": "MARGIN", "default_party_role": "PAYEE", "charge_context": "COMMERCIAL", "calculation_basis": "FLAT"},
)


COMMON_CHARGE_ALLOCATION_PROFILES: tuple[dict[str, object], ...] = (
    {
        "profile_code": "DIRECT_HEADER_DEFAULT",
        "profile_name": "Direct Header Allocation",
        "version_number": 1,
        "source_level": "HOUSE",
        "source_to_house_driver": None,
        "house_to_item_driver": None,
        "final_posting_level": "HOUSE",
        "default_quantity_uom": None,
        "notes": "Single-step allocation profile for direct document or header-level posting.",
        "settings_json": {"shape": "DIRECT"},
    },
    {
        "profile_code": "STAGED_CONTAINER_ITEM_DEFAULT",
        "profile_name": "Staged Container Allocation",
        "version_number": 1,
        "source_level": "CONTAINER",
        "source_to_house_driver": "CBM",
        "house_to_item_driver": "WEIGHT",
        "final_posting_level": "PO_SCHEDULE_LINE",
        "default_quantity_uom": "CBM",
        "notes": "Two-stage allocation profile for intermediate container-to-target propagation.",
        "settings_json": {"shape": "STAGED"},
    },
    {
        "profile_code": "MANUAL_TARGET_DEFAULT",
        "profile_name": "Manual Target Allocation",
        "version_number": 1,
        "source_level": "SHIPMENT",
        "source_to_house_driver": "CBM",
        "house_to_item_driver": "WEIGHT",
        "final_posting_level": "PO_SCHEDULE_LINE",
        "default_quantity_uom": None,
        "notes": "Manual allocation profile with no automatic basis defaults.",
        "settings_json": {"shape": "MANUAL"},
    },
)


COMMON_BUSINESS_DATE_PROFILES: tuple[dict[str, object], ...] = (
    {
        "profile_code": "OCEAN_HOUSE_STANDARD",
        "profile_name": "Ocean House Exchange Rate Policy",
        "description": "Fallback chain for ocean-house exchange-rate date resolution.",
        "version_number": 1,
        "steps": (
            {
                "step_number": 10,
                "date_key": "SHIPPED_ON_BOARD_DATE",
                "notes": "Prefer shipped-on-board date when the source system provides it.",
            },
            {
                "step_number": 20,
                "date_key": "SHIPMENT_ACTUAL_DEPARTURE_DATE",
                "notes": "Fallback to the actual departure date.",
            },
            {
                "step_number": 30,
                "date_key": "SHIPMENT_PLANNED_DEPARTURE_DATE",
                "notes": "Fallback to the estimated departure date.",
            },
        ),
    },
    {
        "profile_code": "AIR_HOUSE_STANDARD",
        "profile_name": "Air House Exchange Rate Policy",
        "description": "Fallback chain for air-house exchange-rate date resolution.",
        "version_number": 1,
        "steps": (
            {
                "step_number": 10,
                "date_key": "ACTUAL_FLIGHT_DEPARTURE_DATE",
                "notes": "Prefer the actual flight departure date when available.",
            },
            {
                "step_number": 20,
                "date_key": "AWB_EXECUTION_DATE",
                "notes": "Fallback to the air waybill execution date.",
            },
            {
                "step_number": 30,
                "date_key": "ESTIMATED_FLIGHT_DEPARTURE_DATE",
                "notes": "Fallback to the estimated flight departure date.",
            },
        ),
    },
)
