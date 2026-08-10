# UI Administration Guide

This guide covers the master-data workflows available in the LedgerFlow Flutter web application. Read [Core concepts](core-concepts.md) for the domain model and [Authentication](authentication.md) before connecting the UI to a production API.

## Connect The UI

The deployed UI starts in a read-only demo workspace. Demo data is intentionally local to the browser build and is not written to the database.

1. Select **Connect API** in the top bar.
2. Enter the API base URL, such as `http://localhost:8000`.
3. Enter a bearer token issued for that API.
4. Confirm that the sidebar status changes from **Demo workspace** to **Live API**.

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
2. Choose **Row columns**. These controlled columns determine which lane, mode, equipment, commodity, service, scale, validity, profile, and override values appear on every row.
3. Add rows. Use the dropdowns for controlled values, profile selectors for overrides, and date pickers for effective dates.
4. Save the book in `DRAFT` status.
5. Edit the draft while it is under review. The UI sends its `lock_version` to prevent a stale overwrite.
6. Select **Publish draft** to make that version available to contracts and rating.
7. Select **New draft** from an existing version for later pricing changes.
8. Inspect the real version history; published and retired versions are immutable.

Every fixed rate row requires `rate_amount`; percentage rows require `rate_percent` and receive their monetary base from quote context or a calculation-template subtotal. Basis and charge context inherit from the header component unless their override columns are selected. Removing a row column also removes its values from the saved payload, so hidden dimensions cannot continue affecting matching. Contracts cannot release against an unpublished rate-book version.

## Calculation Templates

Open **Calculation templates** when a contract needs more than one charge component.

1. Select **New template** and enter a stable code and name.
2. Add ordered steps. Each step selects a component, relationship role, and optional rate book. The rate-book dropdown shows only books for that component.
3. Optionally set a subtotal key, a boolean quote-context precondition key, or mark output as statistical.
4. Save and edit the draft, then select **Publish** after every referenced rate book is published.
5. Use **New draft** for later changes; published versions remain immutable.

A rate book answers "how much for this one component?" A calculation template answers "which components run, in what order, and which rate book prices each one?" Subtotal keys accumulate earlier non-statistical steps and can provide the monetary base for later percentage steps.

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
| Rate books | `charge.rate_books.create`, `workspace.update`, `versions.create`, `publish` |
| Calculation templates | `charge.calculation_templates.create`, `workspace.update`, `versions.create`, `publish` |

The UI is not a security boundary. The API policy adapter must enforce the final authorization and tenant scope.

## Troubleshooting

- **Create/edit buttons are disabled:** the UI is still in demo mode. Connect a live API.
- **A profile is missing from a component selector:** publish a version first.
- **An assignment cannot be created:** publish the selected business-date profile first.
- **Allocation validation fails:** shipment/container sources require a source-to-house driver; PO schedule-line posting requires a house-to-item driver.
- **A published version cannot be edited:** create a new draft version. This is intentional audit behavior.
- **A request returns 401/403:** verify token issuer, audience, expiry, claims, and policy-adapter rules.
- **A request is blocked by the browser:** add the exact UI origin to `CORS_ALLOWED_ORIGINS`.
