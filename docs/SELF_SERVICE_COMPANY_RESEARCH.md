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

## Optional cross-industry study

In **Discover → Coverage studies → Self-service**, use **Inspect next company** to inspect the next member of the fixed twelve-company sample. **Recheck company** explicitly replaces that company's observation; **Restart study** clears session progress without fetching sources. Changing tabs, selecting company evidence and ordinary rerenders revalidate retained observations without new requests.

The four declared groups contain AMD/NVDA/QCOM, JPM/BAC/C, DUK/SO/NEE and TSM/SAP/IBN. They are study groups, not a market, industry or domicile census. Ten capabilities have separate available, partial, held, excluded, failed or unattempted states. A bank's excluded FCFF scenario does not erase useful financial observations, and a dated close does not establish P/E eligibility. The exact-replay check uses disposable private storage without reading user notes or writing user evidence stores. [Capabilities, measured results and source boundaries](CROSS_INDUSTRY_SELF_SERVICE.md)

## What happens when a filing arrives

Every financial refresh checks the issuer's SEC submissions metadata as well as Companyfacts. The inventory retains the current version for each annual/quarterly reporting period, accession, form, document, filing date, acceptance time and observation receipt. It validates issuer identity and exact SEC paths. Acceptance time and official filing date remain separate; neither is invented from the other.

The shared filing catalog now handles large bank submissions catalogs by bounding the raw input and selecting relevant report forms before validating the reduced inventory. Event report dates remain separate from financial periods. Valid legacy document metadata is retained; an absent document stays an explicit gap, and missing current-document metadata cannot revive an older filing. Validated native-currency 6-K facts require an exact source accession, filing date and structured duration before a quarter or interim period can be corroborated. A 6-K event date alone remains insufficient, and known newer reporting periods retain current-data holds.

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

[Online source methods](ONLINE_COMPANY_RESEARCH.md) · [Capability study](CROSS_INDUSTRY_SELF_SERVICE.md) · [Peer method](ONLINE_PEER_VALUATION.md) · [Roadmap](../ROADMAP.md) · [Release evidence](SELF_SERVICE_RESEARCH_RELEASE.md)

Complete bank peer-source retention is now lossless and bounded, with the original documents restored before unchanged identity/EPS/price checks. JPM/BAC/C normalized cover evidence now saves/replays through the existing snapshot and Monitor workflow; bank operating-company DCF remains excluded. [Snapshot evidence](BANK_RESEARCH_SNAPSHOT_RELEASE.md). See [bank evidence and remaining gaps](BANK_PEER_EVIDENCE_RELEASE.md).
