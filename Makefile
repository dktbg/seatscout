# Dev tasks. Tooling lives in .venv (make setup, or see CLAUDE.md).
VENV := .venv/bin

.PHONY: setup test test-live lint-check lint-fix

setup:
	python3.13 -m venv .venv && $(VENV)/pip install -e ".[dev]"

test:
	$(VENV)/pytest

test-live:
	$(VENV)/pytest -m integration

lint-check:
	$(VENV)/ruff check src tests
	$(VENV)/ruff format --check src tests

lint-fix:
	$(VENV)/ruff check --fix src tests
	$(VENV)/ruff format src tests
