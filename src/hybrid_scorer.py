"""
src/hybrid_scorer.py — The performance-weighted hybrid.

Closes a real gap that the case study previously claimed but did not
implement: a callable hybrid that combines the rule scorer (transparent,
hand-built) with the trained XGBoost models (learned patterns) and
returns both components plus a blend, plus a disagreement flag for
human review.

Weights are performance-weighted on the held-out v2 test set:
  delay:  0.6 ML + 0.4 rule    (XGBoost AUC 0.847 > rule scorer ~0.80)
  return: 0.5 ML + 0.5 rule    (neither method clearly stronger)

A disagreement flag fires when the rule and ML scores differ by more
than DISAGREEMENT_THRESHOLD on the 0-100 scale — the order is then
surfaced for human review, which is the operational value of the hybrid.

Usage:
    from src.hybrid_scorer import score_hybrid
    result = score_hybrid(order_dict)
"""

import os
import pickle

import pandas as pd

from src.rule_scorer import score_order

MODELS_DIR = "output/models"

WEIGHTS = {
    "delay":  {"ml": 0.6, "rule": 0.4},
    "return": {"ml": 0.5, "rule": 0.5},
}

DISAGREEMENT_THRESHOLD = 25   # on the 0-100 scale

_models = None


def _load_models():
    """Lazy-load the trained XGBoost models from output/models/."""
    global _models
    if _models is None:
        with open(os.path.join(MODELS_DIR, "delay_xgb.pkl"), "rb") as f:
            delay_model = pickle.load(f)
        with open(os.path.join(MODELS_DIR, "return_xgb.pkl"), "rb") as f:
            return_model = pickle.load(f)
        _models = {"delay": delay_model, "return": return_model}
    return _models


def _featurize_one(order):
    """Encode one order dict into the numeric + one-hot frame the ML
    models were trained on. Must match `train_ml_model.featurize`."""
    row = {
        "vendor_is_new":               int(bool(order.get("vendor_is_new", False))),
        "vendor_reliability":          float(order.get("vendor_reliability", 0.85)),
        "order_qty":                   int(order.get("order_qty", 200)),
        "sampling_delay_days":         float(order.get("sampling_delay_days", 0)),
        "fabric_arrival_delay_days":   float(order.get("fabric_arrival_delay_days", 0)),
        "trims_confirmation_lag_days": float(order.get("trims_confirmation_lag_days", 0)),
        "factory_ncr_count":           int(order.get("factory_ncr_count", 0)),
        "buyer_change_frequency":      int(order.get("buyer_change_frequency", 1)),
    }
    df = pd.DataFrame([row])
    for col in ["vendor_cluster", "fabric_type", "destination_tier",
                "payment_mode", "season"]:
        val = order.get(col, "")
        dummies = pd.get_dummies(pd.Series([val]), prefix=col)
        df = pd.concat([df, dummies.reset_index(drop=True)], axis=1)
    return df


def _align(x, model):
    """Reindex x to the model's expected feature columns; unseen → 0."""
    expected = model.get_booster().feature_names
    return x.reindex(columns=expected, fill_value=0.0).astype(float)


def score_hybrid(order):
    """Return blended scores plus components and disagreement flags.

    Result dict keys:
      rule_delay, ml_delay, hybrid_delay
      rule_return, ml_return, hybrid_return
      delay_reasons, return_reasons     (from the rule scorer, for explainability)
      agree_delay, agree_return         (bool)
      disagreements                     ({delay: None | float, return: None | float})
    """
    models = _load_models()
    rule = score_order(order)
    rule_delay = rule["delay_score"]
    rule_return = rule["return_score"]

    x = _featurize_one(order)
    ml_delay = float(models["delay"].predict_proba(_align(x, models["delay"]))[0, 1] * 100)
    ml_return = float(models["return"].predict_proba(_align(x, models["return"]))[0, 1] * 100)

    w_d, w_r = WEIGHTS["delay"], WEIGHTS["return"]
    hybrid_delay = round(w_d["ml"] * ml_delay + w_d["rule"] * rule_delay, 1)
    hybrid_return = round(w_r["ml"] * ml_return + w_r["rule"] * rule_return, 1)

    delay_gap = abs(ml_delay - rule_delay)
    return_gap = abs(ml_return - rule_return)
    agree_delay = delay_gap < DISAGREEMENT_THRESHOLD
    agree_return = return_gap < DISAGREEMENT_THRESHOLD

    return {
        "rule_delay":     rule_delay,
        "ml_delay":       round(ml_delay, 1),
        "hybrid_delay":   hybrid_delay,
        "rule_return":    rule_return,
        "ml_return":      round(ml_return, 1),
        "hybrid_return":  hybrid_return,
        "delay_reasons":  rule["delay_reasons"],
        "return_reasons": rule["return_reasons"],
        "agree_delay":    agree_delay,
        "agree_return":   agree_return,
        "disagreements": {
            "delay":  None if agree_delay else round(delay_gap, 1),
            "return": None if agree_return else round(return_gap, 1),
        },
    }


def demo():
    """Print hybrid scores for two example orders so the blend is visible."""
    examples = [
        ("High-risk Tirupur woven festive COD Tier-3 with NCRs", {
            "vendor_id": "V03", "vendor_is_new": False, "vendor_cluster": "Tirupur",
            "vendor_reliability": 0.85, "fabric_type": "woven", "order_qty": 400,
            "destination_tier": "Tier-3", "payment_mode": "COD", "season": "festive",
            "sampling_delay_days": 5, "fabric_arrival_delay_days": 7,
            "trims_confirmation_lag_days": 4, "factory_ncr_count": 5,
            "buyer_change_frequency": 2,
        }),
        ("Low-risk Bengaluru knit prepaid Tier-1 normal clean", {
            "vendor_id": "V05", "vendor_is_new": False, "vendor_cluster": "Bengaluru",
            "vendor_reliability": 0.93, "fabric_type": "knit", "order_qty": 150,
            "destination_tier": "Tier-1", "payment_mode": "Prepaid", "season": "normal",
            "sampling_delay_days": 0, "fabric_arrival_delay_days": 0,
            "trims_confirmation_lag_days": 0, "factory_ncr_count": 0,
            "buyer_change_frequency": 1,
        }),
    ]
    for label, order in examples:
        r = score_hybrid(order)
        print(f"\n— {label} —")
        print(f"  rule_delay={r['rule_delay']:5.1f}  ml_delay={r['ml_delay']:5.1f}  "
              f"→ hybrid_delay={r['hybrid_delay']:5.1f}  "
              f"({'agree' if r['agree_delay'] else 'DISAGREE'})")
        print(f"  rule_return={r['rule_return']:5.1f}  ml_return={r['ml_return']:5.1f}  "
              f"→ hybrid_return={r['hybrid_return']:5.1f}  "
              f"({'agree' if r['agree_return'] else 'DISAGREE'})")


if __name__ == "__main__":
    demo()
