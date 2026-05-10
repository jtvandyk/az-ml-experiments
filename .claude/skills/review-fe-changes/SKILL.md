---
name: review-fe-changes
description: Run a static-analysis checklist against feature-engineering notebook changes (notebooks/02_feature_engineering/02_build_feature_matrix.ipynb and 03_engineer_derived_features.ipynb). Catches the specific anti-patterns that have bitten this pipeline before. Use before committing FE changes or when reviewing an FE PR.
---

# Review feature-engineering changes

Pre-commit / pre-merge review for the feature-engineering notebooks. Catches the regressions we've actually had to fix in this repo (HP filter row-misalignment, merge inside per-feature loop, parquet-as-CSV, `_log_join` zombie helper, unprefixed WEO columns colliding with WDI, ENG_CFG column drift).

## When to use

- Before committing any change to `notebooks/02_feature_engineering/02_build_feature_matrix.ipynb` or `03_engineer_derived_features.ipynb`.
- When reviewing a PR that touches those notebooks.
- After an `add-data-source` run, since wiring touches `02/02`.

## When NOT to use

- For data-pull notebooks (`01_data_pull/`) — those have a different contract; no script for them yet.
- For model-development notebooks — different concerns (sweep config, MLflow logging) live there.

## Steps

1. **Run the static checker** on one or both FE notebooks:

   ```bash
   # Both notebooks (default targets):
   python3 .claude/skills/review-fe-changes/scripts/check_fe.py --all

   # Or a single notebook:
   python3 .claude/skills/review-fe-changes/scripts/check_fe.py \
       notebooks/02_feature_engineering/03_engineer_derived_features.ipynb
   ```

   Exit code 0 = clean. Exit code 1 = at least one ERROR-severity finding.

2. **Walk the manual checklist** below for things the script doesn't catch.

3. **Report findings as a punchlist** — what's wrong, where (cell ID + line if possible), and what to do. Don't auto-fix unless the user asks; review is for surfacing, not silently mutating.

## What the checker catches automatically

Each finding has a severity (ERROR / WARN / INFO), a cell ID, and a message.

### `02_build_feature_matrix.ipynb`

| Check | Severity | Why |
|---|---|---|
| `_log_join` helper still defined | WARN | Removed in the audit refactor; reappearing means a stale revert |
| `_join_iso3_source("X", ...)` where `"X"` is not a key in `RAW_PREFIXES` | ERROR | Will raise `KeyError` at runtime |
| Comment string `"(notebooks 14c–14g sources)"` (the old wrong form) | WARN | Stale; should be `"(notebooks 14–18 sources)"` |
| WEO joined without `feature_prefix=` | ERROR | Collides with WDI on `gdp_growth_pct`, `inflation_*`, etc. → silent `_x`/`_y` columns |

### `03_engineer_derived_features.ipynb`

| Check | Severity | Why |
|---|---|---|
| `df.merge(` inside a `for ... in derived_cols:` loop in Section D audit cell | ERROR | O(n_features) merges; always hoist outside the loop |
| HP-filter cell uses `.extend(` to populate trend/cycle | ERROR | Row-alignment bug — must use `df.loc[grp.index, col] = ...` |
| HP-filter input uses `.fillna(0)` instead of `ffill().bfill()` | WARN | Zero-fills produce spurious leading downturns for countries with NaN early years |
| Catalog write uses `write_parquet(..., '.csv')` (parquet payload, csv suffix) | ERROR | Breaks any consumer expecting CSV; use `to_csv` |
| Section C spatial spillover writes via per-row `.at[...]` | WARN | Slow on full panel; deferred refactor in `docs/refactor-backlog.md` |

### Cross-notebook (only when `--all` passed)

| Check | Severity | Why |
|---|---|---|
| `OUTCOME_COLS` in `02/02` and `ENG_CFG['outcome_cols']` in `02/03` differ | WARN | Out-of-sync outcome lists silently skip features in the audit |

## Manual checklist (script does not catch)

These need eyeballs:

1. **Did the new feature show up in `_catalog`?** Every column added by Section A/B/C should call `_catalog_add(...)`. Missing calls → silent feature, not in `feature_catalog_additions.csv`.
2. **Is `output_prefix` advancing?** Catalog and engineered parquet must land in the same `{RUN_DATE}` partition.
3. **Did `LABEL_HORIZON` change?** If yes, every downstream notebook must be re-run; verify the model-dev notebook reads the new partition.
4. **Did the temporal split (`TRAIN_END_YEAR`, `VAL_END_YEAR`) change?** If yes, document why — moving boundaries silently changes test-set composition.
5. **Are new ENG_CFG column references present in the panel?** The runtime warning logs missing columns at load; check the notebook's first execution log for "ENG_CFG references N column(s) that are not in the feature matrix".
6. **For new sources: is `feature_prefix=` used when collisions are possible?** Cross-check the new source's column names against `panel.columns` after the prior joins.

## Helper script

- `scripts/check_fe.py` — runs the static checks listed above.

It is pure stdlib (no extra deps) and operates on the notebook JSON directly. Safe to run repeatedly.
