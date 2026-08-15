# Company Workbench document-first design QA

## Decision and scope

- Final implementation base: `530c297a634c869d9b289bfaa3ccbd25b6fde9c3` (`Unify Workbench brief title`).
- Route and state: default local profile, saved AAPL, light theme, `?mode=research&page=company-workbench&ticker=AAPL`, closed and explicitly opened states.
- Visual contract: grade the selected direction by its document-led Company Brief, four answer lanes, strong evidence-status rail, restrained editorial treatment, responsive hierarchy, preserved functionality, and product-truth boundaries. Pixel identity is not the acceptance standard.
- Browser surface: the required in-app Browser selection was attempted first and returned `Browser is not available: iab`. Per the installed Product Design browser-selection instructions, the final visual and interaction pass used the connected Chrome extension; no standalone Playwright session substituted for this Product Design pass.
- Final browser parameters: 1440 x 1024 CSS pixels, 100% zoom, device pixel ratio 1, viewport screenshot, Chrome, exact loopback route above.

## Source and evidence ledger

| Artifact | State / dimensions | SHA-256 |
|---|---|---|
| `/Users/yjian070/.codex/generated_images/019fe1a2-ef19-73c0-8e1a-069060f28b90/exec-a7444f21-6213-40f5-b4c0-cfb6bcb75797.png` | Selected target, 1487 x 1058 | `0f4105b35445cf11c1397b6e2d5b422a023723be9c828dc43438c8df446f0d7f` |
| `/tmp/company-workbench-design-qa-530c297a/aapl-closed-1440x1024.png` | Final closed AAPL, 1440 x 1024 | `c065f3141d98db60598c99ba8dc9f8e9987f95b368f44c7dfbed66fd3c9a90d0` |
| `/tmp/company-workbench-design-qa-530c297a/aapl-opened-1440x1024.png` | Final opened AAPL, 1440 x 1024 | `05b186533e96b54eaddd0de35012c3d48058b4c6e54c523c3b97c3426adaf1f4` |
| `/tmp/company-workbench-design-qa-530c297a/target-vs-aapl-opened-1440x1024.png` | Same-input full comparison; target normalized to 1440 x 1024 at left, implementation at right; 2898 x 1066 including labels/gutter | `f57ebd7b62eacbd11dda0f43cc6eaaae227cd05659eec718e350e4af0f8ad57e` |
| `/tmp/company-workbench-design-qa-530c297a/target-brief-vs-implementation-brief.png` | Focused primary-brief comparison, 2018 x 566 | `8df42a0736fdfdbc08dbdb80056a2376a33e150ef61411dded15bb885b220fce` |
| `/tmp/company-workbench-design-qa-530c297a/target-rail-vs-implementation-rail.png` | Focused evidence-rail comparison, 1138 x 1033 | `a6ecd97da568fa02cf8895d8431972a0f7897a68c6c99014fcd9628168b7ee94` |
| `/tmp/company-workbench-document-browser.530c297a/results.json` | Six-cell Workbench matrix | `c3b56fcb5930fdf149190f681d40ea94692865b9b447f09e4fbad3766e0d670b` |
| `/tmp/company-workbench-non-workbench.530c297a/results.json` | Research Desk scope-control cell | `1caefcc21e8d3eb99a8dc41fafde3e1082ce1065a75e0259a182535fb352154c` |
| `/tmp/company-workbench-accessibility-focused-530c297a.json` | Existing Workbench accessibility route at desktop and phone | `31b7240ed8b0ba832f604c3ac5f1d9782a294fcfab857e842483cec5f6931904` |

The selected target is an external fixed input and predates the implementation head. The five implementation/comparison PNGs were captured or assembled during the connected-Chrome pass on base head `530c297a634c869d9b289bfaa3ccbd25b6fde9c3`; their hashes preserve the observed pixels but do not independently encode Git provenance. The three JSON files explicitly identify that commit. Temporary files are evidence only and are not staged. The visual matrix's recorded source hashes for `src/workspace_visual_browser_gate.py` (`76dea123d40f2e9037f3053cf7812bb1cd40e7d2d936889cd85c5e6db62418c3`) and `tests/test_workspace_visual_browser_gate.py` (`912a6bbf3577f98e3d804f079dd92ac098a27f374a657ec30e4bba291be17305`) still match the final files byte for byte; the only subsequent gate edits were the separately retested accessibility collector and its unit coverage.

## Same-input visual assessment

The full comparison and both focused crops were opened and inspected together. The final implementation earns the approved direction:

- **Document hierarchy:** one stable Workbench H1 frames one 44 px serif `AAPL Company Brief` H2 and a four-lane answer document. No legacy decorative ticker/title duplicate remains. The brief is the dominant content, not a dashboard-card collection.
- **Evidence rail:** the navy `Company evidence status` landmark is one labelled semantic `<aside>` at desktop. It contains exactly five truth-bound lane rows and reflows below the brief when required.
- **Editorial restraint:** typography, hairline rules, narrow lane accents, generous whitespace, muted copy, and a limited navy/green/amber palette create the intended memo-like hierarchy while retaining the product design system.
- **Responsive hierarchy:** at phone and 200% layouts the four answer lanes stack, the brief precedes the rail, and both precede the module gate. The document, aside, and actions remain inside the viewport width.
- **Function preservation:** the visible Data Health action remains usable. The detailed modules stay closed initially and open only after the explicit gateway action.

