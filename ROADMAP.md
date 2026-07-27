# Roadmap

Stock Research Command Center follows one principle: **data readiness first, analysis second, research decision last**. It is research-only software: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

This is the active plan only. Completed delivery history lives in [Completed Milestones](docs/COMPLETED_MILESTONES.md).

## Current Truth

Use live, read-only commands instead of static counts:

- Master universe rows: use `make project-status` or `make status-check TOP_N=5`.
- Active research rows: use `make project-status` or the dashboard Home page.
- Lane readiness: use `make readiness-ops-center`.
- Historical proof versus current readiness: use `make proof-readiness-reconciliation TOP_N=20`; current saved readiness remains authoritative, and `historical_supported_currently_blocked` identifies an older supporting outcome that cannot be reused as current support.
- Stale-readiness impact: use `make readiness-preview TOP_N=20`; it computes proposed stable states in memory, writes no files, and does not make saved readiness current.
- DCF price-lineage impact: use the independently labeled section in the same `make readiness-preview TOP_N=20` output; it audits the exact latest usable price row without changing DCF readiness or inferring provider provenance.
- Source/provider state: use `make session-source-preflight` and `make provider-setup-checklist`.
- Package/share state: use `make pilot-readiness-check TOP_N=10` and `make public-check`.
- Public portfolio packaging: use `make linkedin-share-check` and `make browser-qa-evidence`; the LinkedIn asset is a count-safe Company Workbench answer visual, while the stable repository link is appropriate only after the reviewed feature reaches the default branch.
- Commercial-beta contract state: use `make commercial-beta-check`; this is local contract evidence, not hosted or operated proof.
- Commercial-beta release-candidate state: use `make commercial-beta-release-check`; browser timing remains separate generated evidence.
- SEC quarterly cash-generation pilot: use `make sec-quarterly-cash-preview AS_OF=<timezone-aware-cutoff>`; it is one exact-company source review, writes no artifact, and cannot activate Company Workbench or readiness.
- Prospective field-proof state: use `make prospective-field-proof-status`, then `make prospective-field-proof-preview INPUT=<reviewed_field_proof.csv> AS_OF=<utc-cutoff>`; only `make prospective-field-proof-record INPUT=<same-file> AS_OF=<same-cutoff> PREVIEW_RECEIPT=<exact-receipt> CONFIRM_REVIEWED=1` can append after explicit review.
- PR engineering gate: `.github/workflows/commercial-research-beta.yml` runs the minimal read-only test, dashboard, research-render, wording, hygiene, and whitespace contract for pull requests to `main`; hygiene and whitespace now inspect the explicit event base/head SHA range after a full-history exact-head checkout. Every revision must reverify and automation is never human review.
- Persistent continuation contract: use [Commercial Research Beta Continuation Contract](docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md); it requires repo-truth-first execution, one-time external classification, and direct evidence for every completion claim.

The committed PR snapshot remains the tracked June 7 readiness snapshot, which remains stale under this roadmap's declared-date policy. An excluded July 21 local generated working-data snapshot exists outside the committed PR evidence. A fresh read-only `make readiness-preview TOP_N=20` run against that local state reported `no_readiness_changes` and zero stable readiness changes. That local observation is not committed PR evidence and does not authorize staging or a readiness rebuild; rerun the command instead of treating any snapshot count as durable truth.

The product deliberately separates the tracked master universe, active universe, and analysis-ready subset. It must never imply that the whole tracked universe is analysis-ready.

Default personal-research flow: **Research Desk -> Discover -> Company Workbench -> Monitor**.

Company Workbench now arbitrates one overall next task. Its change answer carries an explicit `none`, `snapshot_only`, or `source_backed` context kind: an empty queue gets a neutral no-queued-change label, snapshot-only context gets only its own label, and source-backed context gets the source-backed label. A change can win only through the separate strict source-backed eligibility flag: open items keep their suggested review task, still-blocked items keep `wait_for_evidence` and their wait condition, and intentionally deferred items keep `monitor` and their wait condition. Forward View guidance remains lane-specific rather than a competing overall task, and readiness and evidence states remain independent and unchanged.

Public visitor flow remains: **Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History**. Operator mode remains the source/proof workflow. Data Health and Proof History are Advanced Evidence in Personal Research mode, not equal primary destinations.

Stage A-G labels are continuation maturity lanes only; they do not replace the numbered Stage 0-6 exit gates in the continuation contract. Stage A is the isolated prospective field-proof evidence primitive. Stage B — local field-proof audit and operator hardening is the second approved local priority after legacy surface quarantine: it may improve read-only audit, error explanation, and operator review ergonomics, but it has no readiness mapping. Any mapping into proof-readiness reconciliation, Company Workbench, canonical data, or a readiness lane requires a separate design and approval.

## Now: Commercial Research Beta Foundation

**Goal:** turn the proven Personal Research workflow into a controlled, rights-aware beta foundation without claiming hosting, licensed broad coverage, calibrated prediction, or commercial launch readiness.

1. **Implemented locally:** the source-rights registry fails closed in explicit commercial mode; unverified Yahoo/yfinance rights remain research-only.
2. **Implemented locally:** a deterministic maximum-50 focused-cohort matrix separates usable, partial, candidate-only, blocked, and excluded lanes without broad-universe readiness claims.
3. **Implemented locally:** quarterly Revenue/EPS trend and exact-period Forward View contracts preserve revision lineage, production provenance, freshness downgrades, no-derived-Q4 policy, and independent calibration gates.
4. **Implemented locally:** controlled refresh and private-beta readiness contracts describe deterministic failure handling and external account requirements without enabling automatic apply or claiming hosted capabilities.
5. **Implemented locally:** research-route render smoke, desktop/phone performance contracts, and a consolidated read-only release check verify the local candidate without refreshing data or weakening blocked states.
6. **Implemented locally:** the Evidence Activation Layer adds a five-company Earnings Nowcast readiness board, fail-closed consensus source status, append-only prospective snapshot planning, point-in-time valuation regime context, research outcome learning, and catalyst evidence timelines inside the existing four-page workflow.
7. **Implemented locally:** Discover is answer-first: readiness-backed search and company actions render before cohort scope and lane-coverage context, while the unchanged cohort evidence remains collapsed under Advanced.
8. **Implemented locally:** Company Workbench is answer-first: a Workbench-only compact header removes duplicated freshness/action metadata while retaining page identity, selected ticker/profile scope, and the research-only boundary. One anchored answer slot renders the same fail-closed fast and final selected-company answer before the collapsed Review path and lane-coverage controls; the redundant `Selected Company` heading is removed, and other routes keep the full header.
8a. **Verified locally:** the anchored answer now carries an explicit Personal Research visual contract instead of relying on Public-mode-only styles. At `1280x720` it renders one four-column selected-ticker answer with the ticker-specific Data Health action visible. At `390x844`, the answer begins at approximately `409px`, the Data Health link ends at approximately `669px`, the stop condition ends at approximately `705px`, Review path ends at approximately `746px`, lane coverage ends at approximately `806px`, and document width remains `390px`. This is local browser evidence only; it changes no readiness, source, report conclusion, or generated artifact and proves no hosted behavior, accessibility conformance, reviewer validation, demand, or product-market fit.
9. **Implemented locally:** Research Desk is answer-first: the weekly summary, four direct research answers, and Discover action render before unchanged cohort scope, coverage cards, and full matrices under Advanced Evidence.
10. **Implemented locally:** Monitor is answer-first: the weekly summary and deduplicated research-change answer render before five-company Earnings Nowcast readiness under Advanced; an empty queue remains a neutral wait state with one Discover action and never implies that no real-world event occurred.
11. **Implemented locally:** a no-file quarterly cash-generation evidence contract derives operating margin, free cash flow, and FCF margin from compatible explicit components, preserves revision and source lineage, enforces explicit filed-Q4 evidence, and renders five independent Business Trend answers while production values remain withheld without a reviewed adapter.
12. **Implemented locally:** a pure one-company adapter acceptance harness fails closed on ticker/source identity, commercial rights, supported fields, cutoff, revision ambiguity, missing or incompatible components, Revenue compatibility, complete-period derivation, and explicit filed-Q4 evidence. `accepted_for_review` always preserves `production_activation=false` and empty readiness promotions.
13. **Source state classified:** point-in-time consensus remains `external_data_required`; no permitted reviewed input is on record. Do not repeat provider probes until a permitted key is configured or a reviewed CSV is supplied; the exact resume step is one-ticker validate and preview.
14. **Implemented locally and live-source verified:** the initial NVIDIA milestone, before the AMD result in item 47, accepted NVIDIA Q1 FY2027 accession `0001045810-26-000052` for review from exact SEC Companyfacts, submissions `acceptanceDateTime`, and primary filed-table evidence. It verified Revenue USD 81.615B, operating income USD 53.536B, cash from operations USD 50.344B, and capital expenditures USD -1.757B only after explicit filed-table outflow proof. The command writes no cache or generated artifact, keeps `production_activation=false` and readiness promotions empty, and does not activate Company Workbench, prove another company or quarter, or relax Q4 evidence.
   **Implemented locally:** one explicit user-flow composition exposed that accepted result only at the opt-in NVIDIA Company Workbench `cash_preview=1` route. It showed the three cash-generation answers as preview evidence, kept exact technical lineage under Advanced, withheld the complete preview on any required failure, left the normal Workbench and all readiness states unchanged, and wrote nothing. At that original NVIDIA-only stage, it does not prove a second company, historical depth, Q4 portability, production activation, hosting, reviewer validation, calibration, demand, or product-market fit.
