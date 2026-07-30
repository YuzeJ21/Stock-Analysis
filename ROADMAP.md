# Roadmap

Stock Research Command Center is an **Evidence-First Research Workbench** for serious individual equity researchers and small research teams. Its operating rule is **data readiness first, analysis second, research decision last**.

It is research-only: no investment advice, recommendation, company ranking, broker integration, order routing, auto-trading, direct buy/sell instruction, allocation, position sizing, stop-loss, take-profit, or fabricated evidence. The active roadmap is this file; detailed delivery history lives in [Completed Milestones](docs/COMPLETED_MILESTONES.md), accessibility findings in [Accessibility Evidence](docs/ACCESSIBILITY_EVIDENCE.md), point-in-time-universe remediation in [Point-in-Time Universe Review History](docs/internal/POINT_IN_TIME_UNIVERSE_REVIEW_HISTORY.md), and persistent execution boundaries in the [Commercial Research Beta Continuation Contract](docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md).

## Current Truth

- Master universe rows: use `make project-status` or `make status-check TOP_N=5`.
- Active research rows: use `make project-status` or the dashboard Home page.
- Lane readiness: use `make readiness-ops-center`.
- Historical proof versus current readiness: use `make proof-readiness-reconciliation TOP_N=20`. It is a current-snapshot audit; historical proof cannot promote current readiness.
- Stale-readiness impact: use `make readiness-preview TOP_N=20`. It computes future proposed states in memory, writes no files, and does not authorize staging or a readiness rebuild.
- Source/provider state: use `make session-source-preflight` and `make provider-setup-checklist`.
- Package/share state: use `make pilot-readiness-check TOP_N=10`, `make public-check`, and `make browser-qa-evidence`.
- Commercial-beta state: use `make commercial-beta-check`, `make commercial-beta-performance-gate`, and `make commercial-beta-release-check`. These are local evidence only; they do not refresh data and do not prove market validation.
- Point-in-time universe software: only `make point-in-time-universe-status MANIFEST=<path>` and `make point-in-time-universe-preview MANIFEST=<path> TOP_N=20` are supported. Both are read-only.

The product deliberately separates the tracked master universe, active universe, and analysis-ready subset. It must never imply that the whole tracked universe is analysis-ready.

The tracked June 7 readiness snapshot remains stale under this roadmap's declared-date policy. An excluded July 21 local generated working-data snapshot is not committed PR evidence. A read-only preview reported zero stable readiness changes, but that observation does not authorize staging or a readiness rebuild. Rerun the current commands instead of copying counts into documentation.

`historical_supported_currently_blocked`, `explicit_ticker_change`, and `current_canonical_row_missing` are distinct reconciliation outcomes. Current saved readiness remains authoritative, and reconciliation does not establish the historical cause of a transition, restore canonical data, or report current readiness totals.

The stale readiness continuation gate follows declared source dates, never file mtimes. `make readiness-preview TOP_N=20` does not make saved readiness current, does not refresh data, and is not current readiness counts or rebuild approval; provider ordering and ranking output remain planning context only until a separate intentional reviewed write runs `make readiness`.

Primary research flow: **Research Desk -> Discover -> Company Workbench -> Monitor**.

Public visitor flow: **Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History**.

Operator source/proof work remains separate. Data Health and Proof History are Advanced Evidence in Personal Research mode. Empty ledgers stay empty; candidate context stays untrusted.

Data Health and Proof History stay inside Personal Research mode and retain `Return to Company Workbench`; the detour does not change readiness. The direct-open loading state preserves Selected ticker -> `Use now` -> `Still withheld` -> `Open Data Health`, a 44px primary action, at least 50px result rows, no horizontal overflow, no traceback, and the desktop four-column layout. Phone first-action density, Advanced data health cards, Auto-refresh status, and Session Source Preflight are workflow evidence only. This does not prove market validation, does not change readiness, source, research, or generated-artifact state, and does not prove hosted behavior, accessibility conformance, reviewer validation, demand, or product-market fit.

