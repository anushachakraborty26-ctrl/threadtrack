# ThreadTrack Risk Scoring Rubric

The rule-based layer of ThreadTrack. Every purchase order is scored 0-100 for **delay risk** and 0-100 for **return risk**, with a plain-English reason attached to every point added.

## Why a rule-based layer at all?

ThreadTrack is a two-tier model: this transparent rule-based scorer + an ML classifier (Phase 4). The rule layer exists because:

- **Explainability.** A buying merchant can read exactly *why* an order was flagged. ML alone is a black box; buyers don't act on predictions they can't interrogate.
- **No training data required.** The rubric works from domain knowledge on day one.
- **Auditability.** Every weight traces to a cited benchmark in `benchmarks.md` or to documented industrial-engineering reasoning.

The weights were designed by a NIFT industrial engineering student, calibrated against the cited industry benchmarks, and tuned against observed model behaviour.

## How scoring works

1. Every order starts at a **baseline** (delay 10, return 15).
2. Each risk **factor** that applies adds points to delay, return, or both.
3. **Interaction factors** add bonus points when two conditions combine.
4. Final scores are **capped at 100**.
5. Scores bucket into bands: **Low (0-35), Medium (35-65), High (65-100)**.

Crucial design rule: the scorer uses **only information known at order-placement time**. It never uses actual delivery dates, actual delays, or actual returns — those are future outcomes. Using them would be data leakage.

## The factors

| # | Factor | Condition | Delay pts | Return pts | Reasoning & source |
|---|---|---|---|---|---|
| Baseline | — | every order | 10 | 15 | Starting point; return baseline higher because fashion D2C base return rate is 22% (§3) |
| 1 | New vendor | `vendor_is_new` | +22 | +10 | New vendors slip 1.5-2.5x in first cycle (§8). Largest single delay weight. |
| 2 | Tirupur cluster | `cluster == Tirupur` | +14 | +3 | Tirupur at 95% capacity utilization — crisis zone (§5) |
| 3 | Bengaluru cluster | `cluster == Bengaluru` | +4 | 0 | 82% utilization — mild. No direct return effect. |
| 4 | Low reliability | `reliability < 0.85` | +12 | +6 | Lower-reliability vendors miss SLAs more; quality variance drives some returns |
| 5 | Woven fabric | `fabric == woven` | +12 | +5 | Wovens have longer production cycles (§7); mildly fit-sensitive |
| 6 | Large order | `order_qty > 350` | +8 | 0 | Big orders strain vendor capacity (delay). Quantity does not drive per-order returns. |
| 7 | Tier-3 destination | `tier == Tier-3` | +10 | +14 | Last-mile delivery weaker in Tier-3; address quality + COD prevalence drive returns (§3 §5) |
| 8 | Tier-2 destination | `tier == Tier-2` | +5 | +7 | Moderate version of Tier-3 effects |
| 9 | COD payment | `payment == COD` | +2 | +22 | COD returns ~4x prepaid (§3). Largest single return weight. Minimal delay effect. |
| 10 | Festive season | `season == festive` | +12 | +10 | Festive capacity squeeze (§7); elevated return rates (§3) |
| 11 | Monsoon season | `season == monsoon` | +8 | +3 | Transport disruption (§7); minor return effect |

## Interaction factors

Interactions add **bonus** points when two conditions combine — capturing that the combination is worse than the sum of the parts.

| # | Interaction | Delay pts | Return pts | Reasoning |
|---|---|---|---|---|
| 12 | Monsoon AND woven | +10 | +3 | Monsoon transport disruption hits woven supply chains hardest (§7) |
| 13 | Festive AND COD | 0 | +14 | Festive COD return rate hits 58% vs <15% prepaid (§3). Return-only interaction. |
| 14 | New vendor AND Tirupur | +10 | +2 | A new vendor inside a 95%-utilization cluster compounds capacity risk |

