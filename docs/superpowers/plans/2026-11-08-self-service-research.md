# Self-Service Company Research Implementation Plan

**Goal:** Connect online observations and new structured filings to usable company research tools without Codex or CSV preparation.

**Architecture:** Generic filing lifecycle plus a shared observed-data context; adapters reuse existing validation, scenario math and research records. New private context receipts support comparison/Monitor without modifying canonical or existing SEC receipt schemas.

**Tech stack:** Existing Python/Streamlit, SEC and permitted personal price paths, deterministic calculation kernels, pytest and real desktop/phone browser checks; no new dependency or AI account.

**Spec:** `docs/superpowers/specs/2026-11-08-self-service-research-design.md`.

## Global constraints

- Personal Research only; no rights, canonical data, approved field or saved-readiness promotion. Existing saved workflows remain independent and available.
- No prepared company CSVs, raw archive public fixtures, paid feeds, credentials, hosting or human testers.
- Preserve reported/derived/hypothetical, annual/quarter/YTD, currency, issuer/share identity and current/replayed scopes. Preserve existing peer-method conditions.
- Explicit refresh only; failures replace attempted current state. Reuse each response, with no ordinary-read network or silent stale fallback.

## Review focus

- A new filing can precede facts; retrieving old facts today must not label them current.
- Older-period amendments and comparative facts require period-specific source handling.
- User assumptions cannot become source facts or saved DCF readiness; CFO−PP&E cannot become FCFF.
- Changing company/source revision must invalidate output and keep profile/CIK isolation.
- Snapshots must reject tamper, bad paths/oversize/wrong identity and remain historical on replay.

### Task 1: Generic filing context and annual inspection

**Files:** create `src/online_filing_context.py`, `tests/test_online_filing_context.py`.

**Interfaces:**
- `build_filing_inventory(receipt, *, ticker, expected_cik, as_of=None)` → normalized sealed `online-filing-inventory-v1`; `status`, `reason`, ticker/CIK, observed/source receipt, `issuer` (name/sic/entity_type/fiscal_year_end), `latest` (annual/quarterly anchor or null), `periods` (annual/quarterly anchor lists), and earnings-report/review-trigger metadata. Anchors retain accession, form, period_end/report_date, filed, accepted_at, primary_document, source_url and amendment flag.
- `validated_filing_inventory(inventory, *, ticker, expected_cik, as_of=None, allow_historical=False)` → validated inventory or null.
- `corroborate_online_financials(financial, inventory, *, as_of=None)` → `{status, current:{annual,quarterly}, periods:{annual:{end:state},quarterly:{end:state}}, gaps}`. Each state has `status` (`corroborated`, `facts_pending`, `amendment_unresolved`, `withheld`), reason and anchor. Do not mutate financial fields/histories.
- `build_online_earnings_components(facts_receipt, inventory, *, ticker, expected_cik, as_of=None)` → separate personal-inspection annual standard fields with exact source metadata/individual holds, not approved fields.

- [x] RED/GREEN inventory, newest-period and older-period revisions, facts lag, schema/freshness/identity and comparable-source tests.
- [x] Verify generic annual concepts and unit/duration/version conflicts without issuer-specific policies.

### Task 2: Online tool adapters

**Files:** create `src/online_research_tools.py` (and focused helper module if needed), `tests/test_online_research_tools.py`.

**Interfaces:** `build_online_research_context(financial, prices, peers=None, association=None, *, ticker, profile_key, expected_cik=None, notes=None, scenario=None, as_of=None)` → spec context. Fields: `schema_version`, `ticker`, `sec_cik`, `profile_key`, `status`, `observed_at`, `source_revision`, `source_receipts`, `filing_inventory`, `filing_coverage`, `earnings_components`, `business_trend`, `peer_read_through`, `forward_view`, `decision_lab`, `gaps`, `saved_readiness_promoted=False`, `commercial_eligible=False`. All JSON-safe.

`business_trend` has exact `periods`, `metrics` (`key,label,status,value,unit,period_start,period_end,source_refs,reason`), narrative/gaps. Metrics include revenue_yoy/revenue_qoq (ratio), operating_margin (ratio), operating_margin_change_pp (percentage_points), cfo_less_ppe (source currency), where genuinely compatible.

`run_online_scenario(context, parameters, *, assumed_net_debt=None, assumed_shares=None, capital_structure_basis=None)` → JSON-safe hypothetical result with status/reason, currency, enterprise/equity/per-assumed-share results, projected flows, sensitivity, explicit assumptions, source_revision/input_identity and gaps. Parameters accept ScenarioParameters or its five-field dictionary. Do not manufacture saved readiness or zero missing capital structure.

