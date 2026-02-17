# FINCENTER Architecture — v0.2.0

## The 7 Blocks

### 1. Sources Multimodales
**Active:** PDF, Excel, JSON, CSV via `src/ingestion/pipeline.py`

**Implemented but not wired** (`src/ingestion/connectors.py`):
- `S3Connector` — boto3, requires `AWS_ACCESS_KEY_ID` + bucket name
- `KafkaConnector` — confluent-kafka, requires bootstrap servers
- `SharePointConnector` — Office365 REST, requires client credentials
- `APIConnector` — generic REST for ERP/SAP/Sage integration
- `IoTLogsConnector` — reads local log directories (functional now)
- `MediaConnector` — OCR via pytesseract, audio via Whisper (stubs)

To activate any connector: instantiate it, call `.connect()`, iterate `.list_documents()`, fetch raw bytes and pass to existing parsers.

---

### 2. Cognitive Ingestion (`src/ingestion/`)
- `pipeline.py` — discovers files, orchestrates parse → extract → validate → store
- `parsers/` — JSON (invoices/contracts), Excel (budgets), PDF (invoices)
- `extractors/` — spaCy NER, amount normalization, multi-format date parsing
- `validators.py` — fuzzy duplicate detection, statistical anomaly checking

---

### 3. Real-Time Feedback (`src/feedback/loop.py`)
- `record_prediction(entity_type, entity_id, metric, predicted_value)` → saves Prediction node
- `record_actual(prediction_id, actual_value)` → computes error_pct; triggers re-index if > 20%
- `get_accuracy_stats()` → per-entity-type avg/best/worst error

---

### 4. RAGraph (`src/rag/`)

**Neo4j node types:**

| Node | Key properties |
|---|---|
| Invoice | id, vendor, amount, status, due_date |
| Contract | id, vendor, annual_value, end_date, auto_renewal |
| Budget | department, year, budget, actual, variance |
| EpisodicMemory | id, type, subject, description, confidence, evidence_count |
| WeakSignal | id, score, signals_json, detected_at |
| Recommendation | id, category, priority_score, expected_impact_eur |
| Prediction | id, entity_type, predicted_value, actual_value, error_pct |
| Scenario | id, name, probability, budget_impact_pct, cashflow_impact_pct |

**RAG Orchestrator** (`src/rag/orchestrator.py`):
1. `query_sync(question)` — graph context + episodic memory + LLM
2. `query(question)` — async: adds vector search step
3. `get_vendor_financial_summary(vendor)` — cross-node graph traversal
4. `get_contract_with_invoices(contract_id)` — relationship traversal

**Episodic Memory** (`src/memory/episodic.py`):
- Detects: vendor_overbilling, department_overspend, late_payment_pattern, seasonal_spike
- `run_pattern_detection()` runs on API startup and on `POST /api/memory/refresh`
- `get_context_for_ai()` injects top 8 patterns into every LLM call

---

### 5. Scenario Simulation (`src/simulation/`)
- `budget.py` — department budget change impact (ROI, confidence intervals)
- `cashflow.py` — multi-scenario T+N forecast (optimistic/base/pessimistic/stress)
- `monte_carlo.py` — probabilistic revenue/cost modeling, VaR
- `ai_scenarios.py` — calls Groq with live financial context → 3 named scenarios with probability + impact %

---

### 6. Decision Fusion (`src/intelligence/decision_fusion.py`)
Aggregates signals from 5 sources, scores each:

```
priority = severity_weight × financial_impact × urgency_factor × 10
severity_weight: critical=3, warning=2, info=1
financial_impact: normalized 0–1 (relative to €500K threshold)
urgency_factor: 1 + days_overdue/100
```

**Weak Signal Correlation** (`src/intelligence/weak_signals.py`):
- Scores individual sub-threshold signals (weight 1–2 each)
- Raises alert when combined score ≥ 4
- Stored as WeakSignal nodes in Neo4j

---

### 7. API de Recommandation (`src/recommendations/engine.py`)

Priority score formula:
```
priority_score = (financial_impact × 0.4) + (urgency × 0.4) + (confidence × 0.2)
scaled to 0–100
```

Three categories: `cost_reduction`, `risk_mitigation`, `revenue_optimization`

---

## Data Flow for a Chat Question

```
User: "Which vendor is overbilling us?"
         │
         ▼
RAGOrchestrator.query_sync()
  ├── _graph_context_sync()  → searches "vendor" keyword → loads contracts + invoices from Neo4j
  ├── EpisodicMemory.get_context_for_ai()  → injects vendor_overbilling patterns
  └── groq_client.answer_question(question, context)  → Llama-3.3-70B generates answer
         │
         ▼
Answer: "Based on episodic memory, Vendor X invoices average 15% above contract value..."
```

---

## Source Connector Wiring (TODO for v1.0.0)

```python
# In src/ingestion/pipeline.py — add connector source option:
# 1. Import connector
from src.ingestion.connectors import S3Connector
# 2. Replace local file discovery with connector fetch
# 3. Pass raw bytes to existing parser functions
```
