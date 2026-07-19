# Roadmap

Stock Research Command Center follows one principle: **data readiness first, analysis second, research decision last**. It is research-only software: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

This is the active plan only. Completed delivery history lives in [Completed Milestones](docs/COMPLETED_MILESTONES.md).

## Current Truth

Use live, read-only commands instead of static counts:

- Master universe rows: use `make project-status` or `make status-check TOP_N=5`.
- Active research rows: use `make project-status` or the dashboard Home page.
- Lane readiness: use `make readiness-ops-center`.
- Stale-readiness impact: use `make readiness-preview TOP_N=20`; it computes proposed stable states in memory, writes no files, and does not make saved readiness current.
- DCF price-lineage impact: use the independently labeled section in the same `make readiness-preview TOP_N=20` output; it audits the exact latest usable price row without changing DCF readiness or inferring provider provenance.
- Source/provider state: use `make session-source-preflight` and `make provider-setup-checklist`.
- Package/share state: use `make pilot-readiness-check TOP_N=10` and `make public-check`.
- Commercial-beta contract state: use `make commercial-beta-check`; this is local contract evidence, not hosted or operated proof.
- Commercial-beta release-candidate state: use `make commercial-beta-release-check`; browser timing remains separate generated evidence.
- Persistent continuation contract: use [Commercial Research Beta Continuation Contract](docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md); it requires repo-truth-first execution, one-time external classification, and direct evidence for every completion claim.

The product deliberately separates the tracked master universe, active universe, and analysis-ready subset. It must never imply that the whole tracked universe is analysis-ready.

Default personal-research flow: **Research Desk -> Discover -> Company Workbench -> Monitor**.

Public visitor flow remains: **Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History**. Operator mode remains the source/proof workflow. Data Health and Proof History are Advanced Evidence in Personal Research mode, not equal primary destinations.

## Now: Commercial Research Beta Foundation

**Goal:** turn the proven Personal Research workflow into a controlled, rights-aware beta foundation without claiming hosting, licensed broad coverage, calibrated prediction, or commercial launch readiness.

