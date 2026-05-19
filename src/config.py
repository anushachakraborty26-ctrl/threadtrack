"""
ThreadTrack — synthetic data generation parameters.

Every value here is calibrated from docs/benchmarks.md.
When that file is updated (e.g. when the NIFT professor sends lead-time corrections),
only this file needs changing — no logic code needs to change.

Section references like (§3) point to sections in docs/benchmarks.md.
"""

# =============================================================================
# DATASET SIZE & TIMEFRAME
# =============================================================================

N_ORDERS = 5000  # one fiscal year of orders for a mid-stage D2C menswear brand

START_DATE = "2025-04-01"  # FY25-26 start
END_DATE = "2026-03-31"    # FY25-26 end

RANDOM_SEED = 42  # so the synthetic data is reproducible


# =============================================================================
# VENDOR POOL (§5 §8)
# =============================================================================
# 12 simulated vendors across the 4 major Indian apparel clusters.
# Reliability score = baseline probability of on-time delivery (used to add noise).
# is_new = first-cycle vendor (1.5-2.5x slip risk per §8).

VENDORS = [
    # Tirupur (knit-dominant, 95% capacity utilization — high slip risk)
    {"id": "V01", "cluster": "Tirupur",   "primary_fabric": "knit",  "reliability": 0.92, "size": "large",  "is_new": False},
    {"id": "V02", "cluster": "Tirupur",   "primary_fabric": "knit",  "reliability": 0.88, "size": "medium", "is_new": False},
    {"id": "V03", "cluster": "Tirupur",   "primary_fabric": "knit",  "reliability": 0.85, "size": "small",  "is_new": False},
    {"id": "V04", "cluster": "Tirupur",   "primary_fabric": "knit",  "reliability": 0.90, "size": "medium", "is_new": False},

    # Bengaluru Urban (mixed; closest cluster to Snitch HQ)
    {"id": "V05", "cluster": "Bengaluru", "primary_fabric": "knit",  "reliability": 0.93, "size": "large",  "is_new": False},
    {"id": "V06", "cluster": "Bengaluru", "primary_fabric": "knit",  "reliability": 0.89, "size": "medium", "is_new": False},

    # Ludhiana (knits + wovens, winter-heavy)
    {"id": "V07", "cluster": "Ludhiana",  "primary_fabric": "knit",  "reliability": 0.87, "size": "medium", "is_new": False},
    {"id": "V08", "cluster": "Ludhiana",  "primary_fabric": "woven", "reliability": 0.84, "size": "small",  "is_new": False},

    # Delhi NCR (woven-dominant, formal menswear)
    {"id": "V09", "cluster": "Delhi NCR", "primary_fabric": "woven", "reliability": 0.86, "size": "medium", "is_new": False},
    {"id": "V10", "cluster": "Delhi NCR", "primary_fabric": "woven", "reliability": 0.82, "size": "small",  "is_new": False},

    # New vendors (first-cycle slip risk per §8)
    {"id": "V11", "cluster": "Tirupur",   "primary_fabric": "knit",  "reliability": 0.75, "size": "small",  "is_new": True},
    {"id": "V12", "cluster": "Bengaluru", "primary_fabric": "knit",  "reliability": 0.78, "size": "small",  "is_new": True},
]

# Vendor concentration: top-3 vendors carry ~60% of volume (§8)
# V01 (Tirupur large), V02 (Tirupur medium), V05 (Bengaluru large) = top 3
VENDOR_WEIGHTS = {
    "V01": 0.25,
    "V02": 0.18,
    "V05": 0.17,
    "V03": 0.08,
    "V04": 0.08,
    "V06": 0.06,
    "V07": 0.05,
    "V08": 0.04,
    "V09": 0.04,
    "V10": 0.03,
    "V11": 0.01,  # new vendor, small share
    "V12": 0.01,  # new vendor, small share
}
# Sanity check (must sum to 1.0); the generator will assert this.


# =============================================================================
# CLUSTER CAPACITY UTILIZATION (§5)
# =============================================================================
# Tirupur currently 95% per TEA data — major delay amplifier
# Other clusters not at peak; used as multipliers in lead-time calculation

CLUSTER_UTILIZATION = {
    "Tirupur":   0.95,  # crisis zone
    "Bengaluru": 0.82,  # tight
    "Ludhiana":  0.78,  # comfortable
    "Delhi NCR": 0.75,  # comfortable
}


# =============================================================================
# FABRIC MIX (§3 §4)
# =============================================================================
# Snitch is knit-heavy menswear (T-shirts, polos, hoodies dominate)
# 75/25 split is calibrated to Snitch-style brand, not India macro
# (India macro is 49% knit per Business Standard but D2C menswear skews knit)

FABRIC_MIX = {
    "knit":  0.75,
    "woven": 0.25,
}

GARMENT_CATEGORIES = {
    "knit":  ["t-shirt", "polo", "hoodie", "sweatshirt", "henley"],
    "woven": ["shirt", "trouser", "chinos", "overshirt", "denim-jacket"],
}


# =============================================================================
# DESTINATION TIER MIX (§2)
# =============================================================================
# Unicommerce 2026: 66% of FY26 incremental orders from non-metro
# We use 34/36/30 to roughly match while keeping Tier-1 substantial