15. **Implemented locally:** the peer evidence-quality contract preserves relationship provenance, reviewer-assigned role, economic comparability, result context, and valuation-anchor eligibility independently. Legacy mappings remain ineligible as valuation anchors when the required role and decision evidence is absent; no role was inferred. Rerun the current peer audit instead of copying row counts into the roadmap.
16. **Next evidence-depth gate:** review one bounded peer relationship through the updated template and write-back guard when a trustworthy source and reviewer are available. Do not start a broad 25-50 company sourcing loop before the first relationship proves the repeatable contract.
17. **Next external validation:** after one repeatable permitted source path and a controlled delivery boundary exist, run 10-20 task-based beta sessions; measure time to first answer, readiness comprehension, misuse risk, trust, performance, and repeat-use intent.
18. **Implemented locally:** phone first-action density now keeps the five profile facts in two rows, removes only duplicated route-card freshness on phone, exposes Discover search and Monitor's weekly state sooner, and keeps Company Workbench's complete review path in a collapsed disclosure before the detailed report. Desktop profile and route metadata remain unchanged.
18a. **Implemented locally:** fresh desktop and `390x844` phone review passes for all five public pages: Home, Stock Selector, Single-Stock Report, Data Health, and Proof History. A later regression audit found that the Single-Stock Report direct-open loading state again placed three large quick-read cards before the evidence handoff. The loading state now renders the same compact selected-ticker answer used by the completed report, preserving Selected ticker -> `Use now` -> `Still withheld` -> `Open Data Health` before provider and report work. Browser measurement verified the 44px handoff fully inside the phone viewport with at least 50px of bottom clearance, no horizontal overflow, and no traceback; desktop remains a four-column layout with the same handoff visible. Data Health and Proof History remain answer/evidence destinations without invented calls to action. This presentation correction does not change readiness, source, research, or generated-artifact state and does not prove hosted behavior, accessibility conformance, external reviewer validation, freshness, demand, or product-market fit.
19. **Implemented locally:** shared pilot and reviewed-batch freshness now fail closed when declared source dates are newer than the saved readiness build, even when file mtimes look current after a checkout or restore. The current saved snapshot is therefore honestly stale until an intentional reviewed `make readiness` run; the read-only gate does not rebuild readiness or create CSV/JSON artifacts.
20. **Implemented locally:** `make readiness-preview TOP_N=20` now runs the production universe and readiness logic in explicit no-write mode, compares only stable saved-versus-proposed readiness fields, caps ticker detail, and routes stale pilot inspection to stdout without creating CSV, JSON, report, sample-report, screenshot, timing, or bytecode churn. It does not make saved readiness current, prove source correctness, or authorize the separate reviewed rebuild.
21. **Implemented locally:** Data Health and Proof History stay inside Personal Research mode when opened from Company Workbench Advanced Evidence, preserve the selected ticker, and expose a direct Return to Company Workbench action before evidence content. The detour does not change readiness or evidence state and adds no route, data mutation, or operator command exposure.
22. **Implemented locally:** the stale readiness continuation gate now gives project status, Session Source Preflight, provider setup, the coverage frontier, Auto-Refresh Status, its runbook, Advanced Data Health cards, and the commercial-beta release path one fail-closed operator answer. While selected-profile readiness is stale or incomplete, `make readiness-preview TOP_N=20` is the only continuation-safe command; source availability, provider classifications, scheduled operations, and ranked coverage rows remain planning context only, and `make readiness` remains a separate intentional reviewed write.
23. **Implemented locally:** the same no-write readiness preview reviews every proposed fundamentals/DCF promotion independently for exact source ID, source/as-of/durable-reference provenance, commercial-rights status, and registered field scope. Composite or unregistered source values, incomplete provenance, and incomplete registered support remain independently blocked. Command-emitted findings are local snapshot observations, not current readiness counts or rebuild approval.
24. **Implemented locally:** the preview explains saved-versus-proposed feature transitions with named method reasons, including acquisition/SPAC, bank/bancorp, financial/insurance/mortgage, closed-end fund, capital-corporation, nonpositive-revenue, realty-trust/BDC, and REIT scope. It reports ready, partial, excluded, added, and removed transitions separately. Exclusion is method fit, not a negative company signal; rerun the preview for current counts.
25. **Implemented locally:** the same no-write preview audits the one latest valid positive-close price row supporting each proposed DCF promotion, then reports row-level `source`/`source_ref`/`retrieved_at` lineage, exact-source commercial rights, and registered `prices` scope independently. Missing provider identity remains missing; file origin, observation dates, adapter availability, and refresh history are not used to infer it. Command-emitted findings are proposed in-memory changes, not current readiness counts or rebuild approval.
26. **Implemented locally:** the manual price normalization, validation, preview, and later reviewed-apply contracts can now preserve explicit prospective `source_ref` and `retrieved_at` fields. Validation reports `lineage_complete` or `lineage_review_required` independently from technical OHLCV validity, and invalid retrieval timestamps remain blank rather than being replaced with current time. This is capability evidence only: no repository price row was normalized or applied, current canonical history remains unchanged, and source rights/registered `prices` scope remain separate.
27. **Implemented locally:** staged price validation and preview now join each exact retained `source` value to the checked-in source-rights registry and report commercial-rights and registered `prices` scope independently from technical validity and lineage. Unknown, blank, unverified, mixed, and approved states fail closed without aliases or provider inference. This is read-only review capability: it does not edit rights, approve apply, rebuild readiness, or change canonical price history.
28. **Implemented locally:** explicit Commercial Research mode now blocks staged-price apply before backup or canonical mutation unless every valid row has complete lineage, approved exact-source rights, and registered `prices` scope. Research mode retains the existing separately reviewed local apply path. Temporary fixtures prove blocked and passing guard states; no repository apply or readiness rebuild occurred.
29. **Implemented locally:** prospective consensus preview now keeps append-only technical validity separate from exact-source commercial rights and metric-specific registered scope. Populated Revenue and EPS values require independent `revenue_consensus` and `eps_consensus` support, and explicit Commercial Research mode blocks before ledger or directory mutation when either rights or required scope is incomplete. Research mode retains explicit reviewed append compatibility. The checked-in registry still has no approved consensus source or scope, no real snapshot was recorded, and readiness remains unchanged.
30. **Implemented locally:** prospective consensus preview and record now share one ordered whole-batch preflight. Proposed rows are simulated against a virtual append-only ledger so intra-batch duplicates, same-period conflicts, missing or reversed supersession, technical rejection, and commercial-evidence gaps are visible before mutation. A deterministic later rejection leaves the saved ledger unchanged; valid batches append in input order through one reviewed call. This is not concurrent-writer locking or crash-safe filesystem transactionality, and no repository consensus row or readiness artifact was written.
31. **Implemented locally:** upstream consensus source-row validation no longer accepts caller-declared rights labels. Technically valid research rows now retain candidate or historical-reviewable status while exact-source commercial rights and each populated Revenue/EPS scope are derived independently from the checked-in registry. Invalid technical rows do not enter commercial-ready counts, composite providers remain unknown exact IDs, and historical rows are `historical_evidence_reviewable`, not activated evidence. The registry still approves no prospective-consensus source or consensus scope, no real snapshot was recorded, and readiness remains unchanged.
32. **Implemented locally:** every upstream consensus source-row review now requires an explicit UTC review cutoff and an exact `current_only` or `point_in_time` scope. A row can enter candidate or historical-reviewable evidence only when `snapshot_at <= retrieved_at <= review_cutoff`; missing/unknown scope, reversed timestamps, and post-cutoff evidence fail technically before commercial review. The normalized cutoff remains in the result, valid sibling rows retain original row numbers, and no real snapshot, rights record, ledger, or readiness artifact changed.
33. **Implemented locally:** prospective collection preview and upstream source-row validation now share one immutable exact-source commercial field-scope decision. The helper preserves ordered required and missing fields, refuses blank or duplicate requirements, keeps commercial-rights approval separate from registered scope, and never expands aliases or composite source IDs. Consumer-specific technical states, blockers, write rules, and readiness remain unchanged; other price, DCF, fundamentals, and cash-generation evidence reviews remain separate domain contracts.
34. **Implemented locally:** `make earnings-consensus-source-review INPUT=<reviewed_source_export.csv> PROVIDER=<source_id> AS_OF=<timestamp>` now gives one supplied upstream consensus export a read-only source-review-before-preview gate. It requires an explicit provider and UTC cutoff, rejects ambiguous CSV shape, preserves original row order, and exposes technical acceptance, candidate versus historical scope, rejection reasons, exact-source rights, and populated Revenue/EPS scope in human or JSON output before collection preview. The upstream export and the prospective collection CSV are distinct input contracts: accepted evidence must be separately reviewed and mapped into the existing prospective schema, never inferred or transformed automatically. The command never fetches, normalizes, records, applies, rebuilds readiness, or writes an artifact.
35. **Implemented and hosted-verified:** one least-privilege GitHub Actions workflow now runs only for pull requests to `main` and executes the full pytest suite, dashboard smoke, all Personal Research route renders, public wording, generated-artifact hygiene, and whitespace checks. It has no schedule, push trigger, secrets, provider access, readiness rebuild, deployment, or artifact upload. Direct GitHub evidence passed on the implementation lineage after adding the missing test runner, removing one live-network dependency from a provider-classification test, and installing the checked-in package so direct script entrypoints work in a clean runner. Every later revision must reverify; human review remains a separate unproven gate.
36. **Implemented and hosted-verified on its implementation lineage:** explicit Commercial Research direct-price refresh now requires one exact immutable provider ID, approved rights, and registered `prices` scope before provider construction/fetch; automatic ladders filter each leg independently and the selected provider is rechecked before merge or status mutation. Research mode retains its existing ladder. No provider was approved or called and no price row or readiness artifact changed. Every later revision requires its own exact-head CI result.
37. **Implemented locally:** focused-cohort saved-row evidence now reviews margins, free cash flow, cash, debt, shares, filing dates, earnings dates, point-in-time Revenue/EPS consensus, and trusted peers through independent technical, provenance, exact-source rights, and registered-field decisions. SEC Companyfacts can support shares and filing dates without unlocking margins, FCF, cash, or debt. Candidate peers remain candidate-only and field-scope blockers stay under Advanced cohort evidence.
38. **Implemented locally:** focused-cohort adjusted price history now requires saved price readiness plus technically usable canonical rows, complete row-level `source`/`source_ref`/`retrieved_at` provenance, approved exact-source rights, and registered `prices` scope before Commercial Research coverage is usable. Every retained history row must pass; mixed or unlined history fails closed. Current canonical history remains useful for research but blocked commercially because it has no row lineage.
39. **Implemented locally:** focused-cohort canonical quarterly Revenue and EPS now conjoin the technical trend packet with a metric-specific commercial review of every populated accepted row. Exact source/reference/retrieval provenance, approved rights, and literal `revenue` or `eps` scope are required independently; SEC Companyfacts Revenue permission cannot unlock EPS, and one mixed or unapproved row blocks only its metric. Research mode retains packet behavior. This closes the Priority 2 cohort field-scope enforcement lane while leaving EPS split-basis verification, loader rejection integrity, revision integrity, explicit Q4 proof, readiness, and nowcast activation independent.
40. **Implemented locally:** the Companyfacts unverified EPS split-basis sentinel is now centralized and fail-closed across every canonical downstream evaluation path found by the audit. Business Trend excludes sentinel EPS values and comparisons, mixed history remains partial with named periods, commercial cohort scope cannot override the technical block, backtests withhold sentinel target/prior-year/consensus EPS outcomes, and EPS-only sentinel targets are excluded. A filed-Q4 integration test proves five contiguous Revenue quarters can become ready while Q1-Q3 Companyfacts EPS keeps EPS withheld despite an explicit filed-Q4 row. Revenue remains independently usable. This closes Priority 3 local sentinel enforcement; it does not create primary split proof, repair canonical rows, activate nowcasts, or satisfy backtest/calibration depth.
41. **Implemented locally:** the prospective consensus ledger now fails closed before status, preview, or record unless every row is valid and each ticker/period forms one unique append-ordered, timestamp-increasing root-to-current-leaf chain. Duplicate IDs/evidence, missing or cross-scope parents, multiple roots, forks, cycles, reversed order, and non-leaf supersession are rejected. Preview emits a deterministic receipt bound to the exact cutoff, Commercial Research mode, proposed input, and saved ledger; record requires and recomputes it before mutation. Source-review and collection schemas remain distinct. This closes Priority 4 local ledger integrity; it does not add concurrent-writer locking, crash recovery, source data, rights, readiness, backtesting, or calibration.
42. **Implemented locally:** normalization, staged price validation/preview/apply, and DCF price-lineage review now share one conservative temporal contract. Declared retrieval requires an explicit timezone, cannot precede the next UTC day after a daily observation, and cannot exceed the explicit review cutoff. Malformed, naive, too-early, post-cutoff, or cutoff-unreviewed retrieval blocks apply before backup or canonical mutation; missing retrieval remains independently incomplete research context. Apply carries one validated staged frame and writes by flushed same-directory atomic replacement, closing the double-read gap. This closes Priority 5 local price integrity; it does not prove provider publication time, payload truth, rights, concurrent locking, crash recovery, readiness, or market validation.
43. **Implemented locally:** dashboard quarterly trends and focused-cohort Revenue/EPS coverage now treat the complete canonical quarterly-actual CSV as one validation unit. One rejected canonical row blocks every accepted-subset trend and cohort packet until the ledger is corrected; row number and reason remain visible only under Advanced quarterly evidence. Missing ledgers remain empty and no row is repaired or promoted. This closes Priority 6 canonical-quarterly consumption integrity; optional valuation, catalyst, and outcome ledger rights gates remain separate and open.
44. **Implemented locally:** non-empty historical valuation, supported catalyst, and reviewed research-outcome packets now require every used row to pass exact-source commercial rights plus literal `valuation_history`, `catalyst_evidence`, or `research_outcomes` scope before the Commercial Research dashboard can label the lane supported/reviewed. One unknown, unapproved, or scope-incomplete source blocks that scoped result; reasons stay under Advanced. Research-mode builders remain independent, candidate catalyst context never becomes supported, and empty ledgers remain empty. This closes Priority 6 optional-ledger commercial eligibility; it does not approve a source, populate a ledger, validate payload truth, or establish market evidence.
45. **Implemented locally; exact-head CI is required on every revision:** the PR workflow now checks out the event head with full history, binds explicit base/head SHAs, classifies `git diff --name-status BASE...HEAD` through the existing hygiene rules, fails on generated CSV/JSON churn, reports manual-review paths without reclassification, and runs whitespace against the same range. A temporary two-commit repository test proves committed generated churn is found even with a clean working tree. The exact beta workflow and source-rights registry are narrowly classified as product configuration; no broad `.github/` or `config/` allowlist exists. The current committed range has 0 generated churn and 0 manual-review paths. This closes Priority 7 locally; automation remains distinct from human review and never substitutes for the newest head's hosted result.
46. **Implemented locally after independent re-audit:** filed-Q4 extraction no longer maps absent or malformed split language to `as_reported`. It records `primary_split_basis_unverified`; the shared EPS predicate blocks both primary and Companyfacts unverified sentinels and rejects arbitrary nonempty basis text. A five-quarter integration proves Revenue can remain ready while EPS is withheld when primary split proof is absent. Explicit dated split proof remains usable. This corrects the remaining Priority 3 defect without changing canonical data, readiness, or generated artifacts.
47. **Implemented locally and live-source verified:** AMD Q1 FY2026 accession `0000002488-26-000076` now joins NVIDIA in one immutable, shared loader and explicit `cash_preview=1` Company Workbench path. The AMD filing supplied Revenue USD 10.253B, operating income USD 1.476B, cash from operations USD 2.955B, capital expenditures USD -0.389B, and `explicit_filed_table_outflow` evidence before free cash flow USD 2.566B was displayed. This is bounded two-company portability; it does not prove broad company coverage, arbitrary-filing support, historical depth, Q4 support, production activation, current readiness, hosting, reviewer validation, calibration, demand, or product-market fit.
48. **Implemented and audited:** the final branch review's local evidence-integrity findings are closed. Historical valuation observations reject non-finite valuation inputs, require a canonical real `YYYY-MM-DD` denominator period end, reject blank, malformed, and non-calendar denominator period ends, and reject post-cutoff retrieval evidence. Walk-forward Nowcast targets and prior-year benchmarks canonicalize Revenue/EPS independently through explicit `supersedes_source_ref` lineage, retain one event per ticker/period, and withhold ambiguous leaves per metric so one metric does not suppress the other; they use cutoff-bounded prior-year benchmarks so post-cutoff revisions cannot leak. This does not render stale readiness current or complete consensus, calibration, hosted, reviewer, operating, demand, or product-market-fit gates.
49. **Implemented locally; exact-head CI required:** the least-privilege pull-request workflow now pins `actions/checkout@v6` and `actions/setup-python@v6`, replacing the Node 20 action versions that GitHub had begun forcing onto Node 24 with a deprecation annotation. The workflow contract rejects the retired pins while preserving the same pull-request-only trigger, read-only permission, exact-head checkout, full-history PR-range hygiene, test, render, wording, and whitespace gates. This is delivery-platform maintenance only; it does not change product behavior, data, readiness, rights, hosting, reviewers, calibration, or market evidence.
50. **Implemented locally:** proof-readiness reconciliation compares the latest applicable append-only batch proof per valid ticker and independent lane with the current ticker, DCF, share-count, price, peer-mapping, or peer-valuation readiness field. `historical_supported_currently_blocked` names conflicts without restoring data or rewriting history; current-ready rows without matching supporting proof remain independently visible. Advanced Proof History shows the global and selected-ticker answer before raw ledgers, while the primary Research Desk -> Discover -> Company Workbench -> Monitor flow stays unchanged. `make proof-readiness-reconciliation TOP_N=20` is read-only and current saved readiness remains authoritative. The current-snapshot audit emits findings for that invocation only, not durable coverage totals. Reconciliation does not restore canonical data, prove source rights, field scope, provenance, payload truth, commercial use, or any external maturity gate.
51. **Implemented locally:** ticker-level historical support requires the latest supporting proof to explicitly name the ticker in `changed_tickers`; this is `explicit_ticker_change`, while scope membership alone is non-supporting. `proof_applicability` and `current_blocker_code` remain independent two-axis diagnoses: `current_canonical_row_missing` and other current observable blockers describe saved inputs. Current blocker diagnosis does not establish the historical cause. No canonical data, readiness, or proof history was rewritten; rerun the read-only command for current counts.
52. **Implemented locally — Stage A prospective field proof:** `make prospective-field-proof-status` reports absent, valid, or invalid state without writing; `make prospective-field-proof-preview INPUT=<reviewed_field_proof.csv> AS_OF=<utc-cutoff>` reports `technical_write_eligible` and `commercial_evidence_eligible` independently and emits a preview receipt; and `make prospective-field-proof-record INPUT=<same-file> AS_OF=<same-cutoff> PREVIEW_RECEIPT=<exact-receipt> CONFIRM_REVIEWED=1` is the explicit append. The preview receipt binds ledger, input, cutoff, commercial mode, and source-rights registry. This is prospective-only: an absent ledger is a valid empty state, and legacy narrative proof is not upgraded. No sample field-proof rows are checked in. Cooperative local locking narrows cooperating-writer races, but the primitive is not crash-safe, not a database transaction, and not protection from non-cooperating writers. It does not activate readiness, does not update canonical data, does not update proof-readiness reconciliation, and does not activate Company Workbench. Any future mapping requires a separate design.
53. **Implemented locally — public packaging reconciliation:** the README now has one external-reviewer entry point with Research Desk -> Discover -> Company Workbench -> Monitor as the primary product story and the five-page Public path as a secondary controlled demo. The LinkedIn package uses the maturity-accurate `Evidence-First Company Research` title, a default-branch versus draft-preview link boundary, and a reviewed real-app `1200x627` AVGO Company Workbench image that shows `Use now`, `Still withheld`, the Data Health handoff, the stop rule, and the research-only boundary without volatile readiness figures. Commercial Research performance timing now treats `Use now` as Workbench first-useful evidence rather than the page title. This is local packaging and runtime-contract evidence only; it changes no data, readiness, source, rights, forecast, conclusion, hosted state, reviewer evidence, demand, or product-market-fit gate.
54. **Implemented locally — Research Decision Lab:** the existing reviewer-authored Thesis Journal, Decision-Process Scorecard, Research Outcome Review, selected-profile report, and Change Monitor now compose one immutable six-lane loop for Plan, Evidence, Invalidation, Scenario, Review trigger, and Learning. Company Workbench preserves its selected-ticker answer and renders exactly one Decision Lab after `What Changed`; Monitor preserves Weekly Research Summary first and adds a stable-order Research Discipline Review before the independent source-change monitor. Invalid saved evidence fails closed per ticker, identities and evidence remain under Advanced, and no route, ledger, readiness state, report, company score, position field, recommendation, or transaction action was added. The approved contract is `docs/superpowers/specs/2026-07-22-research-decision-lab-design.md`; local implementation does not prove source coverage, predictive accuracy, investment performance, independent adoption, hosted reliability, commercial demand, competitive superiority, or product-market fit.