1. **Implemented locally:** the source-rights registry fails closed in explicit commercial mode; unverified Yahoo/yfinance rights remain research-only.
2. **Implemented locally:** a deterministic maximum-50 focused-cohort matrix separates usable, partial, candidate-only, blocked, and excluded lanes without broad-universe readiness claims.
3. **Implemented locally:** quarterly Revenue/EPS trend and exact-period Forward View contracts preserve revision lineage, production provenance, freshness downgrades, no-derived-Q4 policy, and independent calibration gates.
4. **Implemented locally:** controlled refresh and private-beta readiness contracts describe deterministic failure handling and external account requirements without enabling automatic apply or claiming hosted capabilities.
5. **Implemented locally:** research-route render smoke, desktop/phone performance contracts, and a consolidated read-only release check verify the local candidate without refreshing data or weakening blocked states.
6. **Implemented locally:** the Evidence Activation Layer adds a five-company Earnings Nowcast readiness board, fail-closed consensus source status, append-only prospective snapshot planning, point-in-time valuation regime context, research outcome learning, and catalyst evidence timelines inside the existing four-page workflow.
7. **Implemented locally:** Discover is answer-first: readiness-backed search and company actions render before cohort scope and lane-coverage context, while the unchanged cohort evidence remains collapsed under Advanced.
8. **Implemented locally:** Company Workbench is answer-first: the existing selected-company report answer renders as the first expanded research content, while unchanged lane-coverage cards remain available under a collapsed Advanced section.
9. **Implemented locally:** Research Desk is answer-first: the weekly summary, four direct research answers, and Discover action render before unchanged cohort scope, coverage cards, and full matrices under Advanced Evidence.
10. **Implemented locally:** Monitor is answer-first: the weekly summary and deduplicated research-change answer render before five-company Earnings Nowcast readiness under Advanced; an empty queue remains a neutral wait state with one Discover action and never implies that no real-world event occurred.
11. **Implemented locally:** a no-file quarterly cash-generation evidence contract derives operating margin, free cash flow, and FCF margin from compatible explicit components, preserves revision and source lineage, enforces explicit filed-Q4 evidence, and renders five independent Business Trend answers while production values remain withheld without a reviewed adapter.
12. **Implemented locally:** a pure one-company adapter acceptance harness fails closed on ticker/source identity, commercial rights, supported fields, cutoff, revision ambiguity, missing or incompatible components, Revenue compatibility, complete-period derivation, and explicit filed-Q4 evidence. `accepted_for_review` always preserves `production_activation=false` and empty readiness promotions.
13. **Source state classified:** point-in-time consensus remains `external_data_required` with 0 prospective snapshots. Do not repeat provider probes until a permitted key is configured or a reviewed CSV is supplied; the exact resume step is one-ticker validate and preview.
14. **Source state classified:** the quarterly cash-generation adapter is `external_source_and_review_required`. The local contract is complete, but no reviewed real-company operating-income, cash-from-operations, and capital-expenditure adapter is connected; resume with one company and explicit Q4 evidence, not a broad refresh.
15. **Implemented locally:** the peer evidence-quality contract preserves relationship provenance, reviewer-assigned role, economic comparability, result context, and valuation-anchor eligibility independently. The current 75 legacy mappings produce 0 eligible valuation anchors by design; no role was inferred.
16. **Next evidence-depth gate:** review one bounded peer relationship through the updated template and write-back guard when a trustworthy source and reviewer are available. Do not start a broad 25-50 company sourcing loop before the first relationship proves the repeatable contract.
17. **Next external validation:** after one repeatable permitted source path and a controlled delivery boundary exist, run 10-20 task-based beta sessions; measure time to first answer, readiness comprehension, misuse risk, trust, performance, and repeat-use intent.
18. **Implemented locally:** phone first-action density now keeps the five profile facts in two rows, removes only duplicated route-card freshness on phone, exposes Discover search and Monitor's weekly state sooner, and keeps Company Workbench's complete review path in a collapsed disclosure before the detailed report. Desktop profile and route metadata remain unchanged.
19. **Implemented locally:** shared pilot and reviewed-batch freshness now fail closed when declared source dates are newer than the saved readiness build, even when file mtimes look current after a checkout or restore. The current saved snapshot is therefore honestly stale until an intentional reviewed `make readiness` run; the read-only gate does not rebuild readiness or create CSV/JSON artifacts.
20. **Implemented locally:** `make readiness-preview TOP_N=20` now runs the production universe and readiness logic in explicit no-write mode, compares only stable saved-versus-proposed readiness fields, caps ticker detail, and routes stale pilot inspection to stdout without creating CSV, JSON, report, sample-report, screenshot, timing, or bytecode churn. It does not make saved readiness current, prove source correctness, or authorize the separate reviewed rebuild.
21. **Implemented locally:** Data Health and Proof History stay inside Personal Research mode when opened from Company Workbench Advanced Evidence, preserve the selected ticker, and expose a direct Return to Company Workbench action before evidence content. The detour does not change readiness or evidence state and adds no route, data mutation, or operator command exposure.
22. **Implemented locally:** the stale readiness continuation gate now gives project status, Session Source Preflight, provider setup, the coverage frontier, Auto-Refresh Status, its runbook, Advanced Data Health cards, and the commercial-beta release path one fail-closed operator answer. While selected-profile readiness is stale or incomplete, `make readiness-preview TOP_N=20` is the only continuation-safe command; source availability, provider classifications, scheduled operations, and ranked coverage rows remain planning context only, and `make readiness` remains a separate intentional reviewed write.
23. **Implemented locally:** the same no-write readiness preview now reviews every proposed fundamentals/DCF promotion independently for exact source ID, source/as-of/durable-reference provenance, commercial-rights status, and registered field scope. The current inspection finds 152 unique technical promotions, but 95 use unregistered exact source values, 4 lack complete provenance, and all 152 lack complete registered support for the four fundamentals fields. These are proposed in-memory changes, not current readiness counts or rebuild approval.
24. **Implemented locally:** the preview now explains saved-versus-proposed feature transitions with named method reasons. The current inspection accounts for all 464 newly excluded DCF rows—acquisition/SPAC, bank/bancorp, financial/insurance/mortgage, closed-end fund, capital-corporation, nonpositive-revenue, realty-trust/BDC, or REIT scope—and separately reports ready, partial, excluded, added, and removed transitions. Exclusion is method fit, not a negative company signal.
25. **Implemented locally:** the same no-write preview now audits the one latest valid positive-close price row supporting each proposed DCF promotion. The current inspection finds 146/146 promotions with one unambiguous usable latest row, but 0/146 with complete row-level `source`/`source_ref`/`retrieved_at` lineage, 0/146 with approved exact-source commercial rights, and 0/146 with registered `prices` scope. Missing provider identity remains missing; file origin, observation dates, adapter availability, and refresh history are not used to infer it. These are proposed in-memory changes, not current readiness counts or rebuild approval.
26. **Implemented locally:** the manual price normalization, validation, preview, and later reviewed-apply contracts can now preserve explicit prospective `source_ref` and `retrieved_at` fields. Validation reports `lineage_complete` or `lineage_review_required` independently from technical OHLCV validity, and invalid retrieval timestamps remain blank rather than being replaced with current time. This is capability evidence only: no repository price row was normalized or applied, current canonical history remains unchanged, and source rights/registered `prices` scope remain separate.
27. **Implemented locally:** staged price validation and preview now join each exact retained `source` value to the checked-in source-rights registry and report commercial-rights and registered `prices` scope independently from technical validity and lineage. Unknown, blank, unverified, mixed, and approved states fail closed without aliases or provider inference. This is read-only review capability: it does not edit rights, approve apply, rebuild readiness, or change the 146-row canonical audit.
28. **Implemented locally:** explicit Commercial Research mode now blocks staged-price apply before backup or canonical mutation unless every valid row has complete lineage, approved exact-source rights, and registered `prices` scope. Research mode retains the existing separately reviewed local apply path. Temporary fixtures prove blocked and passing guard states; no repository apply or readiness rebuild occurred.

