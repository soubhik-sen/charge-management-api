# UI Administration Guide

This guide covers the master-data and quote-testing workflows available in the LedgerFlow Flutter web application. Read [Core concepts](core-concepts.md) for the domain model and [Authentication](authentication.md) before connecting the UI to a production API.

## Connect The UI

The deployed UI starts in an empty disconnected workspace. It displays records only after a successful API connection; local fixture data is reserved for automated component tests and is never presented by the application shell.

1. Select **Connect API** in the top bar.
2. Enter the API base URL, such as `http://localhost:8000`.
3. Enter a bearer token issued for that API.
4. Confirm that the sidebar status changes from **Not connected** to **Live API**.

The token is held only in memory. Reloading the page removes it. The browser never receives the JWT signing secret.

## Recommended Configuration Sequence

1. Create calculation profiles and publish their initial versions.
2. Create allocation profiles and publish their initial versions.
3. Create business-date profiles, publish them, and add assignment scopes when inheritance is required.
4. Create or edit charge components and select the published profiles as defaults.
5. Maintain FX rates needed by cross-currency pricing.
6. Create and publish component-specific rate books.
7. Create and publish calculation templates when a contract needs an ordered multi-component build.
8. Reference published books or templates from contracts.

This order prevents a component from pointing to a draft definition that cannot safely execute.

## Charge Components

Open **Components** to search the full-width component catalog. Select a row to expand its classification, rating defaults, profile usage, and edit actions in place; select it again to collapse it.

### Create A Component

1. Select **New component**.
2. Enter a stable uppercase-style code and a readable name.
3. Set category, business context, default payer/payee role, and calculation basis.
4. Optionally select published calculation and allocation profiles.
5. Select a business-date policy:
   - `LEGACY_BASIS` uses the component's single date basis.
   - `INHERIT_PROFILE` resolves a scoped business-date assignment at runtime.
   - `PROFILE_OVERRIDE` requires a specific published business-date profile.
6. Save the component.

Use **Edit defaults** to change reusable behavior. **Deactivate** is a soft delete: historical documents retain their component reference while new work can exclude the inactive component.

Category is stable classification metadata used for cataloging and reporting; it does not change the amount formula. Charge context identifies the operational side or lifecycle area where a charge applies. For example, `DESTINATION` means import/arrival-side work, and a rate row with that effective context matches a quote that supplies `charge_context=DESTINATION`. The tax switch similarly classifies a component for reporting and downstream tax handling; it does not calculate tax by itself.

Calculation basis, charge context, calculation profile, allocation profile, and business-date policy are component-level defaults. A rate row may leave basis/context blank to inherit them or select an explicit override. The API returns both the resolved snapshot (`basis`, `charge_context`) used by that rate-book version and nullable override fields (`basis_override`, `charge_context_override`). This snapshot keeps published pricing reproducible if the component default changes later.

Migration `0022` marks every pre-existing row basis as an explicit override because basis was mandatory in the earlier API. This preserves historical behavior instead of silently replacing it with a later component default.

## Calculation Profiles

A calculation profile turns a selected rate into a source amount. Open **Profiles**, then select **Calculation**.

### Create And Publish

1. Select **New** and enter the profile identity.
2. Configure the initial draft version:
   - Application level: shipment, container, house, or PO schedule line.
   - Method: flat amount or rate times product.
   - Optional effective dates and rate UOM.
   - Ordered factor resolvers, including code, label, resolver, UOM, required state, and optional default value.
3. Save the profile. Version 1 is created in `DRAFT` status.
4. Review the version summary and select **Publish**.

`RATE_TIMES_PRODUCT` requires at least one factor. Published versions are immutable. Select **New draft** to copy a previous version into the editor, change it, and publish a later version.

### Use The Profile

Select the published profile from a component's **Calculation profile** field. Rate entries and contract lines can provide more specific overrides through their API workspaces. Runtime provenance records the effective profile version and resolved factor values.

## Allocation Profiles

An allocation profile distributes one calculated source amount to a final posting level. Open **Profiles**, then select **Allocation**.

### Create And Publish

1. Select **New** and enter the profile identity.
2. Choose the source and final posting levels.
3. Enter a source-to-house driver when the source is shipment or container.
4. Enter a house-to-item driver when the final level is `PO_SCHEDULE_LINE`.
5. Set the effective period and choose `BLOCK` or `EQUAL` as the missing-driver policy.
6. Optionally set a quantity UOM, adapter-specific settings JSON, and version notes.
7. Save the draft and select **Publish** after review.

