# Provenance Contract

This contract defines the minimum evidence boundary for Stock Research Command Center. It applies to the dashboard, reports, imported rows, and public demo package.

The product principle remains: data readiness first, analysis second, research decision last. A displayed calculation is not an investment recommendation, and an unavailable input remains unavailable.

## Record Contract

Every analysis-ready record or report section should expose, directly or through its source/readiness detail:

| Field | Meaning | Boundary |
| --- | --- | --- |
| `readiness_state` | `ready`, `partial`, `blocked`, `excluded`, or an evidence outcome such as `candidate_context_only`. | A state is not a recommendation. |
| `source` | Named local, SEC, provider, filing, or reviewed source origin. | Source availability alone does not render a value usable. |
| `as_of_date` | Financial period, market date, filing date, or source effective date. | It is not the same as retrieval time. |
| `reporting_period` | Fiscal period attached to a financial, earnings, or estimate record, where supplied. | A reporting period is not inferred from the retrieval date or a market price date. |
| `currency` | Source-supplied price or financial currency, where available. | The product does not infer currency, perform cross-currency conversion, or treat absent currency as a common unit. |
| `retrieved_at` | When a provider or local artifact was obtained, where available. | Missing retrieval time lowers freshness certainty; it does not get invented. |
| `method_version` | Version of the project rule or calculation that produced the section. | Method changes must be documented before public claims change. |
| `missing_inputs` | Required fields that are absent, stale, malformed, or unproven. | Missing inputs suppress the dependent conclusion. |
| `confidence_boundary` | Plain-language limit on how the section can be used. | It must never override a blocked or excluded state. |

## Lane Requirements

| Lane | Minimum source evidence | What stays withheld without it |
| --- | --- | --- |
| Price and risk context | Valid OHLCV rows with date and provider/source context. | Trend, momentum, and risk claims beyond the available history. |
| Fundamentals | Source-backed financial fields plus reporting period/as-of information. | Quality, leverage, margin, or growth interpretation for absent fields. |
| Share count | Explicit filing or trusted source fact with date/context. | Per-share DCF math; shares are never inferred from price or market cap. |
| DCF | Price, revenue, free cash flow or FCF margin, shares, method assumptions, and company eligibility. | Fair-value scenario math and valuation interpretation. |
| Candidate peers | Industry, SIC, product, or other contextual suggestion. | Candidate context must not satisfy trusted-peer readiness. |
| Trusted peers | Source-backed relationship, review rationale, source/as-of date, reviewer-assigned peer role, economic comparability basis, explicit valuation-anchor decision, and required peer inputs. | Peer-relative valuation and comparative conclusions. |
| Earnings and estimates | Trusted provider/import fields, fiscal period, source, and retrieval/as-of context. | Optional readiness or consensus interpretation from date-only or target-only rows. |
| Earnings Nowcast | Prior quarterly actuals plus an exact-period point-in-time consensus snapshot, all timestamped no later than the forecast cutoff; model version and input hash are mandatory. | Revenue/EPS range, consensus-relative classification, and every probability output. Candidate signals never satisfy this gate. |

Trusted-peer relationship provenance and valuation-anchor eligibility are independent. A source-backed mapping remains relationship evidence, but peer medians additionally require a reviewed `core_peer` or `secondary_peer` role, explicit relationship rationale, economic comparability basis, and `valuation_anchor_eligible=yes`. Missing fields, other roles, and legacy mappings remain context-only. No role or comparability field may be inferred from sector, industry, peer group, popularity, or existing row count.

## Earnings Nowcast Point-In-Time Contract

Every forecast event must preserve `ticker`, `fiscal_period`, `as_of_timestamp`, expected report date and forecast horizon when known, source publication/retrieval timestamps, direct source references, Revenue/EPS metric definitions, `model_version`, `input_snapshot_hash`, readiness/freshness states, and source IDs. Historical consensus snapshots are append-only evidence. An exact duplicate is not re-added; a revised or currently visible estimate is retained as a separate revision and must not overwrite the snapshot that was knowable at a prior cutoff. Duplicate actual rows cannot inflate quarterly history, and conflicting actuals remain blocked unless an explicit `supersedes_source_ref` resolves the revision chain.

