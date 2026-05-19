"""
src/generate_data.py — Synthetic PO dataset generator for ThreadTrack.

Reads parameters from src/config.py, generates N_ORDERS synthetic purchase orders
calibrated to industry benchmarks (docs/benchmarks.md), writes to data/synthetic_pos.csv.

Each order goes through:
  1. Date selection (with festive volume skew)
  2. Vendor selection (weighted by concentration)
  3. Fabric + garment category
  4. Destination tier + city
  5. Payment mode
  6. Order quantity
  7. Planned lead time calculation (sum of stage means)
  8. Actual lead time calculation (planned + noise + amplifiers)
  9. Delay determination (actual > planned + buffer)
 10. Return probability (base rate × stacked multipliers)
 11. Return determination (random draw against probability)

Run from project root with venv active:
    python -m src.generate_data
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src import config


# =============================================================================
# SETUP
# =============================================================================

def setup_seed():
    """Seed both random and numpy so the dataset is reproducible."""
    random.seed(config.RANDOM_SEED)
    np.random.seed(config.RANDOM_SEED)


# =============================================================================
# PICK FUNCTIONS — each returns one attribute for one order
# =============================================================================

def pick_po_date(date_range):
    """
    Pick a PO date with festive-season volume skew.
    Festive months (Sep-Nov) get 3x weight per benchmarks §2.
    """
    weights = []
    for d in date_range:
        season = config.SEASON_BY_MONTH[d.month]
        if season == "festive":
            weights.append(config.FESTIVE_VOLUME_MULTIPLIER)
        else:
            weights.append(1.0)
    return random.choices(date_range, weights=weights, k=1)[0]


def pick_vendor():
    """Pick a vendor by weighted random based on VENDOR_WEIGHTS (top-3 = ~60%)."""
    vendor_ids = list(config.VENDOR_WEIGHTS.keys())
    weights = list(config.VENDOR_WEIGHTS.values())
    chosen_id = random.choices(vendor_ids, weights=weights, k=1)[0]
    # Look up the full vendor dict by ID
    for v in config.VENDORS:
        if v["id"] == chosen_id:
            return v


def pick_fabric_for_vendor(vendor):
    """
    Vendors stick to their primary fabric 80% of the time.
    20% cross-over reflects real-world flexibility.
    """
    if random.random() < 0.8:
        return vendor["primary_fabric"]
    return "woven" if vendor["primary_fabric"] == "knit" else "knit"


def pick_garment_category(fabric):
    """Pick a random garment category from the fabric's category list."""
    return random.choice(config.GARMENT_CATEGORIES[fabric])


def pick_destination():
    """Pick a destination tier (by TIER_MIX weights) then a city within that tier."""
    tiers = list(config.TIER_MIX.keys())
    weights = list(config.TIER_MIX.values())
    tier = random.choices(tiers, weights=weights, k=1)[0]
    city = random.choice(config.CITIES_BY_TIER[tier])
    return tier, city


def pick_payment_mode():
    """Pick payment mode (60% COD, 40% Prepaid for D2C menswear value tier)."""
    modes = list(config.PAYMENT_MIX.keys())
    weights = list(config.PAYMENT_MIX.values())
    return random.choices(modes, weights=weights, k=1)[0]


def pick_order_qty():
    """Order quantity from a normal distribution, clipped to min/max bounds."""
    qty = int(np.random.normal(config.ORDER_QTY_MEAN, config.ORDER_QTY_STD))
    return max(config.ORDER_QTY_MIN, min(config.ORDER_QTY_MAX, qty))


# =============================================================================
# LEAD TIME CALCULATIONS
# =============================================================================

def calculate_planned_lead_time(fabric, tier):
    """
    Sum of stage means (no variance) + last mile mean.
    This is what the buyer 'promises' — the planned delivery date.
    """
    total = 0.0
    for stage, (mean, _std) in config.LEAD_TIMES[fabric].items():
        total += mean
    last_mile_mean, _ = config.LAST_MILE[tier]
    total += last_mile_mean
    return round(total)


def calculate_actual_lead_time(fabric, tier, vendor, season):
    """
    Actual lead time = planned WITH noise + real-world amplifiers.

    Amplifiers stacked in this order:
      1. Sample each stage WITH variance (normal distribution)
      2. Seasonal amplifier (festive +30%, monsoon +10/40%, normal 1.0)
      3. Cluster utilization penalty (non-linear above 0.85)
      4. Vendor reliability noise (lower reliability = wider variance)
      5. New vendor amplifier (first-cycle slip: 1.8x)
    """
    total = 0.0

    # 1. Sample each production stage with noise
    for stage, (mean, std) in config.LEAD_TIMES[fabric].items():
        total += np.random.normal(mean, std)

    # Sample last mile with noise
    lm_mean, lm_std = config.LAST_MILE[tier]
    total += np.random.normal(lm_mean, lm_std)

    # 2. Apply seasonal amplifier
    total *= config.SEASONAL_AMPLIFIERS[season][fabric]

    # 3. Cluster utilization penalty (non-linear above 0.85, but gentler)
    util = config.CLUSTER_UTILIZATION[vendor["cluster"]]
    if util > 0.85:
        util_amp = 1.0 + (util - 0.85) * 0.8  # 0.95 util → ~1.08x (was 1.20x)
        total *= util_amp

    # 4. Vendor reliability noise (can go either way — sometimes early, sometimes late)
    total += np.random.normal(0, (1 - vendor["reliability"]) * 4)

    # 5. New vendor amplifier (first-cycle slip, but not catastrophic)
    if vendor["is_new"]:
        total *= 1.30  # was 1.8 — too aggressive when stacked with other amps

    # Clip to a sensible minimum (no order takes <5 days end-to-end)
    return max(5, round(total))


