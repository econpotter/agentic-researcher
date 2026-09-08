setup:
    uv sync
    pre-commit install

test:
    uv run pytest

lint:
    uv run ruff check

fmt:
    uv run ruff format

check: test lint typecheck

typecheck:
    uv run mypy src