SEC quarterly actuals follow the same append-only cutoff boundary. Q1-Q3 requires a 60-120 day SEC Companyfacts duration fact with a one-to-one source-backed fiscal identity/period-end mapping. Companyfacts EPS is marked `companyfacts_split_basis_unverified` until separate primary evidence proves comparability. Q4 requires one explicit result table and one selected-column period-end date in a SEC-filed primary-source exhibit; filing metadata cannot supply that date, and annual-minus-nine-month derivation is forbidden. Staging may identify source-backed quarter-continuity gaps, but it must not infer the missing period, Revenue, EPS, or fiscal basis. Revenue and EPS are independently ready, and EPS is withheld if its split-adjustment, share, operations, accounting, currency, or scale basis is not comparable within the source-backed history. The unverified sentinel cannot enter Business Trend values/comparisons, cohort EPS usability, target EPS backtest outcomes, prior-year EPS benchmarks, or consensus EPS benchmarks. A Revenue-bearing backtest event can remain Revenue-evaluable, but an EPS-only sentinel target is excluded. Stage output is review-only, always declares `automatic_apply=false`, and is rejected for canonical data/import paths or existing non-generated evidence directories.

## Quarterly Cash-Generation Evidence Contract

Operating income, cash from operations, and reported capital expenditures use a separate versioned observation contract with ticker, fiscal period, period end, value, currency, scale, accounting basis, duration basis, source, immutable source reference, publication time, retrieval time, and explicit revision lineage. Q4 observations must carry `explicit_filed_quarter`; annual-minus-nine-month derivation, filing-metadata period substitution, and inferred Q4 values remain forbidden. Exact duplicates may collapse, one explicit revision leaf may supersede an older source reference, and unresolved conflicting leaves block only the affected component.

Derived operating margin, free cash flow, and FCF margin exist only in memory and retain all component source references for Advanced evidence. The implementation adds **no new data file, writer, template, or generated artifact**. Production remains withheld until a reviewed source adapter supplies compatible observations; synthetic observations remain test-only. These derived points cannot write canonical inputs, alter deterministic forecasts, or unlock valuation, consensus, catalysts, outcomes, backtesting, or calibration.

The one-company adapter acceptance result is also in-memory. It records deterministic identity, source-rights, supported-field, cutoff, revision, component, compatibility, complete-period, and explicit-Q4 decisions without fetching or persisting a payload. Every result preserves `production_activation=false` and `readiness_promotions=()`. `accepted_for_review` proves only that a candidate batch passed the local contract; it does not change the source-rights registry, authorize storage or redistribution, establish a reviewed real-company source, or promote any product readiness state.

The target-period actual and every source published after the cutoff are evaluation evidence only and must never enter forecast inputs. Trusted peer/news signals require explicit source, publication time, excerpt hash, review state, and trusted-peer relationship evidence where applicable. They remain directional context and cannot create a numeric adjustment or numerical probability.

The synthetic fixture packet is software-test evidence only. The five-company SEC staging scope (NVDA, AMD, AVGO, MU, and QCOM) is not a coverage claim. Real output remains `awaiting_point_in_time_consensus`, and numerical probability remains `awaiting_calibration_evidence` until the documented out-of-sample gates pass.

Prospective consensus snapshots are append-only. Each row preserves a unique snapshot ID, ticker, fiscal period, snapshot and retrieval timestamps, source and durable reference, Revenue/EPS values when present, complete comparability definitions, expected report date, review state, and an explicit superseded snapshot ID for revisions. Current-only provider payloads remain candidate context and cannot be relabeled as historical point-in-time evidence.

