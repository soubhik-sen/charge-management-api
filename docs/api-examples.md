# API Examples

These examples use the local Docker profile. On Windows PowerShell, invoke `curl.exe` rather than the `curl` alias.

Read [Core concepts and module guide](core-concepts.md) first if you are deciding which objects your integration needs.

```bash
BASE_URL=http://localhost:8000/api/v1/charge-management
TOKEN=local-dev-token
```

## Inspect Initialization Data

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/initialization-data"
```

## Create And Publish An Allocation Profile

Create:

```bash
curl -sS -X POST "$BASE_URL/allocation-profiles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_code": "SHIPMENT_BY_WEIGHT",
    "profile_name": "Shipment charges by weight",
    "initial_version": {
      "effective_from": "2026-01-01",
      "effective_to": "2026-12-31",
      "source_level": "SHIPMENT",
      "source_to_house_driver": "GROSS_WEIGHT",
      "house_to_item_driver": "ITEM_WEIGHT",
      "final_posting_level": "PO_SCHEDULE_LINE",
      "default_quantity_uom": "KG",
      "missing_driver_policy": "BLOCK"
    }
  }'
```

Copy the returned first version `id`, then publish it:

```bash
VERSION_ID=replace_with_returned_version_id
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/allocation-profile-versions/$VERSION_ID/publish"
```

Profiles retain immutable published versions; create a new draft version for later changes.

## Create And Assign A Business-Date Profile

Create an ordered fallback chain:

```bash
curl -sS -X POST "$BASE_URL/business-date-profiles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_code": "OCEAN_ACTUAL_THEN_PLANNED",
    "profile_name": "Ocean actual then planned departure",
    "description": "Exchange-rate date fallback for ocean house shipments",
    "initial_version": {
      "steps": [
        {"step_number": 1, "date_key": "SHIPMENT_ACTUAL_DEPARTURE_DATE"},
        {"step_number": 2, "date_key": "SHIPMENT_PLANNED_DEPARTURE_DATE"},
        {"step_number": 3, "date_key": "DOCUMENT_DATE"}
      ]
    }
  }'
```

Publish the returned version, then assign the returned profile:

```bash
DATE_VERSION_ID=replace_with_returned_version_id
PROFILE_ID=replace_with_returned_profile_id

curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/business-date-profile-versions/$DATE_VERSION_ID/publish"

curl -sS -X POST "$BASE_URL/business-date-profiles/$PROFILE_ID/assignments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "GLOBAL",
    "shipment_scope": "OCEAN_HOUSE",
    "business_purpose": "EXCHANGE_RATE_DATE",
    "priority": 100,
    "is_active": true
  }'
```

Only one effective profile can own the same owner scope, shipment scope, and business purpose slot.

Resolve the profile independently against operational context:

```bash
curl -sS -X POST "$BASE_URL/business-dates/resolve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"profile_id\": $PROFILE_ID,
    \"date_values\": [
      {
        \"date_type\": \"SHIPMENT_ACTUAL_DEPARTURE_DATE\",
        \"date_value\": \"2026-07-20\"
      },
      {
        \"date_type\": \"DOCUMENT_DATE\",
        \"date_value\": \"2026-07-21\"
      }
    ],
    \"fallback_date\": \"2026-07-22\"
  }"
```

Each item names exactly what date the caller supplied. The API rejects unknown date types,
invalid ISO dates, and duplicate date types with `422`. The response identifies the normalized
supplied keys, published profile version, attempted keys, selected key, resolved date, and whether
the explicit fallback was used. The former untyped `context` object remains accepted only for
backward compatibility.

## Maintain And Resolve An FX Rate

Migrations seed source `MANUAL` with ID `1`. Create a directional EUR-to-USD rate:

```bash
curl -sS -X POST "$BASE_URL/fx-rates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "source_currency": "EUR",
    "target_currency": "USD",
    "rate_date": "2026-07-21",
    "rate": "1.1500000000",
    "rate_type": "MID",
    "conversion_method": "DIRECT",
    "metadata_json": {"provenance": "manual-example"}
  }'
```

A stored rate means target-currency units per one source-currency unit. Convert EUR 100 to USD:

```bash
curl -sS -X POST "$BASE_URL/fx-rates/resolve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_currency": "EUR",
    "target_currency": "USD",
    "rate_date": "2026-07-21",
    "amount": "100",
    "source_code": "MANUAL",
    "rate_type": "MID",
    "conversion_method": "DIRECT",
    "allow_prior_date": true,
    "allow_inverse": true
  }'
```

The response includes the selected rate and date, effective rate, converted amount, and whether inverse lookup was applied.

## Preview A Charge Calculation And Allocation

Use the preview endpoint when an ERP, TMS, or other host needs the reusable calculation engine without creating a quote or document. This example calculates 12.5% of USD 200 and allocates the exact USD 25 result by a 1:2 driver ratio:

```bash
ALLOCATION_VERSION_ID=replace_with_published_allocation_version_id

curl -sS -X POST "$BASE_URL/calculations/preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"basis\": \"PERCENTAGE\",
    \"rate_percent\": \"12.5\",
    \"percentage_base_amount\": \"200\",
    \"source_currency\": \"USD\",
    \"target_currency\": \"USD\",
    \"allocation_profile_version_id\": $ALLOCATION_VERSION_ID,
    \"allocation_targets\": [
      {
        \"target_level\": \"HOUSE\",
        \"target_object_type\": \"house\",
        \"target_object_id\": \"H-1\",
        \"driver_value\": \"1\"
      },
      {
        \"target_level\": \"HOUSE\",
        \"target_object_type\": \"house\",
        \"target_object_id\": \"H-2\",
        \"driver_value\": \"2\"
      }
    ]
  }"