**Maturity assessment:** the quarterly cash-generation slice improves **methodology maturity**, cash-conversion transparency, adapter extensibility, fail-closed reliability, and reviewer trust. It makes Company Workbench more useful for understanding operating profitability versus cash generation without inventing missing facts. It **does not prove real-company coverage or market validation**, licensed source operation, hosted reliability, reviewer adoption, commercial demand, calibration quality, or product-market fit. The product therefore remains a local Commercial Research Beta release candidate, not a market-validated platform.

The acceptance harness closes a local adapter-governance gap, but it **does not prove a real-company source payload**, a rights expansion, a reviewer decision, production activation, or user demand. The checked-in SEC Companyfacts rights record does not currently list the three cash-generation component fields, so that source remains blocked for this adapter contract until a separate reviewed rights change exists.

The phone first-action slice improves **local usability maturity** and reviewer comprehension. It does not change readiness, source evidence, coverage, forecasts, or research conclusions, and it does not prove hosted reliability, external reviewer demand, commercial demand, or product-market fit.

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

## Later External Stages

### P1: Controlled Hosted Preview Verification

**Goal:** turn the deterministic `demo` profile into a verified, controlled hosted demo without exposing local refresh data or credentials.

Repository-side preparation is complete. The remaining deployment work requires an external host/account and a verified public URL.

1. Choose a Streamlit-compatible host and deploy `main` with `dashboard.py` as the entrypoint.
2. Set `STOCK_RESEARCH_DATA_PROFILE=demo` in the host environment.
3. Keep provider keys, account IDs, tokens, and broker/session files out of the repo and public app.
4. Verify the five-page workflow on the hosted URL at desktop and mobile widths.
5. Set `HOSTED_DEMO_URL` locally only after the URL opens successfully, then rerun the public gates before changing GitHub or LinkedIn copy.

