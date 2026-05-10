---
name: panel-sanity-check
description: Load an engineered feature-matrix parquet (local path or ADLS) and run a battery of structural checks — required keys, duplicates, country/year coverage, outcome-label presence, missingness, near-zero variance, all-NaN columns. Use after a feature-engineering rebuild, after adding a data source, or before a sweep.
---

# Sanity-check the engineered feature matrix

Catches the structural problems that don't surface until model training fails or a sweep produces silent garbage. Verifies the matrix actually has the shape and contents the rest of the pipeline assumes.

## When to use

- Immediately after rerunning `notebooks/02_feature_engineering/03_engineer_derived_features.ipynb`.
- After adding a new data source (the join in `02/02` may have introduced surprise NaNs or column collisions).
- Before kicking off a HyperDrive sweep — failed sweeps from a malformed matrix burn cluster minutes.
- When a notebook reports unexpected row counts and you want a structured diagnosis.

## When NOT to use

- For raw source parquets (`raw/<source>/<RUN_DATE>/...`) — the contract is different (single source, no derived features). Use the validate cell in the source-pull notebook instead.
- For runtime model diagnostics — that's the `inspect-sweep-results` skill.

## Steps

1. **Run the script with a parquet path:**

   ```bash
   # Local file
   python3 .claude/skills/panel-sanity-check/scripts/check_panel.py \
       path/to/feature_matrix_engineered.parquet

   # ADLS path
   python3 .claude/skills/panel-sanity-check/scripts/check_panel.py \
       abfss://data@<account>.dfs.core.windows.net/processed/feature_matrix_engineered/20260510/feature_matrix_engineered.parquet
   ```

   The script auto-detects `abfss://` and uses `DefaultAzureCredential`. For local paths it uses pandas directly.

2. **Optional flags:**
   - `--countries-min 30 --countries-max 200` — bounds for the warning on country count.
   - `--years-expected 2000-2024` — expected year range; warns if min/max diverge.
   - `--outcome-cols "civil_war_onset,coup_attempt,..."` — required labels (defaults to the canonical 12 from `.claude/data-and-predictors.md` §2).
   - `--missingness-threshold 0.75` — warn on columns more than this fraction missing.
   - `--nzv-threshold 1e-6` — std below this → near-zero-variance flag.
   - `--top-missing 20` — how many most-missing columns to list (default 20).

3. **Read the punchlist.** Output is grouped by severity (`ERROR` / `WARN` / `INFO`). Exit code is 0 if no `ERROR`-severity findings; 1 otherwise.

4. **For `WARN` and `INFO` findings**, decide whether they're real problems or expected. The script is intentionally a bit chatty — it's better to surface a borderline warning and have you dismiss it than miss a real issue.

## What it checks

| Severity | Check |
|---|---|
| ERROR | `iso3` or `year` column missing |
| ERROR | Duplicate `(iso3, year)` rows |
| ERROR | Any required outcome label column missing |
| ERROR | `iso3` has any NaN values |
| ERROR | `year` has any NaN values |
| WARN | Country count outside `[--countries-min, --countries-max]` |
| WARN | Year range disagrees with `--years-expected` |
| WARN | Any feature column 100% NaN |
| WARN | Near-zero-variance count > 5% of feature columns |
| WARN | Any feature column more than `--missingness-threshold` missing |
| WARN | Country has fewer than 5 years of data |
| WARN | Year has fewer than 40 countries represented |
| WARN | Column-name collision indicators (`_x` / `_y` suffixes from a silent merge) |
| INFO | Row count vs. (countries × years) |
| INFO | Top N most-missing columns |
| INFO | NZV column list (if any) |

## Helper script

- `scripts/check_panel.py` — loads the parquet (local or ADLS) and runs the checks.

Requires `pandas` and `pyarrow` (already in the project env). For ADLS reads it additionally needs `azure-identity` and `adlfs`. The script imports lazily so local-only checks don't require the Azure stack.