Stage A-G labels are continuation maturity lanes only; they do not replace the numbered Stage 0-6 exit gates. Stage B — local field-proof audit and operator hardening is complete locally. A blocked priority does not become complete; classify it once and move to the next safe executable priority.

## Now: Commercial Research Beta Foundation

**Current product stage:** local Commercial Research Beta release candidate and controlled portfolio/demo package, not a hosted or commercially launched product.

**Positioning:** a maintained evidence-first research tool candidate, not a smaller Bloomberg, Koyfin, TIKR, Fiscal.ai, AlphaSense, Quartr, or QuantConnect.

**What works locally**

- Research Desk frames the saved cohort and change state; Discover selects a readiness-backed company; Company Workbench composes trends, valuation, forward scenarios, evidence, and authoring; Monitor reviews verified change and research discipline.
- Research Decision Lab supports read-only composition plus append-only thesis, counter-thesis, evidence, catalyst, invalidation, scenario-assumption, and outcome records through validate -> preview -> explicit confirm.
- SEC quarterly actuals preserve source lineage. EPS split basis remains unverified without explicit proof. Q4 actuals require an explicit SEC-filed Q4 table; Q4 is never derived.
- Historical Valuation Regime, Source Freshness Timeline - Implemented, Research Comparison View - Implemented, Peer Read-Through Map, Scenario Lab, Research Outcome Review, and Catalyst Evidence Timeline stay fail-closed when their ledgers or source inputs are empty. Historical-valuation numeric loading also rejects blank or malformed numerator/denominator evidence per row instead of coercing it to zero or discarding valid sibling rows.
- Calculation software supports price setup, drawdown, volatility, beta, Sharpe/Sortino, DCF/scenarios, valuation context, deterministic nowcast contracts, walk-forward review, and point-in-time-universe validation.
- Quant interpretation eligibility is implemented locally at `195ea18da9d1d6e06c36f8320509ccde46cdaa57`: one shared, fail-closed overlay keeps valuation, indicator, and review/risk calculations and readiness independent while classifying their interpretation as current context, historical/review-only, or withheld.
- Commercial source-rights, refresh-operation, provider-neutral authorization, workspace-isolation, audit-obligation, retention, monitoring, incident, and rollback contracts are locally testable. Local contracts do not prove hosted operation.
- Public/package/release gates and current-head automation verify code, wording, route rendering, hygiene, and research boundaries. Automated evidence is not independent human review.

**Current truthful limitations**

- Real semiconductor nowcast coverage remains `awaiting_point_in_time_consensus`.
- Numerical Beat/Miss probability remains `awaiting_calibration_evidence` and withheld until at least 100 valid leakage-safe out-of-sample events pass every predeclared gate.
- A saved artifact being current relative to local files does not render its latest market observation current. Current-market interpretation requires an independent observation-recency state.
- Local market-observation recency is implemented as a read-only, independently fail-closed check of the selected local `prices.csv` path. Its exact policy is seven calendar days from the dashboard review date, not an exchange-session SLA. Permitted market-data source rights and hosted freshness remain external gates.
- Structured external provenance and exact-source rights proof for the current local quant inputs remain absent. The overlay therefore leaves local quant results historical/review-only or withholds them where the required proof is absent; it does not establish a current-market claim, hosted operation, calibration, nowcast activation, or commercial completion.
- One permitted independently reviewed real point-in-time universe package, one permitted point-in-time consensus source, and one genuinely reviewed peer relationship are not on record.
- Independent beta sessions completed: zero. The local protocol is ready, but it is not user-validation or demand evidence.

## Next: Ordered Maturity Work

Select the first priority with a safe executable task. If its next gate needs an unavailable source, account, environment, reviewer, or elapsed event history, classify it once under **Externally blocked** and continue to the next executable priority. Passing local tests never completes an external gate.

Documentation and routing reconciliation is complete locally. Reopen it only when current repository evidence reproduces contract drift.

