# Research Methodology

This project is a local stock research command center. It does not ask a model to invent an opinion. It follows a deterministic workflow:

1. Check whether the local data is ready.
2. Run only the analysis that the ready data can support.
3. Withhold or block analysis that needs missing inputs.
4. Explain the assumptions, missing fields, and next research step.

The methodology is intentionally conservative. Missing prices, fundamentals, peers, earnings, or analyst estimates are treated as quality-control blockers, not as values to infer.

## Methodology Status

Current public method version: **Methodology v1 - readiness-first deterministic gates**. The field-level evidence boundary is defined in [Provenance Contract](PROVENANCE_CONTRACT.md).

This method is useful for a controlled research/demo product because it makes the data gate visible before analysis. It is not a complete valuation terminal, not investment advice, and not a recommendation engine.

### Readiness Promotion Evidence Review

When saved readiness is stale, `make readiness-preview TOP_N=20` runs the production readiness logic in memory and keeps the proposed technical state separate from the evidence needed to review a rebuild. False-to-true fundamentals and DCF changes are checked against the exact canonical source value, source/as-of/durable-reference provenance, the checked-in commercial-rights decision, and the registered field list for Revenue, free cash flow, FCF margin, and shares outstanding.

Composite or unregistered source values remain unknown exact identifiers; the method does not split them or borrow the rights decision of one component. Numerical completeness can therefore produce a proposed technical promotion while the evidence review remains blocked. DCF also depends on price evidence, and the current canonical price rows do not establish row-level provider provenance, so the fundamentals review never claims complete DCF commercial provenance. The preview writes nothing, does not edit source rights, does not make saved readiness current, and cannot authorize the separately reviewed `make readiness` boundary.

The independent `DCF Price Lineage Review` inspects only false-to-true DCF promotions. For each ticker it parses canonical dates and positive closes, selects the greatest observation date, and requires exactly one row at that date. It then keeps five states independent: proposed technical DCF promotion, unique latest-row selection, complete row-level `source`/`source_ref`/`retrieved_at` lineage, exact-source commercial rights, and registered `prices` field scope. A missing usable row or duplicate latest date fails closed; the review does not choose an arbitrary duplicate.

An observation date is not a retrieval timestamp. `as_of_date`, the `local:prices.csv` file-origin label, file modification time, adapter presence, refresh warnings, and OHLCV shape cannot establish the original provider or durable row reference. The current no-write inspection finds one unambiguous usable latest row for all 146 proposed DCF promotions, but no promoted row has complete lineage, approved exact-source rights, or registered price scope because the canonical source identifier is absent. This identifies an evidence gap; it does not invalidate local research prices, change technical readiness, or authorize a historical schema rewrite or readiness rebuild.

For future reviewed rows, the manual normalization path accepts explicit `source_ref` and `retrieved_at` metadata and preserves them through validation, preview, and a later separately authorized apply. Validation reports row-level lineage completeness independently from technical OHLCV validity. It never substitutes normalization time for retrieval time, and an invalid retrieval timestamp remains blank. Complete preservation still does not establish commercial rights, registered `prices` support, freshness, reviewer acceptance, or apply/rebuild authorization.

Staged validation and preview also evaluate the exact retained `source` value against the checked-in registry. The rights decision uses the existing commercial-eligibility contract, while price scope requires literal `prices` membership in the same exact record. Approved, unverified, unknown, blank, and mixed batches remain explicit; composite values are not split and aliases are not inferred. Invalid technical rows are excluded from these counts. The joined review adds evidence states without changing technical validity, lineage completeness, merge counts, source rights, or apply/readiness authorization.

Explicit Commercial Research mode then applies a pre-mutation conjunction: every valid staged row must have complete lineage, approved exact-source rights, and registered `prices` scope. Failure returns before backup or canonical write and lists the independent blockers. Research mode does not inherit this commercial license gate, so existing local research compatibility remains intact. A passing guard is necessary for the commercial mutation path but is not payload review, freshness proof, readiness promotion, or automatic apply authorization.

Direct provider refresh uses the same exact-source commercial metadata boundary before it can fetch or mutate. Each concrete provider has one fixed source ID; CLI aliases cannot borrow another record's rights, and an automatic ladder reviews each reachable leg independently. Commercial Research mode filters or refuses unapproved and scope-incomplete legs before provider execution, then rechecks the exact selected provider before adding fetched rows or status output. A missing or changed identity fails closed. Research mode retains its existing provider order and local refresh behavior. This enforcement does not approve any provider, add row-level lineage to canonical history, validate a payload, or make readiness current.

Focused-cohort saved-row coverage applies field scope per lane rather than reusing one source-level approval. Technical availability, source/reference provenance, exact-source commercial rights, and registered scope remain separate for margins, free cash flow, cash, debt, shares, filing dates, earnings dates, each populated Revenue/EPS consensus metric, and every trusted-peer relationship. Cash and debt can therefore be partial independently, and Revenue-only consensus permission cannot unlock EPS. A date-only consensus row is not evidence. Candidate peers remain context-only. Commercial blockers are shown in the collapsed Advanced cohort evidence; research mode retains its source-backed local behavior.

Adjusted price history in the same Commercial cohort additionally requires saved price readiness and at least one technically usable canonical date/positive-close row. Every retained history row must carry exact `source`, durable `source_ref`, and explicit `retrieved_at`, and its exact source must independently pass approved rights plus registered `prices` scope. One missing or unapproved row blocks the history rather than borrowing another row's permission. Current canonical history has no row lineage, so it remains local research context rather than commercially supported cohort evidence. Retrieval chronology remains a separate audit boundary.

Canonical quarterly Revenue and EPS coverage applies the same field-specific commercial conjunction to accepted actual rows before a technical trend packet can mark the cohort lane usable. Every populated row for the metric needs source/reference/retrieval provenance, approved exact-source commercial rights, and literal `revenue` or `eps` scope. Revenue and EPS are independent: SEC Companyfacts' registered Revenue scope cannot unlock EPS. A passing commercial display review does not prove split-basis comparability, Q4 evidence, revision integrity, loader completeness, readiness, or nowcast activation; Research mode retains the existing packet-only behavior.

