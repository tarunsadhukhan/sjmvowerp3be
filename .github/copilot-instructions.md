## Vowerp3be — AI coding agent instructions

These notes help an AI coding agent get productive quickly in this backend repo (FastAPI + SQLAlchemy, multi-tenant). Keep suggestions focused, minimal, and safe.

1) Big picture
- FastAPI app in `src/main.py` that mounts many routers. The item master APIs live under `/api/itemMaster` in `src/masters/items.py`.
- Multi-tenant DB approach: `src/config/db.py` derives the tenant DB name from request headers (subdomain, x-forwarded-host, referer or explicit `subdomain` header) and constructs a tenant MySQL URL. `get_tenant_db` yields a SQLAlchemy session bound to that tenant DB.
- Data access: mix of SQLAlchemy ORM models (e.g. `src/masters/models.py`) and raw SQL Text queries in `src/masters/query.py`. Queries use `sqlalchemy.text()` with named bind params (e.g. `:co_id`, `:item_id`).
- For table structure context, use the SQL prompts under `dbqueries/` (e.g. `procurement.sql`, `usertables.sql`); they describe how each table was generated and help when drafting new queries, models, or schemas.
- Key folders under `src/`:
  - `authorization/` — login flows, JWT refresh helpers, auth routers, and models used for validating users.
  - `common/` — shared logic split by persona (`companyAdmin`, `ctrldskAdmin`, `portal`); utilities here are reused across modules and tenants.
  - `config/` — project-wide configuration (database engines, CORS, environment loading). Treat this as the single source for connection/session helpers.
  - `masters/` — APIs and data access for master data. Follows the pattern of `models.py`, `query.py`, and feature routers (e.g. `items.py`).
  - Module folders (e.g. `procurement/`) — contain feature-specific endpoints. Each module should include `query.py` for SQL text, optional `models.py`/`schemas.py` for ORM/Pydantic definitions, and one or more router files (`indent.py`, etc.) that orchestrate requests. Modules may call into `masters` or `common` when business logic overlaps.
  - When introducing a new module, mirror the `procurement/` structure so DB mutations and schemas stay discoverable even if only part of the stack (e.g. `models.py`) is used initially.

2) How to run & test (developer workflow)
- Local dev (venv): activate your Python environment and run the app with uvicorn: `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`.
- Docker: project includes a Dockerfile. Build: `docker build -t vowerp-backend .` and run with `docker run -d -p 8000:8000 --env-file .env --name vowerp3be vowerp3be-docker`.
- CI: workflow in `.github/workflows/deploy.yml` installs deps and builds/pushes a Docker image to ECR; tests may be run inside the built image using `pytest`.

3) Important repo conventions & patterns
- Multi-tenant lookup: Always pass `co_id` or rely on `get_tenant_db` which uses request headers to select the tenant DB. Many endpoints expect `co_id` as a query param; validate it early (raise 400 if missing).
- SQL Text queries: `src/masters/query.py` functions return `sqlalchemy.text` objects. Always execute them with a parameter dict matching the named binds. Example: `db.execute(get_item_table(co_id), {"co_id": int(co_id), "search": search_param})`.
- Passing NULL: use Python `None` (not string "null"). When a query binds `:item_id` and you want SQL NULL, pass `{"item_id": None}`.
- UOM and other lookups: Some query functions (e.g. `get_uom_list`) accept no params; do not pass `co_id` unless the function signature requires it.

4) Auth and token handling
- Auth helpers are in `src/authorization/utils.py`. Endpoints commonly use `Depends(get_current_user_with_refresh)` which will re-issue an access token using a refresh token stored in the default DB when access token is expired. The function reads the refresh token from `con_user_master` using a DB session created from `src/config/db.py`'s `default_engine`.
- Cookie name: `access_token`. Production cookie domain is `.vowerp.co.in` when `ENV=production`.

5) Files and hotspots to inspect when fixing bugs
- `src/masters/items.py` — primary place for item APIs, duplicate checks, and recent fixes. Look here for parameter handling and error responses.
- `src/masters/query.py` — canonical SQL queries. If you change binds, update callers to pass the same named params.
- `src/config/db.py` — tenant resolution logic. Mistakes here can cause the wrong DB/connection to be used.
- `src/authorization/utils.py` — JWT creation/refresh/verification; modify carefully.

6) Examples to copy/paste
- Executing a parameterized text query and converting rows:
  - q = get_item_table(co_id)
  - rows = db.execute(q, {"co_id": int(co_id), "search": search_param}).fetchall()
  - data = [dict(r._mapping) for r in rows]

7) Common pitfalls
- Do not call `int("null")`. Use `None` to represent SQL NULL when passing binds.
- Keep parameter names consistent: `:co_id`, `:item_id`, `:item_grp_id`, `:search` are used widely.
- Many functions return `text(sql)`; they are not ORM queries and must be executed via `db.execute()`.
- When adding or updating endpoints, run a quick smoke test with the tenant header or `co_id` query param to ensure `get_tenant_db` picks the right DB.

8) When to prefer ORM vs text SQL
- Use raw `text()` queries when they contain complex recursive CTEs (the project already uses them for hierarchical item groups). Use ORM for simple CRUD and when adding new models if consistent with surrounding code.

9) Safety & tests
- Make minimal changes to existing SQL unless necessary; modify callers first to match parameter names.
- Add small unit tests in `test/` when changing business logic; the repo uses `pytest`.

If any section is unclear or you'd like examples for a concrete endpoint (for example, `CreateItem` or `item_create_setup`) tell me which file or flow and I'll expand the instructions with precise code snippets and tests.
