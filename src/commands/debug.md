# /debug

Analyze and fix broken things in the codebase. Use this when something is not working and you need to figure out why.

## Before you start

Read these files:
- CLAUDE.md — patterns and conventions
- SESSIONS.md — latest entry for recent context

## Diagnostic protocol

### Step 1 — Reproduce the problem

If the human described a symptom, reproduce it:
```bash
# Try to start the system
docker compose up -d 2>&1

# Check service health
docker compose ps
docker compose logs --tail=50 <service>

# Try to run tests
pytest -x --tb=short 2>&1

# Try to run the frontend
cd frontend && npm run dev 2>&1
```

### Step 2 — Classify the problem

| Category | Symptoms | Common causes |
|----------|----------|---------------|
| **Won't start** | Service exits immediately, port already in use | Missing env vars, DB not running, migration not applied, port conflict |
| **Runtime error** | 500 errors, unhandled exceptions | Missing import, wrong type, null reference, missing DB column |
| **Test failure** | Tests fail that previously passed | Schema change without migration, mock data stale, import path change |
| **Build error** | Frontend/backend won't compile | Missing dependency, syntax error, circular import |
| **Data error** | Wrong data returned, empty responses | Query bug, wrong join, missing seed data, stale cache |
| **Integration error** | Frontend can't talk to backend | CORS, wrong port, wrong endpoint path, auth header missing |

### Step 3 — Diagnose

For each category, follow this diagnostic tree:

**Won't start:**
1. `docker compose logs <service> --tail=100` — read the actual error
2. Check `.env` against `.env.example` — any missing vars?
3. `alembic current` — is the DB schema up to date?
4. `lsof -i :<port>` — is the port already in use?

**Runtime error:**
1. Read the full traceback — what file, what line, what exception?
2. Check if the file was recently modified (look at SESSIONS.md)
3. Check if a dependency was added but not installed
4. Check if a migration was written but not applied

**Test failure:**
1. Run only the failing test with verbose output: `pytest tests/path/test_file.py::test_name -v --tb=long`
2. Compare the test's expectations against the current spec (api-spec.yaml or erd.dbml)
3. Check if the test's fixtures/mocks are stale

**Build error:**
1. Clear caches: `find . -type d -name __pycache__ -exec rm -rf {} +` or `rm -rf node_modules/.cache`
2. Check import paths — did a file get moved?
3. Check for circular imports: follow the import chain

**Data error:**
1. Query the DB directly to check what's stored
2. Check the repository layer — is the query correct?
3. Check if seed data exists

**Integration error:**
1. Check backend CORS settings
2. Check frontend API client base URL
3. Check if the endpoint exists: `curl http://localhost:8000/api/v1/<path>`
4. Check auth: is the JWT being sent?

### Step 4 — Fix

Apply the minimum fix that resolves the problem without changing unrelated code.

Rules:
- Fix only what is broken. Do not refactor adjacent code.
- If the fix requires changing a spec (api-spec.yaml, erd.dbml), STOP — that's a `/change-scope` situation.
- If the fix is in code from a previous issue, note it in the commit message.
- Write a test that would have caught this bug, if one doesn't already exist.

### Step 5 — Verify

1. Run the failing thing again — does it work now?
2. Run the full test suite — did the fix break anything else?
3. If the system was down, start it and verify it's healthy.

### Step 6 — Report

Tell the human:
```
🔧 Debug complete

Problem: <one sentence>
Root cause: <one sentence>
Fix: <what was changed>
Files modified: <list>
Tests: <passing/failing status>

Recommendation: <any follow-up action needed>
```

Log the fix in SESSIONS.md if it was significant.