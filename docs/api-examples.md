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

For caller-specific fields, first define a canonical pricing dimension and a per-caller mapping profile, then use `dimension_codes` on the book and `dimension_values` on its rows. See [Caller attribute mapping](caller-attribute-mapping.md) for complete requests and matching rules. The standard fields in this example remain valid without a mapping profile.

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
    "request_number": "ROAD-QUOTE-001",
    "caller_system_code": "TRANSPORT_COCKPIT",
    "caller_schema_version": "1",
    "company_id": 10,
    "customer_id": 20,
    "origin_code": "ESBCN",
    "destination_code": "USNYC",
    "mode": "OCEAN",
    "source_object_type": "SHIPMENT",
    "source_object_id": "SHIPMENT-10042",
    "container_count": "2",
    "chargeable_weight": "18000",
    "requested_service_date": "2026-08-15",
    "currency": "USD",
    "calculation_inputs": {
      "DISTANCE_KM": "620"
    },
    "component_calculation_inputs": {
      "BASE_FREIGHT": {
        "BOOKING_FACTOR": "1"
      }
    },
    "date_values": [{
      "date_type": "DOCUMENT_DATE",
      "date_value": "2026-08-10"
    }]
  }'

QUOTE_ID=replace_with_returned_quote_id
curl -sS -X PUT "$BASE_URL/quote-requests/$QUOTE_ID/workspace" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"REQUESTED"}'

curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/quote-requests/$QUOTE_ID/rate"

# Resume an integration request without scanning paginated results.
curl -sS -G -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "request_number=ROAD-QUOTE-001" \
  "$BASE_URL/quote-requests"

# Delete an unawarded test quote and its offers/options.
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/quote-requests/$QUOTE_ID"
```

The final response contains one option line for `BASE_FREIGHT` with amount `5000.00`. Each generated line records the exact source contract plus the selected direct contract line or template route, rate book/row, and calculation template/step when applicable.

`calculation_inputs` are global factor values. A key under `component_calculation_inputs` takes precedence for that component. `date_values` contains typed dates supplied by the caller; business-date profiles select among those values in configured order. `requested_service_date` remains the explicit pricing-date override when present. See the generated OpenAPI schema for the controlled `date_type` values, or import `examples/road-quote-request.json` in the Quotes workspace for a complete road example.

Award an option, inspect approval readiness and provenance, then execute the document lifecycle:

```bash
QUOTE_OPTION_ID=replace_with_rated_option_id
curl -sS -X POST "$BASE_URL/quote-requests/$QUOTE_ID/award" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"quote_option_id\": $QUOTE_OPTION_ID, \"execution_source_system\": \"ROUTEWISE\", \"execution_plan_id\": \"PLAN-A\", \"execution_route_id\": \"ROUTE-001\", \"execution_source_id\": \"plan:PLAN-A:route:ROUTE-001\", \"execution_request_number\": \"PLAN-A-ROUTE-001\"}"

DOCUMENT_ID=replace_with_returned_charge_document_id
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/charge-documents/$DOCUMENT_ID/workspace"

curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/charge-documents/$DOCUMENT_ID/approve"

curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/charge-documents/$DOCUMENT_ID/post-export"

curl -sS -X POST "$BASE_URL/charge-documents/$DOCUMENT_ID/reverse" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Customer cancelled movement"}'
```

The award call is safe to retry with the same executable plan/route/request identity: it returns the existing charge document and commitment. A second route such as `ROUTE-002` may use the same customer, lane, equipment, service, and pricing date and still creates its own document. Reusing `PLAN-A` / `ROUTE-001` with a different `execution_request_number`, awarding a different option on an already-awarded request, or attempting to rank after award returns `409`.

The workspace returns `approval_ready`, authoritative `approval_checks`, linked invoices/matches, and the awarded `source_quote_option`. Match each document line's `source_quote_option_line_id` to that option's lines to recover exact contract, rate-book row, and calculation-template provenance. The default export stores an idempotent `INTERNAL_LEDGER` JSON batch; an adopter must wire external delivery separately.

Delete an incorrectly captured invoice while its linked charge document is still editable:

```bash
INVOICE_ID=replace_with_invoice_id
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/invoices/$INVOICE_ID"
```

Delete an editable direct/manual charge document only after its invoices have been removed. Quote-derived documents and documents linked to downstream lifecycle records are retained for audit:

```bash
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/charge-documents/$DOCUMENT_ID"
```

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
      \"accumulate_result_in_subtotal\": true,
      \"rate_book_id\": $RATE_BOOK_ID
    }]
  }"

TEMPLATE_ID=replace_with_returned_template_id
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/calculation-templates/$TEMPLATE_ID/publish"
```

The common template-based contract needs no component lines. Bind the published template at the header:

```bash
curl -sS -X POST "$BASE_URL/contracts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"contract_number\": \"CUSTOMER-EU-STANDARD\",
    \"contract_name\": \"Customer EU standard pricing\",
    \"contract_role\": \"PAYEE\",
    \"company_id\": 10,
    \"customer_id\": 20,
    \"currency\": \"USD\",
    \"selection_priority\": 100,
    \"default_calculation_template_id\": $TEMPLATE_ID,
    \"template_routes\": [],
    \"lines\": []
  }"
```

When one contract must choose different templates for different conditions, add `template_routes`. A route contains applicability fields and `calculation_template_id`, but no charge component. The lowest route priority wins, then the most specific applicability; an unresolved tie returns `409`. Contract matching uses the same lowest-priority/most-specific rule and resolves at most one payer and one payee contract.

For a later percentage step that reads `BASE_TRANSPORT` but must not increase that base for subsequent percentage steps, use the same `subtotal_key` with `"accumulate_result_in_subtotal": false`. The resulting line still contributes to its payer/payee commercial total. This differs from `"is_statistical": true`, which excludes the line from commercial totals and subtotal accumulation.

## Discover The Remaining API

The generated [OpenAPI document](../app/contracts/charge-management-api.openapi.json) is the source for the complete component, alias, rate-book, template, contract, quote, commitment, charge-document, invoice, matching, and export surface. Swagger UI at `/docs` can execute the same calls interactively.
