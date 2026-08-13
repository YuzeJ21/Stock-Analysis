# Research Desk Answer-First Design

## Purpose

Research Desk should answer the researcher's weekly questions before showing technical cohort scope and lane coverage. The current route renders four focused-cohort cards before the weekly summary, the four direct research answers, and the Discover action. Those cards are truthful, but they delay the primary review path. This slice changes presentation hierarchy only; it does not change cohort selection, coverage states, weekly-summary derivation, change events, readiness, or navigation.

## Product Contract

The Research Desk route will render in this order:

1. Personal Research workspace header with freshness, research-only boundary, and the Discover next action.
2. `Weekly research summary` and its existing traceable summary cards.
3. The existing four direct answers: what changed, which companies need attention, what is blocked or stale, and what to review next.
4. The existing `Open Discover` primary action.
5. One collapsed `Advanced Evidence` drawer containing the existing focused-cohort cards, cohort-coverage cards, full cohort and coverage frames, weekly rows, and evidence links.
6. The existing research-change evidence drawer.

The cohort cards remain available and unchanged. Closing the drawer does not broaden eligibility, infer lane coverage, or turn a no-change state into proof that no real-world event occurred.

## Architecture

`src/dashboard.py` remains the composition owner. `render_research_desk()` will move the two existing `render_signal_cards(...)` calls from above the weekly summary to the top of the existing collapsed `Advanced Evidence` block. No helper signature, card payload, state calculation, query parameter, or route mapping changes.

`tests/test_research_mode_dashboard_contract.py` will protect the complete source order and confirm that concise and full cohort evidence remain inside Advanced. `src/public_performance_gate.py` will change Research Desk's first-useful marker from the route title to `Weekly research summary` and use only visible answer-first markers for full settle. `tests/test_public_performance_gate.py` will protect that contract.

## Failure And Boundary Behavior

- Empty weekly summaries retain their existing truthful no-traceable-change message.
- Empty or partial cohorts retain their existing blocked or partial cards under Advanced.
- Full company-by-lane rows remain available and are never replaced by an aggregate claim.
- Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, and calibration remain independent.
- Candidate context cannot alter a forecast, readiness state, or trusted evidence.
- The change writes no data and creates no generated report artifact.

## Documentation

`docs/PERSONAL_RESEARCH_MODE.md` will document the Research Desk answer-first order. `docs/DASHBOARD_QA.md` will record desktop and phone first-view evidence. `ROADMAP.md` will record the verified local slice and leave Monitor as the final Stage 1 route audit.

## Verification

The route-order and performance-marker contracts must fail before implementation and pass afterward. Focused route/workspace tests, the full repository suite, dashboard smoke, research render smoke, the 48-sample commercial performance gate, public wording, public check, pilot readiness, diff hygiene, whitespace checks, and staged hygiene remain required. Live review must cover `1280x720` and `390x844`, keep Advanced closed, retain the weekly answer and Discover action, and show no horizontal overflow. Screenshots, timing JSON, CSV, JSON, report, and sample-report churn remain excluded.
