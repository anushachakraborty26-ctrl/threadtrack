"""
src/scrape_reviews.py — Pull Snitch customer reviews from the Google Play Store.

Snitch's Play Store app id is co.shopney.snitch. This script downloads recent
reviews, keeps the columns we need, and saves data/snitch_reviews.csv.

These real customer reviews are the independent, real-world evidence for Phase 5:
the LLM layer will classify them into supply chain themes, and the result will be
checked against the model's predictions.

Run from the project root (venv active):
    python src/scrape_reviews.py
"""

import pandas as pd
from google_play_scraper import reviews, Sort

APP_ID = "co.shopney.snitch"   # Snitch — Google Play package id


def main():
    print("ThreadTrack — Snitch review scraper")
    print("=" * 50)
    print(f"App: {APP_ID} (Google Play, India store)")

    # Pull recent reviews. We ask for a generous number; the store returns
    # however many actually exist, up to that count.
    result, _ = reviews(
        APP_ID,
        lang="en",
        country="in",
        sort=Sort.NEWEST,
        count=1200,
    )
    print(f"Pulled {len(result)} raw reviews.")

    df = pd.DataFrame(result)

    # Keep and rename the columns we care about
    keep = df[["reviewId", "content", "score", "thumbsUpCount", "at"]].copy()
    keep = keep.rename(columns={
        "content": "review_text",
        "score": "rating",
        "thumbsUpCount": "helpful_votes",
        "at": "review_date",
    })

    # Drop reviews with no text — they carry no signal for classification
    keep = keep[keep["review_text"].notna()]
    keep = keep[keep["review_text"].str.strip() != ""]
    keep = keep.reset_index(drop=True)

    keep.to_csv("data/snitch_reviews.csv", index=False)

    print()
    print(f"Saved {len(keep)} reviews with text to data/snitch_reviews.csv")
    print()
    print("Rating distribution (1 = worst, 5 = best):")
    for rating, count in keep["rating"].value_counts().sort_index().items():
        bar = "#" * int(count / max(1, len(keep)) * 40)
        print(f"  {rating} star: {count:4d}  {bar}")
    print()
    print(f"Average rating: {keep['rating'].mean():.2f}")
    print(f"Date range: {keep['review_date'].min()}  to  {keep['review_date'].max()}")


if __name__ == "__main__":
    main()
