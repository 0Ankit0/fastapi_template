# Environment Profiles

| Profile | Use |
|---|---|
| `local` | Local cloning, feature experimentation, and UI development |
| `staging` | Integrated provider and deployment rehearsal |
| `production` | Live traffic with hardened hosts, secrets, and monitoring |

Each profile should define feature flags, primary providers, fallback order, database targets, Redis settings, and public client config.