The bounded observation-recency UX repair is complete locally. Research Desk,
Discover, and Monitor now show one profile-lane interpretation; Company
Workbench shows one selected-ticker interpretation. Exact selected/profile/SPY/
QQQ dates, machine states, policy, path, and excluded-date diagnostics remain
inside responsive Advanced evidence. A direct four-route browser matrix at
`1280x720` and `390x844` verifies one summary, four independently labelled
cards, phone single-column layout, and no evidence-container horizontal
overflow without writing screenshots or other artifacts.

Immediate approved local reliability queue:

Completed local item: `1. Add shared provenance and recency eligibility to valuation, indicator, and review-metric interpretation without coupling their independent readiness states.` The shared overlay is implemented at
`195ea18da9d1d6e06c36f8320509ccde46cdaa57`; this historical queue entry is not
an open task, and the independent historical-valuation numeric-integrity repair
did not substitute for it.

Completed local framework reliability item: `1. Close the same-document
Streamlit transport reliability evidence.` Exact local commit
`d68ab27bee9c07c450faeb866b08cbf13638b56f`
passed 4,381 tests, the required render/public/commercial-beta/pilot gates, and
all 12 six-route/two-viewport browser results. Every result reported zero
deprecated-component warnings, bridge iframes, bridge focusable descendants,
and bridge height; the owned bounded server-output capture also reported zero
deprecated warnings. The same 18 generated paths remained excluded. Hosted
exact-head CI still requires the intentional push and is not local evidence.

1. Continue the remaining safe automated Priority 7 accessibility work.

Priority 7 accessibility remains the next numbered maturity priority. Its remaining safe automated work follows these bounded reliability repairs; true zoom, forced colors, reduced motion, screen-reader, and independent-human evidence remain external until a suitable environment exists.

### Priority 1 — Legacy portfolio, ranking, and action-language quarantine

Priority 1 — completed locally. Legacy portfolio, ranking, position, cost-basis, picks, entry-zone, disposition, and transaction-like surfaces are Operator-only compatibility utilities labelled `Legacy research utility — not part of Personal Research Mode`. Public and Personal Research routes fail closed. Retained compatibility code cannot feed Company Workbench, Research Decision Lab, readiness, recommendations, sizing, or transaction behavior.

### Priority 2 — Stage B field-proof audit and operator hardening: completed locally

Stage B — completed locally. This is prospective-only; legacy narrative proof is not upgraded, and an absent ledger is a valid empty state. `technical_write_eligible` and `commercial_evidence_eligible` remain independent. `make prospective-field-proof-audit` and preview expose append history, current/superseded state, blockers, per-row technical/commercial answers, and receipt revalidation without writes. Stage B is the second approved local priority after legacy surface quarantine. There is no readiness mapping; any activation requires a separate design. Activation remains non-active and separately designed. No sample field-proof rows are checked in.

`make prospective-field-proof-status`, `make prospective-field-proof-preview INPUT=<reviewed_field_proof.csv> AS_OF=<utc-cutoff>`, and `make prospective-field-proof-record INPUT=<same-file> AS_OF=<same-cutoff> PREVIEW_RECEIPT=<exact-receipt> CONFIRM_REVIEWED=1` preserve `preview_receipt_persisted=false` and `receipt_revalidation_required=true`. The preview receipt binds ledger, input, cutoff, commercial mode, and source-rights registry. Audit and preview do not activate readiness; the audit does not update canonical data, does not update proof-readiness reconciliation, and does not activate Company Workbench.

### Priority 3 — In-app research-record authoring: completed locally

Priority 3 — completed locally after direct desktop/phone runtime review and the required automated acceptance matrix. Thesis, evidence, catalyst, and outcome records are all available in the collapsed Company Workbench composer. A valid record requires an exact preview and explicit confirmation before save. Drafts are untrusted and preview receipts are session-only. Production tests never append repository ledgers; persistence tests use temporary ledgers. automated generation cannot become reviewer-authored evidence. A saved record cannot change readiness, forecasts, probabilities, recommendations, or any other ledger.

