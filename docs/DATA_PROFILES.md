# Data Profiles

The product uses named data profiles to keep the public demo separate from the local research workspace.

| Profile | Purpose | Git policy | Start command |
| --- | --- | --- | --- |
| `demo` | Compact, deterministic public product snapshot. | Tracked and reviewed. | `make demo-dashboard` |
| `default` | Existing repository data paths for compatibility and operator work. | Track only reviewed source artifacts. | `make dashboard` |
| `local` | Full refreshed research workspace, caches, and generated local outputs. | Ignored. | `STOCK_RESEARCH_DATA_PROFILE=local make dashboard` |

## Public Demo Contract

`data/demo/manifest.json` records the selected tickers, snapshot date, per-file row counts, date bounds, SHA-256 checksums, source labels, and known limitations. Verify it without rebuilding:

```bash
make demo-data-check
```

Rebuild the compact snapshot only after deliberately reviewing the local source data:

```bash
make demo-data-build
```

The demo profile is product evidence. It is not a data-freshness claim, does not include personal holdings or credentials, and never unlocks source-gated fundamentals, peers, earnings, estimates, or valuation inputs.

## Profile Selection

Set `STOCK_RESEARCH_DATA_PROFILE` to `demo`, `default`, or `local`. Explicit `data_dir` and `output_dir` arguments always override the profile. Public and hosted checks use `demo` so a green gate proves the compact shareable package, not an arbitrary local refresh.

Seed the ignored `local` profile from the current canonical workspace with `make local-profile-seed`. It copies the runtime CSVs, imports, readiness reports, and operational outputs, but never copies caches, backups, demo data, or generated stock reports. Price validate, preview, apply, and refresh targets use this local profile by default.
