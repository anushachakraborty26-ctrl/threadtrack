"""
src/feedback_loop_simulation.py — v2: a simulated MLOps feedback loop.

The reviewer's #5 critique: "no feedback loop, no learning. When the order
ships, does your model see the actual outcome and update?" — v2 sprint 1
documented the loop but did not run one. This script runs one.

The v2 dataset spans 12 months. The simulation:
  - Trains an initial model on the first 3 months.
  - Streams the remaining 9 months one at a time, injecting escalating
    drift (5% → 15% → 30% over three equal segments).
  - Tracks two trajectories on the streaming months:
      FROZEN — trained once at month 3, never retrained. The v1 behaviour.
      LOOP   — retrained every 2 streaming months on all accumulated
               data with realised outcomes. The v2 behaviour.
  - Plots both AUCs over simulated time, with drift segments shaded and
    retrain events marked.

The visible saw-tooth recovery on the LOOP line is the feedback loop
working. The flat-then-falling FROZEN line is what a one-shot model does.

Run from project root with venv active:
    python -m src.feedback_loop_simulation
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from src.messy_data_stress_test import corrupt, featurize_for_ml

INPUT_PATH = "data/scored_pos.csv"
CHART_PATH = "output/feedback_loop_simulation.png"
REPORT_PATH = "output/feedback_loop_simulation.txt"

INITIAL_TRAIN_MONTHS = 3
RETRAIN_EVERY_MONTHS = 2
SEED = 42


def drift_rate_for_step(step, total_streaming):
    """Escalating drift across the streaming horizon (three segments)."""
    third = max(1, total_streaming // 3)
    if step < third:
        return 0.05
    if step < 2 * third:
        return 0.15
    return 0.30


def auc(y_true, y_score):
    """ROC AUC; NaN if a month happens to have one class only."""
    if len(set(y_true)) < 2:
        return float("nan")
    return roc_auc_score(y_true, y_score)


def train_model(x, y):
    return LogisticRegression(max_iter=2000).fit(x, y)


def main():
    print("ThreadTrack v2 — simulated MLOps feedback loop")
    print("=" * 62)
    print()

    df = pd.read_csv(INPUT_PATH, parse_dates=["po_date"])
    df = df.sort_values("po_date").reset_index(drop=True)
    df["month"] = df["po_date"].dt.to_period("M")
    months = sorted(df["month"].unique())
    print(f"Loaded {len(df)} orders across {len(months)} months "
          f"({months[0]} → {months[-1]})")

    # --- Initial training window (clean data) ---
    init_months = months[:INITIAL_TRAIN_MONTHS]
    df_init = df[df["month"].isin(init_months)].copy()
    print(f"Initial training: {init_months[0]} → {init_months[-1]} "
          f"({len(df_init)} orders)")

    x_init = featurize_for_ml(df_init)
    y_init = df_init["is_delayed"].astype(int).values
    model_frozen = train_model(x_init, y_init)
    model_loop = train_model(x_init, y_init)
    # Two separate feature schemas — the frozen model's is locked at init
    # forever; the loop model's grows each time it retrains. Conflating
    # them is exactly the bug ruff/tests can't catch — it only shows up
    # when the schemas diverge after a retrain.
    frozen_cols = x_init.columns
    loop_cols = x_init.columns

    # --- Streaming production months (with drift) ---
    streaming_months = months[INITIAL_TRAIN_MONTHS:]
    n_streaming = len(streaming_months)
    print(f"Streaming production: {n_streaming} months "
          f"({streaming_months[0]} → {streaming_months[-1]})")
    print(f"Retrain trigger: every {RETRAIN_EVERY_MONTHS} streaming months")
    print("Drift schedule: 5% → 15% → 30%\n")

    df_accum = df_init.copy()                        # the loop's growing memory
    labels, drift_rates, auc_frozen, auc_loop = [], [], [], []
    retrain_events = []

    for step, month in enumerate(streaming_months):
        rate = drift_rate_for_step(step, n_streaming)
        df_month = df[df["month"] == month].copy()
        df_month_messy = corrupt(df_month, seed=SEED + step, rate=rate)

        x_month_raw = featurize_for_ml(df_month_messy)
        x_month_frozen = x_month_raw.reindex(columns=frozen_cols, fill_value=0.0)
        x_month_loop = x_month_raw.reindex(columns=loop_cols, fill_value=0.0)
        y_month = df_month["is_delayed"].astype(int).values

        a_frozen = auc(y_month, model_frozen.predict_proba(x_month_frozen)[:, 1])
        a_loop = auc(y_month, model_loop.predict_proba(x_month_loop)[:, 1])

        labels.append(str(month))
        drift_rates.append(rate)
        auc_frozen.append(a_frozen)
        auc_loop.append(a_loop)

        # The loop's outcomes database grows by this month's (messy) records
        df_accum = pd.concat([df_accum, df_month_messy], ignore_index=True)

        retrain_marker = ""
        # Retrain the loop model periodically — but not after the last month
        if (step + 1) % RETRAIN_EVERY_MONTHS == 0 and step + 1 < n_streaming:
            x_acc = featurize_for_ml(df_accum)
            loop_cols = x_acc.columns                # loop schema grows here
            y_acc = df_accum["is_delayed"].astype(int).values
            model_loop = train_model(x_acc, y_acc)
            retrain_events.append(step)
            retrain_marker = "  ← RETRAIN"

        print(f"  step {step+1:2d}  {month}   drift {rate:5.0%}   "
              f"frozen {a_frozen:.3f}   loop {a_loop:.3f}{retrain_marker}")

    mean_frozen = float(np.nanmean(auc_frozen))
    mean_loop = float(np.nanmean(auc_loop))
    lift = mean_loop - mean_frozen
    print()
    print(f"Frozen model — mean AUC across stream: {mean_frozen:.3f}")
    print(f"Loop   model — mean AUC across stream: {mean_loop:.3f}")
    print(f"Loop lift over frozen:                  {lift:+.3f}")

    # --- Chart ---
    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5.5))

    third = max(1, n_streaming // 3)
    ax.axvspan(-0.5, third - 0.5, alpha=0.05, color="green",
               label="low drift (5%)")
    ax.axvspan(third - 0.5, 2 * third - 0.5, alpha=0.10, color="orange",
               label="medium drift (15%)")
    ax.axvspan(2 * third - 0.5, n_streaming - 0.5, alpha=0.15, color="red",
               label="high drift (30%)")

    x_pos = list(range(n_streaming))
    ax.plot(x_pos, auc_frozen, "o-", color="#C0392B", linewidth=2,
            label="Frozen model (v1 behaviour)")
    ax.plot(x_pos, auc_loop, "o-", color="#2E5B8A", linewidth=2,
            label="Loop-retrained model (v2 behaviour)")

    for r in retrain_events:
        ax.axvline(r + 0.5, color="#2E5B8A", linestyle="--", alpha=0.4)

    if retrain_events:
        ax.annotate("↑ retrain events",
                    xy=(retrain_events[0] + 0.5, 0.96),
                    xytext=(retrain_events[0] + 0.5, 0.98),
                    fontsize=9, color="#2E5B8A", ha="left")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Delay AUC on the month's orders")
    ax.set_xlabel("Streaming month")
    ax.set_title("Simulated MLOps feedback loop — AUC over streaming months "
                 "as data drifts")
    ax.set_ylim(0.55, 1.02)
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=140)
    plt.close()
    print(f"Saved chart to  {CHART_PATH}")

    # --- Text report ---
    with open(REPORT_PATH, "w") as f:
        f.write("ThreadTrack v2 — simulated MLOps feedback loop\n")
        f.write("=" * 62 + "\n\n")
        f.write(f"Dataset:                  {len(df)} orders across "
                f"{len(months)} months ({months[0]} -> {months[-1]})\n")
        f.write(f"Initial training window:  {INITIAL_TRAIN_MONTHS} months "
                f"({len(df_init)} orders)\n")
        f.write(f"Streaming window:         {n_streaming} months\n")
        f.write(f"Retrain trigger:          every {RETRAIN_EVERY_MONTHS} "
                "streaming months\n")
        f.write("Drift schedule:           5% -> 15% -> 30% "
                "(three equal segments)\n\n")
        f.write(f"{'Month':<12} {'Drift':<8} {'Frozen AUC':<12} "
                f"{'Loop AUC':<12} {'Event':<10}\n")
        for i, m in enumerate(labels):
            event = "retrain" if i in retrain_events else ""
            f.write(f"{m:<12} {drift_rates[i]:<8.0%} "
                    f"{auc_frozen[i]:<12.3f} {auc_loop[i]:<12.3f} "
                    f"{event:<10}\n")
        f.write("\n")
        f.write(f"Frozen mean AUC across stream:  {mean_frozen:.3f}\n")
        f.write(f"Loop   mean AUC across stream:  {mean_loop:.3f}\n")
        f.write(f"Loop lift over frozen:          {lift:+.3f}\n\n")
        f.write("Interpretation:\n")
        f.write("  - The frozen model degrades as drift accumulates; nothing\n")
        f.write("    pulls it back up.\n")
        f.write("  - The loop model retrains on accumulated outcomes; it\n")
        f.write("    recovers at each retrain and tracks the moving data\n")
        f.write("    distribution.\n")
        f.write("  - The visible saw-tooth recovery on the loop line IS the\n")
        f.write("    feedback loop, running.\n")
    print(f"Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