The driver fields are allocation bases such as weight, volume, quantity, or value. The profile combines those bases into a reusable two-stage policy. Calculation determines the source amount first; allocation distributes it without recalculating it.

### Use The Profile

Select the published profile from a component's **Allocation profile** field. Rate entries, contract lines, aliases, or transaction lines can apply more specific allocation references. The selected profile and version are snapshotted into charge provenance.

## Business-Date Profiles

Open **FX & dates**. The workspace opens on **Business dates** and shows profile versions plus assignment scopes.

### Create And Publish

1. Select **New** and enter the profile identity.
2. Add date steps in fallback order. The first available date wins at runtime.
3. Optionally constrain the version with effective-from and effective-to dates.
4. Save the initial draft.
5. Select **Publish**.

Supported date keys are presented as a controlled list, including actual/planned departure, arrival, house bill issue, flight dates, airway-bill execution, manual line date, and document date.

### Assign A Profile

Assignments are available only after a profile has a published version.

1. Select **Assign** in the profile inspector.
2. Choose `GLOBAL`, `COMPANY`, `CUSTOMER`, `VENDOR`, `FORWARDER`, or `CARRIER`.
3. Provide a numeric scope ID for non-global assignments.
4. Select ocean-house or air-house shipment scope.
5. Set priority. Lower numbers win among matching assignments.
6. Save the assignment.

Use component policy `INHERIT_PROFILE` to select an assignment at runtime. Use `PROFILE_OVERRIDE` when one component must always use a specific profile. Removing an assignment deletes that scope binding; it does not delete the profile or historical provenance.

## FX Rates

Open **FX & dates**, then select **FX rates**.

1. Select **New rate**.
2. Select a source already represented in the register, or enter the numeric source ID when the register is empty.
3. Enter different three-letter source and target currencies, an ISO rate date, a positive directional rate, rate type, and conversion method.
4. Save the rate. Select a row to inspect or edit it.
5. Use **Deactivate** to make an obsolete rate unavailable to new resolutions while retaining it for audit.

FX sources themselves remain API-maintained. The UI derives source choices from loaded rates; use `/fx-rate-sources` through Swagger or an integration when creating the first non-seeded source.

## Rate Books

Open **Rate books** to manage pricing tables grouped by stable rate-book code.

1. Select **New rate book** and choose the single charge component priced by the book. The component is fixed for the family.
2. Choose **Row columns**. These controlled columns determine which lane, mode, equipment, commodity, service, scale, validity, profile, override, and active custom-dimension values appear on every row.
3. Add rows. Use the dropdowns for controlled values, profile selectors for overrides, and date pickers for effective dates.
4. Save the book in `DRAFT` status.
5. Edit the draft while it is under review. The UI sends its `lock_version` to prevent a stale overwrite.
6. Select **Publish draft** to make that version available to contracts and rating.
7. Select **New draft** from an existing version for later pricing changes.
8. Inspect the real version history; published and retired versions are immutable.

Every fixed rate row requires `rate_amount`; percentage rows require `rate_percent` and receive their monetary base from quote context or a calculation-template subtotal. Basis and charge context inherit from the header component unless their override columns are selected. Removing a row column also removes its values from the saved payload, so hidden dimensions cannot continue affecting matching. Contracts cannot release against an unpublished rate-book version.

## Caller Mappings

Open **Caller mappings** when more than one caller application or schema supplies rate applicability attributes.

1. Use **Dimensions** to inspect locked system dimensions or create a custom canonical dimension with a stable code, data type, optional allowed values, and case-sensitivity rule.
2. Use **Profiles** to create a mapping for one caller-system code and schema version.
3. Add mappings from caller paths, such as `shipment.deliveryZone`, to canonical dimensions. Mark genuinely mandatory attributes as required; use defaults and value maps only when they are part of the integration contract.
4. Preview representative raw JSON and verify both custom `dimension_values` and built-in standard fields before the caller sends production quotes.
5. Select the custom dimensions as columns on each applicable rate-book family and populate row values.

Do not create a dimension for every caller field. A canonical dimension is appropriate only when it has stable commercial meaning and participates in row matching. Formula factors belong in calculation inputs, boolean template gates belong in quote context, and operational dates belong in typed date values. See [Caller attribute mapping](caller-attribute-mapping.md) for request examples and lifecycle rules.

## Calculation Templates

Open **Calculation templates** when a contract needs more than one charge component.

