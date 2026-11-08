# Lossless bank peer evidence retention

## Intent and measured defect

JPM, BAC and C must retain the complete source evidence needed by the existing peer validator. This work follows the user's explicit authorization to implement, test and synchronize without human testing. Reuse the current Python/Streamlit architecture and isolated worktree; preserve canonical data, source rights and unrelated checkouts.

Baseline: 1f7e149df3587f18a0a8c6d1ea2caf6fe0a507d5. Fresh JPM collection reproduces a 74,100,090-byte classification-referenced peer packet. Selected-security source documents account for most of the size. Lossless zlib compression produces 5,274,077 bytes, approximately 7.03 MB after base64, leaving room in the existing 8 MiB retained-company limit. The original source packet was captured privately with its complete object digest and per-component measurements.

## Approaches

- Raising all packet/session limits would preserve evidence but increase retained memory without addressing duplication or compressibility.
- Removing source documents or narrowing source arrays would lose evidence required by the independent identity and earnings checks. This conflicts with the request.
- Use a versioned, bounded, lossless JSON storage envelope only when a company packet would otherwise exceed the retained limit. This is the implementation choice: preserve every original value, document body, date, source digest, permission and packet digest, then restore the original packet before existing validation.

## Boundaries and implementation

Keep the 8 MiB retained-company and 64 MiB retained-study limits unchanged. A new codec uses canonical JSON, zlib and strict base64. The decoded-peer limit is explicitly 128 MiB, sized above the measured complete 74.1 MB packet; this is a bounded transient reconstruction allowance, not a valuation or source-parser rule change. Reject oversized input/output, invalid encoding/schema/hash/length, noncanonical or duplicate-key/nonfinite JSON, corrupt/trailing/concatenated/truncated streams and inconsistent ticker/classification references.

The envelope preserves the classification content reference. Every reference consumer, including both pruning paths, must understand it so later classification refreshes cannot strand older packets. Restore the complete original classification and verify the original inner packet digest; never reseal altered source evidence. The unchanged peer validator then rechecks issuer/share identity, source documents, annual diluted EPS, completed same-day closes, fiscal-window compatibility, splits and the minimum three references.

Ordinary reads must make no source requests or snapshot writes. A damaged retained packet produces a precise peer hold without erasing independent financial/price results. Uncompressible or over-bound evidence retains an explicit capacity gap; it never becomes an old successful verdict. Legacy plain packets remain readable. Storage does not grant source rights, make bank FCFF models eligible or establish an economic-peer relationship.

## Verification and delivery

Prove exact restored object equality and original document bytes/digests on JPM, BAC and C. Compare old fallback versus new retention from the same full captured inputs before interpreting fresh changes. Preserve valid exclusions after the storage blocker is removed. Test corruption, stale sources, classification replacement/pruning, resource limits and failed retries. Use production source/valuation functions with constructed documents for desktop/phone journeys; keep real captures private. Finish with focused regression, six route renders, rights/data checks, independent review, updated roadmap/release evidence, local commits and authorized GitHub main synchronization.
