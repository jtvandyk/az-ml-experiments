# Meta-Plan: Social Instability Classifiers
## 4–6 Month Single Data Scientist Project on Azure ML

**Compiled:** April 2026
**Compute & tracking:** Azure ML (HyperDrive, MLflow, Managed Endpoints)
**Architecture target:** XGBoost/RF ensemble (months 1–4) → optional hybrid Bi-LSTM + XGBoost (months 5–6)
**Primary evaluation metric:** AUPRC (not AUROC — rare events require precision-recall evaluation per Ward, Greenhill & Bakke 2010 and every subsequent benchmark)

---

## Strategic Framing

Three findings from the literature should govern every architecture decision:

1. **No single model wins.** EMBERS, ViEWS, CoupCast, and the IMF WP all demonstrate ensemble fusion beats any individual model by 5–15 AUPRC points. Build toward an ensemble from day one, not as a late addition.

2. **XGBoost is the best single tabular base learner.** For structured country-month data, gradient boosted trees consistently outperform Random Forest (IMF WP 2021; Wang 2018 correcting Muchlinski). RF is valuable as an ensemble member, not the primary model.

3. **Temporal validation is non-negotiable.** Train on T₀→T-2, validate on T-1, test on T. No shuffled k-fold. Models evaluated otherwise are unreliable for deployment. This is the single most common methodological failure in the literature (Ward, Greenhill & Bakke 2010).

---

## Phase I — Infrastructure & Data (Month 1)

### Weeks 1–2: Azure ML Workspace + Data Procurement

**Infrastructure (Week 1)**
- Provision Azure ML Workspace via Bicep template: Workspace, Storage Account, CPU compute cluster (Standard_DS3_v2, min 0 / max 4 nodes — autoscale keeps cost near zero when idle)
- Configure MLflow tracking URI to Azure ML: `azureml://<workspace-name>`; verify test run appears in portal
- Repo structure: `data/{raw,processed,splits}`, `notebooks/`, `src/{features,training,inference,monitoring}`, `configs/`, `infra/`
- `.env.template` with: `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_WORKSPACE_NAME`, `ACLED_API_KEY`, `MLFLOW_TRACKING_URI`

**Data procurement (Week 2)**

Primary sources:

| Dataset | Contents | Access |
|---------|----------|--------|
| ACLED | Event-level conflict + protest data, Africa focus; ~25K events/year | Free registration at acleddata.com |
| World Bank WDI | GDP per capita, unemployment, inflation, population, urbanisation; annual | `wbdata` Python package |
| V-Dem | Regime type (liberal democracy index, executive constraints, elections); annual | `vdemdata` Python or CSV download |
| GDELT GKG | Monthly Goldstein score and tone by country (optional — months 3+) | BigQuery |

Geographic scope: Africa (NG, ZA, UG, DZ + neighbors for spatial contagion features); 2010–present.

**Decisions to make in Week 2 — record in `docs/schema_definition.md`:**

1. **Unit of analysis:** country-month (recommended — matches ACLED temporal resolution; annual is too coarse for protest forecasting)
2. **Target variable:** multi-class, 4 categories — `peaceful_protest`, `riot_violence`, `armed_conflict`, `no_event` — mapped from ACLED `disorder_type` + `event_type`. Binary is simpler but loses strategic value.
3. **Prediction horizon:** 1-month ahead for v1 (predict month T+1 from features through T). 3-month ahead as stretch goal.
4. **Geographic scope:** Africa (54 countries × ~168 months ≈ 9,000 country-month observations). Sufficient for tabular ML; insufficient for deep learning — informs architecture choices.

**Outputs:** `data/raw/acled_raw.csv`, `data/raw/wdi_panel.csv`, `data/raw/vdem_panel.csv`, `docs/schema_definition.md`, Azure ML Workspace live

---

### Weeks 3–4: EDA + Feature Engineering Foundation

**EDA notebook** (`notebooks/01_eda.ipynb`):
- Class distribution by country and month — expect heavy imbalance (~80% no-event cells; armed conflict <2%)
- Missing data heatmap by country-year (fragile states have worst WDI coverage — document which features need imputation)
- Temporal autocorrelation: ACLED monthly event counts as time series per country; identify conflict cycles

**Feature engineering foundation** (`src/features/engineer.py`):

The most predictive feature categories from the literature:

| Category | Features | Source |
|----------|----------|--------|
| Conflict history | ACLED event count (t-1, t-3, t-6, t-12 months); rolling 3/6-month mean; binary "any event in prior month" | ACLED |
| Regime type | V-Dem liberal democracy index; executive constraints; elections in prior 12 months | V-Dem |
| Economic stress | GDP growth YoY; inflation rate; unemployment; food price index | WDI + FAO |
| Spatial contagion | Neighbor-country event count weighted by inverse distance; same-language-group event count | ACLED + COW |
| Population | Log population; urban share | WDI |
| Temporal | Month of year (seasonality); years since last major event (duration model-inspired) | Derived |

