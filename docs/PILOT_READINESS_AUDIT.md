# Pilot Readiness Audit

## Workbench and Monitor private pilot

Reviewed November 18, 2026.

The November 20 local rehearsal is recorded below. Its repeatable entry point is `make private-pilot-rehearsal`. The [rehearsal plan](superpowers/plans/2026-11-20-private-pilot-rehearsal.md) defines the fixed profile, provider failure and rollback checks.

**The operated private pilot stays on hold.** Workbench and Monitor support a local research rehearsal using disposable profiles and constructed evidence. The inspected repository and GitHub deployment records show a public static Pages site. The readiness classifier's `local_ready` result describes local guidance and controls. [Private beta architecture](PRIVATE_BETA_ARCHITECTURE.md) · [Public Pages](https://yuzej21.github.io/Stock-Analysis/)

| Gate | Local evidence | Open before an operated pilot |
| --- | --- | --- |
| Source rights and retention | The registry lists six approved SEC Companyfacts fields, with derived-data redistribution and attribution conditions. Exact filing and listing evidence use their own personal-inspection status. Yahoo price and peer context remain research-only. Commercial mode blocks the personal online paths at the entry points. | Record permission for the exact pilot workflow, including provider access, display to another user, stored research snapshots, retention and deletion, and permitted outputs. Release only approved fields and disable unsupported lanes. |
| Workspace isolation | Protected Workbench and Monitor processes now bind trusted Streamlit identity to a server-configured workspace. Reads, writes and stale confirmations recheck membership and role. Snapshots, notes, SEC receipts and dispositions retain their issuer and ticker scopes. | Configure a real identity provider and verify access denial, revocation and audit persistence with two test accounts against the intended storage and host. |
| Provider recovery | Listing refresh can reuse recent matching session receipts after qualifying transport failures. It retains the original dates and revalidates market and financial evidence independently. Explicit failures withdraw old answers and repeat failures are bounded. Saved evidence can reopen without providers. | Verify timeouts, stale data, outage recovery, alerts and operating ownership on the intended host. Enforce the SEC request budget across processes and users and keep unsupported answers withheld during the rehearsal. [SEC rate policy](https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits) |
| Rollback | Atomic snapshot publication and interrupted-save recovery have local tests. The November 20 rehearsal reopens synthetic snapshots with the previous reader and switches the local application to its previous revision and back while preserving the disposable store. | Verify filesystem publication primitives on the intended host. Keep a verified previous application and matching configuration available. Rehearse restoration there and verify user separation, saved-pair access, audit continuity and health after the switch. Record who can carry it out. |
| Independent workflow evidence | Automated checks exercise the product and verify stated states. Independent researcher evidence remains `awaiting_external_review`. | Record one independently completed Workbench-to-Monitor workflow before reporting the private pilot ready. |

### November 20 local rehearsal

The rehearsal uses two explicitly configured local profiles sharing a disposable filesystem. Each profile holds distinct synthetic notes and saved observations for the same ticker and issuer. Workbench and Monitor reopened the selected profile's exact saved evidence and rejected another profile's snapshot. Desktop at 1440×1000 and phone at 390×844 verified both return actions, cold reload, foreign Workbench and Monitor routes, and visible source-rights gaps with provider transport blocked.

Provider recovery uses a constructed annual P/E packet through the production collector. A simulated timeout withdraws the old comparison, passive reads retain the hold, and an explicit retry restores the accepted values from the same inputs. The saved historical snapshot remains byte-identical through the incident. Existing abrupt-write and concurrent-save cases remain part of the command.

Reader compatibility runs the saved-data module from `3682b320cf27a2c5b7af84c6d4566e808057a7e5` in a fresh process with the current supporting validators, then returns to the current reader. It verifies four exact synthetic records, unchanged comparisons, note changes, cross-profile reads and rejection of mismatched save scopes. The separate local application switch uses `c1cb630854bc2e21831d04effef248bf2a640981`, whose Workbench implementation differs from the current application. The same disposable snapshot store is used before the switch, during previous-version replay and after returning to the current version.