```

The result is side-effect free. It returns source and target amounts, calculation snapshots, FX resolution, allocation-profile snapshot, ratios, and deterministic `8.33` / `16.67` target amounts. For cross-currency preview, set different source/target currencies and supply `rate_date`; the resolver applies exact/prior and direct/inverse policy.

## Rate A Quote From A Contract

Create an effective-dated rate book. Overlapping rows are allowed; the engine selects one winner by applicability, specificity, priority, and scale floor.

```bash
curl -sS -X POST "$BASE_URL/rate-books" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_book_code": "EU_OCEAN_2026",
    "rate_book_name": "EU ocean customer rates",
    "charge_component_code": "BASE_FREIGHT",
    "row_attribute_keys": [
      "origin_code",
      "destination_code",
      "mode",
      "scale_from",
      "basis_override",
      "priority"
    ],
    "status": "DRAFT",
    "valid_from": "2026-01-01",
    "valid_to": "2026-12-31",
    "entries": [{
      "charge_component_code": "BASE_FREIGHT",
      "rate_amount": "2500",
      "basis_override": "PER_CONTAINER",
      "currency": "USD",
      "origin_code": "ESBCN",
      "destination_code": "USNYC",
      "mode": "OCEAN",
      "scale_from": "1",
      "priority": 100,
      "is_active": true
    }]
  }'
```

Use the returned rate-book `id` in a payee contract, then release it:

```bash
RATE_BOOK_ID=replace_with_returned_rate_book_id

curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/rate-books/$RATE_BOOK_ID/publish"

curl -sS -X POST "$BASE_URL/contracts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contract_number\": \"CUSTOMER-2026-001\",
    \"contract_name\": \"Customer ocean pricing\",
    \"contract_role\": \"PAYEE\",
    \"company_id\": 10,
    \"customer_id\": 20,
    \"valid_from\": \"2026-01-01\",
    \"valid_to\": \"2026-12-31\",
    \"lines\": [{
      \"line_number\": 10,
      \"charge_component_code\": \"BASE_FREIGHT\",
      \"rate_book_id\": $RATE_BOOK_ID,
      \"origin_code\": \"ESBCN\",
      \"destination_code\": \"USNYC\",
      \"mode\": \"OCEAN\"
    }]
  }"

CONTRACT_ID=replace_with_returned_contract_id
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/contracts/$CONTRACT_ID/release"
```

Create, submit, and rate a quote:

```bash
curl -sS -X POST "$BASE_URL/quote-requests" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 10,
    "customer_id": 20,
    "origin_code": "ESBCN",
    "destination_code": "USNYC",
    "mode": "OCEAN",
    "container_count": "2",
    "chargeable_weight": "18000",
    "requested_service_date": "2026-08-15",
    "currency": "USD"
  }'

QUOTE_ID=replace_with_returned_quote_id
curl -sS -X PUT "$BASE_URL/quote-requests/$QUOTE_ID/workspace" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"REQUESTED"}'

curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/quote-requests/$QUOTE_ID/rate"
```

The final response contains one option line for `BASE_FREIGHT` with amount `5000.00`.

To change published pricing, create a new draft version rather than mutating the published row:

```bash
curl -sS -X POST "$BASE_URL/rate-books/$RATE_BOOK_ID/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_book_code": "EU_OCEAN_2026",
    "rate_book_name": "EU ocean customer rates",
    "charge_component_code": "BASE_FREIGHT",
    "row_attribute_keys": [
      "origin_code",
      "destination_code",
      "mode",
      "basis_override"
    ],
    "status": "DRAFT",
    "currency": "USD",
    "valid_from": "2026-01-01",
    "valid_to": "2026-12-31",
    "entries": [{
      "charge_component_code": "BASE_FREIGHT",
      "rate_amount": "2600",
      "basis_override": "PER_CONTAINER",
      "currency": "USD",
      "origin_code": "ESBCN",
      "destination_code": "USNYC",
      "mode": "OCEAN"
    }]
  }'
```

The response contains the complete version history. Publish the returned draft ID when it is ready; the API retires the prior published version while contracts pinned to it remain reproducible.

To combine multiple component-specific books, create and publish a calculation template:

```bash
curl -sS -X POST "$BASE_URL/calculation-templates" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"template_code\": \"EU_OCEAN_STANDARD\",
    \"template_name\": \"EU ocean standard charge build\",
    \"status\": \"DRAFT\",
    \"steps\": [{
      \"step_number\": 10,
      \"charge_component_code\": \"BASE_FREIGHT\",
      \"relationship_role\": \"BOTH\",
      \"subtotal_key\": \"BASE_TRANSPORT\",
      \"rate_book_id\": $RATE_BOOK_ID
    }]
  }"

TEMPLATE_ID=replace_with_returned_template_id
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/calculation-templates/$TEMPLATE_ID/publish"
```

## Discover The Remaining API

The generated [OpenAPI document](../app/contracts/charge-management-api.openapi.json) is the source for the complete component, alias, rate-book, template, contract, quote, commitment, charge-document, invoice, matching, and export surface. Swagger UI at `/docs` can execute the same calls interactively.