**Maturity assessment:** the quarterly cash-generation slice improves **methodology maturity**, cash-conversion transparency, adapter extensibility, fail-closed reliability, and reviewer trust. The live NVIDIA and AMD previews now prove bounded two-company portability for one official-source real-company adapter path, but it **does not prove broad real-company coverage or market validation**. Company Workbench still withholds these metrics because the preview is not activation. The slice also does not prove hosted reliability, reviewer adoption, commercial demand, calibration quality, or product-market fit. The product therefore remains a local Commercial Research Beta release candidate, not a market-validated platform.

The acceptance harness plus bounded SEC pilot prove bounded exact-source review and an explicit SEC field-scope contract. They do **not** prove production activation, broad company coverage, historical depth, Q4 coverage, independent reviewer adoption, or user demand. This historical cash-preview work does not compete with the Stage B next-safe lane. Activation remains non-active and separately designed; it is not a current next route, may not write readiness, and may not infer missing evidence.

The prospective consensus guard improves **methodology, evidence-governance, and commercial operating maturity** by preventing a technically valid reviewed row from silently becoming commercially writable without exact rights and metric scope. It preserves useful local research collection and keeps Revenue/EPS evidence independent. It does **not** provide a provider entitlement, licensed dataset, reviewed real snapshot, historical depth, calibration evidence, external reviewer result, hosted operation, commercial demand, or product-market fit.

