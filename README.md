# FINCENTER — Financial Intelligence Command Center

> AI-powered platform that centralizes, analyzes, and visualizes enterprise financial data using a knowledge graph, vector search, episodic memory, and a large language model.

**Version:** 0.2.0 &nbsp;|&nbsp; **Updated:** 2026-02-17 &nbsp;|&nbsp; **Status:** All 7 architecture blocks implemented

---

## Table of Contents

1. [What FINCENTER Does](#what-fincenter-does)
2. [System Architecture](#system-architecture)
3. [Module Map](#module-map)
4. [Dashboard Pages](#dashboard-pages)
5. [API Reference](#api-reference)
6. [Data Sources](#data-sources)
7. [Project Structure](#project-structure)
8. [Starting the Project](#starting-the-project)
9. [Troubleshooting](#troubleshooting)

---

## What FINCENTER Does

Replaces 10–15 disconnected financial tools with a single intelligent platform.

| Capability | How |
|---|---|
| Budget variance tracking | Neo4j graph + real-time dashboard |
| Overdue invoice monitoring | Configurable threshold alerts |
| Contract expiry management | 30/60/90-day warning pipeline |
| Natural language Q&A | RAG Orchestrator + Groq/Llama-3.3-70B |
| What-if simulations | Budget, cashflow, Monte Carlo + AI scenarios |
| Pattern learning | Episodic memory (vendor overbilling, dept overspend) |
| Risk clustering | Weak signal correlation across all sources |
| Ranked decisions | Decision Fusion from 5 signal sources |
| Scored recommendations | Priority 0–100 with expected financial impact |

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     SOURCES MULTIMODALES                              │
│  PDF / Excel / JSON / CSV  ←── Active (ingestion pipeline)           │
│  S3 / Kafka / SharePoint / API ←── Connectors implemented, not wired │
│  Audio / Video / Images / IoT  ←── Stubs in connectors.py            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────┐       ┌───────────────────────────────────┐
│   COGNITIVE INGESTION     │       │       REAL-TIME FEEDBACK          │
│  pipeline.py              │◄─────►│  feedback/loop.py                 │
│  parsers: PDF/Excel/JSON  │       │  • Calcul Écart Prévu/Réel        │
│  extractors: NER/amounts  │       │  • record_actual() → error %      │
│  validators: dedup/QA     │       │  • Ré-Indexation si erreur > 20%  │
└──────────────┬────────────┘       └───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        RAGraph (Neo4j + FAISS)                        │
│                                                                       │
│   memory/episodic.py          rag/orchestrator.py    llm/groq_client  │
│   • vendor_overbilling        • vector search        • Llama-3.3-70B  │
│   • dept_overspend            • graph traversal      • temp=0.2       │
│   • late_payment_pattern      • memory injection     • 4096 tokens    │
│   • seasonal_spike            • LLM reasoning                         │
└──────────────┬────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SCÉNARIO SIMULATION                            │
│  simulation/budget.py      simulation/cashflow.py                    │
│  simulation/monte_carlo.py simulation/ai_scenarios.py (Groq LLM)    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DECISION FUSION                               │
│  intelligence/decision_fusion.py — Agrégation Multi-sources          │
│  intelligence/weak_signals.py   — Corrélation d'Indices Faibles      │
│  • budget overruns  • overdue invoices  • expiring contracts         │
│  • episodic patterns  • weak signal clusters                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API DE RECOMMANDATION                              │
│  recommendations/engine.py  — scored & ranked recommendations        │
│  Dashboard: 8 pages (React + Recharts + Tailwind)                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Module Map

| Block | Module | File |
|---|---|---|
| Sources | File ingestion | `src/ingestion/pipeline.py` |
| Sources | Cloud/stream connectors *(not wired)* | `src/ingestion/connectors.py` |
| Cognitive Ingestion | Parsers | `src/ingestion/parsers/` |
| Cognitive Ingestion | NER + extractors | `src/ingestion/extractors/` |
| Real-Time Feedback | Prediction tracking | `src/feedback/loop.py` |
| RAGraph | Neo4j CRUD + Cypher | `src/rag/graph.py` |
| RAGraph | FAISS vector store | `src/rag/vectorstore.py` |
| RAGraph | **RAG Orchestrator** | `src/rag/orchestrator.py` |
| RAGraph | Episodic Memory | `src/memory/episodic.py` |
| RAGraph | LLM client | `src/llm/groq_client.py` |
| Simulation | Budget / Cashflow / Monte Carlo | `src/simulation/{budget,cashflow,monte_carlo}.py` |
| Simulation | AI Scenario Generation | `src/simulation/ai_scenarios.py` |
| Decision Fusion | Multi-source ranking | `src/intelligence/decision_fusion.py` |
| Decision Fusion | Weak signal correlation | `src/intelligence/weak_signals.py` |
| Recommendations | Scored engine | `src/recommendations/engine.py` |
| API | All endpoints | `src/api/main.py` |

> **Note on connectors:** `src/ingestion/connectors.py` contains complete classes for S3, Kafka, SharePoint, REST API, IoT/Logs, and Media (Audio/Video/Images). They are **not yet wired** into the ingestion pipeline — each requires credentials and the relevant SDK (`boto3`, `confluent-kafka`, etc.). The pipeline currently reads from local directories only.

---

## Dashboard Pages

| Route | Page | Data Source |
|---|---|---|
| `/` | Budget Augmented | `/api/budgets/summary` |
| `/contracts` | Contracts & Clauses | `/api/contracts/expiring` |
| `/invoices` | Invoices & Treasury | `/api/invoices/overdue` |
| `/alerts` | Alerts *(live from Decision Fusion)* | `/api/fusion/decisions` |
| `/simulations` | Simulations + AI Scenarios | `/api/simulations/*` |
| `/intelligence` | Intelligence Hub | weak-signals + decisions + memory |
| `/recommendations` | Recommendations feed | `/api/recommendations` |
| `/chat` | AI Financial Assistant | `/api/chat` → RAG Orchestrator |

---

## API Reference

Full interactive docs at `http://localhost:8080/docs`.

### Core

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Server + Neo4j + VectorStore status |
| GET | `/api/budgets/summary?year=2024` | All departments |
| GET | `/api/invoices/overdue?days=0` | Overdue invoices (capped at 365 days) |
| GET | `/api/contracts/expiring?days=90` | Expiring contracts |

### Intelligence (new in v0.2.0)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rag/query` | Full RAG pipeline with sources list |
| GET | `/api/rag/vendor/{vendor}` | Graph traversal by vendor |
| GET | `/api/sources/health` | Connector availability status |
| GET | `/api/memory/patterns` | Learned episodic patterns |
| POST | `/api/memory/refresh` | Trigger pattern detection |
| GET | `/api/intelligence/weak-signals` | Active stress clusters |
| GET | `/api/fusion/decisions` | Ranked tactical decisions |
| GET | `/api/recommendations` | Scored recommendations |
| POST | `/api/recommendations/{id}/acknowledge` | Mark done |
| POST | `/api/simulations/ai-generate` | Groq-powered scenario generation |
| POST | `/api/feedback/record` | Save a prediction |
| POST | `/api/feedback/actual` | Record actual, compute error |
| GET | `/api/feedback/accuracy` | Accuracy stats |
| POST | `/api/chat` | AI Q&A (via RAG Orchestrator) |

---

## Data Sources

### Current Data in Neo4j

| Type | Count | Notes |
|---|---|---|
| Invoices | ~484 | Synthetic 2024 data. Days overdue **capped at 365** in API. |
| Contracts (synthetic) | ~50 | JSON-based, 6 expiring within 365 days |
| Contracts (real PDFs) | 30 | Ingested from `Contracts_30_English/`, IDs: CTR-ENG-001→030 |
| Budget nodes | ~28 | 7 departments × 2022–2024 |

### Re-ingest the 30 English contracts

```bash
python scripts/ingest_contracts.py --dir "C:/Users/Yassine/Desktop/Contracts_30_English"
```

### Wiring a new source connector

1. Open `src/ingestion/connectors.py`
2. Instantiate the connector with credentials: `S3Connector(bucket="my-bucket", region="eu-west-1")`
3. Call `.connect()` then `.list_documents()` / `.fetch_document(doc_id)`
4. Pass the raw bytes through the existing parsers (`parse_invoice_pdf`, etc.)

```python
# Example: ingest from S3
from src.ingestion.connectors import S3Connector
from src.ingestion.parsers.pdf import parse_invoice_pdf
import tempfile, pathlib

s3 = S3Connector(bucket="fincenter-docs")
s3.connect()
for doc in s3.list_documents():
    raw = s3.fetch_document(doc["doc_id"])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw)
        result = parse_invoice_pdf(pathlib.Path(f.name))
```

---

## Project Structure

```
TASK 2/
├── src/
│   ├── api/main.py               # FastAPI — all 25+ endpoints
│   ├── config.py                 # Pydantic settings + GROQ_API_KEY
│   ├── rag/
│   │   ├── graph.py              # Neo4j CRUD + Cypher queries
│   │   ├── vectorstore.py        # FAISS embeddings
│   │   └── orchestrator.py       # RAG Orchestrator (vector+graph+memory+LLM)
│   ├── llm/groq_client.py        # Groq / Llama-3.3-70B
│   ├── memory/episodic.py        # Pattern detection + EpisodicMemory nodes
│   ├── feedback/loop.py          # Prediction tracking + re-indexation
│   ├── intelligence/
│   │   ├── weak_signals.py       # Weak signal correlation
│   │   └── decision_fusion.py    # Multi-source signal ranking
│   ├── recommendations/engine.py # Scored recommendation generation
│   ├── simulation/
│   │   ├── budget.py / cashflow.py / monte_carlo.py
│   │   └── ai_scenarios.py       # Groq-powered scenario generation
│   └── ingestion/
│       ├── pipeline.py           # File-based ingestion orchestrator
│       ├── connectors.py         # S3/Kafka/SharePoint/IoT stubs
│       ├── parsers/              # pdf.py, excel.py, json.py
│       ├── extractors/           # ner.py, amounts.py, dates.py
│       └── validators.py
├── dashboard/src/pages/
│   ├── BudgetDashboard.tsx
│   ├── ContractsDashboard.tsx
│   ├── InvoicesDashboard.tsx
│   ├── AlertsDashboard.tsx       # Live from /api/fusion/decisions
│   ├── SimulationsDashboard.tsx  # + AI Scenarios tab
│   ├── IntelligenceDashboard.tsx # NEW — weak signals + decisions + memory
│   ├── RecommendationsDashboard.tsx # NEW — scored feed
│   └── ChatDashboard.tsx
├── scripts/
│   ├── producer.py               # Synthetic data generator
│   └── ingest_contracts.py       # Ingest PDF contracts folder
├── data/synthetic/               # Budgets, invoices, contracts (2024)
├── data/processed/               # Vectors + metadata
└── docker-compose.yml            # Neo4j, PostgreSQL, Redis
```

---

## Starting the Project

### Every-day startup

```bash
# Terminal 1 — API (port 8080)
cd "C:\Users\Yassine\Desktop\TASK 2"
start.bat

# Terminal 2 — Dashboard (port 5173)
cd "C:\Users\Yassine\Desktop\TASK 2\dashboard"
npm run dev
```

### First-time setup

```bash
docker compose up -d
pip install -r requirements.txt
python scripts/producer.py --output data/synthetic/
python -m src.ingestion.pipeline --input data/synthetic/ --output data/processed/
python load_neo4j.py
python scripts/ingest_contracts.py   # load 30 English contracts
cd dashboard && npm install
```

### Verify

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/fusion/decisions
curl http://localhost:8080/api/memory/patterns
curl -X POST http://localhost:8080/api/simulations/ai-generate
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 8080 in use | `start.bat` kills it automatically |
| "Failed to fetch" in dashboard | Start API before `npm run dev` |
| Days overdue = 1287 | Fixed — API now caps at 365 days |
| Vendor = UNKNOWN in contracts | PDFs are image-based; text extraction fallback needed |
| Neo4j not connecting | `docker compose restart neo4j` |
| AI chat no answer | Check `GROQ_API_KEY` in `.env` |
| Memory patterns empty | Run `POST /api/memory/refresh` after data load |