Consensus collection preview preserves two independent decisions. Technical validity covers schema, cutoff, immutable identity, revision lineage, cooldown, and explicit review state. Commercial evidence uses the exact source ID, explicit commercial approval, and the registered scope required by each populated metric: `revenue_consensus` for Revenue and `eps_consensus` for EPS. Unknown, composite, unverified, or scope-incomplete sources fail closed without inferred provider identity. Explicit Commercial Research mode refuses the append before directory or ledger mutation when commercial evidence is incomplete; research mode keeps its reviewed local append contract. A passing guard cannot certify payload correctness, source freshness, comparability, historical depth, calibration, or readiness.

The prospective ledger is validated as a whole before status, preview, or record. Each ticker/period must form exactly one append-ordered, timestamp-increasing root-to-current-leaf chain with unique snapshot IDs and unique evidence identities. Missing parents, cross-scope revisions, multiple roots, forks, cycles, reversed order, and non-leaf supersession fail closed. Batch preview emits a deterministic receipt bound to the normalized review cutoff, Commercial Research mode, complete proposed input, and complete existing ledger; record recomputes that receipt immediately before mutation and refuses any mismatch. This narrows the reviewed mutation boundary but does not claim multi-process locking or crash-safe transactionality.

Price provenance separates field presence from temporal integrity. `retrieved_at` is complete only when it has an explicit timezone and the shared daily-price validator proves `observation availability <= retrieved_at <= review cutoff`; a parseable naive value is not UTC evidence. Normalization, staged preview/apply, and DCF lineage use the same blockers. A declared invalid retrieval blocks canonical apply before backup or write, while an entirely missing retrieval remains visibly incomplete and can stay technical research context only. Successful apply uses the exact once-read validated frame and an atomic same-directory replacement. Atomic replacement does not prove source truth, publication timing, reviewer intent, locking, or recovery across backup and replace.

Consensus source-row validation cannot receive provenance permission as a caller label. It resolves the exact provider against the same registry and returns registry-derived rights plus row-specific required and missing metric scopes only for technically accepted rows. Candidate context and point-in-time reviewability remain visible when commercial evidence is incomplete, but neither state can authorize append, activation, readiness, backtesting, or calibration. Invalid rows never become commercially ready merely because their source record is approved.

The prospective collector and source-row validator obtain their registry-derived decision from the same immutable commercial field-scope review. The result retains the exact source ID, rights state, ordered required fields, ordered missing fields, and the combined metadata gate; it rejects blank or duplicate requirements and never infers aliases or composite membership. Consumer-specific technical states, blockers, and mutation rules remain separate. This decision cannot prove the payload, timestamps, comparability, reviewer intent, collection, activation, freshness, readiness, backtesting, or calibration.

`make earnings-consensus-source-review INPUT=<reviewed_source_export.csv> PROVIDER=<source_id> AS_OF=<timestamp>` exposes that source validation as a read-only gate before collection preview. It accepts no default provider or cutoff, preserves original one-based accepted and rejected row positions, refuses blank/duplicate headers and undeclared extra values, and writes neither normalized rows nor a report file. This upstream contract requires explicit `history_scope`; it is distinct from the prospective collection contract's `review_state`. A human-reviewed, evidence-preserving mapping into the existing prospective schema is a separate step with no automatic transformer or writer. The returned rights and scope evidence comes only from the checked-in registry; it cannot prove payload correctness, durable-reference validity, publication availability, collection, activation, readiness, backtesting, or calibration.

Each source-row validation result also preserves its normalized review cutoff. A row must declare an exact supported history scope and satisfy `snapshot_at <= retrieved_at <= review_cutoff` before commercial evidence is evaluated. Rejected rows retain their original one-based positions, and valid sibling rows are reviewed independently. This local cutoff guards leakage and ordering; it does not manufacture a publication timestamp, source reference, permission, freshness state, or activation decision.

