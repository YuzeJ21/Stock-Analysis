# Company Workbench Answer-First Design

## Purpose

Company Workbench should show the selected company's usable research answer before technical lane-coverage cards. The current route renders two selected-ticker coverage cards between the `Selected Company` heading and the existing report renderer. Those cards are truthful, but they delay the report's compact supported, withheld, and next-action answer. This slice changes presentation hierarchy only; it does not change report construction, readiness, coverage, data, routes, or evidence.

## Product Contract

The Company Workbench route will render in this order:

1. Personal Research workspace header, review path, and `Selected Company` heading.
2. One collapsed `Advanced: selected-company lane coverage` section containing the existing selected-ticker coverage cards.
3. The unchanged single-stock report renderer, whose compact selected-company answer remains the first expanded research content.
4. The existing route-level Advanced Evidence section and research-change evidence drawer.

The collapsed section remains visible as a technical-evidence affordance, but its cards do not occupy the default first view. The report continues to fail closed for missing data and independently presents what is usable, withheld, changed, uncertain, and next.

## Architecture

`src/dashboard.py` remains the route-composition owner. `render_company_workbench()` will wrap the existing `focused_ticker_coverage_cards(coverage, ticker)` rendering call in a collapsed Streamlit expander immediately before the existing `render_single_stock_report()` call. No helper signature, provider call, session-state key, query parameter, report section, or navigation mapping changes.

`tests/test_research_mode_dashboard_contract.py` will protect the route order and collapsed state. `src/public_performance_gate.py` will add the visible Advanced label to the Company Workbench full-settle marker contract, and `tests/test_public_performance_gate.py` will protect that marker set.

## Failure And Boundary Behavior

- Missing or unmatched ticker coverage still produces the existing blocked cards inside Advanced.
- The report does not infer coverage when the expander is closed.
- Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, and calibration remain independent.
- Candidate context cannot modify a scenario, readiness state, or trusted evidence.
- Empty valuation, catalyst, outcome, or coverage evidence stays empty or blocked.
- The change writes no data and creates no generated report artifact.

## Documentation

`docs/PERSONAL_RESEARCH_MODE.md` will document the answer-first Company Workbench order. `docs/DASHBOARD_QA.md` will record desktop and phone first-view evidence. `ROADMAP.md` will record the verified local workflow-hardening slice without changing external source, hosting, pilot, or calibration gates.

## Verification

The route-order and performance-marker tests must fail against the current expanded-card composition before implementation and pass afterward. Focused route/workspace tests, the full repository suite, dashboard smoke, research render smoke, the 48-sample commercial performance gate, public wording, public check, pilot readiness, diff hygiene, whitespace checks, and staged hygiene remain required. Live review must cover `1280x720` and `390x844`, keep the new Advanced section closed, and show no horizontal overflow. Screenshots, timing JSON, CSV, JSON, report, and sample-report churn remain excluded.
