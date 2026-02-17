# FINCENTER — Financial Intelligence Command Center

> An AI-powered platform that centralizes, analyzes, and visualizes the entire financial life of an enterprise using a graph database, vector search, and a large language model.

---

## Table of Contents

1. [What FINCENTER Does](#what-fincenter-does)
2. [System Architecture](#system-architecture)
3. [Components](#components)
   - [Backend — FastAPI](#backend--fastapi)
   - [Graph Database — Neo4j](#graph-database--neo4j)
   - [Vector Store — FAISS](#vector-store--faiss)
   - [AI Assistant — Groq / Llama 3.3 70B](#ai-assistant--groq--llama-33-70b)
   - [Ingestion Pipeline](#ingestion-pipeline)
   - [Simulation Engine](#simulation-engine)
   - [Frontend — React Dashboard](#frontend--react-dashboard)
4. [Dashboard Pages](#dashboard-pages)
5. [API Reference](#api-reference)
6. [Use Cases](#use-cases)
7. [Project Structure](#project-structure)
8. [Starting the Project](#starting-the-project)
9. [Troubleshooting](#troubleshooting)
10. [Data Management](#data-management)

---

## What FINCENTER Does

FINCENTER replaces 10–15 disconnected financial tools with a single platform. It ingests financial documents (budgets, invoices, contracts), stores them in a knowledge graph, and exposes everything through a REST API and an interactive dashboard with an AI assistant.

**Core capabilities:**
- Track budget vs. actual spending across all departments
- Monitor overdue invoices and outstanding cash flow
- Alert on contracts expiring within configurable timeframes
- Answer natural language questions about any financial data
- Run what-if simulations (budget cuts, cash flow forecasts, Monte Carlo modeling)
- Detect anomalies and generate proactive recommendations

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│   Budget Excel files    JSON Invoices    JSON Contracts          │
│                   Synthetic data (scripts/producer.py)           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                             │
│   src/ingestion/pipeline.py  ──▶  src/ingestion/parsers/        │
│   Parsers: JSON / Excel / PDF                                    │
│   Extractors: NER (spaCy), amounts, dates                        │
│   Validators: duplicates, anomalies, data quality                │
└────────────┬──────────────────────────┬─────────────────────────┘
             │                          │
             ▼                          ▼
┌────────────────────┐      ┌───────────────────────┐
│  Neo4j Graph DB    │      │   FAISS Vector Store   │
│  (Docker port 7687)│      │   (data/vectors/)      │
│                    │      │                        │
│  Nodes:            │      │  768-dim embeddings    │
│    Invoice         │      │  (all-mpnet-base-v2)   │
│    Contract        │      │  Semantic search       │
│    Budget          │      │  over all documents    │
│    Client, Vendor  │      └───────────────────────┘
│  Relationships:    │
│    GENERATES       │
│    SIGNED, PAYS    │
└────────┬───────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI — src/api/main.py                      │
│   Port 8080   ·   Swagger UI at /docs                           │
│                                                                  │
│   /api/budgets/*          Budget variance & summary              │
│   /api/invoices/*         Overdue invoices                       │
│   /api/contracts/*        Expiring contracts & clauses           │
│   /api/simulations/*      Budget / cashflow / Monte Carlo        │
│   /api/analytics/*        Payment patterns, dashboard summary    │
│   /api/search             Semantic document search               │
│   /api/chat               AI Q&A (Groq / Llama 3.3 70B)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              React Dashboard — dashboard/                        │
│   Port 5173+  ·  6 pages  ·  Recharts + Tailwind CSS            │
│                                                                  │
│   /              Budget Augmented                                │
│   /contracts     Contracts & Clauses                             │
│   /invoices      Invoices & Treasury                             │
│   /alerts        Alerts & Recommendations                        │
│   /simulations   Scenario Simulations                            │
│   /chat          AI Financial Assistant                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### Backend — FastAPI

**File:** `src/api/main.py`

The API server is the central hub. It starts two services on startup:
- `FinancialGraph` — connects to Neo4j and creates graph constraints
- `VectorStore` — loads FAISS index and sentence-transformer model

All endpoints are async. CORS is configured to allow requests from `localhost:5173–5177` for the Vite dev server.

The server is started with:
```
python -m src.api.main --port 8080
```

Swagger documentation is available at `http://localhost:8080/docs`.

---

### Graph Database — Neo4j

**File:** `src/rag/graph.py`
**Docker container:** `fincenter-neo4j` (ports 7474 HTTP, 7687 Bolt)

Neo4j stores all financial entities as nodes and their relationships as edges. This allows queries that are impossible in a relational database, such as: *"Find all invoices generated by contracts that a client signed, where payment was more than 15 days late."*

**Node types:**

| Node | Key Properties |
|------|----------------|
| `Invoice` | id, date, due_date, vendor, amount, status |
| `Contract` | id, type, vendor, start_date, end_date, annual_value, auto_renewal |
| `Budget` | department, year, category, budget, actual, variance |
| `Client` | name |
| `Vendor` | name |
| `Clause` | type, description |

**Relationships:**

| Relationship | Meaning |
|---|---|
| `(Contract)-[:GENERATES]->(Invoice)` | Contract produces invoices |
| `(Client)-[:SIGNED]->(Contract)` | Client signed a contract |
| `(Contract)-[:HAS_CLAUSE]->(Clause)` | Contract contains a clause |

**Key queries implemented in `graph.py`:**

- `get_budget_variance(department)` — variance for one department
- `get_budget_summary(year)` — all departments aggregated by year
- `get_overdue_invoices(days_overdue)` — invoices past due date, ordered by days overdue
- `get_expiring_contracts(days_ahead)` — contracts expiring within N days
- `search_contracts_by_clause(clause_type)` — contracts containing a specific clause
- `analyze_client_payment_patterns(client)` — average payment delay for a client

---

### Vector Store — FAISS

**File:** `src/rag/vectorstore.py`
**Storage:** `data/vectors/`

Documents are embedded using `sentence-transformers/all-mpnet-base-v2` (768 dimensions) and stored in a FAISS index for fast approximate nearest-neighbor search.

Used by the `/api/search` endpoint to find semantically similar documents even when keywords don't match exactly. For example, searching *"late payment penalty"* returns contracts with clauses about *"retard de paiement"*.

---

### AI Assistant — Groq / Llama 3.3 70B

**File:** `src/llm/groq_client.py`
**Endpoint:** `POST /api/chat`

On every chat request, the API:
1. Queries Neo4j for live financial context (budgets, overdue invoices, expiring contracts)
2. Builds a structured system prompt with today's date and real numbers
3. Sends the user question + context to Llama 3.3 70B via the Groq API
4. Returns the answer

**System prompt includes:**
- Today's date (for quarter/year interpretation)
- Budget vs. actual for all departments
- Top 10 most overdue invoices with amounts and days overdue
- Overdue count breakdowns (30/60/90 day thresholds)
- All contracts expiring within the next 365 days

**Model settings:** temperature 0.2 (factual), max 4096 tokens.

---

### Ingestion Pipeline

**File:** `src/ingestion/pipeline.py`
**Parsers:** `src/ingestion/parsers/` (json.py, excel.py, pdf.py)
**Extractors:** `src/ingestion/extractors/` (ner.py, amounts.py, dates.py)
**Validators:** `src/ingestion/validators.py`

The pipeline discovers and processes financial documents from a source directory:

1. **Parse** — reads JSON invoices/contracts, Excel budget sheets, PDF documents
2. **Extract** — uses spaCy NER to find companies, amounts, dates, and clause text
3. **Validate** — checks for duplicates (fuzzy matching), anomalous amounts (statistical), missing required fields
4. **Store** — creates Neo4j nodes, generates vector embeddings, writes metadata JSON

To trigger ingestion:
```
POST /api/ingestion/start?input_dir=data/synthetic&output_dir=data/processed
```

Or directly:
```
python load_neo4j.py
```

---

### Simulation Engine

**Files:** `src/simulation/budget.py`, `src/simulation/cashflow.py`, `src/simulation/monte_carlo.py`

Three simulation types are available via the API and the Simulations dashboard page:

**Budget Impact Simulation** (`/api/simulations/budget`)
Simulates the financial effect of changing a department's budget by a given percentage over N months. Returns projected ROI, confidence intervals, monthly projections, and break-even point. Uses department-specific impact multipliers (e.g., Sales and Marketing have higher revenue sensitivity than HR).

**Cash Flow Forecast** (`/api/simulations/cashflow`)
Projects cash flow forward for multiple scenarios (baseline, optimistic, pessimistic, stress test). Takes into account overdue invoice recovery rates, contract payment schedules, and seasonal patterns.

**Monte Carlo Simulation** (`/api/simulations/monte-carlo`)
Runs N iterations of randomized revenue/cost scenarios using configurable volatility parameters. Returns the probability distribution of outcomes, VaR (Value at Risk), and confidence-interval bounds.

---

### Frontend — React Dashboard

**Directory:** `dashboard/`
**Stack:** React 19 + TypeScript + Vite + Tailwind CSS + Recharts
**API communication:** All calls go through Vite's dev proxy → no CORS issues

The dashboard consists of a shared `Layout` with navigation and 6 page components. All data is fetched live from the FastAPI backend on page load.

---

## Dashboard Pages

### 1. Budget Augmented (`/`)

Tracks budget performance across all departments for a given fiscal year.

**What you see:**
- 4 summary cards: Total Budget, Total Actual Spend, Overall Variance, Departments Over Budget
- Bar chart comparing budget vs. actual by department (color-coded: red = over budget)
- Pie chart showing budget distribution across departments
- Table with each department's budget, actual, variance (amount and %)

**Use case:** A CFO opens this page Monday morning to see which departments overspent last quarter and by how much.

---

### 2. Contracts & Clauses (`/contracts`)

Monitors contract expiration and clause content.

**What you see:**
- Summary cards: Expiring Soon, Critical (≤30 days), Warning (31–60 days), Total Value at Risk
- Search bar for filtering by vendor or contract ID
- Filter buttons: 30 / 60 / 90 / 180 days ahead
- Contract cards showing: vendor, contract ID, end date, annual value, auto-renewal flag, urgency color (red/orange/yellow)

**Use case:** Procurement team runs this monthly to identify contracts that need renewal decisions before they auto-expire or lapse.

---

### 3. Invoices & Treasury (`/invoices`)

Tracks all overdue invoices and outstanding cash flow.

**What you see:**
- Summary cards: Total Overdue (count), Overdue Amount ($), Critical >60 days (count), Average Days Overdue
- Filter buttons: All / 30+ / 60+ / 90+ days overdue
- Table with: Invoice ID, Vendor, Date, Amount, Days Overdue, Urgency badge (Critical / High / Medium / Low)

**Use case:** Accounts payable team uses this daily to prioritize collection calls — sorting by days overdue to focus on the most critical outstanding balances first.

---

### 4. Alerts & Recommendations (`/alerts`)

Consolidated view of all financial risk signals.

**What you see:**
- Alert cards grouped by category: Budget, Contract, Invoice, Optimization
- Severity levels: Critical (red), Warning (orange), Info (blue), Success (green)
- Each alert shows: type, message, recommended action, financial impact estimate, timestamp

**Use case:** Finance director uses this as a daily briefing — a single view of everything that needs attention without having to check each dashboard separately.

---

### 5. Simulations (`/simulations`)

Interactive scenario modeling for financial planning.

**What you see:**
- Adjustable sliders: Budget cut %, Revenue growth %, Inflation rate
- Multi-line chart: Baseline vs. With Cuts vs. With Inflation vs. Optimized
- Yearly impact calculations per scenario
- Real-time recalculation as parameters change

**Use case:** Finance team uses this before a board meeting to model the impact of a proposed 15% budget reduction on Q3 cash flow, presenting 3 scenarios with confidence ranges.

---

### 6. AI Financial Assistant (`/chat`)

Natural language interface to all financial data.

**What you see:**
- Chat interface with message history
- Example questions sidebar
- Real-time responses from Llama 3.3 70B with live Neo4j data

**Example questions the AI answers accurately:**
- *"Which department is most over budget?"*
- *"How many invoices are overdue by more than 60 days?"*
- *"Which vendor has the highest outstanding invoice?"*
- *"What is the total value of contracts expiring this quarter?"*
- *"Summarize the budget performance across all departments."*

**Use case:** Any team member — including non-finance staff — can ask financial questions in plain English and get accurate, data-backed answers without learning Cypher or SQL.

---

## API Reference

All endpoints are documented interactively at `http://localhost:8080/docs`.

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server status + Neo4j/VectorStore connectivity |
| GET | `/` | API info and version |

### Budgets

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| GET | `/api/budgets/summary` | `year=2024` | All departments aggregated |
| GET | `/api/budgets/{department}/variance` | — | Single department variance |

### Invoices

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| GET | `/api/invoices/overdue` | `days=0` | All invoices past due (filter by min days overdue) |
| GET | `/api/invoices/{invoice_id}` | — | Single invoice detail |

### Contracts

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| GET | `/api/contracts/expiring` | `days=90` | Contracts expiring within N days |
| GET | `/api/contracts/{contract_id}/clauses` | — | All clauses for a contract |
| GET | `/api/search/contracts/clauses` | `clause_type=penalty` | Contracts with a specific clause type |

### Simulations

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| POST | `/api/simulations/budget` | `department`, `change_percent`, `months` | Budget impact projection |
| POST | `/api/simulations/cashflow` | `months_ahead`, `scenarios` | Cash flow forecast |
| POST | `/api/simulations/monte-carlo` | `revenue`, `volatility`, `costs`, `iterations` | Probabilistic modeling |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/payment-patterns/{client}` | Client payment delay analysis |
| GET | `/api/analytics/dashboard/summary` | Comprehensive summary for all sections |

### Search & AI

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/search` | `{"query": "...", "limit": 5}` | Semantic document search |
| POST | `/api/chat` | `{"message": "..."}` | AI Q&A with live financial context |

---

## Use Cases

### Use Case 1: Monthly Budget Review

**Who:** CFO, Finance Director
**Flow:**
1. Open the Budget page — immediately see which departments are over budget
2. Click a department for detailed variance breakdown
3. Ask the AI: *"Why is Marketing over budget and what are the risks?"*
4. Run a simulation: *"What happens to cash flow if we cut Marketing by 10%?"*

---

### Use Case 2: Accounts Payable Recovery

**Who:** Accounts Payable Manager
**Flow:**
1. Open Invoices page — filter to 90+ days overdue
2. Sort by amount to prioritize high-value recoveries
3. Ask the AI: *"Which vendors have the most overdue invoices?"*
4. Export the list for collection follow-up

---

### Use Case 3: Contract Renewal Planning

**Who:** Procurement, Legal
**Flow:**
1. Open Contracts page — filter to 60 days ahead
2. Check auto-renewal flags to avoid unwanted renewals
3. Search by clause type to find all contracts with penalty clauses
4. Ask the AI: *"Which contracts expiring this quarter have the highest annual value?"*

---

### Use Case 4: Board Meeting Preparation

**Who:** Finance team
**Flow:**
1. Open the Alerts page for a complete risk overview
2. Use the Simulations page to model 3 budget scenarios
3. Ask the AI for a full summary to use as talking points
4. Screenshot or export key charts for the presentation

---

### Use Case 5: Onboarding a New Finance Analyst

**Who:** New hire with no system access yet
**Flow:**
1. Open the AI Assistant
2. Ask: *"Explain the current financial situation of the company"*
3. Ask follow-up questions naturally — no training needed
4. Get accurate answers backed by real data

---

## Project Structure

```
TASK 2/
│
├── start.bat                        # One-click startup (kills old server, starts fresh)
├── load_neo4j.py                    # Loads processed metadata into Neo4j
├── docker-compose.yml               # Neo4j, PostgreSQL, Redis containers
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (credentials, ports)
│
├── src/
│   ├── config.py                    # Centralized Pydantic settings
│   │
│   ├── api/
│   │   └── main.py                  # FastAPI app — all endpoints, CORS, lifespan
│   │
│   ├── rag/
│   │   ├── graph.py                 # Neo4j operations (CRUD + Cypher queries)
│   │   └── vectorstore.py           # FAISS vector store + embeddings
│   │
│   ├── llm/
│   │   └── groq_client.py           # Groq API client (Llama 3.3 70B)
│   │
│   ├── ingestion/
│   │   ├── pipeline.py              # Orchestrator — discovers and processes files
│   │   ├── validators.py            # Data quality: duplicates, anomalies, ranges
│   │   ├── parsers/
│   │   │   ├── json.py              # Invoice and contract JSON parser
│   │   │   ├── excel.py             # Budget Excel parser (multi-sheet)
│   │   │   └── pdf.py               # PDF text extraction
│   │   └── extractors/
│   │       ├── ner.py               # spaCy named entity recognition
│   │       ├── amounts.py           # Financial amount extraction and normalization
│   │       └── dates.py             # Date parsing across multiple formats
│   │
│   └── simulation/
│       ├── budget.py                # Budget change impact simulation
│       ├── cashflow.py              # Multi-scenario cash flow forecasting
│       └── monte_carlo.py           # Monte Carlo probabilistic modeling
│
├── dashboard/                       # React frontend
│   ├── src/
│   │   ├── App.tsx                  # Router — 6 routes
│   │   ├── lib/utils.ts             # fetchAPI helper, API_BASE_URL ("/api")
│   │   ├── components/
│   │   │   ├── Layout.tsx           # Navigation sidebar + header
│   │   │   └── ui/Card.tsx          # Reusable card components
│   │   └── pages/
│   │       ├── BudgetDashboard.tsx  # Budget variance charts and table
│   │       ├── ContractsDashboard.tsx # Expiring contracts with search/filter
│   │       ├── InvoicesDashboard.tsx  # Overdue invoices table with urgency
│   │       ├── AlertsDashboard.tsx    # Consolidated alerts and recommendations
│   │       ├── SimulationsDashboard.tsx # Interactive scenario modeling
│   │       └── ChatDashboard.tsx    # AI assistant chat interface
│   ├── vite.config.ts               # Vite proxy: /api → localhost:8080
│   ├── tailwind.config.js           # Tailwind with CSS variable color mapping
│   └── postcss.config.js            # PostCSS with Tailwind v3
│
├── data/
│   ├── synthetic/                   # Raw generated data
│   │   ├── budgets/                 # Excel files (3 years)
│   │   ├── invoices/                # 500 JSON invoice files
│   │   └── contracts/               # 50 JSON contract files
│   └── processed/
│       ├── metadata/                # Processed JSON (used by load_neo4j.py)
│       └── vectors/                 # FAISS index files
│
└── scripts/
    └── producer.py                  # Synthetic data generator with messiness control
```

---

## Starting the Project

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop (running)
- Groq API key in `.env` file

### Every-day startup

**Terminal 1 — API Server:**
```
cd "C:\Users\Yassine\Desktop\TASK 2"
start.bat
```
Wait for `Application startup complete.`

**Terminal 2 — Dashboard:**
```
cd "C:\Users\Yassine\Desktop\TASK 2\dashboard"
npm run dev
```
Open `http://localhost:5173` (or whichever port Vite picks).

### First-time setup (from scratch)

```bash
# 1. Start databases
docker compose up -d

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key

# 4. Generate synthetic data
python scripts/producer.py --output data/synthetic/ --num-invoices 500 --num-contracts 50

# 5. Run ingestion pipeline (processes files → data/processed/)
python -m src.ingestion.pipeline --input data/synthetic/ --output data/processed/

# 6. Load data into Neo4j
python load_neo4j.py

# 7. Install frontend dependencies
cd dashboard && npm install && cd ..

# 8. Start the system (see Every-day startup above)
```

### Verify everything is working

```bash
# API healthy?
curl http://localhost:8080/health

# Budget data loaded?
curl "http://localhost:8080/api/budgets/summary?year=2024"

# Overdue invoices?
curl "http://localhost:8080/api/invoices/overdue?days=0"

# AI chat working?
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Which department is most over budget?\"}"
```

---

## Troubleshooting

### Port 8080 already in use

```
start.bat
```
The startup script automatically kills any existing process on port 8080 before starting.

Or manually:
```
netstat -ano | grep 8080
# Find the PID, then:
powershell -Command "Stop-Process -Id <PID> -Force"
```

### Dashboard shows "Failed to fetch"

The Vite proxy handles cross-origin requests automatically — but requires the API to be running first. Start `start.bat` before `npm run dev`.

### Neo4j not connecting

```bash
# Check Docker is running
docker compose ps

# Restart Neo4j container
docker compose restart neo4j

# Check logs
docker compose logs neo4j
```

### AI chat returns no answer

Check your Groq API key in `.env`:
```
GROQ_API_KEY=gsk_...
```

### Days overdue showing wrong values / NaN

The server must be restarted after any code changes. Use `start.bat` — it always kills the old process first.

---

## Data Management

### Current data in Neo4j

| Type | Count | Details |
|------|-------|---------|
| Invoices | 484 | All UNPAID, overdue 1100–1500+ days |
| Contracts | 50 | Real annual values, 6 expiring within 365 days |
| Budget nodes | 28 | 7 departments × years 2022–2024 |

### Inspect data in Neo4j Browser

Open `http://localhost:7474` (credentials: `neo4j / fincenter2024`)

```cypher
-- Count all nodes by type
MATCH (n) RETURN labels(n) AS type, COUNT(n) AS count

-- Top 5 overdue invoices
MATCH (i:Invoice)
WHERE i.due_date < date()
RETURN i.id, i.vendor, i.amount, duration.inDays(i.due_date, date()).days AS days_overdue
ORDER BY days_overdue DESC LIMIT 5

-- Budget variance by department (2024)
MATCH (b:Budget {year: 2024})
WITH b.department AS dept, sum(b.actual - b.budget) AS variance
RETURN dept, variance ORDER BY variance DESC
```

### Reset data (nuclear option — loses everything)

```bash
docker compose down -v
docker compose up -d
# Wait ~30 seconds for Neo4j to initialize
python load_neo4j.py
```

### Back up Neo4j data

Neo4j data is stored in a Docker named volume (`neo4j_data`). It survives container restarts and reboots. To export:

```bash
docker exec fincenter-neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/import
```
