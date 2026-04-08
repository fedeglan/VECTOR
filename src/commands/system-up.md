# /system-up

Start the full system and provide everything the human needs to test it.

## What you do

### Step 1 — Pre-flight checks

```bash
# Check Docker is running
docker info > /dev/null 2>&1 || echo "Docker is not running"

# Check .env exists
test -f .env || echo ".env file missing — copy from .env.example"

# Check required ports are free
for port in 5432 8000 5173; do
  lsof -i :$port > /dev/null 2>&1 && echo "Port $port is in use"
done
```

If any check fails, fix it or tell the human what to do.

### Step 2 — Start the system

```bash
# Build and start all services
docker compose up -d --build

# Wait for services to be healthy
echo "Waiting for services..."
sleep 5

# Check all services are running
docker compose ps
```

If any service failed to start, run `docker compose logs <service> --tail=50` and diagnose.

### Step 3 — Apply migrations and seed data

```bash
# Apply database migrations
docker compose exec backend alembic upgrade head

# Run seed data (if seed script exists)
docker compose exec backend python -m backend.scripts.seed
```

### Step 4 — Verify health

```bash
# Check backend is responding
curl -s http://localhost:8000/docs > /dev/null && echo "✓ Backend: http://localhost:8000" || echo "✗ Backend not responding"

# Check frontend is responding
curl -s http://localhost:5173 > /dev/null && echo "✓ Frontend: http://localhost:5173" || echo "✗ Frontend not responding"

# Check database
docker compose exec db pg_isready && echo "✓ Database: healthy" || echo "✗ Database not responding"
```

### Step 5 — Report to the human

Provide a complete testing brief:

```
🚀 System is up and running

## Access
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API docs (Swagger)**: http://localhost:8000/docs

## Test credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@<app>.com | <password> |
| Manager | manager@<app>.com | <password> |
| Analyst | analyst@<app>.com | <password> |

(Credentials from seed data script)

## Navigation flow to test
1. Login as admin → verify dashboard loads with correct data
2. Navigate to <primary view> → verify <primary action> works
3. <Step-by-step flow matching the current phase's scope>

## What to pay attention to
- [ ] <Critical workflow 1 — what could go wrong>
- [ ] <Critical workflow 2>
- [ ] <Edge case to check>
- [ ] <Permission boundaries — test as different roles>

## Known limitations (this phase)
- <Feature X is not yet implemented — coming in V1>
- <Feature Y uses mock data — will be real in next phase>

## If something breaks
Describe what you see and I'll run /debug to fix it.
```

Adjust the credentials, navigation flow, and attention items based on:
- Which phase is currently being tested (MVP, V1, V2)
- What issues have been completed (read SESSIONS.md)
- What the PRD says the primary workflows are

### If the system won't start

Do NOT just report failure. Debug it:
1. Read all container logs
2. Check the most common causes: missing env vars, port conflicts, migration errors
3. Fix what you can
4. Report what you fixed and what still needs human intervention