Hardening commit `07758114c` closes the confirmation race: all three append engines share one resolved-ledger cooperative lock, receipts bind resolved ledger identity, every new preview resets confirmation, and uncertain post-append teardown requires one-shot read-side reload before success.

Final integrity commit `e3a090dba` ensures confirmation appends only the receipt-matched recomputed record and enforces one readable active thesis lineage: revisions must supersede the exact active entry and preserve its thesis ID. The Company Workbench locks and explains that relationship, with temporary-ledger create -> revise -> reload coverage.

Confirmation-integrity commit `5a6c55921` binds every displayed preview field, preview time, and destination label to the exact receipt. If an append raises after it may have written, confirmation returns one-shot `save_pending_reload` with the exact record ID unless the locked ledger is provably unchanged; it never invites a blind duplicate retry.

Priority 4's local validator is frozen; its permitted real-data exit gate remains externally incomplete. Priority 6's provider-neutral authorization contract is complete locally; hosted implementation remains environment-dependent. Priority 7 accessibility remediation is the next safe executable local lane.

### Priority 4 — Point-in-time benchmark and universe foundation

The approved design is `docs/superpowers/specs/2026-07-23-point-in-time-universe-foundation-design.md`. It remains isolated from the current ticker-centric universe.

Implemented locally: read-only immutable-package status/preview with ten independent states: manifest, technical, temporal, identity, membership, corporate action, delisting, source rights, reproduction, and leakage. Synthetic fixtures remain test-only and local software evidence cannot complete Priority 4.

Priority 4 remains open until one bounded permitted real dataset is independently reviewed, reproduces the expected membership count and digest, and passes rights, identity, corporate-action, delisting, survivorship, cutoff, partition, reproduction, and leakage gates. The controls for corporate actions, delistings, survivorship, and leakage remain explicit and independent.

This local evidence does not change independent readiness for actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, or calibration.

It does not provide investment advice; numerical probability remains unavailable without calibration; Q4 evidence and EPS split-basis compatibility remain explicit; synthetic evidence stays test-only; candidate peer evidence remains candidate-context-only.

Digest method: `membership_count_and_sha256_at_cutoff_v1`. Supported commands are exactly `make point-in-time-universe-status MANIFEST=<path>` and `make point-in-time-universe-preview MANIFEST=<path> TOP_N=20`.

Resource limits and detailed remediation evidence live in `docs/internal/POINT_IN_TIME_UNIVERSE_REVIEW_HISTORY.md`. Priority 4 remains externally incomplete.

Local resource budgets for one supplied package: preview sample 100 rows; manifest 1 MiB; each contract CSV 32 MiB; four contract snapshots combined 64 MiB; source-rights registry 4 MiB; declared rows 250,000 per contract; package traversal 32 entries. These local bounds do not prove scale, hosted reliability, or market readiness. No permitted independently reviewed real dataset, accepted expected count/digest, or source-rights proof is on record.

### Priority 5 — One permitted consensus source and one reviewed peer relationship

Review one exact-source, permitted, point-in-time consensus snapshot for one ticker/fiscal period and one independently sourced peer relationship. Technical validity, rights, Revenue, EPS, comparability, reviewer decision, append history, and valuation-anchor eligibility remain independent.

Neither item unlocks probability, broad coverage, readiness in another lane, or a company conclusion.

Set `SOURCE_INPUT=<reviewed_source_export.csv>`, then run `make earnings-consensus-source-review INPUT=$SOURCE_INPUT PROVIDER=<source_id> AS_OF=<timestamp>` before collection preview. After separate human review and explicit evidence-preserving mapping, set `COLLECTION_INPUT=<prospective_consensus.csv>` and run `make earnings-consensus-collection-preview INPUT=$COLLECTION_INPUT AS_OF=<same-timestamp>`. Only after exact preview review may `CONFIRM_REVIEWED=1 make earnings-consensus-collection-record INPUT=$COLLECTION_INPUT AS_OF=<same-timestamp> PREVIEW_RECEIPT=<exact-receipt>` create an append-only evidence record. It does not activate readiness or numerical probability. Never infer an explicit provider.

