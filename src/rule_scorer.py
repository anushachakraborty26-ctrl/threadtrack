"""
src/rule_scorer.py — Rule-based risk scorer for ThreadTrack.

Takes one purchase order and returns:
  - delay_score   (0-100)
  - return_score  (0-100)
  - delay_reasons  (list of plain-English strings)
  - return_reasons (list of plain-English strings)

The rubric (weights) was designed from NIFT industrial engineering domain
knowledge + the cited benchmarks in docs/benchmarks.md.
Every weight is explainable — see docs/scoring_rubric.md.

THE APPROVED RUBRIC (reference while writing the function):

  BASELINE:                       delay = 10,  return = 15

  vendor_is_new = True:           delay = 22,  return = 10
  vendor_cluster = Tirupur:       delay = 14,  return = 3
  vendor_cluster = Bengaluru:     delay = 4,   return = 0
  vendor_reliability < 0.85:      delay = 12,  return = 6
  fabric_type = woven:            delay = 12,  return = 5
  order_qty > 350:                delay = 8,   return = 0
  destination_tier = Tier-3:      delay = 10,  return = 14
  destination_tier = Tier-2:      delay = 5,   return = 7
  payment_mode = COD:             delay = 2,   return = 22
  season = festive:               delay = 12,  return = 10
  season = monsoon:               delay = 8,   return = 3

  INTERACTIONS:
  monsoon AND woven:              delay = 10,  return = 3
  festive AND COD:                delay = 0,   return = 14
  new vendor AND Tirupur:         delay = 10,  return = 2
"""


