# FINCENTER Architecture Documentation

## System Overview

FINCENTER is a cognitive architecture-based platform for financial intelligence that centralizes, analyzes, and visualizes enterprise financial data through multi-modal document ingestion, graph-based knowledge representation, and AI-powered simulation.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                 │
│  Excel Budgets │ PDF Invoices │ JSON Contracts │ CSV Accounting │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INGESTION LAYER                                 │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Parsers  │  │Extractors│  │Validators│  │  Pipeline    │  │
│  │ PDF/Excel │  │ NER/Dates│  │  Quality │  │Orchestration │  │
│  │   JSON    │  │ Amounts  │  │  Checks  │  │ Batch Proc.  │  │
│  └───────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RAG LAYER                                    │
│  ┌────────────────────┐    ┌──────────────────────────┐        │
│  │   Neo4j Graph DB   │    │   Vector Store (FAISS)   │        │
│  │                    │    │                          │        │
│  │ Nodes:             │    │ Embeddings:              │        │
│  │  • Contracts       │    │  • Document vectors      │        │
│  │  • Invoices        │    │  • Semantic search       │        │
│  │  • Budgets         │    │  • Similarity matching   │        │
│  │  • Clients         │    │                          │        │
│  │  • Vendors         │    │ Model:                   │        │
│  │                    │    │  sentence-transformers   │        │
│  │ Relationships:     │    │  all-mpnet-base-v2       │        │
│  │  • GENERATES       │    │                          │        │
│  │  • IMPACTS         │    │                          │        │
│  │  • SIGNED          │    │                          │        │
│  │  • HAS_CLAUSE      │    │                          │        │
│  └────────────────────┘    └──────────────────────────┘        │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                SIMULATION LAYER                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                 │
│  │  Budget  │  │ Cashflow │  │ Monte Carlo  │                 │
│  │   Sim    │  │ Forecast │  │ Probabilistic│                 │
│  │          │  │          │  │  Simulation  │                 │
│  └──────────┘  └──────────┘  └──────────────┘                 │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Budgets  │  │ Invoices │  │Contracts │  │  Search  │      │
│  │   API    │  │   API    │  │   API    │  │   API    │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │Simulation│  │Analytics │  │Ingestion │                    │
│  │   API    │  │   API    │  │   API    │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DASHBOARD (React)                              │
│  Page 1: Augmented Budget    │  Page 4: Alerts                 │
│  Page 2: Contract Management │  Page 5: Simulations            │
│  Page 3: Invoices & Treasury │                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Ingestion Layer

**Purpose**: Transform raw financial documents into structured, validated data.

#### 1.1 Document Parsers

- **PDF Parser** (`src/ingestion/parsers/pdf.py`)
  - Uses `pdfplumber` for text extraction
  - Falls back to `pytesseract` OCR for scanned documents
  - Extracts tables and structured data
  - Handles multi-page invoices

- **Excel Parser** (`src/ingestion/parsers/excel.py`)
  - Parses budget Excel files with `openpyxl`
  - Handles merged cells and multiple sheets
  - Normalizes amount formats (1,250.50 vs 1.250,50)
  - Auto-detects table structures

