# Clean Company Workbench release evidence

Date: November 7, 2026. Baseline: `86434b337c036fb3a88eb4a1e2366f6ee0e861c4`.

## Delivered scope

- A stable five-section company rail and one company heading, followed by four scoped observations and a financial chart/table.
- Annual and direct-quarter financial views with metric selection, explicit gaps, period evidence and separately labelled cumulative cash flow. Mixed cash-flow definitions remain visible in table cells and cannot form one trend.
- Named access to Business Trend, Scenario Lab, sensitivities, Peer Read-Through, Valuation Methods, Forward View, catalysts, Decision Lab, authoring and the HTML Research Brief. Saved models retain their existing identity and input requirements.
- Monitor returns restore the exact captured profile/ticker/online-CIK or saved/receipt navigation key. Drafts, scenario inputs and confirmation/action state are not overwritten.
- A matching synthetic English demo, current README/walkthrough/Featured guidance, and a replacement synthetic screenshot.

## Automated evidence

Local live observations and screenshots remain outside Git under `/tmp/stock-clean-live-browser`.

- Baseline Workbench/answer tests: 58 passed.
- New financial presentation checks cover source validation, identity isolation, mode boundaries, immutable inputs, mixed cash-flow definitions and separately qualified EPS.
- Workspace/review/navigation preservation checks: 178 passed.
- Desktop/phone demo, source failure, exact-pair Monitor, state retention and control-contrast regression suite: 24 passed.
- Independent review found two presentation-boundary issues; both were fixed and checked. A subsequent reproduced Monitor section-state conflict was fixed without weakening the return assertions.
- Live AMD supports a bounded annual-P/E reference comparison. Live QCOM retains a visible insufficient-reference gap, with explicit exclusions. These checks do not establish complete industry or company coverage.
- The broad repository run executed 9,071 cases: 9,002 passed, three skipped, and 66 failed. The failures were obsolete UI/document assertions and cascading form-state contamination from partially mocked unit fixtures. All 66 were subsequently covered by passing targeted reruns; this is a combined verification record, not a claim that the first full command was green.
- Final combined state-isolation regression: 167 passed. Final documentation, source-boundary and performance-contract tests: 144 passed. The failed-check rerun also passed 61 cases; the remaining cases were verified in the targeted groups. The two stale browser wait-target checks passed after correction. Assertions for privacy, source rights, read-only behavior, accessibility and exact-pair scope remain in place.
- Final live AMD/QCOM checks: two passed. At 390×844, both complete price and peer cards fit inside the first viewport; each company navigation control is 44px, with no horizontal page overflow. AMD had six qualifying references; QCOM had zero of 12 checked candidates and retained the comparison gap.
- Updated initial-route performance contract: 16 desktop/phone cold/warm samples passed with the original thresholds. This measures the lazy workspace frame, not provider refresh latency or the completeness of online evidence. It performs no source refresh or automatic tool reveal.
- All 78 tracked data/configuration files were compared byte-for-byte with the baseline and were unchanged.

The final review found no remaining actionable code issues. The GitHub workflow is pull-request triggered; a direct main sync does not create a hosted CI run. Local verification and the Pages build are separate evidence.

## Published verification

- Tested source commit: [`883ed121f06b278daaa701fad669644913703dc6`](https://github.com/YuzeJ21/Stock-Analysis/commit/883ed121f06b278daaa701fad669644913703dc6). A fresh post-commit presentation, source-boundary, navigation and performance-contract group passed 81 tests.
- Pages commit: [`717263f202698fcaec27ed113659906ce9420a17`](https://github.com/YuzeJ21/Stock-Analysis/commit/717263f202698fcaec27ed113659906ce9420a17), built successfully from that source. Both public HTML responses returned HTTP 200 and matched the reviewed build bytes by SHA-256.
- The hosted [English Overview](https://yuzej21.github.io/Stock-Analysis/#overview) was inspected in the browser. Three eligible peers produce the sample comparison; two retain the explicit comparison gap. “View why” opens the matching evidence and exclusions. The separately dated [AMD case](https://yuzej21.github.io/Stock-Analysis/amd.html) matches its reviewed build and retains its market-data hold.
- Current synthetic screenshot: [English company research demo](assets/english-company-research-demo.png). Real live screenshots remain local.
- This verification follow-up changes documentation only; it does not alter the tested application or generated demo.

## Data and distribution boundary

No canonical data or source-rights configuration is changed by this package. Refresh remains explicit, and changing sections reuses loaded observations. The same-day completed-close requirement, annual reported diluted EPS, 35-day fiscal window and minimum three qualified references are unchanged.

The public screenshot and interactive demo use synthetic observations. The separate AMD public case retains its dated SEC-derived evidence and its market-data comparison hold. Real live price/provider observations are not added to the repository or Pages output.

GitHub Pages hosts the static demonstration, not the full Streamlit workspace. Full-workspace hosting, operated commercial data rights and independent user validation remain separate gates.

## Reproduce

```sh
make test
make dashboard-smoke research-dashboard-render-smoke public-wording-check
make commercial-beta-check staged-hygiene-check
```

Opt in to live checks against an already running local app:

```sh
STOCK_LIVE_WORKBENCH_BASE_URL=http://127.0.0.1:8530 \
STOCK_LIVE_WORKBENCH_OUTPUT_DIR=/tmp/stock-clean-live-browser \
python3 -m pytest -q tests/test_live_company_workbench_browser.py
```

The live checks accept localhost only and reject output paths inside the repository. They refresh read-only observations, visit every company section, inspect source/exclusion details and check desktop/phone layout. They do not save research records or change canonical data.

Build both public artifacts because the AMD case shares the demo stylesheet:

```sh
python3 -m scripts.build_company_demo --output /tmp/stock-clean-public/index.html
python3 -m scripts.build_amd_demo --output /tmp/stock-clean-public/amd.html
```

## Next executable stage

Review one named peer relationship beyond mechanical industry screening. Explain differences in business mix, growth, margins, capital intensity and fiscal periods only when supported by comparable sources. Keep QCOM's insufficient-peer gap visible and avoid treating an annual-P/E premium as an intrinsic-value conclusion.