The source registry still grants six Companyfacts fields their recorded scope and keeps Yahoo prices and company context commercially unverified. Annual diluted EPS, exact archives, listing inputs, retained snapshots, and delivery to another user require their own applicable source decisions. SEC developer guidance was checked on November 20 and still specifies a maximum of ten requests per second across machines for each user. Yahoo's official terms page returned a fetch error during this review, so its current terms could not be rechecked. The registry's held decision continues to apply. [Source registry](../config/source_rights.yml) · [SEC developer guidance](https://www.sec.gov/about/developer-resources) · [Yahoo terms](https://legal.yahoo.com/ca/en/yahoo/terms/otos/)

Hosted authentication, server-side access enforcement, durable audit storage, retention and deletion, shared provider-rate controls, operating ownership and independent researcher completion remain open. These local tests provide evidence for the local rehearsal scope. The operated private pilot stays on hold.

`make private-pilot-rehearsal` passed **218 tests in 213.25 seconds**, including five browser cases and the existing snapshot, notes, authorization, provider and readiness checks. There were zero skips. The protected-artifact guard passed. Screenshots and JSON proof files stayed in temporary test directories. One existing dateutil deprecation warning was reported. The two-profile browser and provider-recovery cases ran on desktop and phone. The application rollback browser case ran on desktop. The application, source registry and canonical data have no changes in this stage.

### Runtime authorization follow-up

The next stage connected the existing role policy to Workbench and Monitor and their private storage entry points. Protected mode obtains identity only from Streamlit's authenticated user, checks issuer, audience and token expiry, and reloads the server registry at each operation. Cross-workspace profiles and paths are rejected before filesystem access. Viewer writes and revoked confirmations are blocked. Protected data roots are server-bound, and client parameters cannot select identity or role. The normal local personal workflow retains its existing entry points.

These checks use synthetic users and memberships. Real identity-provider setup and verification in the intended host remain open. Durable audit and retention, authenticated export delivery, provider permissions and operated recovery remain separate gates. Protected-mode exports are held pending an authorized delivery endpoint. [Runtime configuration](WORKSPACE_AUTHORIZATION.md)

`make workspace-authorization-check` passed **561 tests in 128.47 seconds** with zero skips under the protected-artifact guard. The run used the declared Streamlit 1.62.0 and Playwright 1.62.0 runtime with the optional Authlib dependency installed. Desktop at 1440×1000 and phone at 390×844 verified editor writes, viewer restrictions, both saved-evidence return paths, foreign routes, forged client parameters, a stale confirmation after downgrade, and existing and cold Monitor routes after revocation. Direct storage tests also downgraded membership while writers waited for a lock or scanned history, verifying authorization again at mutation. All six personal research routes rendered successfully. Ten public-document checks passed separately. One existing dateutil warning was reported.

### Durable workspace audit follow-up

Protected Workbench, Monitor and private-store authorization guards now require a separate private SQLite audit sink. Allowed read/append/update decisions and policy denials are committed before access proceeds. Invalid identity, invalid configuration, wrong-profile/destination and unsupported-route denials are included. Events use fixed versioned fields and pseudonymous principal/workspace hashes; raw claims, tokens, research text, issuer/ticker IDs and paths are excluded. UI capability probes do not count as write attempts, and an allowed event does not claim that a later write completed.

The independent sink permits a minimal denial record even if the membership registry cannot be loaded. If the audit sink itself cannot be used, protected access stops; only a generic server diagnostic is emitted. The local backend rejects unsafe permissions, symlinks, corrupt or incompatible databases and bounded lock contention. There is no application mutation or public read endpoint for audit events. A same-user administrator can replace the local file, so hosted tamper resistance and off-host backup remain open. [Configuration and event contract](WORKSPACE_AUTHORIZATION.md#durable-access-decisions)

Desktop at 1440×1000 and phone at 390×844 verified the exact Workbench–Monitor return and cold replay, one authorized note revision, downgrade/revocation and foreign-workspace denials. Removing the actual audit directory blocked both private routes and an already-rendered save. Restoring it preserved the retained decisions and research bytes. The browser cases made zero provider requests and continued to show the source-rights hold. They use disposable stores and synthetic identities, not a real identity-provider or host verification.

The source registry and canonical research inputs are unchanged. The operated pilot remains on hold for actual identity/host verification, provider permission, audit backup/continuity and retention/deletion, authorized exports, operational ownership and independent researcher evidence.

The expanded `make workspace-authorization-check` passed **580 tests in 171.66 seconds**, zero skips, under the protected-artifact guard on Streamlit 1.62.0 and Playwright 1.62.0 with the workspace authentication dependency installed. One existing dateutil warning was reported. All six personal research routes rendered successfully. The 97 public-document checks and public wording scan passed separately. Audit tests include sixteen committed events from four concurrent processes, append-only enforcement, schema and metadata rejection, bounded contention, configuration/authentication/role/scope denials and prevented private snapshot I/O without auditing. The unchanged source registry has SHA-256 `6fe137aaec84fc63ae9a3a43d1fb2841caca10744288fcddc24c57f060ac59b1`. Screenshots, synthetic registries and audit databases remain in temporary test directories outside Git.

### Source decisions for the pilot

- **SEC Companyfacts and EDGAR archives.** The SEC permits access and reuse of public filings and publishes fair-access requirements. The application registry covers normalized Companyfacts revenue, shares outstanding, filing dates, operating income, operating cash flow and capital expenditures. Archive receipts, other concepts and live delivery to pilot users need a scope decision under the application's release policy. [SEC reuse guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions) · [SEC automated access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Application source registry](../config/source_rights.yml)
- **Yahoo Finance.** Workbench uses price and company context and can preserve normalized price and peer observations with a research snapshot. The registry restricts that path to local research and leaves redistribution unapproved. Yahoo's published terms require express prior permission for automated collection. The pilot needs a recorded permission decision for the provider path, including delivery and storage. [Yahoo terms](https://legal.yahoo.com/ca/en/yahoo/terms/otos/) · [Workbench valuation method](ONLINE_PEER_VALUATION.md)
- **Listing metadata.** Nasdaq Trader documents both directory feeds and describes a reuse exception for specified categories of its own events data. The combined listing input also uses other-exchange records and SEC issuer mappings. Review the intended use of each exact input before sharing the normalized inventory or relying on it in a hosted workflow. [Directory definitions](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs) · [Nasdaq data notice](https://www.nasdaqtrader.com/trader.aspx?id=symbollookup)

### Automated verification

The November 18 checks used application revision [`3ed65199`](https://github.com/YuzeJ21/Stock-Analysis/commit/3ed65199da2081bba12d5ba8604e0d3706f9bdba). The 556 targeted tests passed. The commercial-beta contract checks and all six research-route renders passed locally. The contract continued to report hosted authentication and storage as account-required, and rollback, incident response and owner capacity as operations-required.

Eight browser cases passed across desktop and phone using two constructed profiles in a shared disposable store. Each profile reopened its own snapshot from Monitor and preserved it on reload. The other profile's snapshot stayed unavailable in Workbench. Replay preserved the saved bytes and made zero provider requests. Hosted authentication and authorization require verification in the intended service.

Public documentation checks passed 94 of 97 assertions, up from 93 at the starting revision. The three pre-existing failures cover two roadmap length assertions and a LinkedIn brief wording assertion.

The provider rehearsal replayed retained DUK observations with a simulated outage and zero upstream requests. The failed refresh replaced the previous peer comparison with a hold. Explicit retry restored the comparison from the same evidence. Passive reads made zero additional provider calls. The local rollback rehearsal used the snapshot reader from [`3682b320`](https://github.com/YuzeJ21/Stock-Analysis/commit/3682b320cf27a2c5b7af84c6d4566e808057a7e5) before returning to the current reader. The rehearsal exercised saved-data compatibility and exposed the interrupted-write gap above. Hosted application, storage and operations recovery remain open.

### Snapshot save and replay recovery

Snapshot writes now stage a private file outside the history index, check the complete write, and synchronize it before publishing the immutable ID. Saves in one profile, issuer and ticker scope serialize the capacity check and publication. Duplicate inputs keep the existing record. A stopped writer can leave one pending file in its scope. The next save clears that file while the earlier history remains available.

The local save path requires filesystem locking, same-volume hard links, and file and directory synchronization. Existing snapshot IDs, formats, and replay paths still apply. Damaged published files continue to surface a verification error.

The 705 targeted tests included a thrown write error, a short write, abrupt process exit, duplicate retries, concurrent saves and the scope capacity limit. All six research routes rendered, and the package built. Eight browser checks across two constructed profiles and both screen sizes covered filing research, saved comparisons, exact Monitor replay, and the other profile's snapshot remaining unavailable. Separate desktop and phone checks reopened the unchanged DUK pair. The previous and current readers both reopened all four constructed snapshots with matching bytes. The browser and rollback rehearsals used zero upstream provider requests.

This local change advances the save and recovery gate. The intended hosted environment, authenticated workspace controls, provider permission and independent researcher evidence still need verification before an operated pilot.

## Historical demo sharing audit

Date: 2026-06-22

Last repo-truth refresh: 2026-07-09

Historical snapshot notice: this dated audit is superseded for current lane truth. Run `make readiness-ops-center` for current selected-profile readiness; `make status-check TOP_N=5` only describes a saved generated snapshot and can be stale.

Verdict: ready for a controlled pilot with manual gates.

This audit reviews the current repository as a pilot package, not as a broad public launch. The product is research-only and readiness-first: missing trusted data must remain visible as `blocked`, `partial`, `still_blocked`, `skipped`, or `excluded` rather than being filled with placeholder analysis.

### Stage at the time

Current stage: controlled GitHub/LinkedIn pilot-share package with manual gates.

The repository is past prototype/internal-alpha for the core workflow because it has a working Streamlit dashboard, single-stock reports, readiness gates, proof ledgers, screenshot evidence, and release checks. It is ready to share as a controlled GitHub/LinkedIn portfolio demo after `make public-check` passes, but it is not public launch-ready as a hosted data product. Hosted demo remains external-account-required until a public URL is deployed and verified. Provider activation remains external-key-required for FMP, Alpha Vantage, and Finnhub. Broad fundamentals, source-backed peers, earnings, analyst estimates, and full valuation inputs remain intentionally incomplete for much of the broad universe. Use `make readiness-ops-center` for current local counts before quoting them; saved generated snapshots are historical context only.

### Stage ratings

| Category | Rating | Evidence |
| --- | --- | --- |
| Data ingestion and coverage | Yellow | Price coverage and local import workflows exist, but broad fundamentals, peer mappings, earnings, and estimates remain source-review gated. Run `make readiness-ops-center` before quoting current ticker or lane counts; use `make status-check TOP_N=5` only for saved generated-snapshot context that can be stale. |
| Evidence ledger / provenance | Green | `make pilot-readiness-check TOP_N=10` reports the reviewed batch proof ledger and latest durable outcome. |
| Readiness states | Green | `make readiness-ops-center` separates ready, partial, blocked, and excluded states for price, DCF, share count, peers, optional lanes, and not-applicable rows. |
| Stale data detection | Green | `make pilot-readiness-check TOP_N=10` reports readiness artifacts are current relative to watched source files. |
| Financial-model gating and research-only safety | Green | DCF, peer valuation, earnings, and estimates stay withheld until trusted source rows pass validation, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof recording. |
| UI/product-page clarity | Green | Public workflow is guided through Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History, with advanced/operator details kept secondary; rerun live desktop/mobile review after UI changes. |
| Operator workflow | Green | Data Health, reviewed-batch packets, pilot readiness checks, proof queues, and commit/package handoffs exist and are copy-only. |
| Test coverage | Green | Full test suite passes locally inside `make public-check`; rerun the gate before sharing so the count is current. |
| CI/release checks | Green | `make public-check` passed end-to-end in the current environment, including public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks. |
| Documentation/onboarding | Green | README, LinkedIn brief, public demo walkthrough, hosted-demo deployment guide, source activation guide, release checklist, and pilot runbook all name the current share boundary. |
| Expansion roadmap | Yellow | Next expansion is source/provider dependent: configure at most one keyed provider, run one reviewed ticker smoke, and keep peer/optional lanes source-gated until trusted rows exist. |
| Maintainability | Yellow | Many dashboard helpers have been extracted and tested, but the Streamlit dashboard remains large and should continue to shrink after pilot-critical behavior stabilizes. |

### Pilot blockers

| ID | Blocker title | Severity | Pilot impact | Evidence from repo | Fixable by code/docs | Planned fix | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PB-001 | Dedicated pilot audit missing | High | Pilot reviewer lacks one concise verdict, rating table, blocker list, and command log. | No `docs/PILOT_READINESS_AUDIT.md` before this pass. | Yes | Create this audit with stage, ratings, blockers, evidence, and validation. | Fixed |
| PB-002 | Dedicated pilot runbook missing | High | A pilot operator must stitch setup and proof flow together from README, Operator Guide, Data Strategy, and Makefile. | No `docs/PILOT_RUNBOOK.md` before this pass. | Yes | Add a runbook covering setup, environment, data files, pilot workflow, refreshes, reports, states, provenance, checks, blocked stocks, limitations, and guardrails. | Fixed |
| PB-003 | Screenshot QA status stale in docs | Medium | Reviewer could think three real workflow screenshots are still pending even though `make browser-qa-evidence` reports ready. | `docs/DASHBOARD_QA.md` listed single-stock workflow, Data Health proof lane, and queue drawer routing as manual capture pending. | Yes | Update QA status table and matching regression expectation. | Fixed |
| PB-004 | Pilot entry/exit criteria hard to find | Medium | Roadmap is comprehensive but long; a pilot reviewer needs a short stage capsule. | `ROADMAP.md` has detailed milestones but no compact controlled-pilot criteria block near current state. | Yes | Add a controlled-pilot stage gate with entry criteria, exit criteria, next priorities, post-pilot work, risks, non-goals, and what not to build before pilot. | Fixed |
| PB-005 | Broad trusted data coverage incomplete | High | Many tickers still cannot support DCF, peer mapping, earnings, or analyst-estimate context. | `make readiness-ops-center` and `make data-coverage-proof-queues TOP_N=10` show current ready, partial, blocked, excluded, and still-blocked lane counts. | Partly source-dependent | Keep lanes visibly blocked; use `make provider-setup-checklist` when source-proof queues have no unreviewed executable company candidates, then run one reviewed source-proof slice only when new source-backed rows exist. | External/manual gate |
| PB-006 | Dashboard smoke can be environment-limited | Medium | Local socket restrictions can prevent in-session product-page smoke even when code is valid, but the current environment passed dashboard smoke through `make public-check`. | `make public-check` completed dashboard smoke successfully on 2026-07-09; rerun the gate immediately before sharing. | No, environment dependent | Run `make public-check` before public sharing; if dashboard smoke later fails because a local port cannot bind, verify `make dashboard-smoke` or `make dashboard` in a normal local shell. | Manual recheck gate |
| PB-007 | Optional provider access can be unavailable | Medium | SEC/Yahoo paths may fail in restricted sessions, so broad unattended data proof cannot be guaranteed. | Session preflight commands can return `session_sec_unavailable` or `session_yfinance_unavailable`. | No, network/provider dependent | Use local reviewed rows when present; otherwise mark ticker/lane `still_blocked`, `skipped`, or `excluded` and move to the next executable lane. | External/manual gate |
| PB-008 | Keyed free-tier providers not configured | Medium | More fundamentals/share-count fallback coverage cannot expand through FMP, Alpha Vantage, or Finnhub until local keys are configured. | `make session-source-preflight` reports FMP, Alpha Vantage, and Finnhub as `provider_key_missing`; `make project-status` says the best next proof is `make provider-setup-checklist`. | No, owner setup dependent | Keep real keys out of the repo; use the reviewed one-ticker smoke command before broad batches after setup. | External/manual gate |

### Command evidence

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short --branch --untracked-files=no` | Passed with generated churn only | Rerun the live status gate before sharing. Local reviewed commits may be ahead of GitHub until pushed; dirty generated CSV/report churn and broad stock-report artifacts stay excluded by default. |
| `git log -5 --oneline` | Passed | Latest commits include public UX review completion, compact single-stock report start, and the reviewed provider smoke review sequence. |
| `make diff-hygiene-summary` | Passed | Product/code/docs/test package was clean before this audit refresh; generated/sample report churn stays local unless individually reviewed evidence. |
| `make pilot-readiness-check TOP_N=10` | Passed with manual gates | Verdict: `pilot-ready with manual gates`; public-check remains the explicit share gate. |
| `make project-status` | Passed | Reports the current local price, fundamentals/input-ready, operating-company DCF-ready, peer-ready, locked-input, provider-gap, and next-proof state. Treat exact counts as snapshot values and rerun before quoting them. |
| `make session-source-preflight` | Passed | SEC, SEC submissions, yfinance import/stage, Stooq/Yahoo price ladder, and local fundamentals are available; FMP, Alpha Vantage, and Finnhub keys are missing; IBKR remains optional and disabled. |
| `make readiness-ops-center` | Passed | Lane board confirms partial/blocked/manual/excluded states, source-proof queue exhaustion, and provider setup as the next safe proof path. |
| `make hosted-demo-readiness` | Passed with external account gate | Repo-side hosting files are ready; no public hosted Streamlit URL is configured, so GitHub remains the public link until deployment is verified. |
| `make provider-setup-checklist` | Passed | Checklist names FMP as the first keyed free-tier provider to configure and shows the reviewed smoke -> validate -> preview -> stop-before-apply sequence. |
| `make universe-preview-summary` | Passed | Read-only universe metadata preview returned 50 capped rows, with one new SMH metadata candidate and one fallback source warning. Universe membership remains metadata only and does not unlock fundamentals, share count, DCF, peers, earnings, estimates, or recommendations. |
| `make public-check` | Passed | Public wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo checks passed. |
| `make public-wording-check` | Passed | Public wording scan passed; rerun before sharing because the scanned file count changes as docs and sample artifacts change. |
| `make browser-qa-evidence` | Passed | Verdict ready; all listed screenshot evidence is ready and screenshots remain product evidence only. |

### Product UI review

Reviewed product-facing surfaces:

- README visitor path.
- Streamlit entrypoint: `make dashboard`, public route `http://localhost:8501/?mode=public`.
- Data Health pilot evidence and proof workflow described by `make pilot-readiness-check`.
- Screenshot evidence inventory from `make browser-qa-evidence`.
- Single-stock Markdown report workflow through documented `make stock-report-md TICKER=<ticker>` commands.

Assessment:

- A pilot operator can see ready, partial, blocked, and excluded states before analysis.
- Evidence and proof routes are visible through Proof History, Data Health, reviewed batch proof rows, and pilot packets.
- Source freshness and stale readiness warnings are represented by pilot/readiness checks.
- Missing fields and coverage gaps are explicit.
- DCF and peer valuation gates remain separate and conservative.
- The research-only boundary is repeated in README, checks, runbooks, and release docs.
- The remaining UI risk is not correctness; it is review freshness after future changes. Re-run browser QA, dashboard smoke, and live desktop/mobile review after UI wording, layout, route, or screenshot changes.

### External and manual gates at the time

- Source coverage: trusted fundamentals, share counts, peer mappings, earnings, and analyst estimates require reviewed source rows. Code must not invent these.
- Provider setup: FMP, Alpha Vantage, and Finnhub are keyed free-tier fallbacks. Configure them only in local env files, run the reviewed one-ticker smoke command first, then validate and preview before applying any row.
- Hosted demo: no public hosted Streamlit URL is configured. Keep the GitHub repository link as the public share target until an external host/account is chosen and the hosted route passes the public gates.
- Public-check confirmation: run `make public-check` immediately before sharing so the wording, whitespace, full tests, dashboard smoke, browser QA evidence, and visitor-demo gates are fresh.
- License choice: the repository is public-reviewable under the controlled portfolio-demo license, but it should not be described as open source or reusable software unless the owner intentionally changes the license.

### Demo sharing verdict at the time

Ready for a controlled pilot with manual gates.

The current public share should focus on the GitHub/LinkedIn portfolio workflow: readiness-first product flow, real screenshots, local dashboard instructions, methodology, and visible source-proof boundaries. The next data-expansion move is not another broad proof loop; it is provider activation or reviewed source rows, one ticker at a time, through smoke, validate, preview, source-provenance review, rebuilt readiness, and proof history. The product should not be described as launch-ready, hosted, provider-backed, or full-universe analysis-ready until those external/source gates are actually satisfied.