## Factor 15 — prediction chaining

After all 14 factors, a final rule feeds the **predicted delay score** into the return score:

- If `delay_score >= 60`: return +15
- Else if `delay_score >= 40`: return +8

**Why this is legitimate (not leakage):** the scorer cannot use the *actual* delay outcome — but it just *computed* `delay_score`, a prediction available at order time. Delayed orders return ~1.4x more (the delay → return causal link, confirmed in EDA). Factor 15 captures that pathway using the prediction, not the outcome.

## v2 — upstream operational factors (16–21)

v2 added five operational signals planners actually watch day to day. Each is sampled per order in the generator and amplifies the actual lead time and return probability, so the data carries genuine predictive signal. These factors are **backward-compatible** — they only fire when the new keys are present, so v1 rows continue to score the v1 way.

| # | Factor | Condition | Delay pts | Return pts | Reasoning |
|---|---|---|---|---|---|
| 16 | Sampling delay 3+ days | `sampling_delay_days >= 3` | +6 | 0 | Sampling slippage pushes production back |
| 17 | Fabric mill late 5+ days | `fabric_arrival_delay_days >= 5` | +8 | 0 | Cut/sew cannot start until fabric is in |
| 18 | Trims confirmation lag 3+ days | `trims_confirmation_lag_days >= 3` | +5 | +6 | Buyer-side bottleneck; late changes raise quality risk |
| 19 | Factory NCR backlog (4+) | `factory_ncr_count >= 4` | +3 | +14 | Recent non-conformances signal elevated quality risk |
| 20 | Buyer changes frequent (level 3) | `buyer_change_frequency == 3` | +6 | +10 | Late-stage rework hits both delay and quality |
| 21 | Sampling delay + first-cycle vendor | `sampling_delay_days >= 3` AND `vendor_is_new` | +6 | 0 | Compounding new-vendor slip |

## Validation results

Applied to all 5,000 synthetic orders on the **v2 dataset** (`src/apply_scorer.py`):

**Delay scorer — strong discrimination:**

| Predicted band | Actual delay rate |
|---|---|
| Low (0-35) | 15.0% |
| Medium (35-65) | 55.4% |
| High (65-100) | 94.5% |

A 6.3× spread from Low to High. When the scorer flags an order High, it actually delays 95% of the time.

**Return scorer — directional discrimination:**

| Predicted band | Actual return rate |
|---|---|
| Low (0-35) | 23.8% |
| Medium (35-65) | 29.3% |
| High (65-100) | 44.8% |

A 1.9× spread — monotonic and useful, but softer than delay.

## Honest limitations

1. **Returns are inherently less predictable than delays.** A large share of return risk flows through paths invisible at order-placement time — whether the order *actually* gets delayed (a partly-random future outcome), and the customer's subjective reaction to fit/fabric/colour on arrival. No order-time model can predict returns as sharply as delays. The 2x vs 10x gap reflects the problem, not a rubric flaw.

2. **The rubric and the synthetic data share calibration sources.** Both were built from the same benchmarks, so this validation proves *internal coherence and sensible discrimination* — not real-world accuracy. True external validation comes in Phase 5, against actual Snitch customer reviews.

3. **Lead-time weights are partly estimates.** Several §7 inputs await validation from a NIFT operations professor; the rubric is parameterised so these can be updated without code changes.

## How this feeds the hybrid model

The rule scorer is tier one of two. In Phase 4, an XGBoost classifier learns from the same features. The final ThreadTrack score blends both:

- **Rule scorer** — transparent, explainable, trusted by buyers
- **ML classifier** — captures subtle multi-factor interactions humans miss
- **Hybrid** — agreement between the two raises confidence; disagreement flags an order for human review

---

*Rubric v1 designed and validated 2026-05-20; v2 factors 16–21 added 2026-05-24. Weights live in `src/rule_scorer.py`; full benchmark citations in `docs/benchmarks.md`.*