The same preview summarizes newly ready, partial, and excluded feature transitions plus added or removed ticker rows. New DCF exclusions use the exact existing company-scope method and report a deterministic primary reason: non-operating asset type, acquisition/SPAC, closed-end fund, bank/bancorp, financial/insurance/mortgage, REIT, realty-trust/BDC, capital corporation, or nonpositive-revenue margin model. Reasons explain method fit; they are not company-quality labels. Transition counts can overlap for one ticker and are not current readiness totals.

Use this quick model card before relying on a page or report:

| Check | What to verify | Boundary |
| --- | --- | --- |
| Method version | The dashboard or report is using the readiness-first deterministic gates described here. | A newer method version should document changed gates, assumptions, and report wording. |
| Freshness by lane | Latest price date, latest fundamentals filing date, peer review date, optional-context review date, and proof-ledger date. | Screenshots and sample reports are product evidence only; they do not prove current data freshness. |
| Provenance | Source, as-of date, reviewed/import status, and whether the row is source-backed, candidate context, blocked, skipped, or excluded. | Metadata, candidate peers, or provider availability do not substitute for fundamentals, share-count, peer valuation, earnings, or analyst-estimate proof. |
| DCF assumptions | WACC, terminal growth, forecast years, growth caps, FCF margin caps, and any normalization warning. | DCF output is scenario math, not a price target or instruction. |
| Peer context | Candidate peers are separated from trusted relationships, result read-through, and valuation-anchor inputs. | Candidate peers can guide review, but they are not trusted peer proof. |
| Public share boundary | Public screenshots, walkthroughs, and QA evidence show product behavior. | They do not unlock blocked inputs or prove today's market/fundamental data. |

## Lane-Level Freshness Policy

Freshness is evaluated per lane because a daily price series, an annual filing, and a reviewed peer relationship do not age at the same rate. The product uses three review labels:

- `current`: the required source/as-of evidence exists and no newer known event requires review.
- `review_due`: the row may remain useful as historical context, but the expected event or review cadence has arrived and the lane needs source review before a current-state claim.
- `stale_or_unknown`: the as-of date, source event, or review evidence is missing or too uncertain to support a freshness claim. Required analysis stays blocked when freshness is part of its gate.

| Lane | Review expectation | Stale or changed behavior |
| --- | --- | --- |
| Price / momentum | Check the latest saved trading date when the project is opened; a daily after-close refresh is appropriate when current setup context is needed. | Show the latest date and short-history state. Do not imply intraday or real-time coverage, and do not fabricate missing OHLCV history. |
| Fundamentals | Review after a verified quarterly or annual filing/source event. | Keep the filing/as-of date visible. A newer filing makes the prior row `review_due`; missing trusted fields remain blocked. |
| Quarterly business trend | Review only from a fully parseable canonical ledger of explicit, versioned quarterly actual rows available by the selected cutoff. | Any rejected canonical row blocks the complete dashboard trend/cohort packet; row-numbered reasons stay under Advanced. Revenue and EPS comparisons require compatible metric definitions and matching periods. Missing comparisons remain partial; ambiguous revisions and absent evidence remain blocked. Q4 is never derived from annual values. |
| Optional valuation, catalyst, and outcome evidence | Research-mode technical review remains separate. Commercial Research composition additionally reviews every used row against its exact source ID and literal `valuation_history`, `catalyst_evidence`, or `research_outcomes` registry scope. | One unknown, unapproved, or scope-incomplete used row blocks the supported/reviewed packet. Candidate catalyst context cannot satisfy supported evidence. Empty ledgers stay empty; blocker details stay under Advanced. |
| Share count | Review after a validated capital-structure filing or explicit share-count fact. | Do not infer shares from price or market cap. Missing explicit evidence remains blocked even when metadata is current. |
| DCF | Regenerate when a required fundamental, share-count, cash/debt input, price reference, or methodology version changes. | DCF inherits the weakest required input state. Stale or missing required inputs withhold current interpretation rather than silently reusing a prior conclusion. |
| Trusted peers | Version and periodically review accepted relationships, and review again after a material business-model or segment change. | Missing source, rationale, reviewer, review date, or mapped-peer valuation inputs keeps the relationship candidate-only or blocked. |
| Earnings / estimates | Treat as optional and time-sensitive; review only through a trusted provider/manual row carrying period and retrieval/as-of evidence. | Date-only or target-only rows remain candidate context. Missing trusted fields keep the lane locked. |

A timestamp cannot turn an unsupported row into trusted evidence. Fresh metadata, screenshots, provider availability, or candidate context cannot substitute for the field-level source proof required by a readiness gate.

Quarterly business trend is descriptive and backward-looking. Sequential and year-over-year changes do not become a forecast, recommendation, or numerical adjustment to DCF or Earnings Nowcast. Revenue, EPS, operating margin, free cash flow, and FCF margin keep independent `ready`, `partial`, `blocked`, or `withheld` states.

The quarterly cash-generation contract derives operating margin as reported operating income divided by compatible quarterly Revenue, free cash flow as **cash from operations + reported capital expenditures** while preserving the source-reported capital-expenditure sign, and FCF margin as derived free cash flow divided by compatible quarterly Revenue. Inputs must match currency, scale, accounting basis, duration basis, fiscal period, and period end. Cross-quarter comparisons use the stable accounting definition rather than treating different period-end dates as different measurement definitions. Missing, ambiguous, post-cutoff, zero-denominator, or incompatible inputs block only the affected metric. The contract is in-memory and descriptive; it does not write a source row, modify a canonical dataset, or promote DCF, Earnings Nowcast, peer, catalyst, outcome, backtest, or calibration readiness.

The one-company adapter acceptance harness composes that derivation with the immutable commercial source-rights registry. It requires one ticker, one matching source ID, explicitly approved commercial use, explicit support for operating income, cash from operations, and capital expenditures, no unresolved cutoff/revision/component/compatibility blockers, and at least one period with all three derived metrics. Its only success state is a local review-routing state: **accepted_for_review is not production activation**. A passing candidate still requires the actual source payload, rights review, and human review before any production caller may supply it.

