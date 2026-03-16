# Local Setup

1. Copy backend, frontend, and mobile environment templates into working `.env` files.
2. Start infrastructure with `docker compose up db redis`.
3. Install backend dependencies and run migrations.
4. Install frontend dependencies and start the Next.js app.
5. Install Flutter dependencies and launch the mobile app.
6. Validate runtime discovery with `/api/v1/system/capabilities/` and `/api/v1/system/providers/`.
