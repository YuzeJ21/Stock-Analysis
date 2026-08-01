# Company Workbench HTML Research Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure, evidence-gated Company Workbench HTML Research Brief that previews and downloads from memory without creating repository artifacts or duplicating the Python valuation engine.

**Architecture:** Extend the authoritative Python DCF result with its already-computed explicit-period subtotal. Build one immutable, sanitized presentation snapshot from existing Workbench objects. Render that snapshot as either a scoped Streamlit fragment or a complete offline document. Prepare one fail-closed Scenario Lab session result before the brief and reuse it in the existing detailed controls.

**Tech Stack:** Python 3.10+, frozen dataclasses, standard-library escaping/hashing/URL parsing, pandas, Streamlit 1.52 to less than 2, pytest 8+, Playwright with the repository's existing Chrome discovery.

## Non-Negotiable Boundaries

- Start from `docs/superpowers/specs/2026-07-31-company-workbench-html-research-brief-design.md` and current branch truth.
- Keep Streamlit, the four-route workflow, saved-data architecture, readiness model, and Python calculations authoritative.
- The HTML layer performs no DCF, sensitivity, momentum, historical-valuation, readiness, ranking, expected-return, or probability calculation.
- Use `Scenario value/share`; never produce target price, recommendation, ranking, transaction, position, allocation, upside/downside, margin-of-safety, or action language.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, peer, historical-valuation, catalyst, outcome, backtesting, and calibration states.
- A calculated DCF status does not unlock equity or per-share output without the corresponding existing bridge inputs and results.
- Display `shares_outstanding` only as `Shares outstanding used by existing model`; disclose its basis as unverified unless explicit proof exists.
- Candidate context cannot alter deterministic scenarios or become trusted evidence. Q4 and EPS split-basis boundaries remain unchanged. Synthetic fixtures stay test-only.
- The renderer accepts no output path and performs no file, network, refresh, readiness, import, apply, report, ledger, screenshot, timing, or external-service write.
- No executable JavaScript, form, iframe, image, font, external stylesheet, analytics, or runtime network request.
- Preserve the 18 pre-existing dirty generated CSV/report paths byte-for-byte and keep them unstaged. Never use `git add -A`.
- Do not run `make readiness`, `make pipeline`, `make verify`, `make validate-all`, broad refresh/import/apply commands, report writers, screenshot writers, or timing writers.
- Keep PR #113 open and draft. Do not merge or deploy.

## File Map

- Modify `src/valuation.py`, `tests/test_valuation.py`.
- Create `src/company_workbench_html.py`, `tests/test_company_workbench_html.py`.
- Create `src/scenario_lab_session.py`, `tests/test_scenario_lab_session.py`.
- Modify `src/dashboard.py`, `tests/test_dashboard_helpers.py`, `tests/test_dashboard_render_smoke.py`, `tests/test_research_mode_dashboard_contract.py`.
- Modify `scripts/public_wording_check.py`, `tests/test_public_wording_check.py`, `tests/test_diff_hygiene.py`.
- Create `src/company_workbench_html_browser_gate.py`, `tests/test_company_workbench_html_browser_gate.py`; modify `Makefile`.
- Modify `.github/workflows/commercial-research-beta.yml` and `tests/test_github_actions_workflow.py` so exact-head CI installs the declared browser-test dependency and Chromium before the full suite.
- Modify `README.md`, `docs/METHODOLOGY.md`, `ROADMAP.md`, `docs/ACCESSIBILITY_EVIDENCE.md`, `docs/DASHBOARD_QA.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, `tests/test_public_v1_release_docs.py`, and `tests/test_launchers.py`.

## Preflight Protected-Artifact Baseline

Before Task 1, verify branch/remote/PR truth and the exact dirty-path set. Local commits may be ahead of origin, but origin must not contain commits absent locally. Stop before editing if any assertion fails.

```bash
git fetch origin codex/personal-research-mode-mvp
test "$(git branch --show-current)" = "codex/personal-research-mode-mvp"
test "$(git rev-list --left-only --count origin/codex/personal-research-mode-mvp...HEAD)" = "0"
test "$(gh pr view 113 --json state --jq .state)" = "OPEN"
test "$(gh pr view 113 --json isDraft --jq .isDraft)" = "true"
test "$(gh pr view 113 --json headRefName --jq .headRefName)" = "codex/personal-research-mode-mvp"
python3 - <<'PY'
import subprocess

expected = {
    "data/analyst_estimates_readiness.csv",
    "data/dcf_readiness.csv",
    "data/earnings_readiness.csv",
    "data/price_coverage_report.csv",
    "data/reports/analyst_estimates_readiness_report.csv",
    "data/reports/data_source_status.csv",
    "data/reports/dcf_readiness_report.csv",
    "data/reports/earnings_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
    "data/reports/fundamentals_coverage_report.csv",
    "data/reports/peer_readiness_report.csv",
    "data/reports/peer_unlock_worklist.csv",
    "data/reports/price_coverage_report.csv",
    "data/reports/ticker_readiness_report.csv",
    "data/reports/universe_coverage_report.csv",
    "data/universe_master.csv",
    "outputs/feature_readiness_summary.csv",
    "outputs/peer_unlock_worklist.csv",
}
rows = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    text=True,
).splitlines()
actual = {row[3:] for row in rows}
if actual != expected:
    raise SystemExit(f"unexpected preflight paths: {sorted(actual ^ expected)}")
PY
```

Then record the output of this read-only command in the execution handoff. Re-run it after every task before committing and after the final verification matrix; every hash must remain identical to the pre-Task-1 baseline.

```bash
shasum -a 256 \
  data/analyst_estimates_readiness.csv \
  data/dcf_readiness.csv \
  data/earnings_readiness.csv \
  data/price_coverage_report.csv \
  data/reports/analyst_estimates_readiness_report.csv \
  data/reports/data_source_status.csv \
  data/reports/dcf_readiness_report.csv \
  data/reports/earnings_readiness_report.csv \
  data/reports/feature_readiness_summary.csv \
  data/reports/fundamentals_coverage_report.csv \
  data/reports/peer_readiness_report.csv \
  data/reports/peer_unlock_worklist.csv \
  data/reports/price_coverage_report.csv \
  data/reports/ticker_readiness_report.csv \
  data/reports/universe_coverage_report.csv \
  data/universe_master.csv \
  outputs/feature_readiness_summary.csv \
  outputs/peer_unlock_worklist.csv
