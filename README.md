# ThreadTrack

> A delay & return risk prediction system for D2C menswear supply chains — pairing apparel industrial-engineering domain knowledge with machine learning and an LLM-driven validation layer.

**Status:** Phases 1–5 complete · Phase 6 (deliverables) in progress · **v2 sprint 1 shipped** (see [`docs/v2_plan.md`](docs/v2_plan.md))

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
| Synthetic dataset | 5,000 purchase orders, calibrated to McKinsey / Ministry of Textiles / Wazir benchmarks (45.6% delayed, 32.9% returned, v2 upstream features included) |
| Delay prediction | XGBoost **AUC 0.847** — strong; delay is predictable from order-time data |
| Return prediction | XGBoost **AUC 0.571** — weak, and that is the finding (see below) |
| Rule scorer discrimination | Delay risk bands separate the actual delay rate **15% → 55% → 95%**; return bands only **24% → 29% → 45%** |
| LLM classification | **1,189** real Snitch reviews tagged into 6 supply chain themes via the Claude API |
| Validation | Independent customer reviews corroborate the model's risk priorities |

**The headline finding — delays are predictable, returns are not.** Three independent methods agree: the rule scorer (6.3× vs 1.9× band separation on the v2 dataset), the ML models (AUC 0.847 vs 0.571), and the feature-importance shapes. The reason is structural — a delay is caused by order-time factors the model can see (vendor, route, season); a return is caused by post-purchase factors it cannot (does the garment fit, is the quality acceptable). The LLM layer confirms it: sizing and product-quality complaints — the real triggers of a return — are exactly the information missing at order time. A weak return AUC is therefore an honest result, not a broken model.

---

## v2 — what v1 is weak at, and what's now shipped

v1 was honest about *infrastructure* limits (the case study sets out a v1-vs-production table). What it did not address was *modelling-depth* limits — the same five things any senior practitioner would flag. v2 closes them. The case study's Section 12 has the full account; the short version:

- **Operationally symbolic without a loop.** A model trained once and pushed to GitHub is a frozen snapshot. v2 names the MLOps loop as a first-class part of the system, diagrams it (below), AND ships a runnable simulation [`src/feedback_loop_simulation.py`](src/feedback_loop_simulation.py) that runs the loop over twelve simulated months with escalating drift — chart at [`output/feedback_loop_simulation.png`](output/feedback_loop_simulation.png). Under high drift the loop pulls clearly ahead of a frozen v1-style model.
- **The data problem.** v1's synthetic data is statistically realistic but operationally clean — no typos, no missing fields, no drift. v2 ships [`src/messy_data_stress_test.py`](src/messy_data_stress_test.py), which corrupts the dataset the way real factory ERPs corrupt it and reports what happens: rule scorer AUC drops from **0.801 → 0.709**; logistic regression drops from **0.861 → 0.786** and partly recovers to **0.799** when retrained on the messy distribution. That recovery is the argument for the loop.
- **Upstream operational features.** v1's features were the textbook five (vendor, cluster, fabric, season, payment, tier, qty). v2 adds the signals planners actually watch — `sampling_delay_days`, `fabric_arrival_delay_days`, `trims_confirmation_lag_days`, `factory_ncr_count`, `buyer_change_frequency` — generated per order, amplifying actual outcomes, and used by six new rule-scorer factors. v2 delay rate calibrates to ~46% (v1 was 31.7%) because it models more delay mechanisms; the calibration loop ran three passes, the same discipline as v1.
- **Actions, not just scores.** v1's `recommended_action` returned one generic line per band. v2 ships [`src/action_playbook.py`](src/action_playbook.py) — `recommend_actions(order, scores)` returns a ranked list of specific moves (escalate trims, reserve fallback at V09, pre-book fabric, push prepaid, etc.), each with a target team and an expected impact.
- **A callable hybrid.** v1 described a "performance-weighted hybrid" that did not exist as runnable code — the XGBoost model only lived in a notebook. v2 ships [`src/hybrid_scorer.py`](src/hybrid_scorer.py) — it loads the trained XGBoost models (saved by [`src/train_ml_model.py`](src/train_ml_model.py)) and the rule scorer, returns both components plus a 0.6/0.4 (delay) and 0.5/0.5 (return) blend, and flags orders where the two methods disagree by more than 25 points for human review.
- **A named user.** v1 was built for nobody in particular. v2 writes the planner persona (below) and orients the product around her fifteen-minute window.
- **Engineering hygiene.** v2 also adds the basics v1 skipped — `tests/` (26 pytest checks), `ruff` as a project-wide linter, a `Makefile` that consolidates the pipeline into single targets (`make data`, `make test`, `make all`), and a `pyproject.toml` declaring tooling configuration.

## The MLOps loop (v2 architecture)

```
   ┌────────────┐     ┌────────────┐     ┌────────────────┐
   │   ORDER    │ ──► │  PREDICT   │ ──► │     ACTION     │
   │ (intake)   │     │  (scorer)  │     │   (playbook)   │
   └────────────┘     └────────────┘     └────────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │   OUTCOME     │
                                          │   (was it     │
                                          │    late?      │
                                          │    returned?) │
                                          └───────┬───────┘
                                                  │
   ┌────────────┐     ┌────────────┐     ┌────────▼───────┐
   │  DEPLOYED  │ ◄── │  RETRAIN   │ ◄── │   OUTCOMES DB  │
   │   MODEL    │     │  (loop)    │     │  (per brand)   │
   └────────────┘     └────────────┘     └────────────────┘
        ▲
        │   ┌───────────┐
        └── │ MONITORING│  ◄─── drift, AUC against incoming outcomes,
            └───────────┘       alerting on degradation
```

v1 implements the prediction box only. v2 names every other box as part of the system; production runs the whole loop.

## The user: Priya, planner at the brand

7:30 a.m., before her standup. She opens the dashboard. The top of her screen shows the twelve orders that crossed the high-risk threshold overnight. For each one she needs three things in fifteen seconds: *which to escalate first*, *what to do for each*, *who to call*. She closes the dashboard at 7:45, walks into standup with a working list, and has acted on three of them by 9:30. **The whole product is built around that fifteen-minute window** — entering only what she already knows (city, vendor, date), scoring before placing, and the ranked action playbook.

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
- [x] Phase 6 — Excel workbook + Streamlit dashboard + case study PDF
- [x] v2 — Modelling-depth iteration (upstream features, stress test, action playbook, feedback loop simulation, callable hybrid, tests + linter)
- [ ] Deployment — Streamlit Community Cloud

## Author

**Anusha Chakraborty** — Industrial Engineering & Supply Chain, NIFT
anushachakraborty26@gmail.com

---

*ThreadTrack is a portfolio project. The purchase-order dataset is synthetic, with distributions calibrated to public industry benchmarks; the validation layer uses public Google Play Store reviews. No proprietary or confidential data is used.*