The consensus batch preflight improves **recording reliability and reviewer trust** by making preview and mutation use the same ordered lineage decision and by preventing known later failures from leaving partial reviewed inputs. It does not add multi-process locking, crash recovery, a scheduler, source data, source rights, nowcast readiness, calibration evidence, hosted reliability, reviewer adoption, or product-market fit.

The source-row validation rights join improves **methodology and source-governance maturity** by removing a caller-controlled approval label from the earlier provider-review boundary and aligning it with exact registry evidence. It preserves useful research-only candidate and historical review without turning commercial permission into technical validity. It does not add a provider entitlement, validate a real payload, activate evidence, supply point-in-time history, unlock nowcasts, create calibration evidence, or prove product-market fit.

The consensus source temporal contract improves **leakage resistance and review reliability** by making the review boundary explicit for candidate and historical rows and refusing unknown evidence scope. It does not prove publication availability, provider rights, payload correctness, historical depth, collection reliability, nowcast readiness, calibration, reviewer adoption, or product-market fit.

The shared consensus commercial field-scope decision improves **methodology consistency and maintenance reliability** by preventing the collection and source-review paths from drifting on exact-source rights or populated-metric scope. It is registry-metadata review only: it cannot prove a payload, timestamp, comparability, reviewer intent, collection, activation, readiness, backtesting, calibration, hosted reliability, demand, or product-market fit.

The pull-request engineering gate improves **software-delivery maturity and independent reproducibility** by moving selected local checks into GitHub's PR boundary. A direct hosted run now proves the automation path on its verified revision and exposed two legitimate portability gaps that local editable/network state had masked. It still does not provide independent human review, and neither automated result can prove source rights, data freshness, reviewer adoption, commercial demand, or product-market fit.

The consensus source-review command improves **Stage 2 operating reliability and reviewer visibility** by turning the existing in-memory validator into a repeatable read-only gate before collection preview. It does not supply a provider, entitlement, dataset, payload proof, durable source-reference proof, collection, readiness, backtesting, calibration, hosting, reviewers, demand, or market validation. The current point-in-time consensus and commercial-rights dependencies remain external.

The phone first-action and anchored Workbench-answer slices improve **local usability maturity** and reviewer comprehension. They do not change readiness, source evidence, coverage, forecasts, or research conclusions, and they do not prove hosted reliability, external reviewer demand, commercial demand, or product-market fit.

The public packaging reconciliation improves **portfolio clarity, first-review usability, and evidence credibility** by aligning the README, LinkedIn copy, curated screenshot, browser-QA contract, and first-useful timing with the same answer-first Workbench experience. It removes a stale count-heavy social claim and makes draft/default-branch link status explicit. It does not prove external sharing, independent reviewer comprehension, hosted reliability, commercial adoption, competitive differentiation, demand, or product-market fit.

The declared-date freshness alignment improves **operating reliability** by making pilot packaging, reviewed batches, project status, and the selected-profile context agree on the same fail-closed boundary. It does not refresh source data, rebuild readiness, or turn stale counts into current counts; file mtimes remain a second check rather than a substitute for declared source dates.

The readiness-impact preview improves **operating maturity** by making the effect of a future reviewed rebuild inspectable before generated artifacts are written. The current preview detects substantial proposed fundamentals and DCF readiness movement, but those in-memory counts are not current product claims and do not prove source rights, methodology correctness, reviewer acceptance, hosted operation, market demand, or product-market fit.

The same-mode evidence detour improves **workflow continuity maturity** by letting a researcher inspect blocked inputs or proof and return to the selected company without switching workspaces. It does not change readiness, prove visual or accessibility compliance, add source evidence, demonstrate hosted behavior, validate external reviewer demand, or establish product-market fit.

The stale readiness continuation gate improves **operating reliability** by preventing status, provider, coverage, scheduler, and commercial-beta release surfaces from routing an operator into broad source or refresh work from stale counts. It does not refresh data, prove source correctness, authorize a rebuild, or satisfy an external gate. It does not prove market validation.

The promotion-evidence review improves **methodology and operating maturity** by separating technical numerical completeness from provenance, exact-source commercial rights, registered field scope, and the DCF price-source dependency before a generated rebuild is considered. It does not invalidate canonical research rows, edit the rights registry, split composite source labels, establish complete DCF provenance, authorize `make readiness`, or prove market demand.

The change-cause review improves **explainability and review reliability** by making broad feature movement attributable to named, tested method rules instead of opaque field diffs. Its transition counts can overlap and are not current readiness totals; it does not change company scope, upgrade partial inputs, create a ranking, or authorize a rebuild.

The DCF price-lineage review improves **methodology and operating maturity** by separating a usable latest price row from row-level provenance, exact-source rights, and registered price-field support. It identifies a concrete migration/source-review requirement without rewriting canonical price history or pretending the original provider can be reconstructed. It does not invalidate local research rows, change DCF math or readiness, establish commercial permission, authorize generated-data migration, prove freshness, or validate product-market fit.

The prospective lineage-preservation path improves **source-operating maturity** by making the reviewed evidence fields durable through the existing preview-first workflow. It closes a local schema-loss gap without inventing historical evidence or making provenance mandatory for local technical research. It does not prove that a permitted provider exists, approve rights, validate a real payload, authorize apply, refresh readiness, or demonstrate market demand.

The staged rights-and-scope review improves **review reliability and source-governance maturity** by answering technical validity, lineage completeness, exact-source rights, and registered price scope in one no-write result. It closes a review-join gap but does not supply a provider, expand a license, validate a payload, authorize apply, refresh readiness, or establish commercial demand.

The commercial price-apply guard improves **mutation safety and operating maturity** by turning those independent evidence states into a pre-write stop rule only when Commercial Research mode is explicit. It prevents an informational warning from becoming an unlicensed commercial data mutation, while preserving local research compatibility. Passing the guard still does not prove payload correctness, reviewer approval, freshness, readiness, hosted controls, or market demand.

**Exit gate:** local release gates pass; one permitted source path demonstrates repeatable provenance and freshness; a controlled host enforces the claimed access boundary; and 10-20 reviewers can complete the primary workflow without mistaking it for advice or live-market certainty.

**Stop rule:** do not call this commercially launched, authenticated, predictive, broadly licensed, or externally validated until those separate external gates are proven. Do not reopen broad source loops merely to increase counts.

## Completed Regression Gate

### P0: Profile Truth And Local Research Change Workflow

**Status:** implemented and locally verified on 2026-07-15.

Every dashboard and status surface uses one selected-profile context for source date, readiness build time, snapshot identity, freshness, and matching coverage counts. Generated comparable snapshots support deterministic filing, readiness, price-history, fundamentals/share-count, and Nowcast-consensus change events. The derived review queue prioritizes unresolved research work, while append-only review outcomes remain separate from readiness mutation.

Use `make profile-context`, `make research-change-snapshot`, `make research-change-monitor`, and `make research-review-queue`. Generated snapshots and event previews stay unstaged. A missing baseline means no comparison is available; it never means no changes occurred.

**Boundary:** local monitoring is read-only except for the explicit reviewed-resolution append. Hosted alerts, scheduled snapshot rotation, and notification delivery remain Later and require operating evidence.

### P0: Research Thesis And Evidence Journal

**Status:** implemented and locally verified on 2026-07-15; retain as a research-process regression gate.

The selected-profile Single-Stock Report now shows one compact, reviewer-authored thesis answer with supporting and conflicting evidence, catalysts, risks, invalidation conditions, confidence history, and review dates. `data/research_thesis_journal.csv` is append-only. Thesis revisions preserve prior entries through `supersedes_entry_id`; generated thesis text and Change Monitor tasks never write journal rows automatically.

Use `make thesis-journal TICKER=<ticker>` to read, `make thesis-journal-preview ...` to validate without writing, and `CONFIRM_REVIEWED=1 make thesis-journal-record ...` only after source review. Journal entries never mutate source rows, readiness, valuation, or Review Queue outcomes.

**Boundary:** the journal documents a research process. Confidence is not investment conviction, expected return, position size, or a transaction instruction.

### P0: Performance Release Candidate

**Status:** passed locally on the fixed demo profile on 2026-07-14; retain as a release regression gate.

**Goal:** keep the guided public workflow fast enough that an external reviewer does not mistake loading for a broken page.

Use the tracked `data/demo/manifest.json` snapshot as the fixed performance dataset. Do not mix route measurements with broad data refreshes or generated local-profile churn.

1. Run `make public-performance-contract` to inspect the read-only route, viewport, snapshot, and threshold contract.
2. Run `make public-performance-gate` for real-browser cold and warm evidence at desktop and phone widths.
3. Run `make commercial-beta-performance-gate` for Research Desk, Discover, Company Workbench, and Monitor.
4. Measure the visible shell, first useful answer, and full settle separately; report repeated warm results as p90 rather than selecting the fastest run.
5. Treat Stock Selector, Single-Stock Report, Data Health, and all four research routes as critical. Keep Home and Proof History regression-protected.
6. Optimize saved summaries, deferred detail, pagination, and deterministic caching in small tested slices without weakening readiness or hiding blocked states.

Use `make commercial-beta-release-check` for the consolidated local release-candidate gate. It does not run the optional browser timing command or prove hosted/private availability.

**Exit gate:** loading feedback within 1 second, first useful answer within 3 seconds, warm full-settle p90 within 5 seconds, and cold full settle within 10 seconds on the defined local reference environment.

**Stop rule:** a missing browser dependency is `environment_limited`, not a pass. Keep timing JSON and screenshots generated and unstaged unless one concise artifact is intentionally reviewed.

## Supporting External Release Gates

These supporting gates are governed by the Approved Next-Stage Maturity Program above. They do not override its priority order, authorize deployment, or replace the primary four-route research workflow.

### P1: Controlled Hosted Preview Verification

**Goal:** turn the deterministic `demo` profile into a verified, controlled hosted demo without exposing local refresh data or credentials.

Repository-side preparation is complete. Provider-specific implementation and deployment require an explicitly approved host/account, identity and storage boundary, and verified URL.

