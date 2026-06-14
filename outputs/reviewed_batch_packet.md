# Reviewed Batch Run Packet

Research-only: this packet plans data-readiness work. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.

- Batch ID: `RB-20260614T035812Z`
- Selected lane: `metrics`
- Lane scope: `metric_readiness_review`
- Ticker scope: `top 10`
- Freshness status: `current`
- Freshness note: Readiness artifacts are current relative to watched source files.
- Refresh command if blocked: `make readiness`

## Readiness Snapshot

- Pre-run snapshot command: `make readiness-snapshot`
- Refresh saved readiness reports before relying on final counts: `make readiness`
- Current operations view: `make readiness-ops-center`
- Current frontier view: `make coverage-frontier TOP_N=10`

## Proposed Actions

### Metric Readiness Review: A

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AACB

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AACI

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AACO

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAL

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAME

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAOI

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAON

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAPG

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

### Metric Readiness Review: AAPL

- Workflow mode: `read_only_review`
- Source/freshness context: Requires trusted local prices, benchmark rows, fundamentals, market context, and peer inputs depending on blocker family. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL`
- Capped execution command: `make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Validate: `not_applicable_read_only_metric_review`
- Preview: `review metric blocker families, source gates, and row-level missing inputs before any data work`
- Apply gate: `not_applicable; metrics remain blocked until the underlying trusted source rows are reviewed through their lane`
- Post-run verification: `make readiness && make metric-readiness-board TOP_N=10 TICKERS=A,AACB,AACI,AACO,AAL,AAME,AAOI,AAON,AAPG,AAPL BENCHMARKS=SPY,QQQ`
- Readiness comparison: `make reviewed-batch-compare LANE=metrics BATCH_ID=RB-20260614T035812Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260614T035812Z" LANE="metric_readiness_review" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: metric-readiness console output; Data Health Metrics lane; optional reviewed_batch_packet.csv
- Rollback checklist: No local data is mutated by metric-readiness review. If follow-up source rows are changed in another lane, use that lane's rollback path.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files; the missing metric inputs have not been traced to prices, fundamentals, market cap, or peer-input proof

Lane proof instructions:
- Record the SPY/QQQ blocker-family summary before opening row-level proof.
- Map each blocked metric to its source lane: prices, fundamentals, market context, or peer inputs.
- Do not apply rows from the metrics packet; use the underlying reviewed lane packet when source proof exists.
- After any reviewed source-lane change, rerun make readiness and make metric-readiness-board before describing the metric as ready.

## Review Checklist

- Confirm readiness artifacts are current or run `make readiness`.
- Confirm the dry run matches the intended lane and capped scope.
- Confirm source files are trusted and local.
- For mutating workflows, run validate -> preview -> apply only after review.
- Check rejected-row reports before treating any lane as supported.
- Run post-run readiness verification and record supported, still_blocked, skipped, or excluded honestly.
- Record changed readiness counts and changed tickers only when the before/after proof supports them.
- Classify generated CSV/JSON artifacts as kept evidence or excluded local churn before staging.

## Proof Row Template

Ledger path suggestion: `data/reviewed_batch_proofs.csv` or the existing reviewed data proof ledger.
Final outcome options: supported, still_blocked, skipped, excluded.

- batch_id:
- lane:
- scope:
- tickers:
- pre_run_readiness_snapshot:
- command_run:
- validation_result:
- preview_result:
- apply_result:
- post_run_readiness_snapshot:
- changed_readiness_counts:
- changed_tickers:
- reviewer:
- review_date:
- source_files:
- generated_artifacts_reviewed:
- final_outcome:
- notes:

CSV template row:

`RB-20260614T035812Z,metric_readiness_review,metrics,top 10,make readiness-snapshot or saved readiness counts before command,<copy exact command>,<pass/fail/not_applicable>,<reviewed rows / no unexpected rows / not_applicable>,<not_run/applied/skipped>,make readiness && lane proof command,<before -> after counts, or none>,<tickers changed, or none>,<name>,<YYYY-MM-DD>,<trusted local source files reviewed>,<CSV/JSON artifacts kept/excluded>,supported|still_blocked|skipped|excluded,<source proof, blockers, rollback notes>`

## Guardrails

- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.
- Do not treat a high unlock-impact lane as a security ranking.
- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.
- Do not proceed when source proof, validation, preview, rejected-row checks, or rollback path is unclear.
