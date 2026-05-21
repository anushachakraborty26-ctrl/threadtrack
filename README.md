# ThreadTrack

> A delay & return risk prediction system for D2C menswear supply chains — pairing apparel industrial-engineering domain knowledge with machine learning and an LLM-driven validation layer.

**Status:** Phases 1–5 complete · Phase 6 (deliverables) in progress

---

## The problem

Indian D2C menswear brands like Snitch drop 100+ new SKUs a week. At that velocity, a supply chain slip is invisible until customers complain — and by then it is already a refund, a return, or a lost repeat purchase.

Most delay-prediction tools are built without supply chain domain knowledge. They miss what a buying merchandiser knows intuitively: fabric category interacts with season, new vendors slip more in their first cycle, and tier-2/3 city deliveries carry risk that vendor SLAs don't surface.

ThreadTrack predicts which purchase orders are at risk of delay or return — and explains *why*, in terms an analyst can act on.

## Approach

A two-tier risk model, plus an independent real-data validation layer:

- **Rule-based scorer** — a hand-built, fully transparent scoring rubric (15 weighted factors: vendor reliability, fabric × season, destination tier, payment mode, a new-vendor penalty, and more). Every score is explainable.
- **ML classifier** — an XGBoost model trained on a synthetic purchase-order dataset whose distributions are calibrated to cited industry benchmarks.
- **Hybrid score** — a performance-weighted blend of the two, with a built-in agreement check that flags the orders where the rule scorer and the ML model disagree for human review.
- **LLM layer** — the Anthropic Claude API classifies real Snitch customer reviews into six supply chain complaint themes, using structured outputs to guarantee machine-readable results.
- **Validation** — the model's risk story is triangulated against the independent voice of 1,189 real customers.

## Key results

| Result | Detail |
|---|---|
| Synthetic dataset | 5,000 purchase orders, calibrated to McKinsey / Ministry of Textiles / Wazir benchmarks (31.7% delayed, 29.4% returned) |
| Delay prediction | XGBoost **AUC 0.855** — strong; delay is predictable from order-time data |
| Return prediction | XGBoost **AUC 0.578** — weak, and that is the finding (see below) |
| Rule scorer discrimination | Delay risk bands separate the actual delay rate **9% → 50% → 92%**; return bands only **22% → 28% → 43%** |
| LLM classification | **1,189** real Snitch reviews tagged into 6 supply chain themes via the Claude API |
| Validation | Independent customer reviews corroborate the model's risk priorities |

**The headline finding — delays are predictable, returns are not.** Three independent methods agree: the rule scorer (9.9× vs 2.0× band separation), the ML models (AUC 0.855 vs 0.578), and the feature-importance shapes. The reason is structural — a delay is caused by order-time factors the model can see (vendor, route, season); a return is caused by post-purchase factors it cannot (does the garment fit, is the quality acceptable). The LLM layer confirms it: sizing and product-quality complaints — the real triggers of a return — are exactly the information missing at order time. A weak return AUC is therefore an honest result, not a broken model.

## Architecture

Two independent data sources, converging at validation:

```
 SYNTHETIC TRACK                      REAL-DATA TRACK
 ---------------                      ---------------
 Industry benchmarks                  1,200 Snitch app reviews
        |                                     |
        v                                     v
 5,000-order synthetic                 LLM theme classifier
 purchase-order dataset                (Claude API, 6 themes)
        |                                     |
 Rule scorer  +  XGBoost                      |
        |                                     |
        v                                     |
 Hybrid risk score  ------>  Validation  <-----+
        |                  (triangulation)
        v
 Excel workbook . Streamlit dashboard . case study PDF   (Phase 6)
```

## Repository structure

```
src/
  config.py            calibrated parameters for the synthetic dataset
  generate_data.py     builds the 5,000-order synthetic PO dataset
  rule_scorer.py       the 15-factor rule-based risk scorer
  apply_scorer.py      applies the scorer across the full dataset
  scrape_reviews.py    pulls Snitch reviews from the Google Play Store
  classify_reviews.py  LLM classification pipeline (Claude API, resumable)
  validate.py          triangulates review themes against the model
notebooks/
  01_eda.ipynb         exploratory analysis of the synthetic dataset
  02_model.ipynb       ML training, evaluation, and hybrid scoring
data/                  synthetic + scored orders, scraped + classified reviews
docs/                  benchmark research, scoring rubric, process documentation
output/                generated charts
```

## Tech stack

- **Python** — pandas, NumPy, scikit-learn, XGBoost
- **Anthropic Claude API** — LLM review classification with structured outputs
- **Jupyter, matplotlib, seaborn** — analysis and visualisation
- **google-play-scraper** — review collection
- Planned (Phase 6) — **Streamlit** dashboard, **Excel** risk workbook

## Running the pipeline

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python src/generate_data.py      # build the synthetic dataset
python src/apply_scorer.py       # run the rule-based scorer
python src/scrape_reviews.py     # collect Snitch reviews
python src/classify_reviews.py   # classify reviews (needs ANTHROPIC_API_KEY in .env)
python src/validate.py           # validate model vs reviews
```

The ML models are trained and evaluated in `notebooks/02_model.ipynb`.

## Roadmap

- [x] Phase 1 — Foundation + industry benchmark research
- [x] Phase 2 — Synthetic data generation + EDA
- [x] Phase 3 — Rule-based scoring rubric
- [x] Phase 4 — ML classifier + hybrid scoring
- [x] Phase 5 — LLM layer + validation
- [ ] Phase 6 — Excel workbook + Streamlit dashboard + case study PDF

## Author

**Anusha Chakraborty** — Industrial Engineering & Supply Chain, NIFT
anushachakraborty26@gmail.com

---

*ThreadTrack is a portfolio project. The purchase-order dataset is synthetic, with distributions calibrated to public industry benchmarks; the validation layer uses public Google Play Store reviews. No proprietary or confidential data is used.*
