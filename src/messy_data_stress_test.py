"""
src/messy_data_stress_test.py — v2 data-quality stress test.

The strongest critique of v1:
   "You trained on data that does not exist in any real factory. My factories
    have '100% cotton' spelled five ways, half the lead-time fields blank,
    and a sampling team that updates the system three days late."

This script answers it with numbers. It corrupts the clean v2 dataset in
the ways real factory ERPs actually fail — typos, missing values, late
updates, inflated entries — and reports what happens to model performance.

Three runs:
  1. Rule scorer on CLEAN data — the baseline.
  2. Rule scorer on MESSY data — degrades and cannot adapt (it is static).
  3. Logistic regression on the same features:
       a. trained on clean, tested on clean   (baseline)
       b. trained on clean, tested on messy   (degrades — distribution shift)
       c. RETRAINED on messy, tested on messy (partial recovery — the loop)

The third comparison is the argument for an MLOps retraining loop, not a
frozen one-shot model. The same finding applies to a brand whose buyer mix
shifts, whose suppliers change behaviour, or whose fabric vocabulary drifts.

Run from project root with venv active:
    python -m src.messy_data_stress_test
"""

import os
import random

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from src.rule_scorer import score_order

INPUT_PATH = "data/scored_pos.csv"
OUTPUT_PATH = "output/messy_data_stress_test.txt"

CORRUPTION_RATE = 0.30   # fraction of values in each categorical column
SEED = 42

CLUSTER_TYPOS = {
    "Tirupur":   ["tirupur", "Tiruppur", "T'pur", "TIRUPUR", "tirupur ", ""],
    "Bengaluru": ["bengaluru", "Banglore", "Bangalore", "BENGALURU", ""],
    "Ludhiana":  ["ludhiana", "Ludhana", "LUDHIANA", ""],
    "Delhi NCR": ["delhi ncr", "delhi-ncr", "Delhi", "NCR", ""],
}
FABRIC_TYPOS = {
    "knit":  ["KNIT", "kniT", "K", ""],
    "woven": ["WOVEN", "Woven", "W", ""],
}
SEASON_TYPOS = {
    "normal":  ["NORMAL", "regular", ""],
    "festive": ["FESTIVE", "Festive", "fest", ""],
    "monsoon": ["MONSOON", "Monsoon", "mon", ""],
}
TIER_TYPOS = {
    "Tier-1": ["tier-1", "T1", "Tier1", ""],
    "Tier-2": ["tier-2", "T2", "Tier2", ""],
    "Tier-3": ["tier-3", "T3", "Tier3", ""],
}


# ----------------------------------------------------------------- corruption
def corrupt(df, seed, rate=None):
    """Return a deliberately messy copy of df — the same orders, with the
    kind of data-quality damage a real factory ERP produces.

    `rate` controls the categorical corruption rate. Missing-numeric rates
    and quantity-typo rates scale proportionally so a single dial drives the
    overall drift severity. Defaults to module-level CORRUPTION_RATE so the
    one-shot stress test keeps its existing behaviour; the feedback-loop
    simulation passes a varying rate to model escalating drift over time.
    """
    if rate is None:
        rate = CORRUPTION_RATE
    scale = rate / CORRUPTION_RATE   # 1.0 at default, < 1.0 for lighter drift

    rng = np.random.default_rng(seed)
    random.seed(seed)
    out = df.copy()

    def mess_categorical(col, typos):
        mask = rng.random(len(out)) < rate
        for idx in out.index[mask]:
            real = out.at[idx, col]
            out.at[idx, col] = random.choice(typos.get(real, [""]))

    mess_categorical("vendor_cluster", CLUSTER_TYPOS)
    mess_categorical("fabric_type", FABRIC_TYPOS)
    mess_categorical("season", SEASON_TYPOS)
    mess_categorical("destination_tier", TIER_TYPOS)

    # Missing numerics — sampling/fabric/trims fields go blank a LOT because
    # in real factories the team that owns them updates the system days late
    # or not at all. Cast to object before NaN-injection so strict-dtype
    # columns (bool, int) accept the missing marker. Per-column base rates
    # scale by `scale` so light drift is genuinely lighter.
    for col, base_rate in [("vendor_reliability",          0.10),
                           ("vendor_is_new",               0.05),
                           ("sampling_delay_days",         0.40),
                           ("fabric_arrival_delay_days",   0.40),
                           ("trims_confirmation_lag_days", 0.40),
                           ("factory_ncr_count",           0.25),
                           ("buyer_change_frequency",      0.15)]:
        if col not in out.columns:
            continue
        if out[col].dtype != object:
            out[col] = out[col].astype(object)
        mask = rng.random(len(out)) < (base_rate * scale)
        out.loc[mask, col] = np.nan

    # Order quantity — 5% set to 0 (missing), 2% inflated 10x (typo)
    out.loc[rng.random(len(out)) < (0.05 * scale), "order_qty"] = 0
    big_mask = rng.random(len(out)) < (0.02 * scale)
    out.loc[big_mask, "order_qty"] = out.loc[big_mask, "order_qty"] * 10

    return out


