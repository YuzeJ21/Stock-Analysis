# Consensus Ledger Integrity Design

## Problem

The prospective consensus collector validates proposed rows and preflights a
batch, but it does not validate every existing ledger row before status, preview,
or append. Static ledgers can therefore contain duplicate IDs, duplicate evidence
identities, forks, missing parents, reversed revisions, multiple roots, or cycles
without an explicit fail-closed decision. Recording also recomputes a preview at
each row's retrieval time instead of proving it is the exact batch, cutoff, and
ledger state that a reviewer previewed.

## Decision

Add one ledger-integrity validator used by status, preview, and append. It first
validates every row's schema and evidence contract with row numbers, then requires:

- globally unique snapshot IDs and semantic evidence identities;
- exactly one root per ticker/fiscal-period chain;
- every revision parent to exist in the same scope and appear earlier;
- at most one child per snapshot;
- strictly later snapshot and retrieval timestamps for every child; and
- an acyclic chain in which every row is reachable from the one root.

Proposed input remains a separate batch contract: rows are individually parsed,
then simulated in supplied order against a validated virtual ledger. A proposed
revision may supersede only the current leaf. Invalid existing evidence blocks the
entire preview or append before mutation.

## Preview receipt

Every batch preview normalizes the explicit UTC review cutoff and reports:

- a digest of the validated existing ledger;
- a digest of the exact ordered proposed input;
- a receipt derived from the schema version, cutoff, both digests, and commercial
  mode.

Recording requires the same cutoff and receipt. It reloads and revalidates the
ledger, recomputes all digests and decisions, and refuses mismatches before
creating a directory or opening the ledger for append. This binds review to the
exact immutable input and ledger state. It is not a multi-process lock or a
crash-safe database transaction; those remain separate operating concerns.

## Input boundary

Upstream `SOURCE_INPUT` and prospective `COLLECTION_INPUT` remain different
schemas. No command maps, normalizes, or writes one from the other. A receipt
proves only local collection review integrity; it does not prove source rights,
payload correctness, historical availability, nowcast readiness, or calibration.

## Verification

- Status, preview, and append reject row-numbered malformed existing rows.
- Duplicate IDs/identities, multiple roots, missing parents, forks, cycles,
  reversed order/timestamps, and non-leaf supersession fail closed.
- An invalid existing ledger or later proposed rejection preserves exact bytes.
- Record requires and verifies the preview cutoff and receipt.
- Changed input, cutoff, existing ledger, commercial mode, or receipt causes no
  filesystem mutation.
- Valid linear research and commercial chains still append in order.