### Priority 6 — Controlled hosted operating boundary

Provider-neutral, deny-by-default workspace authorization is complete locally. `src.hosted_access_control.evaluate_workspace_access` creates an append-only, privacy-safe audit obligation. The module has no dashboard, ledger, readiness, provider, persistence, environment, network, or generated-artifact integration. It does not prove hosted authentication, deployed isolation, audit storage, retention, monitoring, rollback, incident response, operated capacity, or market validation.

The actual environment must prove authentication, cross-user/cross-workspace denial, least privilege, durable persistence, append-only audit, retention/deletion, health monitoring, recovery, rollback, and named operating ownership. A local contract or URL alone is insufficient.

**Exit gate:** the actual hosted environment directly proves every claimed control, including an observed rollback rehearsal and named owner.

### Priority 7 — Accessibility evidence beyond screenshots

The approved narrow remediation is implemented and has reproducible local direct-browser evidence at exact tested implementation anchor `0000c97e7db17e5d4353e30e976f2b7dec6bfd46`. `make research-accessibility-browser-check` first verified a clean product/code/test/docs tree, classified and excluded exactly 18 unstaged generated CSV/output paths, and verified the rendered Stock Research Command Center `Demo` profile before attaching the commit or profile. It then passed all eight Research Desk, Discover, ticker-bound Company Workbench, and Monitor cases at `1280x720` and `390x844`: after initial focus was cleared, one physical Tab focused the sole skip link, whose box was fully inside both horizontal and vertical viewport bounds before Enter preserved the route and focused the answer; the labelled workflow navigation and every applicable route link were inside the viewport, and each link was at least `44px` high; all four actually rendered eligible Discover actions had unique ticker-bound names; focused summaries exposed a solid three-pixel outline; and rejected empty-thesis validation bound, described, and focused Thesis Id while retaining one global alert. The live Workbench regression then changed the draft, proved the bridge-owned Thesis Id node and relationships were removed, and proved the next validation associated only `effective_at is required` with Effective At on desktop and phone. The gate uses no DOM-order enumeration or programmatic skip-link focus as keyboard evidence; rejects non-loopback or mismatched servers and dirty implementation evidence without attributing a local commit/profile; fails closed without Chrome/Playwright; assumes no Discover row count; and writes no JSON, timing, report, screenshot, readiness, canonical-data, or ledger artifact.

The separately reviewed framework-safe semantic-main slice is implemented and has direct local browser evidence at exact tested implementation anchor `d1328eaa4d08cf08ec2b70939e4e031ee5f907b0`. The focused gate tests returned `22 passed`; `make research-accessibility-browser-check` again verified the loopback Stock Research Command Center `Demo` identity and a clean product tree while excluding the same 18 unstaged generated paths, then passed all 12 Research Desk, Discover, ticker-bound Company Workbench, Monitor, Research Data Health, and Research Proof History cases at `1280x720` and `390x844` with no failures. Every initial DOM and every DOM after a genuine same-document Streamlit `notRunning` -> `running` -> `notRunning` script cycle had exactly one role-based main with exact `role="main"`, `id="research-main"`, `aria-label="Stock research workspace"`, one contained answer target, one level-one heading, and host bridge status `applied`; only that same-document rerun/probe phase preserved the exact route with zero top-level navigation. A hidden inert mutation probe also required the live bridge observer to restore `applied` before the probe was removed. Separately, every case deliberately navigated to an explicit different Research route and back, waited for marker/stability/exact H1, then required the full away and return URLs, including the complete query string and empty fragment with the ticker parameter where present, before repeating semantic-main, runtime, and applicable primary/secondary navigation assertions. The physical-Tab skip target was focused inside the unique initial main; all cases had no console/page error, rendered traceback, or horizontal overflow across the recorded phases. The controlled native radio event and installed Streamlit test-state transition are framework engineering evidence only, not pointer/keyboard/mobile-sidebar interaction credit or a public cross-version compatibility guarantee. The gate remained repository/data read-only and produced no repository artifact.

