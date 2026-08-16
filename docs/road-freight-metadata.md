# Road Freight Metadata

LedgerFlow includes a reusable European road and land freight metadata pack. It is industry-aligned rather than a claim that one universal charge-code list exists: carriers use different commercial labels, but the same operational charge families recur across tariffs.

The seed design is grounded in published carrier and regulatory material:

- [DHL Freight road surcharges](https://www.dhl.com/nl-en/home/freight/help-center-for-european-road-and-rail/dhl-freight-surcharges.html) identifies fuel, currency adjustment, toll/kilometer levies, and peak-season surcharges.
- [DSV road surcharges](https://www.dsv.com/en/countries/switzerland/surcharges) identifies dangerous goods, loading-device or pallet exchange, toll, congestion, and fuel charges.
- [European Commission road charging](https://transport.ec.europa.eu/transport-modes/road/road-charging_en) distinguishes distance-based tolls from time-based vignettes and covers vehicle, CO2, environmental, and congestion differentiation.
- [UNECE ADR 2025](https://unece.org/transport/publications/agreement-concerning-international-carriage-dangerous-goods-road-adr-2025) is the governing framework behind the dangerous-goods component.
- [UNECE e-CMR guide](https://unece.org/trade/documents/2023/10/executive-guide-e-cmr) explains the road consignment-note context behind CMR documentation.

## Seeded Charge Components

| Component code | Meaning | Default basis |
| --- | --- | --- |
| `ROAD_FREIGHT_FTL` | Full-truckload linehaul | `FLAT` |
| `ROAD_FREIGHT_LTL` | Less-than-truckload linehaul | `WEIGHT` |
| `ROAD_FUEL_SURCHARGE` | Road diesel/fuel adjustment | `PERCENTAGE` |
| `ROAD_TOLL` | Distance-sensitive road toll | `DISTANCE` |
| `ROAD_CONGESTION_SURCHARGE` | Congestion-zone or network surcharge | `FLAT` |
| `LOW_EMISSION_ZONE_SURCHARGE` | Environmental or low-emission-zone access | `FLAT` |
| `WAITING_TIME` | Vehicle or driver waiting | `PER_HOUR` |
| `LOADING_SERVICE` | Loading labor/service | `FLAT` |
| `UNLOADING_SERVICE` | Unloading labor/service | `FLAT` |
| `TAIL_LIFT_SERVICE` | Tail-lift collection or delivery | `FLAT` |
| `ADR_DANGEROUS_GOODS` | ADR dangerous-goods handling/transport | `FLAT` |
| `TEMPERATURE_CONTROL` | Temperature-controlled equipment/service | `FLAT` |
| `PALLET_EXCHANGE` | Pallet or loading-device exchange | `PER_PALLET` |
| `MULTI_STOP_SURCHARGE` | Additional pickup/delivery stops | `PER_STOP` |
| `REDELIVERY` | Second delivery attempt | `FLAT` |
| `FAILED_COLLECTION` | Unsuccessful collection attempt | `FLAT` |
| `DELIVERY_APPOINTMENT` | Booked or timed delivery appointment | `FLAT` |
| `REMOTE_AREA_SURCHARGE` | Remote or difficult-service area | `FLAT` |
| `OVERWEIGHT_SURCHARGE` | Excess weight handling | `WEIGHT` |
| `OVERSIZE_SURCHARGE` | Excess dimensions or non-standard footprint | `FLAT` |
| `SPECIAL_TRANSPORT_PERMIT` | Permit/escort administration for exceptional loads | `FLAT` |
| `CMR_DOCUMENTATION` | CMR/e-CMR documentation service | `DOCUMENT` |

Every seeded road component has `charge_context=ROAD`. Category and context classify and match charges; they do not change arithmetic by themselves. The calculation basis or selected calculation profile controls arithmetic. Component values are defaults; a rate-book row may store an explicit basis, context, calculation-profile, or allocation-profile override.

## Calculation Profiles

| Profile | Required caller input | Formula |
| --- | --- | --- |
| `PER_KILOMETER` | `DISTANCE_KM` | unit rate x kilometers |
| `PER_STOP` | `STOP_COUNT` | unit rate x stops |
| `PER_PALLET` | `PALLET_COUNT` | unit rate x pallets |
| `PER_LOADING_METER` | `LOADING_METERS` | unit rate x loading meters |
| `PER_HOUR` | `DURATION_HOURS` | unit rate x hours |

The first four use the generic `MANUAL` factor resolver because route and loading-unit data belong to the caller's TMS, ERP, routing engine, or shipment adapter. `PER_HOUR` uses the built-in duration resolver. Missing required factors block calculation instead of silently assuming `1`.

The seed pack assigns `PER_KILOMETER` to `ROAD_TOLL`, `PER_HOUR` to `WAITING_TIME`, `PER_PALLET` to `PALLET_EXCHANGE`, and `PER_STOP` to `MULTI_STOP_SURCHARGE`. Rate-book rows and contract lines can still override those component defaults explicitly.

Use `POST /api/v1/charge-management/calculations/preview` with the published profile version and `calculation_inputs`:

```json
{
  "basis": "DISTANCE",
  "rate_amount": "1.25",
  "source_currency": "EUR",
  "target_currency": "EUR",
  "calculation_profile_version_id": 9,
  "calculation_inputs": {
    "DISTANCE_KM": "480"
  }
}
```

The example returns a source amount of EUR 600. Profile/version and input snapshots are returned for auditability. Resolve the actual version ID from `GET /calculation-profiles?q=PER_KILOMETER`; do not hardcode the example ID.

## Allocation Profiles

The road pack publishes three item-cost allocation choices:

| Profile | Shipment to House | House to item |
| --- | --- | --- |
| `ROAD_WEIGHT_TO_ITEM` | Gross weight | Gross weight |
| `ROAD_VOLUME_TO_ITEM` | Cubic volume | Cubic volume |
| `ROAD_EQUAL_TO_ITEM` | Count | Count |

Allocation is a separate decision from calculation. For example, a toll can be calculated from route distance and then allocated to commercial items by weight. A host that does not post to item level can leave allocation unselected or use a header-level profile.

## Business Date And FX

`ROAD_SHIPMENT_STANDARD` is a published exchange-rate date profile with this fallback order:

1. `ROAD_ACTUAL_PICKUP_DATE`.
2. `ROAD_PLANNED_PICKUP_DATE`.
3. `CMR_ISSUE_DATE`.
4. `DOCUMENT_DATE`.

`ROAD_SHIPMENT` is an allowed assignment and charge-document scope. The caller supplies typed values through `POST /business-dates/resolve`; Swagger and `GET /initialization-data` expose the accepted date identifiers. LedgerFlow does not infer missing operational dates from free text.

The road-specific identifiers are `ROAD_ACTUAL_PICKUP_DATE`, `ROAD_PLANNED_PICKUP_DATE`, `ROAD_ACTUAL_DELIVERY_DATE`, `ROAD_PLANNED_DELIVERY_DATE`, and `CMR_ISSUE_DATE`. Delivery dates are available for custom profiles even though the seeded FX policy is pickup-led.

Example caller values:

```json
{
  "profile_code": "ROAD_SHIPMENT_STANDARD",
  "date_values": [
    {
      "date_type": "ROAD_ACTUAL_PICKUP_DATE",
      "date_value": "2026-08-09"
    },
    {
      "date_type": "DOCUMENT_DATE",
      "date_value": "2026-08-08"
    }
  ]
}
```

After resolving the business date, use it as `rate_date` for FX resolution or calculation preview. This keeps the host responsible for operational facts and LedgerFlow responsible for deterministic policy evaluation.