### Typography, spacing, color, assets, and copy

- Typography: the app keeps `Company Workbench` as the sole H1 and exposes `AAPL Company Brief` as the sole display H2. The H2 renders at 44 px, weight 600, line height 46.2 px, with Georgia/Times serif fallbacks and `#0F172A` ink. Existing sans-serif body and control typography remains consistent with adjacent routes.
- Spacing: at 1440 x 1024 the title is `x=122.5..577.4`, `y=328.7..406.9`; the brief is `x=122.5..998.3`, `y=327.7..616.4`; the rail is `x=1026.3..1288.9`, `y=342.7..616.5`. The target's denser, earlier-starting document was not copied at the cost of shell consistency.
- Color: the rail uses `#0B1B2B`; heading/state text uses `#F8FAFC` at 16.64:1, and metadata/labels use `#CBD5E1` at 11.73:1. The enabled module gate uses `#F8FAFC` on `#155E4B` at 7.34:1. The green Data Health action remains product-consistent.
- Assets: target-only icons, date/calendar furniture, disclosure chevrons, and recent-note imagery were not fabricated. No placeholder asset, inline drawing, emoji, or invented icon was introduced.
- Copy: all visible statements come from current saved-company/readiness logic. The page retains the research-only boundary and does not promote missing evidence into a conclusion.

## Target-to-product-truth deviations

| Target element intentionally not copied | Product-truth treatment | Reason |
|---|---|---|
| Mock Apple business-trend narrative and valuation-context prose | Existing source-backed modules remain behind the explicit gateway; unavailable quarterly evidence stays withheld | The target prose is not repository evidence and would fabricate analysis |
| `As of Aug 14, 2026`, per-lane `Updated Aug 12, 2026`, and dated recent notes | Actual saved readiness is shown without invented update dates or notes | No matching authoritative local rows support those dates |
| Target `Supported` and `Partial` lane states | Actual AAPL states are `Reviewable` for Fundamentals/DCF and `Withheld` for Peers/Earnings/Estimates | Readiness must fail closed and use current product semantics |
| Target freshness explanation and recent Data Health feed | Compact `AAPL · Stale` metadata and five current readiness rows | No traceable saved notes exist for the richer feed |
| Target icons, chevrons, calendar, and external-link glyphs | Text labels, semantic regions, native links/actions | No approved matching asset set was available; assets were not approximated |
| Target's always-visible lower analysis narrative | Existing analysis, journal, methodology, HTML brief, and audit action open after the explicit module gateway | Preserves the task's intentional closed-first disclosure boundary |

## Interaction and runtime evidence

Connected Chrome, final base head:

- Closed state: exact AAPL URL; viewport 1440 x 1024 at DPR 1; one H1; one `AAPL Company Brief` H2; zero legacy heading span/strong nodes; one labelled brief; one labelled semantic `ASIDE`; five evidence rows; no `Research Decision Lab`; no horizontal overflow; app idle; no console errors.
- Module gateway: enabled, 241.75 x 44 CSS pixels, `#F8FAFC` on `#155E4B` at 7.34:1. One semantic click removed the gateway.
- Opened state: URL, viewport, and DPR remained exact; scroll origin remained `(0,0)`; brief count 1; semantic aside count 1; display H2 count 1; legacy duplicate count 0; gateway count 0; no horizontal overflow; no console errors.
- Preserved opened content: `Quant interpretation boundary`, `What Changed`, `Research Decision Lab`, `Business Trend`, `Valuation`, `Forward View`, `What Remains Withheld`, `Research Conclusion`, the research thesis/evidence journal, `HTML Research Brief`, and `Download Audit Data` were all present.

## Browser and accessibility gates

| Evidence | Result |
|---|---|
| Workbench visual matrix: 1440 x 1024, 1280 x 720, 390 x 844 at 100% and 200% | 6/6 passed; commit `530c297a`; failures `[]`; source snapshot valid and stable |
| Workbench document contract in every matrix cell | One H1/H2/nav/labelled brief/labelled semantic aside/gate, five rail rows, zero positive tabindex, >=44 px action, correct desktop/reflow geometry, phone lanes stacked |
| Existing Workbench accessibility route: 1280 x 720 and 390 x 844 | 2/2 passed, 73 assertions per cell, failures `[]`; exact `NVDA Company Brief` semantic H2 collected on the initial and return states |
| Accessibility runtime | Captured local server and state-harness output; zero deprecated `st.components.v1.html` warnings; no console/page errors; repository snapshot unchanged |
| Accessibility interaction/state | Explicit module open passed in one attempt; authoring error association/cleanup, exact route away/return, forced colors, reduced motion, focus, and overflow checks passed |
| Non-Workbench scope control: Research Desk 1280 x 720 at 100% | Passed; failures `[]`; runtime/focus/target/network checks retained; zero external HTTP requests |

