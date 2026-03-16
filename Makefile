docs-check:
	python3 scripts/validate_documentation.py

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && npm run typecheck && npm run test

mobile-test:
	cd mobile && flutter analyze && flutter test

dev-up:
	docker compose up --build

dev-down:
	docker compose down -v