Build feature matrix as country-month panel: `data/processed/feature_matrix.parquet`

**Outputs:** `notebooks/01_eda.ipynb`, `src/features/engineer.py`, `data/processed/feature_matrix.parquet`, class balance report

---

## Phase II — Baseline + Model Selection (Months 2–3)

### Weeks 5–6: Temporal Splits + Baselines

**Strict temporal splits** (`src/features/splitter.py`):
- Train: 2010–2022
- Validation: 2023
- Test: 2024 (held out until final evaluation only)
- Export: `data/splits/{train,val,test}_indices.json`
- Add assertion that no test-set date appears in training index — enforce at runtime

**Rule-based baseline** (MLflow run: `baseline_rules`):
- IF ACLED events > 0 in prior month AND GDP growth < 0 → predict `riot_violence`
- Log AUPRC, F1-macro, per-class precision/recall
- This is the floor — every model must beat it

**Logistic regression baseline** (MLflow run: `baseline_logreg`):
- Firth rare-event logistic regression (King & Zeng 2001) — standard comparison point in the literature
- Features: lag-1 event count, regime type, GDP growth, spatial lag
- Log AUPRC, F1-macro; compare to rule-based

---

### Weeks 7–9: XGBoost + Random Forest Tuning

**XGBoost** (`src/training/train_xgboost.py`):
- Class imbalance: `scale_pos_weight = count(no_event) / count(instability)` per class (one-vs-rest)
- Local RandomizedSearchCV (20 iterations) first; if training time < 3 min/run, proceed locally; otherwise submit HyperDrive job to Azure ML CPU cluster

Hyperparameter grid:

| Parameter | Values | Notes |
|-----------|--------|-------|
| `n_estimators` | 200, 500, 1000 | |
| `max_depth` | 3, 4, 6 | Shallow — conflict data is noisy; deep trees overfit |
| `learning_rate` | 0.01, 0.05, 0.1 | |
| `subsample` | 0.6, 0.8 | Stochastic boosting |
| `colsample_bytree` | 0.6, 0.8 | |
| `min_child_weight` | 5, 10, 20 | Key regularizer for rare events |

Log every run: `mlflow.xgboost.log_model()`, AUPRC per class, F1-macro, confusion matrix PNG.

If >50 iterations needed: HyperDrive job on Azure ML CPU cluster, Bandit early stopping `slack_factor=0.15`.

**Random Forest** (`src/training/train_rf.py`):
- `class_weight="balanced"` throughout
- Comparable hyperparameter grid
- RF is slower than XGBoost but provides diverse predictions for the ensemble

**SHAP analysis** (`notebooks/03_shap_analysis.ipynb`):
- `shap.TreeExplainer` on best XGBoost run (exact and fast via TreeSHAP)
- Summary plot for global feature importance; waterfall plots for individual country predictions
- Log SHAP plots as MLflow artifacts

**Outputs:** XGBoost and RF champions registered in MLflow, SHAP notebook, `models/model_comparison.csv`

---

### Weeks 10–11: Ensemble + Error Analysis

**Stacking ensemble** (`src/training/train_ensemble.py`):
- Out-of-fold XGBoost and RF predictions on training set → meta-features
- Meta-learner: logistic regression (simple, interpretable — per ViEWS stacking approach)
- Also try simple weighted averaging of calibrated probabilities (often within 3–5 AUPRC of stacking; compare both)
- Log ensemble as separate MLflow run

**Error analysis** (`notebooks/04_error_analysis.ipynb`):
- Confusion matrix by event type and country
- Identify systematically misclassified country-months (false negatives on riot onset are highest-cost)
- Check: are false negatives concentrated in specific countries, seasons, or economic conditions?
- Flag feature gaps: e.g., if food price spike events are missed → add FAO food price index
- Log confusion matrix + breakdown as MLflow HTML artifact

**Champion model selection:**
- Primary metric: AUPRC averaged across instability classes (excluding `no_event`)
- Secondary: F1-macro, false negative rate on `riot_violence` and `armed_conflict`
- Register champion in MLflow Registry with status `Staging`
- Document decision in `docs/champion_selection.md` (metrics, error profile, production constraints)

**Outputs:** Stacking ensemble registered, error analysis notebook, champion model in MLflow Staging

---

## Phase III — Deployment + Monitoring (Month 4)

### Weeks 13–14: Inference Package + Testing

