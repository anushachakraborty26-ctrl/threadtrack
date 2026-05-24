# ThreadTrack — one-line targets for the full pipeline.
#
# All targets assume an activated virtualenv at ./venv.
# Run from project root.  See README for the pipeline overview.

PY = ./venv/bin/python
RUFF = ./venv/bin/ruff

.PHONY: help data score ml hybrid stress loop playbook test lint all clean

help:
	@echo "ThreadTrack targets:"
	@echo "  make data      — regenerate synthetic dataset (generate + score)"
	@echo "  make ml        — train the XGBoost delay + return models"
	@echo "  make stress    — run the messy-data stress test"
	@echo "  make loop      — run the simulated MLOps feedback loop"
	@echo "  make playbook  — demo the action playbook"
	@echo "  make hybrid    — demo the rule + ML hybrid scorer"
	@echo "  make test      — run pytest"
	@echo "  make lint      — run ruff"
	@echo "  make all       — data + ml + stress + loop + test + lint"
	@echo "  make clean     — remove pycache"

data:
	$(PY) -m src.generate_data
	$(PY) -m src.apply_scorer

score:
	$(PY) -m src.apply_scorer

ml:
	$(PY) -m src.train_ml_model

stress:
	$(PY) -m src.messy_data_stress_test

loop:
	$(PY) -m src.feedback_loop_simulation

playbook:
	$(PY) -m src.action_playbook

hybrid:
	$(PY) -m src.hybrid_scorer

test:
	$(PY) -m pytest tests/ -v

lint:
	$(RUFF) check .

all: data ml stress loop test lint
	@echo "Pipeline + tests + lint all passed."

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	@echo "Cleaned __pycache__ directories."