A multi-row prospective input is one ordered review batch. Preview builds a virtual ledger from saved rows and earlier technically reviewable proposed rows, preserving complete row-level technical and commercial evidence. Record consumes that same batch decision and refuses the entire mutation when any technical blocker exists or, in Commercial Research mode, any rights or populated-metric scope is incomplete. The saved ledger remains unchanged after a deterministic batch rejection. Successful record appends all reviewed rows in supplied order through one handle; it does not rewrite earlier evidence. This is validation consistency, not a guarantee against concurrent writers, process interruption, or filesystem failure.

Historical valuation observations preserve the numerator timestamp, denominator period end, denominator availability timestamp, metric definition ID, retrieval time, and source reference. A denominator unavailable at the historical price timestamp is rejected. Definition changes create separate history segments instead of a mixed regime.

Research outcome and catalyst ledgers are append-only reviewed evidence. Outcomes retain the original thesis entry, observation window, review time, source, and learning; they contain no return or skill score. Catalysts retain publication, retrieval, effective time, event type, evidence state, and reviewer. Neither ledger mutates source data, readiness, forecasts, probabilities, DCF assumptions, or recommendations.

## Freshness Rules

Freshness is lane-specific. A price date, a filing date, and a peer review date answer different questions.

- Price context: use the latest available market date and row-history depth; a short history may remain partial.
- Fundamentals and share count: use filing date and reporting period; quarterly or annual changes do not invalidate an older filing, but the report should surface its period.
- Peer mappings: use source review date; candidate suggestions do not acquire freshness merely because price data refreshed.
- Earnings and estimates: use provider retrieval and estimate period; unsupported fields remain optional context only.
- Earnings Nowcast: use the forecast cutoff, actual publication time, consensus snapshot time, retrieval time, and fiscal-period identity. A current price or later revised estimate cannot refresh an older point-in-time forecast.
- Screenshots and the demo manifest show product/package evidence. They are not data-freshness proof.

## Method Versioning

The current public methodology is **v1 readiness-first deterministic gates**. A change to a gate, valuation formula, eligibility rule, assumption cap, source normalization, or public interpretation must:

1. Update `docs/METHODOLOGY.md` and this contract.
2. Add or update regression tests for the changed rule.
3. Preserve prior readiness truth until source rows are rebuilt and reviewed.
4. Surface the new `method_version` in the affected report or data artifact when that output is regenerated.

## Demo Boundary

The `demo` profile is a compact tracked snapshot with a manifest, checksums, selected tickers, and known limitations. It proves that the product workflow can render and explain readiness states. It is not data-freshness proof and does not unlock blocked inputs.

The `local` profile is an ignored mutable workspace for refreshed research data. It may contain newer local rows, but those rows need the same validate, preview, apply, rebuild, and proof gates before they change a readiness claim.

Both profiles remain research-only: no broker execution, order routing, auto-trading, direct buy/sell instructions, or fabricated values.

## Readiness Promotion Evidence Review Contract

The stdout-only readiness preview treats a false-to-true fundamentals or DCF flag as a proposed technical change, not as proof that its source is correct, commercially permitted, current, or complete. For each proposed promotion it recovers the exact canonical fundamentals source value, as-of date, durable source reference when supplied, exact checked-in commercial-rights decision, and registered support for `revenue`, `free_cash_flow`, `fcf_margin`, and `shares_outstanding`.

Source identifiers are exact. A composite or unregistered value is not split, normalized to a registered component, or granted inferred rights. Missing or duplicate canonical rows, missing source/as-of/reference fields, unapproved exact sources, and missing registered field support fail closed in the evidence review without changing the technical readiness frame. The fundamentals review does not establish price-source provenance required by DCF. Even a complete review is inspection evidence only; it cannot write an artifact, mark stale readiness current, edit the rights registry, or authorize the separate reviewed make readiness rebuild.

### DCF Price-Lineage Review

For each false-to-true DCF promotion, the no-write preview reviews the exact latest canonical price row independently. A usable selection requires a parseable observation `date`, a positive numeric `close`, the greatest date for the ticker, and exactly one row at that date. Missing usable rows and duplicate latest-date rows fail closed rather than selecting by row order.

