# Dashboard QA Notes

This file records lightweight browser QA evidence for public-facing dashboard polish.

## 2026-06-06 Main Gap Fix Pass

Checked pages:

- Home: confirmed the Current Data Coverage section renders with the latest local readiness snapshot and copy-only proof commands.
- Single-Stock Report: confirmed the page renders with ready, blocked, excluded, and copy-only guidance.
- Value / Re-rating: confirmed the page renders valuation readiness language without overclaims.
- Data Health: confirmed the page renders proof workflow guidance and keeps missing context locked.

Screenshots:

- [Home coverage QA](assets/dashboard-qa-home-coverage.png)
- [Data Health QA](assets/dashboard-qa-data-health.png)

Boundary checked:

- No broker integration, order execution, auto-trading, or direct buy/sell instruction language appeared in the checked pages.
- Commands remain copy-only; the dashboard does not run refreshes or imports from the UI.

## 2026-06-07 Public Product Flow Pass

Checked pages:

- Home: confirmed the visitor route shows `Review one stock`, `Improve data coverage`, and `Explore ready names`, plus a trusted-data pilot path for improving 5-10 companies first.
- Single-Stock Report: confirmed a local `NVDA` preview renders the visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, then `Best Review Path` before detailed tabs.

Boundary checked:

- `Best Review Path` correctly routes the DCF/peer-ready `NVDA` example to review DCF, peers, and source readiness instead of sending it back to price coverage.
- Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.

## 2026-06-07 Follow-Up Product Copy Pass

Checked pages and reports:

- Sidebar: confirmed the main navigation control reads `Choose your path`, not internal review-control language.
- Data Health: confirmed first-screen wording uses checklist/review-path language before advanced command detail.
- Value / Re-rating: confirmed the broad valuation input count is labeled separately from exact company DCF-ready counts.
- Portfolio Review: confirmed table helper copy says `next-step context` instead of internal-tool operational wording.
- Trusted Data Pilot: confirmed the read-only pilot prints a company starter set and separates `QQQ` / `SMH` as ETF/index monitor examples, not operating-company DCF targets.
- `outputs/stock_reports/a.md`: confirmed standalone DCF peer wording no longer repeats `DCF assumptions and sensitivity`.

Boundary checked:

- The changes stay copy-only and research-only.
- No generated CSV/JSON churn was published with the UI copy pass.

## 2026-06-10 Public Navigation And Data Strategy Pass

Checked pages and docs:

- Sidebar: confirmed the main navigation control reads `Choose your path` and exposes `Review one stock`, `Improve data coverage`, and `Explore ready names` before advanced pages.
- Sidebar: confirmed detailed pages remain available under `Advanced pages`, so deep research views are not removed.
- Home: confirmed the first-run proof trail shows copyable commands for the dashboard, NVDA ready proof, META blocked proof, QQQ excluded proof, MU peer-limited proof, CRDO fundamentals-gated proof, and the trusted-data pilot.
- Data Strategy: confirmed the Automation Boundary table separates repeatable checks from human-reviewed source judgment.

Boundary checked:

- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.
- Data coverage guidance still requires trusted source rows for fundamentals, peers, earnings, analyst estimates, and valuation inputs.

## 2026-06-10 Trusted Pilot Candidate UX Pass

Checked pages and docs:

- Home: confirmed the first-run proof trail now points visitors to `make trusted-data-pilot-candidates TOP_N=10` before the ticker-scoped trusted-data pilot checklist.
- Home: confirmed the next-step cards describe the candidate list as read-only and keep the ticker-scoped pilot as the follow-up proof loop.
- Portfolio Review: confirmed the page renders plain-language capability and limit cards after Streamlit finishes loading, with review-only wording and no portfolio action instruction.
- Public docs: confirmed the release checklist and LinkedIn brief explain candidate ranking first, then the selected-company evidence loop.

Boundary checked:

- Candidate ranking remains copy-only and read-only; it does not refresh prices, import rows, or change readiness outputs.
- ETF/index examples remain monitor-context demos, not operating-company DCF pilot targets.

## 2026-06-11 Public Route Alignment Pass

Checked pages and assets:

- README: confirmed the Product Tour routes `Explore ready names` directly to `Monthly Picks`.
- Dashboard preview asset: confirmed the visual route copy now says `Explore ready names: Monthly Picks and sample reports`.
- Public checks: confirmed `make public-check` passes after the route and preview alignment.

Boundary checked:

- The route change is navigation copy only; it does not refresh data, import rows, or change readiness outputs.
- The generated Monthly Picks CSV remains local working output and was not committed as part of this QA pass.

## 2026-06-11 Visitor Guide Browser Pass

Checked pages and commands:

- Monthly Picks: confirmed the page renders the new `Reader Guide` with `Open a one-stock report next`, `No automatic conclusion`, and the Data Health path for empty candidate states.
- Single-Stock Report: confirmed the page renders the demo ticker guide for `NVDA`, `META`, `QQQ`, `MU`, `CRDO`, plus optional `A`, `SMH`, and `APLD` before the report button.
- Trusted Data Pilot CLI: confirmed candidate output no longer repeats the `Decision gate` label and still prints read-only source-proof boundaries.

Boundary checked:

- The browser pass used the local Streamlit page only; it did not refresh data, import rows, or change readiness outputs.
- Monthly candidate guidance stays a research queue, not a recommendation list.
- Single-stock demo guidance keeps DCF-ready, blocked, excluded, and standalone DCF examples separate.

## 2026-06-11 Data Health Freshness Routine Pass

Checked pages and docs:

- Data Health: confirmed the `Freshness Routine` section explains a read-only daily/opening routine before any refresh or import step.
- Data Health: confirmed price freshness guidance starts with a capped dry-run command and tells users to inspect generated CSV diffs before a real capped loop.
- Data Health: confirmed fundamentals, peer mappings, earnings, and analyst estimates remain review-required lanes instead of unattended automation targets.
- Public checklist: confirmed the release flow points visitors to Data Health for safe freshness guidance without suggesting daily manual full-universe refreshes.

Boundary checked:

- The freshness routine is copy-only; the dashboard does not execute refreshes, imports, broker actions, or trades.
- This pass documents workflow clarity only; it does not claim new fundamentals, peer, earnings, or analyst-estimate coverage.