**Dependencies:** the local performance release gate, an external hosting account, a public or access-controlled preview URL, and a human browser review of the deployed route.

**Stop rule:** keep GitHub as the public link until the hosted route is verified. Call the route private only when access control is actually enforced. Screenshots remain product evidence only, never data-freshness proof.

### P1: Controlled Pilot Review

**Goal:** validate whether an external reviewer can understand the product in under three minutes.

1. Share the controlled beta package with 10-20 reviewers after the delivery boundary is verified.
2. Ask reviewers to follow the public visitor flow without operator instructions.
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

## Next: Focused-Cohort Evidence

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

1. Run the default executable queue: `make price-history-proof-queue TOP_N=25`.
   - `momentum-not-ready` rows describe a readiness state, not a refresh instruction.
   - `unreviewed preferred-history candidates` are the only default queue rows eligible for a narrow reviewed investigation.
   - `reviewed source-limited items` are excluded from the default queue because they remain wait-only.
2. Use audit mode only to inspect reviewed source-limited items: `INCLUDE_REVIEWED=1 make price-history-proof-queue TOP_N=25`.
3. When compatible reviewed evidence exists, use `make price-history-batch-closeout TOP_N=25` to produce the read-only grouped closeout scaffold. It does not record proof rows, stage files, commit, or push.

**Stop rules:** stop on no readiness movement in reviewed scope; no identical source-limit retry unless source behavior or verified OHLCV changes; batch compatible proof evidence intentionally; never commit or push one proof row per ticker by default; pivot to the next roadmap item when no executable candidates.

### P3: 25-50 Company Trusted-Peer Pilot

**Goal:** address the largest analytical-depth gap without inferring trusted peers across the full universe.

1. Select 25-50 operating companies from a few clearly comparable industries.
2. Generate candidate peer context from SIC, industry, and product context; label it `candidate_context_only`.
3. Promote a relationship only after source-backed review captures peer source, review date, rationale, as-of context, reviewer-assigned peer role, economic comparability basis, and an explicit valuation-anchor decision.
4. Keep peer trend readiness separate from peer valuation readiness.
5. Require at least two explicitly eligible `core_peer` or `secondary_peer` relationships plus trusted peer price, fundamentals, and valuation inputs before relative valuation appears.

**Dependencies:** a licensed or otherwise trustworthy peer relationship source and reviewed mappings.

**Stop rule:** sector similarity is not trusted-peer proof. Do not target broad-universe peer readiness before the pilot has repeatable evidence.

**Evidence-quality slice implemented:** the source-review template, write-back guard, local provider, readiness engine, and Peer Read-Through Map now preserve and evaluate `peer_role`, `relationship_rationale`, `comparability_basis`, and `valuation_anchor_eligible`. Legacy seven-column relationships remain visible for source-backed trend or result context but fail closed as valuation anchors. Candidate rows remain separate. No existing canonical peer row was assigned a role by inference.

The implemented Peer Read-Through Map is the review surface for this future cohort. This contract improves local methodology but does not satisfy the external trusted-relationship dependency, review the existing 75 canonical rows, or create broad peer coverage by itself.

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
| Operated controls | contract-ready | independent fail-closed states for account controls, incident response, rollback, and owner capacity | hosted accounts, named coverage, and supervised operating rehearsal |
| FMP fallback | optional key missing | one-ticker smoke, validation, preview, provenance gate | `FMP_API_KEY` outside Git |
| Alpha Vantage / Finnhub | optional keys missing | capped fallback interfaces and source-state checks | provider keys and a reviewed use case |
| Trusted peers | source-gated | candidate/trusted separation, role/comparability/anchor contract, and proof workflow | licensed or otherwise trustworthy reviewed relationships, roles, rationales, and comparability decisions |
| Earnings / estimates | intentionally locked | optional-context states and import gates | trusted provider/manual rows with supported fields |

## Success Gates

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