git status --short --branch
```

After each comparison, run `make diff-hygiene-summary` to detect any new generated or manually reviewed artifact path. Stop that slice if a protected hash changes or a new artifact appears; do not absorb it into a later baseline.

---

### Task 1: Authoritative DCF Subtotal And Immutable Snapshot

**Files:**
- Modify: `src/valuation.py`
- Modify: `tests/test_valuation.py`
- Create: `src/company_workbench_html.py`
- Create: `tests/test_company_workbench_html.py`

**Primary interface:** `build_company_workbench_html_snapshot(inputs: CompanyWorkbenchHtmlInputs) -> CompanyWorkbenchHtmlSnapshot`.

- [ ] **Step 1: Add a failing authoritative-subtotal test**

Add a test named `test_calculate_dcf_exposes_authoritative_discounted_explicit_total`. Calculate one complete DCF and assert:

```python
assert result.discounted_explicit_total == pytest.approx(sum(result.discounted_fcfs))
assert result.enterprise_value == pytest.approx(
    result.discounted_explicit_total + result.discounted_terminal_value
)
```

Run:

```bash
python3 -m pytest tests/test_valuation.py::test_calculate_dcf_exposes_authoritative_discounted_explicit_total -q
```

Expected: fail because `DCFResult` has no `discounted_explicit_total` field.

- [ ] **Step 2: Expose the subtotal inside the authoritative calculation**

Add `discounted_explicit_total: float | None = None` to `DCFResult`. In `calculate_dcf`, assign `sum(discounted_fcfs)` once and use that named value in `enterprise_value = discounted_explicit_total + discounted_terminal_value`. Do not change any formula, rounding, default scenario, or readiness rule.

Run:

```bash
python3 -m pytest tests/test_valuation.py -q -k 'discounted_explicit_total or dcf'
```

Expected: the new test and existing DCF tests pass.

- [ ] **Step 3: Write failing snapshot-contract tests before creating the module**

Create synthetic test-only fixtures in `tests/test_company_workbench_html.py`. Tests must cover:

- exact copying of projected FCFs, discounted FCFs, explicit subtotal, terminal values, enterprise value, equity value, per-share value, and every sensitivity cell;
- enterprise value available while equity/per-share are withheld, with overall bridge state `partial`;
- a malicious payload containing equity/per-share values but neither net debt nor both cash and debt; those values remain withheld;
- a non-calculated DCF payload containing populated projected/discounted FCF, subtotal, terminal, enterprise, equity, and per-share values exposes none of them;
- missing, zero, negative, NaN, or infinite shares withhold per-share output;
- share label and unverified basis wording;
- canonical Bear/Base/Bull order;
- a modified Base accepted only when result status is calculated, ticker/profile match, input identity is present, and changed assumptions are non-empty;
- stale ticker, stale profile, empty identity, or unchanged Scenario Lab results rejected without affecting canonical scenarios;
- canonical sensitivity copied from `valuation_snapshot.sensitivity_table`; accepted modified Base sensitivity copied from `ScenarioLabResult.sensitivity_table`;
- a legacy/malicious finite sensitivity grid remains withheld whenever its owning canonical or modified Base bridge has `per_share_state != "available"`;
- exhaustive independent lane states for actuals, consensus, Revenue, EPS, valuation, peers, historical valuation, catalysts, outcomes, backtesting, and calibration;
- generic analyst-estimate availability cannot unlock consensus, backtesting, calibration, or probability without a matching source-backed point-in-time `nowcast_packet`;
- a same-ticker nowcast packet for a different fiscal period, with an invalid `as_of_timestamp`, or dated after either the report `generated_at` or the brief `review_cutoff` is rejected and withholds consensus, backtesting, calibration, and probability;
- a malicious packet with `probability_available=True`, at least 100 events, no failed gates, and an invented probability still emits no numerical Beat/Miss probability because the current packet has no separately approved probability-producing field contract;
- even a matching consensus-ready packet caps consensus, backtesting, and calibration at `partial` with `portable nowcast provenance incomplete`; reference-like `source_ids` and the forecast cutoff cannot be relabeled as source ID, retrieval time, rights, or field scope;
- every profile-bearing input/event must match `profile_context.profile_key`, every ticker-bearing input must match the report ticker, and mismatched selected answer, recency, journal, Decision Lab, catalyst, Forward View, valuation regime, quarterly trend, or nowcast evidence is withheld;
- the independent outcome lane is always `withheld` in version 1 with `portable outcome scope and provenance incomplete`; no `OutcomeStatus` text, count, or state is accepted into the snapshot, while the separately profile-and-ticker-scoped Decision Lab learning lane remains independent;
- empty valuation, catalyst, thesis, outcome, consensus, peer, and quarterly-actuals lanes shown as empty/withheld, never fixture text;
- explicit Q4, EPS split-basis, candidate-context, calibration, and synthetic-fixture boundaries;
- source references, private paths, secrets, unsafe URLs, and reviewer-authored action language fail closed;
- deterministic filename and snapshot identity;
- no loader, calculator, file, network, refresh, readiness, report, or ledger call.

Add a concrete order test for snapshot section keys:

```python
assert [row.key for row in snapshot.research_sections] == [
    "business-trend",
    "key-drivers",
    "risks",
    "catalysts",
    "evidence-gaps",
    "valuation-regime",
]
assert [row.key for row in snapshot.decision_lanes] == [
    "plan",
    "evidence",
    "invalidation",
    "scenario",
    "review-trigger",
    "learning",
]
```

Run:

```bash
python3 -m pytest tests/test_company_workbench_html.py -q
```

Expected: collection fails because `src.company_workbench_html` does not exist.

- [ ] **Step 4: Define exact frozen presentation contracts**

Create these frozen dataclasses in `src/company_workbench_html.py`; every collection field is a tuple containing only frozen dataclasses, strings, booleans, integers, finite floats, or `None`:

- `HtmlBriefSafeReference(label: str, href: str)`.
- `HtmlBriefAnswer(label: str, title: str, body: str, state: str, badges: tuple[str, ...])`.
- `HtmlBriefDcfBridge(state: str, enterprise_state: str, equity_state: str, per_share_state: str, explicit_total_state: str, projected_fcfs: tuple[float, ...], discounted_fcfs: tuple[float, ...], discounted_explicit_total: float | None, terminal_value: float | None, discounted_terminal_value: float | None, enterprise_value: float | None, cash: float | None, debt: float | None, net_debt: float | None, equity_value: float | None, shares_outstanding: float | None, shares_label: str, share_basis_state: str, scenario_value_per_share: float | None, currency: str, blockers: tuple[str, ...])`.
- `HtmlBriefScenario(name: str, state: str, modified: bool, method_name: str, revenue_growth: float | None, fcf_margin: float | None, wacc: float | None, terminal_growth: float | None, forecast_years: int | None, bridge: HtmlBriefDcfBridge)`.
- `HtmlBriefSensitivity(state: str, wacc_values: tuple[float, ...], terminal_growth_values: tuple[float, ...], value_grid: tuple[tuple[float | None, ...], ...], blockers: tuple[str, ...])`.
- `HtmlBriefSection(key: str, title: str, state: str, answer: str, facts: tuple[tuple[str, str], ...], blockers: tuple[str, ...])`.
- `HtmlBriefEvidenceRow(section: str, state: str, source_id: str, source_ref: HtmlBriefSafeReference, as_of: str, retrieved_at: str, rights_state: str, field_scope_state: str, model_identity: str, input_identity: str, blockers: tuple[str, ...])`.
- `CompanyWorkbenchHtmlInputs(report_payload: Mapping[str, object], profile_context: ProfileContext, observation_recency: ObservationRecencySet | None, selected_answer: Mapping[str, object], authoritative_task: Mapping[str, object], scenario_lab_result: ScenarioLabResult | None, nowcast_packet: Mapping[str, object] | None, decision_lab_state: ResearchDecisionLabState, quarterly_trend: QuarterlyTrendPacket, forward_view: ForwardViewPacket, journal_state: JournalState | None, valuation_regime: ValuationRegimePacket, catalyst_timeline: CatalystTimeline)`.
- `CompanyWorkbenchHtmlSnapshot(ticker: str, profile_label: str, review_cutoff: str, source_as_of: str, generated_at: str, model_version: str, freshness_state: str, rights_state: str, boundary: str, answers: tuple[HtmlBriefAnswer, ...], recency: HtmlBriefSection, readiness_lanes: tuple[HtmlBriefSection, ...], scenarios: tuple[HtmlBriefScenario, ...], sensitivity: HtmlBriefSensitivity, research_sections: tuple[HtmlBriefSection, ...], decision_lanes: tuple[HtmlBriefSection, ...], evidence_rows: tuple[HtmlBriefEvidenceRow, ...], blockers: tuple[str, ...], identity: str)`.

Copy every consumed list/dict into the primitive tuple contracts above before returning. Add a mutation-isolation test that mutates the original report, source metadata, and reviewer object after construction and proves snapshot content and identity do not change. Do not place profile key, data/output directories, `snapshot_inputs`, observation `source_path`, raw source mappings, analyst recommendation/target fields, or hidden session state in the snapshot.

- [ ] **Step 5: Implement exhaustive state, text, and source normalization**

Add `normalize_html_brief_state(value: object) -> str` with this exact mapping:

- `available`: `available`, `ready`, `calculated`, `current`, `supported`, `complete`, `usable_now`, `documented`, `reviewable`, `reviewed`, `review_current`, `evidence_recorded`, `process_documented`, `thesis_documented`, `invalidation_documented`, `baseline_ready`, `backtest_ready`, `signal_context_ready`, `probability_available`.
- `partial`: `partial`, `incomplete`, `conflict_review_needed`, `overdue_review`, `scheduled_review`, `review_now`.
- `stale`: `stale`, `stale_review_only`, `stale_or_unknown`.
- `not_recorded`: `not_recorded`, `not recorded`, `not_started`, `empty`, `missing`.
- `excluded`: `excluded`, `not_applicable`, `candidate_context_only`.
- `withheld`: `withheld`, `blocked`, `still_blocked`, `commercial_evidence_blocked`, `unavailable`, `insufficient_data`, `insufficient_history`, `not_supported`, `unverified`, `rejected`, an empty value, and every unknown value.

Add `safe_html_brief_text(value) -> str` and `safe_html_brief_reference(value) -> HtmlBriefSafeReference`:

- reject control characters, absolute/local/repository paths, path traversal, credential-like values, tokens, cookies, and secret-like key/value fragments;
- replace direct buy/sell/short/hold, position-size, allocation, stop-loss/take-profit, order, broker, ranking, target-price, expected-return, upside/downside, and margin-of-safety instructions with one explicit withheld message instead of echoing the text;
- preserve safe plain identifiers such as an SEC accession as escaped text with `href=""`;
- expose an href only for `https` with a hostname, no userinfo, query, fragment, control character, or secret-like path;
- reject `javascript:`, `data:`, `file:`, `vbscript:`, protocol-relative URLs, and every other active/non-HTTPS URL form.

Apply these functions to every dynamic string before it reaches a frozen snapshot, not only source references.

- [ ] **Step 6: Implement independent DCF bridge gates and scenario selection**

For each supplied DCF result:

1. No projected/discounted FCF, explicit subtotal, terminal, enterprise, equity, or per-share number is displayable unless `dcf_result.status == "calculated"`. Within a calculated result, copy only finite existing numeric fields; never recompute a missing field.
2. `enterprise_state` is available only when status is calculated and enterprise value is finite.
3. `explicit_total_state` is available only when status is calculated and the new authoritative field is finite. Never sum discounted FCFs in the snapshot or renderer.
4. The equity bridge is eligible only when assumptions contain finite net debt, or both finite cash and finite debt. `equity_state` is available only when that bridge is eligible and the supplied equity value is finite.
5. `per_share_state` is available only when equity is available, shares are finite and greater than zero, and supplied per-share value is finite.
6. Overall bridge state is available when all three stages are available, partial when at least one stage is available, otherwise withheld.
7. Keep an exact blocker for each unavailable stage. An upstream available stage remains visible.

Accept a Scenario Lab result only under all matching conditions from Step 3. Use it only for the Base scenario. Pass both `report_payload` and the accepted result to sensitivity selection; use the accepted result's grid for modified Base and the canonical report grid otherwise. Validate dimensions and finite cells without recalculation. A sensitivity grid is available only when the owning canonical or modified Base bridge has `per_share_state == "available"`; otherwise withhold the entire grid with an exact bridge blocker. Bear and Bull always remain canonical.

- [ ] **Step 7: Build the complete snapshot and identity**

Implement `build_company_workbench_html_snapshot` with this deterministic precedence and no other source reads:

- `ticker`: normalized `report_payload["ticker"]`; `selected_answer["Ticker"]`, observation selected scope, nowcast, quarterly trend, Forward View, journal, Decision Lab, valuation regime, and catalyst timeline must match. Any mismatch adds a blocker and withholds that object and its evidence rows.
- `profile scope`: journal, Decision Lab, every catalyst event, and accepted Scenario Lab result must equal `profile_context.profile_key`. Any mismatch is withheld. Profile key is used only for matching and is never copied into the portable snapshot.
- `generated_at`: valid ISO timestamp from `report_payload["generated_at"]`; otherwise `not recorded`. Never use wall-clock time.
- `review_cutoff`: valid `forward_view.source_cutoff`, else the date/time part of `generated_at`, else valid `profile_context.source_as_of`, else `not recorded`.
- `source_as_of`: `profile_context.source_as_of` only.
- `model_version`: `report_payload["method_version"]`, else `report_payload["provenance"]["method_version"]`, else `not recorded`.
- `currency`: `report_payload["financial_summary"]["currency"]`, else `price_snapshot.currency`, else `not recorded`.
- `freshness_state`: normalize the selected-ticker observation state when present; otherwise normalize `profile_context.freshness_state`.
- `rights_state`: derive only from emitted evidence rows. An empty evidence set is `withheld`. Any `restricted`, `unverified`, missing, or inconsistent rights/scope row makes the rollup `withheld`; a non-empty set in which every row is `not_applicable` makes it `excluded`; only a non-empty set whose applicable rows are all `permitted` can be `available`. This rollup never unlocks a lane.
- `share_basis_state`: `unverified` in version 1 because current report/DCF contracts contain shares outstanding but no explicit share-basis proof. Never infer or relabel diluted shares.

Map inputs to presentation rows as follows:

- Primary answers: selected-answer columns `Use Now` and `Still Blocked`, then the authoritative task; render labels `Usable now`, `Still withheld`, `Next research task` in that order.
- Recency: selected ticker state, through date, age/message, policy days, and evaluation as-of; omit `source_path`.
- Readiness lanes in fixed order `actuals`, `consensus`, `revenue`, `eps`, `valuation`, `peers`, `historical-valuation`, `catalysts`, `outcomes`, `backtesting`, `calibration`. Actuals/Revenue/EPS come from `QuarterlyTrendPacket`; valuation uses DCF field gates; peers use `ForwardViewPacket.peer_context`; historical valuation and catalysts use their supplied domain objects. The independent `outcomes` lane is always `withheld` in version 1 with `portable outcome scope and provenance incomplete`; no `OutcomeStatus` field is accepted or copied.
- Consensus, backtesting, and calibration use only a matching `nowcast_packet` whose `evidence_scope == "source_backed_preview_only"`. Matching requires normalized packet ticker equality, exact equality between `nowcast_packet["fiscal_period"]` and `report_payload["earnings_summary"]["fiscal_period"]`, and a valid packet `as_of_timestamp` no later than every valid applicable boundary among the report `generated_at` and computed brief `review_cutoff`; a missing earnings fiscal period, invalid timestamp, different period, or post-cutoff packet withholds all three lanes. Consensus also requires `readiness.consensus_ready is True`; analyst-estimate availability in the report is never sufficient. Backtesting may copy only packet verdict/count/blockers, and calibration may copy only state/event count/gates. Because the current packet exposes reference-like source IDs and a forecast cutoff but no distinct source ID, retrieval timestamp, rights state, or field scope, each matching lane is capped at `partial` with `portable nowcast provenance incomplete`; otherwise it is withheld. Version 1 always withholds numerical Beat/Miss probability: `probability_available`, event counts, clean gates, or any uncontracted probability-like packet key cannot expose a number. A missing or synthetic packet withholds all three lanes independently.
- Research sections in the exact Step 3 order use quarterly/Forward View/report risk/catalyst/valuation-regime objects. Empty objects produce explicit empty/withheld rows.
- Decision lanes copy the supplied six `ResearchDecisionLabState.lanes` by key in fixed order, preserving each independent state.
- Evidence rows use only sanitized `provenance.source_records`, `valuation_snapshot.source_metadata`, accepted Scenario Lab `source_metadata`/`input_identity`, journal entries, and catalyst events. Deduplicate by the full frozen row while preserving section order. Matching nowcast `source_ids` may appear only as sanitized reference-like facts on a `partial`/`withheld` lane; packet `as_of_timestamp` is a forecast cutoff, not a retrieval time. They must not populate `HtmlBriefEvidenceRow.source_id`, `retrieved_at`, `rights_state`, or `field_scope_state`. Never infer a source ID, reference, retrieval time, rights status, or field scope.
- Current `QuarterlyTrendPacket` retains a latest source reference but not a complete source ID/retrieval/rights tuple, and `ValuationRegimePacket` retains references but not the complete tuple. Their research summaries may render only as `partial` or `withheld` with an exact `portable provenance incomplete` blocker unless a complete evidence row is explicitly linked to the exact same scoped source record in another supplied object. They cannot contribute an `available` evidence row by themselves. `OutcomeStatus` is not an input in version 1 because it retains neither profile/ticker scope nor portable source identity; do not infer or self-attest that linkage.

Build primary answers in this order: `Usable now`, `Still withheld`, `Next research task`. Keep technical evidence and input identity in `evidence_rows` for Advanced only.

Construct the entire sanitized snapshot with `identity=""`, then compute SHA-256 over `json.dumps(asdict(snapshot_without_identity), sort_keys=True, separators=(",", ":"), ensure_ascii=False)` and return a copy containing that identity. This makes dates, recency, readiness lanes, freshness, rights, boundary, answers, scenarios, sensitivity, research sections, Decision Lab lanes, evidence, input identities, and blockers identity-bearing.

Add `company_workbench_html_filename(snapshot) -> str` using only uppercase ticker characters `[A-Z0-9.-]`, the first valid ISO date from `review_cutoff`, then `generated_at`, and suffix `-research-brief.html`; use `undated` when neither date is valid. The helper accepts no path.

- [ ] **Step 8: Run focused tests and commit Task 1**

```bash
python3 -m pytest tests/test_valuation.py tests/test_company_workbench_html.py -q
git diff --check
git add -- src/valuation.py src/company_workbench_html.py tests/test_valuation.py tests/test_company_workbench_html.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add HTML research brief snapshot contract"
```

Expected: all focused tests pass; only the four named files are staged; the 18 generated paths remain unstaged.

---

### Task 2: Scoped Fragment, Secure Offline Document, And Download Contract

**Files:**
- Modify: `src/company_workbench_html.py`
- Modify: `tests/test_company_workbench_html.py`

- [ ] **Step 1: Write all renderer tests before implementation**

Add failing tests for:

- exact section order: overview, answers, scenarios, DCF bridge, sensitivity, business/forward view, Decision Lab, Advanced evidence;
- one H1 plus semantic header/main/section/table/caption/footer in the full document;
- a fragment rooted at one `<article class="srcc-html-brief">` with an H2, and no `<html>`, `<head>`, `<body>`, `<header>`, `<main>`, `<footer>`, skip link, CSP meta, or script;
- every fragment CSS selector beginning with `.srcc-html-brief`; no unscoped `table`, `th`, `td`, universal, `:focus-visible`, `body`, or heading selector;
- full-document CSS scoped under `.srcc-html-document` except the document's own media declarations;
- exact CSP: `default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'` and no `frame-ancestors` claim;
- no script, event handler, form, iframe, CSS URL, remote asset, unsafe or auto-fetching source reference, private path, secret, or raw markup; validated user-clicked HTTPS references remain permitted;
- `0`, negative supported values, and empty strings formatted distinctly; zero must never become `not recorded`;
- complete/partial/withheld/stale/not-recorded/excluded labels and non-color cues;
- DCF and sensitivity display strings derived from the supplied snapshot only;
- safe HTTPS references linked with `rel="noreferrer noopener"`; safe non-URL identifiers remain text; unsafe references disappear;
- print, forced-colors, reduced-motion, focus, responsive table, and research-boundary CSS;
- deterministic UTF-8 document bytes and pure download metadata.

