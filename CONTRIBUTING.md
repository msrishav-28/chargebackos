# Contributing Guidelines

Thank you for contributing to this project. Because this codebase operates under strict enterprise standards, all contributions must meet high bars for correctness, security, and maintainability.

## Engineering Standards

Every line of code you write will be reviewed under hostile scrutiny. Keep the following rules in mind:

1. **Strict Typing:** No implicit `any`. Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to silence the compiler. If you must bypass the type system, you must leave a one-line comment explaining why.
2. **No Dead Code:** Do not commit unused imports, hanging routes, empty components, or commented-out blocks of code "just in case". 
3. **No Silent Failures:** Fail loudly on invariant violations. Never use empty catch blocks or ignore errors just to keep the UI from crashing.
4. **Security First:** Never commit secrets, credentials, or `.env` files with real values. Ensure authorization is checked on every read and write operation.

## UI and Design Rules

We do not use generic template styles. This project uses a highly specific design system detailed in `DESIGN.md`.

- **Do not invent colors.** Use the established CSS variables (e.g., `--color-indigo-navy`).
- **Do not introduce new fonts.** Stick to the typographic scale defined in the design document.
- **Do not bypass the component library.** If you need a button or an input, use the ones provided in `src/components/ui`. 

## Database Changes

The product schema lives in FastAPI (`api/`) on Neon. Alembic is the migration tool.

1. Do not make database changes without prior approval.
2. Add a new Alembic revision under `api/alembic/versions/`.
3. Never edit an existing migration that has already been applied.
4. Use `DATABASE_URL_DIRECT` (Neon host without `-pooler`) for Alembic. Use pooled `DATABASE_URL` for the running API.
5. Dropping tables or columns destroys stored records and must be explicitly authorized.
6. Do not rewrite the website to Next.js. Follow `AGENTS.md`.

## Submitting a Pull Request

1. Create a feature branch from `main`.
2. Ensure you have run the full test suite and it passes.
3. Ensure `npm run lint` and `npm run typecheck` complete with zero errors.
4. Describe your changes in plain English in the PR description, focusing on *what* the user will notice and *why* the change was made.
