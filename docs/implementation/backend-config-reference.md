# Backend Configuration Reference

This document explains the settings defined in `backend/src/apps/core/config.py` and how they are resolved at runtime.

## How settings are loaded

- Environment variables are loaded first from `backend/.env`.
- Some values are derived automatically when you omit them. Example: `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`.
- A subset of non-secret settings can be overridden from the `generalsetting` table at runtime.
- Sensitive or infrastructure-bound settings remain environment-only and should be changed through deployment configuration, not through the database.

## How to modify settings safely

- For local development, edit `backend/.env`.
- For container or cloud deployments, set environment variables in compose, Kubernetes, ECS, or your secrets manager.
- Prefer explicit URLs for `DATABASE_URL`, `REDIS_URL`, and Kafka credentials in production.
- After changing infrastructure settings, restart the backend and worker processes.
- After changing feature flags, verify the corresponding frontend route or backend router is still enabled.

## App and identity settings

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `PROJECT_NAME` | `FastAPI Template` | Public application name used in docs and metadata. | Set per environment or product. |
| `APP_ENV` | `development` | High-level environment label. | Use `development`, `staging`, or `production`. |
| `APP_INSTANCE_NAME` | `fastapi-template` | Stable service instance name for logs and integrations. | Change to match deployment/service naming. |
| `APP_REGION` | `local` | Region label for runtime metadata. | Set to your deployment region like `us-east-1`. |
| `API_V1_STR` | `/api/v1` | Base prefix for versioned API routes. | Only change during API versioning or proxy rewrites. |

## Authentication and session settings

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `SECRET_KEY` | `supersecretkey` | General signing and fallback secret. | Always override in real environments. |
| `PASETO_SECRET_KEY` | unset | Dedicated PASETO signing secret. | Set explicitly in production token environments. |
| `PASSWORD_PEPPER` | falls back to `SECRET_KEY` | Extra secret mixed into password hashing. | Set separately from `SECRET_KEY` for stronger isolation. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime in minutes. | Increase carefully for UX, decrease for stricter security. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days. | Adjust to session policy requirements. |
| `ACCESS_TOKEN_COOKIE` | `access_token` | Cookie name used for browser access tokens. | Change only if proxy/app naming requires it. |
| `REFRESH_TOKEN_COOKIE` | `refresh_token` | Cookie name used for browser refresh tokens. | Keep aligned with auth clients and logout logic. |
| `SECURE_COOKIES` | `False` | Sends cookies only over HTTPS when enabled. | Enable in HTTPS deployments. |
| `COOKIE_DOMAIN` | unset | Shared cookie domain for subdomain auth. | Set to parent domain for multi-subdomain deployments. |
| `COOKIE_SAMESITE` | `lax` | Browser cross-site cookie policy. | Use `none` only when you also use HTTPS. |

## Password and login protection

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed attempts before account lockout logic applies. | Tune with support/security requirements. |
| `ACCOUNT_LOCKOUT_DURATION_MINUTES` | `30` | Lockout period after repeated failures. | Increase for stricter brute-force resistance. |
| `REQUIRE_EMAIL_VERIFICATION` | `False` | Requires verified email before full access. | Enable when onboarding must verify identity. |
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length. | Increase for stricter password policy. |
| `PASSWORD_REQUIRE_UPPERCASE` | `True` | Requires uppercase characters. | Disable only if using a passphrase-friendly policy. |
| `PASSWORD_REQUIRE_LOWERCASE` | `True` | Requires lowercase characters. | Disable only with a deliberate password policy change. |
| `PASSWORD_REQUIRE_DIGIT` | `True` | Requires at least one digit. | Adjust to product password policy. |
| `PASSWORD_REQUIRE_SPECIAL` | `False` | Requires at least one special character. | Enable if compliance requires it. |

