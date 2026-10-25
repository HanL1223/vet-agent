.PHONY: install run test lint reset

PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"
	test -f .env || cp .env.example .env

run:
	$(BIN)/uvicorn vetagent.api.app:create_app --factory --reload --port 8000 --env-file .env

test:
	$(BIN)/pytest -q

lint:
	$(BIN)/ruff check src tests
	$(BIN)/ruff format --check src tests

reset:
	rm -f vetagent.db
