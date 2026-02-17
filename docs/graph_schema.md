# FINCENTER Neo4j Graph Schema

Complete documentation of the financial knowledge graph schema.

---

## Schema Overview

The FINCENTER graph schema models financial entities and their relationships to enable:
- Contract-to-invoice lineage tracking
- Budget impact analysis
- Client payment pattern detection
- Clause-based contract search

---

## Node Types

### 1. Contract

Represents service contracts, agreements, and legal commitments.

**Labels**: `:Contract`

**Properties**:
```cypher
{
  id: STRING (UNIQUE),           // Contract ID (e.g., "CTR-2024-001")
  title: STRING,                 // Contract title/name
  type: STRING,                  // Contract type (e.g., "SERVICE", "SUPPLY")
  vendor: STRING,                // Vendor name
  start_date: DATE,              // Contract start date
  end_date: DATE,                // Contract end date
  annual_value: FLOAT,           // Annual contract value
  total_value: FLOAT,            // Total contract value
  auto_renewal: BOOLEAN,         // Auto-renewal flag
  renewal_notice_days: INTEGER,  // Notice period for non-renewal
  status: STRING,                // Status (e.g., "ACTIVE", "EXPIRED")
  billing_frequency: STRING,     // Billing frequency (e.g., "MONTHLY", "QUARTERLY")
  payment_terms_days: INTEGER,   // Payment terms in days (e.g., 30)
  created_at: DATETIME,          // Creation timestamp
  updated_at: DATETIME           // Last update timestamp
}
```

**Indexes**:
```cypher
CREATE INDEX contract_id_index FOR (c:Contract) ON (c.id);
CREATE INDEX contract_vendor_index FOR (c:Contract) ON (c.vendor);
CREATE INDEX contract_end_date_index FOR (c:Contract) ON (c.end_date);
```

**Example**:
```cypher
CREATE (c:Contract {
  id: "CTR-2024-001",
  title: "Software License Agreement",
  type: "SERVICE",
  vendor: "Software Provider Inc",
  start_date: date("2024-01-01"),
  end_date: date("2024-12-31"),
  annual_value: 120000.0,
  auto_renewal: false,
  renewal_notice_days: 90,
  status: "ACTIVE",
  billing_frequency: "MONTHLY",
  payment_terms_days: 30
})
```

---

### 2. Invoice

Represents vendor invoices and bills.

**Labels**: `:Invoice`

**Properties**:
```cypher
{
  id: STRING (UNIQUE),           // Invoice ID (e.g., "INV-2024-0001")
  number: STRING,                // Invoice number (alternative to id)
  date: DATE,                    // Invoice issue date
  due_date: DATE,                // Payment due date
  paid_date: DATE,               // Actual payment date (if paid)
  vendor: STRING,                // Vendor name
  client: STRING,                // Client name
  amount_ht: FLOAT,              // Amount excluding tax (Hors Taxe)
  tax_rate: FLOAT,               // Tax rate (e.g., 0.20 for 20%)
  tax_amount: FLOAT,             // Tax amount
  amount_ttc: FLOAT,             // Amount including tax (Toutes Taxes Comprises)
  currency: STRING,              // Currency code (e.g., "EUR", "USD")
  status: STRING,                // Status (e.g., "PAID", "UNPAID", "OVERDUE")
  payment_method: STRING,        // Payment method (e.g., "WIRE", "CHECK")
  reference: STRING,             // External reference (PO number, etc.)
  notes: STRING,                 // Additional notes
  created_at: DATETIME,          // Creation timestamp
  updated_at: DATETIME           // Last update timestamp
}
```

**Indexes**:
```cypher
CREATE INDEX invoice_id_index FOR (i:Invoice) ON (i.id);
CREATE INDEX invoice_vendor_index FOR (i:Invoice) ON (i.vendor);
CREATE INDEX invoice_due_date_index FOR (i:Invoice) ON (i.due_date);
CREATE INDEX invoice_status_index FOR (i:Invoice) ON (i.status);
```