This closes the five narrow reproduced defects and the stable route-level semantic-main defect for the recorded local automated browser matrices only. Complete independent-human keyboard review, 200%/400% zoom and reflow, forced colors, reduced motion, screen-reader tasks, dynamic announcements, loading/empty/withheld/stale/failure states, remaining small framework controls, and material-defect retests. Automated DOM checks and screenshots are supporting engineering evidence only; they do not prove WCAG conformance, screen-reader usability, hosted behavior, or independent-human accessibility validation.

The earlier K01/K03/K04/K05/K06/K09 and mobile-navigation failures remain historical evidence in `docs/ACCESSIBILITY_EVIDENCE.md`; the new direct gate supersedes those five narrow implementation findings only at its recorded product anchor and viewports. Priority 7 remains incomplete.

The earlier Streamlit normalization to `target="_blank"` also remains historical evidence; the route-preserving correction continues to use fragment-only `#public-page-answer` with `target="_self"`. The current gate directly verifies the resulting same-route focus transfer without treating the historical defect as current.

Use `docs/ACCESSIBILITY_TASK_PROTOCOL.md`; the protocol is not completion evidence. The corrected same-page target is `#public-page-answer`; incomplete direct tasks remain `blocked_environment`. No WCAG conformance claim is made.

### Priority 8 — Independent workflow validation

Run 10-20 independent workflow sessions with the target researcher persona through Research Desk -> Discover -> Company Workbench -> Monitor. Owner-led, automated, fixture, and screenshot sessions do not count.

Measure task completion, time to first useful answer, readiness comprehension, evidence tracing, authoring friction, trust, misuse risk, perceived performance, repeat-use intent, and the most important missing workflow. Use voluntary minimal-data capture, withdrawal handling, a deletion date, anonymized evidence, reproducible findings, severity decisions, and material-defect retests.

The local invitation, scorecard, log schema, runbook, and closeout checklist are ready. This does not prove demand, retention, product-market fit, or financial validity.

### Priority 9 — Out-of-sample calibration cohort

Accumulate at least 100 valid leakage-safe out-of-sample events from permitted point-in-time inputs with immutable cutoffs, comparable actuals, revision lineage, exclusions, missingness, and reproducible cohort membership.

Evaluate predeclared Brier score, calibration bins, constant-benchmark improvement, sample sufficiency, missingness, stability, and temporal/cohort leakage. Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting, and calibration remain independent. Probability stays withheld unless every applicable gate passes.

### Priority 10 — Separately approved hypothetical paper-position laboratory

Implementation is not authorized. A separate approved design must cover research-only intent, private-data policy, language, misuse analysis, and acceptance. It must prohibit recommendations, model-generated sizing, allocation, live holdings, account imports, brokers, order routing, auto-trading, stop/profit instructions, and performance claims. Live brokerage remains out of scope permanently.

## Externally blocked

| Stage | Classification | Evidence checked | Exact unblock condition |
| --- | --- | --- | --- |
| Priority 4 | `point_in_time_benchmark_universe_and_rights_required` | No permitted independently reviewed real package is on record. | Supply one bounded permitted package and independent expected-count/digest review; pass rights, identity, corporate-action, delisting, survivorship, cutoff, partition, reproduction, and leakage gates. |
| Priority 5 consensus | `permitted_point_in_time_consensus_and_rights_required` | No permitted exact-period point-in-time input or approved exact-source field rights are on record. | Configure one permitted source or reviewed CSV, approve exact-source rights/field scope, then validate and preview one ticker/period without inferring a provider. |
| Priority 5 peer | `trustworthy_peer_source_and_review_required` | No genuinely reviewed relationship is on record. | Provide source/as-of evidence and reviewer capacity; record role, rationale, comparability, and an explicit valuation-anchor decision. |
| Priority 6 | `hosted_account_and_controls_required` | No verified hosted identity/persistence environment or URL is on record. | Approve the exact environment and directly verify authentication, isolation, audit, retention, monitoring, backup, rollback, incident response, and named owner capacity. |
| Priority 7 | `accessibility_manual_review_environment_required` | Partial desktop/phone evidence exists; true zoom, forced colors, reduced motion, and screen-reader coverage are incomplete. | Provide a suitable review environment and complete the task protocol plus material-defect retests. |
| Priority 8 | `independent_reviewers_required` | The protocol is locally ready; zero independent sessions are on record. | Complete 10-20 independent target-persona sessions with anonymized evidence and retest material defects. |
| Priority 9 | `calibration_cohort_required` | Valid real leakage-safe calibration events: zero. | Accumulate at least 100 permitted events and pass the predeclared calibration/benchmark gates. |

