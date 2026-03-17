# Provider Configuration

- Email: choose `EMAIL_PROVIDER` and optional `EMAIL_FALLBACK_PROVIDERS`.
- Push: choose `PUSH_PROVIDER` and configure Web Push, FCM, or OneSignal credentials.
- SMS: choose `SMS_PROVIDER` with Twilio or Vonage credentials.
- Analytics: choose `ANALYTICS_PROVIDER` with PostHog or Mixpanel credentials.
- Payments: enable the gateways needed for the downstream project.
- Public provider state can be inspected from `/api/v1/system/providers/` and `/api/v1/system/general-settings/`.
