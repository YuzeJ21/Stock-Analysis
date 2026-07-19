# Personal Research Evidence Detour Continuity Design

## Purpose

Personal Research Mode has four healthy primary routes: Research Desk, Discover, Company Workbench, and Monitor. Data Health and Proof History are intentionally secondary evidence routes under Advanced.

The current Company Workbench Advanced Evidence links break workspace continuity: Data Health opens Operator mode and Proof History opens Public mode. Both evidence pages already support Personal Research mode, including the research header and restricted non-operator presentation, but the existing links do not use that capability. The pages also state that the user should return to Company Workbench without exposing a direct return action.

This slice keeps evidence inspection inside Personal Research mode and makes the detour explicitly reversible without adding routes, changing data, or moving technical evidence into the primary research answer.

## Audit Evidence And Limits

Current AppTest render smoke passed for Research Desk, Discover, Company Workbench, and Monitor. Source and contract inspection confirmed:

- all four primary routes render the research-only header and one next action;
- Company Workbench keeps lane coverage and evidence links under collapsed Advanced sections;
- `research_path_options` already supports Data Health and Proof History as active evidence detours inside Personal Research mode;
- research-mode Data Health and Proof History already render a Personal Research header and use the non-operator presentation;
- `advanced_evidence_links` currently emits `mode=operator` for Data Health and `mode=public` for Proof History;
- neither evidence detour renders a direct return action.

No new screenshots are permitted by the active continuation contract. This is therefore a route-continuity and render-contract audit, not a screenshot-based visual or accessibility audit. Visual spacing, focus order, contrast, and assistive-technology behavior remain outside this slice.

## Approaches Considered

### 1. Same-mode evidence detour with a direct return action — selected

Change both Advanced Evidence links to `mode=research`. On research-mode Data Health and Proof History, show one direct return link immediately after the research header. Preserve the selected ticker and reopen Company Workbench with `open=1`.

This uses existing routes and presentation boundaries, keeps operator commands out, and provides a clear reversible path.

### 2. Same-mode evidence detour without a return action

Change only the Advanced Evidence URLs and rely on the sidebar route rail to return. This is smaller but leaves the page's stated next action without a matching control and is weaker on phone-sized navigation.

### 3. Keep cross-mode routing and explain the switch

Add copy warning that Data Health opens Operator mode and Proof History opens Public mode. This preserves existing URLs but keeps an unnecessary workspace switch and exposes a more complex mental model.

## Architecture

### Research evidence links

`advanced_evidence_links(ticker)` remains a pure read-only helper. Both URLs use `mode=research`:

- `?mode=research&page=data-health&ticker=<ticker>`;
- `?mode=research&page=proof-history&ticker=<ticker>`.

Ticker values remain uppercased and URL-encoded. Empty tickers omit the ticker query parameter.

### Return destination

Add a pure `research_evidence_return_link(ticker)` helper:

- with a ticker, return `Return to Company Workbench` and `?mode=research&page=company-workbench&ticker=<ticker>&open=1`;
- without a ticker, return `Return to Research Desk` and `?mode=research&page=research-desk`.

The helper returns label, href, and purpose. It writes no state and never infers a ticker.

### Evidence-page integration

When Data Health or Proof History renders in Personal Research mode:

1. render the existing research workspace header;
2. render the return link as the one primary action matching the header guidance;
3. render the existing evidence page unchanged.

Public and Operator modes remain unchanged. The sidebar still includes the active evidence route plus the four primary Personal Research routes.

## Behavior And Boundaries

- No new page, route alias, session state, persistence layer, or data mutation.
- No readiness, source, valuation, catalyst, outcome, consensus, forecast, backtest, or calibration state changes.
- Data Health remains a secondary Advanced evidence route and retains its non-operator presentation in Personal Research mode.
- Proof History remains evidence review only and cannot refresh or unlock data.
- Candidate context remains separate from trusted evidence.
- The return link is navigation only; it does not record a review outcome or mark evidence resolved.
- Research-only wording remains visible on both detours.

## Failure Behavior

- Missing ticker: return to Research Desk; do not invent a company.
- Encoded ticker characters: preserve safe URL encoding.
- Directly opened evidence route: render the same return action from query state.
- Unknown or missing evidence: preserve the existing fail-closed evidence page; navigation remains available.

## Testing

Test first:

1. Advanced Evidence links remain in `mode=research` and preserve encoded ticker state.
2. The return-link helper chooses Company Workbench for a supplied ticker and Research Desk otherwise.
3. Research-mode Data Health and Proof History render the return link after the workspace header and before evidence content.
4. Public and Operator routing remain unchanged.
5. AppTest render smoke covers both evidence detours in addition to the four primary routes.
6. Full dashboard, public, commercial-beta, pilot, whitespace, and hygiene gates remain green except for the already-truthful stale-readiness pilot block.

## Completion Criteria

- Company Workbench Advanced Evidence does not switch workspace modes.
- Both evidence detours expose one direct return action.
- Selected ticker context survives the round trip.
- No generated CSV, JSON, report, sample-report, screenshot, timing, or bytecode artifact changes.
- Documentation continues to describe Data Health and Proof History as secondary Advanced evidence, not primary Personal Research destinations.
