# Cross-security Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline with one final independent review. Steps use checkbox syntax.

**Goal:** Extend literal NEM common coverage and make TSM ADS/currency and XOM successor/annual evidence inspectable without invented eligibility.
**Architecture:** Exact source policies supplement the existing selected-security validator; a focused observation parser supplies structured source facts/notes to the existing company sections. Financial comparison gates remain independent.
**Tech Stack:** Existing Python, ElementTree, pytest, Streamlit and permitted SEC/vendor adapters; no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-02-cross-security-evidence-design.md

## Global Constraints

- Personal Research only; unchanged canonical financials/readiness/rights/5954candidate checkpoint and unrelated work. No purchases/credentials/PR/merge/deploy/publication; tested developer push authorized.
- Preserve exact URL/metadata/raw and reviewed-body SHA; <=24h freshness, original observations,32MiB/document and64MiB/scope. Existing numeric/XML guards remain unchanged.
- Preserve3references/12candidates/SIC/industry/fiscal/currency/completed-price/split/source-pause rules. No NEMCL alias assumption, USD convenience admission or predecessor EPS splice.

## Review Focus

- Resealed dimensionless source contexts must reject additional entity/period children, dimensions and wrong duration or class.
- TSM ordinary versus ADS context, native/convenience currency and IFRS versus US-GAAP cannot silently collapse.
- Source notes/continuations and unanchored paragraph references must identify actual complete bounded source locations without enabling arbitrary text inference.
- Newer filings, wrong identity and stale/missing source components must withdraw cached evidence without hidden transport.
- Actual source-backed financial changes must remain limited to explicit targets, leaving old controls and canonical data unchanged.

---

### Task 1: Exact dimensionless common-security scope

**Files:** Modify src/sec_selected_security.py, src/sec_selected_security_policies.py; create tests/test_cross_security_evidence.py and focused synthetic helpers if needed.
**Interfaces:** doc.cover_context={kind:'dimensionless',context_id:str,period_start:ISOdate}; absent means existing CommonStockMember path. Scope keeps alias_mappings_established=False and exposes unassigned associated codes separately.

- [ ] Write synthetic literal-common success and resealed wrong context/start/entity children/segment/scenario/dimensions/duplicate/common-listing negatives; run python3 -m pytest tests/test_cross_security_evidence.py -q; Expected RED for missing dimensionless path.
- [ ] Add minimal strict opt-in cover validation and exact NEM annual/latest-cover/basis policy from retained official receipts. Do not assign NEMCL.
- [ ] Run python3 -m pytest tests/test_cross_security_evidence.py tests/test_sec_selected_security.py tests/test_bank_peer_security.py tests/test_peer_security_collection.py -q; Expected GREEN.
- [ ] Commit and complete task with same command.

### Task 2: Structured ADS and successor inspection evidence

**Files:** Create src/sec_security_observations.py and tests/test_security_inspection_observations.py; modify src/sec_selected_security.py and source policy records.
**Interfaces:** inspect_observations(raw,*,cik,metadata,url,contracts) returns list of independently parsed numeric or source-note observations. Each contains kind/label/source_ref; numeric facts contain value,concept,namespace,period,entity,unit,class dimensions and fact/context/unit proof; note entries identify exact element/continuation-chain or paragraph ordinal/text digest. doc.inspection_observations holds exact reviewed contracts; validated scope.evidence_observations aggregates results. Inspection never creates original_eps or supported_common.

- [ ] Write synthetic direct ADS/nativeUSD convenience distinctions and resealed wrong class/namespace/entity/period/unit/qualified numeric/continuation cycle/missing source/paragraph digest negatives. Run python3 -m pytest tests/test_security_inspection_observations.py -q; Expected RED missing parser.
- [ ] Implement bounded observation parser and source-aware source contracts for exact TSM annual and XOM successor/quarter. Preserve held financial states and independent vendor conflicts; do not load predecessor financial values as current EPS.
- [ ] Run python3 -m pytest tests/test_security_inspection_observations.py tests/test_cross_security_evidence.py tests/test_sec_selected_security.py tests/test_online_peer_valuation.py -q; Expected GREEN.
- [ ] Commit and complete task with same command.

### Task 3: Company disclosure, coverage and tested delivery

**Files:** Modify src/online_peer_valuation_ui.py, tests/test_selected_security_ui.py, docs/ONLINE_PEER_VALUATION.md, docs/PEER_COVERAGE_METHOD.md, ROADMAP.md.
**Interfaces:** Existing company source/valuation presenters consume evidence_observations without fetching or accepting inspection facts as comparison inputs. Existing coverage audit replays source packets at original dates.

- [ ] Write presenter tests for ADS/native/convenience labels, numeric/context/unit/note references, XOM annual/vendor gates, NEMCL unassigned status and escaping. Run focused UI tests; Expected RED then GREEN after implementation.
- [ ] Fresh explicit production collection for NEM/TSM/XOM; real saved15 comparison and12 unchanged controls, actual dated source receipts and original-observation retention. Record operation/byte counts without claiming HTTP totals.
- [ ] Commit; dispatch one independent final review of b48ac6f1..HEAD. Fix Critical/Important once using RED/GREEN; ledger declined rulings/costs and deferred Minors.
- [ ] Final-head actual desktop1280x900/phone390x844 valuation/sources/coverage checks and real live query, image/DOM geometry. Stop only owned QA preview before full tests.
- [ ] Run task-done using env PYTEST_ADDOPTS='-vv --durations=15 -x' make test; Expected exit0 exact full suite. Verify wording/range hygiene/unchanged hashes, normal developer push with remote/API equality and unchanged main; hostedCI separate. Preserve private evidence/heldPRdraft, restore real preview, archive and delete only own scratch.
