# Bank Peer Document Sets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, with one whole-stage review. Steps use checkbox syntax.

**Goal:** Qualify source-supported BAC/WFC/C common-share evidence so JPM can reach a same-definition reference comparison without relaxing financial gates.
**Architecture:** Optional exact same-accession linked document sets supplement existing source policies. Parsed resource union retains individual source receipts; existing numeric logic and presenters consume source-aware proof.
**Tech Stack:** Existing Python/ElementTree/pytest/Streamlit/SEC adapters; no dependencies.
**Spec:** docs/superpowers/specs/2026-11-01-bank-peer-document-sets-design.md

## Global Constraints

- Personal Research only; unchanged canonical financials/readiness/rights/5954candidate checkpoint and unrelated work. No paid sources, credentials, PR/merge/deploy/publication.
- At most1companion per annual/cover,2docs/role,4docs/policy,32MiB/doc,64MiB/scope; exact safe same-accession filename, literal parent href, no redirects/external XML, raw+reviewed-body SHA, <=24h freshness/nonfuture.
- Compatible namespace-prefix maps, globally unique IDs, explicit WFC equal-duplicate groups only. Direct entity annual diluted USD/shares EPS; original numeric algorithm and Companyfacts agreement. Preserve3references/12candidates/SIC/industry/fiscal/currency/price/split/source-pause rules.
- Separate listing/security/issuer/domicile/activity/financial/point-in-time eligibility. Raw aliases unassigned; BNY6022/BK/current-symbol gap held. No source or economic-peer approval.

## Review Focus

- Cross-accession or undeclared links/resources cannot enter an exact set, including cached resealing.
- Prefix or ID collisions, target/nil/continued facts and conflicting duplicate exchange facts must hold.
- Actual source refs must identify the supplying exhibit, context and unit, not a fabricated primary fact.
- Old single-document/AMD inputs remain unchanged; new required companion loss must withdraw bank comparison.
- Supported bank identity alone cannot override SIC/price/split/period/currency/minimum-reference gates or create hidden fetches.

---

### Task 1: Exact linked-set validation and source-aware parsing

**Files:** Create src/sec_security_document_set.py, tests/document_set_fixtures.py and tests/test_sec_security_document_set.py; modify src/sec_selected_security.py, src/annual_amendment_evidence.py internal EPS helper only, related tests.
**Interfaces:** Optional doc.companion={primaryDocument,href,document_type,sha256,body_sha256,normalization}; scope receipt role.companion mirrors raw receipt. bind_document_set(raw,companion_raw,*,url,companion_url,href) returns parsed root/namespaces/source-ref map. Existing _cover and _original_eps accept optional validated parsed input; existing defaults unchanged. Companion-specific source interpretation is policy-only; collector at most one companion per role and total64MiB.

- [ ] Write synthetic cross-document cover/EPS and actual-reference success cases; missing/changed/mixed accession/link/source, duplicated ID/prefix/target/unit/period and exact duplicate allowlist negatives; same source reread/no transport and old single-document behavior.
- [ ] Run python3 -m pytest tests/test_sec_security_document_set.py -q; Expected missing-feature RED.
- [ ] Implement bounded set binding, fetch/read validation and exact duplicate resolution. No real financial values in fixtures/production.
- [ ] Run python3 -m pytest tests/test_sec_security_document_set.py tests/test_sec_selected_security.py tests/test_annual_amendment_evidence.py tests/test_peer_security_collection.py -q; Expected GREEN.
- [ ] Commit and complete task with that command.

### Task 2: Bank source policies and protected comparison gates

**Files:** Create src/sec_bank_security_policies.py and tests/test_bank_peer_security.py; modify src/sec_selected_security_policies.py imports and necessary source integration tests.
**Interfaces:** BAC/WFC/C exact policy records consumed through Task1 companion/duplicate contract; every source/body/factID from retained official receipts. No EPS constants. Current profile/issuer symbol sets remain required.

- [ ] Write synthetic three-qualified-bank integration cases and mutated companion/Companyfacts/date/SIC/split/price/issuer/reference-count negatives. Policy-backed exact source test reads metadata only, while synthetic integration proves behavior independently.
- [ ] Run python3 -m pytest tests/test_bank_peer_security.py -q; Expected missing-bank RED.
- [ ] Add reviewed policies; privately replay actual annual/current cover+companions, compare direct EPS to the same accession Companyfacts; record blockers, no canonical writes.
- [ ] Run python3 -m pytest tests/test_bank_peer_security.py tests/test_sec_security_document_set.py tests/test_online_peer_valuation.py tests/test_online_peer_sources.py tests/test_online_peer_sec_history.py -q; Expected GREEN.
- [ ] Commit and complete task with same command.

### Task 3: Source disclosure, real coverage and exact-head delivery

**Files:** Modify src/online_peer_valuation_ui.py, tests/test_selected_security_ui.py, docs/ONLINE_PEER_VALUATION.md, docs/PEER_COVERAGE_METHOD.md, ROADMAP.md.
**Interfaces:** Flat source documents retain primary/companion roles and parent href, actual source-aware selected-common/EPS/basis refs. Existing valuation/sources/coverage presenters consume the same read-only packet.

- [ ] Write presenter tests for primary/EX13/EX99roles, real fact/context/unit references, escaping and accepted-bank proof without changing held BNY state; run focused tests; Expected RED then GREEN after presentation.
- [ ] Explicit production refresh JPM and3new bank subjects; compare actual prior JPM/15sample and revalidate14original controls, preserve original dates. Record operation/source-byte provenance and failures; no all-market claim.
- [ ] Commit; one fresh independent whole-stage review f3c9base..HEAD; reproduce/fix Important/Critical once RED/GREEN, ledger all declined rulings/costs and deferred Minors.
- [ ] Final-head browser JPM/BAC/WFC/C valuation/sources +sample desktop1280x900/phone390x844, labelled real source replay and actual production query. Verify actual image/DOM dimensions. Stop only owned previews.
- [ ] Complete task using env PYTEST_ADDOPTS='-vv --durations=15 -x' make test; Expected exit0 exact results. Verify56file wording/range hygiene/unchanged hashes, normal tested-head developer push and API equality; main unchanged/CI separate. Restore real preview, private evidence packet/heldPRdraft, archive and remove only own scratch.
