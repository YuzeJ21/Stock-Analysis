# Self-service company research

The supported local application workflow is **search → Research company → trends and valuation → notes → saved research → Monitor → exact historical replay**. It fetches online observations at runtime. It requires neither an ongoing coding session nor manually prepared company CSVs.

## Use the application

1. Start the existing Streamlit application using the README instructions. Network access is required. Supply SEC request identification through `SEC_USER_AGENT` or the session-only **SEC access** control; no SEC API key is required.
2. Search a name or symbol in Discover and open the explicit company. **Research company** loads financials and dated prices and attempts the independently qualified annual P/E comparison. Source-specific refresh controls remain available.
3. Financial Trends includes **Business Trend** for compatible revenue growth, operating margins and cash generation. Exact annual, direct-quarter and cumulative periods remain distinct. Expand the definitions and source gaps.
4. In Valuation & Peers, **Scenario Lab** applies explicit hypothetical growth, FCFF margin, WACC, terminal growth and horizon to corroborated annual revenue. Changing a control requires recalculation. The result can be enterprise value alone; optional, documented user capital-structure assumptions support a hypothetical value per assumed share. This is not a target price or proof of value for a traded share class. Banks and other unsupported entity bases remain excluded.
5. Add genuine issuer-scoped research records in Research Notes using preview and confirmation. **Forward View and Decision Lab** combine observed trends, the current hypothetical scenario, user hypotheses and missing research tasks. They do not invent consensus, issuer guidance, reviewed catalysts or probabilities.
6. **Save research snapshot**, then reopen or compare it. Monitor's separate **Saved online research updates** queue returns to the exact company and snapshot. A replay remains historical; use explicit research refresh for a current observation.

The public GitHub Pages pages remain static, labelled examples. Running the full app locally does not require a coding session, but does require a running app server. No hosting or background polling service is introduced.

## What happens when a filing arrives

Every financial refresh checks the issuer's SEC submissions metadata as well as Companyfacts. The inventory retains the current version for each annual/quarterly reporting period, accession, form, document, filing date, acceptance time and observation receipt. It validates issuer identity and exact SEC paths. Acceptance time and official filing date remain separate; neither is invented from the other.

When the latest filing and its structured facts align, normal supported annual/quarterly periods feed the same tools without new company-specific code. A filing can arrive before Companyfacts has updated. That state is **facts pending**. An unresolved amendment remains a version gap. Prior observations stay available as dated history, while current financial/scenario/peer claims affected by the gap are withheld. An older-period amendment is evaluated for that period rather than automatically blocking an unrelated newer period. Comparative facts in a later known filing remain comparative history.

8-K and 6-K observations are research review triggers. Their event dates are not automatically financial quarter ends. Non-XBRL statements, issuer extensions, segment interpretation, source-specific tax bridges and unsupported units need separately verified definitions; detecting a new report does not manufacture those values.

## Calculation and source boundaries

- Existing annual, quarterly and foreign-financial validators feed a separate observed-data context. No canonical row, approved source field, saved model readiness or commercial eligibility is promoted.
- Growth requires matching definitions, currency and compatible periods. Missing or conflicting facts stay gaps. No Q4 subtraction, FX/ADS conversion or split-comparable EPS growth is inferred.
- Operating cash flow less positive PP&E spending requires identical periods, units and filing context. It is neither issuer-defined free cash flow nor FCFF. Scenario Lab uses an explicitly hypothetical FCFF margin instead.
- Online P/E retains same-day completed closes, annual diluted EPS, issuer/security identity, split checks, the 35-day fiscal window and at least three qualifying references. Industry references are not automatically reviewed economic peers. A new annual version or price date cannot silently preserve an old current verdict.
- Personal inspection rights remain personal inspection rights. Archive evidence and prices do not inherit Companyfacts field permissions. Commercial operation, redistribution, independent accessibility and market validation remain separate gates.

## Private persistence

Normalized context snapshots live under ignored `outputs/local/online-research-contexts/`, separated by profile, SEC CIK and ticker. Content IDs and envelope checksums protect immutable replay; bounded reads reject tampering, unsupported schemas, oversized files, raw archive bodies and unsafe paths. Exact identical contexts save idempotently. Comparison distinguishes fact/filing changes, transport metadata, scenario assumptions and notes.

These snapshots do not replace the existing four-field SEC receipt schema or the NEM/AMD/DUK exact-pair review dispositions. Monitor presents each lane separately. User-authored notes retain their existing append-only storage and review controls.

[Online source methods](ONLINE_COMPANY_RESEARCH.md) · [Peer method](ONLINE_PEER_VALUATION.md) · [Roadmap](../ROADMAP.md) · [Release evidence](SELF_SERVICE_RESEARCH_RELEASE.md)
