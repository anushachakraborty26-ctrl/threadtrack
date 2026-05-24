"""
src/action_playbook.py — v2: turn a risk score into a ranked action playbook.

The v1 dashboard shows a number ("0.73 probability of delay") and a one-line
recommendation. v2's response to the critique "predicting the problem is not
solving it" is this module: take an order plus its scores, return a ranked
list of *specific*, *executable* actions a planner can take in 15 seconds.

The rules are deliberately rule-based, not learned — they are a planning
heuristic, transparent and easy to override, and the natural step before any
ML-learned policy. Each action is a dict:

    {action, target, expected_impact, priority}

priority 1 is most urgent. Sort ascending.
"""

from src.rule_scorer import score_order

CLUSTER_FALLBACKS = {
    # When a cluster is in crunch, suggest an alternate from a different one.
    "Tirupur":   {"knit":  ("V05", "Bengaluru"), "woven": ("V09", "Delhi NCR")},
    "Bengaluru": {"knit":  ("V01", "Tirupur"),   "woven": ("V09", "Delhi NCR")},
    "Ludhiana":  {"knit":  ("V05", "Bengaluru"), "woven": ("V09", "Delhi NCR")},
    "Delhi NCR": {"knit":  ("V05", "Bengaluru"), "woven": ("V07", "Ludhiana")},
}


def recommend_actions(order, scores=None):
    """Return a ranked list of actions for one order.

    Parameters
    ----------
    order : dict
        Same shape as score_order() input; optionally vendor_id, destination_city.
    scores : dict, optional
        Output of score_order(). Computed from `order` if not supplied.
    """
    if scores is None:
        scores = score_order(order)

    delay = scores["delay_score"]
    ret = scores["return_score"]
    cluster = order.get("vendor_cluster", "")
    vendor_id = order.get("vendor_id", "this vendor")
    fabric = order.get("fabric_type", "knit")

    actions = []

    # ---- highest priority: clear the buyer-side blocker ----
    if order.get("trims_confirmation_lag_days", 0) >= 3 and delay >= 50:
        actions.append({
            "action": "Escalate trims confirmation with buyer",
            "target": "Buyer / merchandising",
            "expected_impact": "Recovers 2-3 days if cleared in 24 hours",
            "priority": 1,
        })

    # ---- highest priority: reserve fallback capacity if cluster in crunch ----
    if cluster in CLUSTER_FALLBACKS and delay >= 60:
        alt_vendor, alt_cluster = CLUSTER_FALLBACKS[cluster].get(
            fabric, CLUSTER_FALLBACKS[cluster]["knit"])
        actions.append({
            "action": f"Reserve fallback capacity at {alt_vendor} ({alt_cluster})",
            "target": "Sourcing / vendor management",
            "expected_impact": "Caps worst-case slip at +5 days",
            "priority": 1,
        })

    # ---- high priority: lock fabric next lot if mill is slipping ----
    if order.get("fabric_arrival_delay_days", 0) >= 5:
        actions.append({
            "action": "Pre-book next fabric lot; freeze tech-pack now",
            "target": "Fabric sourcing",
            "expected_impact": "Cuts 3-4 days off the next slip",
            "priority": 2,
        })

    # ---- high priority: tighten QC if NCRs are stacking ----
    if order.get("factory_ncr_count", 0) >= 4:
        actions.append({
            "action": f"Add in-line QC + AQL retest at {vendor_id}",
            "target": "Quality team",
            "expected_impact": "Catches ~30% of defects before dispatch",
            "priority": 2,
        })

    # ---- medium priority: tell the customer early if delay is locked in ----
    if delay >= 60:
        actions.append({
            "action": ("Notify customer of revised SLA with a small make-good "
                       "(free shipping or coupon)"),
            "target": "CX / marketing",
            "expected_impact": "Reduces cancellation ~15%, lowers return risk",
            "priority": 2,
        })

    # ---- lower priority: buffer the planner's own dispatch SLA ----
    if 35 <= delay < 60:
        actions.append({
            "action": "Add a 2-day buffer to the dispatch SLA; flag at standup",
            "target": "Planning",
            "expected_impact": "Absorbs likely slip without escalation",
            "priority": 3,
        })

    # ---- returns-side: push prepaid if return risk is high on COD ----
    if ret >= 65 and order.get("payment_mode") == "COD":
        actions.append({
            "action": "Offer a small prepaid incentive at checkout for this SKU",
            "target": "Marketing / CX",
            "expected_impact": ("Converts 10-20% COD → prepaid; halves return "
                                "rate on that slice"),
            "priority": 2,
        })

    # ---- returns-side: sizing tightening for Tier-3 returns ----
    if ret >= 65 and order.get("destination_tier") == "Tier-3":
        actions.append({
            "action": "Boost size guide + add a fit-call CTA for this region",
            "target": "Marketing / catalog",
            "expected_impact": "Sizing-driven returns drop ~10% in Tier-3 cities",
            "priority": 3,
        })

    actions.sort(key=lambda a: a["priority"])

    if not actions:
        actions.append({
            "action": "No action required — order is in the safe band, standard monitoring",
            "target": "Planning",
            "expected_impact": "n/a",
            "priority": 3,
        })

    return actions


def format_playbook(actions):
    """Render the action list as plain-English numbered text."""
    lines = []
    for i, a in enumerate(actions, start=1):
        lines.append(f"  {i}. {a['action']}")
        lines.append(f"     target: {a['target']}  ·  impact: {a['expected_impact']}")
    return "\n".join(lines)


def demo():
    """Print two example playbooks so the rules can be sanity-checked."""
    examples = [
        {
            "label": "High-risk: Tirupur woven, festive, COD, Tier-3, late trims, NCRs",
            "order": {
                "vendor_id": "V03", "vendor_is_new": False,
                "vendor_cluster": "Tirupur", "vendor_reliability": 0.85,
                "fabric_type": "woven", "order_qty": 400,
                "destination_city": "Patna", "destination_tier": "Tier-3",
                "payment_mode": "COD", "season": "festive",
                "sampling_delay_days": 5, "fabric_arrival_delay_days": 7,
                "trims_confirmation_lag_days": 4, "factory_ncr_count": 5,
                "buyer_change_frequency": 2,
            },
        },
        {
            "label": "Low-risk: Bengaluru knit, prepaid, Tier-1, normal season, clean",
            "order": {
                "vendor_id": "V05", "vendor_is_new": False,
                "vendor_cluster": "Bengaluru", "vendor_reliability": 0.93,
                "fabric_type": "knit", "order_qty": 150,
                "destination_city": "Mumbai", "destination_tier": "Tier-1",
                "payment_mode": "Prepaid", "season": "normal",
                "sampling_delay_days": 0, "fabric_arrival_delay_days": 0,
                "trims_confirmation_lag_days": 0, "factory_ncr_count": 0,
                "buyer_change_frequency": 1,
            },
        },
    ]
    for ex in examples:
        scores = score_order(ex["order"])
        actions = recommend_actions(ex["order"], scores)
        print(f"\n— {ex['label']} —")
        print(f"  delay_score = {scores['delay_score']},  "
              f"return_score = {scores['return_score']}")
        print(format_playbook(actions))


if __name__ == "__main__":
    demo()