1. Select **New template** and enter a stable code and name.
2. Add ordered steps. Each step selects a component, relationship role, and optional rate book. The rate-book dropdown shows only books for that component.
3. Optionally set a subtotal key, choose whether the result is added to that subtotal, set a boolean quote-context precondition key, or mark output as statistical.
4. Save and edit the draft, then select **Publish** after every referenced rate book is published.
5. Use **New draft** for later changes; published versions remain immutable.

A rate book answers "how much for this one component?" A calculation template answers "which components run, in what order, and which rate book prices each one?" Subtotal keys accumulate eligible earlier steps and provide the current monetary base for later percentage steps. Turn off **Add result to subtotal** when a percentage charge must remain in commercial payer/payee totals but must not increase the base read by later percentage steps. **Statistical output only** has a different effect: it excludes the line from commercial totals and from subtotal accumulation.

## Contracts

Open **Contracts** to connect published pricing to a caller-system party. A released contract is eligible only when its role, typed party IDs, dates, and optional route applicability match the quote request.

1. Select **New contract** and enter a stable contract number, name, and `PAYEE` or `PAYER` role.
2. Select the party type and enter the numeric party ID used by the caller system. This ID participates in matching; payer/payee reference text is descriptive only.
3. Set the validity period, currency, and contract selection priority. Lower numbers take precedence.
4. Select a published **Default calculation template**. It runs once and does not require contract rows.
5. Add **Conditional template routes** only when applicability conditions must select a different published template.
6. Use **Legacy direct component pricing** only for a contract that prices components directly rather than executing a template.
7. Save the draft, review it, then select **Release**. Draft contracts do not match quote requests.

A template route contains conditions and a template reference, but no charge component. Calculation-template steps produce the components and rate-book rows determine applicable prices. If two routes or two contracts remain equal after priority and specificity comparison, the API rejects the request as ambiguous instead of selecting the first stored record.

## Quote Testing

Open **Quotes** to exercise the persisted quote workflow without writing a separate caller application.

1. Select **New quote** or **Upload JSON**. The repository includes `examples/road-quote-request.json` as a road-freight fixture.
2. Enter the same numeric party ID used by a released contract, along with the lane and other matching attributes.
3. Supply standard quantities plus any profile factor inputs. Global `calculation_inputs` apply to every component; `component_calculation_inputs` override them for one component code.
4. Supply operational dates under **Typed dates**. Date profiles choose from these caller-provided values by priority.
5. Save the draft and select **Submit**.
6. Select **Determine contracts** to inspect eligible contracts before calculation.
7. Select **Rate**, then **Rank**. Select an option to inspect every charge line and its source contract, contract line, rate book/row, and calculation template/step.
8. Select **Award** on the chosen option to create the downstream charge documents.

`source_object_type` and `source_object_id` identify the caller's own business object; they do not select a LedgerFlow profile or template. Contract matching determines the executable pricing configuration from party and applicability fields.

Allowed typed date identifiers are `DOCUMENT_DATE`, `MANUAL_LINE_DATE`, `SHIPPED_ON_BOARD_DATE`, `SHIPMENT_ACTUAL_DEPARTURE_DATE`, `SHIPMENT_PLANNED_DEPARTURE_DATE`, `SHIPMENT_ARRIVAL_DATE`, `HOUSE_BILL_ISSUE_DATE`, `ACTUAL_FLIGHT_DEPARTURE_DATE`, `AWB_EXECUTION_DATE`, `ESTIMATED_FLIGHT_DEPARTURE_DATE`, `ROAD_ACTUAL_PICKUP_DATE`, `ROAD_PLANNED_PICKUP_DATE`, `ROAD_ACTUAL_DELIVERY_DATE`, `ROAD_PLANNED_DELIVERY_DATE`, and `CMR_ISSUE_DATE`. The UI presents this as a dropdown and the OpenAPI schema is authoritative for integrations.

## Charge-Document Execution

Open **Charge documents** after awarding a quote. The workspace loads the complete document rather than relying on the shallow list result.

1. Select a charge line to inspect calculation, allocation, date, FX, and immutable JSON snapshots.
2. For quote-derived lines, inspect the linked quote-option line to see the exact contract/line, rate book/row, and calculation template/step used.
3. Use **Set status** to move among `ESTIMATED`, `ACCRUED`, `ACTUAL`, and `DISPUTED`. A disputed document cannot be approved.
4. Select **Refresh checks** to reload the authoritative approval checks from the API. Approval is disabled when status is ineligible or a calculation/allocation state is pending or failed.
5. Select **Approve**. Approval locks the document and copies each line's actual amount, or expected amount when actual is absent, to `approved_amount`.
6. Select **Export** after approval. The result dialog shows the stable export number, target, status, and complete payload. A repeated export returns the existing batch.
7. Select **Reverse** from `APPROVED` or `EXPORTED` and enter a mandatory reason. Reversal preserves the document and audit history.
8. Select **Delete** only for an editable direct/manual document created in error. The API rejects deletion when the document is quote-controlled, derived, linked to invoices/matches/commitments, approved, exported, or reversed.