**Inference code** (`src/inference/`):
- `model_loader.py` — fetch champion model from MLflow registry by version; cache to disk; reload on hash mismatch
- `preprocessor.py` — identical feature pipeline to training (same `engineer.py`); validate input schema at entry
- `predictor.py` — input → features → prediction + confidence → output JSON; threshold calibrated on validation set
- `app.py` — FastAPI with `POST /predict` (single country-month) and `GET /health`

Output schema for `POST /predict`:
```json
{
  "country": "Nigeria",
  "month": "2024-07",
  "prediction": "riot_violence",
  "confidence": 0.71,
  "class_probabilities": {
    "no_event": 0.18,
    "peaceful_protest": 0.11,
    "riot_violence": 0.71,
    "armed_conflict": 0.00
  },
  "model_version": "instability-ensemble-v1"
}
```

**Tests** (`tests/`):
- `test_preprocessor.py` — known inputs → known feature values
- `test_predictor.py` — mock model, verify output schema
- Integration test: 10 real country-months from test set, compare prediction to ground truth

**Azure ML Managed Endpoint** (preferred over ACI — simpler autoscaling, native MLflow integration):
```bash
az ml online-endpoint create --name instability-predictor \
  --resource-group <rg> --workspace-name <ws>

az ml online-deployment create --endpoint instability-predictor \
  --name v1 --model <model-uri>
```
Managed endpoint scales to zero; billed per invocation. Built-in Application Insights logging.

**Outputs:** Inference package, tests passing, endpoint live, health check succeeds

---

### Weeks 15–16: Monitoring + Documentation

**Data drift monitoring** (`src/monitoring/drift_detector.py`):
- Monthly batch job (Azure ML Pipeline or cron): compare incoming inference request features to training distribution using KS test
- Alert threshold: KS statistic > 0.15 on any feature → write to Application Insights custom event
- Retraining trigger: drift detected OR 6-month model staleness

**Documentation:**
- `docs/monitoring_guide.md` — observability setup + Application Insights alert queries
- `docs/rollback_playbook.md` — revert to previous model version via MLflow registry
- `docs/runbook.md` — end-to-end: pull new ACLED data → feature engineering → retrain → evaluate → promote → deploy
- MLflow audit: export all experiment runs + registry history; record which run ID is production and why

**Outputs:** Monitoring dashboard, runbooks, MLflow audit report, go-live checklist

---

## Phase IV — Optional Extension (Months 5–6)

*Pursue only if Phase III completes on schedule and test-set AUPRC falls below 0.55 — indicating tabular features are insufficient and temporal sequence modeling is needed.*

### Month 5: Bi-LSTM Temporal Branch

The Chitengu et al. (2025) architecture — highest-performing result on Africa protest prediction (92% accuracy, South Africa) — uses a **hybrid Bi-LSTM + XGBoost**:

- **Bi-LSTM branch:** processes 12-month sequences of ACLED event counts per country; captures protest wave dynamics that tabular lag features miss
- **XGBoost branch:** processes structural features (regime type, economic indicators)
- **Fusion:** concatenate Bi-LSTM hidden state + XGBoost leaf embeddings → final classification head

**Azure ML GPU cluster** (Standard_NC6, 1× K80): only needed for Bi-LSTM training; autoscale to zero when idle.

`src/training/train_lstm.py`:
- PyTorch or Keras; sequence length = 12 months
- `hidden_size=128`, `num_layers=2`, `dropout=0.3`, bidirectional=True
- Adam optimizer, LR=1e-3, cosine annealing
- Submit as Azure ML GPU compute job; log via `mlflow.pytorch.log_model()`

---

### Month 6: LLM Narrative Layer

From literature consensus: LLMs are **not** primary classifiers but are valuable as a narrative explanation layer (USHMM Early Warning Project; Mueller/Rauh ConflictForecast.org).

Using Azure AI Foundry (already in use for PEA pipeline):
- Input: SHAP feature attribution for a flagged country-month + recent ACLED event summaries (last 30 days)
- Output: 2-paragraph analyst-facing risk narrative explaining why the model flagged the country
- Implementation: `src/inference/narrator.py` — calls the same Azure Foundry endpoint as the PEA pipeline
- Zero-shot prompting with structured SHAP context — no additional fine-tuning required

---

## Azure ML Architecture Map