The bounded SEC pilot now supplies that source-review evidence for NVIDIA Q1 FY2027 only. It selects Revenue, operating income, cash from operations, and capital expenditures from one exact Companyfacts accession and three-month context, requires the matching SEC submissions `acceptanceDateTime`, and matches concept, context, magnitude, and inline-fact identity against the exact filed 10-Q. Companyfacts exposes the capex magnitude without a cash-flow sign, so the pilot records a negative capex observation only when the matching filed-table value is explicitly displayed as an outflow; that proof state is `explicit_filed_table_outflow`. Identical repeated inline disclosures may collapse to the first document fact, but conflicting Companyfacts values, contexts, accessions, primary documents, magnitudes, or timestamps block the complete preview. The read-only result remains `accepted_for_review`; it does not persist a row, activate Company Workbench, rebuild readiness, or establish another company or quarter.

## Profile Truth And Change Review Method

The dashboard resolves exactly one data profile for each run: `Demo`, `Local Research`, or `Default`. Its trust strip separates:

- `Sources through`: latest valid selected-profile source date.
- `Readiness built`: timestamp of the selected saved readiness artifact.
- `Snapshot identity`: deterministic identity of the selected comparison inputs.
- `Freshness`: current, stale, mixed, or missing based on selected-profile evidence.
- Profile-matched coverage: saved Price, fundamentals, DCF, and trusted-peer readiness counts.

Snapshot identity is an audit key, not a freshness or quality score. The monitor requires explicit before/after snapshots from the same profile. A missing baseline yields `baseline_missing` and zero claimed events. Cross-profile comparison fails closed.

Detectors compare explicit readiness fields, SEC filing accession, selected fundamental/share-count values, latest price date, and point-in-time Nowcast consensus identifiers. Each event preserves prior/current values, source reference, profile, both snapshot identities, separate publication/retrieval/detection times where available, evidence status, materiality, and one research task. There is no free-text model detector and no event creates a numerical forecast adjustment.

The Research Review Queue is derived from unresolved events. Lost DCF or fundamentals readiness is reviewed before new context; append-only outcomes record `reviewed_supported`, `reviewed_no_change`, `still_blocked`, `intentionally_deferred`, `skipped`, or `excluded`. Recording an outcome does not change source files, readiness, valuation, or a research conclusion.

## Research Thesis Journal Method

The selected-profile journal is reviewer-authored, append-only research documentation. It records thesis revisions, source-backed supporting and conflicting evidence, catalysts, risks, invalidation conditions, confidence history, and review dates. Existing generated thesis text is context only; it is never copied into the journal automatically.

Preview validates one prospective entry without writing. Recording requires explicit reviewed confirmation. A later thesis must reference the prior thesis entry, and the historical row remains present. Evidence, catalyst, risk, and invalidation entries require a source, durable source reference, and publication timestamp. A Change Monitor event or Review Queue outcome may prompt review but never creates or revises a journal entry.

Confidence describes the reviewer's confidence in the documented hypothesis at that timestamp. It does not measure expected return, allocation size, or transaction direction. An empty journal is `not_started`; a thesis without a source-backed invalidation condition is `incomplete`; and a passed review date is `overdue`.

## Public Workflow Boundary

The public page order is a reading workflow, not an analysis shortcut.

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

Home starts with the visitor question, next safe action, and stop rule before readiness counts. Stock Selector chooses one readiness-backed candidate; Single-Stock Report explains what can be used for that ticker; Data Health explains one blocked lane at a time; Proof History verifies reviewed evidence before trusting a changed state. This page order helps a visitor understand the product, but it does not turn blocked fundamentals, share counts, peers, earnings, estimates, valuation inputs, or metrics into usable inputs. Those fields still require source-backed rows, validation, preview, rejected-row review, apply, rebuilt readiness, and proof history.

## What Is Data Versus App Method

The product separates source inputs from analysis rules so the report is not a black box.

| Layer | Where it comes from | What the product does |
| --- | --- | --- |
| Price rows | Local CSVs, optionally refreshed through a labeled research-grade provider adapter. | Validates enough usable rows exist, then calculates trend, momentum, liquidity, volatility context, and setup labels. |
| Fundamentals rows | Trusted local imports such as SEC/manual CSV workflows. | Checks required fields, derives ratios where supported, and decides whether DCF and quality review can run. |
| Peer mappings and peer metrics | Trusted local peer mapping and peer input CSVs. | Separates peer trend context from peer valuation, and blocks valuation when peer inputs are incomplete. |
| Earnings and analyst estimates | Trusted optional local imports. | Displays optional context only when rows pass schema and source-readiness checks. |
| Report wording | Project code under `src/`. | Converts readiness, calculations, source state, and blockers into plain-language sections without inventing conclusions. |

Third-party or optional provider data can supply rows, but it does not decide the research conclusion. The project code decides whether each local row is usable, which calculation is allowed, and which section must stay blocked or excluded.

## 1. How This Compares To Standard Research Workflows

The product follows a familiar equity-research sequence, but keeps each step visible and gated:

| Standard research step | What this product implements | What stays blocked |
| --- | --- | --- |
| Data collection | Local CSV and optional provider-assisted rows for prices, fundamentals, peers, earnings, and estimates. | Any field that is missing, stale, malformed, or not source-backed. |
| Quality control | Readiness gates for each analysis feature before calculations run. | Valuation, peer comparison, or optional context when required inputs are absent. |
| Intrinsic valuation | A free-cash-flow DCF with visible scenario assumptions, WACC, terminal growth, and sensitivity. | Price targets or valuation claims when DCF inputs are incomplete. |
| Relative valuation | Source-backed peer workflow and peer-input checks. | Peer valuation from guessed relationships, sector fallback, or incomplete peer metrics. |
| Research note | Single-stock report sections generated from readiness, calculations, blockers, and source readiness state. | Recommendations, allocation instructions, or hidden analyst-opinion imports. |

Compared with a professional research terminal or analyst model, this project is intentionally narrower. It does not try to own every data feed or produce a final investment call. Its value is that the workflow is inspectable: the same project code checks data readiness, runs DCF math only when inputs exist, withholds unsupported peer valuation, and explains the next trusted input needed.