The default export target is `INTERNAL_LEDGER`: LedgerFlow stores and returns the JSON export batch. It does not prove delivery to an ERP, billing system, ledger, or event bus. A production adopter must wire the `FinancialExportAdapter` seam or replace the default service composition.

Quote-derived document lines are source-controlled and cannot be edited or deleted in this workspace. Their provenance remains linked through `source_quote_option_line_id`. Direct/manual document line maintenance remains available through the API where quotation policy and lifecycle locks permit it.

In **Invoices**, select **Delete** to remove an incorrectly captured invoice and its reconciliation results. The linked charge document remains. Invoice deletion is disabled after that document is approved, exported, or reversed.

## Version Lifecycle

Versioned profiles, rate books, and calculation templates use the same lifecycle:

```text
Create profile -> Draft version -> Review/edit -> Publish -> Retired by later publication
```

- Profile header fields can be edited independently of version content.
- Draft versions can be edited.
- Published versions cannot be edited.
- Publishing a newer version retires the previous published version.
- Profiles and versions are retained for audit; there is no destructive profile delete action.

## Authorization

The API requires a bearer principal for every administration request. The default policy adapter verifies that a principal exists but deliberately does not impose an adopter-specific role model. A production deployment should map roles/scopes to the `charge.*` actions documented by the route handlers.

Typical UI operations require list/read actions plus:

| Workflow | Action families |
| --- | --- |
| Components | `charge.components.create`, `update`, `delete` |
| Calculation profiles | `charge.calculation_profiles.create`, `update`, `versions.create`, `versions.update`, `versions.publish` |
| Allocation profiles | `charge.allocation_profiles.create`, `update`, `versions.create`, `versions.update`, `versions.publish` |
| Business-date profiles | `charge.business_date_profiles.create`, `update`, `versions.create`, `versions.update`, `versions.publish` |
| Date assignments | `charge.business_date_profiles.assignments.create`, `update`, `delete` |
| FX rates | `charge.fx_rates.create`, `update`, `deactivate` |
| Pricing dimensions | `charge.pricing_dimensions.create`, `update`, `delete` |
| Caller mapping profiles | `charge.caller_mapping_profiles.create`, `update`, `delete`, `preview` |
| Rate books | `charge.rate_books.create`, `workspace.update`, `versions.create`, `publish` |
| Calculation templates | `charge.calculation_templates.create`, `workspace.update`, `versions.create`, `publish` |
| Contracts | `charge.contracts.create`, `workspace.read`, `workspace.update`, `release` |
| Quotes | `charge.quote_requests.create`, `list`, `workspace.read`, `workspace.update`, `determine_contracts`, `rate`, `rank`, `award` |
| Charge documents | `charge.charge_documents.list`, `workspace.read`, `workspace.update`, `delete`, `approve`, `post_export`, `reverse` |
| Invoices | `charge.invoices.list`, `workspace.read`, `workspace.update`, `match`, `delete` |

The UI is not a security boundary. The API policy adapter must enforce the final authorization and tenant scope.

## Troubleshooting

- **Create/edit buttons are disabled:** the UI is still in demo mode. Connect a live API.
- **A profile is missing from a component selector:** publish a version first.
- **An assignment cannot be created:** publish the selected business-date profile first.
- **Allocation validation fails:** shipment/container sources require a source-to-house driver; PO schedule-line posting requires a house-to-item driver.
- **A published version cannot be edited:** create a new draft version. This is intentional audit behavior.
- **No contract matches a quote:** release the contract, use the same party type and numeric ID, and compare line applicability and validity dates with the quote.
- **A calculation profile reports a missing factor:** provide its resolver code in global calculation inputs or in the selected component's calculation inputs.
- **Approve is disabled:** refresh the checks, resolve pending/failed calculation or allocation states, and move a disputed document to an eligible mutable status.
- **Export is disabled:** approve the document first. Export is intentionally available only from `APPROVED` or idempotently from `EXPORTED`.
- **A request returns 401/403:** verify token issuer, audience, expiry, claims, and policy-adapter rules.
- **A request is blocked by the browser:** add the exact UI origin to `CORS_ALLOWED_ORIGINS`.