- [x] RED/GREEN compatible/unsupported trend, cash signs/YTD, industry references, malformed inputs and source revision tests.
- [x] Prove existing DCF kernel is used, margin/growth controls change results, missing capital structure preserves EV only, explicit finite assumptions remain hypothetical, and financial-sector/currency/identity gaps hold.
- [x] Compose Forward View/Decision Lab from actual observations, documented assumptions and genuine user records. No consensus/catalyst or trusted-peer inventions.

### Task 3: Actual app orchestration, UI and snapshots

**Files:** integrate `src/sec_annual_history.py`, `src/mrvl_earnings_sources.py`, `src/company_workbench_ui.py`, `src/dashboard.py`; create `src/online_research_tools_ui.py` and `src/online_research_context_store.py` plus focused integration/storage/browser tests.

- [x] Test and add one submissions observation on generic financial refresh; reuse it in MRVL. Preserve independent source failures and older observed history.
- [x] Wire Research company, optional in-app SEC identification, latest-filing status, all online tools, genuine notes and scenario invalidation. Old saved tools stay separately scoped.
- [x] Add immutable normalized context save/compare/replay with identity/size/path/digest checks. Integrate a separate Monitor queue and company return without changing annual SEC review counts.
- [x] Exercise an unregistered company with no local input rows, new filing/facts pending/updated/amended states, user assumptions, notes, snapshots and Monitor at desktop/phone widths. No file preparation or source network during ordinary navigation.

### Task 4: Verify, document, review and sync

- [x] Validate real online company paths across industries and preserve private source observations.
- [x] Run affected regression, mathematical checks, browser matrix, render/health, rights, wording/hygiene and unchanged-data checks; fix actual failures and review findings.
- [x] Update actual product/run instructions, method, roadmap, gaps and release packet with honest self-service/unsupported boundaries.
- [x] Commit and synchronize verified main; independently verify remote commit and clean worktree.

## Execution ledger

- Baseline `3026da8a473905e662a69703b91d181784fb5113`; clean and synced origin/main; existing linked worktree reused on `codex/self-service-company-research`.
- Source and tool-contract audits confirmed real online financial/price/peer functions, but disconnected saved-tool inputs and no generic filing-inventory corroboration.
- Ruling: implement the user-authorized self-service workflow without another design/test handoff. Use existing platform/source infrastructure and explicit assumptions; no AI provider or hosting expansion.
- Ruling: add observed-data adapters instead of fabricating canonical reviews or saved DCF readiness. Reuse compatible calculation kernels and process rules; preserve the older saved paths.

- Tasks 1–3 implemented: generic filing lifecycle (46 cases), observed tools (48), bounded immutable context storage (41), actual UI/transport/notes/Monitor wiring. Canonical/profile/source-rights and public assets unchanged.
- Independent core review closed earnings freshness/current-version and selected-CIK findings. Whole-change review closed stale primary peer displays, assumption retention, independent submissions acquisition, commercial replay holds and snapshot-only identity through all sections/Monitor. Final scoped verdicts clean.
- Regression evidence: core 390/69.32s; source 430/7.32s; navigation 189/14.63s; additional UI 70/3.67s; final self-service desktop/phone 2/62.37s; six route renders and fresh health passed. Groups overlap; no full-suite claim. Final release packet records failed-run corrections.
- Real MSFT and MRVL latest annual/quarterly filings corroborated; each supplies 18 supported periods and an actual hypothetical scenario. MRVL normalized receipt ~284KB saves/replays unchanged. Live evidence stays /tmp/stock-self-service-live; synthetic browser evidence /tmp/self-service-browser-proof-2026-11-08.
- Protected-data manifest: 89 tracked data/config/assets/docs-assets files unchanged against 3026da8a; aggregate SHA256 6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373.
- Ruling: scope regression to changed source/tool/navigation/notes/store/browser/method contracts, rather than repeating the unchanged 9330-test baseline suite. No full-suite pass or external validation inferred.
- Tested code commit afacbba216b1bfaed7b864643d60ac87eead9684: 231 focused regression cases passed in18.86s on the committed tree. The source commit was fast-forwarded to main and independently matched by ls-remote and the GitHub branch API. Documentation-only follow-up records final evidence; PR-only CI was not invoked or claimed. Fresh running app restarted on8535 with final source. Final branch/worktree equality is checked after the documentation push.