The accessibility gate is read-only automated engineering evidence only. It is not a WCAG-conformance audit, screen-reader validation, independent-human validation, hosted validation, or market validation. The focused matrix intentionally does not claim the unchanged ordered 90-cell matrix. The Workbench observer/evaluator remains Workbench-scoped, and the required non-Workbench control passed, so the brief did not require the broad rerun.

## Comparison history and severity closure

| Pass | Head / finding | Severity | Resolution |
|---|---|---|---|
| 0 | `a6d3e2ad3`: phone 390 x 844 placed the 44 px primary Data Health action below the first-view stop boundary (`y=859..903`) | P1 | Workbench-only mobile compaction landed in `c088c23bf`; the exact phone cell now passes |
| 1 | `c088c23bf`: evidence-rail text inherited dark ink on navy (measured 1.19:1) | P1 | Workbench-only rail color and forced-colors repair landed in `895a8c15b`; final rail text is 11.73:1 or 16.64:1 |
| 2 | `895a8c15b`: enabled module gateway rendered like a disabled control (`#667085` on `#131720`, 3.60:1) | P1 | Workbench-only gateway styling landed in `bbb2ae9b4`; final enabled control is 7.34:1 and 241.75 x 44 |
| 3 | Independent review of `bbb2ae9b4`: visible heading duplicated `AAPL COMPANY BRIEF / COMPANY BRIEF / AAPL`, the H2 was underscaled, and the evidence rail was a labelled `<section>` while the observer accepted any matching class | P2 | Production Fix5 `530c297a` rendered one 44 px editorial H2 and a real labelled `<aside>`; Task 4 tightened collection to the semantic aside and added a literal negative test |
| 4 | `530c297a`: refreshed six-cell matrix, accessibility desktop/phone, closed/open Chrome capture, and full/brief/rail same-input comparisons | None | No P0/P1/P2 presentation, semantic, or functional mismatch remains in the captured state |

### Remaining P3 notes

- The existing application shell keeps a separate `Company Workbench` H1 and workspace-context strip, so the AAPL title begins lower than the target's single-title composition. This preserves cross-route hierarchy and the explicit one-H1/one-H2 contract.
- The evidence rail is intentionally more compact than the target: it omits unsupported descriptions, update dates, recent notes, icons, and chevrons. The resulting density difference is a product-truth constraint, not missing required content.
- Opened legacy content starts with `Quant interpretation boundary` rather than the target's invented Business-trend narrative. Existing module order and evidence boundaries were preserved.
- The tiny red browser-extension badge at the lower-right of the Chrome capture was absent from the application DOM and is excluded from product-byte grading; it does not obscure a required control or claim.

## Test-first gate work

- Visual document evaluator RED: the targeted evaluator test failed at import because the contract did not exist (`1 failed`, 71 deselected). GREEN: the evaluator, Workbench-scoped DOM collector, and six-cell live matrix passed without loosening the existing runtime/focus/target/network checks.
- Semantic aside RED: the literal collector test failed because the observer did not require `aside.company-workbench-evidence-status[aria-label]`. GREEN: the semantic selector, missing-aside evaluator mutations, 73-test visual-gate suite, and six live matrix cells passed.
- Accessibility title RED: the evaluator's passing fixture failed after migration from decorative ticker text to the exact semantic display title. Collector RED: importing `_company_workbench_display_title` failed before the helper existed. GREEN: both targeted contracts, the 61-test accessibility-gate suite, and the two live route cells passed against the one H2.

## Unit, render, and protected-artifact verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_workspace_visual_browser_gate.py` -> `73 passed, 1 warning` (existing dateutil deprecation warning).
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_research_accessibility_browser_gate.py` -> `61 passed, 1 warning` (same existing warning).
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_dashboard_visual_system.py tests/test_dashboard_render_smoke.py tests/test_research_workspace.py tests/test_research_mode_dashboard_contract.py` -> `284 passed, 1 warning` in 430.41 seconds (same existing warning).
- `git diff --check` -> exit 0, no output.
- `git diff --exit-code 13e7e383bee8ca51f462749c91a3dc992d92ea94 -- data outputs` -> exit 0, no output.
- `git status --short -- data outputs` -> exit 0, no output.

The unit/render results above are recorded from the current execution transcript; no separate durable test-log artifact was created. Connected-Chrome DOM, console, and click measurements are likewise session observations cross-checked against the hashed screenshots, not fields embedded in those PNGs.

## Independent review

The first read-only review found two Important/P2 seams: the duplicate, underscaled display title and the non-semantic evidence rail/observer false positive. Fix5 and the Task 4 observer/test changes closed both. The final frozen-byte reviewer then rechecked functional preservation, fail-closed readiness, query/state boundaries, responsive/accessibility behavior, semantic H2/aside collection, target fidelity, status, and protected artifacts: **0 Critical, 0 Important; READY**. A separate evidence audit matched all nine artifact paths and hashes, all six PNG dimensions, the three JSON verdict/count contracts, the 73- and 61-test unit results, and the protected checks; its provenance qualifications are recorded above.

final result: passed