**Example**:
```cypher
CREATE (i:Invoice {
  id: "INV-2024-0001",
  date: date("2024-01-15"),
  due_date: date("2024-02-15"),
  vendor: "Software Provider Inc",
  amount_ht: 10000.0,
  tax_rate: 0.20,
  tax_amount: 2000.0,
  amount_ttc: 12000.0,
  currency: "EUR",
  status: "UNPAID"
})
```

---

### 3. Budget

Represents departmental or project budgets.

**Labels**: `:Budget`

**Properties**:
```cypher
{
  id: STRING (UNIQUE),           // Budget ID
  department: STRING,            // Department name
  category: STRING,              // Budget category (e.g., "PERSONNEL", "MARKETING")
  period: STRING,                // Period (e.g., "2024-Q1", "2024-01")
  year: INTEGER,                 // Fiscal year
  quarter: INTEGER,              // Quarter (1-4)
  month: INTEGER,                // Month (1-12)
  budget: FLOAT,                 // Budgeted amount
  actual: FLOAT,                 // Actual spent amount
  forecast: FLOAT,               // Forecasted amount
  variance: FLOAT,               // Variance (actual - budget)
  variance_percent: FLOAT,       // Variance percentage
  notes: STRING,                 // Notes
  created_at: DATETIME,          // Creation timestamp
  updated_at: DATETIME           // Last update timestamp
}
```

**Indexes**:
```cypher
CREATE INDEX budget_department_index FOR (b:Budget) ON (b.department);
CREATE INDEX budget_year_index FOR (b:Budget) ON (b.year);
CREATE INDEX budget_period_index FOR (b:Budget) ON (b.period);
```

**Example**:
```cypher
CREATE (b:Budget {
  id: "BUD-2024-Q1-MARKETING",
  department: "Marketing",
  category: "ADVERTISING",
  period: "2024-Q1",
  year: 2024,
  quarter: 1,
  budget: 50000.0,
  actual: 52000.0,
  variance: 2000.0,
  variance_percent: 4.0
})
```

---

### 4. Client

Represents clients/customers.

**Labels**: `:Client`

**Properties**:
```cypher
{
  name: STRING (UNIQUE),         // Client name
  type: STRING,                  // Client type (e.g., "CORPORATE", "SME")
  industry: STRING,              // Industry sector
  address: STRING,               // Physical address
  email: STRING,                 // Contact email
  phone: STRING,                 // Contact phone
  siret: STRING,                 // SIRET number (France)
  vat_number: STRING,            // VAT number
  payment_terms_days: INTEGER,   // Default payment terms
  credit_limit: FLOAT,           // Credit limit
  status: STRING,                // Status (e.g., "ACTIVE", "INACTIVE")
  created_at: DATETIME,          // Creation timestamp
  updated_at: DATETIME           // Last update timestamp
}
```

**Indexes**:
```cypher
CREATE INDEX client_name_index FOR (cl:Client) ON (cl.name);
```

**Example**:
```cypher
CREATE (cl:Client {
  name: "Entreprise Alpha",
  type: "CORPORATE",
  industry: "TECHNOLOGY",
  email: "contact@alpha.com",
  payment_terms_days: 30,
  status: "ACTIVE"
})
```

---

### 5. Vendor

Represents vendors/suppliers.

**Labels**: `:Vendor`

**Properties**:
```cypher
{
  name: STRING (UNIQUE),         // Vendor name
  type: STRING,                  // Vendor type
  address: STRING,               // Physical address
  email: STRING,                 // Contact email
  phone: STRING,                 // Contact phone
  siret: STRING,                 // SIRET number (France)
  vat_number: STRING,            // VAT number
  iban: STRING,                  // Bank account (IBAN)
  bic: STRING,                   // Bank identifier (BIC/SWIFT)
  payment_terms_days: INTEGER,   // Standard payment terms
  status: STRING,                // Status (e.g., "ACTIVE", "INACTIVE")
  rating: FLOAT,                 // Vendor rating (0-5)
  created_at: DATETIME,          // Creation timestamp
  updated_at: DATETIME           // Last update timestamp
}
```

**Indexes**:
```cypher
CREATE INDEX vendor_name_index FOR (v:Vendor) ON (v.name);
```