Unavailable dependencies are recorded once and not retried until relevant external state changes. This is the Approved Next-Stage Maturity Program; blocked work must move to the next safe executable priority.

## Later

### Focused price-history maintenance

`PROVIDER=auto` remains **Stooq, Yahoo**, optional IBKR read-only, then keyed FMP, Alpha Vantage, and Finnhub fallbacks. An explicit provider identity and commercial rights/`prices` scope are required before commercial fetch or mutation.

- `momentum-not-ready` is a readiness state, not a refresh instruction.
- Only `unreviewed preferred-history candidates` are default investigation candidates.
- Inspect `reviewed source-limited items` only with `INCLUDE_REVIEWED=1`.
- Use `make price-history-batch-closeout TOP_N=25` only when compatible reviewed evidence exists.
- stop on no readiness movement in reviewed scope; no identical source-limit retry unless source behavior or verified OHLCV changes; batch compatible proof evidence intentionally; never commit or push one proof row per ticker by default; pivot to the next roadmap item when no executable candidates.

Provider setup/source-boundary review comes before candidate loops. The current source-proof queues have no unreviewed executable company candidates. Run `make provider-setup-checklist`; run `make trusted-data-pilot-candidates TOP_N=10` only after relevant source state changes.

### Focused peer expansion

A 25-50 company trusted-peer pilot is governed by the Approved Next-Stage Maturity Program and begins only after the single reviewed relationship in Priority 5 proves trustworthy sourcing and repeatable review capacity. Candidate sector similarity is not peer proof.

### Research-oriented monitoring

After source and workflow evidence support it, add source-linked filing/catalyst changes, thesis reminders, watchlists, and daily/weekly “what changed” recaps. Any summary must be cited to approved evidence and unable to change readiness, forecasts, or reviewed records automatically.

### Product-direction decision

Use `docs/PRODUCT_DIRECTION_DECISION.md` after hosted, independent-review, trusted-peer, data-economics, operating-capacity, and repeat-use evidence exists. Default direction remains a maintained personal/small-team research tool; an operated platform is not authorized by feature volume or test counts.

## Completed with evidence

Detailed evidence is in `docs/COMPLETED_MILESTONES.md`; this section is an index, not duplicated chronology.

### P0: Profile Truth And Local Research Change Workflow

Implemented and regression-gated. Snapshot-only and source-backed changes stay distinct; missing change evidence is not a negative company signal.

### P0: Research Thesis And Evidence Journal

Implemented with append-only provenance, invalidation, conflicting evidence, outcome review, and no automatic readiness or forecast promotion.

### P0: Performance Release Candidate

Passed on the fixed `data/demo/manifest.json` profile with shell, first useful answer, warm/cold settle, and p90 contracts. `make commercial-beta-performance-gate` and `make commercial-beta-release-check` are the current rerun paths.

### P1 local prerequisite: Hosted operating contracts

Local deployment and operating contracts are complete; actual hosted verification remains externally blocked under Priority 6.

### P1 local prerequisite: Independent beta protocol

The independent-session protocol is locally complete; actual sessions remain externally blocked under Priority 8.

### P2: Scenario Lab - Implemented

Scenario assumptions are explicit research context and cannot become recommendations, rankings, or deterministic forecast inputs.

### Earnings Nowcast real-data safety infrastructure