```
Azure ML Workspace
├── Compute
│   ├── cpu-cluster (Standard_DS3_v2, 0–4 nodes)   training, HyperDrive
│   └── gpu-cluster (Standard_NC6, 0–2 nodes)       LSTM only (Phase IV)
│
├── Data Assets
│   ├── acled-africa-2010-present    (versioned)
│   ├── wdi-panel                    (versioned)
│   └── feature-matrix-vN            (versioned, updated monthly)
│
├── Experiments (MLflow)
│   ├── baseline-rules
│   ├── baseline-logreg
│   ├── xgboost-tuning
│   ├── rf-tuning
│   ├── ensemble-stacking
│   └── lstm-hybrid                  (Phase IV)
│
├── Model Registry
│   ├── instability-xgboost-champion  (Staging → Production)
│   ├── instability-rf-v1
│   ├── instability-ensemble-v1
│   └── instability-lstm-hybrid       (Phase IV)
│
└── Managed Endpoint
    └── instability-predictor         (FastAPI, autoscale 0–2 replicas)
```

---

## Single Data Scientist Adjustments

The original plan assumed 1–3 annotators for custom labeling. With one person, the annotation bottleneck is severe. Three mitigations:

1. **Use ACLED labels directly.** ACLED's `event_type` and `sub_event_type` fields are already expert-coded at record level. Map them to your 4-class taxonomy without manual re-annotation. Saves 2–3 weeks of Month 1 work.

2. **Defer active learning.** The Label Studio uncertainty-sampling tiers are valuable but require a model in production before they help. Implement in months 5–6 only if model performance is below target.

3. **Use HyperDrive instead of manual grid search.** Submit overnight HyperDrive jobs to the CPU cluster rather than running experiments serially. Budget ~$30–50/month for cluster time; set a spending alert at $100/month.

---

## Success Criteria

| Milestone | Target | Rationale |
|-----------|--------|-----------|
| Month 1 complete | Feature matrix built, temporal splits defined, EDA notebook runnable | No model can be trained without clean data foundation |
| Month 2 complete | Baseline AUPRC logged; logistic regression > rule-based | Establishes benchmark floor |
| Month 3 complete | XGBoost AUPRC ≥ 0.55 on validation set | Literature suggests 0.55–0.70 for Africa protest data with ACLED features |
| Month 4 complete | Endpoint live, health check passes, monitoring dashboard active | Production-ready |
| Month 5 *(optional)* | Hybrid AUPRC ≥ 0.65 on validation set | Only pursue if tabular models plateau below 0.60 |

---

## Timeline Summary

| Month | Phase | Key Deliverables | Azure ML Usage |
|-------|-------|-----------------|----------------|
| 1 | Infrastructure + Data | Workspace, ACLED/WDI/V-Dem loaded, feature matrix v1, EDA notebook | Workspace setup, first MLflow run |
| 2 | Baselines + Splits | Rule-based + logistic regression baselines, temporal splits, feature matrix finalized | MLflow experiment tracking |
| 3 | XGBoost + RF | Tuned models, SHAP analysis, error analysis, champion registered | HyperDrive on CPU cluster |
| 4 | Ensemble + Deployment | Stacking ensemble, Managed Endpoint live, monitoring, runbooks | Managed Endpoint, Application Insights |
| 5 *(optional)* | Bi-LSTM branch | Hybrid LSTM + XGBoost, improved AUPRC if needed | GPU cluster, PyTorch job |
| 6 *(optional)* | LLM narrative layer | Analyst-facing risk narratives via Azure Foundry | Foundry API (existing PEA infra) |

---

## Key Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| ACLED API schema change breaks feature pipeline | Low | Version-pin raw data as Azure ML Data Assets; add schema assertion tests |
| Azure ML compute costs exceed budget | Medium | CPU cluster autoscales to zero; disable GPU cluster when idle; spending alert at $100/month |
| Feature engineering takes longer than planned | High | Prioritize lag features + regime type (proven in literature); defer GDELT text features to Phase IV |
| AUPRC < 0.50 on test set | Medium | Diagnose by class: if `no_event` recall is inflating the number, check class weighting; if `armed_conflict` AUPRC is low, add spatial contagion features |
| Temporal leakage invalidates results | High | Enforce strict temporal split in `splitter.py`; assert no test-set date appears in training index at runtime |

---

## Source Documents

This meta-plan synthesizes four planning documents in this repo:

| File | Contents |
|------|----------|
| `plan-socialInstabilityClassifiers.prompt.md` | Original 4-month phased plan (data procurement, annotation, tuning, deployment) |
| `model_types_instability_prediction.md` | Literature synthesis across model generations (logistic regression → tree methods → deep learning → LLMs) |
| `# Dataset & Variable Synthesis.md` | Comprehensive catalog of source datasets (ACLED, WDI, V-Dem, GDELT) and predictor/label taxonomies |
| `# Snowball Literature Review: Machine Le.md` | Annotated bibliography of 30+ studies across five instability domains (EMBERS, ViEWS, CoupCast, IMF WP, Chitengu 2025) |
