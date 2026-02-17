"""
FINCENTER Graph Database Operations

This module handles all interactions with the Neo4j graph database,
including creating nodes, relationships, and querying the financial knowledge graph.
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from src.config import settings


class FinancialGraph:
    """Interface to Neo4j graph database for financial data."""
    
    def __init__(self):
        """Initialize connection to Neo4j."""
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self._create_constraints()
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
    
    def _create_constraints(self):
        """Create uniqueness constraints on key properties."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Budget) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Client) REQUIRE cl.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vendor) REQUIRE v.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:EpisodicMemory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (w:WeakSignal) REQUIRE w.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Recommendation) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Scenario) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Prediction) REQUIRE p.id IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation warning: {e}")
    
    # ============================================
    # Budget Operations
    # ============================================
    
    async def get_budget_variance(self, department: str) -> Optional[Dict[str, Any]]:
        """
        Get budget variance for a department.
        
        Args:
            department: Department name
        
        Returns:
            Budget variance data or None if not found
        """
        query = """
        MATCH (b:Budget {department: $department})
        RETURN b.department AS department,
               b.budget AS budget,
               b.actual AS actual,
               (b.actual - b.budget) AS variance,
               (b.actual - b.budget) / b.budget * 100 AS variance_percent
        """
        
        with self.driver.session() as session:
            result = session.run(query, department=department)
            record = result.single()
            
            if record:
                return dict(record)
            return None
    
    async def get_budget_summary(self, year: int) -> List[Dict[str, Any]]:
        """
        Get budget summary for all departments in a year.
        
        Args:
            year: Fiscal year
        
        Returns:
            List of budget summaries
        """
        query = """
        MATCH (b:Budget)
        WHERE b.year = $year AND b.department <> 'UNKNOWN'
        WITH b.department AS department,
             sum(b.budget) AS budget,
             sum(b.actual) AS actual
        RETURN department,
               budget,
               actual,
               (actual - budget) AS variance
        ORDER BY department
        """
        
        with self.driver.session() as session:
            result = session.run(query, year=year)
            return [dict(record) for record in result]
    
    # ============================================
    # Invoice Operations
    # ============================================
    
    async def get_overdue_invoices(self, days_overdue: int = 0) -> List[Dict[str, Any]]:
        """
        Get all overdue invoices.
        
        Args:
            days_overdue: Minimum days overdue (0 for all overdue)
        
        Returns:
            List of overdue invoices
        """
        query = """
        MATCH (i:Invoice)
        WHERE i.status = 'UNPAID'
          AND i.due_date IS NOT NULL
          AND i.due_date < date()
          AND duration.inDays(i.due_date, date()).days >= $days
        WITH i, duration.inDays(i.due_date, date()).days AS raw_days
        RETURN i.id AS invoice_id,
               toString(i.date) AS date,
               i.vendor AS vendor,
               i.amount AS amount,
               i.status AS status,
               CASE WHEN raw_days > 365 THEN 365 ELSE raw_days END AS days_overdue
        ORDER BY days_overdue DESC
        """

        with self.driver.session() as session:
            result = session.run(query, days=days_overdue)
            return [dict(record) for record in result]
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific invoice.
        
        Args:
            invoice_id: Invoice ID
        
        Returns:
            Invoice data or None if not found
        """
        query = """
        MATCH (i:Invoice {id: $invoice_id})
        RETURN i.id AS invoice_id,
               toString(i.date) AS date,
               i.vendor AS vendor,
               i.amount AS amount,
               i.status AS status
        """
        
        with self.driver.session() as session:
            result = session.run(query, invoice_id=invoice_id)
            record = result.single()
            
            if record:
                return dict(record)
            return None
    
    # ============================================
    # Contract Operations
    # ============================================
    
    async def get_expiring_contracts(self, days_ahead: int = 90) -> List[Dict[str, Any]]:
        """
        Get contracts expiring within specified days.
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of expiring contracts
        """
        query = """
        MATCH (c:Contract)
        WHERE c.end_date IS NOT NULL
          AND c.end_date > date()
          AND c.end_date <= date() + duration({days: $days})
        RETURN c.id AS contract_id,
               c.vendor AS vendor,
               toString(c.end_date) AS end_date,
               c.annual_value AS annual_value,
               c.auto_renewal AS auto_renewal,
               duration.inDays(date(), c.end_date).days AS days_until_expiry
        ORDER BY days_until_expiry
        """
        
        with self.driver.session() as session:
            result = session.run(query, days=days_ahead)
            return [dict(record) for record in result]
    
    async def search_contracts_by_clause(self, clause_type: str) -> List[Dict[str, Any]]:
        """
        Find contracts with specific clause type.
        
        Args:
            clause_type: Type of clause (e.g., "price_revision", "penalty")
        
        Returns:
            List of contracts with matching clauses
        """
        query = """
        MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause {type: $clause_type})
        RETURN c.id AS contract_id,
               c.vendor AS vendor,
               cl.description AS clause_description
        """
        
        with self.driver.session() as session:
            result = session.run(query, clause_type=clause_type)
            return [dict(record) for record in result]
    
    # ============================================
    # Analytics Operations
    # ============================================
    
    async def analyze_client_payment_patterns(self, client: str) -> Optional[Dict[str, Any]]:
        """
        Analyze payment patterns for a specific client.
        
        Args:
            client: Client name
        
        Returns:
            Payment pattern analysis
        """
        query = """
        MATCH (cl:Client {name: $client})-[:SIGNED]->(c:Contract)-[:GENERATES]->(i:Invoice)
        WHERE i.status = 'PAID'
        WITH duration.between(date(i.due_date), date(i.paid_date)).days AS delay
        RETURN AVG(delay) AS avg_delay_days,
               STDEV(delay) AS delay_variance,
               MIN(delay) AS min_delay,
               MAX(delay) AS max_delay,
               COUNT(*) AS total_invoices
        """
        
        with self.driver.session() as session:
            result = session.run(query, client=client)
            record = result.single()
            
            if record:
                return dict(record)
            return None
    
    # ============================================
    # Graph Creation (for ingestion)
    # ============================================
    
    def create_invoice(self, invoice_data: Dict[str, Any]):
        """Create an invoice node in the graph."""
        # Extract just the date part from datetime strings
        date_str = str(invoice_data['date']).split()[0] if invoice_data.get('date') else ''
        due_date_str = str(invoice_data['due_date']).split()[0] if invoice_data.get('due_date') else ''

        query = """
        MERGE (i:Invoice {id: $id})
        SET i.date = CASE WHEN $date <> '' THEN date($date) ELSE null END,
            i.due_date = CASE WHEN $due_date <> '' THEN date($due_date) ELSE null END,
            i.vendor = $vendor,
            i.amount = $amount,
            i.status = $status
        RETURN i
        """

        with self.driver.session() as session:
            session.run(query,
                id=invoice_data['id'],
                date=date_str,
                due_date=due_date_str,
                vendor=invoice_data['vendor'],
                amount=invoice_data['amount'],
                status=invoice_data['status']
            )
    
    def create_contract(self, contract_data: Dict[str, Any]):
        """Create a contract node in the graph."""
        # Extract just the date part from datetime strings
        start_date_str = str(contract_data['start_date']).split()[0] if contract_data.get('start_date') else ''
        end_date_str = str(contract_data['end_date']).split()[0] if contract_data.get('end_date') else ''

        query = """
        MERGE (c:Contract {id: $id})
        SET c.type = $type,
            c.vendor = $vendor,
            c.start_date = CASE WHEN $start_date <> '' THEN date($start_date) ELSE null END,
            c.end_date = CASE WHEN $end_date <> '' THEN date($end_date) ELSE null END,
            c.annual_value = $annual_value,
            c.auto_renewal = $auto_renewal
        RETURN c
        """

        with self.driver.session() as session:
            session.run(query,
                id=contract_data['id'],
                type=contract_data['type'],
                vendor=contract_data['vendor'],
                start_date=start_date_str,
                end_date=end_date_str,
                annual_value=contract_data['annual_value'],
                auto_renewal=contract_data['auto_renewal']
            )
    
    def link_contract_to_invoice(self, contract_id: str, invoice_id: str):
        """Create relationship between contract and invoice."""
        query = """
        MATCH (c:Contract {id: $contract_id})
        MATCH (i:Invoice {id: $invoice_id})
        MERGE (c)-[:GENERATES]->(i)
        """

        with self.driver.session() as session:
            session.run(query, contract_id=contract_id, invoice_id=invoice_id)

    # ============================================
    # Node Creation Methods (called by ingestion pipeline)
    # ============================================

    def create_invoice_node(self, document: Dict[str, Any]):
        """
        Create invoice node from ingestion pipeline document.

        Args:
            document: Parsed invoice document with metadata
        """
        # Check if data is nested or at top level
        data = document.get('data', document)

        # Extract vendor name
        vendor = data.get('vendor', {})
        vendor_name = vendor.get('name', 'UNKNOWN') if isinstance(vendor, dict) else str(vendor)

        invoice_data = {
            'id': data.get('invoice_id', 'UNKNOWN'),
            'date': str(data.get('date', '')),
            'due_date': str(data.get('due_date', '')),
            'vendor': vendor_name,
            'amount': float(data.get('total_ttc', 0)),
            'status': data.get('status', 'UNPAID')
        }
        self.create_invoice(invoice_data)

    def create_contract_node(self, document: Dict[str, Any]):
        """
        Create contract node from ingestion pipeline document.

        Args:
            document: Parsed contract document with metadata
        """
        # Check if data is nested or at top level
        data = document.get('data', document)

        # Extract vendor name from parties if available
        vendor_name = 'UNKNOWN'
        parties = data.get('parties', [])
        if isinstance(parties, list) and len(parties) > 0:
            # Find the provider party
            for party in parties:
                if isinstance(party, dict):
                    role = party.get('role', '').upper()
                    if role in ['PROVIDER', 'VENDOR', 'SUPPLIER']:
                        vendor_name = party.get('name', 'UNKNOWN')
                        break
            # If no provider found, use first party
            if vendor_name == 'UNKNOWN' and isinstance(parties[0], dict):
                vendor_name = parties[0].get('name', 'UNKNOWN')
        elif 'vendor' in data:
            vendor = data.get('vendor', {})
            vendor_name = vendor.get('name', 'UNKNOWN') if isinstance(vendor, dict) else str(vendor)

        # Handle annual_value which might be stored as amount
        annual_value = data.get('annual_value', data.get('amount', 0))
        # Parse string amounts
        if isinstance(annual_value, str):
            annual_value = annual_value.replace(',', '').replace(' ', '').replace('EUR', '')
            try:
                annual_value = float(annual_value)
            except ValueError:
                annual_value = 0

        contract_data = {
            'id': data.get('contract_id', 'UNKNOWN'),
            'type': data.get('type', data.get('category', 'SERVICE')),
            'vendor': vendor_name,
            'start_date': str(data.get('start_date', '')),
            'end_date': str(data.get('end_date', '')),
            'annual_value': float(annual_value) if annual_value else 0,
            'auto_renewal': data.get('auto_renewal', data.get('auto_renew', False))
        }
        self.create_contract(contract_data)

    # ============================================
    # EpisodicMemory Node Operations
    # ============================================

    def create_episodic_memory_node(self, pattern_data: Dict[str, Any]):
        """Create or update an EpisodicMemory node."""
        query = """
        MERGE (m:EpisodicMemory {id: $id})
        SET m.type = $type,
            m.subject = $subject,
            m.description = $description,
            m.confidence = $confidence,
            m.evidence_count = $evidence_count,
            m.last_updated = $last_updated
        RETURN m
        """
        with self.driver.session() as session:
            session.run(query, **pattern_data)

    def get_episodic_memories(self, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return stored episodic memory patterns."""
        if pattern_type:
            query = """
            MATCH (m:EpisodicMemory {type: $type})
            RETURN m.id AS id, m.type AS type, m.subject AS subject,
                   m.description AS description, m.confidence AS confidence,
                   m.evidence_count AS evidence_count, m.last_updated AS last_updated
            ORDER BY m.confidence DESC
            """
            with self.driver.session() as session:
                result = session.run(query, type=pattern_type)
                return [dict(r) for r in result]
        else:
            query = """
            MATCH (m:EpisodicMemory)
            RETURN m.id AS id, m.type AS type, m.subject AS subject,
                   m.description AS description, m.confidence AS confidence,
                   m.evidence_count AS evidence_count, m.last_updated AS last_updated
            ORDER BY m.confidence DESC
            """
            with self.driver.session() as session:
                result = session.run(query)
                return [dict(r) for r in result]

    # ============================================
    # WeakSignal Node Operations
    # ============================================

    def create_weak_signal_node(self, signal_data: Dict[str, Any]):
        """Create a WeakSignal node."""
        query = """
        MERGE (w:WeakSignal {id: $id})
        SET w.score = $score,
            w.signals_json = $signals_json,
            w.detected_at = $detected_at,
            w.acknowledged = $acknowledged
        RETURN w
        """
        with self.driver.session() as session:
            session.run(query, **signal_data)

    def get_weak_signals(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """Return active weak signal clusters."""
        query = """
        MATCH (w:WeakSignal)
        WHERE w.acknowledged = false OR NOT $only_active
        RETURN w.id AS id, w.score AS score, w.signals_json AS signals_json,
               w.detected_at AS detected_at, w.acknowledged AS acknowledged
        ORDER BY w.score DESC
        """
        with self.driver.session() as session:
            result = session.run(query, only_active=only_active)
            return [dict(r) for r in result]

    # ============================================
    # Recommendation Node Operations
    # ============================================

    def create_recommendation_node(self, rec_data: Dict[str, Any]):
        """Create or update a Recommendation node."""
        query = """
        MERGE (r:Recommendation {id: $id})
        SET r.category = $category,
            r.title = $title,
            r.description = $description,
            r.priority_score = $priority_score,
            r.expected_impact_eur = $expected_impact_eur,
            r.confidence = $confidence,
            r.supporting_evidence = $supporting_evidence,
            r.created_at = $created_at,
            r.acknowledged = $acknowledged
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, **rec_data)

    def get_recommendations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return top recommendations sorted by priority."""
        query = """
        MATCH (r:Recommendation)
        RETURN r.id AS id, r.category AS category, r.title AS title,
               r.description AS description, r.priority_score AS priority_score,
               r.expected_impact_eur AS expected_impact_eur, r.confidence AS confidence,
               r.supporting_evidence AS supporting_evidence, r.created_at AS created_at,
               r.acknowledged AS acknowledged
        ORDER BY r.priority_score DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, limit=limit)
            return [dict(r) for r in result]

    def acknowledge_recommendation(self, rec_id: str):
        """Mark a recommendation as acknowledged."""
        query = "MATCH (r:Recommendation {id: $id}) SET r.acknowledged = true"
        with self.driver.session() as session:
            session.run(query, id=rec_id)

    # ============================================
    # Prediction Node Operations (Feedback Loop)
    # ============================================

    def create_prediction_node(self, pred_data: Dict[str, Any]):
        """Create a Prediction node."""
        query = """
        MERGE (p:Prediction {id: $id})
        SET p.entity_type = $entity_type,
            p.entity_id = $entity_id,
            p.metric = $metric,
            p.predicted_value = $predicted_value,
            p.actual_value = $actual_value,
            p.error_pct = $error_pct,
            p.timestamp = $timestamp,
            p.reindexed = $reindexed
        RETURN p
        """
        with self.driver.session() as session:
            session.run(query, **pred_data)

    def get_predictions(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return prediction records."""
        if entity_type:
            query = """
            MATCH (p:Prediction {entity_type: $entity_type})
            RETURN p.id AS id, p.entity_type AS entity_type, p.entity_id AS entity_id,
                   p.metric AS metric, p.predicted_value AS predicted_value,
                   p.actual_value AS actual_value, p.error_pct AS error_pct,
                   p.timestamp AS timestamp, p.reindexed AS reindexed
            ORDER BY p.timestamp DESC
            """
            with self.driver.session() as session:
                result = session.run(query, entity_type=entity_type)
                return [dict(r) for r in result]
        else:
            query = """
            MATCH (p:Prediction)
            RETURN p.id AS id, p.entity_type AS entity_type, p.entity_id AS entity_id,
                   p.metric AS metric, p.predicted_value AS predicted_value,
                   p.actual_value AS actual_value, p.error_pct AS error_pct,
                   p.timestamp AS timestamp, p.reindexed AS reindexed
            ORDER BY p.timestamp DESC
            """
            with self.driver.session() as session:
                result = session.run(query)
                return [dict(r) for r in result]

    # ============================================
    # Raw Data Access Helpers (for intelligence modules)
    # ============================================

    def get_all_invoices_raw(self) -> List[Dict[str, Any]]:
        """Return all invoices with raw fields for analysis."""
        query = """
        MATCH (i:Invoice)
        WITH i, CASE WHEN i.due_date IS NOT NULL
                     THEN duration.inDays(i.due_date, date()).days
                     ELSE 0 END AS raw_days
        RETURN i.id AS invoice_id, i.vendor AS vendor, i.amount AS amount,
               i.status AS status,
               CASE WHEN raw_days > 365 THEN 365 ELSE raw_days END AS days_overdue
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [dict(r) for r in result]

    def get_all_budgets_raw(self) -> List[Dict[str, Any]]:
        """Return all budget nodes for analysis."""
        query = """
        MATCH (b:Budget)
        RETURN b.department AS department, b.year AS year,
               b.budget AS budget, b.actual AS actual, b.variance AS variance
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [dict(r) for r in result]

    def get_all_contracts_raw(self) -> List[Dict[str, Any]]:
        """Return all contracts with days_until_expiry for analysis."""
        query = """
        MATCH (c:Contract)
        RETURN c.id AS contract_id, c.vendor AS vendor,
               c.annual_value AS annual_value,
               CASE WHEN c.end_date IS NOT NULL
                    THEN duration.inDays(date(), c.end_date).days
                    ELSE 999 END AS days_until_expiry
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [dict(r) for r in result]

    def create_budget_node(self, budget_item: Dict[str, Any]):
        """
        Create budget node from ingestion pipeline data.

        Args:
            budget_item: Budget item with department, amounts, etc.
        """
        query = """
        MERGE (b:Budget {department: $department, year: $year, category: $category})
        SET b.budget = $budget,
            b.actual = $actual,
            b.variance = $variance
        RETURN b
        """

        # Handle French field name "département" as well as English "department"
        department = (
            budget_item.get('department')
            or budget_item.get('département')
            or 'UNKNOWN'
        )

        # Calculate actual from quarterly values if not provided directly
        def _parse_amount(v) -> float:
            if v is None:
                return 0.0
            import re as _re
            s = str(v).replace(',', '').strip()
            # Extract leading numeric portion (handles "67100.10 EUR" etc.)
            m = _re.match(r'[-+]?\d*\.?\d+', s)
            return float(m.group()) if m else 0.0

        actual = budget_item.get('actual')
        if actual is None or actual == 0:
            actual = sum(
                _parse_amount(budget_item.get(q))
                for q in ('q1', 'q2', 'q3', 'q4')
            )
        else:
            actual = float(actual)

        budget_amount = _parse_amount(budget_item.get('budget', 0))
        variance = actual - budget_amount

        # Infer year from source_file if not present
        year = budget_item.get('year')
        if not year:
            src = str(budget_item.get('source_file', ''))
            import re
            m = re.search(r'(\d{4})', src)
            year = int(m.group(1)) if m else 2024

        with self.driver.session() as session:
            session.run(query,
                       department=department,
                       year=int(year),
                       category=budget_item.get('category', 'GENERAL'),
                       budget=budget_amount,
                       actual=actual,
                       variance=variance
                       )
