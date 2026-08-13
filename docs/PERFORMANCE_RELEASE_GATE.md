# Performance Release Gate

This is the reviewed local performance baseline for the guided public workflow. It is product performance evidence only, not data-freshness proof, source proof, investment advice, or evidence that a hosted URL exists.

## Fixed Baseline

| Field | Value |
| --- | --- |
| Application baseline commit | `fb86bd3edef72a1e35064ecc03ca8e7fb63ec34a` |
| Demo snapshot identity | `4f6f28d3a6b2df3c3c459fad325d75e2f2ee45dc398616e3c638ead91819549d` |
| Demo manifest | `data/demo/manifest.json` |
| Measurement date | `2026-07-14` |
| Environment | macOS arm64, local Google Chrome, headless Playwright, Streamlit demo profile |
| Viewports | `1280x720`, `390x844` |
| Evidence file | `/tmp/stock-command-center-public-performance.json` |

The tracked demo manifest supplies file hashes and row counts. Broad local CSV/report churn is not part of this baseline and stays excluded from staging.

## Gate Contract

| Experience point | Limit |
| --- | ---: |
| Warm visible-shell p90 | 1.0s |
| Cold visible-shell max | 1.0s |
| Warm first-useful p90 | 3.0s |
| Cold first-useful max | 3.0s |
| Warm full-settle p90 | 5.0s |
| Cold full settle | 10.0s |

Stock Selector, Single-Stock Report, and Data Health are critical routes. Home and Proof History remain regression-protected references.

## Reviewed Local Result

The release run used five warm runs and one server-cold run for every public route at both viewports: 60 recorded route samples, with zero route failures.

| Route | Viewport | Legacy combined shell p90 | Legacy combined first useful p90 | Warm full p90 | Cold full |
| --- | --- | ---: | ---: | ---: | ---: |
| Home | 1280x720 | 0.250s | 1.974s | 2.487s | 2.823s |
| Home | 390x844 | 0.247s | 1.987s | 2.206s | 2.843s |
| Stock Selector | 1280x720 | 0.248s | 1.866s | 2.307s | 2.795s |
| Stock Selector | 390x844 | 0.235s | 1.755s | 2.367s | 2.661s |
| Single-Stock Report | 1280x720 | 0.278s | 1.784s | 2.465s | 2.831s |
| Single-Stock Report | 390x844 | 0.279s | 1.784s | 2.358s | 2.819s |
| Data Health | 1280x720 | 0.277s | 1.969s | 2.463s | 3.022s |
| Data Health | 390x844 | 0.278s | 1.853s | 2.370s | 2.917s |
| Proof History | 1280x720 | 0.341s | 1.773s | 2.563s | 2.628s |
| Proof History | 390x844 | 0.245s | 1.876s | 2.425s | 2.714s |

Local verdict: **passed**. The result does not remove the separate hosted-preview and external-review gates.

## Commercial Beta Research Workflow Result

The research workflow was measured on 2026-07-18 from immutable release-candidate
commit `e930bd0e1b1062c029a7633a226db8dbc03a506b` using the same tracked demo
snapshot and environment. The run covered Research Desk, Discover, Company
Workbench, and Monitor at both viewports with one cold and five warm samples:
48 recorded route samples, zero failures, and no horizontal overflow.

| Route | Viewport | Legacy combined shell p90 | Legacy combined first useful p90 | Warm full p90 | Cold full |
| --- | --- | ---: | ---: | ---: | ---: |
| Research Desk | 1280x720 | 0.238s | 1.934s | 2.137s | 2.881s |
| Research Desk | 390x844 | 0.202s | 1.991s | 2.153s | 2.875s |
| Discover | 1280x720 | 0.211s | 1.864s | 2.444s | 2.768s |
| Discover | 390x844 | 0.208s | 1.842s | 2.474s | 2.964s |
| Company Workbench | 1280x720 | 0.224s | 1.783s | 2.856s | 3.162s |
| Company Workbench | 390x844 | 0.216s | 1.812s | 2.797s | 3.218s |
| Monitor | 1280x720 | 0.208s | 1.962s | 2.213s | 2.826s |
| Monitor | 390x844 | 0.231s | 1.811s | 2.246s | 2.679s |

