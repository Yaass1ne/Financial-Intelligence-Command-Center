# FINCENTER — Quick Start Guide

Get the full system running in under 5 minutes.

## Services

| Service | URL | Purpose |
|---|---|---|
| FastAPI backend | http://localhost:8080 | REST API + AI |
| Swagger docs | http://localhost:8080/docs | 25+ endpoints |
| React dashboard | http://localhost:5173 | 8-page dashboard |
| Neo4j browser | http://localhost:7474 | Graph explorer |

## Every-day startup

```bash
# Terminal 1
cd "C:\Users\Yassine\Desktop\TASK 2"
start.bat                  # kills port 8080, starts API

# Terminal 2
cd "C:\Users\Yassine\Desktop\TASK 2\dashboard"
npm run dev                # starts Vite on port 5173
```

## First-time setup

```bash
docker compose up -d
pip install -r requirements.txt
python scripts/producer.py --output data/synthetic/
python load_neo4j.py
python scripts/ingest_contracts.py   # loads 30 real contracts
cd dashboard && npm install
```

## Quick checks

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/fusion/decisions
curl http://localhost:8080/api/memory/patterns
curl -X POST http://localhost:8080/api/simulations/ai-generate
```

## Key pages

| Page | What to look for |
|---|---|
| `/intelligence` | Weak signals + ranked decisions + learned patterns |
| `/recommendations` | Scored (0–100) action items with evidence |
| `/alerts` | Live alerts from Decision Fusion (replaces hardcoded mock) |
| `/simulations` | Click "AI Scenarios" tab → Generate 3 Groq-powered scenarios |
| `/chat` | Ask in natural language — context includes episodic memory |

## Notes

- **Days overdue** are capped at 365 in the API (data is from 2024)
- **30 English contracts** are already loaded (CTR-ENG-001 to CTR-ENG-030)
- **S3/Kafka connectors** exist in `src/ingestion/connectors.py` but need credentials to activate
