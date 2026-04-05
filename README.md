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
2. Run `make setup`.
3. Read [project-orientation.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/project-orientation.md), [configuration-management.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/configuration-management.md), [template-finalization-checklist.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/template-finalization-checklist.md), and [TEMPLATE_RELEASE_CHECKLIST.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/TEMPLATE_RELEASE_CHECKLIST.md).
4. Start local dependencies with `make infra-up`.
5. Run migrations with `make backend-migrate`.
6. Start the apps with `make backend-dev`, `make frontend-dev`, and `make mobile-dev`.
7. Verify the starter with `make health-check` and `make ci`.

## Validation

- Backend lint and tests: `make backend-lint` and `make backend-test`
- Frontend lint, typecheck, tests, and build: `make frontend-lint` and `make frontend-test`
- Mobile analyze and tests: `make mobile-lint` and `make mobile-test`
- Docs validation: `make docs`
- Full local quality bar: `make ci`

## Docker

- The repo uses a single root `docker-compose.yml` as the canonical Docker entrypoint.
- Start the full stack with `docker compose up --build`.
- Start only infrastructure dependencies with `docker compose up -d db redis`.
- Stop and remove the stack with `docker compose down -v`.
- Podman is also supported with the same compose file: `podman compose config`, `podman compose up --build -d`, and `podman compose down`.
- If a local service already uses a default port, override the published host ports with env vars such as `POSTGRES_PORT=15432`, `REDIS_PORT=16379`, `BACKEND_PORT=18000`, or `FRONTEND_PORT=13000`.
- The backend image follows least-privilege runtime guidance: the final container runs as a dedicated non-root user, and OS package installation is avoided unless a builder-stage dependency truly requires it.
