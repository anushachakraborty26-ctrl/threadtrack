"""Tests for src/action_playbook.recommend_actions."""

from src.action_playbook import recommend_actions

LOW_RISK_ORDER = {
    "vendor_id": "V05", "vendor_is_new": False, "vendor_cluster": "Bengaluru",
    "vendor_reliability": 0.93, "fabric_type": "knit", "order_qty": 150,
    "destination_tier": "Tier-1", "payment_mode": "Prepaid", "season": "normal",
    "sampling_delay_days": 0, "fabric_arrival_delay_days": 0,
    "trims_confirmation_lag_days": 0, "factory_ncr_count": 0,
    "buyer_change_frequency": 1,
}

HIGH_RISK_ORDER = {
    "vendor_id": "V03", "vendor_is_new": False, "vendor_cluster": "Tirupur",
    "vendor_reliability": 0.85, "fabric_type": "woven", "order_qty": 400,
    "destination_tier": "Tier-3", "payment_mode": "COD", "season": "festive",
    "sampling_delay_days": 5, "fabric_arrival_delay_days": 7,
    "trims_confirmation_lag_days": 4, "factory_ncr_count": 5,
    "buyer_change_frequency": 2,
}


def test_low_risk_returns_no_action():
    """A low-risk order should fall through to the 'no action' default."""
    actions = recommend_actions(LOW_RISK_ORDER)
    assert len(actions) == 1
    assert "No action required" in actions[0]["action"]


def test_high_risk_returns_multiple_actions():
    """A worst-case order should fire several rules."""
    actions = recommend_actions(HIGH_RISK_ORDER)
    assert len(actions) >= 5


def test_actions_sorted_by_priority():
    """Returned actions must be sorted ascending by priority (most urgent first)."""
    actions = recommend_actions(HIGH_RISK_ORDER)
    priorities = [a["priority"] for a in actions]
    assert priorities == sorted(priorities)


def test_every_action_has_required_keys():
    """Each action must carry action, target, expected_impact, priority."""
    for order in (LOW_RISK_ORDER, HIGH_RISK_ORDER):
        for a in recommend_actions(order):
            assert set(a.keys()) >= {"action", "target", "expected_impact", "priority"}


def test_trims_escalation_fires_when_lag_is_high():
    """Late trims confirmation + high delay should produce the trims escalation."""
    order = dict(HIGH_RISK_ORDER)
    actions = recommend_actions(order)
    texts = " ".join(a["action"] for a in actions)
    assert "trims confirmation" in texts.lower()


def test_fallback_capacity_suggestion_for_tirupur_high_delay():
    """High-risk Tirupur orders should surface a fallback-vendor suggestion."""
    actions = recommend_actions(HIGH_RISK_ORDER)
    texts = " ".join(a["action"] for a in actions)
    assert "fallback" in texts.lower() or "V09" in texts or "V05" in texts
