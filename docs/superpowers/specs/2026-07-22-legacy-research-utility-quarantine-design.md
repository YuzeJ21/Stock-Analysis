# Legacy Research Utility Quarantine Design

**Date:** 2026-07-22
**Status:** Approved by the Next-Stage Maturity Program
**Scope:** Legacy compatibility routes and product wording only

## Purpose

The supported product is Personal Research Mode:

```text
Research Desk -> Discover -> Company Workbench -> Monitor
```

The repository also retains older calculation and report surfaces for monthly picks, momentum leaders, portfolio review, value/re-rating, and a final watchlist. They are useful for regression and compatibility work, but their ranked-company, holdings, cost-basis, disposition, and action-like language is outside the supported research workflow. This design prevents those surfaces from being mistaken for current investing capability without deleting compatibility code or rewriting historical outputs.

## Audit Findings

1. The supported Personal Research and Public route rails do not list the legacy pages.
2. Explicit query routes can still preserve an advanced page in Personal Research or Public mode because the explicit page wins after the route rail chooses its safe default.
3. Operator navigation displays legacy page names beside current maintenance and evidence tools without a compatibility label.
4. Monthly Picks renders ordered candidates and track-record context in the primary view. Output tabs can render ranked, portfolio, and watchlist tables without an explicit legacy boundary.
5. `portfolio_review.py`, `monthly_picks.py`, and historical output filenames remain part of deterministic pipeline compatibility. Removing them would create broad migration risk unrelated to the current product workflow.
6. The Research Decision Lab already forbids importing `portfolio_review.py`; its pure composition module does not consume dashboard output frames. Company Workbench loads selected-company evidence independently, but a direct contract test is needed so that isolation cannot regress silently.
7. README and readiness documentation still describe the old outputs as general product capability instead of compatibility-only artifacts.

## Approaches Considered

### Delete legacy calculations and reports

This would remove ambiguity, but it would also break historical report contracts, tests, and operator regression workflows. It is disproportionate to the product-surface problem and is not selected.

### Relabel pages only

This is low effort, but it does not close direct-route leakage and still exposes ranked or position-oriented content on first view. It is insufficient.

### Operator-only quarantine with collapsed compatibility output

This is selected. It preserves deterministic compatibility code while preventing legacy pages from becoming Personal Research or Public product capabilities. The route, navigation label, page boundary, collapsed output, documentation, and isolation tests all reinforce the same contract.

## Quarantined Pages

The immutable quarantine set is:

- `Monthly Picks`
- `Momentum Leaders`
- `Portfolio Review`
- `Value / Re-rating`
- `Final Watchlist`

`Overview`, `Market Direction`, `Single-Stock Report`, `Data Health`, and `Universe Manager` are not included. They remain operator or supported evidence/research surfaces and do not inherently represent portfolio actions or company ranking. Any transaction-like content found inside them must still be removed or separately quarantined.

## Route Contract

- Personal Research mode may open only Research Desk, Discover, Company Workbench, Monitor, Data Health, or Proof History.
- Public mode may open only Home, Stock Selector, Single-Stock Report, Data Health, or Proof History.
- A quarantined explicit deep link resolves to `Research Desk` in Personal Research mode and `Home` in Public mode.
- Operator mode may preserve and open quarantined routes.
- Query parsing keeps historical aliases so old operator links remain usable; access control occurs when resolving the workspace page, not by deleting aliases.

## Operator Navigation And Page Contract

The Operator advanced selector prefixes quarantined pages with `Legacy utility ·`. Canonical page titles remain unchanged internally.

Every quarantined page begins with the exact boundary:

`Legacy research utility — not part of Personal Research Mode`

The boundary explains that the retained view is compatibility-only and cannot provide recommendations, ranking for action, position sizing, transaction direction, readiness, or Decision Lab evidence. Detailed candidate cards, charts, track records, position/cost-basis fields, and tables require expanding `Advanced: legacy compatibility output` and then selecting a separate load checkbox. Rendering occurs only after both deliberate Operator actions, which avoids unsupported nested Streamlit expanders while keeping the default page free of legacy output.

The primary view contains only the legacy boundary and fail-closed availability state. It must not expose a ranked candidate, disposition, position percentage, cost basis, entry/exit zone, or transaction-like action.

## Data And Evidence Boundaries

- No calculation, CSV schema, report filename, readiness state, source record, or canonical data changes in this slice.
- No generated CSV, JSON, report, screenshot, or timing artifact is created or staged.
- Legacy output cannot populate Research Decision Lab lanes, Research Conclusion, Next Research Task, readiness, calibration, or a recommendation.
- Candidate context remains untrusted and cannot alter deterministic forecasts.
- Empty or missing compatibility output stays explicit; it is never fabricated.
- The quarantine does not make retained legacy calculations commercially validated or market-ready.

## Documentation Contract

README, Product Spec, Readiness Model, ROADMAP, and the continuation contract must distinguish:

- the supported Personal Research workflow;
- operator-only legacy compatibility utilities; and
- retained historical output filenames.

Public claims must not describe portfolio review, picks, final watchlists, ranked companies, sizing, or action states as current product features.

## Test And Acceptance Evidence

The slice exits only when direct tests prove:

1. the exact quarantine set and operator labels;
2. Personal Research and Public deep links fail closed to their safe home pages;
3. Operator deep links remain available;
4. quarantined output requires one collapsed legacy disclosure plus explicit load confirmation;
5. Research Decision Lab and Company Workbench do not import or consume legacy portfolio, monthly-pick, or final-watchlist contracts;
6. public wording and no-trading checks remain green;
7. full tests, dashboard render checks, release checks, and hygiene checks pass without staging generated churn.

This evidence proves local product isolation only. It does not prove hosted controls, independent-user comprehension, accessibility, source rights, consensus coverage, calibration, demand, or product-market fit.
