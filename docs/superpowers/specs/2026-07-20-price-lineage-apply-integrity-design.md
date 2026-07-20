# Price Lineage and Apply Integrity Design

## Problem

Price lineage currently treats any parseable `retrieved_at` value as complete.
Naive timestamps are silently interpreted as UTC, retrieval can precede the end
of a daily price observation or exceed the reviewer cutoff, and DCF lineage does
not evaluate the same temporal rule. Apply also previews the staged file and then
reads it a second time, so the frame written is not necessarily the frame that
passed preview. The final CSV write is direct rather than atomic.

## Temporal decision

Add one pure daily-price temporal validator shared by normalization, staged
validation/preview/apply, and DCF price-lineage review. For a daily observation
dated `D`, the earliest defensible availability is `D + 1 day 00:00:00 UTC`.
This is deliberately conservative and does not claim an exchange-specific close
or provider publication time.

When lineage declares `retrieved_at`, the timestamp must include an explicit UTC
offset. It must be at or after the daily availability boundary and at or before
an explicitly timezone-aware review cutoff. Missing retrieval remains a separate
lineage gap so research-only technical price rows can remain usable; a malformed,
naive, too-early, post-cutoff, or cutoff-unreviewed retrieval cannot pass temporal
lineage or Commercial Research apply.

Normalization does not invent timestamps. If the operator supplies
`retrieved_at`, normalization requires a review cutoff and refuses the complete
normalization before writing when any normalized observation violates the shared
temporal rule. Staged validation and preview expose independent temporal counts
and blockers without changing technical OHLCV validity. DCF review adds temporal
blockers independently from exact-source rights and registered `prices` scope.

## Single-frame apply

Build preview from one staged-file read and retain the validated immutable frame
inside the apply call. Apply must not re-read or re-normalize the staged CSV after
the commercial and temporal decision. Before mutation it computes the merge from
that frame, optionally writes the existing canonical backup, writes the complete
new CSV to a temporary file in the canonical directory, flushes and fsyncs it,
then replaces the canonical path atomically.

Known pre-write validation failures create neither a backup nor canonical file.
An atomic replace narrows partial-write risk on one filesystem, but this remains
a local file workflow: it is not a concurrent-writer lock, database transaction,
or guarantee that backup creation and canonical replacement succeed together.

## Verification

- Naive, malformed, too-early, post-cutoff, and missing-cutoff retrieval evidence
  fail the same shared temporal vocabulary across all four consumers.
- Explicit timezone offsets normalize to UTC deterministically.
- Missing retrieval remains technically usable in research mode but commercially
  blocked as incomplete lineage.
- Apply reads the staged file once and writes the exact validated frame.
- A staged-file change after that read cannot change the written rows.
- Known temporal, rights, scope, or technical failures preserve canonical bytes
  and create no backup.
- Successful writes use same-directory atomic replacement and preserve the
  existing no-delete merge behavior.
