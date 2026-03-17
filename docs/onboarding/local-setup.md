# Local Setup

1. Copy backend, frontend, and mobile environment templates into working `.env` files.
2. Start infrastructure with `docker compose up db redis`.
3. Install backend dependencies and run migrations.
   This creates the schema and seeds the `generalsetting` table from the current environment.
4. Install frontend dependencies and start the Next.js app.
5. Install Flutter dependencies and launch the mobile app.
6. Validate runtime discovery with `/api/v1/system/capabilities/`, `/api/v1/system/providers/`, and `/api/v1/system/general-settings/`.
7. For local SQLite development, confirm that the backend is using `app.db` unless you intentionally override the database name.
