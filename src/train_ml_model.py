"""
src/train_ml_model.py — Train XGBoost delay and return models on the v2 data.

Replaces the notebook-only training step with a runnable, reproducible script
that:
  - Loads the current scored dataset (data/scored_pos.csv)
  - Featurizes the rows (numeric + one-hot, including v2 upstream features)
  - Trains an XGBoost classifier for is_delayed and is_returned
  - Reports AUC on a held-out 20% test set
  - Reports top feature importances for each model
  - Reports rule-scorer band separation on the same dataset
  - Saves the trained models to output/models/ as pickles (so the hybrid is
    no longer notebook-bound)
  - Saves a machine-readable metrics file (output/ml_metrics.json) and a
    plain-English report (output/ml_model_report.txt)

Run from project root with venv active:
    python -m src.train_ml_model
"""

import json
import os
import pickle

import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

INPUT_PATH = "data/scored_pos.csv"
MODELS_DIR = "output/models"
REPORT_PATH = "output/ml_model_report.txt"
METRICS_PATH = "output/ml_metrics.json"

SEED = 42


def featurize(df):
    """Encode features for ML — numeric + one-hot, identical to the
    stress-test featurizer so models are directly comparable."""
    numeric_cols = ["vendor_is_new", "vendor_reliability", "order_qty",
                    "sampling_delay_days", "fabric_arrival_delay_days",
                    "trims_confirmation_lag_days", "factory_ncr_count",
                    "buyer_change_frequency"]
    x = df[numeric_cols].copy()
    x = x.fillna({"vendor_reliability": 0.85, "vendor_is_new": False,
                  "order_qty": 200, "sampling_delay_days": 0,
                  "fabric_arrival_delay_days": 0,
                  "trims_confirmation_lag_days": 0,
                  "factory_ncr_count": 0, "buyer_change_frequency": 1})
    for cat_col in ["vendor_cluster", "fabric_type", "destination_tier",
                    "payment_mode", "season"]:
        dummies = pd.get_dummies(df[cat_col].fillna("missing"), prefix=cat_col)
        x = pd.concat([x, dummies], axis=1)
    return x.astype(float)


def train_and_eval(df, target_col, label):
    """Train an XGBoost classifier for `target_col`; return model + AUC +
    feature importances on a held-out 20%."""
    x = featurize(df)
    y = df[target_col].astype(int).values

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=SEED, stratify=y)

    model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        eval_metric="auc", random_state=SEED,
    ).fit(x_train, y_train)

    auc = roc_auc_score(y_test, model.predict_proba(x_test)[:, 1])
    importances = pd.DataFrame({
        "feature": x.columns,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    print(f"\n=== {label} model ===")
    print(f"  AUC on held-out test:  {auc:.3f}")
    print("  Top 5 features:")
    for _, row in importances.head(5).iterrows():
        print(f"    {row['feature']:32s}  {row['importance']:.3f}")
    return model, auc, importances


def band_separation(df, score_col, outcome_col):
    """Real outcome rate by predicted-score band — the rule-scorer's
    discriminative power on the dataset."""
    bands = pd.cut(df[score_col], bins=[0, 35, 65, 100],
                   labels=["Low", "Medium", "High"])
    rates = df.groupby(bands, observed=True)[outcome_col].mean()
    return {str(k): round(v * 100, 1) for k, v in rates.items()}


def main():
    print("ThreadTrack — XGBoost ML training on the v2 dataset")
    print("=" * 60)

    df = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df)} orders from {INPUT_PATH}")
    print(f"  Delay rate:  {df['is_delayed'].mean() * 100:.1f}%")
    print(f"  Return rate: {df['is_returned'].mean() * 100:.1f}%")

    delay_model, delay_auc, delay_imp = train_and_eval(df, "is_delayed", "Delay")
    return_model, return_auc, return_imp = train_and_eval(df, "is_returned", "Return")

    delay_bands = band_separation(df, "delay_score", "is_delayed")
    return_bands = band_separation(df, "return_score", "is_returned")

    print("\n=== Rule-scorer band separation (v2 dataset) ===")
    print(f"  Delay  bands  Low={delay_bands['Low']}%  "
          f"Medium={delay_bands['Medium']}%  High={delay_bands['High']}%")
    print(f"  Return bands  Low={return_bands['Low']}%  "
          f"Medium={return_bands['Medium']}%  High={return_bands['High']}%")

    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(os.path.join(MODELS_DIR, "delay_xgb.pkl"), "wb") as f:
        pickle.dump(delay_model, f)
    with open(os.path.join(MODELS_DIR, "return_xgb.pkl"), "wb") as f:
        pickle.dump(return_model, f)
    print(f"\nModels saved to {MODELS_DIR}/")

    metrics = {
        "n_orders":           len(df),
        "delay_rate_total":   round(df["is_delayed"].mean() * 100, 1),
        "return_rate_total":  round(df["is_returned"].mean() * 100, 1),
        "delay_auc":          round(delay_auc, 3),
        "return_auc":         round(return_auc, 3),
        "delay_band_rates":   delay_bands,
        "return_band_rates":  return_bands,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {METRICS_PATH}")

    with open(REPORT_PATH, "w") as f:
        f.write("ThreadTrack — XGBoost ML training on the v2 dataset\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Dataset:      {len(df)} orders\n")
        f.write(f"Delay rate:   {metrics['delay_rate_total']}%\n")
        f.write(f"Return rate:  {metrics['return_rate_total']}%\n\n")
        f.write("XGBoost performance on the held-out 20% test set:\n")
        f.write(f"  Delay  AUC: {delay_auc:.3f}\n")
        f.write(f"  Return AUC: {return_auc:.3f}\n\n")
        f.write("Rule-scorer band separation (full dataset):\n")
        d = metrics["delay_band_rates"]
        r = metrics["return_band_rates"]
        f.write(f"  Delay  Low={d['Low']}%  Medium={d['Medium']}%  "
                f"High={d['High']}%\n")
        f.write(f"  Return Low={r['Low']}%  Medium={r['Medium']}%  "
                f"High={r['High']}%\n\n")
        f.write("Delay model — top 10 features by importance:\n")
        for _, row in delay_imp.head(10).iterrows():
            f.write(f"  {row['feature']:32s}  {row['importance']:.3f}\n")
        f.write("\nReturn model — top 10 features by importance:\n")
        for _, row in return_imp.head(10).iterrows():
            f.write(f"  {row['feature']:32s}  {row['importance']:.3f}\n")
    print(f"Report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
