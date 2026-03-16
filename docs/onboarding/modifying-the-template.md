# Modifying the Template

## Safe Modification Workflow

1. Identify the layer you are changing: backend, frontend, mobile, docs, or infrastructure.
2. Update the source-of-truth config first.
3. Extend interfaces and registries before editing route or UI logic.
4. Update clients to consume capability discovery instead of hard-coded assumptions.
5. Add or adjust tests.
6. Update docs and run the validator.

## Common Modification Patterns

### Add a New Provider

- Add settings in `config.py`.
- Create an adapter in the backend provider layer.
- Register it in the communications or analytics factory.
- Expose any client-safe values through discovery APIs.
- Add web/mobile registration or SDK wiring if the provider is client-facing.

### Add a New Feature Flagged Module

- Add a `FEATURE_*` setting.
- Gate router registration in `main.py`.
- Hide or show related UI through capability discovery.
- Document what happens when the module is disabled.

### Change an Existing Public API

- Preserve compatibility when possible.
- Update web and mobile consumers in the same change.
- Add migration notes to the docs if downstream projects might already depend on the old contract.

## Files You Usually Touch

- Backend settings: [config.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/core/config.py)
- Backend app wiring: [main.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/main.py)
- System discovery APIs: [api.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/system/api.py)
- Web runtime hooks: [use-system.ts](/Users/ankit/Projects/Python/fastapi/fastapi_template/frontend/src/hooks/use-system.ts)
- Mobile runtime bootstrap: [notification_bootstrapper.dart](/Users/ankit/Projects/Python/fastapi/fastapi_template/mobile/lib/features/notifications/presentation/widgets/notification_bootstrapper.dart)

## Do Not Skip

- Update `backend/.env.example`
- Update `docs/`
- Run backend, frontend, mobile, and docs checks