- **JSON Parser** (`src/ingestion/parsers/json.py`)
  - Schema validation with Pydantic
  - Handles missing required fields gracefully
  - Normalizes dates (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
  - Parses nested structures (vendor, client, line items)

#### 1.2 Entity Extractors

- **Amount Parser** (`src/ingestion/extractors/amounts.py`)
  - Handles multiple formats: 1,250.50 / 1.250,50 / 1250.50
  - Detects currency symbols (€, $, £, EUR, USD)
  - Parses tax rates (TVA 20%, VAT 5.5%)
  - Calculates HT ↔ TTC conversions

- **Date Parser** (`src/ingestion/extractors/dates.py`)
  - Supports: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, DD.MM.YYYY
  - Resolves ambiguities (prefers European format)
  - Handles relative dates (Q1 2024 → 2024-03-31)
  - Parses payment terms ("net 30" → 30 days)

- **NER Extractor** (`src/ingestion/extractors/ner.py`)
  - spaCy-based entity extraction
  - Detects: Companies, People, Locations, Organizations
  - Handles French and English text
  - Tags entity roles (CLIENT, VENDOR, BANK)

#### 1.3 Data Validators

- **Schema Validation** (`src/ingestion/validators.py`)
  - Required fields validation
  - Amount range checks (no negative budgets)
  - Date sequence validation (start_date < end_date)
  - Duplicate detection using fuzzy matching
  - Anomaly flagging (unusual amounts, missing vendors)

#### 1.4 Pipeline Orchestrator

- **Main Pipeline** (`src/ingestion/pipeline.py`)
  - Batch processing (default: 50 documents/batch)
  - Multiprocessing for parallel document processing
  - Progress tracking with `tqdm`
  - Error logging to `logs/ingestion.log`
  - Generates ingestion statistics

**Throughput Target**: >100 documents/second

---

### 2. RAG Layer (Knowledge Representation)

**Purpose**: Store and query financial knowledge using graph and vector representations.

#### 2.1 Neo4j Graph Database

- **Graph Schema** (`src/rag/graph.py`)
  - Nodes: Contract, Invoice, Budget, Client, Vendor, Department
  - Relationships: GENERATES, IMPACTS, SIGNED, HAS_CLAUSE
  - Properties: amounts, dates, statuses, payment patterns

- **Query Patterns**:
  - Budget variance by department
  - Overdue invoices with client payment history
  - Contracts expiring within N days
  - Clause-based contract search
  - Payment pattern analysis

**Query Performance Target**: <200ms (p95)

#### 2.2 Vector Store

- **Implementation** (`src/rag/vectorstore.py`)
  - FAISS for approximate nearest neighbor search
  - Sentence-Transformers model: `all-mpnet-base-v2`
  - 768-dimensional embeddings
  - Metadata filtering support

- **Use Cases**:
  - Semantic search: "Find contracts with automatic renewal"
  - Document similarity detection
  - Clause matching across contracts

**Search Latency Target**: <50ms (p95)

---

### 3. Simulation Layer

**Purpose**: Provide "what-if" analysis and predictive modeling for financial decisions.

#### 3.1 Budget Simulator

- **Implementation** (`src/simulation/budget.py`)
  - Simulates impact of +/-X% budget changes
  - Uses historical data for baseline
  - Projects revenue/cost changes over N months
  - Returns confidence intervals (default: 95%)

- **Department-Specific Multipliers**:
  - Marketing: 3.0x revenue multiplier
  - Sales: 5.0x revenue multiplier
  - IT: 1.5x cost efficiency
  - R&D: 10.0x revenue multiplier (high risk/reward)

#### 3.2 Cash Flow Forecaster

- **Implementation** (`src/simulation/cashflow.py`)
  - Predicts liquidity at T+90 days
  - Accounts for client payment delays
  - Includes seasonal variations
  - Supports multiple scenarios (optimistic, base, pessimistic)

- **Liquidity Risk Levels**:
  - **CRITICAL**: Balance < 0
  - **HIGH**: Balance < 20% of payables
  - **MEDIUM**: Balance < 50% of payables
  - **LOW**: Balance > 50% of payables

#### 3.3 Monte Carlo Simulator

- **Implementation** (`src/simulation/monte_carlo.py`)
  - 10,000 iterations by default
  - Models uncertainty in revenues, costs, payment delays
  - Returns distribution with percentiles (P5, P50, P95)
  - Early stopping when converged (convergence threshold: 0.01)

- **Distributions Supported**:
  - Normal distribution
  - Log-normal distribution (ensures positive values)
  - Uniform distribution

---

### 4. API Layer

**Purpose**: RESTful API exposing all FINCENTER functionality.

#### 4.1 Technology Stack

- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Validation**: Pydantic
- **Documentation**: Auto-generated OpenAPI (Swagger UI + ReDoc)

#### 4.2 Endpoint Categories

1. **Budget Endpoints**
   - GET `/api/budgets/{department}/variance`
   - GET `/api/budgets/summary`

2. **Invoice Endpoints**
   - GET `/api/invoices/overdue`
   - GET `/api/invoices/{invoice_id}`

3. **Contract Endpoints**
   - GET `/api/contracts/expiring`
   - GET `/api/contracts/{id}/clauses`

4. **Search Endpoints**
   - POST `/api/search`
   - GET `/api/search/contracts/clauses`

5. **Simulation Endpoints**
   - POST `/api/simulations/budget`
   - POST `/api/simulations/cashflow`
   - POST `/api/simulations/monte-carlo`

6. **Analytics Endpoints**
   - GET `/api/analytics/payment-patterns/{client}`
   - GET `/api/analytics/dashboard/summary`

7. **Ingestion Endpoints**
   - POST `/api/ingestion/start`

#### 4.3 API Performance Targets

- Response time: <200ms (p95) for queries
- Response time: <5s for simulations
- Throughput: 1000+ requests/second

---

### 5. Dashboard Layer

**Purpose**: Interactive web interface for financial intelligence.

#### 5.1 Technology Stack (Planned)

- **Frontend**: React + TypeScript
- **State Management**: Redux or Zustand
- **Charts**: D3.js or Recharts
- **UI Framework**: Tailwind CSS + shadcn/ui
- **Real-time Updates**: WebSockets

#### 5.2 Dashboard Pages

1. **Page 1: Augmented Budget**
   - Real-time variance tracking
   - Department-level drill-down
   - Budget vs. actual visualization
   - Trend analysis

2. **Page 2: Contract & Clause Management**
   - Contract expiry calendar
   - Clause search and analysis
   - Renewal recommendations
   - Risk assessment

3. **Page 3: Invoices & Treasury**
   - Outstanding invoices dashboard
   - Payment delay analysis
   - Cash flow waterfall chart
   - Liquidity forecast

4. **Page 4: Alerts & Recommendations**
   - Budget overruns
   - Overdue invoices
   - Expiring contracts
   - Anomaly detection alerts

5. **Page 5: Simulations & Scenarios**
   - Interactive budget simulator
   - Cash flow forecasting tool
   - Monte Carlo analysis
   - Scenario comparison

---

## Data Flow

### Ingestion Flow

```
1. Document Upload
   ↓
2. File Type Detection (PDF/Excel/JSON)
   ↓
3. Parser Selection
   ↓
4. Entity Extraction (NER, Amounts, Dates)
   ↓
5. Data Validation
   ↓
6. Graph Node Creation (Neo4j)
   ↓
7. Vector Embedding Generation (FAISS)
   ↓
8. Metadata Storage
   ↓
9. Ingestion Statistics Update
```

### Query Flow

```
1. API Request (e.g., "Get overdue invoices")
   ↓
2. Query Neo4j Graph
   ↓
3. Enrich with Vector Search (if semantic query)
   ↓
4. Apply Business Logic (e.g., calculate days overdue)
   ↓
5. Format Response
   ↓
6. Return JSON to Client
```

### Simulation Flow

```
1. Simulation Request (e.g., "Budget +10%")
   ↓
2. Load Historical Data (from Neo4j)
   ↓
3. Calculate Baseline Metrics
   ↓
4. Run Simulation Iterations
   ↓
5. Calculate Statistics (mean, P95, etc.)
   ↓
6. Generate Projections
   ↓
7. Return Results with Confidence Intervals
```

---

## Technology Choices & Rationale

### Why Neo4j?

- **Relationship-centric**: Financial data is inherently relational (contracts → invoices → budgets)
- **Cypher queries**: Intuitive query language for graph traversal
- **ACID compliance**: Ensures data consistency
- **Performance**: Optimized for relationship queries

### Why FAISS?

- **Speed**: Approximate nearest neighbor search in <50ms
- **Scalability**: Handles millions of vectors
- **No external dependencies**: Can run in-memory
- **CPU-friendly**: No GPU required

### Why FastAPI?

- **Performance**: Async support, fastest Python framework
- **Type safety**: Pydantic validation prevents bugs
- **Auto-documentation**: OpenAPI spec generated automatically
- **Developer experience**: Clean, modern Python 3.10+ syntax

### Why Sentence-Transformers?

- **Quality**: State-of-the-art semantic embeddings
- **Multilingual**: Handles French and English
- **Efficient**: 768-dimensional vectors (vs. 1536 for OpenAI)
- **Open-source**: No API costs

---

## Deployment Architecture

### Local Development

```
Docker Compose
├── api (FastAPI)
├── neo4j (Graph DB)
├── postgres (Metadata storage)
└── redis (Cache - optional)
```

### Production (Planned)

```
Load Balancer (Nginx)
   ↓
API Cluster (3+ instances)
   ↓
├── Neo4j Cluster (3 nodes)
├── PostgreSQL + TimescaleDB
├── Redis Cluster
└── Celery Workers (for async ingestion)
```

---

## Security Considerations

### Current Implementation

- No authentication (development only)
- Input validation via Pydantic
- No sensitive data logging

### Production Requirements

1. **Authentication**: JWT tokens or API keys
2. **Authorization**: Role-based access control (RBAC)
3. **Encryption**: TLS for API, encrypted DB connections
4. **Rate Limiting**: 100 requests/minute per user
5. **Audit Logging**: All data modifications logged
6. **PII Masking**: Sensitive fields masked in logs
7. **GDPR Compliance**: Data retention policies, right to deletion

---

## Performance Optimization

### Ingestion

- Batch processing (50 documents/batch)
- Multiprocessing for CPU-bound tasks
- Streaming for large Excel files (don't load entire file)
- Connection pooling for database operations

### RAG Queries

- Neo4j indexes on frequently queried properties
- FAISS HNSW index for fast vector search
- Redis caching for frequently accessed data (5min TTL)
- Query result pagination (limit 100 results)

### API

- Gzip compression for responses
- Database connection pooling
- Async/await for non-blocking I/O
- Background tasks for long-running operations

---

## Monitoring & Observability

### Metrics (Production)

- Ingestion throughput (docs/sec)
- API latency (p50, p95, p99)
- Database query times
- Error rates
- Cache hit rates

### Tools

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Sentry**: Error tracking
- **ELK Stack**: Log aggregation and search

---

## Future Enhancements

1. **Real-time Ingestion**: Webhook-based document ingestion
2. **Email Integration**: Parse invoices from email attachments
3. **OCR Improvements**: Fine-tuned OCR model for financial documents
4. **LLM Integration**: GPT-4 for complex clause extraction
5. **Mobile App**: iOS/Android dashboard
6. **ERP Connectors**: SAP, Ciel, Odoo integrations
7. **Predictive Analytics**: ML models for revenue forecasting
8. **Anomaly Detection**: Unsupervised learning for fraud detection

---

**Last Updated**: 2025-02-16
**Version**: 0.1.0
**Architecture Owner**: Yassine (yassine@fincenter.ai)
