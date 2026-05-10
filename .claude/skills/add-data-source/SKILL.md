---
name: add-data-source
description: Scaffold a new country-year data-pull notebook (notebooks/01_data_pull/NN_pull_<source>.ipynb) following project conventions, and walk the user through wiring it into the feature-matrix build (notebooks/02_feature_engineering/02_build_feature_matrix.ipynb). Use whenever adding a new data source to the pipeline.
---

# Add a new data source to the pipeline

Scaffolds a pull notebook from the canonical template, then walks the user through the downstream wiring. Designed to enforce the contract that `_join_iso3_source` expects: parquet keyed by `(iso3, year)`, name→ISO3 fallback in place, no surprise column collisions.

## When to use

- The user wants to add a new data source (e.g. "let's pull Source X").
- A new source has been agreed but the `01_data_pull/` notebook for it doesn't exist yet.

## Pre-flight questions to confirm with the user

Ask these BEFORE running the scaffold — the answers go into the template:

1. **Source name and short description** (e.g. "FAO Locust Watch — desert-locust early-warning bulletins").
2. **Source key** (snake_case, used for filenames + ADLS prefix). Convention: short, lowercase, no provider acronym repetition. Examples: `fao_locust`, `wbi`, `vparty`.
3. **Provider URL or API endpoint.**
4. **Cadence** (annual / monthly→annual / event-level → annual).
5. **Does the source publish ISO3 codes?** If only country names, the template's `name_to_iso3` fallback is required.
6. **Is this a predictor source, a label source, or both?** Determines whether to update `OUTCOME_COLS` in `02/02` and `ENG_CFG['outcome_cols']` in `02/03`.
7. **Will column names collide with an existing source?** WEO/WDI was the cautionary tale (`gdp_growth_pct` in both). If yes, plan a `feature_prefix=` from the start.

## Steps

1. **Find the next available NN.** List `notebooks/01_data_pull/` and pick the next two-digit prefix. Current latest is 26 — verify with `ls notebooks/01_data_pull/ | tail -3`.

2. **Run the scaffold script** with the answers from pre-flight:

   ```bash
   python3 .claude/skills/add-data-source/scripts/scaffold_pull.py \
       --nn 27 \
       --source-name "FAO Locust Watch" \
       --source-key fao_locust \
       --source-description "Desert-locust early-warning bulletins" \
       --provider "FAO" \
       --source-url "https://locust-hub-hqfao.hub.arcgis.com/" \
       --cadence "Monthly → annual aggregate" \
       --notebook-dir notebooks/01_data_pull
   ```

   This writes `notebooks/01_data_pull/27_pull_fao_locust.ipynb` from the template.

3. **Customise the placeholder cells.** Open the new notebook and fill in:
   - **Cell `cell-fetch`** — the actual download/API call. The template has a `TODO` and a placeholder that intentionally raises `NotImplementedError`.
   - **Cell `cell-clean`** — column selection, type coercion, year extraction.
   - **Cell `cell-iso3`** — only if the source lacks ISO3; the template ships with a working `name_to_iso3` helper plus an override map for known edge cases (Côte d'Ivoire, Eswatini, Czechia, etc.).

4. **Wire into the feature matrix.** Apply two edits to `notebooks/02_feature_engineering/02_build_feature_matrix.ipynb` — use the `edit-notebook` skill for this. The exact edits are:

   - **Add to `RAW_PREFIXES`** (cell `cell-3`): one new line before the closing brace, e.g.
     ```python
     "fao_locust":   "raw/fao_locust",
     ```
   - **Add a `_join_iso3_source(...)` call** (cell `be22c077`, in the supplementary-sources section). Use `feature_prefix=` if any column will collide; use `filename_hint=` if the prefix holds multiple parquets.

5. **(Optional) Update ENG_CFG** in `notebooks/02_feature_engineering/03_engineer_derived_features.ipynb` (cell `aa000004`) if the new source has columns that should get `log1p`, `sqrt`, `_diff1`, or HP-filter transforms. Skip for label-only sources.

6. **(Label sources only) Add the outcome label** to `OUTCOME_COLS` in `02/02` cell `e1af34a0` and to `ENG_CFG['outcome_cols']` in `02/03` cell `aa000004`. Document the label per the checklist in `.claude/data-and-predictors.md` §5.

7. **Smoke-test.** Run the new pull notebook end-to-end on a small year range (`PANEL_END_YEAR = PANEL_START_YEAR + 1`) before committing. Verify the written parquet has columns `iso3`, `year`, no duplicates on `(iso3, year)`.

## Conventions the template enforces

| Concern | Convention |
|---|---|
| ADLS path | `raw/{source_key}/{RUN_DATE}/{source_key}_panel.parquet` |
| Required columns | `iso3` (3-letter ISO), `year` (Int64) — non-negotiable |
| Duplicates | `drop_duplicates(["iso3", "year"])` before write |
| Auth | `DefaultAzureCredential()` — no secrets in the notebook |
| RUN_DATE | `datetime.utcnow().strftime("%Y%m%d")` — same partition format as every other source |
| Country-name fallback | Always include the `name_to_iso3` helper, even if the source ships ISO3 directly. Saves the next person from the BTI-style "no iso3 → silent KeyError downstream" surprise. |

## Helper scripts

- `scripts/scaffold_pull.py` — copies the template and substitutes placeholders.
- `templates/data_pull_template.ipynb` — canonical notebook structure (16 cells; mirrors `26_pull_ndgain.ipynb`).
- `templates/country_overrides.json` — name→ISO3 overrides (Cote d'Ivoire, Eswatini, etc.) embedded into the scaffolded notebook by default.

## Checklist for review

Before marking the new source as integrated, confirm:

- [ ] Pull notebook runs end-to-end without error.
- [ ] Output parquet has `iso3` and `year` columns; spot-check a few country-years against the source.
- [ ] `02/02` joins the new source; running `02/02` produces a non-zero "columns added" line for it.
- [ ] No new `_x` / `_y` suffixes in the panel after the join (collision check).
- [ ] Engineered notebook (`02/03`) runs without ENG_CFG-validation warnings about the new columns.