## Runtime, logging, and incident detection

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `DEBUG` | `True` | Enables development behavior and local defaults. | Disable in staging and production. |
| `TESTING` | `False` | Enables test-mode behavior. | Only set from test runners. |
| `LOG_LEVEL` | `INFO` | Base application log level. | Use `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |
| `LOG_PERSIST_MIN_LEVEL` | `INFO` | Minimum level stored in persisted observability logs. | Raise if storage noise becomes excessive. |
| `LOG_OUTPUTS` | `console,database,web` | Active log sinks. | Remove sinks if you want less persistence or streaming. |
| `LOG_FILE_PATH` | `logs/application.log` | File output location when file logging is enabled. | Point to mounted storage when needed. |
| `LOG_RETENTION_DAYS` | `7` | Prune age for persisted logs. | Increase for longer audit retention. |
| `LOG_SQL_QUERIES` | `False` | Enables SQL query logging. | Use only while debugging performance or query shape. |
| `FAILED_LOGIN_BURST_THRESHOLD` | `5` | Suspicious failed-login incident threshold. | Tune to match auth traffic patterns. |
| `FAILED_LOGIN_BURST_WINDOW_MINUTES` | `30` | Time window for failed-login burst detection. | Shorten for faster alerting, lengthen for lower sensitivity. |
| `TOKEN_CHURN_THRESHOLD` | `3` | Threshold for excessive token issuance/revocation. | Tune against expected token rotation. |
| `TOKEN_CHURN_WINDOW_MINUTES` | `10` | Time window for token churn detection. | Adjust to session behavior. |
| `RATE_LIMIT_SPIKE_THRESHOLD` | `10` | Threshold for rate-limit spike incidents. | Increase if noisy during load tests. |
| `RATE_LIMIT_SPIKE_WINDOW_MINUTES` | `10` | Time window for rate-limit spike detection. | Tune for alert sensitivity. |
| `ERROR_SPIKE_THRESHOLD` | `5` | Threshold for error spike incidents. | Increase if background jobs create expected noise. |
| `ERROR_SPIKE_WINDOW_MINUTES` | `10` | Time window for error spike detection. | Tune with observability goals. |

## Feature flags

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `FEATURE_AUTH` | `True` | Enables auth routers and auth flows. | Disable only for very specialized deployments. |
| `FEATURE_MULTITENANCY` | `True` | Enables tenant and organization features. | Disable if the app is single-tenant only. |
| `FEATURE_NOTIFICATIONS` | `True` | Enables notification APIs and related UI. | Disable if you do not use notifications. |
| `FEATURE_WEBSOCKETS` | `True` | Enables websocket endpoints and live features. | Disable if you do not need realtime features. |
| `FEATURE_FINANCE` | `True` | Enables payment and finance modules. | Disable in products without billing flows. |
| `FEATURE_ANALYTICS` | `True` | Enables analytics API routes. | Disable if analytics is not part of the deployment. |
| `FEATURE_SOCIAL_AUTH` | `True` | Enables OAuth provider discovery and callbacks. | Disable if only username/password login is allowed. |
| `FEATURE_MAPS` | `False` | Enables mapping features and public map config. | Enable only when the frontend uses maps. |

## Redis and Celery

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `REDIS_HOST` | `localhost` | Redis host used when `REDIS_URL` is not set. | Set to your Redis hostname or service DNS. |
| `REDIS_PORT` | `6379` | Redis port. | Change for non-default Redis ports. |
| `REDIS_DB` | `0` | Redis logical database index. | Separate environments or workloads with different DBs if desired. |
| `REDIS_PASSWORD` | unset | Redis password. | Store in env or a secret manager. |
| `REDIS_MAX_CONNECTIONS` | `10` | Max Redis client pool connections. | Increase for busier deployments. |
| `REDIS_URL` | derived | Full Redis URL. | Set explicitly in production for clarity. |
| `CELERY_BROKER_URL` | derived | Celery broker URL. | Override if broker differs from Redis. |
| `CELERY_RESULT_BACKEND` | derived | Celery result backend URL. | Override if result storage differs. |
| `CELERY_TASK_TIME_LIMIT` | `1800` | Hard task runtime limit in seconds. | Increase only for known long-running jobs. |
| `CELERY_RESULT_EXPIRES` | `3600` | Result retention in seconds. | Increase if clients read results later. |
| `CELERY_TASK_ALWAYS_EAGER` | derived from `DEBUG` | Executes tasks inline when enabled. | Use `False` in integration or production-like runs. |
| `CELERY_QUEUE_DEFAULT` | `default` | Default Celery queue name. | Change to match worker topology. |

## HTTP, CORS, trusted hosts, and websockets

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `BACKEND_CORS_ORIGINS` | `http://localhost,http://localhost:3000` | Allowed browser origins. | Add deployed frontend origins. |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,test,testserver` | Allowed host headers in production mode. | Add public domains behind your proxy/load balancer. |
| `PROXY_TRUSTED_HOSTS` | `*` | Trusted proxy hosts for forwarded headers. | Restrict in production if possible. |
| `FORWARDED_ALLOW_IPS` | `*` | Allowed proxy IPs for forwarded header handling. | Restrict to proxy/load balancer IP ranges in production. |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default API rate limit. | Tune with expected traffic. |
| `RATE_LIMIT_LOGIN` | `5/minute` | Login endpoint rate limit. | Raise only if UX is too restrictive. |
| `RATE_LIMIT_SIGNUP` | `3/hour` | Signup endpoint rate limit. | Tune for onboarding and abuse control. |
| `RATE_LIMIT_PASSWORD_RESET` | `3/hour` | Password reset rate limit. | Tune for support volume and abuse prevention. |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend base URL for links and redirects. | Set to the deployed frontend URL. |
| `SERVER_HOST` | `http://localhost:8000` | Backend public base URL. | Set to the externally reachable backend URL. |
| `HTTP_TIMEOUT_SECONDS` | `15.0` | Default outgoing HTTP timeout. | Raise for slow upstreams, lower for stricter failure bounds. |
| `HTTP_RETRY_COUNT` | `1` | Default outgoing HTTP retries. | Increase for transient upstream failures. |
| `HTTP_BACKOFF_SECONDS` | `0.5` | Base HTTP retry backoff. | Tune if upstreams need gentler retry spacing. |
| `WS_ALLOWED_ORIGINS` | `http://localhost:3000` | Allowed websocket origins. | Add frontend domains that open websocket connections. |
| `WS_HEARTBEAT_INTERVAL_SECONDS` | `30` | Websocket heartbeat interval. | Tune for proxy idle timeout behavior. |
| `WS_MAX_IDLE_SECONDS` | `90` | Idle timeout for websocket connections. | Increase if clients idle longer between pings. |

