# Dashboard QA Notes

This file records lightweight browser QA evidence for public-facing dashboard polish.

## 2026-06-06 Main Gap Fix Pass

Checked pages:

- Home: confirmed the Current Data Coverage section renders with the latest local readiness snapshot and copy-only unlock commands.
- Single-Stock Report: confirmed the page renders with ready, blocked, excluded, and copy-only guidance.
- Value / Re-rating: confirmed the page renders valuation readiness language without overclaims.
- Data Health: confirmed the page renders unlock workflow guidance and keeps missing context locked.

Screenshots:

- [Home coverage QA](assets/dashboard-qa-home-coverage.png)
- [Data Health QA](assets/dashboard-qa-data-health.png)

Boundary checked:

- No broker integration, order execution, auto-trading, or direct buy/sell instruction language appeared in the checked pages.
- Commands remain copy-only; the dashboard does not run refreshes or imports from the UI.

## 2026-06-07 Public Product Flow Pass

Checked pages:

- Home: confirmed the visitor route shows `Review one stock`, `Explore ready names`, and `Improve data coverage`, plus a trusted-data pilot path for improving 5-10 companies first.
- Single-Stock Report: confirmed a local `NVDA` preview renders `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, then `Best Review Path` before detailed tabs.

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
- Home: confirmed the first-run proof trail shows copyable commands for the dashboard, one proof report, one blocked/excluded example, and the trusted-data pilot.
- Data Strategy: confirmed the Automation Boundary table separates repeatable checks from human-reviewed source judgment.

Boundary checked:

- Commands remain copy-only; the dashboard does not run refreshes or imports and does not connect to external accounts from the UI.
- Data coverage guidance still requires trusted source rows for fundamentals, peers, earnings, analyst estimates, and valuation inputs.

## 2026-06-10 Trusted Pilot Candidate UX Pass

Checked pages and docs:

- Home: confirmed the first-run proof trail now points visitors to `make trusted-data-pilot-candidates TOP_N=10` before the ticker-scoped trusted-data pilot checklist.
- Home: confirmed the next-step cards describe the candidate queue as read-only and keep the ticker-scoped pilot as the follow-up proof loop.
- Portfolio Review: confirmed the page renders plain-language capability and limit cards after Streamlit finishes loading, with review-only wording and no portfolio action instruction.
- Public docs: confirmed the release checklist and LinkedIn brief explain candidate ranking first, then the selected-company evidence loop.

Boundary checked:

- Candidate ranking remains copy-only and read-only; it does not refresh prices, import rows, or change readiness outputs.
- ETF/index examples remain monitor-context demos, not operating-company DCF pilot targets.
