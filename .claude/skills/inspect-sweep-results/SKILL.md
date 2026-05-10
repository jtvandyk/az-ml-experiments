---
name: inspect-sweep-results
description: Pull MLflow runs from a HyperDrive sweep and produce the per-outcome diagnostic table from .claude/metric-interpretation-guide.md §9 — best/median/std of val/test/train AUPRC, val→test gap, Brier vs. prevalence baseline, P@20, best_iteration distribution, and hyperparameter-clustering recommendations for the next round.
---

# Inspect HyperDrive sweep results

Translates a fresh MLflow experiment into the structured diagnostic the metrics guide actually expects you to produce after each sweep round. Surfaces overfitting, structural shift, ceiling saturation on `best_iteration`, and where the next sweep's search space should narrow.

## When to use

- Immediately after a HyperDrive sweep finishes (typically `src/train/sweep_outcome.yml` × 5 outcomes).
- During a check-in on an in-progress sweep (read-only — won't interfere with running trials).
- When deciding whether to launch Round 2 — this skill produces the specific "narrow `max_depth` to 4–5" type recommendations.

## When NOT to use

- For per-prediction diagnostics — that's the inference notebook + SHAP, not MLflow.
- Before the first sweep completes — there's nothing to read yet.

## Steps

1. **Identify the experiment name.** Default is `instability_xgboost` per the project convention. Override with `--experiment` if your sweep used a different name.

2. **Run the script:**

   ```bash
   python3 .claude/skills/inspect-sweep-results/scripts/inspect_sweep.py \
       --experiment instability_xgboost
   ```

   With explicit MLflow tracking URI (only needed if not already set via `MLFLOW_TRACKING_URI`):

   ```bash
   python3 .claude/skills/inspect-sweep-results/scripts/inspect_sweep.py \
       --tracking-uri "azureml://..." \
       --experiment instability_xgboost
   ```

3. **Common flags:**
   - `--outcome civil_war_onset` — restrict to one outcome (otherwise iterates over all `tags.outcome` values present).
   - `--top-n 10` — number of best trials per outcome to summarise (default 5).
   - `--n-estimators-ceiling 300` — for the `best_iteration` saturation check.
   - `--json` — emit JSON instead of markdown (useful for piping into other tooling).
   - `--include-failed` — count failed trials (default skips them).

4. **Read the four diagnostic patterns** the script highlights for each outcome (these come straight from `.claude/metric-interpretation-guide.md` §2 and §9):

   | Pattern | What it means | Response |
   |---|---|---|
   | `train ≈ val >> test` | Overfitting to train+val | Tighten regularisation; reduce `max_depth`, raise `min_child_weight` |
   | `train >> val ≈ test` | Overfitting to training only | Same levers; check for leakage |
   | `train ≈ val ≈ test` (all moderate) | Genuine signal difficulty | Accept; richer features / more data |
   | `val >> test`, `train ≈ val` | Structural temporal shift post-2021 | Document; don't chase with tuning |

5. **Use the hyperparameter-clustering recommendations** (printed near the bottom of each outcome section) to design the Round 2 search space. The script identifies the min/median/max of each tunable across the top-N trials.

## What the script outputs (per outcome)

- **Per-metric summary table:** best / median / std of `val_auprc`, `test_auprc`, `train_auprc`, `val_brier`, `val_precision_at_20`, `best_iteration`.
- **Top-N trials table:** sorted by `val_auprc`, with each trial's metrics + key hyperparameters.
- **Four diagnostic checks:**
  1. val→test gap on best trial (≤0.05 = within noise; >0.10 = likely structural shift)
  2. val_brier vs. prevalence × (1 − prevalence) baseline (must beat baseline)
  3. `best_iteration` saturation (>80% of `n_estimators_ceiling` → early stopping not firing)
  4. train→val gap on best trial (>0.20 → serious overfitting)
- **Round-2 recommendations:** narrowed ranges for `max_depth`, `learning_rate`, `min_child_weight`, `gamma`, `reg_alpha`.

## Helper script

- `scripts/inspect_sweep.py` — uses `mlflow.search_runs()`. Imports lazily so `--help` works without MLflow installed; full runs require `pip install mlflow`.
