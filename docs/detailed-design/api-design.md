# API Design

## System Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/system/capabilities/` | Enabled modules, active providers, fallbacks |
| `GET /api/v1/system/providers/` | Provider readiness by channel |
| `GET /api/v1/system/health/` | Liveness signal |
| `GET /api/v1/system/ready/` | Readiness signal |

## Notification Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/notifications/preferences/` | Fetch current user preferences |
| `PATCH /api/v1/notifications/preferences/` | Update channel flags |
| `GET /api/v1/notifications/devices/` | List registered devices |
| `POST /api/v1/notifications/devices/` | Register device token or subscription |
| `DELETE /api/v1/notifications/devices/{id}/` | Remove a registered device |
| `GET /api/v1/notifications/push/config/` | Public runtime push config |
| `PUT /api/v1/notifications/preferences/push-subscription/` | Legacy web push compatibility |
| `DELETE /api/v1/notifications/preferences/push-subscription/` | Legacy cleanup path |
