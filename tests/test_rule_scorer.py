"""Tests for src/rule_scorer.score_order."""

from src.rule_scorer import score_order

# A boring baseline order — no factor should fire except the cluster bonus.
BASELINE_LOW = {
    "vendor_is_new":      False,
    "vendor_cluster":     "Bengaluru",   # +4 delay
    "vendor_reliability": 0.93,          # above 0.85 → no penalty
    "fabric_type":        "knit",        # knit is the lighter fabric
    "order_qty":          100,           # below 350
    "destination_tier":   "Tier-1",      # no tier penalty
    "payment_mode":       "Prepaid",     # COD is the return driver
    "season":             "normal",
}

# A worst-case order — most factors fire.
WORST_CASE = {
    "vendor_is_new":      True,
    "vendor_cluster":     "Tirupur",
    "vendor_reliability": 0.70,
    "fabric_type":        "woven",
    "order_qty":          500,
    "destination_tier":   "Tier-3",
    "payment_mode":       "COD",
    "season":             "festive",
}


def test_scores_are_in_range():
    """Scores must always be between 0 and 100 inclusive."""
    for order in (BASELINE_LOW, WORST_CASE):
        r = score_order(order)
        assert 0 <= r["delay_score"] <= 100, r
        assert 0 <= r["return_score"] <= 100, r


def test_baseline_low_risk_order_has_low_scores():
    """A baseline order should score in the Low band (≤ 35)."""
    r = score_order(BASELINE_LOW)
    # baseline 10 delay + 4 (Bengaluru) = 14
    assert r["delay_score"] == 14
    # baseline 15 return, no other factors fire
    assert r["return_score"] == 15


def test_worst_case_saturates_at_100():
    """A worst-case order should hit the 100 cap on both scores."""
    r = score_order(WORST_CASE)
    assert r["delay_score"] == 100
    assert r["return_score"] == 100


def test_worst_case_higher_than_baseline():
    """Worst-case must dominate baseline on both axes."""
    base = score_order(BASELINE_LOW)
    worst = score_order(WORST_CASE)
    assert worst["delay_score"] > base["delay_score"]
    assert worst["return_score"] > base["return_score"]


def test_reasons_are_attached():
    """Worst-case order should carry many explanation strings."""
    r = score_order(WORST_CASE)
    assert len(r["delay_reasons"]) >= 5
    assert len(r["return_reasons"]) >= 4


def test_v2_factors_fire_when_upstream_present():
    """High upstream signals should push delay AND return higher than v1-only baseline."""
    v1_only = dict(BASELINE_LOW)
    v2_loaded = dict(BASELINE_LOW,
                     sampling_delay_days=5,
                     fabric_arrival_delay_days=7,
                     trims_confirmation_lag_days=4,
                     factory_ncr_count=5,
                     buyer_change_frequency=3)
    r1 = score_order(v1_only)
    r2 = score_order(v2_loaded)
    assert r2["delay_score"] > r1["delay_score"]
    assert r2["return_score"] > r1["return_score"]


def test_v2_factors_are_silent_on_v1_orders():
    """Backward-compat: an order without any v2 keys must score identically
    to one with all v2 keys explicitly set to zero/level-1."""
    v1_implicit = dict(BASELINE_LOW)
    v2_explicit_zero = dict(BASELINE_LOW,
                            sampling_delay_days=0,
                            fabric_arrival_delay_days=0,
                            trims_confirmation_lag_days=0,
                            factory_ncr_count=0,
                            buyer_change_frequency=1)
    assert score_order(v1_implicit) == score_order(v2_explicit_zero)
