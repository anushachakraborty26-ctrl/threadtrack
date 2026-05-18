# ThreadTrack

> A delay & return risk predictor for D2C menswear supply chains — built by a NIFT industrial engineering student combining apparel domain knowledge with ML.

**Status:** In active development — Phase 1 of 6

---

## The problem

Indian D2C menswear brands like Snitch drop 100+ new SKUs per week. At that velocity, supply chain slip is invisible until customers complain — and by then it's already a refund, a return, or a lost repeat purchase.

Most delay-prediction tools are built by data teams that don't understand apparel. They miss what a buying merchandiser knows intuitively: fabric category interacts with season, new vendors slip more in their first cycle, and tier-3 city deliveries carry hidden risk that doesn't show up in vendor SLAs.

ThreadTrack predicts which orders are at risk **and explains why in language a buyer can act on.**

## What it does

A two-tier risk scorer for purchase orders:

- **Rule-based domain layer** — hand-built scoring rubric grounded in apparel industrial engineering (fabric × season interactions, vendor reliability decay, last-mile carrier risk by region)
- **ML classifier** — XGBoost trained on synthetic order data with distributions calibrated to real industry benchmarks
- **Hybrid score** — weighted blend with rule overrides for high-confidence flags
- **LLM layer** — extracts supply chain signals from unstructured inputs (customer reviews, simulated supplier messages)
- **Validation loop** — model predictions cross-checked against 500+ real Snitch app reviews coded by LLM for supply chain themes

## Architecture

```
Industry benchmarks ──► Synthetic PO dataset
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
        Rule-based scorer            ML classifier
                └─────────────┬─────────────┘
                              ▼
                      Hybrid risk score
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
       Excel tool      Streamlit demo      LLM layer
                                                │
                                                ▼
                                    Validation against
                                    real customer reviews
```

## Tech stack

- **Python** — pandas, scikit-learn, XGBoost
- **Streamlit** — analyst dashboard
- **Anthropic Claude API** — LLM layer
- **Excel** — buyer-facing risk workbook

## Roadmap

- [ ] Phase 1 — Foundation + industry benchmark research *(in progress)*
- [ ] Phase 2 — Synthetic data generation + EDA
- [ ] Phase 3 — Rule-based scoring rubric
- [ ] Phase 4 — ML classifier + hybrid scoring
- [ ] Phase 5 — LLM layer + validation correlation
- [ ] Phase 6 — Excel tool + Streamlit demo + case study PDF

## Author

**Anusha Chakraborty** — Industrial Engineering & Supply Chain, NIFT
Building this to apply for D2C menswear supply chain analyst internships.

anushachakraborty26@gmail.com

---

*ThreadTrack is a portfolio project. The synthetic dataset is calibrated against public industry benchmarks; the real-data validation uses public app store reviews. No proprietary data is used.*
