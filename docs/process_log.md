# ThreadTrack — Process Log

> The day-by-day logbook of building ThreadTrack — the bits that don't fit a
> polished case study. Errors, dead ends, judgment calls, and the small
> lessons that came out of each. Append-only.
>
> Phases 1 to 6 (Days 1 to 8) are covered in the case study at
> `docs/ThreadTrack_Case_Study.pdf`. This log picks up at Day 9, when the
> first serious external critique arrived and the v2 iteration began. The
> case study replaced the original .docx process documentation as the
> portfolio narrative; this log replaces it as the honest journey.

---

## Day 9 — Receiving the critique and shipping v2 sprint 1

*(23 May 2026)*

The v1 of ThreadTrack — README, case study, dashboard, Excel workbook —
was ready to share. It went to a senior apparel-tech practitioner for
review. The reply that came back was the best thing that could have
happened: a long, specific, generous-but-brutal critique that told the
project exactly what would impress him the next time around. Five points
landed.

He wrote that, operationally, a model trained once and pushed to GitHub
is *symbolic* — without a feedback loop pulling real outcomes back in,
it is a frozen snapshot the day it is trained, and it rots silently as
the world changes. He wrote that the data had never seen the mess of a
real factory ERP — *"100% cotton" spelled five ways, half the lead-time
fields blank, a sampling team that updates the system three days late*.
He wrote that the project's features were the same five things every
textbook uses, and the signals planners actually watch — sampling delay,
fabric mill slip, trims confirmation lag, factory NCR backlog,
buyer-change frequency — sit upstream of all of them. He wrote that a
score is not a fix; the honest deliverable is not *"this order is 73%
likely to be late"* but *"this order is 73% likely to be late, and here
are the three things to do about it, in order of impact."* And he wrote,
as a closing meta-instruction, that the students who impress him most are
the ones who can describe v1's weakness by their own framework and
describe v2.

That last line was the brief. v2 is the response.

### What was done

**Upstream operational features.** Five signals were added to
`src/config.py` as calibrated distributions and to `src/generate_data.py`
as a new `pick_upstream_features` step: `sampling_delay_days`,
`fabric_arrival_delay_days`, `trims_confirmation_lag_days`,
`factory_ncr_count`, `buyer_change_frequency`. Each is sampled per order
and feeds two lifts: the actual lead-time calculation (so it amplifies
the real outcome) and the return-probability calculation (for the
quality-related ones). Six new rule-scorer factors (16–21 in
`src/rule_scorer.py`) were added that fire when these features cross
thresholds — backward-compatible, so v1 rows continue to score the v1
way via Python's `.get(default)` pattern.

**The messy-data stress test.** A new `src/messy_data_stress_test.py`
script corrupts the v2 dataset the way real factory ERPs corrupt their
own — multiple spellings of vendor clusters, blank fields, inflated
quantity entries, missing numerics — and reports two things: the rule
scorer's AUC on clean (0.801) vs messy (0.709) data, and a quick
logistic-regression baseline that drops from 0.861 on clean to 0.786 on
messy and recovers to 0.799 when retrained on the messy distribution.
That recovery is the visible argument for the loop.

**A ranked action playbook.** `src/action_playbook.py:recommend_actions`
takes an order and its scores and returns a stack-ranked list of
specific moves — escalate trims with the buyer if the lag is high,
reserve fallback capacity at an alternate vendor if the cluster is in
crunch, pre-book the next fabric lot if the mill is slipping, push
prepaid at checkout if return risk is high on a COD order. Each carries
a target team and an expected impact. Rule-based to start; a
learned-policy version is sprint-2 territory.

**A simulated MLOps feedback loop.**
`src/feedback_loop_simulation.py` trains a model on the first three
months of the v2 dataset, streams the remaining nine with escalating
drift (5% → 15% → 30%), and retrains every two months. Two trajectories
are tracked: a *frozen* model (trained once, never updated — the v1
behaviour) and a *loop* model (retrained on each batch of new data).
Under low and medium drift the two lines overlap. Under high drift the
loop pulls clearly ahead. The chart is at
`output/feedback_loop_simulation.png` — the loop, running, not just
diagrammed.

### Errors and setbacks

> **Pandas 3 strictness — `Invalid value 'nan' for dtype 'bool'`.** The
> messy-data stress test corrupts the dataset by injecting NaN into
> several columns. The first attempt failed at row-set assignment
> because pandas 3 refuses to coerce NaN into a bool column without an
> explicit upcast — a strictness change from pandas 2. The fix: cast
> the target column to `object` before NaN-injection, so the missing
> marker has somewhere to live. **The lesson:** library version bumps
> quietly tighten rules that older code relied on; the only way to
> catch them is to run the code, fail, and read the message carefully.