Run:

```bash
python3 -m pytest tests/test_company_workbench_html.py -q -k 'renderer or document or fragment or download or csp or css'
```

Expected: fail because the renderer/download functions do not exist.

- [ ] **Step 2: Implement exact pure renderer interfaces**

Add frozen `HtmlBriefDownloadSpec(data: bytes, file_name: str, mime: str)` and these functions:

- `render_company_workbench_html_fragment(snapshot: CompanyWorkbenchHtmlSnapshot) -> str`.
- `render_company_workbench_html_document(snapshot: CompanyWorkbenchHtmlSnapshot) -> str`.
- `company_workbench_html_bytes(snapshot: CompanyWorkbenchHtmlSnapshot) -> bytes`.
- `company_workbench_html_download_spec(snapshot: CompanyWorkbenchHtmlSnapshot) -> HtmlBriefDownloadSpec`.

Use one escaped section-content renderer, but distinct wrappers:

- Fragment wrapper: scoped style plus `<article class="srcc-html-brief" aria-labelledby="srcc-brief-title">`; use H2 for its title.
- Document wrapper: doctype, `<html lang="en">`, metadata/CSP/style, `<body class="srcc-html-document">`, skip link, one header/H1, `<main id="research-brief-main" tabindex="-1">`, and footer.

