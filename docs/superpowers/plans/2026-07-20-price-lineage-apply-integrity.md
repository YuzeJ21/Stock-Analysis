# Price Lineage and Apply Integrity Implementation Plan

1. Add failing unit tests for timezone awareness, observation availability,
   review cutoff, normalized UTC output, and stable blocker vocabulary.
2. Add failing normalization, staged validation/preview, DCF-lineage, and
   commercial-apply integration tests using the same temporal cases.
3. Add a shared daily-price temporal review module and route every consumer
   through it without changing source-rights or field-scope decisions.
4. Make explicit normalization retrieval require the exact review cutoff and
   fail before writing on invalid temporal evidence.
5. Refactor staged preview/apply so apply carries the one validated frame rather
   than reading the staged CSV twice.
6. Replace direct canonical writes with a flushed, fsynced, same-directory
   temporary file and atomic replace; retain the optional reviewed backup.
7. Update Make targets, methodology, provenance, operator docs, ROADMAP, and the
   continuation contract without running readiness or writing repository data.
8. Run focused/full tests and all required product, commercial, pilot, PR-range,
   whitespace, generated-artifact, and staged-hygiene checks; commit, push,
   update draft PR #113, and verify hosted CI on the exact head.
