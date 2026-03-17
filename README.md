# FastAPI Template

A reusable full-stack template with FastAPI, Next.js, and Flutter, built around feature flags, pluggable providers, and reusable project documentation.

The project is designed so that most customization starts with configuration and capability discovery, not code forks. The backend is the source of truth for enabled modules, active providers, public runtime settings, and operational behavior.

## What It Includes

- Config-driven modules for auth, multi-tenancy, notifications, websockets, finance, analytics, and social auth.
- Communications provider switching for email, push, and SMS.
- Runtime discovery APIs for clients and operators.
- Database-backed runtime settings overrides for safe operational config.
- Centralized operational config for cookies, hosts, rate limits, logging, observability, storage, Celery, and websocket behavior.
- Web and mobile clients that adapt to enabled modules and configured providers.
- A full `docs/` system modeled on the Project-Ideas documentation structure.

## Quick Start

1. Review [docs/README.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/README.md).
2. Read [project-orientation.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/project-orientation.md) and [configuration-management.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/configuration-management.md).
3. Copy environment files and configure providers.
4. Start local dependencies with `docker compose up`.
5. Run backend, frontend, and mobile apps with the commands in the onboarding docs.

## Validation

- Backend tests: `cd backend && uv run pytest`
- Frontend checks: `cd frontend && npm run typecheck && npm run test && npm run build`
- Mobile checks: `cd mobile && flutter analyze && flutter test`
- Docs validation: `python3 scripts/validate_documentation.py`
