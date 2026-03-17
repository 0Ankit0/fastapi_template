# Environment Configuration

| Profile | Purpose | Defaults |
|---|---|---|
| `local` | Fast feedback for developers | SQLite `app.db`, memory-backed Celery, optional providers disabled |
| `staging` | Full integration verification | Managed DB/Redis, real provider sandboxes |
| `production` | Live workloads | Hardened hosts, managed services, monitoring enabled |

## Key Configuration Areas

- Feature flags: `FEATURE_*`
- Communications: `EMAIL_PROVIDER`, `PUSH_PROVIDER`, `SMS_PROVIDER`, fallbacks
- Analytics: `ANALYTICS_PROVIDER`, provider credentials
- Payments: provider-specific enablement and secrets
- Runtime: database, Redis, Celery, CORS, media, frontend URLs

## Database Naming Convention

- The default logical database name is `app`.
- In local SQLite mode, this resolves to:
  - `DATABASE_URL=sqlite+aiosqlite:///./app.db`
  - `SYNC_DATABASE_URL=sqlite:///./app.db`
- In non-debug relational deployments, `POSTGRES_DB=app` is the default unless an environment overrides it explicitly.

## Runtime Override Rules

- The backend starts from environment values first.
- After the database connection is available, the `generalsetting` table can override runtime-safe keys.
- Bootstrap-only keys such as `DATABASE_URL` and `SYNC_DATABASE_URL` are intentionally excluded from runtime DB override.
