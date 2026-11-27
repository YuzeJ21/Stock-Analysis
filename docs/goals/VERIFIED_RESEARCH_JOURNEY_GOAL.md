# Next goal: a verified research journey

Act as product lead and release engineer for Stock Research Command Center.
Review the current GitHub revision, CI results and existing company-research
tests. Verify one complete supported journey: search for a company, explicitly
research it, trace financial evidence, understand valuation or its hold, save a
note and research context, open Monitor, and return to the exact historical
evidence. Verify provider-failure recovery and desktop/phone behavior.

Make that journey a separate, reproducible CI gate using the existing real
browser tests and calculation/storage code. Require the declared runtime,
browser and local-server capability. Missing, skipped, expected-failure,
uncollected or teardown-failed mandatory cases cannot pass. Keep the full
repository suite as a separate required check; a journey pass does not replace
it. Install the existing workspace dependency extra for protected-route checks.

Inspect completed CI failures, reproduce them where the environment permits,
and fix their causes without loosening source checks, deleting assertions,
silently skipping tests or inventing successful evidence. Preserve canonical
data, rights decisions and private records. Test with constructed sources and
disposable storage; do not contact people or live providers.

Record exact results and remaining blockers, obtain an independent code review,
and sync the review branch. Do not merge, deploy, purchase, change credentials
or claim real-user, hosted, source-rights or commercial validation. Exit with
the mandatory journey's actual CI result and an honest whole-suite status.
