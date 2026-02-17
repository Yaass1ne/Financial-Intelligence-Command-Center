# FINCENTER API Examples

Comprehensive API usage examples for all FINCENTER endpoints.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, the API does not require authentication. For production deployment, add JWT or API key authentication.

---

## Table of Contents

1. [Health & Status](#health--status)
2. [Budget Endpoints](#budget-endpoints)
3. [Invoice Endpoints](#invoice-endpoints)
4. [Contract Endpoints](#contract-endpoints)
5. [Search & RAG](#search--rag)
6. [Simulation Endpoints](#simulation-endpoints)
7. [Analytics Endpoints](#analytics-endpoints)
8. [Ingestion Endpoints](#ingestion-endpoints)

---

## Health & Status

### Check API Health

**GET** `/health`

```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "neo4j": "connected",
    "vectorstore": "connected"
  }
}
```

---

## Budget Endpoints

### Get Budget Variance for Department

**GET** `/api/budgets/{department}/variance`

Get budget variance analysis for a specific department.

**cURL Example:**
```bash
curl http://localhost:8080/api/budgets/Marketing/variance
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://localhost:8080/api/budgets/Marketing/variance"
)
data = response.json()

print(f"Department: {data['department']}")
print(f"Budget: {data['budget']}")
print(f"Actual: {data['actual']}")
print(f"Variance: {data['variance_percent']}%")
```

**Response:**
```json
{
  "department": "Marketing",
  "budget": 50000.0,
  "actual": 52000.0,
  "variance": 2000.0,
  "variance_percent": 4.0
}
```

### Get Budget Summary

**GET** `/api/budgets/summary?year=2024`

Get summary of all department budgets for a fiscal year.

**cURL Example:**
```bash
curl "http://localhost:8080/api/budgets/summary?year=2024"
```

**Response:**
```json
[
  {
    "department": "Marketing",
    "budget": 50000.0,
    "actual": 52000.0,
    "variance": 2000.0
  },
  {
    "department": "Sales",
    "budget": 75000.0,
    "actual": 73000.0,
    "variance": -2000.0
  }
]
```

---

## Invoice Endpoints

### Get Overdue Invoices

**GET** `/api/invoices/overdue?days=15`

Get all invoices overdue by at least N days.

**cURL Example:**
```bash
curl "http://localhost:8080/api/invoices/overdue?days=15"
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://localhost:8080/api/invoices/overdue",
    params={"days": 15}
)
invoices = response.json()

for invoice in invoices:
    print(f"{invoice['invoice_id']}: {invoice['amount']} EUR ({invoice['days_overdue']} days overdue)")
```

**Response:**
```json
[
  {
    "invoice_id": "INV-2024-0123",
    "date": "2024-01-15",
    "vendor": "ACME Corp",
    "amount": 1200.0,
    "status": "UNPAID",
    "days_overdue": 25
  }
]
```

### Get Specific Invoice

**GET** `/api/invoices/{invoice_id}`

Get details for a specific invoice.

**cURL Example:**
```bash
curl http://localhost:8080/api/invoices/INV-2024-0001
```

**Response:**
```json
{
  "invoice_id": "INV-2024-0001",
  "date": "2024-01-15",
  "vendor": "ACME Corp",
  "amount": 1200.0,
  "status": "PAID"
}
```

---

## Contract Endpoints

### Get Expiring Contracts

**GET** `/api/contracts/expiring?days=90`

Get contracts expiring within N days.

**cURL Example:**
```bash
curl "http://localhost:8080/api/contracts/expiring?days=90"
```

**Response:**
```json
[
  {
    "contract_id": "CTR-2024-001",
    "vendor": "Software Provider Inc",
    "end_date": "2024-06-30",
    "annual_value": 100000.0,
    "auto_renewal": false,
    "days_until_expiry": 45
  }
]
```

### Get Contract Clauses

**GET** `/api/contracts/{contract_id}/clauses`

Get all clauses for a specific contract.

**cURL Example:**
```bash
curl http://localhost:8080/api/contracts/CTR-2024-001/clauses
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://localhost:8080/api/contracts/CTR-2024-001/clauses"
)
data = response.json()

print(f"Contract: {data['contract_id']}")
print(f"Total Clauses: {data['total_clauses']}")

for clause in data['clauses']:
    print(f"  - {clause['type']}: {clause['description']}")
```

**Response:**
```json
{
  "contract_id": "CTR-2024-001",
  "clauses": [
    {
      "type": "PRICE_REVISION",
      "description": "Annual price revision based on CPI",
      "value": "CPI + 2%"
    },
    {
      "type": "TERMINATION",
      "description": "30 days notice required",
      "value": "30 days"
    }
  ],
  "total_clauses": 2
}
```

---

## Search & RAG

### Semantic Search

**POST** `/api/search`

Semantic search across all financial documents.

**cURL Example:**
```bash
curl -X POST http://localhost:8080/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "contracts with price revision clauses", "limit": 10}'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8080/api/search",
    json={
        "query": "contracts with automatic renewal",
        "limit": 5
    }
)
results = response.json()

for result in results:
    print(f"Document: {result['document_id']}")
    print(f"Type: {result['document_type']}")
    print(f"Score: {result['score']}")
    print(f"Content: {result['content'][:100]}...")
```

**Request:**
```json
{
  "query": "contracts with price revision clauses",
  "limit": 10
}
```

**Response:**
```json
[
  {
    "document_id": "CTR-2024-001",
    "document_type": "contract",
    "content": "Service agreement with annual price revision...",
    "score": 0.92,
    "metadata": {
      "vendor": "Software Provider Inc",
      "annual_value": 100000
    }
  }
]
```

### Search Contracts by Clause Type

**GET** `/api/search/contracts/clauses?clause_type=price_revision`

Find all contracts with a specific clause type.

**cURL Example:**
```bash
curl "http://localhost:8080/api/search/contracts/clauses?clause_type=price_revision"
```

**Response:**
```json
[
  {
    "contract_id": "CTR-2024-001",
    "vendor": "Software Provider Inc",
    "clause_description": "Annual price revision based on CPI"
  }
]
```

---

## Simulation Endpoints

### Budget Change Simulation

**POST** `/api/simulations/budget`

Simulate the impact of a budget change.

**cURL Example:**
```bash
curl -X POST "http://localhost:8080/api/simulations/budget?department=Marketing&change_percent=10&months=12"
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8080/api/simulations/budget",
    params={
        "department": "Marketing",
        "change_percent": 10,  # 10% increase
        "months": 12
    }
)
result = response.json()

print(f"Department: {result['department']}")
print(f"Change: {result['change_percent']}%")
print(f"Projected ROI: {result['roi']:.2%}")
print(f"Confidence Interval: {result['confidence_interval']}")
```

**Response:**
```json
{
  "department": "Marketing",
  "change_percent": 10,
  "simulation_months": 12,
  "projected_revenue": 660000.0,
  "projected_costs": 660000.0,
  "roi": 0.15,
  "confidence_interval": [0.12, 0.18],
  "confidence_level": 0.95,
  "monthly_projections": [
    {
      "month": 1,
      "revenue": 55000.0,
      "cost": 55000.0,
      "cumulative_revenue": 55000.0,
      "cumulative_costs": 55000.0,
      "roi": 0.0
    }
  ]
}
```

### Cash Flow Forecast

**POST** `/api/simulations/cashflow`

Forecast cash flow for different scenarios.

**cURL Example:**
```bash
curl -X POST "http://localhost:8080/api/simulations/cashflow?months_ahead=3&scenarios=optimistic&scenarios=base&scenarios=pessimistic"
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8080/api/simulations/cashflow",
    params={
        "months_ahead": 3,
        "scenarios": ["optimistic", "base", "pessimistic"]
    }
)
forecast = response.json()

for scenario in ["optimistic", "base", "pessimistic"]:
    data = forecast[scenario]
    print(f"\n{scenario.upper()}")
    print(f"Final Balance: {data['final_balance']}")
    print(f"Min Balance: {data['min_balance']}")
    print(f"Liquidity Crisis: {data['liquidity_crisis']}")
```

**Response:**
```json
{
  "optimistic": {
    "forecast": [...],
    "final_balance": 125000.0,
    "min_balance": 105000.0,
    "max_balance": 125000.0,
    "total_inflows": 630000.0,
    "total_outflows": 505000.0,
    "net_cashflow": 125000.0,
    "liquidity_crisis": false
  },
  "base": {
    "final_balance": 95000.0,
    "liquidity_crisis": false
  },
  "pessimistic": {
    "final_balance": 65000.0,
    "liquidity_crisis": false
  }
}
```

### Monte Carlo Simulation

**POST** `/api/simulations/monte-carlo`

Run Monte Carlo simulation for revenue/cost uncertainty.

**cURL Example:**
```bash
curl -X POST "http://localhost:8080/api/simulations/monte-carlo?revenue=100000&revenue_volatility=0.15&costs=80000&cost_volatility=0.10&iterations=10000"
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8080/api/simulations/monte-carlo",
    params={
        "revenue": 100000,
        "revenue_volatility": 0.15,
        "costs": 80000,
        "cost_volatility": 0.10,
        "iterations": 10000
    }
)
result = response.json()

print(f"Mean: {result['mean']}")
print(f"Std Dev: {result['std']}")
print(f"P5: {result['percentiles']['p5']}")
print(f"P50: {result['percentiles']['p50']}")
print(f"P95: {result['percentiles']['p95']}")
print(f"Probability Positive: {result['probability_positive']:.1%}")
```

**Response:**
```json
{
  "mean": 20000.0,
  "median": 19950.0,
  "std": 18000.0,
  "min": -25000.0,
  "max": 65000.0,
  "percentiles": {
    "p5": -9500.0,
    "p50": 19950.0,
    "p95": 49500.0
  },
  "iterations": 10000,
  "converged": false,
  "probability_positive": 0.87
}
```

---

## Analytics Endpoints

### Payment Pattern Analysis

**GET** `/api/analytics/payment-patterns/{client}`

Analyze payment patterns for a specific client.

**cURL Example:**
```bash
curl http://localhost:8080/api/analytics/payment-patterns/ACME%20Corp
```

**Response:**
```json
{
  "avg_delay_days": 15.5,
  "delay_variance": 8.2,
  "min_delay": -5,
  "max_delay": 45,
  "total_invoices": 24
}
```

### Dashboard Summary

**GET** `/api/analytics/dashboard/summary`

Get comprehensive dashboard summary with key metrics.

**cURL Example:**
```bash
curl http://localhost:8080/api/analytics/dashboard/summary
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://localhost:8080/api/analytics/dashboard/summary"
)
summary = response.json()

print("=== DASHBOARD SUMMARY ===")
print(f"\nBudgets:")
print(f"  Total Budget: {summary['budgets']['total_budget']}")
print(f"  Total Actual: {summary['budgets']['total_actual']}")
print(f"  Variance: {summary['budgets']['variance']}")

print(f"\nInvoices:")
print(f"  Overdue Count: {summary['invoices']['overdue_count']}")
print(f"  Overdue Amount: {summary['invoices']['total_overdue_amount']}")

print(f"\nContracts:")
print(f"  Expiring Soon: {summary['contracts']['expiring_soon']}")

print(f"\nAlerts: {len(summary['alerts'])}")
for alert in summary['alerts']:
    print(f"  [{alert['severity']}] {alert['message']}")
```

**Response:**
```json
{
  "budgets": {
    "total_budget": 500000.0,
    "total_actual": 520000.0,
    "variance": 20000.0,
    "departments_over_budget": 3
  },
  "invoices": {
    "total_outstanding": 150000.0,
    "overdue_count": 12,
    "total_overdue_amount": 45000.0
  },
  "contracts": {
    "total_active": 25,
    "expiring_soon": 5,
    "total_annual_value": 2500000.0
  },
  "alerts": [
    {
      "type": "budget_overrun",
      "severity": "warning",
      "message": "3 departments over budget"
    },
    {
      "type": "overdue_invoices",
      "severity": "high",
      "message": "12 overdue invoices"
    }
  ]
}
```

---

## Ingestion Endpoints

### Start Ingestion Pipeline

**POST** `/api/ingestion/start`

Trigger document ingestion pipeline (runs in background).

**cURL Example:**
```bash
curl -X POST "http://localhost:8080/api/ingestion/start?input_directory=data/synthetic&output_directory=data/processed"
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8080/api/ingestion/start",
    params={
        "input_directory": "data/synthetic",
        "output_directory": "data/processed"
    }
)
result = response.json()

print(f"Status: {result['status']}")
print(f"Message: {result['message']}")
```

**Response:**
```json
{
  "status": "started",
  "message": "Ingestion pipeline started in background",
  "input_directory": "data/synthetic",
  "output_directory": "data/processed"
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "error": "Error type",
  "detail": "Detailed error message"
}
```

**Example:**
```bash
curl http://localhost:8080/api/invoices/INVALID-ID
```

**Response (404):**
```json
{
  "error": "Not found",
  "detail": "Invoice 'INVALID-ID' not found"
}
```

---

## Interactive API Documentation

For interactive API documentation with built-in testing:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

---

## Rate Limiting

For production deployment, implement rate limiting:

```python
# Example: 100 requests per minute
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/budgets/summary")
@limiter.limit("100/minute")
async def get_budget_summary():
    ...
```

---

**Last Updated**: 2025-02-16
**API Version**: 0.1.0
