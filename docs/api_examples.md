# FINCENTER API Examples — v0.2.0

Base URL: `http://localhost:8080` | Interactive docs: `/docs`

---

## Health & Status

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/sources/health   # connector status (S3, Kafka, etc.)
```

---

## Budgets / Invoices / Contracts

```bash
curl "http://localhost:8080/api/budgets/summary?year=2024"
curl "http://localhost:8080/api/invoices/overdue?days=60"   # days_overdue capped at 365
curl "http://localhost:8080/api/contracts/expiring?days=90"
curl "http://localhost:8080/api/search/contracts/clauses?clause_type=penalty"
```

---

## Intelligence (v0.2.0)

```bash
# RAG query — graph + episodic memory + LLM
curl -X POST http://localhost:8080/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which vendor is overbilling us?"}'

# Vendor graph traversal
curl "http://localhost:8080/api/rag/vendor/TechCorp"

# Episodic memory patterns
curl "http://localhost:8080/api/memory/patterns"
curl -X POST http://localhost:8080/api/memory/refresh

# Weak signals
curl "http://localhost:8080/api/intelligence/weak-signals"

# Decision fusion (used by /alerts dashboard)
curl "http://localhost:8080/api/fusion/decisions"

# Recommendations
curl "http://localhost:8080/api/recommendations"
curl -X POST "http://localhost:8080/api/recommendations/rec_cost_Marketing_abc123/acknowledge"
```

---

## Simulations

```bash
# Manual
curl -X POST "http://localhost:8080/api/simulations/budget?department=Marketing&change_percent=-10&months=12"
curl -X POST "http://localhost:8080/api/simulations/cashflow?months_ahead=3"
curl -X POST "http://localhost:8080/api/simulations/monte-carlo?revenue=5000000&costs=4000000"

# AI-generated (Groq/Llama-3.3-70B from live data)
curl -X POST http://localhost:8080/api/simulations/ai-generate
```

---

## Feedback Loop

```bash
# Record prediction
curl -X POST http://localhost:8080/api/feedback/record \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"budget","entity_id":"Marketing","metric":"actual_spend","predicted_value":500000}'

# Record actual (triggers re-index if error > 20%)
curl -X POST http://localhost:8080/api/feedback/actual \
  -H "Content-Type: application/json" \
  -d '{"prediction_id":"<uuid>","actual_value":620000}'

curl "http://localhost:8080/api/feedback/accuracy"
```

---

## AI Chat

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which department is most over budget?"}'
```

Context = live budgets + overdue invoices + expiring contracts + episodic memory patterns (via RAG Orchestrator).