## 2. Readiness Gate

The readiness gate runs before valuation or report conclusions.

| Area | Minimum rule | Output behavior |
| --- | --- | --- |
| Price | Enough valid local price rows with positive close values. | Makes setup and trend context available. |
| Momentum | More local price history than the basic price gate. | Makes momentum and market-direction context available. |
| Liquidity / correlation | Longer local price history. | Makes risk-context review available. |
| Fundamentals | Trusted local row with required numeric fields and source. | Makes company fundamentals review available. |
| DCF | Company ticker plus price, revenue, free cash flow or FCF margin, and shares outstanding. | Makes standalone DCF review available. |
| Peers | Source-backed peer mappings plus peer price/fundamental inputs. | Makes peer trend or peer valuation context available depending on input depth. |
| Earnings / estimates | Trusted local optional-context rows. | Makes optional context available only when trusted rows pass readiness. |

The app labels each feature as `ready`, `partial`, `blocked`, or `excluded`. ETFs, index proxies, and funds are excluded from operating-company DCF because that valuation method does not fit their monitor role.

## 3. Fundamental Analysis

Fundamental analysis uses local fields such as revenue, revenue growth, free cash flow, FCF margin, operating margin, profit margin, EPS, cash, debt, shares outstanding, and source metadata.

The product does not claim a company is attractive or unattractive when core fields are missing. Instead it explains which fields are available, which fields are missing, and whether those fields are enough for DCF or peer-relative review.

Fundamental review is therefore a validation-and-interpretation layer, not a third-party analyst summary. A full company row can support revenue scale, growth, margin, free-cash-flow conversion, leverage/cash context, and DCF input quality. A partial row supports only the fields that are actually present.

The fundamental-analysis contract is:

| Question | Product rule | What remains withheld |
| --- | --- | --- |
| Is there a trusted company row? | Checks the local fundamentals row, source metadata, and required numeric fields. | Company-quality language when the row is missing or source status is unclear. |
| Is the business scale visible? | Reads revenue and revenue growth when present. | Growth interpretation when revenue history is absent or malformed. |
| Is cash generation visible? | Reads free cash flow directly, or uses revenue and FCF margin when both are trusted. | Free-cash-flow conversion claims when both FCF and FCF margin are missing. |
| Is balance-sheet context visible? | Reads cash, debt, or net-debt fields when present. | Leverage or cash-cushion language when balance-sheet fields are unavailable. |
| Can DCF run? | Requires price, revenue, free cash flow or FCF margin, shares outstanding, and valid assumptions. | Fair value/share, sensitivity, and valuation interpretation until required fields pass readiness. |
| Can peer valuation run? | Requires standalone company readiness plus source-backed peer mappings and peer valuation inputs. | Peer-relative valuation from guessed peers, sector fallback, or incomplete peer metrics. |

This means a fundamentals-ready row is not automatically a conclusion. It is permission to review the fields that are present. A DCF-ready row is permission to review scenario math. A peer-ready row is permission to review source-backed relative context. The report and dashboard keep those permissions separate so a partial fundamentals row cannot become a valuation view without ready inputs.

## 4. Price, Momentum, And Risk Context

Price and momentum analysis uses local OHLCV rows when they are available. The product calculates moving averages, returns, relative strength, volume ratio, setup status, and volatility context from those rows.

For volatility context:

- If local `high`, `low`, and `close` fields are available, the product reports ATR from those fields.
- If high/low inputs are missing but close prices exist, it can use a close-to-close volatility proxy.
- Proxy volatility is labeled as an approximation in reports and dashboard cards.
- If neither path is supported, the volatility field stays unavailable rather than being guessed.

This volatility context can affect local risk penalties and review notes, but it is not an allocation or trading instruction.

Theme and sector ETFs, such as a fintech proxy used for relative context, are optional benchmark inputs. If their OHLCV rows are missing, the app labels the theme/sector comparison as limited while leaving the stock's own readiness state governed by its own local data.

## 5. DCF Calculation

The DCF model is a transparent free-cash-flow workflow:

```text
Base FCF = free_cash_flow
or
Base FCF = revenue * FCF margin

Projected FCF[t] = Projected FCF[t-1] * (1 + scenario growth[t])

Discounted FCF[t] = Projected FCF[t] / (1 + WACC)^t

Terminal value = Terminal FCF / (WACC - terminal growth)

Enterprise value = Sum(discounted FCFs) + Discounted terminal value

Equity value = Enterprise value + cash - debt
or
Equity value = Enterprise value - net debt

Fair value per share = Equity value / shares outstanding
```

The default report uses bear, base, and bull scenarios. Scenario assumptions are visible in the report, including revenue growth, FCF margin, WACC, terminal growth, and forecast years. If assumptions are invalid or required inputs are missing, the DCF returns `insufficient_data`, meaning the valuation is intentionally blocked until trusted inputs exist.

DCF output is treated as scenario math, not a price target. The report should show the input path, assumptions, sensitivity, and data-confidence limits so a reader can challenge the model instead of trusting a hidden conclusion.

The Scenario Lab is a session-local review layer over that same DCF engine. It starts from the selected profile's source-backed baseline and permits revenue growth from -50% to 40%, FCF margin from -50% to 45%, WACC from 5% to 20%, terminal growth from -2% to 5%, and a one-to-ten-year forecast horizon; terminal growth must remain below WACC. Missing company eligibility, DCF readiness, provenance, revenue, margin, or shares closes the gate and suppresses all numerical scenario output. Adjustments never modify canonical fundamentals, readiness, reports, or proof history.

The Source Freshness Timeline derives a display chronology from the selected report only. It never substitutes retrieval time for publication or effective time, never treats report generation as source freshness, and never infers a forecast cutoff or revision date. Known events are ordered newest first; invalid or absent timestamps remain explicit unknowns. The timeline explains evidence timing but does not change any lane's readiness state.

The Research Comparison View uses two or three selected tickers from the existing readiness-backed Stock Selector. It preserves selection order and compares asset type, research state, price, fundamentals, DCF, trusted-peer readiness, supported analysis, blocked inputs, next proof, proof freshness, and reviewer-authored catalysts or risks from the selected profile's journal. It never calculates a score or winner and does not fill missing evidence. Candidate peer wording cannot turn a blocked trusted-peer field into a ready one.

