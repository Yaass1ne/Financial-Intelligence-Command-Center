# FINCENTER Neo4j Graph Schema — v0.2.0

---

## Node Types

### Core Financial Nodes

| Node | Properties | Unique constraint |
|---|---|---|
| `Invoice` | id, date, due_date, vendor, amount, status | id |
| `Contract` | id, type, vendor, start_date, end_date, annual_value, auto_renewal | id |
| `Budget` | department, year, category, budget, actual, variance | (department, year, category) |
| `Client` | name | name |
| `Vendor` | name | name |
| `Clause` | type, description, value | — |

### Intelligence Nodes (v0.2.0)

| Node | Properties | Unique constraint |
|---|---|---|
| `EpisodicMemory` | id, type, subject, description, confidence, evidence_count, last_updated | id |
| `WeakSignal` | id, score, signals_json, detected_at, acknowledged | id |
| `Recommendation` | id, category, title, priority_score, expected_impact_eur, confidence, acknowledged | id |
| `Prediction` | id, entity_type, entity_id, metric, predicted_value, actual_value, error_pct, reindexed | id |
| `Scenario` | id, name, probability, description, budget_impact_pct, cashflow_impact_pct, key_risks, recommended_actions | id |

---

## Relationships

| Relationship | Pattern | Meaning |
|---|---|---|
| `GENERATES` | `(Contract)-[:GENERATES]->(Invoice)` | Contract produces invoices |
| `SIGNED` | `(Client)-[:SIGNED]->(Contract)` | Client signed contract |
| `HAS_CLAUSE` | `(Contract)-[:HAS_CLAUSE]->(Clause)` | Contract clause |
| `PAYS` | `(Client)-[:PAYS]->(Invoice)` | Invoice payment |

---

## EpisodicMemory Types

| type | subject | Trigger |
|---|---|---|
| `vendor_overbilling` | vendor name | avg invoice > 110% monthly contract |
| `department_overspend` | dept name | actual > budget × 1.05 for 2+ years |
| `late_payment_pattern` | vendor name | avg days_overdue > 30 across 2+ invoices |
| `seasonal_spike` | "All Departments" | 3+ periods > 120% of avg spend |

---

## Useful Cypher Queries

```cypher
-- All nodes by type
MATCH (n) RETURN labels(n) AS type, COUNT(n) AS count ORDER BY count DESC

-- Budget overruns (2024)
MATCH (b:Budget {year: 2024})
WHERE b.actual > b.budget
RETURN b.department, b.budget, b.actual, b.actual - b.budget AS overrun
ORDER BY overrun DESC

-- Contracts expiring soon
MATCH (c:Contract)
WHERE c.end_date > date() AND c.end_date <= date() + duration({days: 90})
RETURN c.id, c.vendor, c.end_date, c.annual_value
ORDER BY c.end_date

-- Learned patterns with high confidence
MATCH (m:EpisodicMemory) WHERE m.confidence > 0.7
RETURN m.type, m.subject, m.description, m.confidence
ORDER BY m.confidence DESC

-- Top-priority recommendations
MATCH (r:Recommendation) WHERE r.acknowledged = false
RETURN r.title, r.category, r.priority_score, r.expected_impact_eur
ORDER BY r.priority_score DESC LIMIT 10

-- Vendor full picture (contracts + invoices + patterns)
MATCH (c:Contract {vendor: "TechCorp"})
OPTIONAL MATCH (c)-[:GENERATES]->(i:Invoice)
OPTIONAL MATCH (m:EpisodicMemory {subject: "TechCorp"})
RETURN c.id, c.annual_value, count(i) AS invoice_count, collect(m.description) AS patterns
```

---

## Data Summary (Feb 2026)

| Type | Count | Source |
|---|---|---|
| Invoice | ~484 | Synthetic (2024), days_overdue capped at 365 |
| Contract | ~50 | Synthetic (JSON) |
| Contract | 30 | Real PDFs — CTR-ENG-001 to CTR-ENG-030 |
| Budget | ~28 | Synthetic — 7 depts × 2022-2024 |
| EpisodicMemory | Dynamic | Auto-detected on startup |
| WeakSignal | Dynamic | Detected on `/api/intelligence/weak-signals` |
| Recommendation | Dynamic | Generated on `/api/recommendations` |