**Example**:
```cypher
CREATE (v:Vendor {
  name: "Software Provider Inc",
  type: "TECHNOLOGY",
  email: "billing@softwareprovider.com",
  siret: "12345678901234",
  payment_terms_days: 30,
  status: "ACTIVE",
  rating: 4.5
})
```

---

### 6. Clause

Represents contract clauses.

**Labels**: `:Clause`

**Properties**:
```cypher
{
  id: STRING,                    // Clause ID
  type: STRING,                  // Clause type (e.g., "PRICE_REVISION", "PENALTY")
  description: STRING,           // Clause description
  value: STRING,                 // Clause value (if applicable)
  impact: STRING,                // Financial impact level (e.g., "HIGH", "MEDIUM", "LOW")
  requires_action: BOOLEAN,      // Whether action is required
  action_date: DATE,             // Date action is required
  notes: STRING                  // Additional notes
}
```

**Example**:
```cypher
CREATE (cl:Clause {
  id: "CLAUSE-001",
  type: "PRICE_REVISION",
  description: "Annual price revision based on CPI index",
  value: "CPI + 2%",
  impact: "MEDIUM",
  requires_action: true,
  action_date: date("2025-01-01")
})
```

---

### 7. Department

Represents organizational departments.

**Labels**: `:Department`

**Properties**:
```cypher
{
  name: STRING (UNIQUE),         // Department name
  code: STRING,                  // Department code
  manager: STRING,               // Department manager name
  cost_center: STRING,           // Cost center code
  budget_total: FLOAT,           // Total annual budget
  headcount: INTEGER,            // Number of employees
  status: STRING                 // Status (e.g., "ACTIVE")
}
```

**Example**:
```cypher
CREATE (d:Department {
  name: "Marketing",
  code: "MKT",
  manager: "Jane Doe",
  cost_center: "CC-100",
  budget_total: 200000.0,
  headcount: 15,
  status: "ACTIVE"
})
```

---

## Relationship Types

### 1. GENERATES

**Pattern**: `(Contract)-[:GENERATES]->(Invoice)`

**Direction**: Contract → Invoice

**Properties**:
```cypher
{
  billing_cycle: STRING,         // Billing cycle (e.g., "MONTHLY", "QUARTERLY")
  sequence_number: INTEGER,      // Sequence number for this contract
  generated_date: DATE           // Date invoice was generated
}
```

**Example**:
```cypher
MATCH (c:Contract {id: "CTR-2024-001"})
MATCH (i:Invoice {id: "INV-2024-0001"})
CREATE (c)-[:GENERATES {
  billing_cycle: "MONTHLY",
  sequence_number: 1,
  generated_date: date("2024-01-15")
}]->(i)
```

**Use Cases**:
- Track which invoices belong to which contract
- Calculate total invoiced vs. contract value
- Identify missing invoices for a contract

---

### 2. IMPACTS

**Pattern**: `(Invoice)-[:IMPACTS]->(Budget)`

**Direction**: Invoice → Budget

**Properties**:
```cypher
{
  category: STRING,              // Budget category impacted
  percentage: FLOAT              // Percentage of budget consumed
}
```

**Example**:
```cypher
MATCH (i:Invoice {id: "INV-2024-0001"})
MATCH (b:Budget {id: "BUD-2024-Q1-IT"})
CREATE (i)-[:IMPACTS {
  category: "SOFTWARE",
  percentage: 24.0
}]->(b)
```

**Use Cases**:
- Budget impact analysis
- Track which invoices affect which budgets
- Calculate variance sources

---

### 3. SIGNED

**Pattern**: `(Client)-[:SIGNED]->(Contract)`

**Direction**: Client → Contract

**Properties**:
```cypher
{
  signed_date: DATE,             // Date contract was signed
  signatory: STRING,             // Name of signatory
  role: STRING                   // Role (e.g., "CLIENT", "VENDOR")
}
```

**Example**:
```cypher
MATCH (cl:Client {name: "Entreprise Alpha"})
MATCH (c:Contract {id: "CTR-2024-001"})
CREATE (cl)-[:SIGNED {
  signed_date: date("2024-01-01"),
  signatory: "John Smith",
  role: "CLIENT"
}]->(c)
```