## Database

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `POSTGRES_SERVER` | `localhost` | Postgres host used when `DATABASE_URL` is not set. | Set to your database host or service DNS. |
| `POSTGRES_USER` | `postgres` | Postgres username. | Set to the application DB user. |
| `POSTGRES_PASSWORD` | `postgres` | Postgres password. | Store securely and override in every real environment. |
| `POSTGRES_DB` | `app` | Database name. | Set to your application database. |
| `DATABASE_URL` | derived | Full SQLAlchemy database URL. | Prefer explicit URL in deployed environments. |
| `DB_POOL_SIZE` | `10` | SQLAlchemy connection pool size. | Increase for higher concurrency. |
| `DB_MAX_OVERFLOW` | `20` | Temporary connections beyond the base pool size. | Tune alongside pool size and DB capacity. |
| `DB_POOL_TIMEOUT` | `30` | Wait time for a DB connection. | Increase if bursts exhaust the pool. |
| `DB_POOL_RECYCLE` | `1800` | Connection recycle interval in seconds. | Lower if long-lived connections are dropped by the network. |

## Media and storage

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `MEDIA_DIR` | `media` | Local media storage directory. | Set to a mounted writable path. |
| `MEDIA_URL` | `/media` | URL prefix for local media serving. | Change only if reverse proxy or frontend expects another path. |
| `STORAGE_BACKEND` | `local` | Selects `local` or `s3` media storage. | Switch to `s3` for cloud object storage. |
| `MEDIA_BASE_URL` | empty | Explicit media base URL override. | Set when media is served from CDN or another domain. |
| `S3_BUCKET` | empty | S3 bucket name. | Set when using S3 storage. |
| `S3_REGION` | `us-east-1` | S3 region. | Match your bucket region. |
| `S3_ENDPOINT_URL` | empty | Custom S3-compatible endpoint. | Use for MinIO or other S3-compatible storage. |
| `S3_USE_PATH_STYLE` | `False` | Enables path-style S3 URLs. | Enable for MinIO or providers that require it. |
| `MAX_AVATAR_SIZE_MB` | `5` | Avatar upload size limit. | Increase if you allow larger profile images. |