Implement `format_html_brief_number(value, *, currency="", percent=False)` so `None` renders `not recorded`, zero renders a numeric zero, non-finite input is rejected before rendering, percentages format supplied decimal values, and currency output includes the escaped recorded currency code. Do not perform valuation arithmetic.

`HtmlBriefDownloadSpec` must contain `company_workbench_html_bytes(snapshot)`, the safe filename, and exact MIME `text/html; charset=utf-8`. It has no path or writer.

- [ ] **Step 3: Implement fully scoped CSS**

Prefix fragment selectors with `.srcc-html-brief`. Prefix full-document selectors with `.srcc-html-document`. Scope universal reduced-motion rules beneath the corresponding root. Use one-column reflow below 700px, a local `.table-scroll`, visible `:focus-visible`, state text/borders independent of color, print-visible Advanced evidence and boundary, and forced-color borders. Do not hide blockers or provenance in print.

- [ ] **Step 4: Run focused tests and commit Task 2**

```bash
python3 -m pytest tests/test_company_workbench_html.py -q
git diff --check
git add -- src/company_workbench_html.py tests/test_company_workbench_html.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Render secure offline research briefs"
```

---

### Task 3: Fail-Closed Current Scenario Lab Session Adapter

**Files:**
- Create: `src/scenario_lab_session.py`
- Create: `tests/test_scenario_lab_session.py`
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