**Use Cases**:
- Find all contracts for a client
- Analyze client relationship value
- Track contract history

---

### 4. HAS_CLAUSE

**Pattern**: `(Contract)-[:HAS_CLAUSE]->(Clause)`

**Direction**: Contract → Clause

**Properties**:
```cypher
{
  section: STRING,               // Contract section where clause appears
  page: INTEGER                  // Page number (if applicable)
}
```

**Example**:
```cypher
MATCH (c:Contract {id: "CTR-2024-001"})
MATCH (cl:Clause {type: "PRICE_REVISION"})
CREATE (c)-[:HAS_CLAUSE {
  section: "Article 5",
  page: 3
}]->(cl)
```

**Use Cases**:
- Clause-based contract search
- Risk assessment (contracts with penalty clauses)
- Renewal planning (auto-renewal clauses)

---

### 5. HAS_PAYMENT_PATTERN

**Pattern**: `(Client)-[:HAS_PAYMENT_PATTERN]->(Vendor)`

**Direction**: Client → Vendor (or standalone on Client)

**Properties**:
```cypher
{
  avg_delay_days: FLOAT,         // Average payment delay in days
  std_dev_days: FLOAT,           // Standard deviation of delays
  total_invoices: INTEGER,       // Total number of invoices
  on_time_rate: FLOAT,           // Percentage paid on time
  last_updated: DATETIME         // Last pattern update
}
```

**Example**:
```cypher
MATCH (cl:Client {name: "Entreprise Alpha"})
CREATE (cl)-[:HAS_PAYMENT_PATTERN {
  avg_delay_days: 15.5,
  std_dev_days: 8.2,
  total_invoices: 24,
  on_time_rate: 0.45,
  last_updated: datetime()
}]->()
```

**Use Cases**:
- Cash flow forecasting
- Credit risk assessment
- Payment delay prediction

---

### 6. MANAGES

**Pattern**: `(Department)-[:MANAGES]->(Budget)`

**Direction**: Department → Budget

**Properties**:
```cypher
{
  responsibility: STRING         // Type of responsibility
}
```

**Example**:
```cypher
MATCH (d:Department {name: "Marketing"})
MATCH (b:Budget {id: "BUD-2024-Q1-MARKETING"})
CREATE (d)-[:MANAGES {
  responsibility: "PRIMARY"
}]->(b)
```

---

## Common Query Patterns

### 1. Find Overdue Invoices

```cypher
MATCH (i:Invoice)
WHERE i.status = 'UNPAID'
  AND i.due_date < date()
WITH i, duration.between(date(i.due_date), date()).days AS days_overdue
WHERE days_overdue >= 15
RETURN i.id AS invoice_id,
       i.vendor AS vendor,
       i.amount_ttc AS amount,
       days_overdue
ORDER BY days_overdue DESC
```

### 2. Budget Variance by Department

```cypher
MATCH (b:Budget)
WHERE b.year = 2024
RETURN b.department AS department,
       SUM(b.budget) AS total_budget,
       SUM(b.actual) AS total_actual,
       SUM(b.variance) AS total_variance,
       SUM(b.variance) / SUM(b.budget) * 100 AS variance_percent
ORDER BY variance_percent DESC
```

### 3. Contracts Expiring Soon

```cypher
MATCH (c:Contract)
WHERE c.status = 'ACTIVE'
  AND c.end_date > date()
  AND c.end_date <= date() + duration({days: 90})
WITH c, duration.between(date(), date(c.end_date)).days AS days_until_expiry
RETURN c.id AS contract_id,
       c.vendor AS vendor,
       c.end_date AS end_date,
       c.annual_value AS annual_value,
       c.auto_renewal AS auto_renewal,
       days_until_expiry
ORDER BY days_until_expiry
```

### 4. Contract-to-Invoice Lineage

```cypher
MATCH (c:Contract {id: 'CTR-2024-001'})-[:GENERATES]->(i:Invoice)
RETURN c.id AS contract_id,
       c.annual_value AS contract_value,
       COLLECT(i.id) AS invoice_ids,
       SUM(i.amount_ttc) AS total_invoiced,
       COUNT(i) AS invoice_count
```