## Maps

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `MAP_PROVIDER` | `osm` | Active map provider label. | Set to `google` when switching map provider. |
| `OSM_MAPS_ENABLED` | `True` | Enables OpenStreetMap support. | Disable if you want Google-only maps. |
| `GOOGLE_MAPS_ENABLED` | `False` | Enables Google Maps support. | Enable when you provide Google Maps credentials. |
| `GOOGLE_MAPS_API_KEY` | empty | Google Maps browser API key. | Set from your Google Cloud project. |
| `GOOGLE_MAPS_MAP_ID` | empty | Optional Google Maps map styling ID. | Set when using custom map styling. |
| `MAP_DEFAULT_LATITUDE` | `27.7172` | Default map center latitude. | Change to your primary geography. |
| `MAP_DEFAULT_LONGITUDE` | `85.3240` | Default map center longitude. | Change to your primary geography. |
| `MAP_DEFAULT_ZOOM` | `13` | Default map zoom level. | Tune for city, region, or global views. |

## Kafka

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `KAFKA_ENABLED` | `False` | Enables the Kafka producer lifecycle on app startup. | Set to `True` only when Kafka infrastructure and credentials are ready. |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Bootstrap broker list. | Set as comma-separated hosts like `k1:9092,k2:9092`. |
| `KAFKA_CLIENT_ID` | `fastapi-template` | Kafka producer client identifier. | Set per service or deployment for observability. |
| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT` | Kafka transport security mode. | Use `SSL` or `SASL_SSL` in secured clusters. |
| `KAFKA_SASL_MECHANISM` | empty | SASL authentication mechanism. | Set to `PLAIN`, `SCRAM-SHA-256`, or your cluster requirement. |
| `KAFKA_USERNAME` | empty | Kafka SASL username. | Set when using SASL-authenticated clusters. |
| `KAFKA_PASSWORD` | empty | Kafka SASL password. | Store securely in secrets management. |
| `KAFKA_TOPIC_PREFIX` | `fastapi-template` | Prefix applied to published topic names. | Use a stable environment/application prefix. |
| `KAFKA_DEFAULT_TOPIC` | `application.events` | Default topic name used when no topic is provided. | Change to your main events topic. |
| `KAFKA_CONSUMER_GROUP` | `fastapi-template` | Default consumer group name for future consumers. | Align with your worker/consumer naming. |
| `KAFKA_REQUEST_TIMEOUT_MS` | `15000` | Producer request timeout in milliseconds. | Raise for slow or distant clusters. |
| `KAFKA_ENABLE_IDEMPOTENCE` | `True` | Enables idempotent producer mode. | Disable only if the cluster/config does not support it. |

## Email

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `EMAIL_ENABLED` | `False` | Enables email delivery features. | Turn on only when a provider is configured. |
| `EMAIL_PROVIDER` | `smtp` | Active email provider. | Set to `smtp`, `resend`, or `ses`. |
| `EMAIL_FALLBACK_PROVIDERS` | empty | Ordered fallback email providers. | Set as comma-separated provider names. |
| `EMAIL_HOST` | `smtp.example.com` | SMTP server host. | Set to your SMTP server hostname. |
| `EMAIL_PORT` | `587` | SMTP port. | Change for SSL/TLS or provider-specific ports. |
| `EMAIL_HOST_USER` | `user@example.com` | SMTP username. | Set to the mailbox or auth username. |
| `EMAIL_HOST_PASSWORD` | `password` | SMTP password. | Store securely in env/secrets. |
| `EMAIL_FROM_ADDRESS` | `noreply@example.com` | Default sender address for SMTP email. | Set to a verified sender. |
| `RESEND_API_KEY` | empty | Resend API key. | Set when using Resend. |
| `RESEND_FROM_ADDRESS` | `noreply@example.com` | Default sender address for Resend. | Set to a verified Resend sender. |
| `AWS_REGION` | `us-east-1` | AWS region for SES and other AWS integrations. | Match your SES region. |
| `AWS_ACCESS_KEY_ID` | empty | AWS access key ID. | Set via secrets manager or IAM-injected env. |
| `AWS_SECRET_ACCESS_KEY` | empty | AWS secret access key. | Store securely and rotate regularly. |
| `SES_FROM_ADDRESS` | `noreply@example.com` | Default SES sender address. | Set to a verified SES sender. |

## Push notifications

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `PUSH_ENABLED` | `False` | Enables push notification features. | Enable only after configuring a provider. |
| `PUSH_PROVIDER` | `webpush` | Active push provider. | Set to `webpush`, `fcm`, or `onesignal`. |
| `PUSH_FALLBACK_PROVIDERS` | empty | Ordered fallback push providers. | Set as comma-separated provider names. |
| `VAPID_PRIVATE_KEY` | empty | Web Push private key. | Set for browser Web Push. |
| `VAPID_PUBLIC_KEY` | empty | Web Push public key exposed to the frontend. | Set with the matching private key. |
| `VAPID_CLAIMS_EMAIL` | `mailto:admin@example.com` | Contact claim used for Web Push. | Set to a real operational contact. |
| `FCM_SERVER_KEY` | empty | Legacy FCM server key. | Set only if using the legacy server-key flow. |
| `FCM_PROJECT_ID` | empty | Firebase project ID. | Required for modern FCM service account flow. |
| `FCM_WEB_VAPID_KEY` | empty | Firebase web push VAPID key. | Set for FCM browser push. |
| `FCM_API_KEY` | empty | Firebase web API key. | Set for frontend FCM initialization. |
| `FCM_APP_ID` | empty | Firebase app ID. | Set from Firebase project configuration. |
| `FCM_MESSAGING_SENDER_ID` | empty | Firebase messaging sender ID. | Set from Firebase project configuration. |
| `FCM_AUTH_DOMAIN` | empty | Firebase auth domain. | Set when frontend Firebase auth config requires it. |
| `FCM_STORAGE_BUCKET` | empty | Firebase storage bucket. | Set when using Firebase Storage-backed features. |
| `FCM_MEASUREMENT_ID` | empty | Firebase measurement ID. | Set when analytics integration uses it. |
| `FCM_SERVICE_ACCOUNT_JSON` | empty | Inline FCM service account JSON. | Prefer secret-managed multiline env or file mount. |
| `FCM_SERVICE_ACCOUNT_FILE` | empty | Path to FCM service account JSON file. | Use when mounting a credential file. |
| `ONESIGNAL_APP_ID` | empty | OneSignal app ID. | Set when using OneSignal. |
| `ONESIGNAL_API_KEY` | empty | OneSignal REST API key. | Store securely in secrets management. |
| `ONESIGNAL_WEB_APP_ID` | empty | Optional OneSignal web app ID override. | Set when the web app ID differs from the main app ID. |

## SMS

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `SMS_ENABLED` | `False` | Enables SMS notification features. | Turn on only when an SMS provider is configured. |
| `SMS_PROVIDER` | `vonage` | Active SMS provider. | Currently set to `vonage`. |
| `SMS_FALLBACK_PROVIDERS` | empty | Ordered fallback SMS providers. | Set as comma-separated provider names when more providers are added. |
| `VONAGE_API_KEY` | empty | Vonage API key. | Set from your Vonage account. |
| `VONAGE_API_SECRET` | empty | Vonage API secret. | Store securely in secrets management. |
| `VONAGE_FROM_NUMBER` | empty | Sender phone number or alphanumeric sender ID. | Set to an approved sender identity. |

## Payments and finance

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `KHALTI_ENABLED` | `True` | Enables Khalti payment support. | Disable when unused. |
| `KHALTI_SECRET_KEY` | sample value | Khalti secret key. | Replace with your real key. |
| `KHALTI_BASE_URL` | Khalti dev URL | Khalti API base URL. | Switch to production URL in production. |
| `ESEWA_ENABLED` | `True` | Enables eSewa payment support. | Disable when unused. |
| `ESEWA_SECRET_KEY` | sample value | eSewa secret key. | Replace with your real key. |
| `ESEWA_MERCHANT_CODE` | `EPAYTEST` | eSewa merchant code. | Set to your real merchant code. |
| `ESEWA_BASE_URL` | eSewa RC URL | eSewa API base URL. | Switch to the production endpoint when going live. |
| `STRIPE_ENABLED` | `False` | Enables Stripe support. | Enable only when Stripe keys are configured. |
| `STRIPE_SECRET_KEY` | sample value | Stripe secret key. | Replace with real test/live secret key. |
| `STRIPE_WEBHOOK_SECRET` | sample value | Stripe webhook signing secret. | Set to the secret from Stripe webhook setup. |
| `PAYPAL_ENABLED` | `False` | Enables PayPal support. | Enable only when PayPal client credentials are configured. |
| `PAYPAL_CLIENT_ID` | sample value | PayPal client ID. | Replace with your sandbox or live client ID. |
| `PAYPAL_CLIENT_SECRET` | sample value | PayPal client secret. | Store securely in secrets management. |
| `PAYPAL_MODE` | `sandbox` | PayPal environment mode. | Use `live` in production. |

## Social authentication

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `GOOGLE_ENABLED` | `False` | Enables Google OAuth provider. | Enable only with valid Google credentials. |
| `GOOGLE_CLIENT_ID` | sample value | Google OAuth client ID. | Set from Google Cloud Console. |
| `GOOGLE_CLIENT_SECRET` | sample value | Google OAuth client secret. | Store securely in secrets management. |
| `GITHUB_ENABLED` | `False` | Enables GitHub OAuth provider. | Enable only with valid GitHub credentials. |
| `GITHUB_CLIENT_ID` | sample value | GitHub OAuth client ID. | Set from GitHub OAuth Apps. |
| `GITHUB_CLIENT_SECRET` | sample value | GitHub OAuth client secret. | Store securely in secrets management. |
| `FACEBOOK_ENABLED` | `False` | Enables Facebook OAuth provider. | Enable only with valid Facebook credentials. |
| `FACEBOOK_CLIENT_ID` | sample value | Facebook OAuth client ID. | Set from Meta for Developers. |
| `FACEBOOK_CLIENT_SECRET` | sample value | Facebook OAuth client secret. | Store securely in secrets management. |
| `SOCIAL_AUTH_REDIRECT_URL` | `http://localhost:3000/auth/callback` | Frontend callback URL after OAuth login. | Set to the deployed frontend callback route. |

