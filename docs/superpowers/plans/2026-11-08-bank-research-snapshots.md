# Bank research snapshots implementation plan

**Goal:** Save and replay complete bank research while retaining cover observations and validation boundaries.

**Architecture:** Versioned parsed cover observations at the validated producer, narrow normalized shape/relationship validation, existing immutable private store and Monitor workflow.

**Tech stack:** Existing Python/Streamlit/pytest/Playwright; no new dependencies, providers or credentials.

**Spec:** docs/superpowers/specs/2026-11-08-bank-research-snapshots-design.md.

## Tasks

- [x] Verify current checkout/main/roadmap and diagnose exact source-backed failure. Baseline focused tests: 69 passed in 1.15 seconds.
- [x] Implement a lossless versioned cover format and strict bounded shape checks; retain the raw/archive gate and source/financial rules.
- [x] Verify actual JPM/BAC/C evidence, two identical saves, unchanged comparison and exact historical replay in disposable stores, with every original cover value/source field accounted for.
- [x] Test all three bank workflows on desktop and phone, including Monitor return, visible holds and source-free replay.
- [x] Complete independent review, affected regression, route/rights/data/wording checks and update public method/roadmap/release evidence.
- [x] Commit and synchronize authorized GitHub main; verify remote blobs, clean checkout and local app health.

## Review focus

- Literal preferred/unassigned symbols may contain spaces, mixed case and slash notation; never convert them to provider aliases.
- Preserve C's companion/context references and WFC's explicit duplicate-exchange references.
- Replaying history must not require today's source dates or mutable policy definitions.
- Malformed normalized cover fields must not become a route for raw archives or unsupported approval claims.
- A successfully stored case must retain pending quarters, excluded references and bank FCFF exclusion.

## Execution evidence

- Final source-backed JPM/BAC/C saves and replay are exact; repeated saves preserve a single immutable identity and file bytes. Reversing only the versioned cover representation restores the original complete context apart from the two revision hashes. All three retain three references, C retains its pending quarter, and bank FCFF remains excluded.
- Final affected regression: 1,046 passed in 39.08 seconds. Exact-tree desktop/phone: two passed in 101.86 seconds. Six route renders and public wording checks passed. Review findings resolved in one bounded wave; no open P1/P2 in re-review.
- All 89 protected files remain unchanged. Private reduced evidence packet: outputs/local/releases/bank-research-snapshots-20261108. Original full sources and actual financial snapshots are not published.

- Implementation 5cf08bfe191e1ff2f01763b62595e06865d4b960 fast-forwarded GitHub main. Git remote and independent GitHub API matched; README/release remote blobs matched local bytes. Owned app restarted on port 8536 with health ok. This evidence-only follow-up does not alter runtime code or other checkouts.
