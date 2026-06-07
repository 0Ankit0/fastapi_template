lint:
	 uv run ruff check src tests

test:
	 uv run pytest --cov=src tests/

dev:
	uv run uvicorn src.main:app --reload

migrate:
	uv run task alembic upgrade head

