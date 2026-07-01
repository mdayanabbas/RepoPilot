# Demo Scenarios

## Scenario 1: FastAPI CORS Issue

Fixture: `backend/tests/fixtures/fastapi_cors_issue`

Issue text:

```text
Browser login requests to POST /api/login fail because CORS is not configured.
```

Expected behavior:
- Framework detection returns `fastapi`.
- Route extraction finds `POST /api/login`.
- Retrieval selects `main.py` and `routes/auth.py`.
- LLM generates a fix plan that recommends adding `CORSMiddleware`.
- Trace includes repository loading, scanning, framework detection, retrieval, context building, and fix-plan generation.

## Scenario 2: Flask Login Issue

Fixture: `backend/tests/fixtures/flask_auth_issue`

Issue text:

```text
POST /api/login returns 401 for valid demo credentials.
```

Expected behavior:
- Framework detection returns `flask`.
- Route extraction finds `POST /api/login`.
- Retrieval selects `app.py`, `routes/auth.py`, and/or `services/auth_service.py`.
- LLM generates a fix plan focused on the login route and auth service.
- Trace includes the same analysis steps and model-call metadata.

## Scenario 3: Unknown Framework Skips LLM

Use a small folder with a plain Python file and no FastAPI or Flask dependency/import signals.

Issue text:

```text
The application fails on startup.
```

Expected behavior:
- Framework detection returns `unknown`.
- Route extraction returns no routes.
- Analysis returns `fix_plan: null`.
- Trace includes `unknown_framework_skip_llm` with status `skipped`.
- No LLM call is made.