- [ ] **Step 1: Write all session and dashboard contract tests first**

Tests must establish:

- stable widget keys scoped by profile and ticker for revenue growth, FCF margin, WACC, terminal growth, and forecast years;
- valid current session values produce exactly one call to existing `run_scenario_lab`;
- missing source baseline returns a blocked session snapshot and never raises;
- nonnumeric values, out-of-range values, and terminal growth greater than or equal to WACC return an invalid/withheld session snapshot, never a result and never an exception;
- AppTest seeds malformed and above-maximum keyed widget state, then proves the dashboard reports the blocker, resets controls to safe defaults for rendering, and does not raise `ValueError` or `StreamlitValueAboveMaxError`;
- missing keys use the current source-backed defaults;
- ticker/profile mismatch and empty input identity cannot be passed to the HTML snapshot as a modified Base;
- `render_single_stock_report` prepares the session once before the HTML brief and passes the same object to the brief and detailed controls;
- dashboard source contains no second `run_scenario_lab(` call.

Run:

```bash
python3 -m pytest tests/test_scenario_lab_session.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q
```

Expected: fail because `src.scenario_lab_session` and the new dashboard contract do not exist.

- [ ] **Step 2: Create the exact session contract and extract the input adapter**

Move `scenario_lab_input_from_report` unchanged from `src/dashboard.py` into `src/scenario_lab_session.py` and import it back.

Create:

```python
@dataclass(frozen=True)
class ScenarioLabSessionSnapshot:
    state: str
    blocker: str
    parameters: ScenarioParameters
    result: ScenarioLabResult | None
    widget_keys: tuple[tuple[str, str], ...]
```

Add:

- `scenario_lab_widget_keys(profile_key, ticker) -> dict[str, str]`.
- `scenario_lab_parameters_from_state(report_payload, state, *, profile_key) -> ScenarioParameters`.
- `run_scenario_lab_from_state(report_payload, state, *, profile_key, dcf_ready, asset_type) -> ScenarioLabSessionSnapshot`.

- [ ] **Step 3: Implement fail-closed session preparation**

Use this exact behavior:

1. Build the current `ValuationInput` once.
2. Try `default_scenario_parameters`. If it raises, return a blocked snapshot with UI-only fallback controls `(0.08, 0.15, 0.09, 0.03, 5)`, `result=None`, and the explicit source-baseline blocker.
3. Read current keyed session values. Convert and call `validate_scenario_parameters` before calculation.
4. On type/range/cross-field error, return `state="withheld"`, `result=None`, the source-backed defaults for safe control rendering, and a visible invalid-session blocker. Do not clamp and calculate.
5. For valid parameters, call existing `run_scenario_lab` exactly once. Preserve its blocked/excluded/calculated result and reason.
6. Never cache/reuse an old result; recompute from the current report and current session values on each Streamlit rerun.

- [ ] **Step 4: Make detailed controls render the prepared session**

Change `render_scenario_lab` to accept `session: ScenarioLabSessionSnapshot` and return `ScenarioLabResult | None`. It must not calculate. Convert `session.widget_keys` to a local dictionary. Initialize a missing widget key from `session.parameters`; when malformed state caused a withheld snapshot, visibly report the blocker and replace the five invalid session-local widget values with the safe source-backed defaults before widget registration. Then call each slider with its explicit key and without a conflicting `value=` argument. This correction affects controls only, never canonical data or HTML evidence. Render no scenario value for an invalid/blocked session and return the supplied result on every branch.

- [ ] **Step 5: Run focused tests and commit Task 3**

```bash
python3 -m pytest tests/test_scenario_lab.py tests/test_scenario_lab_session.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py -q
git diff --check
git add -- src/scenario_lab_session.py src/dashboard.py tests/test_scenario_lab_session.py tests/test_dashboard_helpers.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Prepare current Workbench scenario state"
```

Expected: valid, missing-baseline, malformed, out-of-range, cross-field, mismatch, and one-call cases pass without file changes.

---

### Task 4: Company Workbench Preview And Explicit Download

**Files:**
- Modify: `src/dashboard.py`
- Modify: `tests/test_dashboard_helpers.py`
- Modify: `tests/test_dashboard_render_smoke.py`
- Modify: `tests/test_research_mode_dashboard_contract.py`

- [ ] **Step 1: Write every integration and no-side-effect test first**

Add failing tests for:

