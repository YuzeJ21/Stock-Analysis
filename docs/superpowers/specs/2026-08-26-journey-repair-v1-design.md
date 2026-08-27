# Journey Repair v1 Design

**Status:** Approved by the owner through the Journey Repair v1 goal prompt.

**Implementation base:** local `main` at
`19d59bea64d2a37f69024d60ab195c0b50467d27`.

## Objective

Repair the Personal Research journey so a researcher can discover an
inspectable saved company, open its Company Workbench, detour to Monitor or
Advanced Evidence, and return without losing company context. A cold report
must show a neutral saved-evidence loading state until the authoritative report
payload exists.

This is a presentation and route-state change. It does not change research
calculations, data readiness, source rights, providers, canonical data,
generated artifacts, proof ledgers, or report contents.

## Approved scope

### Discover: evidence access before screen failure

The first Discover answer combines two independently calculated counts:

- saved companies available for evidence review; and
- companies that currently pass the strict screen.

The answer format is:

> `{saved_count} saved companies are available for evidence review; {eligible_count} currently pass the strict screen.`

The saved count comes from the existing readiness-only,
company-only, focused-cohort browser. The eligible count comes from the
existing strict daily research queue. Neither count is hard-coded.

Several alphabetical Company Brief links appear immediately after the answer.
They are evidence-access actions, not a ranking. Search, filters, detailed
readiness rows, strict eligibility detail, and all current blockers remain
available below.

### Monitor: preserve return context without filtering

The selected company is carried to Monitor as `return_ticker`, not `ticker`.
This distinction is visible and semantic:

- Monitor remains the same focused-cohort/workspace follow-up surface.
- `return_ticker` only enables a return action to the selected Company
  Workbench.
- It must not filter Monitor rows, alter counts, or imply a ticker-specific
  monitor.
- A missing, malformed, or unregistered value is removed and ignored.
- A direct Monitor visit without return context behaves exactly as before.

Data Health and Proof History continue using their existing validated `ticker`
context, which already returns to the matching Company Workbench.

### Advanced Evidence: one truthful current-location cue

The four primary Personal Research steps remain Research Desk, Discover,
Company Workbench, and Monitor. Data Health and Proof History do not become
primary workflow steps.

When either evidence page is active, the navigation adds one secondary marker:

- `Advanced Evidence · Data Health`; or
- `Advanced Evidence · Proof History`.

That marker owns the page's sole `aria-current="page"`. No primary step is
marked current at the same time.

### Loading: one neutral state until the final packet

`build_stock_report()` remains the sole authority for the rendered readiness
answer. A cold Single-Stock Report or Company Workbench must not render the
fast saved-readiness summary before the report payload exists.

Before the payload exists, show only the existing neutral loading contract:

- selected ticker;
- saved local review is being prepared;
- no data is refreshed, imported, or fetched from external accounts; and
- the temporary state does not claim that any analysis section is ready or
  blocked.

For a public Single-Stock deep link, keep the route bootstrap visible until
the page has rendered its stable result. For Company Workbench, render the
neutral loading state inside the Company Brief answer slot so the strongest
surface never begins as an empty column.

If report construction fails, show the existing fail-closed error/unavailable
state. Never leave stale optimistic content in the answer slot or evidence
rail.

## State and route contract

| Route | Company state accepted | Meaning |
| --- | --- | --- |
| Discover | none | Search/browse state stays session-local as today. |
| Company Workbench | validated `ticker` | Selected company being reviewed. |
| Monitor | validated `return_ticker` | Return destination only; not a filter. |
| Data Health | validated `ticker` | Existing evidence-lane focus and return context. |
| Proof History | validated `ticker` | Existing proof focus and return context. |

Route canonicalization keeps only the exact allowed keys. Validation uses the
registered local ticker set; invalid context is removed rather than inferred.
Ticker values use the existing URL quoting rules, including symbols such as
`BRK/B`.

## Accessibility and responsive behavior

- Exactly one current-location cue is exposed on every Personal Research or
  Advanced Evidence route.
- The loading panel uses `role="status"`, `aria-live="polite"`, and
  `aria-busy="true"` only while the temporary state is present.
- Return and quick-company actions have ticker-specific accessible names.
- Keyboard focus, focus visibility, reading order, and browser back/forward
  behavior remain testable.
- The current desktop rail and mobile wrapped-grid design are preserved.
- New text must reflow at 390 x 844 without clipping or horizontal overflow.

## Preservation contract

The following remain unchanged and available:

- Discover search, saved presets, filters, strict eligibility, and detailed
  queue evidence;
- Company Workbench's four answer lanes and progressive module gate;
- Monitor's focused-cohort follow-up logic and non-ranking boundary;
- Data Health lane inspection and Proof History raw detail;
- Public, Personal Research, and Operator workspace separation;
- valuation, scenario, thesis, evidence, quarterly trend, report, and offline
  HTML modules;
- all fail-closed readiness, source, rights, freshness, and proof behavior.

## Non-goals

- No new analytics module, route, provider, dataset, cache, or background job.
- No data refresh, import, apply, readiness rebuild, or proof-ledger write.
- No source-rights or GitHub policy change.
- No broad dashboard refactor.
- No ranking, recommendation, expected-return, target-price, transaction, or
  buy/sell language.
- No merge, push, publication, deployment, or hosted-environment change.

## Verification and acceptance

Acceptance requires:

1. Unit/contract tests fail first and then pass for every changed behavior.
2. Discover shows live saved and strict counts with alphabetical quick links.
3. Monitor retains a validated return action while its data remains unchanged.
4. Data Health and Proof History expose one secondary current-location cue.
5. Cold report states show no blank answer area or pre-payload readiness claim.
6. Desktop 1280 x 720 and mobile 390 x 844 browser evidence covers the eight
   states named in the goal prompt.
7. Preservation tests and the complete `make public-check` pass.
8. Protected data, output, proof, readiness, and generated-artifact paths have
   no diff.

> Data readiness first, analysis second, research decision last.
