# Caller Attribute Mapping

LedgerFlow can serve multiple caller applications without making rate books depend on any caller's field names. It owns a canonical pricing vocabulary; each caller either sends that vocabulary directly or uses a versioned mapping profile to translate its payload.

## The Two Layers

### Canonical pricing dimensions

A pricing dimension is a stable LedgerFlow attribute that may be selected as a rate-book column and matched against a quote. Examples are `ORIGIN_CODE`, `DESTINATION_CODE`, `TRANSPORT_MODE`, `EQUIPMENT_TYPE`, and a custom dimension such as `DELIVERY_ZONE`.

System dimensions map to existing first-class quote fields. Administrators can add custom dimensions through **Caller mappings** in the UI or `POST /pricing-dimensions`. A dimension defines its data type, optional allowed values, and case-sensitivity rule.

Rate books declare the custom columns they use in `dimension_codes`. Each row supplies values for those columns in `dimension_values`:

```json
{
  "rate_book_code": "ROAD_ZONE_2026",
  "rate_book_name": "Road delivery-zone rates",
  "charge_component_code": "ROAD_FREIGHT_FTL",
  "dimension_codes": ["DELIVERY_ZONE"],
  "entries": [
    {
      "charge_component_code": "ROAD_FREIGHT_FTL",
      "rate_amount": "175.00",
      "currency": "EUR",
      "dimension_values": {"DELIVERY_ZONE": "CENTRAL"}
    }
  ]
}
```

An active rate row is eligible only when every configured row dimension equals the normalized quote value. A missing quote value makes the row ineligible; it is not treated as a wildcard. A dimension omitted by the row is a wildcard for that dimension.

### Caller mapping profiles

A caller mapping profile belongs to one `caller_system_code` and one `schema_version`. It maps raw caller paths to LedgerFlow dimensions. The source path can be nested using dots, and an optional value map can translate caller codes to canonical values.

Mapping profiles are integration configuration, not commercial configuration. Do not assign them to contracts. The incoming quote selects a profile through `caller_mapping_profile_code`; LedgerFlow normalizes the request first, then contracts match the resulting party IDs and canonical applicability values.

```json
{
  "profile_code": "TMS_V2_ROAD",
  "profile_name": "TMS road schema v2",
  "caller_system_code": "ACME_TMS",
  "schema_version": "2",
  "mappings": [
    {
      "source_attribute": "shipment.deliveryZone",
      "dimension_code": "DELIVERY_ZONE",
      "required": true,
      "value_map": {"central": "CENTRAL", "north": "NORTH"}
    },
    {
      "source_attribute": "shipment.serviceCode",
      "dimension_code": "SERVICE_LEVEL",
      "required": false,
      "default_value": "STANDARD"
    }
  ]
}
```

Use `POST /caller-mapping-profiles/{id}/preview` before integrating a caller. It returns the normalized `dimension_values` and any built-in `standard_fields` without creating a quote.

## Calling Modes

### Caller or adapter sends canonical values

Use this when the caller already has an adapter that understands LedgerFlow. Identify the caller schema for traceability and send standard fields plus any custom canonical dimensions directly:

```json
{
  "request_number": "SHIPMENT-10042",
  "caller_system_code": "TRANSPORT_COCKPIT",
  "caller_schema_version": "1",
  "company_id": 1001,
  "customer_id": 2001,
  "origin_code": "ESBCN",
  "destination_code": "ESMAD",
  "mode": "ROAD",
  "dimension_values": {"DELIVERY_ZONE": "CENTRAL"},
  "currency": "EUR"
}
```

`caller_system_code` and `caller_schema_version` must be supplied together. A mapping profile is not required in this mode.

### LedgerFlow maps a raw caller payload

Use this when the caller should remain unaware of canonical LedgerFlow names. Supply the selected profile and raw attributes:

```json
{
  "request_number": "SHIPMENT-10042",
  "caller_system_code": "ACME_TMS",
  "caller_schema_version": "2",
  "caller_mapping_profile_code": "TMS_V2_ROAD",
  "caller_attributes": {
    "shipment": {
      "deliveryZone": "central",
      "serviceCode": "EXP"
    }
  },
  "company_id": 1001,
  "customer_id": 2001,
  "currency": "EUR"
}
```

LedgerFlow validates that the profile belongs to the supplied caller and schema, resolves required/default values, normalizes types, and stores both the raw caller snapshot and canonical result on the quote. If a caller also supplies a canonical value that conflicts with the mapped result, the API rejects the request instead of silently choosing one.

## Field Responsibilities

| Payload area | Purpose | Used for rate-row matching? |
| --- | --- | --- |
| Standard quote fields such as `origin_code`, `mode`, and `service_level` | Built-in commercial applicability | Yes |
| `dimension_values` | Additional canonical applicability values | Yes |
| `caller_attributes` | Raw, caller-specific source data for a selected mapping profile | Only after mapping |
| `calculation_inputs` and `component_calculation_inputs` | Numeric or formula inputs such as distance, duration, or counts | No; used by calculation profiles |
| `context` | Template preconditions and non-pricing operational facts | No; used by precondition checks |
| `date_values` | Typed operational dates used by business-date profiles | No; used to resolve the pricing/FX business date |

Do not add a canonical pricing dimension for every field published by a caller. Add one only when the value has stable cross-caller commercial meaning and must participate in rate applicability. Caller-only fields can stay in `caller_attributes` or `context`.

## Multi-Caller Lifecycle

1. Define canonical dimensions globally in LedgerFlow.
2. Create a separate mapping profile for each caller/schema contract that needs translation.
3. Preview the profile against a representative payload.
4. Select canonical dimensions on the relevant rate-book family and populate row values.
5. Send caller identity on every quote so stored provenance identifies the source schema.
6. Create a new mapping profile code when a used schema mapping changes materially.

System dimensions cannot be deactivated. A custom dimension used by a rate book or active mapping profile cannot be structurally changed or deactivated. Similarly, a mapping profile used by a quote cannot have its caller identity or mappings rewritten. These guards keep historical quote and rate provenance reproducible.

Existing integrations remain valid: a request without caller identity or custom dimensions follows the original first-class quote fields. This compatibility path should not be used for a new multi-caller integration because it loses source-schema provenance.