The Peer Read-Through Map is a separate evidence view inside the detailed Valuation tab. It checks relationship provenance, explicit business-overlap fields, source-backed peer Revenue/EPS actuals, and target/peer fiscal periods independently. Candidate relationships remain `candidate_context_only`. Trusted relationships without an actual result remain `awaiting_peer_result`; results without both fiscal periods remain `awaiting_fiscal_timing`. Only complete evidence becomes `reviewable_context`, which is directional context only and cannot change forecast, DCF, readiness, ranking, or action outputs.

The Decision-Process Scorecard reviews research discipline for the selected profile and ticker. It checks that readiness was inspected, a thesis and evidence are documented, later review follows recorded conflicting evidence, invalidation and confidence history exist, the review date is current, evidence-change tasks are addressed, and DCF assumptions are visible when DCF is ready. No conflicting evidence is `not_observed`, not automatically complete. Blocked DCF remains `blocked`; monitor-context DCF is `not_applicable`. The scorecard never grades the company, scores expected returns, or changes analysis.

### Conservative DCF Normalization

The product can normalize unusually high or unusually low assumptions before projecting cash flows. This is not a third-party opinion and it does not create new fundamentals. It is a transparent guardrail inside `src/valuation.py` to keep one extreme input from turning into a valuation story without ready inputs.

- Observed revenue growth above the conservative start-growth cap is capped before projection.
- Very negative observed revenue growth is floored before projection so the model does not compound an extreme one-period decline indefinitely.
- Projected early-year FCF growth can be capped even after the revenue-growth path is built.
- Observed FCF margin above the conservative margin cap is capped before projection.
- Normalized long-term growth is kept below WACC, and terminal growth must remain below WACC.

When one of these guardrails is used, the report shows a warning such as `Observed revenue growth ... was normalized before projection` or `Normalized growth target was reduced to keep it conservatively below WACC`. These warnings are part of the model audit trail. They mean the DCF ran with visible conservative limits, not that the product guessed missing data or changed source inputs.

The report uses three DCF states:

- `ready`: the local company inputs are complete enough to review assumptions, scenario math, and sensitivity.
- `blocked`: one or more required company inputs are missing, so the report shows missing fields and withholds valuation interpretation.
- `excluded`: the ticker is an ETF, index proxy, or fund monitor context where operating-company DCF does not apply.

This distinction matters because a blocked DCF is not a negative company signal, and an excluded DCF is not a failed calculation. Both are product gates that prevent valuation language without ready inputs.

## 6. Peer And Relative Context

Peer analysis is separate from standalone DCF.

- Peer trend context can be available when mapped peers have enough local price history.
- Peer valuation context requires source-backed peer mappings and peer valuation inputs.
- Missing peer mappings block the mapping proof path; mapped peers with missing price, fundamentals, market cap, or valuation fields block the peer valuation inputs proof path.
- Sector or industry fallback context, if shown, must be labeled as fallback and not trusted manual peer data.
- Contextual earnings read-through additionally requires a source-backed peer actual and explicit target/peer fiscal periods. Calendar proximity or business similarity is not inferred as period comparability.
- Peer valuation uses a stricter independent gate. A relationship may anchor peer medians only when it has source and as-of provenance, a reviewed `core_peer` or `secondary_peer` role, a relationship rationale, an economic comparability basis, and explicit `valuation_anchor_eligible=yes`. Aspirational, negative, excluded-close, and not-clean roles remain context-only. Legacy mappings without these fields stay visible as relationship context but cannot enter peer medians.

This prevents the report from pretending that peer valuation exists when only partial peer data is available.

## 7. Valuation Status

Valuation status is a gate, not a recommendation.

| Status | Meaning |
| --- | --- |
| Ready | Trusted local inputs are enough to show the relevant valuation view. |
| Partial | Some valuation context is available, but the full stack is incomplete. |
| Blocked | Required inputs are missing, so the valuation conclusion is withheld. |
| Excluded | The method does not apply, such as operating-company DCF for ETF/index/fund monitor context. |

The product does not infer valuation conclusions for blocked rows.

Data confidence follows the same principle: complete trusted inputs can raise data confidence for the supported section, while missing fundamentals, stale prices, missing peers, or unavailable optional context reduce data confidence or keep a section locked. Data confidence is never used to override a blocker.

## 8. Data Confidence And Decision Scores

Data confidence is a data-quality and review-routing signal, not investment conviction.

The decision workflow first calculates a data-readiness score from feature state:

```text
Data readiness score =
  (ready features + 0.45 * partial features) / ready-or-partial-or-blocked features

Then blocked features reduce the score.
Excluded methods can reduce the score when nothing else is ready.
```

The public confidence labels follow the data-readiness score:

| Data-readiness score | Label |
| --- | --- |
| 0.80 or higher | high |
| 0.55 to below 0.80 | medium |
| 0.25 to below 0.55 | low |
| below 0.25 | blocked |

Data confidence is capped by decision bucket so a row with missing core inputs cannot look stronger than the data allows:

| Decision bucket | Data-confidence cap / behavior |
| --- | --- |
| Research Now | Uses data readiness plus local analysis score, capped below full certainty. |
| Monitor | Uses ready monitor inputs and is capped below Research Now. |
| Blocked by Data | Stays low even if some partial context exists. |
| Excluded | Can be clear about method exclusion without becoming a company valuation view. |

This means a DCF-ready company can have medium data confidence when optional context is missing, an ETF/index monitor row can have low or medium data confidence for monitoring while DCF stays excluded, and a price-blocked row stays blocked no matter how interesting the ticker might be.

## 9. Scores And Ranking Context

The product uses setup scores, watchlist scores, data-confidence scores, and monthly
candidate scores only to sort local review queues and explain why a ticker
deserves attention next.

Scores are not:

- Price targets.
- Expected returns.
- Portfolio weights.
- Allocation instructions.
- Buy/sell/hold recommendations.

Blocked data reduces data confidence or keeps a section unavailable. It must not be
converted into a weak score-based conclusion.