The first calibration pass on the v2 dataset reported **79.7% of orders
delayed** — far worse than any real business would survive, and a direct
echo of v1's first-pass 77% bug. The cause was the same shape in a
different layer: the new upstream amplifiers stacked on top of v1's
existing amplifiers and compounded. Three passes — 80% → 52% → 45.6% —
got the rate back inside a realistic range. The discipline was the same
loop as v1: build, measure, diagnose, correct, repeat. The fact that the
loop ran *twice* in the same project, with the same shape, is itself a
finding worth recording: compounding bugs in stacked multipliers is the
most likely failure mode of this kind of generator. v3 — should it ever
exist — should start by *expecting* this and watching for it.

> **The sklearn feature-name mismatch in the feedback-loop simulation.**
> The first end-to-end run of the simulation failed with `ValueError:
> Feature names should match those that were passed during fit`. The
> cause was subtle. The script kept ONE `base_cols` variable for both
> models' feature schemas. The frozen model's schema is locked at month
> three forever; the loop model's schema grows every retrain. When the
> loop retrained at step 2 and overwrote `base_cols` with the new
> bigger schema, the next month's input got reindexed to that new
> schema, and the frozen model then choked because it had never seen
> those columns at fit time. The fix: two separate schema variables,
> `frozen_cols` (locked at init) and `loop_cols` (updated on retrain),
> with each month's input aligned to each model's own schema before
> prediction. **The lesson:** when two objects evolve at different
> rates, they need two variables; conflating them is exactly the class
> of bug no linter and no test would have caught at the time.

A smaller setback: a cwd mismatch — `./venv/bin/python: no such file or
directory` — because the shell was sitting in `~` rather than the
project root when a relative path was used. Trivial to fix (`cd` first,
or use the absolute path) but worth recording because the failed-task
log in the agent's UI preserves the failed attempt forever, which can
make a clean-now project look broken in retrospect.

### What Day 9 produced

The full v2 sprint 1: five new modules in `src/`, calibrated upstream
features, a re-scored dataset, a runnable stress test, a runnable
feedback-loop simulation with a chart, a ranked action playbook, and the
v2 sprint plan as `docs/v2_plan.md` (later consolidated into the README
and case study, then deleted as redundant). The discipline of the v1
calibration loop, applied twice. Two real bugs caught and explained.

---

## Day 10 — Sprint 2: cleanup, tests, retrain, consolidation

*(24 – 25 May 2026)*

Day 10 was a different kind of work. Less inventing, more discipline. A
brutally honest internal audit (asked for explicitly) named the gaps
that v2 sprint 1 had still left open — stale headline numbers, no tests,
no linter, the XGBoost model only living inside a notebook, the action
playbook described but never called, two narrative documents covering
the same ground. Sprint 2 closed them.

### What was done

**A linter, and what it caught.** `ruff` was added to the project with a
small `pyproject.toml` enabling pycodestyle errors and warnings,
pyflakes (the real bug-catching family — unused imports, undefined
names), isort import-order, and flake8-bugbear (likely-bug patterns).
The first run flagged **40 issues** across the codebase. 11 were
auto-fixable — out-of-order imports across six files, two f-strings
with no placeholders, a blank line with trailing whitespace. The
remaining 29 split into three groups:

1. **Intentional formatting (E501 line-too-long, 23 instances).** The
   inline-commented config dicts in `config.py` are 125 characters wide
   for readability; wrapping them hurts more than it helps. E501 was
   ignored project-wide.
2. **Bug-bear loop-variable warnings (B007, 2 instances).** The
   `for stage, (mean, _std) in ...` pattern where `stage` was never used
   in the body — renamed to `_stage` to satisfy the rule and document
   intent.
3. **`zip()` calls without an explicit `strict=` parameter (B905, 4
   instances).** Autofixed to `strict=False`, which preserves existing
   behaviour while satisfying the rule.

After the pass, ruff reports a clean codebase. The honest observation:
**a linter would have caught none of the two real bugs from Day 9** (the
pandas dtype strictness and the sklearn feature-name mismatch). Both
were runtime semantic mismatches, not static issues. A linter is hygiene
— it catches a different class of problem than tests do, and a different
class again from "actually running the thing." All three nets are
needed.

**Tests, finally.** A `tests/` directory with four pytest files, 26
tests total, covering: the rule scorer's baseline / worst-case behaviour
and its v2 backward compatibility; the region-aware season calendar;
the action playbook's low-risk and high-risk paths and priority
ordering; and the corruption simulator's row preservation and
rate-scaling. `pytest` was added to requirements. All 26 pass.

