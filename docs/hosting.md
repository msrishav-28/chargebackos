# Hosting (locked stack)

This is the intended hosted shape; deployed services were not verified in the local review. Do not rewrite the website to Next.js.

## Push to `main` — what should happen

After each host is connected to GitHub **once**, a push to `main` should:

- **Vercel:** rebuild and publish the website. Set `VITE_API_URL` in the Vercel project. Auto-deploy is a dashboard switch: Project → Settings → Git → Production Branch `main`.
- **Render:** rebuild the API when `api/` or `render.yaml` changes (`autoDeployTrigger: commit`). Tables update with Alembic **before** traffic switches (`preDeployCommand`). The first successful deploy also seeds synthetic cases (`initialDeployHook`). Later deploys do not wipe the book.
- **Neon:** does not rebuild. It is the record store. Schema changes apply when Render runs Alembic. Do not add Render Postgres.

GitHub Actions (`.github/workflows/ci.yml`) run typecheck, lint, and API tests on every push. They do not replace Vercel or Render deploys.

## Website — Vercel

TanStack Start on Vercel is official when Nitro is in `vite.config.ts` (already present).

- Framework: TanStack Start
- Env: `VITE_API_URL` = the Render origin (e.g. `https://chargebackos-api.onrender.com`)
- Secrets without the `VITE_` prefix stay on the server only

## Server — Render (FastAPI)

Official FastAPI path. Create a **Web Service**, not a static site.

- Root Directory: `api`
- Branch: `main` (auto-deploy on each push that touches `api/` or `render.yaml`)
- Build: install, train scoring file, create tables, seed cases if the book is empty
- Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Free plan has **no Shell** and **no pre-deploy command**. Do not rely on them. If the first build seed is skipped or fails, run seed from your own computer against Neon (see below).
- Health: `/health/live`

Free plan facts (Render docs):

- Sleeps after **15 minutes** with no traffic
- Wake takes about **one minute**
- Open `/health/live` before a pitch
- **Do not** use Render free Postgres (30-day expiry). Use Neon.

## Database — Neon

Official SQLAlchemy path. Copy the connection string from Neon Connect.

- `DATABASE_URL` — **pooled** string (hostname contains `-pooler`) for the running API
- `DATABASE_URL_DIRECT` — **direct** string (no `-pooler`) for Alembic
- Keep `sslmode=require` (the API adds it for `neon.tech` hosts if missing)
- Runtime engine uses `pool_pre_ping=True` so a scaled-to-zero compute does not reuse a dead socket

Do not point FastAPI at Render’s free Postgres.

## Seed from your computer (free Render, no Shell)

Create a local `.env` in the project root (never commit it). Use the same Neon URLs, `AUTH_SECRET`, and `DEMO_PASSWORD` as Render.

From `api/`:

```text
alembic upgrade head
python -m app.seed
```

That writes staff and cases into Neon. Render then reads the same database. Later `python -m app.seed` skips if cases already exist.

## Sign-in across two hosts

`vercel.app` and `onrender.com` are different sites. Browser cookies do not follow automatically.

This pass uses a Bearer token after `/login`. A same-origin website proxy remains later if we want httpOnly cookies only.

## Docker Compose

`docker-compose.yml` is for **other developers** who want local Postgres. This machine does not need Docker if `DATABASE_URL` points at Neon.

## Model artifact release gate

The Render build now runs `python -m app.train` so a matching scoring file exists after each deploy. Restart still uses that build artifact until the next deploy. Do not reset Neon just to recreate a missing model. After deploy, seed once from Render Shell if the book is empty.

`python -m app.train` is database-free. `/health/model` returns 503 for missing, unreadable or incompatible artifacts. `/health/ready` returns 503 for an unavailable or uninitialized database. Existing records remain readable while new scoring fails closed to review.

Apply Alembic explicitly before initial seed; the seed command no longer creates tables outside Alembic. `AUTH_SECRET` must be random and at least 32 characters; `DEMO_PASSWORD` must be unique and at least 12 characters. Keep them in hosting secrets.

Evaluation uses persisted job rows with in-process execution. A restart can interrupt a run; a new scheduling request marks jobs older than 30 minutes failed. Admin reset is a separate destructive operation requiring explicit confirmation. It may take several minutes and replaces shared case history. If it times out, inspect the book before retrying.

Official reference: [Render free-service behavior](https://render.com/docs/free). No hosting settings or shared records were changed during the local review.