# =============================================================================
# RETURN PROBABILITY
# =============================================================================

def calculate_return_probability(payment_mode, season, tier, is_delayed, vendor):
    """
    Stack RETURN_MULTIPLIERS on top of the base 22% fashion D2C rate.
    Capped at 95% (realistic ceiling — no category returns at 100%).
    """
    prob = config.RETURN_RATE_BASE

    # COD multiplier (festive amplifier when applicable)
    if payment_mode == "COD":
        if season == "festive":
            prob *= config.RETURN_MULTIPLIERS["cod_festive"]
        else:
            prob *= config.RETURN_MULTIPLIERS["cod_normal"]

    # Tier-3 amplifier (lower address quality, more COD)
    if tier == "Tier-3":
        prob *= config.RETURN_MULTIPLIERS["tier_3"]

    # Delayed orders return more (the delay → return causal link)
    if is_delayed:
        prob *= config.RETURN_MULTIPLIERS["delayed"]

    # New vendor quality variance
    if vendor["is_new"]:
        prob *= config.RETURN_MULTIPLIERS["new_vendor"]

    return min(0.95, prob)


# =============================================================================
# ORDER ASSEMBLY
# =============================================================================

def generate_one_order(date_range):
    """Generate one complete synthetic PO. Returns a dict of column values."""
    po_date = pick_po_date(date_range)
    vendor = pick_vendor()
    fabric = pick_fabric_for_vendor(vendor)
    garment = pick_garment_category(fabric)
    tier, city = pick_destination()
    payment = pick_payment_mode()
    qty = pick_order_qty()
    season = config.SEASON_BY_MONTH[po_date.month]

    planned = calculate_planned_lead_time(fabric, tier)
    actual = calculate_actual_lead_time(fabric, tier, vendor, season)

    delay_days = actual - planned
    is_delayed = delay_days > config.DELAY_BUFFER_DAYS

    return_prob = calculate_return_probability(payment, season, tier, is_delayed, vendor)
    is_returned = random.random() < return_prob

    delivery_date = po_date + timedelta(days=actual)

    return {
        "po_id": None,  # filled in main()
        "po_date": po_date.strftime("%Y-%m-%d"),
        "vendor_id": vendor["id"],
        "vendor_cluster": vendor["cluster"],
        "vendor_is_new": vendor["is_new"],
        "vendor_reliability": vendor["reliability"],
        "fabric_type": fabric,
        "garment_category": garment,
        "order_qty": qty,
        "destination_city": city,
        "destination_tier": tier,
        "payment_mode": payment,
        "season": season,
        "planned_lead_time_days": planned,
        "actual_lead_time_days": actual,
        "delivery_date": delivery_date.strftime("%Y-%m-%d"),
        "delay_days": delay_days,
        "is_delayed": is_delayed,
        "return_probability": round(return_prob, 3),
        "is_returned": is_returned,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("ThreadTrack synthetic data generator")
    print("=" * 50)

    setup_seed()

    # Build full date range
    start = datetime.strptime(config.START_DATE, "%Y-%m-%d")
    end = datetime.strptime(config.END_DATE, "%Y-%m-%d")
    date_range = []
    current = start
    while current <= end:
        date_range.append(current)
        current += timedelta(days=1)

    print(f"Generating {config.N_ORDERS} POs from {config.START_DATE} to {config.END_DATE}...")

    orders = []
    for i in range(config.N_ORDERS):
        order = generate_one_order(date_range)
        order["po_id"] = f"PO{i+1:06d}"  # PO000001, PO000002, ...
        orders.append(order)

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{config.N_ORDERS}")

    # Convert to DataFrame, sort by po_date, save
    df = pd.DataFrame(orders)
    df = df.sort_values("po_date").reset_index(drop=True)
    df.to_csv(config.OUTPUT_PATH, index=False)

    # Summary
    print()
    print(f"Saved to {config.OUTPUT_PATH}")
    print()
    print("Quick stats:")
    print(f"  Total orders:           {len(df)}")
    print(f"  Delayed orders:         {df['is_delayed'].sum()} ({df['is_delayed'].mean() * 100:.1f}%)")
    print(f"  Returned orders:        {df['is_returned'].sum()} ({df['is_returned'].mean() * 100:.1f}%)")
    print(f"  Avg planned lead time:  {df['planned_lead_time_days'].mean():.1f} days")
    print(f"  Avg actual lead time:   {df['actual_lead_time_days'].mean():.1f} days")
    print(f"  Avg delay:              {df['delay_days'].mean():.1f} days")


if __name__ == "__main__":
    main()
