"""
Shared temporal feature engineering for the standalone instability classifier.

Used by:
  notebooks/xgboost_instability_classifier.ipynb  (training)
  notebooks/xgboost_inference.ipynb                (inference)

The inference path supports target_col=None for data without known outcomes.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def _years_since_last(grp: pd.DataFrame, year_col: str, target_col: str) -> pd.Series:
    grp = grp.sort_values(year_col)
    last_event_year = None
    values = []
    for _, row in grp.iterrows():
        values.append(float("nan") if last_event_year is None
                      else row[year_col] - last_event_year)
        if target_col and row.get(target_col) == 1:
            last_event_year = row[year_col]
    return pd.Series(values, index=grp.index)


def engineer_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add lag, rolling, event-history, and categorical-encoding features.

    Parameters
    ----------
    df : raw country-year panel (must be sorted or will be sorted here)
    cfg : configuration dict with keys:
        country_col, year_col, target_col (str | None), drop_cols (list),
        lag_features (bool), lag_years (list[int]), rolling_windows (list[int]),
        numeric_fill ('median' | 'mean' | 0)
    """
    country_col = cfg["country_col"]
    year_col    = cfg["year_col"]
    target_col  = cfg.get("target_col")  # may be None for unseen data

    df = df.copy().sort_values([country_col, year_col])

    cols_to_drop = [c for c in cfg.get("drop_cols", []) if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    exclude = {country_col, year_col}
    if target_col:
        exclude.add(target_col)
    feature_cols = [c for c in df.select_dtypes(include="number").columns
                    if c not in exclude]

    if cfg.get("lag_features", True):
        for col in feature_cols:
            for lag in cfg.get("lag_years", [1, 2, 3]):
                df[f"{col}_lag{lag}"] = df.groupby(country_col)[col].shift(lag)
        for col in feature_cols:
            for window in cfg.get("rolling_windows", [3, 5]):
                df[f"{col}_roll{window}mean"] = (
                    df.groupby(country_col)[col]
                    .transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
                )

    if target_col and target_col in df.columns:
        df["hist_instability_count"] = (
            df.groupby(country_col)[target_col]
            .transform(lambda s: s.shift(1).expanding().sum())
            .fillna(0)
        )
        df["years_since_last_event"] = (
            df.groupby(country_col, group_keys=False)
            .apply(lambda grp: _years_since_last(grp, year_col, target_col))
        )
    else:
        df["hist_instability_count"] = 0.0
        df["years_since_last_event"] = float("nan")

    numeric_cols = [c for c in df.select_dtypes(include="number").columns
                    if c != target_col]
    fill = cfg.get("numeric_fill", "median")
    if fill == "median":
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    elif fill == "mean":
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    else:
        df[numeric_cols] = df[numeric_cols].fillna(0)

    le = LabelEncoder()
    for col in df.select_dtypes(include=["object", "category"]).columns:
        if col != country_col:
            df[col] = le.fit_transform(df[col].astype(str))

    return df