- `HTML Research Brief` after `Next Research Task` and before the detailed-report gate;
- section present only when `research_mode and report_payload` are true;
- one collapsed expander and one `Download HTML Research Brief` button;
- AppTest checks only presence, label, expander state, and sanitized fragment because Streamlit's DownloadButton proto does not expose MIME, filename, or raw bytes;
- the pure `company_workbench_html_download_spec` checks exact bytes, MIME, and filename;
- an intercepted `st.download_button` call receives those exact fields plus `on_click="ignore"`;
- complete, partial bridge, fully withheld, and modified-session renders;
- refresh, readiness, report writer, file-write, ledger append, network, and external provider entry points patched individually to raise, with the brief still rendering;
- ordinary Workbench source contains no output path, write-capable file-open call, refresh, readiness build, import, apply, or event-record call.

Run:

```bash
python3 -m pytest tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py -q
```

Expected: fail because the Workbench section is absent.

- [ ] **Step 2: Pass existing observation recency without a loader**

Add `observation_recency: ObservationRecencySet | None = None` to `render_single_stock_report`. Pass the already-loaded object from `render_company_workbench`; all other callers retain the default. Select only ticker recency state/date/message, policy days, and as-of. Never copy `source_path`.

- [ ] **Step 3: Prepare one scenario session before either consumer**

Inside the existing `if report_payload:` branch, after `selected_context` exists, call `run_scenario_lab_from_state` once and assign the result to `scenario_session`. This makes the object available to both research-only HTML and the later valuation controls. Do not calculate inside either consumer.

- [ ] **Step 4: Build and render only in the research-mode block**

Immediately after the authoritative next-task card and still inside `if research_mode:`:

1. Convert `single_answer_frame.iloc[0]` to the approved answer mapping.
2. Construct `CompanyWorkbenchHtmlInputs` from the already-built report, context, recency, `scenario_session.result`, Decision Lab, quarterly trend, Forward View, journal, valuation regime, and catalyst objects. Pass `nowcast_packet=nowcast_packet`; do not pass `OutcomeStatus`, infer outcome scope, or substitute generic analyst-estimate readiness. The snapshot emits the fixed withheld outcome lane until a future outcome contract carries inseparable profile/ticker identity and portable provenance.
3. Build the immutable snapshot and download spec.
4. Render one collapsed `st.expander("HTML Research Brief", expanded=False)`.
5. Add the approved research-only caption.
6. Call `st.html(fragment, unsafe_allow_javascript=False)`.
7. Call `st.download_button` with the download spec, key `company-workbench-html:{profile_key}:{ticker}`, and `on_click="ignore"`.

Use ticker as identity; do not add a company-name lookup. Preparing bytes must not create a temp file, output directory, report record, or ledger event.

- [ ] **Step 5: Reuse the same scenario session in detailed valuation**

Pass `scenario_session` to the later `render_scenario_lab`. Non-research Single-Stock Report continues to receive its prepared session but does not render the HTML brief. Ensure no Workbench-only variable is referenced outside the guarded report branch.

- [ ] **Step 6: Run focused dashboard evidence and commit Task 4**

```bash
python3 -m pytest tests/test_company_workbench_html.py tests/test_scenario_lab_session.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py -q
make research-dashboard-render-smoke
git diff --check
git add -- src/dashboard.py tests/test_dashboard_helpers.py tests/test_dashboard_render_smoke.py tests/test_research_mode_dashboard_contract.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Add Workbench HTML research brief"
```

Expected: all four states render; no duplicate calculation; no repository artifact changes.

---

### Task 5: Public Wording And Artifact Hygiene

**Files:**
- Modify: `scripts/public_wording_check.py`
- Modify: `tests/test_public_wording_check.py`
- Modify: `tests/test_company_workbench_html.py`
- Modify: `tests/test_diff_hygiene.py`

- [ ] **Step 1: Write failing scanner and hygiene tests**

Assert:

- `src/company_workbench_html.py` is in `PUBLIC_SOURCE_FILES`;
- complete, partial, and withheld rendered documents return no `find_forbidden_matches` result;
- rendered output contains no affirmative or instructional form of the prohibited concepts in the global boundary; the approved negated research-only and no-recommendation boundary remains visible;
- source/test/browser/doc files remain `product_candidate`;
- `outputs/local/example-research-brief.html` remains `review_manually`, not generated churn;
- no HTML writer path or generated-HTML allowlist exists.

Run:

```bash
python3 -m pytest tests/test_company_workbench_html.py tests/test_public_wording_check.py tests/test_diff_hygiene.py -q
```

Expected: scanner-scope test fails before implementation.

- [ ] **Step 2: Extend scanner scope without weakening rules**

Append only `src/company_workbench_html.py` to `PUBLIC_SOURCE_FILES`. Do not add a global safe-context exception for renderer output. Keep direct rendered-document assertions for affirmative target-price, recommendation, ranking, transaction, position, allocation, expected-return, and action wording while explicitly allowing the approved negated boundary.

- [ ] **Step 3: Lock manual-review HTML hygiene**

Add the exact classification assertions. Do not classify `.html` under `outputs/` or `data/` as generated churn until a future separately approved writer exists.

- [ ] **Step 4: Run checks and commit Task 5**

```bash
python3 -m pytest tests/test_company_workbench_html.py tests/test_public_wording_check.py tests/test_diff_hygiene.py -q
make public-wording-check
make diff-hygiene-summary
git diff --check
git add -- scripts/public_wording_check.py tests/test_public_wording_check.py tests/test_company_workbench_html.py tests/test_diff_hygiene.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Guard HTML brief wording and hygiene"
```

Expected: wording passes; hygiene still reports the same 18 generated paths and no HTML artifact.

---

### Task 6: Actual-Bytes Browser, Print, Accessibility, And No-Write Gate

**Files:**
- Create: `src/company_workbench_html_browser_gate.py`
- Create: `tests/test_company_workbench_html_browser_gate.py`
- Modify: `Makefile`
- Modify: `.github/workflows/commercial-research-beta.yml`
- Modify: `tests/test_github_actions_workflow.py`

- [ ] **Step 1: Write evaluator, fingerprint, and actual-browser tests first**

In `tests/test_company_workbench_html_browser_gate.py`, define complete, partial, and withheld synthetic snapshots locally; do not put them in product code or a real-company route.

Add failing tests for:

- evaluator requires one H1, logical headings, landmarks, captioned tables, skip focus, visible focus, exact CSP, no scripts/handlers/forms/iframes/remote requests, boundary/blocker/provenance visibility, no overflow greater than one pixel, forced-color non-color cues, reduced-motion static behavior, print boundary/evidence visibility, no console error, no page error, and non-empty in-memory PDF bytes beginning `%PDF`;
- each individual defect fails, and each missing observation key fails closed;
- `repository_fingerprint` changes for tracked-byte changes, untracked path/content changes, deletion, and rename in a temporary Git repository;
- one actual-browser matrix test passes injected bytes for all three states and all viewports to `run_company_workbench_html_browser_gate`;
- Makefile target exists, uses `PYTHONDONTWRITEBYTECODE=1`, invokes only this test file, and contains no artifact-output option.
- the CI workflow installs `-e '.[dev]'`, installs Playwright Chromium, and keeps the full test suite fail closed rather than skipping the browser matrix.

