# Local Setup

1. Copy backend, frontend, and mobile environment templates into working `.env` files.
   Backend note: the backend settings model reads process environment and the repository-root `.env` file by default, while `backend/.env.example` is the template reference you should copy values from during setup.
2. Start infrastructure with `docker compose up db redis`.
3. Install backend dependencies and run migrations.
   This creates the schema and seeds the `generalsetting` table from the current environment.
4. Install frontend dependencies and start the Next.js app.
5. Install Flutter dependencies and launch the mobile app.
6. Validate runtime discovery with `/api/v1/system/capabilities/`, `/api/v1/system/providers/`, and `/api/v1/system/general-settings/`.
7. For local SQLite development, confirm that the backend is using `app.db` unless you intentionally override the database name.
8. If you change runtime-editable settings in the database, remember that some startup-sensitive behavior such as middleware, worker bootstrap, and DB engine options may still require a restart.