1. Choose a Streamlit-compatible host only after explicit approval; do not deploy from this roadmap entry alone.
2. Set `STOCK_RESEARCH_DATA_PROFILE=demo` in the host environment.
3. Keep provider keys, account IDs, tokens, and broker/session files out of the repo and public app.
4. Verify Research Desk -> Discover -> Company Workbench -> Monitor on the hosted URL at desktop and mobile widths; test the secondary Public flow separately without substituting it for the primary workflow.
5. Set `HOSTED_DEMO_URL` locally only after the URL opens successfully, then rerun the public gates before changing GitHub or LinkedIn copy.

**Dependencies:** the local performance release gate, an external hosting account, a public or access-controlled preview URL, and a human browser review of the deployed route.

**Stop rule:** keep GitHub as the public link until the hosted route is verified. Call the route private only when access control is actually enforced. Screenshots remain product evidence only, never data-freshness proof.

### P1: Controlled Pilot Review

**Goal:** validate whether an external reviewer can understand the product in under three minutes.

1. Share the controlled beta package with 10-20 reviewers after the delivery boundary is verified.
2. Ask reviewers to follow Research Desk -> Discover -> Company Workbench -> Monitor without operator instructions; the secondary Public visitor flow cannot substitute for this task.
3. Record only concrete issues: where they started, what they thought was usable, what looked blocked, and what they expected to do next.
4. Prioritize reproducible first-viewport, wording, routing, or accessibility defects. Do not use pilot feedback to weaken readiness gates.

Use [Controlled Pilot Review Feedback](docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md) to capture anonymous, reproducible workflow observations without collecting personal, portfolio, or investment-opinion data.

**Dependencies:** a locally passing performance release gate, a verified delivery path, external reviewers, and controlled feedback collection.

**Stop rule:** do not call pilot feedback data proof; it only validates product clarity and workflow reliability.

## Implemented Product Capabilities

### P2: Scenario Lab - Implemented

**Goal:** let a reviewer vary source-backed DCF assumptions and understand valuation sensitivity without changing canonical data or producing a recommendation.

1. Start only from a company whose selected profile is DCF-ready.
2. Load the saved source-backed revenue, FCF or margin, shares, cash, debt, and price context as immutable baseline evidence.
3. Allow bounded changes to revenue growth, operating or FCF margin, discount rate, terminal growth, and forecast horizon.
4. Show baseline and scenario ranges, directional sensitivity, terminal-value contribution, and every changed assumption.
5. Keep scenarios session-local or explicitly exported as generated research artifacts; never apply them to canonical fundamentals or readiness.

**Stop rule:** blocked or excluded DCF inputs produce no valuation output. Scenario results are assumption tests, never fair-value claims, rankings, or direct actions.

**Implemented proof:** the detailed Valuation tab now loads source-backed defaults, enforces bounded controls, reports changed assumptions and sensitivity, and keeps provenance and scenario identity under Advanced. It is session-local and does not change canonical inputs or readiness.

### P2: Source Freshness Timeline - Implemented

**Goal:** show a selected ticker's source chronology without confusing report time, retrieval time, market time, or financial effective date.

The Sources & Gaps tab now derives a deterministic same-profile timeline from the report payload, shows unknown timestamps explicitly, deduplicates exact source records, and keeps raw provenance under Advanced. It never refreshes data, changes readiness, or infers publication, cutoff, or revision dates that are not present.

**Stop rule:** a recent retrieval or report timestamp does not render an older source period current or unlock a blocked lane.

### P2: Research Comparison View - Implemented

**Goal:** compare selected companies across usable evidence, blockers, proof freshness, and reviewed catalysts or risks without ranking them.

The existing operator-only selected review tray now accepts two or three tickers, preserves user order, and displays an evidence matrix for price, fundamentals, DCF, trusted peers, supported analysis, missing inputs, next proof, freshness, and profile-scoped journal context. It adds no route and writes no data.

**Stop rule:** the comparison produces no score, winner, expected return, recommendation, or action; candidate peer context remains separate from trusted-peer readiness.

### P2: Peer Read-Through Map - Implemented

**Goal:** show which peer results can be reviewed as directional business context without treating sector similarity or candidate peers as trusted evidence.

The existing detailed Valuation tab now separates trusted relationships, candidate-only relationships, explicit business-overlap evidence, target/peer fiscal periods, source-backed Revenue/EPS actuals, and the remaining proof needed for contextual read-through. A result becomes `reviewable_context` only when relationship provenance, business overlap, actual result evidence, and both fiscal periods are explicit.

**Stop rule:** candidate peers never become trusted automatically. Missing relationship source, actual result, or fiscal timing withholds read-through; even reviewable context cannot alter Earnings Nowcast numbers, DCF, readiness, rankings, or actions.

### P2: Decision-Process Scorecard - Implemented

**Goal:** render research discipline reviewable without grading a company or measuring investment performance.

The Single-Stock Report now derives profile-scoped checks for readiness review, thesis documentation, recorded evidence, later review of conflicting evidence, invalidation conditions, confidence history, review-date currency, unresolved Change Monitor tasks, and visible DCF assumptions. Details stay collapsed below the Thesis Journal.

**Stop rule:** the scorecard reports process states and next review steps only. It produces no numeric company score, expected return, performance claim, ranking, recommendation, or action; blocked and excluded analysis remain distinct from incomplete documentation.

### P2: Earnings Nowcast Pilot Evidence

**Goal:** move the implemented Earnings Nowcast pilot from synthetic infrastructure proof to a leakage-safe, source-backed semiconductor cohort.

Earnings Nowcast real-data safety infrastructure is implemented for deterministic Revenue/EPS ranges, consensus-relative classification, metric-specific canonical quarterly evidence, comparability checks, evidence-only directional signals, chronological walk-forward backtesting, explicit sample-sufficiency/calibration diagnostics, and a separate probability calibration gate. Versioned read-only append-only onboarding templates, validation, preview, readiness, prospective collection planning, and SEC quarterly actual staging are implemented. The SEC stage accepts Q1-Q3 only from one-to-one source-backed duration/fiscal lineage, marks Companyfacts EPS split basis unverified, accepts Q4 only when an explicit SEC-filed result table supplies the selected-column period end, preserves complete revision chains and cutoff truth, reports quarter-continuity gaps, and rejects canonical or non-generated evidence destinations. It is review-only with no automatic apply path. The committed fixture cohort is synthetic test evidence only.

1. Use the five-company SEC actuals staging scope (NVDA, AMD, AVGO, MU, and QCOM) only to assemble source-backed actual evidence; acquire permitted append-only historical point-in-time consensus snapshots with source references, publication/retrieval timestamps, and explicit Revenue/EPS comparability definitions before any real-company packet.
2. Use `make earnings-nowcast-prospective-plan` for future snapshot collection, then run the implemented onboarding validate/preview/readiness gates before any real-company packet; no automatic apply path exists.
3. Keep candidate peer/news signals separate from reviewed trusted evidence; signals explain context and never mutate forecast numbers.
4. Run chronological out-of-sample evaluation against latest-consensus and prior-year benchmarks.
5. Withhold numerical Beat/Miss probability until at least 100 valid events pass Brier-score, calibration-bin, and benchmark-improvement gates.

Real semiconductor nowcast coverage remains `awaiting_point_in_time_consensus`; numerical probability remains `awaiting_calibration_evidence`. SEC staging success alone does not change either status.

**Activation workflow implemented:** `make earnings-nowcast-cohort-readiness`, `make earnings-consensus-source-status`, `make earnings-consensus-collection-plan`, and `make earnings-consensus-collection-status` separate quarterly actual readiness, exact-period consensus, Q4 evidence, EPS split basis, backtest count, and calibration count. Current-only provider estimates remain candidate context. The first real-data exit step is a permitted append-only prospective snapshot, not a reconstructed historical estimate.

### P2: Evidence Timeline And Learning Layer - Implemented

**Goal:** make forward-looking research reviewable without turning narrative context into numerical prediction.

1. Historical valuation regimes use only aligned point-in-time numerator and denominator evidence. Definition changes split the history; current denominators are never applied to older prices.
2. Research outcome reviews preserve the original thesis reference, observation window, source evidence, and learning in an append-only ledger. They do not calculate returns, rank companies, or score research skill.
3. Catalyst timelines require reviewed event type, source reference, publication, retrieval, and effective timestamps. Candidate context remains visibly separate from supported evidence.
4. These answers live inside Company Workbench and Monitor; raw evidence stays under Advanced.

**Stop rule:** no source-backed rows means withheld output. Catalyst or outcome context cannot change Earnings Nowcast numbers, DCF assumptions, readiness, rankings, recommendations, or actions.

**Stop rule:** do not substitute current analyst estimates for historical point-in-time snapshots, use post-cutoff evidence, infer numeric adjustments from text, claim predictive accuracy from fixtures, or predict post-earnings price movement.

## Local Product Stage: Research Decision Lab (completed)

**Approved design:** `docs/superpowers/specs/2026-07-22-research-decision-lab-design.md`
**Design anchor:** `54e06e1c3` or a later verified descendant
**Current state:** local implementation and responsive workflow evidence complete; reverify the current exact HEAD before reliance

**Goal:** unify the existing research-process capabilities into one repeatable learning loop without turning the Command Center into a trading platform.

### Stage 1 — Read-only composition contract: completed locally

1. Add one focused `src/research_decision_lab.py` derivation module with immutable Plan, Evidence, Invalidation, Scenario, Review trigger, and Learning lanes.
2. Consume only existing selected-profile report, journal, scorecard, outcome, change, and scenario results.
3. Keep lane states independent and choose one deterministic next process step without changing the authoritative company research task.
4. Reject mismatched profile/ticker inputs, preserve truthful empty and blocked states, and generate no persistence or readiness change.
5. Prove the contract with failing-first unit tests, including no-trading-language and cross-lane non-promotion cases.

**Exit gate:** focused derivation tests pass and the module writes no journal, outcome, source, readiness, proof, report, screenshot, or timing artifact.

### Stage 2 — Company Workbench composition: completed locally

1. Render one compact Decision Lab summary after `What Changed` and before detailed company-research sections.
2. Preserve Selected ticker -> `Use now` -> `Still withheld` -> Data Health as the unchanged first answer.
3. Keep Research Conclusion and Next Research Task authoritative and separate from the next process step.
4. Keep identities, timestamps, source rows, and technical diagnostics under existing Advanced disclosures.
5. Verify desktop and `390x844` phone layouts without overflow, duplicated summaries, or first-answer regression.

**Exit gate:** Workbench shows exactly one six-lane summary, `USE NOW` remains the performance marker, and blocked or empty inputs display no fabricated content.

### Stage 3 — Monitor Research Discipline Review: completed locally

