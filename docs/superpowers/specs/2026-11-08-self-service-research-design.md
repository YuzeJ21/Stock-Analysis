# Self-service online company research

## Intended outcome

An unregistered company selected from online search can run the real research workflow without a Codex session, a prepared company CSV, or a company-specific code change for a normal structured annual/quarterly filing. One explicit **Research company** action collects online observations. Business Trend, observed peer read-through, Scenario Lab, Forward View, catalysts/review triggers and Decision Lab use that same company context. Existing saved tools remain available separately.

The user has authorized implementation, automated/desktop/phone testing and GitHub synchronization. Reuse the current isolated worktree, Python/Streamlit and free existing sources. Do not add an AI provider, credentials, paid data, hosting or commercial rights. Preserve canonical data, historical tools and existing receipt/approval gates.

## Approach

Use observed-data adapters over the existing validators and calculation kernels. Do not cast online observations into reviewed canonical rows or fabricate saved DCF readiness. This joins the actual online pipeline to working calculations and user-authored research workflows. It does not claim automatic interpretation of every unstructured filing or an autonomous investment recommendation.

### Filing lifecycle

Every financial refresh independently fetches Companyfacts and one current SEC submissions receipt for the matched CIK. Reuse that receipt in the optional MRVL extension, avoiding a second MRVL profile request. A versioned normalized filing inventory keeps actual annual/quarterly report dates, form, accession, filing/acceptance time and document. Group revisions by reporting period; an unrelated amendment must not hold another period. Comparative facts may be reported in a later known filing. A new filing with missing/older-accession facts is explicitly pending or amendment-unresolved; older values remain historical, not current by substitution.

Ordinary section navigation/replay performs no transport. Explicit refresh replaces the attempted context atomically; failures remain independent. Freshly downloaded old facts are not proof of the newest filing. Store original response digests separately from normalized subsets. Revalidate cache identity/schema/freshness. New annual/quarterly structured periods flow through generic rules; fixed MRVL/AVGO and after-tax adapters remain optional, version-labelled supplements, never blockers for the generic path.

A generic annual standard-concept inspection (net income, diluted EPS, SBC, intangible amortization and disposal gain) can use exact current annual filing metadata, compatible durations and units. Missing/ambiguous concepts stay withheld; no alternate denominator or split assumption is invented. These are personal inspection fields, not new approved canonical fields.

### Shared context and calculations

`build_online_research_context(financial, prices, peers=None, association=None, *, ticker, profile_key, expected_cik=None, notes=None, scenario=None, as_of=None)` produces a JSON-safe `online-company-research-v1` observation with ticker/CIK, source and semantic revision IDs, dated source receipts, filing inventory/coverage, business trend, reported annual components, observed peer context, forward view, decision process and explicit gaps. A semantic source revision excludes retrieval timestamps/raw response digests but includes identity, periods, filing versions, values, price dates and qualified peer inputs. Source metadata changes remain separately observable. No saved-readiness or commercial eligibility is promoted.

- **Business Trend:** consume existing validated annual/direct-quarter/IFRS observations; use exact period dates rather than fabricated fiscal-quarter labels. Calculate compatible revenue YoY, sequential growth only with continuity, operating margin only for compatible definitions, and total operating cash flow less positive PP&E spending only for identical periods/currency/accession. Cumulative flows stay separate. The latter is neither issuer-defined FCF nor FCFF for DCF. Reported EPS is not automatically split-comparable growth.
- **Peer read-through:** use the existing online annual P/E result and its accepted/excluded references. These are observed industry-reference relationships, not trusted economic peers or forecast transmission. Preserve same-day completed close, annual diluted EPS, identity, 35-day windows and minimum three. A newly known annual filing or changed price date must not leave an old peer verdict presented as the current context.
- **Scenario Lab:** reuse `ScenarioParameters`, `DCFAssumptions` and `calculate_dcf` math with validated annual revenue and explicit user growth/FCFF-margin/WACC/terminal/horizon assumptions. Set direct FCF to `None`: CFO−capex is not FCFF, and a direct FCF input would bypass margin controls. Show hypothetical enterprise values without invented capital structure. Optional user-entered net debt and shares may yield clearly hypothetical values per assumed share; missing inputs remain gaps, and no comparison with current market price is inferred. Financial-sector/unsupported operating-company bases are excluded. All assumptions are visibly hypothetical, finite and bounded. Never call saved Scenario Lab with fabricated `dcf_ready=True`.
- **Forward View:** compose observed trends, eligible industry references, explicit scenario assumptions, user hypotheses and source gaps. Newly observed filings are research review triggers, not automatically reviewed catalysts. No invented guidance, consensus or earnings probabilities.
- **Decision Lab:** reuse genuine issuer-scoped journal/outcome records and existing research-process rules/types where compatible. Distinguish hypothetical assumptions documented from saved DCF eligibility. Missing thesis, contrary evidence, invalidation or review date is actionable research work, not a reason to require CSVs. No buy/sell decision or company grade.

Retain user controls by profile+ticker+CIK. A changed source revision invalidates displayed scenario results until rerun, while retaining draft assumptions. Different companies cannot share results. A source outage must not restore a previous successful verdict as current.

### Persistence and Monitor

Add a separate versioned private normalized research-context snapshot store, with immutable IDs, hashes, size/path limits, selected-profile/CIK binding and explicit replay dates. This does not change saved four-field SEC receipts or canonical CSVs. No raw archive body or public export is added. Compare financial/filing changes, source-metadata-only changes, assumptions and notes separately; identical semantic inputs remain unchanged.

Company Notes can save/inspect the current context and compare recent snapshots. Monitor shows these saved online research updates in a separate queue with an exact company/snapshot return link. It must not inflate the existing saved annual SEC review counts. Replay is historical; current research requires explicit refresh. User notes continue through existing forms and stores without preparing files.

### Presentation

Keep the five-section layout. The primary action becomes Research company; source-specific refresh remains under existing controls. Show latest filing/structured-data status near company context, with pending facts explicit. Keep first-screen conclusions concise. Put richer tool details in relevant expanders: Business Trend in Financial Trends, scenarios and industry read-through in Valuation & Peers, Forward View/Decision Lab/snapshots alongside Research Notes, inventory and provenance in Data Sources. Preserve saved tools as separately dated optional research.

If SEC request identification is missing, allow session-local configuration through the app; no credential or environment mutation. The app server still runs locally and the public Pages demo remains separate; document how to run the actual app without Codex.

## Acceptance evidence

- An online-only company absent from local data reaches useful trend analysis and a changing assumption scenario, notes/decision, saved comparison and Monitor through UI only.
- A later annual and quarter with matching structured facts updates tools without a new ticker/filing policy. Facts publication lag, amendments, identity/unit conflicts and provider outages retain precise gaps and invalidate stale results.
- Constructed HTTP tests prohibit external calls; mathematical tests prove controls affect real existing calculation kernels and do not promote readiness. Desktop/phone tests cover controls, snapshots, Monitor return, English, disclosure readability and overflow.
- Independently exercise real online companies from multiple industries, keeping source observations/screenshots outside Git. Preserve source rights and canonical hashes. Run affected regression and required route/health/public checks; expand verification for actual cross-cutting changes/failures. Review independently, commit and sync GitHub main without force.
