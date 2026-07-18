# Discover Answer-First Design

## Purpose

Discover should let a researcher choose a readiness-backed company immediately after reading the route header. The current route renders focused-cohort and lane-coverage cards before the selector, which pushes the search control and company actions below the first desktop viewport. This slice changes presentation order only; it does not change cohort eligibility, readiness, ranking, data, routes, or company links.

## Product Contract

The Discover route will render in this order:

1. Personal Research workspace header with freshness, research-only boundary, and one next action.
2. `Which stock can I review?` heading and the existing readiness-backed selector.
3. One collapsed `Advanced: cohort readiness context` section containing the existing focused-cohort scope and lane-coverage cards.

The selector continues to limit rows to the deterministic focused cohort and continues to open Company Workbench in Personal Research mode. The reordering must not create a score, recommendation, expected-return ranking, inferred coverage, or trusted evidence.

## Architecture

`src/dashboard.py` remains the composition owner. The change reorders existing calls inside the Discover branch of `main()` and wraps the existing `focused_cohort_cards` and `focused_cohort_coverage_cards` output in one collapsed Streamlit expander. No helper signature, data contract, persisted artifact, query parameter, or navigation mapping changes.

`tests/test_research_mode_dashboard_contract.py` owns the source-level route contract. A new regression test will require the selector heading and selector renderer to appear before the collapsed cohort context, and require both existing card groups to remain inside that context.

`src/public_performance_gate.py` owns the real-browser visible-marker contract. Discover's full-settle markers must use visible answer-first text (`Search this review queue` and the collapsed Advanced label), not content hidden inside the closed cohort expander. `tests/test_public_performance_gate.py` protects that marker set.

## Failure And Boundary Behavior

- An empty focused cohort still produces an empty selector and truthful unavailable/blocked cohort context.
- The route does not broaden to the master universe when the cohort is empty.
- Cohort status and gated-lane counts remain available under Advanced; they are not removed or combined.
- Company links continue to target `?mode=research&page=company-workbench`.
- Technical evidence remains collapsed by default at desktop and phone widths.
- The change writes no data and creates no generated report artifact.

## Documentation

`docs/PERSONAL_RESEARCH_MODE.md` will document that Discover is selection-first and keeps cohort context under Advanced. `docs/DASHBOARD_QA.md` will record the first-viewport acceptance contract. `ROADMAP.md` will record the verified local workflow-hardening slice without changing the external source, hosting, pilot, or calibration gates.

## Verification

Verification requires both new regression tests to fail before implementation and pass afterward. Focused route/workspace tests, the full repository suite, dashboard smoke, research render smoke, the 48-sample commercial-beta performance gate, public wording, public check, pilot readiness, diff hygiene, whitespace checks, and staged hygiene remain required. Generated CSV, JSON, report, sample-report, screenshot, and timing churn remains excluded.
