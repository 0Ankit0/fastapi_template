# Configuration Management

## How Configuration Works

### Backend

- Backend runtime settings are defined in [backend/src/apps/core/config.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/core/config.py).
- Values come from environment variables and `.env` files through `pydantic-settings`.
- Feature flags such as `FEATURE_NOTIFICATIONS` control router registration and runtime behavior.
- Provider settings such as `EMAIL_PROVIDER`, `PUSH_PROVIDER`, `SMS_PROVIDER`, and `ANALYTICS_PROVIDER` select the active implementation.

### Frontend

- Web configuration uses `NEXT_PUBLIC_*` variables for browser-safe values.
- The frontend also fetches runtime config from `/api/v1/system/capabilities/` and `/api/v1/notifications/push/config/`.
- If a value is secret or vendor-sensitive, it must stay on the backend and never be moved into `NEXT_PUBLIC_*`.

### Mobile

- Flutter reads `.env` through `flutter_dotenv` for app startup values.
- Mobile capability and push settings are also fetched from backend system APIs so the app can react to deployment-specific configuration.

## How To Manage Configuration

1. Add or change the backend setting in `config.py`.
2. Add the new variable to `backend/.env.example`.
3. Expose it through a system or push config API only if the client truly needs it.
4. Document it in onboarding and infrastructure docs.
5. Add tests for parsing, defaults, and any public API shape change.

## Public vs Private Configuration

- Private: secrets, API keys, signing keys, database credentials, service-account JSON.
- Public: feature flags, active provider names, VAPID public key, FCM public app config, OneSignal app ID.

## Safe Change Checklist

- Is the config secret or public?
- Does the web app need it at build time or can it fetch it at runtime?
- Does the mobile app need an env fallback?
- Did the docs and validator get updated?