The two historical tables predate the category-correct sampling contract. Their
shell and first-useful columns each combined one cold and five warm samples;
nearest-rank p90 of six values selected the maximum of each mixed population.
Keep those values as historical evidence only. Current runs report and enforce
**Warm visible-shell p90** and **Cold visible-shell max** independently at the
same `1.0s` limit, and **Warm first-useful p90** and **Cold first-useful max**
independently at the same `3.0s` limit.

## Current Sampling Reconciliation

The current implementation separates warm and cold shell and first-useful
evidence before aggregation. It preserves the existing warm/cold full-settle
rules, required sample counts, raw samples, route markers, and thresholds. It
does not retry, drop outliers, select a fastest run, or omit cold evidence.

Commit `6328c8cead7c27cb901e7878cd6d7d23fa11bb0e` passed a controlled local
Chrome run on 2026-07-31 with 48 recorded samples, zero route failures, and the
fixed demo snapshot. The aggregate Commercial Research Beta release check also
passed, including 4,474 full-suite tests. The separate accessibility browser
gate passed all six routes at both viewports plus its state harness on the same
commit. These results remain local engineering evidence only.

| Route | Viewport | Warm shell p90 | Cold shell max | Warm first-useful p90 | Cold first-useful max | Warm full p90 | Cold full max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Research Desk | 1280x720 | 0.189s | 0.217s | 1.395s | 2.132s | 2.249s | 2.984s |
| Research Desk | 390x844 | 0.187s | 0.178s | 1.403s | 2.020s | 2.279s | 2.914s |
| Discover | 1280x720 | 0.184s | 0.171s | 1.385s | 1.963s | 2.419s | 2.982s |
| Discover | 390x844 | 0.191s | 0.175s | 1.389s | 1.918s | 2.423s | 2.932s |
| Company Workbench | 1280x720 | 0.184s | 0.177s | 1.413s | 1.935s | 2.751s | 3.241s |
| Company Workbench | 390x844 | 0.199s | 0.171s | 1.442s | 1.949s | 2.787s | 3.246s |
| Monitor | 1280x720 | 0.188s | 0.179s | 1.536s | 1.985s | 2.395s | 2.839s |
| Monitor | 390x844 | 0.183s | 0.174s | 1.543s | 1.978s | 2.384s | 2.824s |

The temporary JSON remains at
`/tmp/stock-command-center-commercial-beta-performance.json` and stays out of
Git. Accept later category-specific failures without an unchanged retry loop;
only a directly measured warm or cold failure justifies route-startup
optimization.

Reproduce the research contract and browser evidence with:

```bash
make commercial-beta-performance-contract
make commercial-beta-performance-gate
```

The generated evidence path is
`/tmp/stock-command-center-commercial-beta-performance.json`. Keep it out of
Git. This local result does not prove hosted performance, external-user task
success, licensed broad data operation, or predictive accuracy.

## Reproduce

```bash
make public-performance-contract
make public-performance-gate
```

The browser command requires the development-only Playwright dependency and an executable Chrome-compatible browser. It starts the deterministic demo profile, records cold and warm route evidence, writes JSON under `/tmp`, and returns nonzero for threshold failures or `environment_limited` browser setup.

For an already-running controlled preview, use:

```bash
make public-performance-gate BASE_URL=https://example.invalid
```

Replace the example only after a real hosted URL exists. A hosted result must be recorded separately because local success does not prove deployment latency, caching, access control, or availability.

## Stop Rules

- Do not rerun broad data refreshes to improve performance numbers.
- Do not select the fastest run; keep warm p90 and cold maximum independent for shell and first-useful evidence.
- Do not call a missing browser dependency a pass.
- Do not stage the generated JSON by default.
- Do not call a preview private unless the host enforces access control.
- Do not treat screenshots or timing evidence as proof that blocked inputs became ready.
