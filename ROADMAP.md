# Roadmap

Stock Research Command Center follows one principle: **data readiness first, analysis second, research decision last**. It is research-only software: no investment advice, broker trading, order routing, auto-trading, direct buy/sell instructions, or fabricated data.

This is the active plan only. Completed delivery history lives in [Completed Milestones](docs/COMPLETED_MILESTONES.md).

## Current Truth

Use live, read-only commands instead of static counts:

- Master universe rows: use `make project-status` or `make status-check TOP_N=5`.
- Active research rows: use `make project-status` or the dashboard Home page.
- Lane readiness: use `make readiness-ops-center`.
- Source/provider state: use `make session-source-preflight` and `make provider-setup-checklist`.
- Package/share state: use `make pilot-readiness-check TOP_N=10` and `make public-check`.

The product deliberately separates the tracked master universe, active universe, and analysis-ready subset. It must never imply that the whole tracked universe is analysis-ready.

Public visitor flow: **Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History**.

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
3. Measure the visible shell, first useful answer, and full settle separately; report repeated warm results as p90 rather than selecting the fastest run.
4. Treat Stock Selector, Single-Stock Report, and Data Health as critical routes. Keep Home and Proof History regression-protected.
5. Optimize saved summaries, deferred detail, pagination, and deterministic caching in small tested slices without weakening readiness or hiding blocked states.

**Exit gate:** loading feedback within 1 second, first useful answer within 3 seconds, warm full-settle p90 within 5 seconds, and cold full settle within 10 seconds on the defined local reference environment.

**Stop rule:** a missing browser dependency is `environment_limited`, not a pass. Keep timing JSON and screenshots generated and unstaged unless one concise artifact is intentionally reviewed.

## External Stages

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

1. Share the GitHub demo package with 5-10 reviewers.
2. Ask reviewers to follow the public visitor flow without operator instructions.
3. Record only concrete issues: where they started, what they thought was usable, what looked blocked, and what they expected to do next.
4. Prioritize reproducible first-viewport, wording, routing, or accessibility defects. Do not use pilot feedback to weaken readiness gates.

Use [Controlled Pilot Review Feedback](docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md) to capture anonymous, reproducible workflow observations without collecting personal, portfolio, or investment-opinion data.

**Dependencies:** a locally passing performance release gate, a verified delivery path, external reviewers, and controlled feedback collection.

**Stop rule:** do not call pilot feedback data proof; it only validates product clarity and workflow reliability.

## Now

### P2: Scenario Lab - Implemented

**Goal:** let a reviewer vary source-backed DCF assumptions and understand valuation sensitivity without changing canonical data or producing a recommendation.

1. Start only from a company whose selected profile is DCF-ready.
2. Load the saved source-backed revenue, FCF or margin, shares, cash, debt, and price context as immutable baseline evidence.
3. Allow bounded changes to revenue growth, operating or FCF margin, discount rate, terminal growth, and forecast horizon.
4. Show baseline and scenario ranges, directional sensitivity, terminal-value contribution, and every changed assumption.
5. Keep scenarios session-local or explicitly exported as generated research artifacts; never apply them to canonical fundamentals or readiness.

**Stop rule:** blocked or excluded DCF inputs produce no valuation output. Scenario results are assumption tests, never fair-value claims, rankings, or direct actions.

**Implemented proof:** the detailed Valuation tab now loads source-backed defaults, enforces bounded controls, reports changed assumptions and sensitivity, and keeps provenance and scenario identity under Advanced. It is session-local and does not change canonical inputs or readiness.

### P2: Earnings Nowcast Pilot Evidence

**Goal:** move the implemented Earnings Nowcast pilot from synthetic infrastructure proof to a leakage-safe, source-backed semiconductor cohort.

Earnings Nowcast real-data safety infrastructure is implemented for deterministic Revenue/EPS ranges, consensus-relative classification, metric-specific canonical quarterly evidence, comparability checks, evidence-only directional signals, chronological walk-forward backtesting, explicit sample-sufficiency/calibration diagnostics, and a separate probability calibration gate. Versioned read-only append-only onboarding templates, validation, preview, readiness, and prospective collection planning are implemented. The committed fixture cohort is synthetic test evidence only.

1. Acquire permitted append-only historical quarterly actuals and point-in-time consensus snapshots with source references, publication/retrieval timestamps, and explicit Revenue/EPS comparability definitions for a narrow semiconductor cohort.
2. Use `make earnings-nowcast-prospective-plan` for future snapshot collection, then run the implemented onboarding validate/preview/readiness gates before any real-company packet; no automatic apply path exists.
3. Keep candidate peer/news signals separate from reviewed trusted evidence; signals explain context and never mutate forecast numbers.
4. Run chronological out-of-sample evaluation against latest-consensus and prior-year benchmarks.
5. Withhold numerical Beat/Miss probability until at least 100 valid events pass Brier-score, calibration-bin, and benchmark-improvement gates.

Real semiconductor nowcast coverage remains `awaiting_point_in_time_consensus`; numerical probability remains `awaiting_calibration_evidence`.

**Stop rule:** do not substitute current analyst estimates for historical point-in-time snapshots, use post-cutoff evidence, infer numeric adjustments from text, claim predictive accuracy from fixtures, or predict post-earnings price movement.

## Next

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
3. Promote a relationship only after source-backed review captures peer source, review date, rationale, and as-of context.
4. Keep peer trend readiness separate from peer valuation readiness.
5. Require trusted peer price, fundamentals, and valuation inputs before relative valuation appears.

**Dependencies:** a licensed or otherwise trustworthy peer relationship source and reviewed mappings.

**Stop rule:** sector similarity is not trusted-peer proof. Do not target broad-universe peer readiness before the pilot has repeatable evidence.

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
| FMP fallback | optional key missing | one-ticker smoke, validation, preview, provenance gate | `FMP_API_KEY` outside Git |
| Alpha Vantage / Finnhub | optional keys missing | capped fallback interfaces and source-state checks | provider keys and a reviewed use case |
| Trusted peers | source-gated | candidate/trusted state separation and proof workflow | reviewed source relationships and rationale |
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