1. Compose focused-cohort process rows from the same per-ticker contract.
2. Keep Weekly Research Summary and source-backed change state first.
3. Group research-process gaps without scoring, ranking, expected-return ordering, allocation, or transaction language.
4. Use stable focused-cohort order followed by ticker; process severity and market value cannot reorder companies.
5. Preserve a truthful empty state that makes no claim about market risk or missing external events.

**Exit gate:** Monitor displays the new review after its weekly summary, keeps source-change and process-discipline states separate, and passes desktop/phone workflow review.

### Stage 4 — Documentation and release evidence: completed locally

1. Update Methodology, Provenance Contract, Personal Research Mode, browser-QA markers, release documentation, ROADMAP, and continuation contracts.
2. Run focused and full tests, Personal Research renders, dashboard smoke, browser QA, public wording, public and commercial-beta release gates, relevant performance gates, pilot boundary, PR-range hygiene, diff hygiene, whitespace, and staged hygiene.
3. Stage exact product/code/docs/test paths only; exclude existing generated CSV/JSON/report/sample-report/screenshot/timing churn.
4. Complete exact staging, coherent commits, controlled branch synchronization, and current-revision hosted CI without merging or public deployment.

**Exit gate:** every design acceptance criterion has direct current evidence. Local tests or screenshots alone do not prove hosted reliability, external reviewer adoption, commercial demand, investment performance, or product-market fit.

### Decision Lab acceptance audit

| Acceptance area | Classification | Current authoritative evidence | Boundary |
| --- | --- | --- | --- |
| Immutable six-lane composition, deterministic identity, independent states, and next-step priority | Proven locally | Focused derivation tests and `src/research_decision_lab.py`; composition commit `1cfed7490` or later verified descendant | Proves deterministic local behavior only. |
| Company Workbench answer-first placement and Advanced evidence boundary | Proven locally | Contract/render tests, desktop and `390x844` live route review, 48-case performance gate; Workbench commit `a4786bb25` or later verified descendant | Does not prove user adoption or source completeness. |
| Monitor stable cohort order, per-ticker failure isolation, truthful empty state, and independent source-change state | Proven locally | Loader/order/isolation tests, render smoke, desktop and phone review; Monitor commit `c7ad977b3` or later verified descendant | Does not claim no market event, risk, or external research need. |
| No writes, no generated artifacts, no ranking, no trading or allocation behavior | Proven locally | Source contract tests, public wording, diff/staged hygiene, and excluded-artifact review | Does not prove broader commercial or operating readiness. |
| Hosted reliability, external reviewer adoption, commercial demand, source coverage, calibration, and operating maturity | Incomplete external gates | Commercial Beta dependency ledger and pilot-readiness boundary | Decision Lab implementation cannot satisfy these gates. |

The next continuation must not reimplement the Decision Lab when these contracts remain green. It should reverify repo truth, choose the highest-value executable Commercial Research Beta gate, classify unavailable external dependencies once, and preserve the existing no-write/readiness boundaries.

### Explicitly later and separately approved

- Add an append-only research pre-commitment record only if usage proves the existing Thesis Journal cannot capture the required plan.
- Consider an isolated hypothetical paper-position laboratory only after a separate design, private-data policy, wording review, and explicit approval.
- Keep live holdings, account imports, recommended sizing, price-triggered stop/profit rules, broker integration, order routing, auto-trading, and real transactions out of scope.

## Next: Approved Next-Stage Maturity Program

This program is the authoritative execution order after the completed Research Decision Lab. Start with the first incomplete priority that can be advanced safely. If a priority currently requires an unavailable source, dataset, account, reviewer cohort, elapsed event history, or new approval, record its last evidence and exact unblock condition once, then move to the next safe executable priority. Recheck it only after relevant external state changes.

A blocked priority does not become complete, and skipping it does not weaken its exit gate. Local contracts, fixtures, screenshots, subagent reviews, and passing tests cannot substitute for real source, hosted, accessibility, independent-user, or calibration evidence. Continue until no safe executable priority remains; declare the overall program complete only when every applicable priority has direct current evidence.

### Priority 1 — Legacy portfolio, ranking, and action-language quarantine

**Status:** Priority 1 — completed locally.

**Current lane:** locally implemented and verified; external product-maturity gates remain separate.

1. Inventory every Personal Research, Public, Advanced, operator, report, test, and documentation surface that exposes legacy portfolio, ranking, or transaction-like language.
2. Remove those concepts from primary research navigation and public product claims, or place them behind an explicit `Legacy research utility — not part of Personal Research Mode` boundary.
3. Quarantine legacy picks, disposition, entry-zone, add-candidate, position-percentage, cost-basis, and ranked-company labels so they cannot be mistaken for current investing capability.
4. Preserve any retained legacy calculation only when required for compatibility and prove it cannot feed Research Decision Lab, company conclusions, readiness, recommendations, sizing, or transaction behavior.

**Exit gate:** route, wording, report, and no-trading tests directly prove that the supported Personal Research workflow remains research-only and that any retained legacy surface is unmistakably isolated.

**Current evidence:** the exact five-page quarantine set is Operator-only; Public and Personal Research deep links fail closed; Operator labels and pages show `Legacy research utility — not part of Personal Research Mode`; detailed compatibility output requires an explicit collapsed control; and source-contract tests prove Company Workbench and Research Decision Lab do not consume legacy portfolio, monthly-pick, momentum, value/re-rating, or final-watchlist outputs. Retained calculations and filenames remain compatibility-only and create no readiness, recommendation, sizing, or transaction authority.

### Priority 2 — Stage B field-proof audit and operator hardening

**Status:** Stage B — completed locally.

**Current lane:** locally implemented and verified; Priority 3 is next.

1. Complete the roadmap-approved read-only audit for prospective field-proof records, preview receipts, current blocker explanations, and append-only history.
2. Improve operator review ergonomics and deterministic error routing without recording evidence automatically.
3. Preserve the existing boundary: no mapping into proof-readiness reconciliation, Company Workbench, canonical data, or any readiness lane.

**Exit gate:** focused tests and read-only operator evidence prove clearer review and failure handling with no ledger, readiness, canonical-data, report, screenshot, timing, or generated-artifact write.

**Current evidence:** `make prospective-field-proof-audit` reports append order, scope and revision counts, current/superseded state, reviewer dispositions, active-head blocker categories, and controlled invalid-ledger errors. Preview text now gives per-row technical/commercial answers and states `preview_receipt_persisted=false` and `receipt_revalidation_required=true`. Byte-snapshot tests prove audit and preview do not write scoped files. The audit does not activate readiness, does not update canonical data, and does not activate Company Workbench.

### Priority 3 — In-app research-record authoring

**Current lane:** Priority 3 — completed locally after direct desktop/phone runtime review and the required automated acceptance matrix. The test-first implementation plan is recorded in `docs/superpowers/plans/2026-07-22-in-app-research-record-authoring.md`. Priority 4's local validator is frozen; its permitted real-data exit gate remains externally incomplete. Priority 6's provider-neutral authorization contract is complete locally; hosted implementation remains environment-dependent. Priority 7 accessibility remediation is the next safe executable local lane.

1. Add simple in-app authoring for thesis, evidence, catalyst, and outcome records using explicit validate -> preview -> confirm flows.
2. Keep records append-only, ticker/profile scoped, reviewer-authored, timestamped, source-aware where applicable, and independently valid or blocked.
3. Show the saved result and correction path without allowing one record type to promote another readiness or evidence lane.
4. Empty ledgers remain empty; draft text and candidate context remain untrusted; automated generation cannot become reviewer-authored evidence.

**Exit gate:** desktop and phone workflow evidence plus persistence, rejection, identity, provenance, and no-fabrication tests prove that a researcher can create and revisit records without using the command line or changing deterministic forecasts, probabilities, recommendations, or readiness.

**Approved design boundary:** one collapsed Company Workbench composer reuses the existing thesis-journal, catalyst, and outcome persistence engines. A session-only receipt binds the exact draft, selected profile/ticker, destination ledger, and current ledger fingerprint; any edit or concurrent append requires a fresh preview. Validation and preview write nothing, confirmation appends to exactly one established ledger, and automated tests use temporary ledgers only.

Hardening commit `07758114c` closes the confirmation race: all three append engines share one resolved-ledger cooperative lock, receipts bind resolved ledger identity, every new preview resets confirmation, and uncertain post-append teardown requires one-shot read-side reload before success.

Final integrity commit `e3a090dba` ensures confirmation appends only the receipt-matched recomputed record and enforces one readable active thesis lineage: revisions must supersede the exact active entry and preserve its thesis ID. The Company Workbench locks and explains that relationship, with temporary-ledger create -> revise -> reload coverage.

Confirmation-integrity commit `5a6c55921` binds every displayed preview field, preview time, and destination label to the exact receipt. If an append raises after it may have written, confirmation returns one-shot `save_pending_reload` with the exact record ID unless the locked ledger is provably unchanged; it never invites a blind duplicate retry.

Thesis, evidence, catalyst, and outcome records are all available in the collapsed Company Workbench composer.
A valid record requires an exact preview and explicit confirmation before save.
Drafts are untrusted and preview receipts are session-only.
Production tests never append repository ledgers; persistence tests use temporary ledgers.
A saved record cannot change readiness, forecasts, probabilities, recommendations, or any other ledger.

Priority 4's local validator is frozen; its permitted real-data exit gate remains externally incomplete.
Priority 6's provider-neutral authorization contract is complete locally; hosted implementation remains environment-dependent.
Priority 7 accessibility remediation is the next safe executable local lane.
That summary is necessary but not sufficient; the exact Priority 4 exit condition below also requires independent review, expected count/digest reproduction, and the partition gate.

### Priority 4 — Point-in-time benchmark and universe foundation

**Current lane:** the provider-neutral first slice is implemented locally
against the approved design in
`docs/superpowers/specs/2026-07-23-point-in-time-universe-foundation-design.md`.
It remains isolated from the current ticker-centric universe merge path and
does not fetch, normalize to disk, apply, rebuild readiness, or activate
analysis.

Implemented locally: read-only immutable-package status/preview with ten independent states: manifest, technical, temporal, identity, membership, corporate action, delisting, source rights, reproduction, and leakage.