Some compatibility output files keep legacy names, including
`outputs/undervalued_candidates.csv`. Treat that file as valuation-readiness and
re-rating context. It is not an automatic undervalued-stock list, and rows with
missing trusted inputs must stay `not_ready`, meaning not enough trusted data exists for valuation, or blocked.

## 10. Report Explanation

Single-stock reports are assembled from the same gates and calculations:

- At A Glance status: mode, decision view, DCF state, peer context, optional context, method cue, and next local step.
- Reader Guide: answers what can be analyzed now, what is still locked or excluded, what trusted input matters next, and the next copy-only command.
- Evaluation Snapshot: summarizes supported evaluation, valuation boundary, data-confidence cue, next proof step, and stop rule before the detailed sections.
- Best Review Path: tells the reader whether to review DCF and peers, prove fundamentals are available, use monitor context, or start with price coverage.
- What can be analyzed now.
- Which mode applies: DCF-ready review, standalone DCF review, price/setup review only, monitor-only context, or data needed before analysis.
- Which calculations ran and which assumptions were used.
- Which sections are blocked or excluded.
- What local input would prove the next useful research step is available.
- Copyable Proof Commands for local, capped, research-only follow-up workflows.
- Which sources were used and how fresh they are.

The report should be read top-down: visitor scan cue first, At A Glance second, Reader Guide third, Evaluation Snapshot fourth, Proof Checklist fifth, Best Review Path sixth, supported analysis next, blocked or excluded analysis next, copyable local proof commands next, then source readiness and valuation detail. The commands are displayed for the reader to copy manually; the report does not run imports or refreshes and does not connect to external accounts.

When a company ticker has the full trusted local input stack, the single-stock report can show:

- At A Glance mode, method cue, and next local step.
- Evaluation Snapshot for supported evaluation, valuation boundary, data-confidence cue, next proof, and stop rule.
- Best Review Path for the safest reading order and proof step.
- Analysis Quality and Evaluation Function Check summaries.
- Price, momentum, liquidity, and market-context review.
- Fundamentals quality context from the imported local company row.
- Standalone DCF assumptions, bear/base/bull scenario values, and sensitivity context.
- Peer trend or peer valuation context only when source-backed peer inputs are ready.
- Earnings or analyst-estimate context only when trusted optional rows are ready.
- Copyable local commands for optional context, peer review, or source-readiness checks when more trusted data is needed.
- Source-readiness notes and the next research question.

When any part of that stack is missing, only the supported sections appear. The report keeps the blocked section visible and explains the exact local input needed next, plus the local command path for inspecting or proving that input.

## 11. Readiness Proof Ladder

The product uses the same readiness proof ladder in the dashboard, single-stock reports, and Data Health review lists:

| Step | What becomes available | What can be analyzed | What stays unavailable |
| --- | --- | --- | --- |
| 1. Prices | Trusted local price rows. | Price/setup review, trend context, basic risk context when enough history exists. | Fundamentals, DCF, peers, earnings, and estimates. |
| 2. Fundamentals / DCF inputs | Trusted company fundamentals with revenue, free cash flow or FCF margin, shares outstanding, and source metadata. | Fundamental field review and standalone DCF assumptions, scenarios, sensitivity, and fair value/share math. | Peer-relative valuation and optional earnings/estimate context. |
| 3. Source-backed peers | Trusted peer mappings first, then explicit peer role, economic comparability and valuation-anchor review, then mapped-peer price, fundamentals, market cap, and valuation inputs. | Peer trend context first, then peer-relative valuation only when at least two eligible anchors and their mapped-peer valuation inputs pass readiness. | Peer premium/discount or peer DCF comparison when roles, comparability, anchor decisions, mappings, or mapped-peer inputs are incomplete. |
| 4. Optional context | Trusted earnings and analyst-estimate CSV rows. | Earnings timing context and analyst-estimate context. | Optional sections remain unavailable when those rows are missing. |

Each step is permission to review a specific analysis layer, not permission to invent the next layer. Price-ready does not mean fundamentals-ready. Fundamentals-ready does not mean DCF-ready unless all required DCF fields pass. DCF-ready does not mean peer-ready. Peer-ready does not mean earnings or analyst estimates are available.

The no-conclusion boundary is explicit: blocked rows must not be labeled undervalued, overvalued, DCF-ready, peer-ready, or optional-context-ready until the trusted input gate for that label passes. ETF, index proxy, and fund rows follow a separate monitor path where operating-company DCF and peer valuation are excluded, not failed.

The safe local sequence is:

1. Inspect the focused review list or report, such as `make focus-fundamentals TICKER=NVDA` or `make focus-peers TICKER=A`.
2. Stage trusted rows only in the matching local CSV path, such as `data/imports/fundamentals.csv`, `data/imports/peers.csv`, `data/staged/earnings/`, or `data/staged/analyst_estimates/`.
3. Run validation and preview before apply: `make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch>`, then `make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>`; apply only after validation passes, preview scope is intended, and rejected rows are zero.
4. Regenerate readiness, then read the report again before interpreting the newly available section.

This ladder is why empty or partial outputs are useful: they show the first trustworthy proof step instead of hiding the gap behind a weak conclusion.

## 12. Earnings Nowcast Pilot Method

The Earnings Nowcast pilot is a separate readiness-gated lane. It does not reuse generic optional-context readiness and does not let an earnings date, current target price, candidate peer, or provider availability unlock a forecast.

The deterministic baseline requires at least five source-backed prior quarterly actuals, the matching prior-year fiscal quarter, and an exact forecast-period point-in-time consensus snapshot available at the forecast cutoff. Fiscal-period rows are canonicalized before history is counted: exact duplicates count once, an explicit source reference can supersede a prior row, and unresolved conflicting values block only the affected metric. Revenue and EPS are evaluated independently and must use comparable currency, unit scale, accounting basis, EPS share/operations basis, and split treatment. A stable Revenue history may produce a range while incompatible or unstable EPS remains withheld. Each snapshot records the fiscal period, cutoff, expected report date, forecast horizon, model version, immutable input hash, freshness state, and source IDs.

