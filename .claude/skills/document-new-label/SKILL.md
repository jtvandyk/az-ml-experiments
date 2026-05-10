---
name: document-new-label
description: Scaffold a label-card markdown stub at docs/labels/<outcome>.md, walking through the four-item documentation checklist (base rate, coverage, onset definition, source-agreement rate) plus construct-validity caveats. Use when introducing a new outcome label to the model.
---

# Document a new label

Captures the substantive claims an outcome label embeds — threshold choice, peace-spell window, source coverage, construct-validity gaps — before it gets baked into the model. Loose label conventions are how forecasts silently shift their meaning across iterations.

## When to use

- A new outcome is being added to `OUTCOME_COLS` in `02/02` and `ENG_CFG['outcome_cols']` in `02/03`.
- An existing outcome's definition is being changed (different threshold, different peace-spell window) — document the new variant, don't overwrite.
- A reviewer asks "what counts as a `civil_war_onset` exactly?" and you can't point at a one-page answer.

## When NOT to use

- Predictor-only sources — those go in `data-and-predictors.md` §1, not `docs/labels/`.
- Internal intermediate flags (e.g. `_event_t-1`) used during label construction but never used as a target.

## Steps

1. **Gather the four required facts** before invoking the script (these are the §5 documentation checklist from `.claude/data-and-predictors.md`):

   | Field | What it answers |
   |---|---|
   | `base_rate` | positives / total country-years (or "TBD — compute after first pull") |
   | `coverage` | which countries; which year range; missing-treatment policy (`0` = no event vs. `NA` = unknown) |
   | `onset_definition` | event threshold + peace-spell window `k`; or delta threshold; or percentile rule |
   | `source_agreement` | only if cross-source triangulated — what fraction of years agree across sources |

2. **Pick a `family`** — the construction pattern. One of:
   - `onset` — peace-spell-filtered onset (UCDP `civil_war_onset`, Powell-Thyne `coup_attempt`)
   - `delta` — deterioration of a continuous index (V-Dem `regime_backsliding`)
   - `percentile` — country-relative percentile exceedance (ACLED `mass_unrest_onset`)
   - `triangulated` — cross-source agreement
   - `weak-supervision` — Snorkel-style labeling functions
   - `llm` — LLM extraction from text

3. **Run the scaffold script:**

   ```bash
   python3 .claude/skills/document-new-label/scripts/scaffold_label_card.py \
       --outcome civil_war_onset \
       --family onset \
       --source "UCDP-GED (notebook 06)" \
       --owner jt
   ```

   Writes `docs/labels/civil_war_onset.md` from the template. Fails if the file already exists (use `--force` to overwrite an in-progress draft).

4. **Fill in the `TODO` markers** in the resulting file. The template has `TODO:` placeholders for every fact the script can't infer (base rate, sensitivity table, references). Don't ship a label card with `TODO:` markers still in it.

5. **Cross-link.** Once the card is filled in:
   - Add the outcome to `OUTCOME_COLS` in `02/02` cell `e1af34a0` and `ENG_CFG['outcome_cols']` in `02/03` cell `aa000004` (use `edit-notebook` for the diff).
   - Add a one-line summary row to `.claude/data-and-predictors.md` §2 with a link to the card.
   - If the label is cross-sourced, the disagreement-row count goes in the card AND should be flagged in `docs/refactor-backlog.md` if disagreement is high (>15%).

## Recommended fields in the card (the template provides all of these)

- Outcome name + family
- Source dataset(s) and notebook number
- Operational definition (threshold rule in pseudocode)
- Base rate (with a date)
- Coverage table (countries × year range; missing-treatment)
- Sensitivity to threshold / peace-spell window — a small table showing how base rate moves as `k` varies (1, 2, 3, 5)
- Construct-validity gaps — what the operational definition does NOT capture (e.g. UCDP misses sub-25-death conflicts, biased toward media-covered events)
- References — papers/datasets that ground the threshold choice

## Helper scripts

- `scripts/scaffold_label_card.py` — copies the template and substitutes outcome/family/source/owner.
- `templates/label_card_template.md` — canonical card structure.