The second through fourth fresh whole-branch reviews drove the raw-row rights,
cutoff-relative history, publication chronology, immutable bounded-read,
aggregate-budget, and structured-input parser closures. The fifth fresh
whole-branch review confirmed those closures and found three Important
trust-boundary defects: C0/C1 characters in structural identifiers could
render the newline-delimited membership digest ambiguous and forge public status
lines, while manifest creation could predate its cutoff or bound evidence.
Commits `b2bbd9961` and `c643d066b` remediate those V5 findings locally with
one shared C0/C1 plus Unicode line/paragraph-separator boundary, safe
structural-token rendering, an explicit creation-at-or-after-cutoff manifest
gate, and exact-row chronology against every contract timestamp. The first
independent R7 review found the Unicode separator and `listing_state_after`
bypass gaps; `c643d066b` closes them locally. The sixth fresh whole-branch
review confirmed those closures and found one remaining Important non-scalar
input defect: lone Unicode surrogate code points could reach public output.
Commit `f143d48ed` rejects Unicode category `Cs` through the shared boundary
and defensively ASCII-escapes it while valid supplementary-plane scalars
remain deterministic. The seventh fresh whole-branch review confirmed the V6
correction and found four further trust-boundary defects (two Critical, one
Important, and one Minor): duplicate JSON/YAML mapping keys could silently
change manifest and rights meaning; invalid or unresolved successor and
listing-state evidence could authorize stale original-member digests;
malformed CSV headers could discard contract bodies and continue; and
non-RFC3339 manifest or policy timestamps were accepted. The local
seventh-review remediation rejects duplicate keys at every mapping depth,
requires strict RFC3339 UTC manifest and policy timestamps with at most six
fractional-second digits, stops malformed
headers as package-level input-identity failures, and enforces explicit
policy/event/listing-state, successor-identity, and membership-consistency
gates without inferring or repairing a successor or membership. An independent
scoped re-review then confirmed the four original findings and the two
compatibility regressions were addressed. The eighth fresh whole-branch review
then found three Critical, nine Important, and two Minor defects across
sub-microsecond ordering, event-time identity, listing chronology and rights,
walk-forward bootstrap aggregation, identity/action reconciliation, eligible
provenance, package-contained bounded reads, manifest type handling,
standalone rights loading, and literal-safe Make arguments. Remediation 9A
through 9G closed every finding test-first. Independent scoped re-reviews
confirmed no remaining Critical or Important finding in each corrected scope;
the two Minor contracts now reject identical issuer/security IDs and
recursively freeze manifest semantics. Freeze reconciliation consolidated 21
overlapping remediation test files into six domain suites and one shared
fixture module, removed one exact duplicate plus cross-remediation private
imports, and closed five additional local correctness gaps: ambiguous parents
cannot authorize forks; pre-action cutoffs do not poison later required
coverage; decision-consumed listing-state evidence is retained in eligible
provenance; manifest nesting is explicitly bounded; and structural source IDs
cannot forge status output. Full branch verification at freeze reconciliation
is 4,084 passing tests,
one environment-limited socket test skipped, and one existing dependency
deprecation warning. The final fresh whole-slice review found one Important
cutoff-relative event regression; it was reproduced, fixed, and confirmed
closed with no remaining Critical or Important issue. The consolidated package
was synchronized at `69c49968e77bfd55fa259695089e1f34ac2fddfb`, and exact-head
GitHub Actions run `30185232040` passed the full 4,084-test, dashboard-startup,
Personal Research render, public-wording, PR-range generated-artifact hygiene,
and whitespace matrix. Real-data evidence remains pending; Priority 4 remains
externally incomplete.

Local resource budgets for one supplied package: preview sample 100 rows; manifest 1 MiB; each contract CSV 32 MiB; four contract snapshots combined 64 MiB; source-rights registry 4 MiB; declared rows 250,000 per contract; package traversal 32 entries.

Snapshot inputs are opened as regular files and read from one descriptor with
at most the declared limit plus one byte retained for overflow detection.
Deeply nested manifest JSON or source-rights YAML fails with a stable readable
input error instead of a traceback. Duplicate JSON/YAML mapping keys and
malformed contract headers also fail nonzero, traceback-free, and write-free
through the direct validator and CLI/Make boundaries.

These local bounds do not prove scale, hosted reliability, or market readiness.

No permitted independently reviewed real dataset, accepted expected count/digest, or source-rights proof is on record.

Reproduction contract: `membership_count_and_sha256_at_cutoff_v1`.

The only operating entries for this lane are
`make point-in-time-universe-status MANIFEST=<path>` and
`make point-in-time-universe-preview MANIFEST=<path> TOP_N=20`.

Synthetic fixtures remain test-only and local software evidence cannot complete Priority 4.

Priority 4 remains open until one bounded permitted real dataset is independently reviewed, reproduces the expected membership count and digest, and passes rights, identity, corporate-action, delisting, survivorship, cutoff, partition, reproduction, and leakage gates.

This local evidence does not change independent readiness for actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, or calibration.

It does not provide investment advice; numerical probability remains unavailable without calibration; Q4 evidence and EPS split-basis compatibility remain explicit; synthetic evidence stays test-only; candidate peer evidence remains candidate-context-only.

**Next executable local step:** keep the synchronized Priority 4 local
validator frozen unless a newly reproduced Critical or Important defect
requires reopening it. One bounded permitted real dataset remains the exact
external exit gate. While that dataset and the independent Priority 5 source
and peer evidence are unavailable, advance the provider-neutral hosted-control
contracts in Priority 6. The live accessibility protocol remains separately
blocked in environments that cannot bind the local dashboard socket; do not
substitute AppTest or screenshots for direct keyboard and assisted-technology
evidence.

1. Establish timestamped benchmark membership, research-universe membership, security identity, and observation cutoffs with suitable source rights and immutable manifests.
2. Handle corporate actions, delistings, survivorship, and leakage explicitly; never substitute today's constituents, identifiers, prices, or fundamentals for historical state.
3. Separate raw, normalized, excluded, and analysis-eligible rows; preserve revision lineage and reproducible rejection reasons.
4. Add leakage-safe train/validation/test or walk-forward boundaries and benchmark diagnostics before treating any result as out-of-sample evidence.

**Exit gate:** the exact permitted-real-data condition above. Do not retry an
unavailable provider or infer source access, field scope, or rights from the
local validator.

### Priority 5 — One permitted consensus source and one reviewed peer relationship

**Current lane:** externally dependent; its two evidence gates remain independent.

1. Review exactly one permitted point-in-time consensus source for one ticker and exact fiscal period through the existing read-only source-review contract.
2. After separate human evidence-preserving mapping into the prospective schema, run collection preview. Only if the exact input, ledger, cutoff, mode, and receipt remain unchanged may the operator run `CONFIRM_REVIEWED=1 make earnings-consensus-collection-record INPUT=$COLLECTION_INPUT AS_OF=<same-timestamp> PREVIEW_RECEIPT=<exact-receipt>`.
3. Treat the result as an append-only evidence record; it does not activate readiness or numerical probability, and it cannot bypass actuals, Revenue/EPS comparability, backtesting, or calibration gates.
4. Establish exactly one genuinely reviewed peer relationship with role, rationale, comparability basis, source/as-of evidence, and an explicit independent valuation-anchor decision.
5. Do not broaden coverage, infer a provider, infer peer trust, or let either gate promote the other.

**Exit gate:** one real consensus snapshot and one real peer relationship independently pass technical, temporal, provenance, rights, field-scope, reviewer, and append-only evidence checks. Neither unlocks numerical probability or broad coverage.

### Priority 6 — Controlled hosted operating boundary

**Current lane:** provider-neutral local control contracts can proceed; provider-specific implementation and hosted verification require an explicitly approved identity, storage, host, and operating environment.

**Implemented locally:** `src.hosted_access_control.evaluate_workspace_access`
now provides one pure, provider-neutral, deny-by-default policy decision.
Structural validation, authenticated-principal matching, active membership,
exact workspace matching, least-privilege role/resource/action rules,
append-only research-record protection, stable privacy-safe reasons, and a
privacy-safe audit obligation are independently tested. The module has no
dashboard, ledger, readiness, provider, persistence, environment, network, or
generated-artifact integration. This local contract does not prove hosted
authentication, deployed isolation, audit storage, retention, monitoring,
rollback, incident response, operated capacity, or market validation.

1. Before an environment is approved, define only provider-neutral control contracts, threat boundaries, interfaces, and denial-test harnesses; do not silently choose an identity, storage, logging, or hosting architecture.
2. After explicit environment approval, implement authentication, private-workspace isolation, least-privilege authorization, secret handling, append-only audit logs, retention/deletion controls, monitoring, health checks, backup, rollback, and incident ownership against that exact environment.
3. Test cross-user and cross-workspace denial, audit completeness, retention execution, failure alerts, recovery, and rollback without exposing local research data.
4. Keep hosting, account creation, purchases, credential use, and public deployment behind explicit approval.

**Exit gate:** the actual hosted environment directly proves every claimed control, including an observed rollback rehearsal and named owner. Local code, configuration, or a URL alone is insufficient.

### Priority 7 — Accessibility evidence beyond screenshots

**Current lane:** a first direct local desktop/phone workflow audit is recorded in `docs/ACCESSIBILITY_EVIDENCE.md`; broader local remediation remains executable, while complete keyboard and assisted-technology evidence still requires a suitable review environment.

The 2026-07-23 audit exercised Research Desk -> Discover -> Company Workbench -> Monitor at `1280x720` and `390x844`. All four routes reflowed without document-level horizontal overflow, visible controls retained accessible names, and no duplicate IDs were observed. It reproduced a `3.3:1` contrast defect on the Monitor `Open Discover` action; the primary link-button theme now uses white on `#0b3b36`, and runtime retest measured `12.4:1`. A second test-first slice added a route-preserving `Skip to page answer` link to every Personal Research route and changed primary route sections from `h3` to `h2`. Direct desktop/phone retest verified the correct skip destination and Company Workbench ticker/open parameters, a focusable answer target, continuous `h1` -> `h2` hierarchy, the non-empty nested Monitor `h3`, and no horizontal overflow. This is partial local evidence only. A stable `main` landmark, direct skip-link keyboard behavior, small framework help/dataframe controls, dynamic-announcement coverage, complete keyboard order, zoom, forced-colors, and screen-reader tasks remain open.

`docs/ACCESSIBILITY_TASK_PROTOCOL.md` now defines exact run metadata, result
states, keyboard-only route tasks, write-free authoring validation, 200%/400%
zoom, forced-colors, reduced-motion, screen-reader, target-size, finding, and
completion contracts; the protocol is not completion evidence. Every task
still requires direct current execution in the recorded environment. The
current Streamlit container API has no stable semantic-role parameter, so an
unsafe DOM-mutation workaround is not accepted as `main` landmark evidence.

1. Add automated semantic checks plus keyboard-only navigation, visible focus, focus order, form labels, error association, text resizing, zoom/reflow, color/contrast, reduced-motion, and screen-reader task review.
2. Exercise the complete Research Desk -> Discover -> Company Workbench -> Monitor workflow at desktop and phone widths.
3. Record reproducible defects, environment, assistive technology, severity, remediation, and retest evidence. Do not claim conformance from screenshots or automation alone.