SEC actual staging has a narrower primary-source lineage rule. Q1-Q3 accepts only 60-120 day SEC Companyfacts duration facts with a one-to-one fiscal identity/period-end mapping; cumulative facts and comparative facts without a source-backed original identity are rejected. Companyfacts EPS is explicitly marked `companyfacts_split_basis_unverified`, which cannot match an `as_reported` or split-adjusted consensus definition. Q4 is accepted only from an explicit fiscal-Q4 result table in a SEC-filed exhibit whose selected value column states one period-end date; filing timestamps and submission report dates are not substitutes. It is never derived by annual-minus-nine-month arithmetic, and guidance, ambiguous headers, or Q4 metrics spanning separate exhibits remain withheld. Evidence is append-only and cutoff-aware, so complete revision chains select the latest source-backed presentation without replacing historical evidence. The stage reports source-backed quarter-continuity gaps without inventing a missing fiscal period or value. Revenue and EPS readiness stay separate; EPS is withheld whenever split-adjustment, share, operations, accounting, currency, or scale basis is not source-backed and comparable across its usable history. The same sentinel is enforced downstream: Business Trend never displays or compares its EPS value, commercial cohort scope cannot override it, and backtesting cannot use it as a target or prior-year EPS outcome. Revenue evaluation remains independent.

Filed-Q4 split basis has its own fail-closed proof boundary. Missing or malformed primary split language records `primary_split_basis_unverified`, not `as_reported`. Both unverified sentinels fail the shared downstream predicate, and arbitrary nonempty basis text is not treated as proof. Only a supported declared basis token or an explicitly parsed dated split statement can unlock EPS comparability; Revenue remains independent.

The model combines recent sequential behavior and same-quarter year-over-year seasonality with fixed versioned weights. It emits ranges and a `higher`, `aligned`, or `lower` consensus-relative classification. It does not accept a text-generated numeric adjustment. Peer earnings, company news, industry indicators, and macro evidence are directional context only; candidate peers remain `candidate_context_only`, while a reviewed trusted source may raise the context state without changing the numerical baseline.

Historical evaluation is chronological walk-forward only. The target actual and later consensus snapshots are excluded from model inputs and used only for scoring after the forecast. A consensus row retrieved on or after the target report is a leakage failure even when its stated snapshot time is earlier. Conflicting rows at the same latest snapshot timestamp are excluded as an ambiguous revision, and a snapshot more than 90 days before the target report is excluded as stale. Fewer than 20 valid events is `backtest_insufficient`, not backtest-ready. Reports separate valid events from exclusions, group exclusion reasons, and include Revenue/EPS error, WAPE where valid, Revenue/EPS/joint interval coverage, directional accuracy, leakage failures, and latest-consensus/prior-year benchmarks. A sample that meets the event minimum but fails to improve the latest-consensus Revenue or EPS benchmark fails the validation verdict with an explicit gate. Numerical Beat/Miss probability stays unavailable until at least 100 valid out-of-sample observations pass finite-value, Brier-score, calibration-bin, and constant-rate benchmark gates. Every populated calibration bin reports its size, mean forecast probability, observed rate, and minimum-size status.

The committed `SYN1`-`SYN5` cohort is synthetic test evidence only. The intended five-company SEC staging scope is NVDA, AMD, AVGO, MU, and QCOM, but real pilot output remains `awaiting_point_in_time_consensus` until exact historical consensus evidence is present. This proves neither real semiconductor coverage, predictive accuracy, nor data freshness. The pilot does not predict post-earnings price movement and does not provide investment advice.

The cohort readiness board reports actual-history, Q4, split-basis, exact-period consensus, backtest, and calibration gates independently. Prospective collection preserves immutable snapshots and revisions; it does not reconstruct historical consensus from a current estimate. Provider configuration is an access state, not an evidence or rights state.

Prospective collection preview also evaluates the exact declared source against the checked-in rights registry without splitting composite identifiers or inferring aliases. Technical `write_allowed` remains the append-only review decision. Commercial evidence separately requires approved rights plus literal `revenue_consensus` support when Revenue is populated and literal `eps_consensus` support when EPS is populated. Explicit Commercial Research mode conjuncts these states before a write and returns before filesystem mutation when either gate is incomplete; research mode retains its explicit reviewed local path. Passing this guard does not prove the estimate payload, point-in-time history, freshness, comparability, reviewer acceptance, calibration, or nowcast readiness.

The earlier source-row validation boundary follows the same independence rule. Its exact normalized provider is resolved through the checked-in registry rather than a caller-declared rights label. Schema, fiscal-period, timestamp, value, and comparability failures determine technical rejection; only technically accepted rows enter commercial counts. Each accepted row requires `revenue_consensus` and `eps_consensus` scope only for the metrics it actually populates. Composite identifiers remain one unknown exact source, and `historical_evidence_reviewable` is a routing state rather than evidence activation or a readiness promotion.

Collection preview and source-row validation share one pure commercial field-scope function. For one exact source ID it combines the existing rights decision with the literal ordered fields required by populated metrics; empty or duplicate field names are invalid, and unknown or composite IDs receive no alias expansion. This centralization changes no technical acceptance, blocker vocabulary, collection rule, or readiness state. Registry metadata cannot establish payload correctness, timestamp integrity, metric comparability, reviewer approval, collection, activation, backtesting, or calibration, and non-consensus evidence domains keep their own contracts.

The supported source-review command is the read-only operating boundary before collection preview: `make earnings-consensus-source-review INPUT=<reviewed_source_export.csv> PROVIDER=<source_id> AS_OF=<timestamp>`. It reads the supplied upstream export without field enrichment, requires explicit provider identity and cutoff, and routes its ordered row mappings through the same validator. Human and JSON output expose rejected rows, candidate versus historical scope, rights, and metric scope; a completed review returns evidence even when the state is blocked. Invocation or ambiguous CSV-shape errors fail nonzero. The source-review export and prospective collection row are distinct input contracts; an accepted source row must be separately reviewed and explicitly mapped into the prospective schema, and the product neither infers fields nor writes that mapping. Neither outcome collects a row, changes readiness, or establishes activation.