def score_order(order):
    """
    Score one order's delay and return risk.

    Parameters
    ----------
    order : dict
        One purchase order. Expected v1 keys:
        vendor_is_new (bool), vendor_cluster (str), vendor_reliability (float),
        fabric_type (str), order_qty (int), destination_tier (str),
        payment_mode (str), season (str).

        Optional v2 upstream-operational keys (additional factors fire if
        present; absent values are treated as best-case defaults so the
        scorer stays backward-compatible with v1 data):
        sampling_delay_days (int), fabric_arrival_delay_days (int),
        trims_confirmation_lag_days (int), factory_ncr_count (int),
        buyer_change_frequency (int, 1-3).

    Returns
    -------
    dict
        Keys: delay_score, return_score, delay_reasons, return_reasons
    """
    # --- Baseline: every order starts here ---
    delay_score = 10
    return_score = 15
    delay_reasons = []
    return_reasons = []

    # =========================================================================
    # SINGLE-FACTOR RULES
    # =========================================================================

    # --- Factor 1: new vendor (TEMPLATE — study this pattern carefully) ---
    if order["vendor_is_new"]:
        delay_score += 22
        return_score += 10
        delay_reasons.append("New vendor — first-cycle slip risk (+22 delay)")
        return_reasons.append("New vendor — quality variance (+10 return)")

    # --- Factor 2: vendor cluster = Tirupur ---
    if order["vendor_cluster"] == "Tirupur":
        delay_score += 14
        return_score += 3
        delay_reasons.append("Vendor in Tirupur — higher slip risk (+14 delay)")
        return_reasons.append("Vendor in Tirupur — slightly higher return risk (+3 return)")

    # --- Factor 3: vendor cluster = Bengaluru ---
    if order["vendor_cluster"] == "Bengaluru":
        delay_score += 4
        delay_reasons.append("Vendor in Bengaluru — moderate slip risk (+4 delay)")

    # --- Factor 4: vendor reliability below 0.85 ---
    if order["vendor_reliability"] < 0.85:
        delay_score += 12
        return_score += 6
        delay_reasons.append("Vendor reliability below 0.85 — higher slip risk (+12 delay)")
        return_reasons.append("Vendor reliability below 0.85 — higher return risk (+6 return)")

    # --- Factor 5: fabric type = woven ---
    if order["fabric_type"] == "woven":
        delay_score += 12
        return_score += 5
        delay_reasons.append("Fabric type is woven — moderate slip risk (+12 delay)")
        return_reasons.append("Fabric type is woven — moderate return risk (+5 return)")

    # --- Factor 6: order quantity above 350 ---
    if order["order_qty"] > 350:
        delay_score += 8
        delay_reasons.append("Order quantity above 350 — higher slip risk (+8 delay)")
    # Note: order_qty return weight is 0 — only append a delay reason.

    # --- Factor 7: destination tier = Tier-3 ---
    if order["destination_tier"] == "Tier-3":
        delay_score += 10
        return_score += 14
        delay_reasons.append("Tier-3 destination — last-mile delivery risk (+10 delay)")
        return_reasons.append("Tier-3 destination — address quality / COD prevalence (+14 return)")

    # --- Factor 8: destination tier = Tier-2 ---
    if order["destination_tier"] == "Tier-2":
        delay_score += 5
        return_score += 7
        delay_reasons.append("Tier-2 destination — moderate last-mile risk (+5 delay)")
        return_reasons.append("Tier-2 destination — moderate return risk (+7 return)")

    # --- Factor 9: payment mode = COD ---
    if order["payment_mode"] == "COD":
        delay_score += 2
        return_score += 22
        delay_reasons.append("COD payment — minor delivery friction (+2 delay)")
        return_reasons.append("COD payment — major return driver, ~4x prepaid (+22 return)")

    # --- Factor 10: season = festive ---
    if order["season"] == "festive":
        delay_score += 12
        return_score += 10
        delay_reasons.append("Festive season — capacity-constrained (+12 delay)")
        return_reasons.append("Festive season — elevated return rate (+10 return)")

    # --- Factor 11: season = monsoon ---
    if order["season"] == "monsoon":
        delay_score += 8
        return_score += 3
        delay_reasons.append("Monsoon season — transport disruption (+8 delay)")
        return_reasons.append("Monsoon season — slightly elevated returns (+3 return)")

    # =========================================================================
    # INTERACTION RULES (bonus points when two factors combine)
    # =========================================================================

    # --- Factor 12: monsoon AND woven ---
    if order["season"] == "monsoon" and order["fabric_type"] == "woven":
        delay_score += 10
        return_score += 3
        delay_reasons.append("Monsoon + woven — compounded transport risk (+10 delay)")
        return_reasons.append("Monsoon + woven — compounded return risk (+3 return)")

    # --- Factor 13: festive AND COD ---
    if order["season"] == "festive" and order["payment_mode"] == "COD":
        return_score += 14
        return_reasons.append("Festive + COD — 58% festive COD return rate (+14 return)")
        # delay weight is 0 — this interaction only drives returns

    # --- Factor 14: new vendor AND Tirupur ---
    if order["vendor_is_new"] and order["vendor_cluster"] == "Tirupur":
        delay_score += 10
        return_score += 2
        delay_reasons.append("New vendor in Tirupur — compounding capacity risk (+10 delay)")
        return_reasons.append("New vendor in Tirupur — compounding return risk (+2 return)")

    # =========================================================================
    # v2 UPSTREAM OPERATIONAL FACTORS (16-21)
    # =========================================================================
    # The signals planners actually watch day to day. Backward-compatible —
    # missing on v1 rows means the factor does not fire (uses .get(default)).

    # --- Factor 16: sampling delay 3+ days ---
    if order.get("sampling_delay_days", 0) >= 3:
        delay_score += 6
        delay_reasons.append(
            "Sampling delay 3+ days — production pushed back (+6 delay)")

    # --- Factor 17: fabric arrival delay 5+ days ---
    if order.get("fabric_arrival_delay_days", 0) >= 5:
        delay_score += 8
        delay_reasons.append(
            "Fabric mill missed date by 5+ days — cut/sew starts late (+8 delay)")

    # --- Factor 18: trims confirmation lag 3+ days ---
    if order.get("trims_confirmation_lag_days", 0) >= 3:
        delay_score += 5
        return_score += 6
        delay_reasons.append(
            "Trims confirmation 3+ days late — buyer-side bottleneck (+5 delay)")
        return_reasons.append(
            "Late trims confirmation — last-minute rework raises return risk (+6 return)")

    # --- Factor 19: factory NCR count 4+ ---
    if order.get("factory_ncr_count", 0) >= 4:
        delay_score += 3
        return_score += 14
        delay_reasons.append(
            "Factory has 4+ recent NCRs — quality backlog (+3 delay)")
        return_reasons.append(
            "Factory has 4+ recent NCRs — elevated quality return risk (+14 return)")

    # --- Factor 20: buyer-change frequency = frequent (level 3) ---
    if order.get("buyer_change_frequency", 1) == 3:
        delay_score += 6
        return_score += 10
        delay_reasons.append(
            "Buyer changes trims frequently — late-stage rework risk (+6 delay)")
        return_reasons.append(
            "Buyer changes trims frequently — quality risk on delivered goods (+10 return)")

    # --- Factor 21: sampling delay AND first-cycle vendor (compounding) ---
    if order.get("sampling_delay_days", 0) >= 3 and order.get("vendor_is_new"):
        delay_score += 6
        delay_reasons.append(
            "Sampling delay on a first-cycle vendor — compounding risk (+6 delay)")

    # --- Factor 15: predicted delay feeds return risk ---
    # delay_score is a PREDICTION computed above — known at order time, not a
    # future outcome. Using it as a return signal is legitimate (no leakage).

    if delay_score >= 60:
        return_score += 15
        return_reasons.append("High predicted delay risk — delayed orders return more (+15 return)")
    elif delay_score >= 40:
        return_score += 8
        return_reasons.append("Moderate predicted delay risk — elevated return risk (+8 return)")
    # =========================================================================
    # CAP SCORES AT 100
    # =========================================================================
    delay_score = min(100, delay_score)
    return_score = min(100, return_score)

    return {
        "delay_score": delay_score,
        "return_score": return_score,
        "delay_reasons": delay_reasons,
        "return_reasons": return_reasons,
    }
