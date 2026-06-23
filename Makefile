lint:
	 uv run ruff check src tests

test:
	 uv run pytest --cov=src tests/

dev:
	uv run uvicorn src.main:app --reload

migrate:
	uv run alembic upgrade head

MSG ?= "migration"
makemigrations:
	uv run alembic revision --autogenerate -m "$(MSG)"

compose-up:
	docker-compose -f infra/docker-compose.yml up -d --build

compose-down:
	docker-compose -f infra/docker-compose.yml down