Run:

```bash
python3 -m pytest tests/test_company_workbench_html_browser_gate.py -q
```

Expected: collection fails because the gate module does not exist.

- [ ] **Step 2: Implement a generic injected-bytes gate**

Create:

- `HtmlBriefBrowserAssertion(name: str, passed: bool, evidence: str)`.
- `HtmlBriefBrowserResult(state: str, viewport: str, assertions: tuple[HtmlBriefBrowserAssertion, ...])` whose `passed` property requires every assertion to pass.
- `evaluate_html_brief_observation(observation) -> HtmlBriefBrowserResult`.
- `repository_fingerprint(repo_root: Path) -> str`.
- `run_company_workbench_html_browser_gate(cases: Mapping[str, bytes], *, repo_root: Path, chrome_executable: Path | None = None) -> tuple[HtmlBriefBrowserResult, ...]`.

`evaluate_html_brief_observation` accepts `Mapping[str, object]`. Define `REQUIRED_OBSERVATION_KEYS` and collect these exact typed values: `state: str`, `viewport: str`, `h1_count: int`, `header_count: int`, `main_count: int`, `footer_count: int`, `section_count: int`, `heading_levels: tuple[int, ...]`, `skip_target_focused: bool`, `visible_focus: bool`, `table_count: int`, `captioned_table_count: int`, `csp: str`, `script_count: int`, `event_handler_count: int`, `form_count: int`, `iframe_count: int`, `remote_request_count: int`, `boundary_visible: bool`, `blockers_visible: bool`, `provenance_visible: bool`, `overflow_px: float`, `forced_colors_non_color_cue: bool`, `reduced_motion_static: bool`, `print_boundary_visible: bool`, `print_provenance_visible: bool`, `console_errors: tuple[str, ...]`, `page_errors: tuple[str, ...]`, `pdf_byte_length: int`, and `pdf_header: str`.

Return assertions named exactly `observation_complete`, `one_h1`, `semantic_landmarks`, `logical_headings`, `skip_focus`, `visible_focus`, `tables_captioned`, `csp_exact`, `no_script`, `no_event_handlers`, `no_forms`, `no_iframes`, `no_remote_requests`, `research_boundary_visible`, `blockers_visible`, `provenance_visible`, `no_overflow`, `forced_colors_non_color_cue`, `reduced_motion_static`, `print_boundary_visible`, `print_provenance_visible`, `no_console_errors`, `no_page_errors`, and `pdf_in_memory`. A missing/wrong-typed key fails `observation_complete` and every dependent assertion; it never raises or silently defaults to a pass.

The source module receives bytes; it contains no synthetic company values. `repository_fingerprint` must enumerate `git ls-files -co --exclude-standard -z`, sort unique relative paths, hash each path, file type, and content/link target, and exclude `.git` plus ignored caches by construction. This covers every tracked file and every visible untracked file, including the 18 dirty generated paths.

- [ ] **Step 3: Implement the fail-closed Playwright matrix**

Reuse `find_chrome_executable` from `src.public_performance_gate`. Prefer an existing system Chrome; otherwise accept the executable path reported by an installed Playwright Chromium. Missing Playwright or an executable browser is a failure.

For each injected document:

1. Create the page and register request interception plus HTTP/HTTPS-request, console-error, and page-error listeners before any content is loaded, so initial document activity cannot escape observation.
2. Decode the supplied UTF-8 bytes strictly, assert re-encoding produces the identical byte sequence, and only then load that exact document with `page.set_content(document, wait_until="load")` at `1280x720`, `390x844`, and `640x900` reflow/200%-equivalent. Do not use a base64 data URL because same-document fragment navigation from a data top frame is blocked by Chrome.
3. Use physical Tab then Enter to activate the skip link and confirm `#research-brief-main` focus/target behavior.
4. Collect heading/landmark/table/CSP/active-content/boundary/blocker/provenance/focus/overflow observations.
5. Emulate forced colors and reduced motion.
6. Emulate print; confirm Advanced evidence and boundary remain visible.
7. Call `page.pdf()` without a path and record byte length/header only.
8. Close page/context and return assertions.

Fingerprint immediately before and after the full matrix; any difference raises and fails. Never write HTML, PDF, screenshot, JSON, timing, or report output.

- [ ] **Step 4: Add the direct Make target**

Add PHONY/help plus:

```make
company-workbench-html-browser-check:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_company_workbench_html_browser_gate.py -q
```

Change the workflow dependency command from `python3 -m pip install -e . pytest` to `python3 -m pip install -e '.[dev]'`, then add `python3 -m playwright install --with-deps chromium` before the full suite. Update `tests/test_github_actions_workflow.py` first to require both exact commands and to reject the old base-only install.

- [ ] **Step 5: Run direct evidence and commit Task 6**

```bash
python3 -m pytest tests/test_company_workbench_html_browser_gate.py tests/test_github_actions_workflow.py -q
make company-workbench-html-browser-check
git diff --check
git add -- src/company_workbench_html_browser_gate.py tests/test_company_workbench_html_browser_gate.py tests/test_github_actions_workflow.py Makefile .github/workflows/commercial-research-beta.yml
make staged-hygiene-check
git diff --cached --check
git commit -m "Verify offline HTML research briefs"
```

Expected: all three states pass all viewports/media modes; no repository fingerprint change.

---

### Task 7: Truth Documentation, Full Verification, Push, And Draft PR Evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `ROADMAP.md`
- Modify: `docs/ACCESSIBILITY_EVIDENCE.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`
- Modify: `tests/test_launchers.py`

- [ ] **Step 1: Write failing documentation and launcher contracts**

Require:

- README calls the feature `Download HTML Research Brief`, existing saved evidence and Python scenario math, research-only, and no refresh/new source;
- methodology records immutable snapshot, authoritative subtotal, independent field gates, share-basis label, safe text/reference policy, offline CSP, no JavaScript/image/network, and zero-write behavior;
- ROADMAP distinguishes local feature completion from source rights, current data, hosted operation, human/screen-reader accessibility, independent sessions, screening validation, and calibration;
- accessibility evidence names actual bytes, three viewports, keyboard, print, forced colors, reduced motion, PDF-in-memory, no overflow, and automated-evidence limits;
- dashboard QA names route, labels, complete/partial/withheld states, direct command, and no-artifact rule;
- continuation prompt records the implementation commit before the documentation commit as `expected anchor or a later verified descendant`, preserves the 18 excluded paths, and keeps PR #113 draft;
- Makefile help and PHONY expose the direct browser command.

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_launchers.py -q
```

Expected: new documentation assertions fail.

- [ ] **Step 2: Update the six truth documents**

Use only verified claims. Do not claim professional line-item DCF, current market coverage, source rights, readiness activation, model certification, hosted operation, human accessibility conformance, reviewer validation, market fit, screening alpha, or probability calibration.

Before editing the continuation prompt, capture the Task 6 HEAD. Record that hash as the implementation anchor followed by `or a later verified descendant`; do not claim the documentation commit is already known.

- [ ] **Step 3: Run focused tests for every changed surface**

```bash
python3 -m pytest \
  tests/test_valuation.py \
  tests/test_company_workbench_html.py \
  tests/test_scenario_lab.py \
  tests/test_scenario_lab_session.py \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_company_workbench_html_browser_gate.py \
  tests/test_github_actions_workflow.py \
  tests/test_public_wording_check.py \
  tests/test_diff_hygiene.py \
  tests/test_public_v1_release_docs.py \
  tests/test_launchers.py -q
