# Modifying the Template

Use this document when you already understand the project structure and want a safe pattern for changing it. If you are new to the repo, read [project-orientation.md](/Users/ankit/Projects/Python/fastapi/fastapi_template/docs/onboarding/project-orientation.md) first.

## Safe Modification Workflow

1. Identify the layer you are changing: backend, frontend, mobile, docs, or infrastructure.
2. Confirm the source of truth for that behavior.
   Usually this is backend config, provider registries, system discovery APIs, or data models.
3. Update the source-of-truth config first.
4. Extend interfaces and registries before editing route or UI logic.
5. Update clients to consume capability discovery instead of hard-coded assumptions.
6. Add or adjust tests.
7. Update docs and run the validator.

## Common Modification Patterns

### Add a New Provider

- Add settings in `config.py`.
- Create an adapter in the backend provider layer.
- Register it in the communications or analytics factory.
- Expose any client-safe values through discovery APIs.
- Add web/mobile registration or SDK wiring if the provider is client-facing.
- Update env templates and provider docs.

### Add a New Feature Flagged Module

- Add a `FEATURE_*` setting.
- Gate router registration in `main.py`.
- Hide or show related UI through capability discovery.
- Document what happens when the module is disabled.
- Add tests for both enabled and disabled states when practical.

### Add or Change Operational Behavior

- Start by checking whether the project already has a config group for that concern.
- If the behavior should be configurable, add or reuse a setting instead of hard-coding a new constant.
- Wire the setting into the actual runtime entrypoint:
  - `main.py` for app startup or middleware
  - service layers for business logic
  - provider adapters for external integrations
  - client runtime hooks for browser or mobile-visible behavior
- Decide whether the setting is env-only, runtime-editable, or public.

### Change an Existing Public API

- Preserve compatibility when possible.
- Update web and mobile consumers in the same change.
- Add migration notes to the docs if downstream projects might already depend on the old contract.

## Files You Usually Touch

- Backend settings: [config.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/core/config.py)
- Backend app wiring: [main.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/main.py)
- Runtime override flow: [settings_store.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/core/settings_store.py)
- System discovery APIs: [api.py](/Users/ankit/Projects/Python/fastapi/fastapi_template/backend/src/apps/system/api.py)
- Web runtime hooks: [use-system.ts](/Users/ankit/Projects/Python/fastapi/fastapi_template/frontend/src/hooks/use-system.ts)
- Mobile runtime bootstrap: [notification_bootstrapper.dart](/Users/ankit/Projects/Python/fastapi/fastapi_template/mobile/lib/features/notifications/presentation/widgets/notification_bootstrapper.dart)

## Do Not Skip

- Update `backend/.env.example`
- Update any root/runtime env handling notes if the loading path changes
- Update `docs/`
- Run backend, frontend, mobile, and docs checks