Pull-request engineering hygiene is range-based, not working-tree-based. The hosted event supplies exact base/head SHAs, checkout fetches their history, generated-artifact classification reads `BASE...HEAD`, and whitespace checks the same range. A clean checkout is therefore not treated as evidence that the PR changes no files. This automation is read-only engineering evidence, not source review, user validation, or merge approval.

Temporal validation is fail-closed for both source categories. The caller supplies one explicit UTC review cutoff, each row declares exactly `current_only` or `point_in_time`, and technical acceptance requires `snapshot_at <= retrieved_at <= review_cutoff`. Equality is allowed; missing/unknown scope, reversed ordering, invalid UTC timestamps, and post-cutoff evidence are rejected before a commercial row is counted. The cutoff does not infer publication time or prove provider availability, rights, payload correctness, freshness, collection, nowcast readiness, backtesting, or calibration.

Batch collection preserves input order and evaluates each row against an in-memory virtual ledger containing saved evidence plus earlier technically reviewable proposed rows. Technical and commercial batch decisions remain separate. An empty input or any technical blocker rejects the complete record operation; explicit Commercial Research mode additionally requires every row's commercial evidence to pass. The CLI preview exposes the same row states and ordered blockers used by record, so a deterministic later rejection cannot leave earlier proposed rows appended. No row is reordered or repaired. This contract does not claim concurrent-writer exclusion or crash-safe transactionality.

The saved prospective ledger is itself an input to that decision and is revalidated in full before status, preview, or record. Every row must satisfy the schema, snapshot IDs and evidence identities must be unique, and each ticker/period must form exactly one append-ordered, timestamp-increasing root-to-current-leaf revision chain. Preview produces a deterministic receipt bound to the normalized cutoff, Commercial Research mode, complete proposed batch, and complete saved ledger. Record requires the same cutoff and receipt and recomputes the decision before mutation; any changed input or intervening ledger write requires a new review. The receipt is local integrity evidence only, not proof of source truth, rights, reviewer approval, process locking, or crash recovery.

Daily price lineage uses one temporal rule across normalization, staged validation/preview/apply, and DCF promotion review. For observation date `D`, local review uses `D + 1 day 00:00 UTC` as the earliest conservative availability boundary. A declared retrieval must carry an explicit timezone offset, must not precede that boundary, and must not exceed the explicit timezone-aware review cutoff. This does not infer an exchange close or provider publication time. Missing retrieval remains an independent lineage gap; malformed, naive, too-early, post-cutoff, or cutoff-unreviewed retrieval cannot become trusted commercial evidence or enter a canonical apply. Apply writes the one previously validated in-memory staged frame through same-directory atomic replacement, without claiming concurrent locking or crash-safe transactionality.

Historical valuation regime context is computed only from observations where the denominator was publicly available by the matching numerator timestamp. Each metric definition forms a separate segment, and fewer than eight compatible observations remains `insufficient_history`. The output is a descriptive range and percentile, never a cheap/expensive label or recommendation.

Research outcome review is an append-only learning loop tied to an original thesis and a closed observation window. Catalyst evidence is a cutoff-safe timeline of reviewed events. Neither uses price returns, sentiment scoring, or narrative adjustments to grade the company, grade the researcher, or change a numerical model.

### Forward View V1

Forward View is a deterministic composition of existing evidence, not a second forecast or valuation engine. It keeps five lanes separate: explicit quarterly Revenue/EPS trend, source-backed DCF bull/base/bear scenarios, trusted peer read-through, reviewer-authored thesis evidence, and the independently gated Earnings Outlook.

Scenario values appear only when DCF readiness passes, source metadata retains both source and source reference, and all three bounded scenarios calculate from the same saved report. Stale profile evidence is labeled partial. Candidate peers, news context, generated narrative, and journal text cannot change Revenue, EPS, DCF assumptions, valuation scenarios, or probabilities. Numerical surprise probability remains governed by the Earnings Nowcast calibration gate.

Every Forward View packet shows its source cutoff, saved-profile freshness, model version, withheld fields, and one next research task. It accepts the production stock-report provenance contract (`provider`, `retrieved_at`, `official`, freshness, and notes) or an explicit source/source-reference pair, and preserves that provenance under Advanced evidence. Any stale, mixed, missing, or unknown saved-profile freshness downgrades otherwise usable sections to review-due rather than presenting them as current.

The Earnings Outlook lane loads only a real source-backed packet for the exact fiscal period named by the selected report. It never silently chooses a different real-company forecast period, never displays synthetic fixture evidence in the workbench, and reads the independent `probability_available` calibration gate before changing probability wording. Missing or incompatible evidence fails closed. The result describes plausible assumption cases and research wait conditions; it does not predict post-earnings price direction, rank companies, or provide an investment recommendation.

## 13. Methodology Limits

This is not a full data-vendor terminal, analyst-estimate service, or execution workflow. The useful strength is transparency: the app shows exactly what local data supports and refuses to overstate missing analysis.

The current methodology is strongest for:

- Readiness and missing-data diagnosis.
- Single-stock report explanation.
- Price and setup context when local price history exists.
- DCF-ready company review when trusted fundamentals are present.
- ETF/index/fund monitor context where company DCF is excluded.

The current methodology remains limited when:

- Fundamentals are missing or stale.
- Peer mappings or peer valuation inputs are unavailable.
- Earnings and analyst-estimate rows have not been imported.
- A ticker has too little local price history.

## 14. Where This Lives In Code

The methodology is implemented in project code, not hidden in a model prompt.

| Method layer | Main local code |
| --- | --- |
| Readiness gates | `src/readiness_engine.py`, `src/dcf_readiness.py`, optional-context readiness helpers |
| DCF and relative valuation | `src/valuation.py`, `src/value_engine.py` |
| Research decision fields | `src/research_decisions.py` |
| Single-stock report wording | `src/stock_report.py` |
| Dashboard methodology and status views | `src/dashboard.py` |
| Earnings Nowcast contracts, readiness, model, backtest, signals, and packet | `src/earnings_nowcast_*.py` |

The local CSV files provide inputs. The product code decides what can be analyzed, what must stay blocked, and what explanation appears.
