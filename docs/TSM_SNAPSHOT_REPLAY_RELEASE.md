# TSM research snapshot replay

The research store now saves larger normalized contexts using lossless compression. Notes, saved comparisons and Monitor use the same snapshot IDs and original observation dates. The store checks issuer and profile scope, evidence shape, identity and checksum before returning either format.

## Measured result

The November 8, 2026 captured TSM observation produced a 758,318-byte normalized context. The original store rejected it at 524,288 bytes. The new stored file uses 91,378 bytes and expands to the original 758,950-byte snapshot envelope. In a disposable store, repeated save returned the same snapshot, full replay matched the source context, comparison reported unchanged, and the Monitor index retained the exact snapshot ID.

Reprocessing the same captured twelve-company sample with the original observation time for each company improved exact replay from 10/12 to 11/12. IBN remains held for missing usable financial evidence. These are same-source replay measurements.

Small snapshots still use plain JSON. Larger snapshots use a versioned zlib envelope under the existing 512 KiB file cap and a 1 MiB decoded cap. Decoding verifies one complete stream, the declared byte count and the original inner snapshot. Original limits on individual values, depth and node count still apply. Discover identifies which size bound produced a hold.

## Remaining TSM work

The captured context still shows annual Companyfacts pending, direct quarter and interim coverage withheld, and the scenario withheld. The next annual stage can start with the existing exact-filing parser. A November 11 source check verified FY2025 revenue, operating income, operating cash flow and PP&E purchases in native TWD in the April 16, 2026 Form 20-F. [Exact SEC filing](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/tsm-20251231.htm)

The October 15 earnings exhibit identifies the quarter ended September 30 and provides native TWD revenue and operating income. A later quarterly implementation needs to bind those fields to the stated duration and qualify cash-flow definitions separately. The November 10 filings describe board approval and October monthly sales. TWD financial statements, USD convenience translations and per-ADS earnings retain their own bases. [SEC earnings exhibit](https://www.sec.gov/Archives/edgar/data/1046179/000104617926000726/a3q26e_withguidancexfinal.htm) · [Board filing](https://www.sec.gov/Archives/edgar/data/1046179/000104617926000797/tsm-boardx202611xx.htm) · [Monthly sales filing](https://www.sec.gov/Archives/edgar/data/1046179/000104617926000796/tsm-revenue20261110.htm)

## Verification

- 327 affected automated tests passed, including legacy files, normalized numeric evidence, both capacity limits and malformed compressed streams.
- Two browser journeys passed at 1440×1000 and 390×844. They used constructed native-TWD observations, the production Notes and Monitor components, and a disposable store to verify the exact return and unchanged comparison.
- Six dashboard research routes rendered successfully. The public wording and staged-file checks passed.

All 89 protected files match baseline `703148203`. Ordered path and content digest manifest SHA-256 is `6dea65bec009270b132211724f426c1fdb557979a8903a5f5cc93b92d9edb373`. The private evidence directory contains measurements and checksums. Captured financial inputs remain in their existing private storage.

[Current roadmap](../ROADMAP.md) · [Goal and acceptance checks](goals/ONLINE_RESEARCH_NEXT_STAGES.md)
