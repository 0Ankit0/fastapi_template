# FastAPI Template

A reusable full-stack template with FastAPI, Next.js, and Flutter, built around feature flags, pluggable providers, and reusable project documentation.

## What It Includes

- Config-driven modules for auth, multi-tenancy, notifications, websockets, finance, analytics, and social auth.
- Communications provider switching for email, push, and SMS.
- Runtime discovery APIs for clients and operators.
- Web and mobile clients that adapt to enabled modules and configured providers.
- A full `docs/` system modeled on the Project-Ideas documentation structure.

## Quick Start

1. Review [docs/README.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/README.md).
2. Copy environment files and configure providers.
3. Start local dependencies with `docker compose up`.
4. Run backend, frontend, and mobile apps with the commands in the onboarding docs.

## Validation

- Backend tests: `cd backend && uv run pytest`
- Frontend checks: `cd frontend && npm run typecheck && npm run test && npm run build`
- Mobile checks: `cd mobile && flutter analyze && flutter test`
- Docs validation: `python3 scripts/validate_documentation.py`