**Retraining the XGBoost model on the v2 data.** Until now the ML
model lived inside `notebooks/02_model.ipynb` with v1 numbers. The case
study and README both cited AUC 0.855 / 0.578 from v1. With the v2
dataset regenerated under them, those numbers were stale — anyone
running the notebook today would get different numbers. A new
`src/train_ml_model.py` script does the same training in runnable form:
load v2 data, featurize the same way the stress test does, 80 / 20
train / test split, train an XGBoost classifier for each of `is_delayed`
and `is_returned`, report AUC and feature importances, write the
trained models to `output/models/delay_xgb.pkl` and `return_xgb.pkl` so
the hybrid can load them, and emit a machine-readable `ml_metrics.json`
plus a plain-English report.

The v2 numbers: **delay AUC 0.847, return AUC 0.571**. Within rounding
of the v1 numbers (0.855 / 0.578). The headline finding — *delays are
predictable, returns largely are not* — holds. The upstream features
contributed real signal to the rule scorer but did not transform the
ML model's accuracy, because XGBoost was already extracting most of
the available signal from the v1 features. The honest takeaway:
**upstream features matter for interpretability and operational realism,
less for headline AUC, on this dataset.** That nuance was added to the
case study explicitly.

**A callable hybrid.** `src/hybrid_scorer.py` was written — the
performance-weighted hybrid the v1 case study had claimed but not
shipped as runnable code. It loads the rule scorer and the XGBoost
models saved by the training script, returns both components plus a
blend (0.6 ML / 0.4 rule for delay; 0.5 ML / 0.5 rule for return), and
flags orders where the two methods disagree by more than 25 points on
the 0–100 scale for human review. The demo against two example orders
showed both pathways: a low-risk order where rule and ML agreed closely
(an "agree" flag), and a high-risk order where the rule scorer said the
return risk was 100 and XGBoost said 58 — a real disagreement, flagged,
which is the operational value of the hybrid.

**Doc refresh and deletions.** The case study had cited v1 numbers
throughout (31.7% delayed, 0.855 / 0.578, 9 / 50 / 92 separation). Every
appearance was updated to v2 (45.6%, 0.847 / 0.571, 15 / 55 / 95). The
calibration callout was rewritten to mention both iterations of the
loop. A new Section 12 (*"v2 — the modelling-depth iteration"*) was
added, with the existing closing renumbered to 13. The README's Key
Results table and v2 section were updated identically. The scoring
rubric document gained a *"v2 — upstream operational factors (16–21)"*
table and updated validation numbers.

Two documents were deleted in the same pass: `docs/v2_plan.md`
(redundant with the README's v2 section) and
`docs/ThreadTrack_Process_Documentation.docx` together with the entire
`docs/process_doc/` Node toolchain (the original 30-page generator).
The reasoning: with the case study sharp enough to serve the portfolio
and hiring-manager audience, maintaining a second narrative artifact in
a second toolchain was double work. This very log file replaces the
.docx as the journey-oriented record, with a much lighter maintenance
footprint — markdown, append-only, renders on GitHub.

**Wiring the action playbook into the dashboard.** The playbook had been
written in sprint 1 but called only from its own `demo()` function. Two
small edits in `app.py` fixed that: `order_from_row` was made NaN-safe
and extended to pass the v2 upstream features through (so recomputed
scores in the Inspect-one-order view actually match the stored scores),
and a `render_actions(order, result)` helper was added that displays the
ranked playbook directly under `render_result` in both Tab 1 (Inspect)
and Tab 2 (the pending-order block).

**A Makefile** was added — `make data`, `make ml`, `make stress`,
`make loop`, `make test`, `make lint`, `make all`. Six command-line
invocations became one, and the project documents itself for anyone
cloning the repo cold.

### Errors and setbacks

The biggest source of friction on Day 10 was scope itself. The internal
audit named eight to ten different issues; the temptation was to fix all
of them at once. Discipline meant picking three priorities — refresh
stale numbers, add tests, retire one of the two narrative docs — and
shipping them cleanly rather than half-finishing twice as much. The
action-playbook wiring, the Makefile, and `hybrid_scorer.py` were
add-ons that fit naturally inside the same sprint; the notebook
re-execution and a deeper rebalance of the v2 scorer weights were
deferred to a future sprint without being abandoned.

A smaller pattern surfaced during the linter pass and is worth naming:
when `ruff --fix` modified seven source files in one step, the agent's
"this file was changed since you last read it" warnings fired loudly.
The change set was correct (auto-formatting), but it broke the implicit
contract of *I read the file, I know its current state, I'm safe to
edit it*. Going forward, running `--fix` early in a session and then
working from the fixed state avoids this whiplash.

A non-error worth recording: the **disagreement flag** in the hybrid
demo fired correctly on the first real run. The high-risk Tirupur
worst-case order produced a rule-scorer return of 100 and an ML return
of 58 — a 42-point gap, well past the 25-point threshold, correctly
labelled `DISAGREE`. The hybrid's operational point (*flag for human
review when methods disagree*) worked end-to-end the first time. Worth
recording because it almost never happens.