## Analytics

| Setting | Default | What it does | How to modify |
| --- | --- | --- | --- |
| `ANALYTICS_ENABLED` | `False` | Enables analytics providers. | Enable only when provider credentials are configured. |
| `ANALYTICS_PROVIDER` | `posthog` | Active analytics provider. | Set to `posthog` or `mixpanel`. |
| `POSTHOG_API_KEY` | empty | PostHog project API key. | Set from your PostHog project. |
| `POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog API host. | Change for self-hosted or regional PostHog. |
| `MIXPANEL_PROJECT_TOKEN` | empty | Mixpanel project token. | Set from your Mixpanel project. |
| `MIXPANEL_API_SECRET` | empty | Mixpanel API secret. | Store securely in secrets management. |
| `MIXPANEL_API_HOST` | `https://api.mixpanel.com` | Mixpanel API host. | Change for proxying or custom endpoints if needed. |

## Runtime-editable versus environment-only values

- Values listed in `NON_RUNTIME_EDITABLE_SETTING_KEYS` are environment-only because they are secrets, connection strings, or infrastructure settings.
- Values in `PUBLIC_GENERAL_SETTING_KEYS` are safe to expose through the system capability/config APIs.
- If you add a new setting, update both lists deliberately instead of relying on defaults.

## Recommended change process

1. Add or update the environment variable in `backend/.env` or deployment configuration.
2. Restart the backend and any affected workers.
3. Verify the effective value through the system configuration endpoint or application behavior.
4. If the change affects a frontend-exposed capability, reload the frontend and confirm the corresponding page reflects the new setting.