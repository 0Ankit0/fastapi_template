# Notifications

- Duplicate device registrations should update the existing device instead of creating noise.
- Push preference enabled with no valid device should not break notification creation.
- Provider fallback should not create duplicate deliveries when the primary succeeds late.
- Legacy push-subscription endpoints must remain compatible while device registry is adopted.