### What Day 10 produced

A linted, tested, callable, internally consistent project. Twenty-six
passing tests. A retrained ML pipeline that no longer lives in a
notebook. A callable hybrid that does what the v1 case study claimed it
did. A 15-page case study with current numbers. A README with the v2
section pointing at every new artifact. A Makefile reducing the pipeline
to single commands. One narrative documentation tradition retired and
replaced by this lighter one.

The git status at the end of Day 10 shows roughly 20 modified files, 14
new files, 4 deletions — a substantial day's work, all of it traceable
to a specific question a senior practitioner asked.

---

---

## Day 11 — The backend sketch

*(25 May 2026)*

A short, focused day. The senior reviewer had named "no API, no
database, no multi-tenancy" as part of the production gap; the case
study's Section 9 described what production would require but the
project shipped no code to back the description. Day 11 closes that —
at portfolio-sketch scope, not production scope.

### What was done

**A FastAPI service in `api/`.** Four files — `db.py` (SQLite schema
and seeding), `models.py` (Pydantic request/response shapes), `main.py`
(the FastAPI app with the endpoints below), and an empty `__init__.py`
to make it a package. The endpoints:

- `GET /health` — liveness
- `POST /score` — rule scorer, no DB write
- `POST /score-hybrid` — rule + ML blend (loads the pickled models)
- `POST /orders` — create + score + persist
- `GET /orders` — list with filters (cluster, season, risk band)
- `GET /orders/{po_id}` — one order with its score and (if captured) outcome
- `POST /orders/{po_id}/outcome` — capture the realised outcome (the
  data that feeds production retraining)

The API runs with `uvicorn api.main:app --reload --port 8000` (also
`make api`). OpenAPI docs at `/docs`.

**SQLite under the hood.** Two-table schema: `orders` (the canonical
record plus its score) and `outcomes` (realised delays/returns, FK to
orders). Indexed on cluster and season. Seeded on first startup from
`data/scored_pos.csv` so the API boots with a working 5000-row dataset.

**Eight API tests.** Health, score, validation rejection, create +
read back, filter by cluster, capture outcome, 404 on unknown orders.
All pass; the full suite is now 34 tests.

### Errors and setbacks

> **SQLite UNIQUE constraint failure on parallel inserts in the same
> millisecond.** The first version generated `po_id` from
> `int(now.timestamp())`. The list-orders test inserted two orders
> back-to-back, both getting the same integer second, collision on the
> primary key. Fix: append a UUID4-derived 8-character suffix to the
> id. **The lesson:** any "unique-by-timestamp" identifier is wrong;
> always combine timestamp with a randomness source, or use a UUID
> outright.

> **Ruff B008 — `Depends() in argument defaults`.** Bug-bear flagged
> the standard `conn = Depends(get_db)` pattern that the FastAPI
> tutorial still uses. The fix was not to suppress the rule but to
> switch to the modern `Annotated[Connection, Depends(get_db)]` form —
> same effect, no false positive, and the recommended idiom in current
> FastAPI docs. **The lesson:** when a linter flags an "official"
> pattern, check whether the official pattern has since moved on.

A small Python-syntax bug followed from that fix. Switching to
`Annotated` made `conn` a parameter without a default, so it had to
come BEFORE the query parameters with defaults in `list_orders` —
Python disallows non-default after default. Reordered the signature;
FastAPI does not care about argument order.

### What Day 11 produced

A runnable REST API. Eight passing API tests, 34 in the full suite,
ruff still clean. The Section 9 architecture sketch is no longer just
a diagram — it now has code behind every box (the scoring layer, the
API surface, the data layer). The README's v2 section and the case
study's Section 12 each pick up a new bullet pointing at `api/`. The
honest framing is preserved: this is a *sketch*. Production would swap
SQLite for Postgres, add authentication, add per-brand tenant
isolation, and run on managed cloud. But the scoring core —
`src/rule_scorer.py`, `src/hybrid_scorer.py` — is unchanged, because
it was already backend-shaped.

---

*This log is append-only. Each future working session adds a new day at
the bottom. The case study at `docs/ThreadTrack_Case_Study.pdf` remains
the polished portfolio narrative; this file is the honest journey
behind it.*
