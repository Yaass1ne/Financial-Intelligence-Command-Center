# FINCENTER — Quick Start Guide

Get the full system running in under 5 minutes.

---

## What you'll have running

| Service | URL | Purpose |
|---------|-----|---------|
| FastAPI backend | http://localhost:8080 | REST API + AI chat |
| Swagger docs | http://localhost:8080/docs | Interactive API explorer |
| React dashboard | http://localhost:5173 | 6-page financial dashboard |
| Neo4j browser | http://localhost:7474 | Graph database explorer |

---

## Prerequisites

Make sure these are installed and running before you start:

- **Python 3.10+** — `python --version`
- **Node.js 18+** — `node --version`
- **Docker Desktop** — must be running (check the system tray icon)
- **Groq API key** — free at https://console.groq.com

---

## Daily Startup (system already set up)

Open **two terminal windows** in the project folder.

**Terminal 1 — API Server:**
```
cd "C:\Users\Yassine\Desktop\TASK 2"
start.bat
```
Wait until you see: `Application startup complete.`

**Terminal 2 — Dashboard:**
```
cd "C:\Users\Yassine\Desktop\TASK 2\dashboard"
npm run dev
```
Open the URL printed by Vite (usually http://localhost:5173).

That's it. Both services are running.

---

## First-Time Setup (starting from scratch)

### Step 1 — Start the databases

```
docker compose up -d
```

This starts Neo4j, PostgreSQL, and Redis as Docker containers. Wait ~15 seconds, then verify:

```
docker compose ps
```

All three services should show as `healthy` or `running`.

Neo4j is accessible at http://localhost:7474 with credentials `neo4j / fincenter2024`.

---

### Step 2 — Install Python dependencies

```
pip install -r requirements.txt
```

---

### Step 3 — Configure environment

```
copy .env.example .env
```

Open `.env` and set your Groq API key:
```
GROQ_API_KEY=gsk_your_key_here
```

Everything else (Neo4j URI, passwords, ports) is pre-configured with defaults that match `docker-compose.yml`.

---

### Step 4 — Generate synthetic data

```
python scripts/producer.py --output data/synthetic/ --num-invoices 500 --num-contracts 50
```

This creates realistic, slightly messy financial data:
- `data/synthetic/budgets/` — 3 years of budget Excel files
- `data/synthetic/invoices/` — 500 JSON invoice files
- `data/synthetic/contracts/` — 50 JSON contract files

---

### Step 5 — Run the ingestion pipeline

```
python -m src.ingestion.pipeline --input data/synthetic/ --output data/processed/
```

This parses all documents, extracts entities, validates data quality, and writes processed JSON to `data/processed/metadata/`.

---

### Step 6 — Load data into Neo4j

```
python load_neo4j.py
```

This reads the processed JSON files and creates nodes and relationships in Neo4j.

Expected output:
```
Loaded 484 invoices
Loaded 50 contracts
Loaded 28 budget items
Done.
```

---

### Step 7 — Install dashboard dependencies

```
cd dashboard
npm install
cd ..
```

---

### Step 8 — Start everything

Follow the **Daily Startup** steps above.

---

## Verify it's all working

Run these checks after startup:

```bash
# 1. API server healthy?
curl http://localhost:8080/health
# Expected: {"status":"healthy","services":{"neo4j":"connected","vectorstore":"connected"}}

# 2. Budget data loaded?
curl "http://localhost:8080/api/budgets/summary?year=2024"
# Expected: JSON array of 7 departments with budget/actual/variance

# 3. Overdue invoices loaded?
curl "http://localhost:8080/api/invoices/overdue?days=0"
# Expected: JSON array of 484 invoices

# 4. AI chat working?
curl -X POST http://localhost:8080/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"Which department is most over budget?\"}"
# Expected: JSON with "response" field containing AI answer
```

---

## Dashboard Navigation

Once the dashboard is open, use the left sidebar to navigate:

| Page | Path | What it shows |
|------|------|---------------|
| Budget Augmented | `/` | Department budget vs. actual, variance charts |
| Contracts & Clauses | `/contracts` | Expiring contracts, urgency levels, auto-renewal |
| Invoices & Treasury | `/invoices` | Overdue invoices, outstanding amounts, urgency |
| Alerts | `/alerts` | All financial risk signals in one view |
| Simulations | `/simulations` | Interactive budget/cashflow scenario modeling |
| AI Assistant | `/chat` | Ask any financial question in plain English |

---

## Common Problems

### "Port 8080 already in use"

An old server process is still running. The `start.bat` script handles this automatically — just use it instead of running Python directly.

If you still need to kill it manually:
```
netstat -ano | findstr :8080
powershell -Command "Stop-Process -Id <PID> -Force"
```

### Dashboard shows "Failed to fetch"

The API server must be started before the dashboard. Make sure `start.bat` completed successfully (shows `Application startup complete.`) before opening the browser.

### "Neo4j connection refused"

Docker Desktop is not running or Neo4j hasn't finished starting up.
```
docker compose ps          # Check status
docker compose restart neo4j   # Restart if needed
docker compose logs neo4j  # See what went wrong
```

### AI chat gives no response or errors

Check that `GROQ_API_KEY` is set in your `.env` file. Get a free key at https://console.groq.com.

### Days overdue all show "0" or "NaN"

The running server is an old instance that loaded old code. Use `start.bat` — it kills any existing process first.

---

## Stopping the project

```
# Stop the API server: press Ctrl+C in Terminal 1
# Stop the dashboard: press Ctrl+C in Terminal 2

# Stop Docker containers (data is preserved):
docker compose down

# Stop Docker AND wipe all data (use with caution):
docker compose down -v
```

---

## Neo4j Browser (optional)

Open http://localhost:7474 and log in with `neo4j / fincenter2024` to run Cypher queries directly:

```cypher
// See all node types and counts
MATCH (n) RETURN labels(n) AS type, COUNT(n) AS count

// Top 10 most overdue invoices
MATCH (i:Invoice)
WHERE i.due_date < date()
RETURN i.id, i.vendor, i.amount,
       duration.inDays(i.due_date, date()).days AS days_overdue
ORDER BY days_overdue DESC LIMIT 10

// Budget performance for 2024
MATCH (b:Budget {year: 2024})
WITH b.department AS dept, sum(b.budget) AS budget, sum(b.actual) AS actual
RETURN dept, budget, actual, (actual - budget) AS variance
ORDER BY variance DESC
```

---

For full documentation see [README.md](README.md).
