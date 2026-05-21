"""
src/classify_reviews.py — Classify Snitch customer reviews into supply chain
themes with the Claude API. This is the heart of Phase 5: the LLM layer.

WHAT THIS DOES
    Reads the 1,200 real Snitch reviews scraped by src/scrape_reviews.py and
    asks Claude to read each one and tag it with the supply chain complaint
    themes it mentions. Saves the tagged result to data/classified_reviews.csv.

WHY USE AN LLM FOR THIS
    A review is unstructured text — a customer wrote whatever they felt. There
    is no tidy "delay" column to read. The signal is buried inside sentences
    like "ordered three weeks ago, still nothing." A keyword rule that greps
    for the word "delay" would miss "still nothing", "never arrived", "took
    forever". An LLM reads for *meaning*, so it catches all of those. Turning
    messy free text into clean, structured labels is exactly the job LLMs are
    built for.

THE 6-THEME SCHEMA (multi-label: a review can have zero, one, or several)
    delivery_delay       late / stuck / never-arrived orders
    return_refund_issue  trouble returning an item or getting money back
    sizing_fit           wrong size, inconsistent sizing, bad fit
    product_quality      fabric / stitching / material defects, not as described
    customer_service     unhelpful, unresponsive, or rude support
    (no theme)           a positive or off-topic review — just an empty list

HOW TO RUN  (from the project root, with the venv active and .env in place)
    python src/classify_reviews.py 40     # TEST: first 40 reviews only (~$0.04)
    python src/classify_reviews.py        # FULL: every review (~$1)

    Always do the test run first. Open the sample CSV it writes, check the
    themes look sensible, and only then do the full run.

    The full run is RESUMABLE. If it stops partway, or the LLM skips a few
    reviews, just run it again — it loads whatever is already classified and
    does only the reviews still missing, so you never pay twice for a review.
"""

import json
import os
import sys

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

# load_dotenv() reads the .env file in the project root and copies the values
# inside it (here, ANTHROPIC_API_KEY) into the environment. The Anthropic
# client then picks the key up on its own. The key never appears in this file,
# so this file is safe to commit to GitHub.
load_dotenv()


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

MODEL = "claude-opus-4-7"          # the Claude model every review is sent to
BATCH_SIZE = 20                    # reviews per API call (1,200 / 20 = 60 calls)

INPUT_CSV = "data/snitch_reviews.csv"
OUTPUT_CSV = "data/classified_reviews.csv"
SAMPLE_CSV = "data/classified_reviews_SAMPLE.csv"   # written by a test run

# The five complaint themes. The sixth outcome — "no complaint" — needs no
# name: it is simply an empty theme list.
THEMES = [
    "delivery_delay",
    "return_refund_issue",
    "sizing_fit",
    "product_quality",
    "customer_service",
]

# Claude Opus 4.7 price per million tokens — used only for the cost report.
PRICE_INPUT_PER_M = 5.0
PRICE_OUTPUT_PER_M = 25.0


# ----------------------------------------------------------------------------
# The system prompt — Claude's standing instructions for every batch
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a supply chain analyst at a direct-to-consumer (D2C) \
menswear brand. You read customer reviews to find the operational problems the \
business needs to fix.

You will be given a batch of customer reviews. Each review starts with an \
identifier in the form [ID n]. For every review, decide which of these supply \
chain problem themes it describes:

- delivery_delay — the order arrived late, took too long, is stuck in transit, \
or never arrived at all.
- return_refund_issue — the customer struggled to return or exchange an item, \
or to get their money back: a refund delayed, denied, or never paid, a pickup \
not arranged, an exchange request ignored.
- sizing_fit — the item was the wrong size, the sizing ran large or small, \
sizes were inconsistent between items, or the fit did not match expectations.
- product_quality — a defect or quality problem with the item itself: fabric, \
stitching, material, colour fading, damage, or the product not matching its \
description or photos.
- customer_service — the support team was unresponsive, slow, unhelpful, or rude.

