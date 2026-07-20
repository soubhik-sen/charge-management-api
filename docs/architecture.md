# Architecture

The standalone Charge Management API is deliberately adapter-neutral.

## Layers
- `app.api.v1`: FastAPI routes and HTTP contract.
- `app.domain`: reusable charge model, seed data, rating, ranking, invoice matching, export lifecycle.
- `app.infrastructure`: replaceable seams for auth, policy, source-object hydration, document storage, and financial export.

## Persistence
The repo is configured for database-backed deployment through SQLAlchemy models and Alembic migrations. The migration set creates the full charge domain schema, a `charge_management_settings` table for adapter-neutral setup such as quotation policy, quote acceptance, provider-cost layer behavior, and charge-date-basis metadata, and seeds common charge components. The current HTTP contract tests still use the in-memory domain harness for fast lifecycle validation; add SQLAlchemy repository tests as the persistence adapter is wired into runtime services.

Schema source:
- `app/db/models.py`
- `alembic/versions/0001_initial_charge_management_schema.py`

## Boundary From FLUXPORT
FLUXPORT has its own embedded implementation. This repo does not import FLUXPORT code and does not require FLUXPORT metadata, role-scope policy tables, document locks, or landed-cost posting.

Quotation policy is generic here: `REQUIRED` means direct charge-document creation is blocked, `OPTIONAL` allows quote-driven or direct documents, and `DIRECT_ONLY` blocks new quote requests. Quote acceptance is also generic: `CUSTOMER_ACCEPTANCE` keeps an explicit acceptance/award step after rating, and `AUTO_ACCEPT` lets a consuming application auto-award the first rated option if that is its operating choice. Consuming products decide how these settings are administered and persisted.

`provider_cost_layer_enabled` controls the rating shape. When disabled, rating can create customer-facing options from matching `PAYEE` customer-pricing contracts without requiring provider-cost contracts. When enabled, the full payer/payee provider-cost path remains available so a consuming product can calculate provider cost, receivable price, and margin.

Quote request cargo fields are also generic. Ocean-style RFQs can use `container_count` and `equipment_type`; air/package RFQs can use `package_count`, `package_type`, `gross_weight`, and `gross_volume_cbm`. Quote requests can carry `valid_from` and `valid_to` so the awarded commitment is consumed within a validity window without requiring a specific service date.

Quote request usability is part of the technical contract. A consuming application can create a quote request, list/search persisted requests, open a quote workspace, continue rate/rank/award actions, and inspect linked options, commitments, and charge documents without depending on transient response IDs.

Charge component aliases are adapter-neutral mapping records. They can stay global or be narrowed by customer, forwarder, and transport mode so the same external label can map to different default allocation behavior for different commercial or logistics contexts. Alias override modes follow the canonical generic contract: `INHERIT_PROFILE`, `OVERRIDE_PROFILE`, and `NO_ALLOCATION`.

Charge allocation profiles are versioned, publishable API records. The standalone contract uses the same canonical profile-version field names as the embedded implementation: `source_level`, `source_to_house_driver`, `house_to_item_driver`, and `final_posting_level`. `HOUSE` remains a supported final posting and charge-line target level in the standalone surface.

Quote offers are adapter-neutral provider submissions against a submitted quote request. A consuming application can create a draft RFQ, move it to `REQUESTED` through the quote workspace update contract, submit an offer, reopen the quote workspace to inspect persisted offers, and rank/award the offer-derived quote option without relying on a host-specific procurement or UI model.

Contract usability is also part of the adapter-neutral contract. Consumers can create payer/payee contracts, list them by role/status/scope identifiers, open a contract workspace, update draft workspace data, and release the selected contract without depending on manual ID entry from a transient create response. Contract headers can carry default rate book and calculation-template references; contract lines can override those defaults for lane/component-specific rating. Release is blocked unless the contract has at least one line and either the header or a line references a rate book or calculation template.

Calculation-template usability is part of the adapter-neutral contract. Consumers can create reusable charge-step templates, list/search them, open a selected template workspace, inspect component steps and related rate books, and update template steps after refresh.

Charge-document usability is part of the same contract boundary. Consumers can create direct documents or receive quote-award documents, list/search them by status/source/scope identifiers, open a document workspace, and continue lifecycle actions against a selected document after refresh.

Invoice usability follows the same rule. Consumers can capture an invoice, list/search invoices, open an invoice workspace with the related charge document and match results, and run matching against the selected invoice without depending on transient create-response IDs.

Quote commitments are adapter-neutral awarded quote outcomes. Award creates a commitment with lane/scope/capacity/amount balances; consumers can call match and consume endpoints when a host application later has an execution object such as a booking, shipment, container, or airwaybill. If that execution object is removed or cancelled, consumers reverse the specific consumption row to restore capacity while preserving audit history. The API does not assume how that object is modeled. A second active commitment is blocked when it has the same commercial scope and overlapping validity.

## Extension Points
- `PolicyAdapter`: authorization and tenant/scope enforcement.
- `SourceObjectHydrator`: optional PO/SO/shipment/container hydration.
- `FinancialExportAdapter`: ledger, ERP, billing, or event export integration.
