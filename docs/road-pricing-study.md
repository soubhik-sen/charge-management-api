# Road pricing study

LedgerFlow includes an opt-in, rerunnable seed script that creates a complete road-freight pricing example through the public API. It is study data, not schema or mandatory production master data.

## Seed the example

Start LedgerFlow, then run:

```bash
python scripts/seed_road_study.py
```

The defaults target `http://127.0.0.1:8000` with the development token `local-dev-token`. Override them when needed:

```bash
LEDGERFLOW_BASE_URL=https://ledgerflow.example.com \
LEDGERFLOW_SERVICE_TOKEN=replace-me \
python scripts/seed_road_study.py
```

The Transport Cockpit downstream Compose stack runs the same script automatically against its LedgerFlow service.

## What it creates

The released PAYEE contract identifies company `1001` as the payee and customer `2001` as the payer. Its default calculation template is `TC-DEMO-ROAD-CUSTOMER`; it has no legacy direct component lines or conditional template routes.

| Step | Charge component | Rate book | Behavior |
| --- | --- | --- | --- |
| 10 | `ROAD_FREIGHT_FTL` | `TC-DEMO-ROAD-EUR` | Adds linehaul to subtotal `BASE_TRANSPORT`. |
| 20 | `ROAD_FUEL_SURCHARGE` | `TC-DEMO-ROAD-FUEL-PCT` | Reads `BASE_TRANSPORT` as its percentage base but does not add fuel back to that subtotal. |
| 30 | `ROAD_TOLL` | `TC-DEMO-ROAD-TOLL-EUR` | Multiplies a per-kilometer rate by `DISTANCE_KM`. |
| 40 | `TAIL_LIFT_SERVICE` | `TC-DEMO-ROAD-TAIL-LIFT-EUR` | Runs only when `context.requires_tail_lift` is true. |
| 50 | `WAITING_TIME` | `TC-DEMO-ROAD-WAITING-EUR` | Runs only when `context.charge_waiting_time` is true and uses `DURATION_HOURS`. |
| 90 | `ROAD_INTERNAL_COST_REFERENCE` | `TC-DEMO-ROAD-INTERNAL-COST` | Produces a statistical benchmark line that is visible in detail but excluded from commercial totals and subtotals. |

Each rate book belongs to one charge component. Its rows demonstrate exact lane/equipment/service matches, a high-priority number for generic fallback rows, and deterministic selection of the most applicable row.

## Study request and expected result

Use [the road quote request](../examples/road-quote-request.json). It describes a standard curtainsider shipment from Barcelona to Madrid, a distance of 620 km, tail-lift service, and 1.5 billable waiting hours.

The selected rows produce:

| Line | Calculation | Amount |
| --- | --- | ---: |
| FTL linehaul | exact lane/equipment/service row | EUR 450.00 |
| Fuel surcharge | 12% of `BASE_TRANSPORT` (EUR 450.00) | EUR 54.00 |
| Toll | EUR 0.18 x 620 km | EUR 111.60 |
| Tail lift | conditional flat charge | EUR 35.00 |
| Waiting time | EUR 28.00 x 1.5 hours | EUR 42.00 |
| Commercial payee total | excludes statistical lines | **EUR 692.60** |
| Internal cost reference | EUR 0.62 x 620 km | EUR 384.40 statistical |

The request deliberately does not send `context.percentage_base_amount` or `context.percentage_bases`. The template creates the percentage base from the earlier linehaul step, which makes subtotal provenance visible on the resulting quote line.

## Rerun and version behavior

Every seeded rate book and template description contains a revision marker. Rerunning the same revision reuses its published objects and does not create duplicates.

If the old one-line `TC-DEMO` example already exists, the script publishes a new version of its rate book and calculation template. Released contracts are immutable, so the script creates a deterministic versioned replacement contract with a better selection priority instead of mutating history. A fresh database receives only the normal `TC-DEMO-PAYEE-2001` contract.

Publishing retires older rate-book and template versions, but historical quote lines retain their exact source version and row identifiers.