```

- [ ] **Step 4: Run the full matrix inside one content-sensitive fingerprint**

```bash
HTML_BRIEF_TREE_BEFORE="$(PYTHONDONTWRITEBYTECODE=1 python3 -c 'from pathlib import Path; from src.company_workbench_html_browser_gate import repository_fingerprint; print(repository_fingerprint(Path.cwd()))')"
python3 -m pytest tests -q
make dashboard-smoke
make research-dashboard-render-smoke
make company-workbench-html-browser-check
make research-accessibility-browser-check TIMEOUT_SECONDS=90
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
HTML_BRIEF_TREE_AFTER="$(PYTHONDONTWRITEBYTECODE=1 python3 -c 'from pathlib import Path; from src.company_workbench_html_browser_gate import repository_fingerprint; print(repository_fingerprint(Path.cwd()))')"
test "$HTML_BRIEF_TREE_BEFORE" = "$HTML_BRIEF_TREE_AFTER"
```

Expected: every command passes and the fingerprint is identical. The 18 existing generated paths are unchanged and unstaged; no HTML, PDF, screenshot, JSON, timing, report, sample-report, canonical-data, or ledger artifact appears.

- [ ] **Step 5: Commit only truth documentation and its tests**

```bash
git add -- \
  README.md \
  ROADMAP.md \
  docs/METHODOLOGY.md \
  docs/ACCESSIBILITY_EVIDENCE.md \
  docs/DASHBOARD_QA.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md \
  tests/test_public_v1_release_docs.py \
  tests/test_launchers.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Document HTML research brief evidence"
```

- [ ] **Step 6: Verify branch, PR, and committed-range hygiene**

```bash
git fetch origin codex/personal-research-mode-mvp
test "$(git branch --show-current)" = "codex/personal-research-mode-mvp"
git status --short --branch
python3 - <<'PY'
import subprocess

expected = {
    "data/analyst_estimates_readiness.csv",
    "data/dcf_readiness.csv",
    "data/earnings_readiness.csv",
    "data/price_coverage_report.csv",
    "data/reports/analyst_estimates_readiness_report.csv",
    "data/reports/data_source_status.csv",
    "data/reports/dcf_readiness_report.csv",
    "data/reports/earnings_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
    "data/reports/fundamentals_coverage_report.csv",
    "data/reports/peer_readiness_report.csv",
    "data/reports/peer_unlock_worklist.csv",
    "data/reports/price_coverage_report.csv",
    "data/reports/ticker_readiness_report.csv",
    "data/reports/universe_coverage_report.csv",
    "data/universe_master.csv",
    "outputs/feature_readiness_summary.csv",
    "outputs/peer_unlock_worklist.csv",
}
rows = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    text=True,
).splitlines()
actual = {row[3:] for row in rows}
if actual != expected:
    raise SystemExit(f"unexpected working-tree paths: {sorted(actual ^ expected)}")
PY
git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD
gh pr view 113 --json state,isDraft,mergeable,headRefName,headRefOid,baseRefOid,statusCheckRollup,url
make pr-range-hygiene-check BASE_SHA="$(gh pr view 113 --json baseRefOid --jq .baseRefOid)" HEAD_SHA="$(git rev-parse HEAD)"
test "$(gh pr view 113 --json state --jq .state)" = "OPEN"
test "$(gh pr view 113 --json isDraft --jq .isDraft)" = "true"
test "$(gh pr view 113 --json headRefName --jq .headRefName)" = "codex/personal-research-mode-mvp"
HTML_BRIEF_REMOTE_ONLY="$(git rev-list --left-only --count origin/codex/personal-research-mode-mvp...HEAD)"
test "$HTML_BRIEF_REMOTE_ONLY" = "0"
```

Expected: only the known 18 generated paths are dirty; PR #113 is open/draft on the expected branch; range hygiene passes.

- [ ] **Step 7: Push only the approved branch and update draft PR #113**

```bash
git push origin codex/personal-research-mode-mvp
test "$(git rev-list --left-right --count origin/codex/personal-research-mode-mvp...HEAD | tr '\t' ' ')" = "0 0"
gh pr comment 113 --body "Company Workbench HTML Research Brief implementation is verified at $(git rev-parse HEAD). Focused and full tests, dashboard/render/accessibility/public/pilot/hygiene gates, and the actual-byte complete/partial/withheld browser-print matrix passed. The feature presents existing saved evidence and Python scenario math; it does not activate readiness or create a new calculation engine. No new repository artifact was created, and the 18 pre-existing generated CSV/report paths remain excluded. External source-rights, current-market, hosted, independent-human accessibility, independent-session, screening-validation, and calibration gates remain open. Keep this PR draft; do not merge or deploy."
```

Do not convert the PR to ready, merge, or deploy.

- [ ] **Step 8: Require exact-head CI with an explicit equality assertion**

```bash
gh pr checks 113 --watch
HTML_BRIEF_LOCAL_HEAD="$(git rev-parse HEAD)"
HTML_BRIEF_PR_HEAD="$(gh pr view 113 --json headRefOid --jq .headRefOid)"
test "$HTML_BRIEF_LOCAL_HEAD" = "$HTML_BRIEF_PR_HEAD"
test "$(gh pr view 113 --json isDraft --jq .isDraft)" = "true"
test "$(gh pr view 113 --json statusCheckRollup --jq '[.statusCheckRollup[] | select(.name == "local-engineering-gate") | .conclusion][0]')" = "SUCCESS"
gh pr view 113 --json isDraft,statusCheckRollup --jq '{isDraft,statusCheckRollup}'
```

Expected: exact heads match, `local-engineering-gate` succeeds for that commit, and `isDraft` is true.

---

## Completion Evidence

This slice is complete only when all seven task commits exist, the full fingerprinted no-write matrix passes, actual downloaded bytes pass the complete/partial/withheld browser/print/accessibility matrix, the branch is pushed/aligned, exact-head CI is green, PR #113 remains draft, and the same 18 generated paths remain excluded with no new repository artifact.

Completion does not establish professional line-item forecasting, current market data, source rights, hosted operation, human accessibility conformance, independent user validation, screening alpha, or probability calibration.
