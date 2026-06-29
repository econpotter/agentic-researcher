setup:
    uv sync
    pre-commit install

test:
    uv run pytest

lint:
    uv run ruff check

fmt:
    uv run ruff format