The selected row must carry an exact `source`, durable `source_ref`, and parseable `retrieved_at`. The exact source must be commercially approved and its checked-in rights record must explicitly support `prices`. Technical promotion, row selection, lineage completeness, commercial rights, and registered field scope remain separate states. Missing or composite sources are not split, normalized, inferred, or granted borrowed rights.

The market observation date, `as_of_date`, local file name or modification time, adapter/provider availability, refresh warning text, and numerical row shape are not substitutes for provider identity, retrieval time, or a durable source reference. The audit changes no technical readiness, canonical row, valuation result, source-rights record, freshness state, or reviewer decision. A complete result would still be inspection evidence, not authorization for `make readiness`; an incomplete result does not by itself invalidate the row for local research context.

The prospective manual price path can preserve explicit `source_ref` and `retrieved_at` values alongside `source`. These values must be reviewer supplied; the normalizer generates no fallback reference or retrieval timestamp. Validation normalizes a valid retrieval timestamp to UTC and reports lineage completeness separately from technical row validity. Preview retains the summary, while apply remains a distinct reviewed mutation with the existing backup and merge boundary. Preserved lineage is necessary but not sufficient: exact-source rights, registered `prices` scope, payload review, freshness, apply intent, and rebuilt readiness remain independently required.

Validation and preview join every exact retained source ID to the checked-in rights record without splitting composite IDs or inferring aliases. They report commercial eligibility and literal `prices` field support separately for approved, unverified, unknown, blank, and mixed batches. Technically invalid rows do not enter these counts. The result is review evidence only: it cannot edit the registry, prove the payload, authorize apply, or promote readiness.

Explicit Commercial Research mode enforces lineage completeness, exact-source rights approval, and registered `prices` scope immediately before staged-price mutation. A failed gate returns without backup creation or canonical write and retains the preview evidence for review. Research mode preserves its separate local apply contract. Guard passage does not certify the payload, reviewer decision, source freshness, readiness build, or proof record.

Direct price refresh has a separate defense-in-depth mutation boundary. Concrete Stooq, Yahoo, FMP, Alpha Vantage, Finnhub, and IBKR implementations expose exact source IDs; automatic-ladder labels must equal the child identity. In explicit Commercial Research mode, every reachable source must independently have approved rights and literal `prices` scope before fetch, and the exact source that returns rows is rechecked before it can enter the merge or status set. A supplied source with missing, changed, composite, unapproved, or scope-incomplete identity is refused without canonical or status mutation. Provider aliases and ladder labels cannot grant or borrow rights. This local guard does not supply row-level `source_ref` or `retrieved_at`, approve a checked-in source, prove provider access or payload quality, or authorize readiness rebuild.

Focused-cohort saved rows use lane-specific provenance and scope. A technically populated value needs an exact source plus durable source reference, approved commercial rights, and the literal registered field for that lane before Commercial Research coverage becomes usable. Margin aliases are reviewed as their exact populated margin field; FCF aliases require `free_cash_flow`; cash and debt are independent; shares require `shares_outstanding`; filing and earnings dates require `filing_dates` and `earnings_dates`; each populated consensus metric requires `revenue_consensus` or `eps_consensus`; and every trusted relationship row requires `trusted_peers`. One supported field never grants a sibling field. Candidate relationships do not enter the trusted decision. These Advanced coverage decisions do not edit canonical evidence, readiness, source rights, forecasts, valuation, or peer roles.

Focused-cohort adjusted price history conjuncts saved readiness with canonical row evidence. At least one row must have a valid date and positive adjusted close or close; every retained row must carry exact source, durable reference, and retrieval timestamp, and every exact source must have approved rights plus literal `prices` scope. Mixed histories fail closed without provider inference. This display review does not validate retrieval chronology, rewrite canonical history, or change research-mode readiness.

