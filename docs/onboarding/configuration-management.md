# Configuration Management

## How Configuration Works

### Backend

- Backend runtime settings are defined in [backend/src/apps/core/config.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/core/config.py).
- Values bootstrap from the repository root `.env` file through `pydantic-settings`.
- After the database is available, runtime setting reads can be overridden from the `generalsetting` table.
- On startup, the backend syncs the current environment snapshot into `generalsetting.env_value`.
- Feature flags such as `FEATURE_NOTIFICATIONS` control router registration and runtime behavior.
- Provider settings such as `EMAIL_PROVIDER`, `PUSH_PROVIDER`, `SMS_PROVIDER`, and `ANALYTICS_PROVIDER` select the active implementation.
- `DATABASE_URL` and `SYNC_DATABASE_URL` remain environment-driven so the app can still connect to the database before runtime overrides are loaded.

### General Settings Table

- Table name: `generalsetting`
- Purpose: persist the known configuration keys, the current environment value, and an optional database override.
- Core columns:
  - `key`: unique config key name
  - `env_value`: latest value discovered from environment/bootstrap config
  - `db_value`: optional value to apply at runtime
  - `use_db_value`: when `true`, runtime reads prefer `db_value`
  - `is_runtime_editable`: marks keys that are safe to override after boot
- Seed behavior:
  - The Alembic migration creates and seeds the table with all known settings.
  - Startup sync keeps `env_value` current for future comparisons.

### Frontend

- Web configuration uses `NEXT_PUBLIC_*` variables for browser-safe values.
- The frontend also fetches runtime config from `/api/v1/system/capabilities/` and `/api/v1/notifications/push/config/`.
- If a value is secret or vendor-sensitive, it must stay on the backend and never be moved into `NEXT_PUBLIC_*`.

### Mobile

- Flutter reads `.env` through `flutter_dotenv` for app startup values.
- Mobile capability and push settings are also fetched from backend system APIs so the app can react to deployment-specific configuration.
- Mobile now also reads `/api/v1/system/general-settings/` for a safe public subset of runtime configuration, including whether a value is currently coming from environment or database.

## How To Manage Configuration

1. Add or change the backend setting in `config.py`.
2. Add the new variable to the root `.env` file or template used by the repo.
3. Decide whether it belongs in the public allowlist for `/api/v1/system/general-settings/`.
4. If it should be database-overridable, do not add it to the non-runtime-editable key set.
5. Document it in onboarding and infrastructure docs.
6. Add tests for parsing, defaults, sync behavior, and any public API shape change.

## Public vs Private Configuration

- Private: secrets, API keys, signing keys, database credentials, service-account JSON.
- Public: feature flags, active provider names, payment-provider enablement, project name, VAPID public key, FCM public app config, OneSignal app ID.

## Safe Change Checklist

- Is the config secret or public?
- Does the web app need it at build time or can it fetch it at runtime?
- Does the mobile app need an env fallback?
- Does the new key need a `generalsetting` row exposed or kept private?
- Did the docs and validator get updated?
