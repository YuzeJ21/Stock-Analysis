# Reviewed Batch Run Packet

Research-only: this packet plans data-readiness work. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.

- Batch ID: `RB-20260613T012355Z`
- Selected lane: `peers`
- Lane scope: `peer_mapping, peer_valuation_inputs`
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

### Peer Mapping Proof: AAPL

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: MSFT

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: CRDO

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: QQQ

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: SMH

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: AACB

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: AACI

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: AACO

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: AAPG

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Mapping Proof: AARD

- Workflow mode: `reviewed_apply`
- Source/freshness context: Peer relationships must be source-backed or clearly labeled fallback context only. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AAPL

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: MSFT

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: CRDO

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: QQQ

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: SMH

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AACB

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AACI

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AACO

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AAPG

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

### Peer Valuation Inputs Proof: AARD

- Workflow mode: `preview_first_reviewed_apply`
- Source/freshness context: Mapped peers need trusted price, fundamentals, market-cap, or valuation inputs before peer valuation appears. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make peer-mapping-queue TOP_N=10`
- Capped execution command: `make focus-peers TICKER=AAPL or add reviewed peer rows/mapped-peer inputs`
- Validate: `make imports-validate`
- Preview: `make imports-preview`
- Apply gate: `make imports-apply only after source-backed peer rows or mapped-peer inputs are reviewed`
- Post-run verification: `make readiness && make peer-mapping-queue TOP_N=10 && make metric-readiness TICKERS=AAPL,MSFT,CRDO,QQQ,SMH,AACB,AACI,AACO,AAPG,AARD BENCHMARK=SPY`
- Expected artifacts: data/imports/peers.csv; data/peers.csv; data/reports/peer_readiness_report.csv; data/reports/peer_unlock_worklist.csv
- Rollback checklist: If peer rows are wrong, do not apply. If applied rows are wrong, restore data/peers.csv and any reviewed mapped-peer input files, then rerun readiness.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Peer/sub-lane proof instructions:
- Record peer_mapping_ready, peer_price_ready, peer_momentum_ready, peer_fundamentals_ready, peer_valuation_ready, and peer_valuation_comparison_ready before changes.
- Inspect the peer sub-lane with make peer-mapping-queue TOP_N=10 and make focus-peers TICKER=<ticker>.
- Treat sector or industry fallback as context only; it is not trusted peer mapping proof.
- After reviewed rows, rerun make readiness and make peer-mapping-queue before reading peer valuation dispersion.

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

`RB-20260613T012355Z,peer_mapping, peer_valuation_inputs,peers,top 10,make readiness-snapshot or saved readiness counts before command,<copy exact command>,<pass/fail/not_applicable>,<reviewed rows / no unexpected rows / not_applicable>,<not_run/applied/skipped>,make readiness && lane proof command,<before -> after counts, or none>,<tickers changed, or none>,<name>,<YYYY-MM-DD>,<trusted local source files reviewed>,<CSV/JSON artifacts kept/excluded>,supported|still_blocked|skipped|excluded,<source proof, blockers, rollback notes>`

## Guardrails

- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.
- Do not treat a high unlock-impact lane as a security ranking.
- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.
- Do not proceed when source proof, validation, preview, rejected-row checks, or rollback path is unclear.
