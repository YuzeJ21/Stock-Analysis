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
| Visible Streamlit shell p90 | 1.0s |
| First useful route answer p90 | 3.0s |
| Warm full-settle p90 | 5.0s |
| Cold full settle | 10.0s |

Stock Selector, Single-Stock Report, and Data Health are critical routes. Home and Proof History remain regression-protected references.

## Reviewed Local Result

The release run used five warm runs and one server-cold run for every public route at both viewports: 60 recorded route samples, with zero route failures.

| Route | Viewport | Shell p90 | First useful p90 | Warm full p90 | Cold full |
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
- Do not select the fastest run; use the recorded p90 summary.
- Do not call a missing browser dependency a pass.
- Do not stage the generated JSON by default.
- Do not call a preview private unless the host enforces access control.
- Do not treat screenshots or timing evidence as proof that blocked inputs became ready.