Focused-cohort quarterly Revenue/EPS display eligibility conjuncts the existing technical trend state with a metric-specific commercial review of every populated accepted canonical row. Each row needs exact source, durable reference, retrieval timestamp, approved commercial rights, and literal `revenue` or `eps` scope. One unapproved, unknown, or scope-incomplete populated row blocks only that metric. Revenue permission never grants EPS permission. This review does not repair rejected rows, resolve revision conflicts, verify EPS split basis, establish explicit-Q4 evidence, change readiness, or activate Earnings Nowcast.

The preview also preserves the method reason for newly excluded DCF transitions. Named reasons are a deterministic explanation of the existing scope decision; absent metadata remains unexplained instead of inferred. Ready, partial, excluded, added, and removed transition counts are independent and may overlap. They are not current readiness totals, evidence of company quality, a ranking, or a recommendation.

## Research Change Event Contract

A research change event requires two comparable generated snapshots from the same selected profile. Each event preserves a deterministic event ID, ticker, event family/subtype, prior/current values, source and source reference, source publication time when available, retrieval and detection time, selected profile, prior/current snapshot identities, evidence status, materiality, and a research-only review task.

Publication time, retrieval time, and detection time are different facts and must not be substituted for one another. Missing source timestamps stay missing. A missing prior snapshot is `baseline_missing`; it does not prove that nothing changed. Cross-profile comparison is invalid.

Event review outcomes are append-only evidence. The latest valid outcome controls whether an event remains in the open queue, but historical rows are retained. Review resolution never mutates canonical sources or readiness. Candidate context, provider reachability, or a detected event cannot become trusted evidence without the existing source review, validation, preview, rejected-row, apply, readiness rebuild, and proof gates.

## Research Thesis Journal Contract

`data/research_thesis_journal.csv` is the canonical reviewed, append-only journal ledger. Every row identifies schema version, entry ID, selected profile, ticker, thesis ID, entry type, recorded/effective timestamps, reviewer, summary, evidence direction, source, durable source reference, source publication timestamp, confidence, review due date, and `supersedes_entry_id`.

Source publication and effective timestamps cannot be later than the recorded timestamp. Evidence, catalyst, risk, and invalidation rows require source provenance. Thesis revisions must remain within the same profile, ticker, and thesis chain and must preserve the prior row. Generated report text, detected changes, queue outcomes, and synthetic fixtures cannot create a reviewed journal entry automatically.

## Scenario Lab Contract

The Scenario Lab never writes canonical data, readiness, reports, or proof records. It derives an immutable input identity from the selected profile, source-backed valuation input, provenance, and bounded session parameters. Only DCF-ready operating companies with source references, revenue, FCF margin, and shares can display numerical scenario math. If the selected row is blocked or excluded, the product shows the reason and withholds baseline, adjusted, sensitivity, and terminal-value figures.

Scenario values are temporary assumption tests. They are not source facts, saved forecasts, price targets, rankings, recommendations, or evidence that can unlock another lane.

## Source Freshness Timeline Contract

The timeline is a read-only same-profile view derived from the selected report payload. Each event preserves a deterministic identity, ticker, profile, lane, event type, timestamp kind, supplied timestamp, source, source reference when present, freshness state, and evidence note. Exact duplicate source events collapse by identity; cross-profile events never merge.

Effective, publication, retrieval, market-observation, forecast-cutoff, revision, and report-generation times are different facts. The product does not substitute one for another. An absent or invalid value remains a `missing timestamp` event, and publication, cutoff, or revision events appear only when the source payload explicitly provides them. The timeline never refreshes data, writes a report, changes readiness, or unlocks a blocked input.

## Research Comparison Contract

The comparison consumes only selected-profile selector rows plus profile-scoped, reviewer-authored Research Thesis Journal state. It preserves ticker selection order and explicit missing states. Journal catalysts and risks appear only when reviewed entries exist for that same profile and ticker; generated text, Change Monitor tasks, and cross-profile rows cannot populate them.

Readiness lanes remain independent, and candidate peer context cannot satisfy trusted-peer readiness. The view writes no data and produces no score, rank, winner, expected return, recommendation, allocation, or transaction instruction.
