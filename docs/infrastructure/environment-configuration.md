# Environment Configuration

| Profile | Purpose | Defaults |
|---|---|---|
| `local` | Fast feedback for developers | SQLite, memory-backed Celery, optional providers disabled |
| `staging` | Full integration verification | Managed DB/Redis, real provider sandboxes |
| `production` | Live workloads | Hardened hosts, managed services, monitoring enabled |

## Key Configuration Areas

- Feature flags: `FEATURE_*`
- Communications: `EMAIL_PROVIDER`, `PUSH_PROVIDER`, `SMS_PROVIDER`, fallbacks
- Analytics: `ANALYTICS_PROVIDER`, provider credentials
- Payments: provider-specific enablement and secrets
- Runtime: database, Redis, Celery, CORS, media, frontend URLs
