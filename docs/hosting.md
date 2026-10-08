# Hosting and Supabase cutover

Target: TanStack Start on the existing Vercel frontend, FastAPI on Render, all application records and staff sessions in Supabase PostgreSQL. Current live configuration has not been inspected. This document describes the intended deployment after this branch is merged.

## Render configuration

Use a Python Web Service with root directory `api`.

- Build: `pip install -r requirements.txt && python -m app.train`
- Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health/live`; verify `/health/ready` and `/health/model` separately before release.
- Database migrations run before the API process on the current free-service Blueprint. Run one deployment at a time. Builds never seed or modify the database.
- A paid service can run migrations in its pre-deploy phase. Do not configure hooks unavailable on the chosen plan.
- The model is generated during the build, not on the ephemeral runtime filesystem after deployment.

Set `DATABASE_URL`, `DATABASE_URL_DIRECT`, `AUTH_SECRET`, `DEMO_PASSWORD`, and `WEB_ORIGIN` as server environment variables. The auth secret must be random, at least 32 characters, and not a placeholder. The demo password must be unique, at least 12 characters, and not a placeholder. Preserve the existing auth secret during migration unless deliberately invalidating sessions.

Editing `render.yaml` alone does not prove an existing manually configured service picked up the change. Compare its actual build/start commands, environment and deployed commit with this document. A database-healthy response is not proof of seeded accounts, model availability or correct CORS.

## Supabase connections and access

Copy the **Session pooler** URI from Supabase Connect for `DATABASE_URL` (port 5432). Use the exact hostname and `postgres.PROJECT_REF` username provided. Percent-encode reserved characters in the password. Set `sslmode=require`, or the stronger certificate-verified mode with the appropriate CA configuration.

Set `DATABASE_URL_DIRECT` to the direct URI on reachable IPv6, or the Session pooler URI on IPv4. Do not use Transaction pooler port 6543 for migrations. A blank value falls back to `DATABASE_URL`.

The API uses psycopg, bounded connection timeouts and five SQLAlchemy connections per process without overflow. Prepared statements are disabled for pooler compatibility. Reassess the connection budget before adding workers.

Revision `0002_backend_only_access` enables RLS and revokes PUBLIC/anon/authenticated access on the application's 20 tables and Alembic version table. The backend must connect as the table owner (the project postgres role for this submission); an unprivileged role without appropriate backend policies will correctly be denied. No browser Supabase key or service-role key is required. Keep database credentials server-only. Disable Supabase's Data API for the dedicated project when not needed; retain migration protections as defense in depth.

These protections are scoped to known application tables; every future migration must protect new tables. The revision's downgrade intentionally does not restore public access.

## Existing-data transfer

Preserve existing data by default. Use a dedicated target and a backup. Inventory source tables and Alembic revision; rehearse restoring the application schema/data with ownership and grants excluded. Do not restore source database roles, extensions indiscriminately, or overwrite Supabase `auth`/`storage` schemas. Apply the security revision after restore. Existing schema should retain its genuine Alembic revision; do not stamp an arbitrary revision to hide a mismatch.

Pause source writes for final copy, reconcile per-table counts and critical records, then change both database URLs and redeploy. Verify staff roles/passwords, case/evidence/draft links, audit history and batch summaries. Do not run demo reset or seed over restored records. Keep the backup and source until acceptance; do not delete Neon as part of the first cutover.

## Fresh demo initialization

Only for a confirmed empty target, set the same server environment in a trusted local shell. From `api/`:

```sh
alembic upgrade head
python -m app.seed
```

`python -m app.seed` is a separate one-time operation. It creates operator accounts and synthetic cases; later runs skip an already initialized case book. Existing user passwords are not updated when `DEMO_PASSWORD` changes. Seeding can take minutes across a remote database and must not be put back into every build or server start. No Docker installation is required.

## Frontend configuration

Set `VITE_API_URL` to the actual HTTPS Render origin and rebuild the frontend. Vite embeds this setting at build time. Set Render `WEB_ORIGIN` to the exact frontend origin (scheme and host, no trailing path or slash). Production origins belong in the allowlist; `*` is not the fix for failed login requests.

Authentication uses a Bearer token held in sessionStorage. Password hashes, staff accounts and session hashes live in Supabase through FastAPI. Supabase Auth is not part of this database migration. Keep privileged admin credentials out of publicly shared judge instructions.

## Recovery checklist

1. Record actual URLs and deployed SHA. Inspect the first failing browser request and Render error without printing secrets.
2. `/health/live` must return 200; otherwise inspect startup, migration, bind port and deployment logs.
3. `/health/ready` must return 200; otherwise inspect connection host/port, credentials, TLS, network reachability and revision. This endpoint currently checks schema availability, not demo completeness.
4. `/health/model` must return 200; otherwise confirm build-time training and packaged model artifact.
5. Login with the seeded analyst, load overview/queue/case, verify allowed and blocked actions, and refresh. A 503 from login can mean `AUTH_SECRET` is still a placeholder. A 401 can mean wrong credentials or a user not seeded into this database.
6. Inspect CORS and `VITE_API_URL` when API health works but the browser fails. Expect a wake delay on a sleeping free instance; retry explicitly, never replay a mutation silently.
7. Redeploy/restart and verify persistence. Record counts and migration version before accepting the cutover.

## Verification

Local API tests use a SQLite behavior adapter. The CI `TEST_POSTGRES_URL` points only to a disposable PostgreSQL service and exercises fresh migrations with an encoded password plus browser-role denial. Never set this test variable to a hosted project: the test creates roles and default privileges for its fixture.

Hosted migration, login and browser acceptance remain required after CI. Logs and connectors for Render/Supabase are not available in this session.

References:
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://render.com/docs/deploys