TIER_MIX = {
    "Tier-1": 0.34,
    "Tier-2": 0.36,
    "Tier-3": 0.30,
}

# Sample destination cities by tier (will be picked randomly within tier)
CITIES_BY_TIER = {
    "Tier-1": ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata"],
    "Tier-2": ["Pune", "Ahmedabad", "Jaipur", "Lucknow", "Coimbatore", "Indore", "Kochi", "Chandigarh", "Surat", "Vadodara"],
    "Tier-3": ["Patna", "Bhubaneswar", "Guwahati", "Mysuru", "Vijayawada", "Dehradun", "Raipur", "Ranchi", "Jodhpur", "Nagpur", "Tiruchirappalli", "Madurai"],
}


# =============================================================================
# PAYMENT MIX (§3)
# =============================================================================
# D2C value-tier menswear is COD-heavy
# COD share aligns with Tier-2/3 mix (COD dominates in non-metro)

PAYMENT_MIX = {
    "COD":     0.60,
    "Prepaid": 0.40,
}


# =============================================================================
# ORDER QUANTITY (per PO)
# =============================================================================
# D2C menswear with weekly drops: small batches per PO
# Mean ~200 pieces, range 50-500 (truncated at min/max)

ORDER_QTY_MEAN = 200
ORDER_QTY_STD  = 80
ORDER_QTY_MIN  = 50
ORDER_QTY_MAX  = 500


# =============================================================================
# LEAD TIMES — by stage, by fabric (§7) [ESTIMATE — pending professor reply]
# =============================================================================
# Format: (mean_days, std_dev_days)
# Generator will sample from a normal distribution and clip to reasonable bounds.
# Replace these when professor validates.

LEAD_TIMES = {
    "knit": {
        "fabric_sourcing": (7.5, 1.5),   # §7: 5-10 days
        "cut_sew":         (6.5, 1.0),   # §7: 5-8 days
        "finishing":       (3.0, 0.7),   # §7: 2-4 days
        "factory_to_dc":   (2.5, 0.5),   # §7: 2-3 days
    },
    "woven": {
        "fabric_sourcing": (14.0, 2.5),  # §7: 10-18 days
        "cut_sew":         (10.0, 1.5),  # §7: 8-12 days
        "finishing":       (5.0, 0.7),   # §7: 4-6 days
        "factory_to_dc":   (3.0, 0.7),   # §7: 2-4 days
    },
}

# Last-mile delivery by tier (§7)
LAST_MILE = {
    "Tier-1": (1.5, 0.4),
    "Tier-2": (3.0, 0.7),
    "Tier-3": (5.0, 1.2),
}


# =============================================================================
# SEASONAL AMPLIFIERS (§7)
# =============================================================================
# Multiplier applied to total lead time based on the season the PO was placed.
# Festive (Sep-Nov): +20-40% across the board
# Monsoon (Jun-Sep): +30-50% on wovens, +10% on knits
# Wedding overlaps with festive in our simple model.

SEASONAL_AMPLIFIERS = {
    "festive": {"knit": 1.18, "woven": 1.20},  # softened from 1.30 (was over-stacking)
    "monsoon": {"knit": 1.05, "woven": 1.22},  # softened from 1.10/1.40
    "normal":  {"knit": 1.00, "woven": 1.00},
}

# Which month → which season (Indian fiscal calendar)
SEASON_BY_MONTH = {
    1:  "normal",   2: "normal",   3: "normal",
    4:  "normal",   5: "normal",
    6:  "monsoon",  7: "monsoon",  8: "monsoon",
    9:  "festive", 10: "festive", 11: "festive",
    12: "normal",
}


# =============================================================================
# DEMAND VOLUME PATTERN
# =============================================================================
# Festive months see 3x normal order volume (§2)
# Used by the generator to skew PO date distribution

FESTIVE_VOLUME_MULTIPLIER = 1.5  # softened from 3.0; the 3x applies to specific sale days, not whole season


# =============================================================================
# DELAY DEFINITION
# =============================================================================
# An order is "delayed" if actual_lead_time > planned_lead_time + buffer

DELAY_BUFFER_DAYS = 5  # was 3 — industry tolerance for D2C menswear is 4-5 days slip


# =============================================================================
# RETURN RATE CALIBRATION (§3)
# =============================================================================
# Base fashion return rate = 22% (GrowwwTech State of Indian D2C 2026)
# Multipliers applied for risk factors. Final return probability is clipped to [0, 0.95].

RETURN_RATE_BASE = 0.22

RETURN_MULTIPLIERS = {
    "cod_normal":   1.25,  # softened from 1.4 (multipliers were stacking too high)
    "cod_festive":  1.55,  # softened from 2.0
    "tier_3":       1.20,  # softened from 1.3
    "delayed":      1.25,  # softened from 1.5 (delay → returns causal link, but gentler)
    "new_vendor":   1.15,  # softened from 1.2
}


# =============================================================================
# OUTPUT
# =============================================================================

OUTPUT_PATH = "data/synthetic_pos.csv"
