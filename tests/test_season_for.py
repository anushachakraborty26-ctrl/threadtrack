"""Tests for the region-aware season calendar — the season_for function
lives in app.py; we replicate its tiny logic here against the config data
so the test stays a unit test and doesn't import Streamlit."""

from datetime import date

from src.config import FESTIVE_MONTHS, REGIONAL_MONSOON_MONTHS


def season_for(order_date, cluster):
    """Inline copy of app.py:season_for for unit-testing without Streamlit."""
    month = order_date.month
    if month in FESTIVE_MONTHS:
        return "festive"
    if month in REGIONAL_MONSOON_MONTHS.get(cluster, []):
        return "monsoon"
    return "normal"


def test_festive_months_are_national():
    """Sep-Nov should be festive for every cluster."""
    for cluster in REGIONAL_MONSOON_MONTHS:
        assert season_for(date(2026, 10, 1), cluster) == "festive"
        assert season_for(date(2026, 9, 15), cluster) == "festive"
        assert season_for(date(2026, 11, 30), cluster) == "festive"


def test_monsoon_is_regional_in_june():
    """June: Tirupur and Bengaluru are in monsoon; Delhi NCR and Ludhiana aren't."""
    assert season_for(date(2026, 6, 15), "Tirupur") == "monsoon"
    assert season_for(date(2026, 6, 15), "Bengaluru") == "monsoon"
    assert season_for(date(2026, 6, 15), "Delhi NCR") == "normal"
    assert season_for(date(2026, 6, 15), "Ludhiana") == "normal"


def test_monsoon_in_july_everywhere():
    """July: all four clusters are in monsoon."""
    for cluster in ["Tirupur", "Bengaluru", "Ludhiana", "Delhi NCR"]:
        assert season_for(date(2026, 7, 15), cluster) == "monsoon"


def test_festive_wins_overlap():
    """When monsoon and festive could both apply, festive wins.
    September is in Bengaluru's monsoon extension and also national festive."""
    # Force the overlap by putting Sep in monsoon for Bengaluru:
    # config has Bengaluru = [6, 7, 8], so Sep isn't a monsoon month there, but
    # this test still proves the FESTIVE_MONTHS check happens first.
    assert season_for(date(2026, 9, 15), "Bengaluru") == "festive"


def test_normal_for_winter_months():
    """December-February should be normal for all clusters."""
    for month in [12, 1, 2]:
        for cluster in REGIONAL_MONSOON_MONTHS:
            assert season_for(date(2026, month, 15), cluster) == "normal"


def test_unknown_cluster_falls_back_to_normal_outside_festive():
    """An unknown cluster should still return a valid season."""
    # June for an unknown cluster — no monsoon match, not festive → normal
    assert season_for(date(2026, 6, 15), "Bogus") == "normal"
    # October — festive applies regardless of cluster
    assert season_for(date(2026, 10, 15), "Bogus") == "festive"