### 5. Client Payment Patterns

```cypher
MATCH (cl:Client {name: 'Entreprise Alpha'})-[:SIGNED]->(c:Contract)-[:GENERATES]->(i:Invoice)
WHERE i.status = 'PAID'
WITH duration.between(date(i.due_date), date(i.paid_date)).days AS delay
RETURN AVG(delay) AS avg_delay_days,
       STDEV(delay) AS delay_variance,
       MIN(delay) AS min_delay,
       MAX(delay) AS max_delay,
       COUNT(*) AS total_invoices,
       SUM(CASE WHEN delay <= 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS on_time_rate
```

### 6. Clause-Based Contract Search

```cypher
MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause {type: 'PRICE_REVISION'})
RETURN c.id AS contract_id,
       c.vendor AS vendor,
       c.annual_value AS annual_value,
       cl.description AS clause_description
ORDER BY c.annual_value DESC
```

### 7. Budget Impact Analysis

```cypher
MATCH (i:Invoice)-[r:IMPACTS]->(b:Budget)
WHERE b.department = 'Marketing'
  AND b.year = 2024
RETURN b.period AS period,
       COUNT(i) AS invoice_count,
       SUM(i.amount_ttc) AS total_invoiced,
       b.budget AS budgeted_amount,
       b.actual AS actual_spent,
       b.variance AS variance
ORDER BY b.period
```

---

## Constraints & Validations

### Uniqueness Constraints

```cypher
CREATE CONSTRAINT contract_id_unique FOR (c:Contract) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT invoice_id_unique FOR (i:Invoice) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT budget_id_unique FOR (b:Budget) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT client_name_unique FOR (cl:Client) REQUIRE cl.name IS UNIQUE;
CREATE CONSTRAINT vendor_name_unique FOR (v:Vendor) REQUIRE v.name IS UNIQUE;
```

### Property Existence Constraints

```cypher
CREATE CONSTRAINT contract_id_exists FOR (c:Contract) REQUIRE c.id IS NOT NULL;
CREATE CONSTRAINT invoice_id_exists FOR (i:Invoice) REQUIRE i.id IS NOT NULL;
CREATE CONSTRAINT budget_dept_exists FOR (b:Budget) REQUIRE b.department IS NOT NULL;
```

---

## Performance Recommendations

### Indexes

Create indexes on frequently queried properties:

```cypher
// Date-based queries
CREATE INDEX invoice_due_date FOR (i:Invoice) ON (i.due_date);
CREATE INDEX contract_end_date FOR (c:Contract) ON (c.end_date);

// Status-based queries
CREATE INDEX invoice_status FOR (i:Invoice) ON (i.status);
CREATE INDEX contract_status FOR (c:Contract) ON (c.status);

// Vendor/Client lookups
CREATE INDEX invoice_vendor FOR (i:Invoice) ON (i.vendor);
CREATE INDEX contract_vendor FOR (c:Contract) ON (c.vendor);

// Department-based queries
CREATE INDEX budget_department FOR (b:Budget) ON (b.department);
CREATE INDEX budget_year FOR (b:Budget) ON (b.year);
```

### Query Optimization Tips

1. **Use LIMIT**: Always limit results for large queries
2. **Index Lookups**: Start queries with indexed properties
3. **Avoid Cartesian Products**: Use proper WHERE clauses
4. **EXPLAIN/PROFILE**: Analyze query plans before production

---

## Schema Evolution

### Version 0.1.0 (Current)

- Basic node types: Contract, Invoice, Budget, Client, Vendor, Clause
- Core relationships: GENERATES, IMPACTS, SIGNED, HAS_CLAUSE
- Payment pattern tracking

### Planned for 0.2.0

- **New Nodes**: AccountingEntry, Payment, Alert
- **New Relationships**: PAYS, TRIGGERS, RESOLVES
- **Enhanced Properties**: Risk scores, ML predictions
- **Temporal Properties**: Version history tracking

---

**Last Updated**: 2025-02-16
**Schema Version**: 0.1.0
**Maintained By**: Yassine (yassine@fincenter.ai)