Rules:
1. Tag only the themes a review actually mentions. Do not infer or guess \
problems that are not stated in the text.
2. A review can mention zero, one, or several themes. Tag every theme that applies.
3. If a review is positive, or is about something outside these five themes, \
return an empty theme list for it.
4. Judge the words of the review, not the star rating. A one-star review with \
no explanation gets an empty list. A five-star review that still mentions a \
late delivery gets delivery_delay.
5. Return exactly one result for every review in the batch, using the exact \
[ID n] number you were given for that review."""


# ----------------------------------------------------------------------------
# The output schema — the exact shape Claude's answer must take
# ----------------------------------------------------------------------------
# This is a JSON Schema: a precise description of a data shape. We hand it to
# the API's "structured outputs" feature, which forces Claude's reply to match
# it exactly — valid JSON, the "results" list present, and (because of "enum")
# only the five allowed theme strings, never a typo or an invented theme.

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "description": "One entry per review in the batch.",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "The [ID n] number of the review.",
                    },
                    "themes": {
                        "type": "array",
                        "description": "Every theme this review mentions; "
                                       "empty if it has no complaint.",
                        "items": {"type": "string", "enum": THEMES},
                    },
                },
                "required": ["id", "themes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def build_user_message(batch):
    """Turn a batch of (review_id, review_text) pairs into one user message.

    Each review is collapsed onto a single line and prefixed with its id, so
    Claude sees an unambiguous, numbered list.
    """
    lines = []
    for review_id, text in batch:
        # " ".join(str(text).split()) collapses any newlines or double spaces
        # inside a review into single spaces, so each review is exactly one
        # clean line. (split() with no argument splits on any whitespace run.)
        clean_text = " ".join(str(text).split())
        lines.append(f"[ID {review_id}] {clean_text}")
    return "Classify every review below.\n\n" + "\n\n".join(lines)


def classify_batch(client, batch):
    """Send one batch of reviews to Claude and return (themes_by_id, usage).

    themes_by_id maps each review id to its list of themes.
    usage is the response's token-usage object, kept for the cost report.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(batch)}],
        # output_config with a json_schema is the "structured outputs"
        # feature: it constrains Claude's reply to match RESULT_SCHEMA exactly.
        # The reply is therefore guaranteed to be valid JSON we can parse.
        output_config={
            "format": {"type": "json_schema", "schema": RESULT_SCHEMA},
        },
    )

    # The reply is one text block of schema-valid JSON. Join all text blocks
    # defensively, then parse the JSON string into a Python dictionary.
    reply_text = "".join(b.text for b in response.content if b.type == "text")
    parsed = json.loads(reply_text)

    themes_by_id = {item["id"]: item["themes"] for item in parsed["results"]}
    return themes_by_id, response.usage


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    print("ThreadTrack — Snitch review classifier (Claude API)")
    print("=" * 60)

    # --- 1. Safety checks before we do anything --------------------------
    if not os.path.exists(INPUT_CSV):
        print(f"Cannot find {INPUT_CSV}. Run src/scrape_reviews.py first.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not found. Check that a .env file exists in "
              "the project root and contains your key.")
        sys.exit(1)

    # --- 2. Test run or full run? ----------------------------------------
    # An optional number on the command line means "test on this many reviews".
    sample_size = None
    if len(sys.argv) > 1:
        try:
            sample_size = int(sys.argv[1])
        except ValueError:
            print(f"Could not read '{sys.argv[1]}' as a number of reviews.")
            sys.exit(1)

    # --- 3. Load the reviews ---------------------------------------------
    df = pd.read_csv(INPUT_CSV)
    df = df.reset_index(drop=True)   # give every review a clean id: 0, 1, 2 ...

    if sample_size is not None:
        df = df.head(sample_size).copy()
        out_path = SAMPLE_CSV
        print(f"TEST RUN — first {len(df)} reviews only.")
    else:
        out_path = OUTPUT_CSV
        print(f"FULL RUN — {len(df)} reviews in {INPUT_CSV}.")

    # --- 4. Resume: skip reviews that are already classified -------------
    # If an output file already exists from an earlier run, load it and work
    # out which reviews still need doing. This makes the script re-runnable:
    # if a run stops partway, or the LLM omits a few reviews from a batch,
    # you just run the script again and it finishes only the leftovers. Each
    # review is matched by reviewId — the permanent unique id the Play Store
    # gave it. (A test run always starts fresh, so it skips this step.)
    previous = None
    if sample_size is None and os.path.exists(out_path):
        previous = pd.read_csv(out_path)
        # An empty themes cell reads back from a CSV as a blank (NaN); turn it
        # back into a real empty string so the whole column stays text.
        previous["themes"] = previous["themes"].fillna("")
        already_done = set(previous["reviewId"])
        todo = df[~df["reviewId"].isin(already_done)].copy()
        print(f"{len(previous)} reviews already classified in {out_path}; "
              f"{len(todo)} still to do.")
    else:
        todo = df

    if len(todo) == 0:
        print("Every review is already classified — nothing to do.")
        return

    # The review's row number is the id we send to Claude; Claude echoes it
    # back, so we always know which answer belongs to which review.
    rows = list(zip(todo.index.tolist(), todo["review_text"].tolist()))
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    print(f"{len(rows)} reviews split into {len(batches)} API call(s) "
          f"of up to {BATCH_SIZE} reviews each.")

    # --- 5. For the full run, confirm before spending money --------------
    if sample_size is None:
        # The first full run measured about $1 for 1,200 reviews, so we scale
        # that rate by however many reviews are actually left to do.
        estimate = len(rows) / 1200 * 1.10
        print(f"Estimated cost: about ${estimate:.2f} of Claude API credit.")
        if input("Type 'y' to proceed: ").strip().lower() != "y":
            print("Cancelled. Nothing was sent.")
            return

    # --- 6. Connect to Claude --------------------------------------------
    # max_retries=5 tells the SDK to automatically retry transient failures
    # (rate limits, brief server errors) with increasing wait times between
    # attempts, so a momentary network blip does not stop the run.
    client = Anthropic(max_retries=5)

    # --- 7. Classify every batch -----------------------------------------
    all_themes = {}            # review id -> list of themes
    total_input_tokens = 0
    total_output_tokens = 0
    completed_batches = 0

    for n, batch in enumerate(batches, start=1):
        print(f"  Batch {n}/{len(batches)} ({len(batch)} reviews) ...",
              end=" ", flush=True)
        try:
            themes_by_id, usage = classify_batch(client, batch)
        except Exception as error:
            print("FAILED")
            print(f"\nBatch {n} failed even after automatic retries: {error}")
            break
        all_themes.update(themes_by_id)
        total_input_tokens += usage.input_tokens
        total_output_tokens += usage.output_tokens
        completed_batches += 1
        print("done")

    if completed_batches == 0:
        print("\nNo reviews were classified this run. Check the API key in "
              ".env and your internet connection, then run the script again.")
        return
    if completed_batches < len(batches):
        print(f"\nStopped early: {completed_batches} of {len(batches)} "
              f"batches finished. Saving those — run the script again to "
              f"pick up the rest.")

    # --- 8. Attach the themes onto the reviews classified this run -------
    # Keep only reviews that actually came back with a classification.
    classified_ids = set(all_themes)
    todo = todo[todo.index.isin(classified_ids)].copy()

    # A human-readable column: themes joined with "; ", or "" for no complaint.
    todo["themes"] = ["; ".join(all_themes[i]) for i in todo.index]

    # One 0/1 column per theme, so the validation step can do simple maths
    # (counts, rates, correlations against the model's risk predictions).
    for theme in THEMES:
        todo[theme] = [int(theme in all_themes[i]) for i in todo.index]

    # A roll-up flag: 1 if the review raised any complaint at all.
    todo["has_complaint"] = todo[THEMES].max(axis=1)

    # --- 9. Combine with any earlier results, then save -----------------
    # Reviews done on previous runs (if any) plus the reviews done now,
    # sorted newest-first so the file stays in a sensible order.
    if previous is not None:
        final = pd.concat([previous, todo], ignore_index=True)
    else:
        final = todo
    final = final.sort_values("review_date", ascending=False)
    final.to_csv(out_path, index=False)

    # --- 10. Report ------------------------------------------------------
    print()
    print("=" * 60)
    print(f"Saved {len(final)} classified reviews to {out_path}")
    if previous is not None:
        print(f"  ({len(todo)} added this run + {len(previous)} from before)")
    still_missing = len(df) - len(final)
    if still_missing > 0:
        print(f"  {still_missing} review(s) still unclassified — run the "
              f"script again to retry just those.")
    print()
    print("Theme counts (one review can fall under several themes):")
    for theme in THEMES:
        count = int(final[theme].sum())
        pct = count / len(final) * 100
        print(f"  {theme:22s} {count:5d}  ({pct:5.1f}%)  {'#' * int(pct / 2)}")
    no_complaint = int((final["has_complaint"] == 0).sum())
    print(f"  {'(no complaint)':22s} {no_complaint:5d}  "
          f"({no_complaint / len(final) * 100:5.1f}%)")

    input_cost = total_input_tokens / 1_000_000 * PRICE_INPUT_PER_M
    output_cost = total_output_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
    print()
    print(f"Tokens used this run: {total_input_tokens:,} in  +  "
          f"{total_output_tokens:,} out")
    print(f"Cost this run: ${input_cost + output_cost:.2f}")

    print()
    print("Sample of classified reviews — check these look right:")
    print("-" * 60)
    for _, row in final.head(15).iterrows():
        labels = row["themes"] if row["themes"] else "(no complaint)"
        text = " ".join(str(row["review_text"]).split())
        if len(text) > 88:
            text = text[:88] + "..."
        print(f"  {row['rating']}*  [{labels}]")
        print(f"      {text}")

    print()
    if sample_size is not None:
        print("Test run complete. If the themes above look sensible, run the "
              "full set with:  python src/classify_reviews.py")
    else:
        print("Full run complete. Next: validate these review themes against "
              "the model's risk predictions.")


if __name__ == "__main__":
    main()