# ------------------------------------------------------------------- helpers
def safe_order_dict(row):
    """Build a score_order() input dict, treating NaN as a safe default."""
    def s(key, default):
        if key not in row.index:
            return default
        v = row[key]
        return default if pd.isna(v) else v
    return {
        "vendor_is_new":                bool(s("vendor_is_new", False)),
        "vendor_cluster":               s("vendor_cluster", ""),
        "vendor_reliability":           float(s("vendor_reliability", 1.0)),
        "fabric_type":                  s("fabric_type", ""),
        "order_qty":                    int(s("order_qty", 0)),
        "destination_tier":             s("destination_tier", ""),
        "payment_mode":                 s("payment_mode", ""),
        "season":                       s("season", ""),
        "sampling_delay_days":          float(s("sampling_delay_days", 0)),
        "fabric_arrival_delay_days":    float(s("fabric_arrival_delay_days", 0)),
        "trims_confirmation_lag_days":  float(s("trims_confirmation_lag_days", 0)),
        "factory_ncr_count":            int(s("factory_ncr_count", 0)),
        "buyer_change_frequency":       int(s("buyer_change_frequency", 1)),
    }


def score_delay_all(df):
    """Return the rule scorer's delay_score for every row."""
    delay = np.zeros(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        delay[i] = score_order(safe_order_dict(row))["delay_score"]
    return delay


def featurize_for_ml(df):
    """Encode features for a quick LR baseline."""
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


# ---------------------------------------------------------------------- main
def main():
    print("ThreadTrack v2 — data-quality stress test")
    print("=" * 62)
    print()

    df_clean = pd.read_csv(INPUT_PATH)
    print(f"Loaded {len(df_clean)} orders from {INPUT_PATH}")
    df_messy = corrupt(df_clean, seed=SEED)
    print(f"Built corrupted copy (~{int(CORRUPTION_RATE * 100)}% of categorical "
          "values corrupted, plus missing numerics and quantity typos)")
    print()

    y = df_clean["is_delayed"].astype(int).values

    # --- 1. rule scorer on clean vs messy ---
    print("Step 1 — rule scorer on clean vs messy data:")
    delay_clean = score_delay_all(df_clean)
    delay_messy = score_delay_all(df_messy)
    auc_rule_clean = roc_auc_score(y, delay_clean)
    auc_rule_messy = roc_auc_score(y, delay_messy)
    print(f"  rule scorer AUC on CLEAN data:  {auc_rule_clean:.3f}")
    print(f"  rule scorer AUC on MESSY data:  {auc_rule_messy:.3f}"
          f"   (drop {auc_rule_clean - auc_rule_messy:+.3f})")
    print("  → a hand-written rule scorer cannot adapt; messy data rots it.")
    print()

    # --- 2. logistic regression, the MLOps-loop argument ---
    print("Step 2 — supervised ML (logistic regression on the same features):")
    x_clean = featurize_for_ml(df_clean)
    x_messy = featurize_for_ml(df_messy).reindex(columns=x_clean.columns,
                                                 fill_value=0.0)

    x_train, x_test, y_train, y_test = train_test_split(
        x_clean, y, test_size=0.2, random_state=SEED, stratify=y)
    model_on_clean = LogisticRegression(max_iter=2000).fit(x_train, y_train)
    auc_ml_clean = roc_auc_score(y_test,
                                 model_on_clean.predict_proba(x_test)[:, 1])
    auc_ml_clean_to_messy = roc_auc_score(
        y, model_on_clean.predict_proba(x_messy)[:, 1])

    print(f"  LR trained on CLEAN, tested on CLEAN:  {auc_ml_clean:.3f}")
    print(f"  LR trained on CLEAN, tested on MESSY:  {auc_ml_clean_to_messy:.3f}"
          f"   (drop {auc_ml_clean - auc_ml_clean_to_messy:+.3f})")
    print()

    xm_train, xm_test, ym_train, ym_test = train_test_split(
        x_messy, y, test_size=0.2, random_state=SEED, stratify=y)
    model_on_messy = LogisticRegression(max_iter=2000).fit(xm_train, ym_train)
    auc_ml_recovered = roc_auc_score(
        ym_test, model_on_messy.predict_proba(xm_test)[:, 1])

    print(f"  LR RETRAINED on MESSY, tested on MESSY:  {auc_ml_recovered:.3f}"
          f"   (recovery {auc_ml_recovered - auc_ml_clean_to_messy:+.3f})")
    print()
    print("  → ML retrained on the current distribution partially recovers.")
    print("    This is the argument for a retraining loop, not a frozen model.")
    print()

    # --- save report ---
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("ThreadTrack v2 — data-quality stress test\n")
        f.write("=" * 62 + "\n\n")
        f.write(f"Corruption: ~{int(CORRUPTION_RATE * 100)}% of categorical "
                "values mistyped or blanked, plus missing numerics and qty typos.\n\n")
        f.write("Rule scorer (static, hand-built):\n")
        f.write(f"  AUC on CLEAN data:  {auc_rule_clean:.3f}\n")
        f.write(f"  AUC on MESSY data:  {auc_rule_messy:.3f}"
                f"   drop {auc_rule_clean - auc_rule_messy:+.3f}\n\n")
        f.write("Logistic regression (the MLOps-loop argument):\n")
        f.write(f"  trained on CLEAN, tested on CLEAN:  {auc_ml_clean:.3f}\n")
        f.write(f"  trained on CLEAN, tested on MESSY:  {auc_ml_clean_to_messy:.3f}"
                f"   drop {auc_ml_clean - auc_ml_clean_to_messy:+.3f}\n")
        f.write(f"  RETRAINED on MESSY, tested on MESSY: {auc_ml_recovered:.3f}"
                f"   recovery {auc_ml_recovered - auc_ml_clean_to_messy:+.3f}\n\n")
        f.write("Interpretation:\n")
        f.write("  - A hand-built scorer cannot adapt; it silently rots under drift.\n")
        f.write("  - ML trained on clean data degrades when reality is messy.\n")
        f.write("  - ML retrained on the messy distribution recovers part of the gap.\n")
        f.write("  - This is the argument for a retraining loop, not a frozen v1 model.\n")
    print(f"Wrote results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
