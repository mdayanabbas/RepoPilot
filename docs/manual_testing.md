# Manual Testing

## Start Backend

From the repository root:

```bash
uvicorn backend.app.main:app --reload
```

The API should be available at `http://127.0.0.1:8000`.

## Check LLM Providers

```bash
curl http://127.0.0.1:8000/api/v1/llm/providers
```

Expected: configured primary and fallback providers, plus supported providers.

## Test LLM JSON

Set `GROQ_API_KEY` for Groq or run LM Studio locally with a loaded model. Then:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/llm/test \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Return valid JSON with status ok and a short message.\"}"
```

Or run:

```bash
python -m backend.app.scripts.smoke_test_llm
```

## Analyze FastAPI Fixture

```bash
python -m backend.app.scripts.smoke_test_analysis \
  backend/tests/fixtures/fastapi_cors_issue \
  "Browser login requests to POST /api/login fail because CORS is not configured."
```

Expected: framework `fastapi`, selected files including `main.py` and/or `routes/auth.py`, a fix plan, and trace steps.

## Analyze Flask Fixture

```bash
python -m backend.app.scripts.smoke_test_analysis \
  backend/tests/fixtures/flask_auth_issue \
  "POST /api/login returns 401 for valid demo credentials."
```

Expected: framework `flask`, selected auth files, a fix plan, and trace steps.

## Check Traces

Use the `run_id` printed by the smoke analysis script:

```bash
curl http://127.0.0.1:8000/api/v1/traces/<run_id>
```

Traces are in memory, so they are only available from the backend process that created them.