**Exit gate:** automated and manual task evidence covers the complete workflow, all material defects are resolved or explicitly bounded, and any conformance claim matches the tested scope.

### Priority 8 — Independent workflow validation

**Current lane:** externally dependent on non-owner participants.

1. Run 10-20 independent workflow sessions with the target researcher persona; maintain a session protocol that prevents coaching and avoids collecting investment recommendations or unnecessary personal data.
2. Measure task completion, time to first answer, readiness comprehension, trust, misuse risk, perceived performance, and repeat-use intent.
3. Separate usability findings from financial evidence, predictive validity, demand, and product-market fit.

**Exit gate:** 10-20 independent workflow sessions have complete anonymized evidence, reproducible findings, severity decisions, and retest outcomes for material defects. Automated, subagent, owner, or screenshot review does not count.

### Priority 9 — Out-of-sample calibration cohort

**Current lane:** time- and source-dependent; local tooling may advance while events accumulate.

1. Accumulate at least 100 valid leakage-safe out-of-sample events from permitted point-in-time inputs with immutable cutoffs, comparable actuals, revision lineage, exclusions, and reproducible cohort membership.
2. Evaluate declared Brier-score, calibration-bin, benchmark-improvement, missingness, and stability gates without selecting thresholds after seeing results.
3. Keep Revenue and EPS, backtesting and calibration, and technical validity and commercial rights independent.

**Exit gate:** the full cohort passes every predeclared gate on direct current evidence. Numerical Beat/Miss probability remains withheld before that point and remains withheld if the gate fails.

### Priority 10 — Separately approved hypothetical paper-position laboratory

**Current lane:** conditional design only; implementation is not authorized by this roadmap entry.

1. Consider a research-only laboratory for user-authored hypothetical paper positions only through a separate approved design, private-data policy, language review, misuse analysis, and acceptance plan.
2. The design must prohibit recommendations, model-generated sizing, allocation instructions, live holdings, account imports, broker connections, order routing, auto-trading, price-triggered stop/profit instructions, and claims of investment performance.
3. Keep any hypothetical state isolated from evidence truth, company ranking, deterministic forecasts, readiness, and calibration.

**Exit gate:** this priority advances only after separate explicit design approval and direct acceptance evidence. Live brokerage remains out of scope permanently.

## Supporting Backlog: Focused-Cohort Evidence

### P2: FMP One-Ticker Source Smoke

**Goal:** add one controlled keyed free-tier fallback after the public pilot foundation is stable.

1. Configure `FMP_API_KEY` outside Git in the ignored local key file or host secrets.
2. Run `make project-status-check`; only continue if it identifies a reviewed candidate scope.
3. Run `make fmp-smoke TICKER=<ticker>` for one ticker.
4. Run `make imports-validate IMPORT_TICKERS=<ticker>` and `make imports-preview IMPORT_TICKERS=<ticker>`.
5. Apply only if validation passes, preview scope is intended, rejected rows are zero, and source provenance is present.
6. Record a supported, candidate-context-only, still-blocked, skipped, or excluded outcome before any larger batch.

**Dependencies:** an FMP key and an executable reviewed candidate. The current source-proof queues have no unreviewed executable company candidates, so provider reachability alone does not unlock coverage.

**Stop rule:** no broad batch from setup alone. Provider setup/source-boundary review must happen before `make trusted-data-pilot-candidates TOP_N=10` only after source state changes.

### P2: Price History Maintenance

Price coverage uses `PROVIDER=auto` in this fixed order: **Stooq, Yahoo**, optional IBKR read-only when explicitly configured, then keyed FMP, Alpha Vantage, and Finnhub fallbacks. This maintenance lane is finite and read-only until a separately reviewed source-backed change is eligible for the import gate.

**Commercial refresh enforcement implemented:** every concrete price provider now has one exact source ID, automatic-ladder labels must match child identity, and explicit Commercial Research mode reviews each reachable provider for approved rights plus registered `prices` scope before fetch. It rechecks the selected provider before merge or status mutation and fails closed on missing or changed identity. Ordinary research mode retains the existing ladder. No provider was approved or called, no canonical price lineage was added, and readiness remains unchanged.

1. Run the default executable queue: `make price-history-proof-queue TOP_N=25`.
   - `momentum-not-ready` rows describe a readiness state, not a refresh instruction.
   - `unreviewed preferred-history candidates` are the only default queue rows eligible for a narrow reviewed investigation.
   - `reviewed source-limited items` are excluded from the default queue because they remain wait-only.
2. Use audit mode only to inspect reviewed source-limited items: `INCLUDE_REVIEWED=1 make price-history-proof-queue TOP_N=25`.
3. When compatible reviewed evidence exists, use `make price-history-batch-closeout TOP_N=25` to produce the read-only grouped closeout scaffold. It does not record proof rows, stage files, commit, or push.

**Stop rules:** stop on no readiness movement in reviewed scope; no identical source-limit retry unless source behavior or verified OHLCV changes; batch compatible proof evidence intentionally; never commit or push one proof row per ticker by default; pivot to the next roadmap item when no executable candidates.

### P3: 25-50 Company Trusted-Peer Pilot

**Goal:** address the largest analytical-depth gap without inferring trusted peers across the full universe.

This expansion is deferred until after the single reviewed relationship in Priority 5 has direct evidence and the review method and capacity are shown to be repeatable. It remains supporting backlog governed by the Approved Next-Stage Maturity Program, not permission to broaden coverage now.

1. Select 25-50 operating companies from a few clearly comparable industries.
2. Generate candidate peer context from SIC, industry, and product context; label it `candidate_context_only`.
3. Promote a relationship only after source-backed review captures peer source, review date, rationale, as-of context, reviewer-assigned peer role, economic comparability basis, and an explicit valuation-anchor decision.
4. Keep peer trend readiness separate from peer valuation readiness.
5. Require at least two explicitly eligible `core_peer` or `secondary_peer` relationships plus trusted peer price, fundamentals, and valuation inputs before relative valuation appears.

**Dependencies:** a licensed or otherwise trustworthy peer relationship source and reviewed mappings.

**Stop rule:** sector similarity is not trusted-peer proof. Do not target broad-universe peer readiness before the pilot has repeatable evidence.

**Evidence-quality slice implemented:** the source-review template, write-back guard, local provider, readiness engine, and Peer Read-Through Map now preserve and evaluate `peer_role`, `relationship_rationale`, `comparability_basis`, and `valuation_anchor_eligible`. Legacy seven-column relationships remain visible for source-backed trend or result context but fail closed as valuation anchors. Candidate rows remain separate. No existing canonical peer row was assigned a role by inference.

The implemented Peer Read-Through Map is the review surface for this future cohort. This contract improves local methodology but does not satisfy the external trusted-relationship dependency, review existing canonical relationships, or create broad peer coverage by itself.

## Later

### P4: Optional Earnings And Analyst Estimates

Proceed only when a trusted provider supplies supported earnings actual/estimate fields, estimate period, source, and retrieval/as-of date. Date-only and target-price-only data remain `candidate_context_only`; optional context never unlocks DCF readiness or becomes a recommendation.

### P4: Scheduler Maturity

Add scheduled snapshot rotation, alerts, and source monitoring only after at least one provider pilot proves deterministic batch limits, provenance, rejection handling, and proof-ledger recording. Daily price and filing checks may be read-only; imports still require validation, preview, and source gates. The local Change Monitor is not itself a hosted alerting service.

### Later: Broader Peer Expansion

Expand beyond the peer pilot only after trusted relationship sourcing, review capacity, and lane-level quality checks are repeatable.

### Later: Product Direction Decision

Use `docs/PRODUCT_DIRECTION_DECISION.md` after hosted-preview, controlled-pilot, and trusted-peer evidence exist. Choose explicitly among a portfolio-quality research prototype, maintained research tool, or operated research platform; keep the decision provisional while those dependencies remain external.

## Dependencies And Manual Gates

| Item | State | What the repo can do | What remains external |
| --- | --- | --- | --- |
| Hosted demo | repo-ready | deterministic demo profile, deployment guide, and local public checks | hosting account, verified public URL, browser review |
| PR engineering evidence | hosted workflow verified | pull-request-only, least-privilege test and read-only product gate with direct successful GitHub evidence | reverify every later revision; independent human review remains external |
| Operated controls | contract-ready | independent fail-closed states for account controls, incident response, rollback, and owner capacity | hosted accounts, named coverage, and supervised operating rehearsal |
| FMP fallback | optional key missing | one-ticker smoke, validation, preview, provenance gate | `FMP_API_KEY` outside Git |
| Alpha Vantage / Finnhub | optional keys missing | capped fallback interfaces and source-state checks | provider keys and a reviewed use case |
| Direct commercial price refresh | fail-closed locally | exact provider identity plus pre-fetch and pre-mutation rights/`prices`-scope enforcement | one reviewed exact provider with approved rights and registered `prices` scope; row-level lineage and payload review remain separate |
| Trusted peers | source-gated | candidate/trusted separation, role/comparability/anchor contract, and proof workflow | licensed or otherwise trustworthy reviewed relationships, roles, rationales, and comparability decisions |
| Earnings / estimates | intentionally locked | optional-context states and import gates | trusted provider/manual rows with supported fields |

## Success Gates

### Independent Engineering Gate

- `.github/workflows/commercial-research-beta.yml` remains pull-request-only and least privilege.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_github_actions_workflow.py -q`
- GitHub reports the current PR revision's `Commercial Research Beta / local-engineering-gate` result.
- Independent human review is requested and evaluated separately from automation.

### Public Demo Gate

- `make demo-data-check`
- `make demo-dashboard-smoke`
- `make demo-dashboard-render-smoke`
- `make public-check`
- `make browser-qa-evidence`
- `make public-wording-check`
- `make pilot-readiness-check TOP_N=10`
- `make diff-hygiene-summary`
- `git diff --check`

### Source-Backed Apply Gate

- A narrow, intended ticker scope.
- Source provenance and relevant as-of context.
- `make imports-validate IMPORT_TICKERS=<ticker>` passes.
- `make imports-preview IMPORT_TICKERS=<ticker>` is narrow and rejected rows are zero.
- Readiness and proof evidence are rebuilt after an approved apply.

## Permanently Out Of Scope

- Broker execution, account actions, order routing, or auto-trading.
- Direct buy/sell instructions or investment recommendations.
- Fabricated prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics.
- Promoting candidate peers, stale rows, screenshots, or provider setup into trusted readiness proof.