Deterministic synthetic-fixture software, point-in-time consensus contracts, actuals lineage, backtest, and calibration gates are implemented. Real-company coverage and predictive accuracy are not established.

### Bounded SEC cash-generation evidence

The one-company adapter acceptance harness and bounded exact-source review started with NVIDIA Q1 FY2027; the later AMD Q1 FY2026 review established bounded two-company portability. They do **not** prove production activation, broad history, Q4 portability, or market validation. The preview does not activate Company Workbench or readiness in ordinary routes and does not prove broad company coverage.

AMD Q1 FY2026 uses accession `0000002488-26-000076`. The one explicit user-flow composition can expose accepted preview evidence only through an opt-in route; it does not prove a second company at the historical NVIDIA-only milestone and never promotes production state.

Valuation and backtest safeguards reject non-finite valuation inputs; require a canonical real `YYYY-MM-DD` denominator period end; reject blank, malformed, and non-calendar denominator period ends; reject post-cutoff retrieval evidence; canonicalize Revenue/EPS independently through explicit `supersedes_source_ref` lineage; retain one event per ticker/period; withhold ambiguous leaves per metric so one metric does not suppress the other; and use cutoff-bounded prior-year benchmarks so post-cutoff revisions cannot leak.

### Research Decision Lab

Implemented locally — Research Decision Lab. Stage 4 — Documentation and release evidence: completed locally. Read-only composition, Workbench integration, Monitor discipline review, and release evidence passed without trading or recommendation behavior.

This does not prove source coverage, predictive accuracy, investment performance, independent adoption, hosted reliability, commercial demand, competitive superiority, or product-market fit.

### Methodology and packaging maturity

Current methodology maturity supports a transparent local research prototype and controlled beta candidate. It does not prove broad real-company coverage or market validation. Phone first-action density, answer-first layout, Advanced data health cards, auto-refresh status, Session Source Preflight, commercial-beta release evidence, and source-rights boundaries are locally verified product/package evidence only.

## Dependencies And Manual Gates

| Item | Local state | Manual/external gate |
| --- | --- | --- |
| Readiness/data | fail-closed software and reviewed local artifacts | source rights, exact-source rows, validate/preview/apply, rebuild, and proof |
| Providers | provider-neutral contracts and capped adapters | explicit provider key/rights/scope and reviewed use case |
| Hosting | architecture and authorization contracts | approved account/environment plus direct operating evidence |
| Accessibility | partial direct desktop/phone evidence | remaining environment/tasks and material-defect retests |
| Reviewer validation | complete privacy-safe protocol | 10-20 independent sessions |
| Calibration | predeclared methodology | at least 100 valid permitted events |

## Success Gates

### Independent engineering gate

- Current-head GitHub Actions result, not a previous revision.
- Full tests, dashboard startup, Personal Research route rendering, public wording, generated-artifact hygiene, and whitespace.
- Independent human review remains separate from automation.

### Public/demo gate

- `make dashboard-smoke`
- `make research-dashboard-render-smoke`
- `make public-wording-check`
- `make public-check`
- `make commercial-beta-release-check`
- `make pilot-readiness-check TOP_N=10`
- `make diff-hygiene-summary`
- `git diff --check`

### Source-backed apply gate

A narrow intended scope, exact-source rights/provenance, validation, preview, rejected-row review, explicit apply/skip decision, rebuilt readiness, and proof-ledger evidence are all required. Candidate context, setup, screenshots, local contracts, or historical proof cannot substitute.

## Permanently Out Of Scope

- Investment advice, direct buy/sell instructions, company rankings, expected-return scores, or automated stock picking.
- Broker execution, account imports, live holdings, order routing, or auto-trading.
- Model-generated sizing, allocation, stop-loss, take-profit, or post-earnings price prediction.
- Fabricated data, forecasts, probabilities, peers, events, sources, timestamps, rights, reviewers, demand, or recommendations.
- Promoting candidate context, stale rows, synthetic fixtures, screenshots, provider setup, or empty ledgers into trusted evidence.
