"""Tests for src/messy_data_stress_test.corrupt — the drift simulator."""

import numpy as np
import pandas as pd

from src.messy_data_stress_test import corrupt


def _sample_frame():
    """Build a tiny frame with the columns corrupt() touches."""
    return pd.DataFrame({
        "vendor_cluster":               ["Tirupur"] * 100,
        "fabric_type":                  ["knit"] * 100,
        "season":                       ["normal"] * 100,
        "destination_tier":             ["Tier-2"] * 100,
        "vendor_reliability":           [0.90] * 100,
        "vendor_is_new":                [False] * 100,
        "sampling_delay_days":          [1] * 100,
        "fabric_arrival_delay_days":    [2] * 100,
        "trims_confirmation_lag_days":  [1] * 100,
        "factory_ncr_count":            [2] * 100,
        "buyer_change_frequency":       [1] * 100,
        "order_qty":                    [200] * 100,
        "is_delayed":                   [False] * 100,
        "is_returned":                  [False] * 100,
    })


def test_corrupt_preserves_row_count():
    """No rows should be added or dropped."""
    df = _sample_frame()
    out = corrupt(df, seed=42)
    assert len(out) == len(df)


def test_corrupt_preserves_outcomes():
    """is_delayed / is_returned are LABELS and must never be corrupted."""
    df = _sample_frame()
    out = corrupt(df, seed=42)
    pd.testing.assert_series_equal(out["is_delayed"], df["is_delayed"],
                                   check_dtype=False)
    pd.testing.assert_series_equal(out["is_returned"], df["is_returned"],
                                   check_dtype=False)


def test_corrupt_produces_some_typos_in_categoricals():
    """At default rate, the categorical columns must have at least one bad value."""
    df = _sample_frame()
    out = corrupt(df, seed=42)
    # vendor_cluster originals are all "Tirupur" — anything else is a typo or blank
    bad = (out["vendor_cluster"] != "Tirupur").sum()
    assert bad > 0


def test_corrupt_produces_some_missing_numerics():
    """At default rate, numeric columns should have at least one NaN."""
    df = _sample_frame()
    out = corrupt(df, seed=42)
    assert out["sampling_delay_days"].isna().sum() > 0


def test_corrupt_with_zero_rate_is_near_identity():
    """At rate=0, almost nothing should change (only the dtype cast remains)."""
    df = _sample_frame()
    out = corrupt(df, seed=42, rate=0.0)
    # vendor_cluster stays Tirupur for every row
    assert (out["vendor_cluster"] == "Tirupur").all()
    # numeric columns stay full (no NaNs at rate 0)
    assert out["sampling_delay_days"].isna().sum() == 0


def test_corrupt_at_higher_rate_corrupts_more():
    """A higher rate should produce more typos than a lower one."""
    df = _sample_frame()
    low_rate_typos = (corrupt(df, seed=42, rate=0.05)["vendor_cluster"] != "Tirupur").sum()
    high_rate_typos = (corrupt(df, seed=42, rate=0.50)["vendor_cluster"] != "Tirupur").sum()
    assert high_rate_typos > low_rate_typos


def test_corrupt_returns_a_copy_not_a_view():
    """The original frame must not be mutated."""
    df = _sample_frame()
    original_first_cluster = df["vendor_cluster"].iloc[0]
    _ = corrupt(df, seed=42)
    assert df["vendor_cluster"].iloc[0] == original_first_cluster
    assert not df["vendor_reliability"].isna().any()


# Suppress unused-import lint for numpy — it's used by the underlying corrupt code.
_ = np
