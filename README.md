# RepoPilot

Local-first AI debugging agent for backend repositories.

RepoPilot analyzes a local or Git-backed Python backend, detects the framework, extracts routes and code structure, retrieves relevant files for an issue, and asks an LLM for a structured fix plan. Phase 1 focuses on FastAPI and Flask projects.

## Current Archotecture Diagram

<img width="2636" height="2564" alt="repo" src="https://github.com/user-attachments/assets/8ae0462c-69aa-4d86-9071-1d5f291426e9" />



## Current Scope

RepoPilot currently supports:

- Local and Git repository loading into a managed workspace
- File scanning and framework detection
- Python AST intelligence for imports, functions, classes, and symbols
- FastAPI and Flask route extraction
- Retrieval and context building for issue-focused analysis
- Groq and LM Studio LLM providers
- Structured fix-plan generation and schema validation
- Trace logging for workflow, tool, and model calls
- SQLite persistence for repositories, analysis runs, retrieval results, fix plans, traces, and architecture graphs
- Analysis run history APIs
- Git history intelligence and Git-aware retrieval boosts
- Static architecture graph building with Mermaid export
- Static knowledge graph building for debugging relationships

Not included yet:

- Code patch generation
- Validation command execution
- Frontend UI
- Docker execution
- GitHub API integration

## Setup

Use Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Create a local environment file:

```powershell
copy .env.example .env
```

Configure one or both LLM providers:

- Groq: set `GROQ_API_KEY` and `GROQ_MODEL`
- LM Studio: start the local server and set `LMSTUDIO_BASE_URL` and `LMSTUDIO_MODEL`

Local database files such as `repopilot.db` are intentionally ignored by Git.

## Run The Backend

```bash
uvicorn backend.app.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

## Main APIs

Repository loading:

```text
POST /api/v1/repositories/load
```

Run full analysis:

```text
POST /api/v1/analysis/run
```

List analysis history:

```text
GET /api/v1/analysis?limit=20&offset=0
```

Fetch one analysis run:

```text
GET /api/v1/analysis/{analysis_run_id}
```

Fetch architecture graph for an analysis:

```text
GET /api/v1/analysis/{analysis_run_id}/architecture?format=json
GET /api/v1/analysis/{analysis_run_id}/architecture?format=mermaid
```

Build architecture graph directly:

```text
POST /api/v1/architecture/build
```

Inspect LLM providers:

```text
GET /api/v1/llm/providers
POST /api/v1/llm/test
```

Fetch traces:

```text
GET /api/v1/traces/{trace_run_id}
```

## Analysis IDs

Analysis responses include two IDs:

- `analysis_run_id`: database ID for analysis history and persisted results
- `trace_run_id`: trace ID for workflow/model/tool event logs

Use `analysis_run_id` with:

```text
GET /api/v1/analysis/{analysis_run_id}
GET /api/v1/analysis/{analysis_run_id}/architecture
```

Use `trace_run_id` with:

```text
GET /api/v1/traces/{trace_run_id}
```

## Smoke Tests

Run a simple LLM provider smoke test:

```bash
python -m backend.app.scripts.smoke_test_llm
```

Run analysis against the FastAPI fixture:

```powershell
python -m backend.app.scripts.smoke_test_analysis ^
  backend/tests/fixtures/fastapi_cors_issue ^
  "Browser login requests to POST /api/login fail because CORS is not configured."
```

Run analysis against the Flask fixture:

```powershell
python -m backend.app.scripts.smoke_test_analysis ^
  backend/tests/fixtures/flask_auth_issue ^
  "POST /api/login returns 401 for valid demo credentials."
```

The analysis smoke script prints both `analysis_run_id` and `trace_run_id`.

## Tests

```bash
pytest
```

## Useful Docs

- Manual testing: `docs/manual_testing.md`
- Demo scenarios: `docs/demo_scenarios.md`
- API notes: `docs/api.md`
- Architecture notes: `docs/architecture.md`
