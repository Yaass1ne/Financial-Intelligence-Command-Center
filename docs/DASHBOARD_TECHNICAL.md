# FINCENTER — Technical Documentation: Dashboard Pages

> How each page works under the hood: data sources, algorithms, API calls, and LLM context.

---

## Table of Contents

1. [Budget Overview](#1-budget-overview)
2. [Contracts & Clause Management](#2-contracts--clause-management)
3. [Invoices & Treasury Management](#3-invoices--treasury-management)
4. [Intelligence Hub](#4-intelligence-hub)
   - [Weak Signal Radar](#section-a--weak-signal-radar)
   - [Decision Fusion](#section-b--decision-fusion)
   - [Episodic Memory Browser](#section-c--episodic-memory-browser)
5. [Recommendations](#5-recommendations)
6. [Simulations & Scenarios](#6-simulations--scenarios)
7. [Alerts](#7-alerts)
8. [AI Financial Assistant (Chat)](#8-ai-financial-assistant-chat)

---

## 1. Budget Overview

**Route:** `/` &nbsp;|&nbsp; **API:** `GET /api/budgets`
**Key files:** `src/rag/graph.py` → `get_all_budgets_raw()`, `dashboard/src/pages/BudgetDashboard.tsx`

### How it works

The page fetches all `Budget` nodes from Neo4j. Each node stores:

| Field | Description |
|---|---|
| `department` | Department name (e.g. IT, Marketing) |
| `year` | Budget year (2020–2024) |
| `category` | Sub-category (Personnel, Equipment…) |
| `budget` | Planned spend in EUR |
| `actual` | Real spend in EUR |
| `variance` | `actual − budget` |

```cypher
MATCH (b:Budget)
RETURN b.department, b.year, b.category, b.budget, b.actual, b.variance
```

The dashboard computes on the frontend:

- **Total Budget / Actual / Variance** — sum across all rows
- **Overspend %** — `(actual − budget) / budget × 100`
- **Bar chart** — groups by department, planned vs actual side by side

> **Important:** The DB has 82 rows but only 15 unique departments. Each department has multiple rows (one per year × category). The summary cards count unique departments, not rows.

---

## 2. Contracts & Clause Management

**Route:** `/contracts` &nbsp;|&nbsp; **API:** `GET /api/contracts/expiring?days=N` or `GET /api/contracts`
**Key files:** `scripts/ingest_contracts.py`, `src/rag/graph.py` → `get_all_contracts_raw()`

### Ingestion pipeline

Contracts are parsed from PDF files by `scripts/ingest_contracts.py`:

1. Opens each PDF with `pdfplumber`
2. Extracts **vendor** via regex cascade:
   ```python
   patterns = [r'LENDER:\s*(.+)', r'vendor:\s*(.+)',
               r'supplier:\s*(.+)', r'between.*and\s+(.+)']
   ```
3. Extracts **annual value** via `FINANCED AMOUNT:` or `annual value:` —
   strips trailing period before `float()` conversion:
   ```python
   value_str.replace(",", "").rstrip(".")  # "82,437.00." → 82437.0
   ```
4. Extracts start/end dates and contract type
5. Stores as `Contract` node in Neo4j via `MERGE (c:Contract {id: $id})`

### Filter thresholds

The default filter window is **180 days**. Urgency thresholds are **relative** to the selected window:

```
Critical  ≤ window / 3        (≤ 60 days  for 180d window)
Warning   ≤ window × 2 / 3   (≤ 120 days for 180d window)
Safe      = everything else
```

This means switching to a 30-day window recalibrates: Critical ≤10d, Warning ≤20d.

---

## 3. Invoices & Treasury Management

**Route:** `/invoices` &nbsp;|&nbsp; **API:** `GET /api/invoices/overdue?days=N`
**Key files:** `src/rag/graph.py` → `get_overdue_invoices()`, `dashboard/src/pages/InvoicesDashboard.tsx`

### Neo4j query

```cypher
MATCH (i:Invoice)
WHERE i.status = 'UNPAID'
  AND i.due_date IS NOT NULL
  AND i.due_date < date()
  AND duration.inDays(i.due_date, date()).days >= $days
WITH i, duration.inDays(i.due_date, date()).days AS raw_days
RETURN i.id, i.date, i.vendor, i.amount, i.status,
       raw_days AS days_overdue   -- no cap, real value shown
ORDER BY days_overdue DESC
```

Days overdue = `today − due_date` in calendar days. No artificial cap — old 2022 invoices correctly show 1,200+ days.

### Two views

| View | Description |
|---|---|
| **By Vendor** (default) | Groups 484 invoices into ~20 vendor rows: count, total amount, max days, avg days |
| **All Invoices** | Individual rows, sorted by days overdue descending |

### Urgency thresholds (frontend)

```
> 365 days → Critical  (red)
> 180 days → High      (orange)
>  60 days → Medium    (yellow)
≤  60 days → Low       (blue)
```

### Filter buttons

`All Overdue` · `30+ Days` · `60+ Days` · `90+ Days` · `365+ Days`
Each passes `?days=N` to the API, which applies it as a `WHERE` condition in the Cypher query.

---

## 4. Intelligence Hub

**Route:** `/intelligence`
**Key file:** `dashboard/src/pages/IntelligenceDashboard.tsx`

Three independent sections, each backed by a different API endpoint.

---

### Section A — Weak Signal Radar

**API:** `GET /api/intelligence/weak-signals`
**File:** `src/intelligence/weak_signals.py` → `WeakSignalDetector`

#### What is a "weak signal"?

A weak signal is an anomaly that is **below the normal alert threshold** on its own, but becomes significant when **multiple weak signals occur together** for the same entity or period.

#### Signal weights

| Signal type | Condition | Weight |
|---|---|---|
| `budget_slightly_over` | 5–15% over budget | 1 |
| `invoice_moderately_overdue` | 15–30 days overdue | 1 |
| `contract_expiring_medium` | 61–90 days to expiry | 1 |
| `vendor_slight_overbilling` | <10% above contract value | 1 |
| `new_episodic_pattern` | Any learned patterns exist | 2 |

#### Detection algorithm

```python
STRESS_THRESHOLD = 4

signals = _collect_signals()          # scan all live Neo4j data
score   = sum(s["weight"] for s in signals)

if score >= STRESS_THRESHOLD:
    # Generate a stable cluster ID from signal content
    content   = json.dumps(sorted([f"{s['type']}:{s['subject']}" for s in signals]))
    signal_id = "ws_" + hashlib.md5(content.encode()).hexdigest()[:12]

    # Only persist if this exact cluster doesn't already exist
    if not already_exists(signal_id):
        graph.create_weak_signal_node(signal_data)
```

#### Deduplication

The cluster ID is an **MD5 hash** of the sorted list of `type:subject` strings. Running detection twice on the same data produces the same ID → Neo4j `MERGE` updates the node rather than creating a duplicate.

#### Score bar rendering

```tsx
width: `${Math.min(100, ws.score * 10)}%`
// score=4 → 40%, score=10 → 100%
```

---

### Section B — Decision Fusion

**API:** `GET /api/fusion/decisions`
**File:** `src/intelligence/decision_fusion.py` → `DecisionFusion`

#### Priority score formula

```
priority_score = severity_weight × financial_impact × urgency × 10

severity_weight:  critical=3, warning=2, info=1
financial_impact: normalized 0→1  (amount / reference_amount)
urgency:          1.0 + (days / 100)  capped at 2.0
```

#### Example — critical overdue invoice

```
Invoice: 85,000 EUR, 90 days overdue
  severity_weight  = 3       (critical: ≥60 days)
  financial_impact = min(1.0, 85000 / 100000) = 0.85
  urgency          = 1 + min(90/100, 1.0) = 1.9
  score            = 3 × 0.85 × 1.9 × 10 = 48.5
```

#### Five source functions

| Source | Reference amount | Urgency bonus |
|---|---|---|
| Budget overruns | 500,000 EUR | Fixed 1.0 |
| Overdue invoices | 100,000 EUR | `1 + days/100` |
| Expiring contracts | 500,000 EUR | `1 + (90−days)/100` |
| Episodic patterns | — (uses confidence) | Fixed 1.0 |
| Weak signal clusters | — (uses score/10) | Fixed 1.2 |

#### Per-source cap

```python
PER_SOURCE_CAP = 5
# Top 5 per source × 5 sources = 25 candidates
# Global sort → return top 20
```

This prevents 484 invoice alerts from dominating the list — at most 5 invoices, 5 budgets, 5 contracts, 5 episodic, 5 weak signals compete for the top 20 slots.

---

### Section C — Episodic Memory Browser

**API:** `GET /api/memory/patterns`
**File:** `src/memory/episodic.py` → `EpisodicMemory`

Runs at server startup and on "Refresh Patterns" click (`POST /api/memory/refresh`).

#### Pattern 1 — `vendor_overbilling`

```python
# avg invoice per vendor vs monthly contract value
monthly_contract = annual_contract_value / 12
avg_invoice      = mean(all invoice amounts for vendor)

if avg_invoice > monthly_contract × 1.10:   # >10% above contract
    ratio      = avg_invoice / monthly_contract
    confidence = min(0.95, 0.5 + invoice_count × 0.05)
    # 9 invoices → 0.5 + 0.45 = 0.95
```

#### Pattern 2 — `department_overspend`

```python
# How many budget years did this dept overspend by >5%?
overspend_years = [y for y in dept_records if actual > budget × 1.05]

if len(overspend_years) >= 2:              # at least 2 years
    confidence = min(0.95, 0.4 + len(overspend_years) × 0.15)
    # 3 years → 0.4 + 0.45 = 0.85
```

#### Pattern 3 — `late_payment_pattern`

```python
# Per vendor: average days overdue across all UNPAID invoices
avg_days = mean(days_overdue for all unpaid invoices of vendor)

if avg_days > 30 and invoice_count >= 2:
    confidence = min(0.90, 0.4 + invoice_count × 0.05)
```

#### Pattern 4 — `seasonal_spike`

```python
avg_actual   = mean(actual spend across all budget rows)
high_periods = [b for b in budgets if b.actual > avg_actual × 1.20]

if len(high_periods) >= 3:
    → seasonal_spike detected, confidence = 0.65
```

#### Display filter

The frontend filters to `confidence >= 0.6` to suppress low-signal noise:
```tsx
patterns.filter(p => p.confidence >= 0.6)
```

---

## 5. Recommendations

**Route:** `/recommendations` &nbsp;|&nbsp; **API:** `GET /api/recommendations`
**File:** `src/recommendations/engine.py` → `RecommendationEngine`

### Priority score formula

```
priority_score = (financial_impact × 0.4) + (urgency × 0.4) + (confidence × 0.2)
# Result scaled to 0–100
```

### Three recommendation categories

#### `cost_reduction`
Generated from:
- Budget overruns >10% → "Reduce spend in {dept}"
- `vendor_overbilling` episodic patterns → "Renegotiate contract with {vendor}"

#### `risk_mitigation`
Generated from:
- Contracts expiring in ≤90 days → "Renew contract: {vendor}"
- Invoices overdue ≥30 days → "Resolve overdue invoice: {vendor}"
- Active weak signal clusters → "Financial stress cluster requires review"

#### `revenue_optimization`
Generated from:
- Departments under budget by ≥15% → "Reallocate surplus from {dept}"

### Deduplication

IDs are deterministic (no random suffix):
```python
"rec_cost_IT"                      # budget overrun
"rec_invoice_INV-2022-001"         # overdue invoice
"rec_contract_CTR-2022-040"        # expiring contract
"rec_reallocate_Legal"             # under-budget dept
"rec_weaksignal_cluster"           # weak signal (singleton)
```

Neo4j `MERGE` on the stable ID = update in place, never duplicate.

---

## 6. Simulations & Scenarios

**Route:** `/simulations`
**APIs:** `GET /api/simulations/run`, `POST /api/simulations/ai-generate`
**Files:** `src/simulation/{budget,cashflow,monte_carlo}.py`, `src/simulation/ai_scenarios.py`

### Slider simulation (frontend-only, no API call)

The projection chart is computed entirely in the browser using seasonal multipliers:

```javascript
const SEASONAL = [0.88, 0.91, 0.97, 1.02, 1.05, 0.98,
                  0.93, 0.95, 1.04, 1.08, 1.12, 1.24]
//                Jan   Feb   Mar   Apr   May   Jun
//                Jul   Aug   Sep   Oct   Nov   Dec
// Pattern: Q4 spike (Dec=124%), Q1 dip (Jan=88%)

// Per scenario line:
monthlyValue = baseline
             × SEASONAL[monthIndex]
             × (1 + growthRate/100) ^ (monthIndex/12)
```

Three lines: **Optimistic** (+growth%), **Baseline** (flat), **Pessimistic** (−growth%)
Y-axis uses `domain={['auto', 'auto']}` so lines are never flat regardless of absolute values.

### AI Scenario Generation (`POST /api/simulations/ai-generate`)

`src/simulation/ai_scenarios.py` flow:

1. **Build live context** from Neo4j:
   - Top budget overruns
   - Top 5 overdue invoices
   - Contracts expiring within 90 days

2. **Send structured prompt** to Groq/Llama-3.3-70B:
   ```
   Given this financial context, generate exactly 3 named financial scenarios in JSON:
   [{"name": "...", "probability": 0.35, "description": "...",
     "budget_impact_pct": -12, "cashflow_impact_pct": -18,
     "key_risks": [...], "recommended_actions": [...]}]
   ```

3. **Parse JSON response** — falls back gracefully if the LLM returns malformed JSON

4. **Persist to Neo4j** as `Scenario` nodes and return to the dashboard

---

## 7. Alerts

**Route:** `/alerts` &nbsp;|&nbsp; **API:** `GET /api/fusion/decisions`

This page reuses the **Decision Fusion** endpoint — the same ranked list as the Intelligence Hub's Section B. It maps each decision to an alert card:

```
severity: "critical" → red card + CRITICAL badge
severity: "warning"  → yellow card + WARNING badge
severity: "info"     → blue card + INFO badge
```

The page is deliberately simple — it is a "triage view" of the Decision Fusion output, designed for quick daily review rather than deep analysis.

---

## 8. AI Financial Assistant (Chat)

**Route:** `/chat` &nbsp;|&nbsp; **API:** `POST /api/chat`
**Files:** `src/rag/orchestrator.py`, `src/llm/groq_client.py`

### Full request flow

```
User types question
    │
    ▼
POST /api/chat { "question": "..." }
    │
    ▼
RAGOrchestrator.query_sync(question)
    │
    ├── Layer 1: Financial Health Snapshot    (always)
    ├── Layer 2: Deep Graph Data              (keyword-triggered)
    ├── Layer 3: Episodic Memory              (always)
    ├── Layer 4: Decision Fusion Top 5        (always)
    └── Layer 5: Weak Signals / Recs          (keyword-triggered)
    │
    ▼
full_context = "\n\n".join(all layers)
    │
    ▼
groq_client.answer_question(question, full_context)
    │
    ▼
Llama-3.3-70B generates answer
    │
    ▼
Return { answer, sources, context_used, vector_hits }
```

---

### The 5 Context Layers

#### Layer 1 — Financial Health Snapshot *(always injected)*

```
FINANCIAL HEALTH SNAPSHOT (live data):
  Budgets: 15 departments, 11 with at least one year over budget
           (total overrun across all years: +2,847,300 EUR)
  Departments overspending for 2+ years: IT (4 yrs), Marketing (3 yrs)
  Invoices: 484 overdue (3,241,000 EUR outstanding)
  Contracts: 80 total, 3 expiring within 90 days
```

Every single response includes this — so even a vague question like *"how are we doing?"* gets grounded in real numbers.

#### Layer 2 — Deep Graph Data *(keyword-triggered)*

Keyword groups and what they inject:

| Keywords in question | Data injected |
|---|---|
| `budget` / `spend` / `department` / `summary` | Full dept-by-dept breakdown: budget, actual, variance, years over budget |
| `invoice` / `overdue` / `payment` / `facture` | Top 5 overdue invoices with vendor, amount, days |
| `vendor` / `q1`–`q4` / `quarter` / `biggest` | Neo4j aggregation: `GROUP BY vendor` filtered by month range |
| `contract` / `expir` / `fournisseur` | All active contracts sorted by days until expiry |

For quarterly vendor queries, a live Cypher query runs:
```cypher
MATCH (i:Invoice)
WHERE i.date.month >= $month_start AND i.date.month <= $month_end
RETURN i.vendor, count(i), sum(i.amount)
ORDER BY sum(i.amount) DESC LIMIT 10
```

#### Layer 3 — Episodic Memory *(always injected)*

```
LEARNED FINANCIAL PATTERNS (Episodic Memory):
  [VENDOR_OVERBILLING | 95%] Vendor 'Digital Agency' average invoice
    (12,847 EUR) exceeds monthly contract value (9,200 EUR) by 39.6%.
  [DEPARTMENT_OVERSPEND | 85%] Department 'IT' overspent by an average
    of 18.3% across 3 budget periods.
  [LATE_PAYMENT_PATTERN | 70%] Vendor 'TechCorp' invoices are on average
    287 days overdue across 24 unpaid invoices.
  [SEASONAL_SPIKE | 65%] Detected 18 budget periods with spending
    >20% above average, suggesting seasonal expenditure spikes.
```

#### Layer 4 — Decision Fusion Top 5 *(always injected)*

```
DECISION FUSION — TOP FINANCIAL RISKS (ranked by priority score):
  [CRITICAL] Budget overrun: IT (score: 54.0, impact: 847,200 EUR)
             — Review discretionary spending and freeze non-critical purchases.
  [CRITICAL] Overdue invoice: Digital Agency (score: 48.5, impact: 85,000 EUR)
             — Contact vendor to resolve payment.
  [WARNING]  Contract expiring: TechCorp (score: 31.2, impact: 240,000 EUR)
             — Initiate renewal negotiations immediately.
  ...
```

#### Layer 5 — Weak Signals or Recommendations *(keyword-triggered)*

| Keywords | Data injected |
|---|---|
| `risk` / `stress` / `signal` / `alert` / `weak` / `concern` | Active weak signal clusters with combined scores and constituent signals |
| `recommend` / `suggest` / `reduce` / `cost` / `optimize` / `improve` / `priority` | Top 5 scored recommendations by category |

---

### What is sent to the LLM

```python
# System message (built by groq_client.build_system_prompt):
"""
You are FINCENTER's financial intelligence assistant.
You answer questions about invoices, contracts, budgets, and financial analytics
based exclusively on the data provided in the context below.

Rules:
- Be concise and factual.
- Format numbers with commas and currency symbols where appropriate.
- If the answer is not in the context, say "I don't have enough data to answer that."
- Never make up figures.

--- FINANCIAL DATA CONTEXT ---
{all 5 layers joined by \n\n}
--- END CONTEXT ---
"""

# User message:
"{the user's natural language question}"
```

### Model configuration

| Parameter | Value | Reason |
|---|---|---|
| Model | `llama-3.3-70b-versatile` | Best open-weight model for structured data Q&A |
| Temperature | `0.2` | Low = factual, avoids hallucination |
| Max tokens | `4096` | Allows detailed multi-part answers |
| API | Groq (not OpenAI) | ~10× faster inference, free tier available |

The low temperature (`0.2`) is the critical setting — it tells the model to stay close to what the context says rather than reasoning freely. At `temperature=0`, the model would be fully deterministic. At `temperature=1.0`, it would start inventing numbers.

---

## Summary Table

| Page | API Endpoint | Backend Source | Real-time? |
|---|---|---|---|
| Budget Overview | `GET /api/budgets` | Neo4j Budget nodes | Yes |
| Contracts | `GET /api/contracts/expiring` | Neo4j Contract nodes | Yes |
| Invoices | `GET /api/invoices/overdue` | Neo4j Invoice nodes | Yes |
| Intelligence — Weak Signals | `GET /api/intelligence/weak-signals` | `WeakSignalDetector` (Neo4j scan) | Yes |
| Intelligence — Decision Fusion | `GET /api/fusion/decisions` | `DecisionFusion` (5 source functions) | Yes |
| Intelligence — Episodic Memory | `GET /api/memory/patterns` | `EpisodicMemory` nodes in Neo4j | On refresh |
| Recommendations | `GET /api/recommendations` | `RecommendationEngine` (3 generators) | Yes |
| Simulations (sliders) | None (frontend only) | Seasonal formula in browser | N/A |
| Simulations (AI) | `POST /api/simulations/ai-generate` | Groq LLM + live Neo4j context | On demand |
| Alerts | `GET /api/fusion/decisions` | Same as Decision Fusion | Yes |
| Chat | `POST /api/chat` | RAGOrchestrator → 5 layers → Groq LLM | On demand |
