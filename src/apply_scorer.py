"""
src/apply_scorer.py — Apply the rule-based scorer to the full dataset.

Loads data/synthetic_pos.csv, scores every order, adds delay_score and
return_score columns, validates that scores correlate with actual outcomes,
and saves data/scored_pos.csv.

Run from project root (venv active):
    python -m src.apply_scorer
"""

import pandas as pd

from src.rule_scorer import score_order


def main():
    print("Applying rule-based scorer to dataset")
    print("=" * 55)

    # Load the synthetic dataset
    df = pd.read_csv("data/synthetic_pos.csv")
    print(f"Loaded {len(df)} orders")

    # Score every order: each row -> dict -> score_order() -> result dict
    results = df.apply(lambda row: score_order(row.to_dict()), axis=1)

    # Pull the two numeric scores into new columns
    df["delay_score"] = results.apply(lambda r: r["delay_score"])
    df["return_score"] = results.apply(lambda r: r["return_score"])

    print("Scored all orders.")
    print(f"  Delay score:  min={df['delay_score'].min()}, "
          f"mean={df['delay_score'].mean():.1f}, max={df['delay_score'].max()}")
    print(f"  Return score: min={df['return_score'].min()}, "
          f"mean={df['return_score'].mean():.1f}, max={df['return_score'].max()}")

    # =========================================================================
    # VALIDATION — do higher scores actually correlate with worse outcomes?
    # =========================================================================
    print("\n" + "=" * 55)
    print("VALIDATION: does the scorer predict reality?")
    print("=" * 55)

    # Bin delay scores into Low / Medium / High
    df["delay_band"] = pd.cut(
        df["delay_score"],
        bins=[0, 35, 65, 100],
        labels=["Low (0-35)", "Medium (35-65)", "High (65-100)"],
    )
    print("\nActual delay rate by predicted delay band:")
    delay_val = df.groupby("delay_band", observed=True)["is_delayed"].agg(["mean", "count"])
    for band, row in delay_val.iterrows():
        print(f"  {band:16s}  actual delay rate = {row['mean']*100:5.1f}%   (n={int(row['count'])})")

    # Bin return scores
    df["return_band"] = pd.cut(
        df["return_score"],
        bins=[0, 35, 65, 100],
        labels=["Low (0-35)", "Medium (35-65)", "High (65-100)"],
    )
    print("\nActual return rate by predicted return band:")
    return_val = df.groupby("return_band", observed=True)["is_returned"].agg(["mean", "count"])
    for band, row in return_val.iterrows():
        print(f"  {band:16s}  actual return rate = {row['mean']*100:5.1f}%   (n={int(row['count'])})")

    # Save scored dataset
    df.to_csv("data/scored_pos.csv", index=False)
    print(f"\nSaved scored dataset to data/scored_pos.csv")


if __name__ == "__main__":
    main()
