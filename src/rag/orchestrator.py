"""
FINCENTER RAG Orchestrator

The central orchestration component of the RAGraph layer.
Combines semantic vector search, Neo4j graph traversal, and LLM reasoning
into a single unified query interface.

Architecture position:
    Sources → Ingestion → [RAG Orchestrator] → Decision Fusion → Recommendations

The orchestrator:
    1. Embeds the query into a vector
    2. Retrieves semantically similar documents (VectorStore)
    3. Enriches results with graph relationships (Neo4j: contracts → invoices → budgets)
    4. Injects episodic memory patterns as additional context
    5. Sends the combined context to the LLM for reasoning
    6. Returns both the answer and the evidence used (grounded response)
"""

from typing import List, Dict, Any, Optional


class RAGOrchestrator:
    """
    Coordinates vector search, graph traversal, and LLM reasoning.

    This is the central intelligence component of the RAGraph layer.
    It implements the Retrieval-Augmented Generation pattern with
    financial graph enrichment.
    """

    def __init__(self, graph, vectorstore, llm_fn, memory=None, decision_fusion=None, weak_signals=None, recommendations=None):
        """
        Args:
            graph:           FinancialGraph instance (Neo4j)
            vectorstore:     VectorStore instance (FAISS embeddings)
            llm_fn:          Callable(question, context) -> str
            memory:          EpisodicMemory instance (optional)
            decision_fusion: DecisionFusion instance (optional)
            weak_signals:    WeakSignalDetector instance (optional)
            recommendations: RecommendationEngine instance (optional)
        """
        self.graph = graph
        self.vectorstore = vectorstore
        self.llm_fn = llm_fn
        self.memory = memory
        self.decision_fusion = decision_fusion
        self.weak_signals = weak_signals
        self.recommendations = recommendations

    # ============================================
    # Public Query Interface
    # ============================================

    async def query(
        self,
        question: str,
        top_k: int = 5,
        include_graph_context: bool = True,
        include_memory: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a full RAG pipeline for a financial question.

        Args:
            question:              Natural language question
            top_k:                 Number of vector search results to retrieve
            include_graph_context: Whether to enrich with graph traversal
            include_memory:        Whether to inject episodic memory patterns

        Returns:
            Dict with 'answer', 'context_used', 'sources'
        """
        context_parts: List[str] = []
        sources: List[Dict[str, Any]] = []

        # Step 1: Vector search — semantic similarity
        vector_results = await self._semantic_search(question, top_k)
        if vector_results:
            context_parts.append(self._format_vector_results(vector_results))
            sources += [{"type": "vector", "id": r["document_id"]} for r in vector_results]

        # Step 2: Graph enrichment — live financial data
        if include_graph_context:
            graph_context = await self._graph_context(question)
            if graph_context:
                context_parts.append(graph_context)
                sources.append({"type": "graph", "id": "neo4j_live"})

        # Step 3: Episodic memory injection
        if include_memory and self.memory:
            memory_context = self.memory.get_context_for_ai()
            if memory_context:
                context_parts.append(memory_context)
                sources.append({"type": "memory", "id": "episodic"})

        # Step 4: LLM reasoning
        full_context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        answer = self.llm_fn(question, full_context)

        return {
            "answer": answer,
            "context_used": full_context,
            "sources": sources,
            "vector_hits": len(vector_results),
        }

    def query_sync(
        self,
        question: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Synchronous version of query() for use outside async contexts.
        Skips vector search (requires async), uses graph + memory only.

        Args:
            question: Natural language question
            top_k:    Ignored in sync mode (vector search is async)

        Returns:
            Dict with 'answer', 'context_used', 'sources'
        """
        context_parts: List[str] = []
        sources: List[Dict[str, Any]] = []

        # Always inject a compact financial health snapshot
        try:
            snapshot = self._financial_snapshot()
            if snapshot:
                context_parts.append(snapshot)
                sources.append({"type": "graph", "id": "snapshot"})
        except Exception:
            pass

        # Graph context — keyword-based deep enrichment
        try:
            graph_context = self._graph_context_sync(question)
            if graph_context:
                context_parts.append(graph_context)
                sources.append({"type": "graph", "id": "neo4j_live"})
        except Exception:
            pass

        # Episodic memory — always injected
        if self.memory:
            try:
                mem = self.memory.get_context_for_ai()
                if mem:
                    context_parts.append(mem)
                    sources.append({"type": "memory", "id": "episodic"})
            except Exception:
                pass

        # Decision fusion — always injected (top 5 ranked risks)
        if self.decision_fusion:
            try:
                fusion_ctx = self._decision_fusion_context()
                if fusion_ctx:
                    context_parts.append(fusion_ctx)
                    sources.append({"type": "intelligence", "id": "decision_fusion"})
            except Exception:
                pass

        # Weak signals — injected when relevant keywords detected
        q_lower = question.lower()
        if self.weak_signals and any(w in q_lower for w in ["signal", "risk", "stress", "weak", "alert", "concern", "worry"]):
            try:
                ws_ctx = self._weak_signals_context()
                if ws_ctx:
                    context_parts.append(ws_ctx)
                    sources.append({"type": "intelligence", "id": "weak_signals"})
            except Exception:
                pass

        # Recommendations — injected when relevant keywords detected
        if self.recommendations and any(w in q_lower for w in ["recommend", "suggest", "should", "action", "reduce", "optimize", "improve", "priority", "cost", "saving", "top"]):
            try:
                rec_ctx = self._recommendations_context()
                if rec_ctx:
                    context_parts.append(rec_ctx)
                    sources.append({"type": "intelligence", "id": "recommendations"})
            except Exception:
                pass

        full_context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        answer = self.llm_fn(question, full_context)

        return {
            "answer": answer,
            "context_used": full_context,
            "sources": sources,
            "vector_hits": 0,
        }

    # ============================================
    # Always-on Financial Health Snapshot
    # ============================================

    def _financial_snapshot(self) -> str:
        """Compact summary of key financial metrics — always injected into LLM context."""
        lines = ["FINANCIAL HEALTH SNAPSHOT (live data):"]
        try:
            budgets = self.graph.get_all_budgets_raw()
            unique_depts = set(b.get("department") for b in budgets if b.get("department"))
            over = [b for b in budgets if (b.get("actual") or 0) > (b.get("budget") or 0)]
            over_depts = set(b.get("department") for b in over if b.get("department"))
            total_variance = sum((b.get("actual", 0) or 0) - (b.get("budget", 0) or 0) for b in over)
            lines.append(
                f"  Budgets: {len(unique_depts)} departments, "
                f"{len(over_depts)} with at least one year over budget "
                f"(total overrun across all years: {total_variance:+,.0f} EUR)"
            )
            # Surface persistent overspenders explicitly for the LLM
            dept_years_over: Dict[str, int] = {}
            for b in over:
                d = b.get("department", "")
                dept_years_over[d] = dept_years_over.get(d, 0) + 1
            persistent = [(d, y) for d, y in dept_years_over.items() if y >= 2]
            if persistent:
                persistent.sort(key=lambda x: -x[1])
                lines.append(
                    "  Departments overspending for 2+ years: "
                    + ", ".join(f"{d} ({y} yrs)" for d, y in persistent)
                )
        except Exception:
            pass
        try:
            invoices = self.graph.get_all_invoices_raw()
            overdue = [i for i in invoices if (i.get("days_overdue") or 0) > 0]
            overdue_value = sum(i.get("amount", 0) or 0 for i in overdue)
            lines.append(f"  Invoices: {len(overdue)} overdue ({overdue_value:,.0f} EUR outstanding)")
        except Exception:
            pass
        try:
            contracts = self.graph.get_all_contracts_raw()
            expiring_90 = [c for c in contracts if 0 < (c.get("days_until_expiry") or 999) <= 90]
            lines.append(f"  Contracts: {len(contracts)} total, {len(expiring_90)} expiring within 90 days")
        except Exception:
            pass
        return "\n".join(lines) if len(lines) > 1 else ""

    def _decision_fusion_context(self) -> str:
        """Top 5 ranked decisions from decision fusion engine."""
        decisions = self.decision_fusion.get_ranked_decisions(limit=5)
        if not decisions:
            return ""
        lines = ["DECISION FUSION — TOP FINANCIAL RISKS (ranked by priority score):"]
        for d in decisions:
            lines.append(
                f"  [{d.get('severity','').upper()}] {d.get('title','?')} "
                f"(score: {d.get('priority_score', 0):.1f}, "
                f"impact: {d.get('financial_impact_eur', 0):,.0f} EUR) "
                f"— {d.get('recommended_action','')}"
            )
        return "\n".join(lines)

    def _weak_signals_context(self) -> str:
        """Active weak signal clusters."""
        signals = self.weak_signals.detect_signals()
        if not signals:
            return ""
        lines = ["WEAK SIGNAL RADAR — ACTIVE STRESS CLUSTERS:"]
        for s in signals[:5]:
            lines.append(
                f"  Score {s.get('score', 0):.1f}: {', '.join(s.get('signals', []))}"
            )
        return "\n".join(lines)

    def _recommendations_context(self) -> str:
        """Top 5 recommendations by priority score."""
        recs = self.recommendations.generate_recommendations()
        if not recs:
            return ""
        lines = ["TOP RECOMMENDATIONS (by priority score):"]
        for r in recs[:5]:
            lines.append(
                f"  [{r.get('category','?')}] {r.get('title','?')} "
                f"(priority: {r.get('priority_score', 0):.0f}/100, "
                f"impact: {r.get('expected_impact_eur', 0):,.0f} EUR)"
            )
        return "\n".join(lines)

    # ============================================
    # Step 1: Semantic Vector Search
    # ============================================

    async def _semantic_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Retrieve semantically similar documents from VectorStore."""
        try:
            results = await self.vectorstore.search(query=query, limit=top_k)
            return results if results else []
        except Exception:
            return []

    @staticmethod
    def _format_vector_results(results: List[Dict[str, Any]]) -> str:
        """Format vector search results as context text."""
        lines = ["RELEVANT DOCUMENTS (semantic search):"]
        for r in results:
            lines.append(
                f"  [{r.get('document_type', 'doc').upper()}] "
                f"{r.get('document_id', '?')} "
                f"(score: {r.get('score', 0):.2f}): "
                f"{str(r.get('content', ''))[:200]}"
            )
        return "\n".join(lines)

    # ============================================
    # Step 2: Graph Context Enrichment
    # ============================================

    async def _graph_context(self, question: str) -> str:
        """Build financial context from live Neo4j data."""
        return self._graph_context_sync(question)

    def _graph_context_sync(self, question: str) -> str:
        """Synchronous graph context builder."""
        parts = []
        q_lower = question.lower()

        # Budget context
        if any(w in q_lower for w in ["budget", "spend", "dépense", "overspend", "variance", "department", "performance", "summarize", "summary"]):
            try:
                budgets = self.graph.get_all_budgets_raw()
                if budgets:
                    unique_depts = set(b.get("department") for b in budgets if b.get("department"))
                    over = [b for b in budgets if (b.get("actual") or 0) > (b.get("budget") or 0)]
                    lines = [f"LIVE BUDGET DATA ({len(unique_depts)} departments, {len(budgets)} budget rows across all years):"]
                    # Aggregate by department
                    dept_totals: Dict[str, Dict] = {}
                    for b in budgets:
                        d = b.get("department", "?")
                        if d not in dept_totals:
                            dept_totals[d] = {"budget": 0, "actual": 0, "years_over": 0}
                        dept_totals[d]["budget"] += b.get("budget", 0) or 0
                        dept_totals[d]["actual"] += b.get("actual", 0) or 0
                        if (b.get("actual") or 0) > (b.get("budget") or 0):
                            dept_totals[d]["years_over"] += 1
                    for dept, totals in sorted(dept_totals.items()):
                        variance = totals["actual"] - totals["budget"]
                        lines.append(
                            f"  {dept}: total budget={totals['budget']:,.0f}, "
                            f"actual={totals['actual']:,.0f}, "
                            f"variance={variance:+,.0f} "
                            f"({totals['years_over']} year(s) over budget)"
                        )
                    parts.append("\n".join(lines))
            except Exception:
                pass

        # Invoice context
        if any(w in q_lower for w in ["invoice", "facture", "overdue", "payment", "paiement"]):
            try:
                invoices = self.graph.get_all_invoices_raw()
                overdue = [i for i in invoices if (i.get("days_overdue") or 0) > 0]
                if overdue:
                    total = sum(i.get("amount", 0) or 0 for i in overdue)
                    lines = [f"OVERDUE INVOICES ({len(overdue)} total, {total:,.0f} EUR outstanding):"]
                    for inv in overdue[:5]:
                        lines.append(
                            f"  {inv.get('vendor','?')}: "
                            f"{inv.get('amount',0):,.0f} EUR, "
                            f"{inv.get('days_overdue',0)} days overdue"
                        )
                    parts.append("\n".join(lines))
            except Exception:
                pass

        # Vendor / quarterly aggregation context
        if any(w in q_lower for w in ["vendor", "q1", "q2", "q3", "q4", "quarter", "biggest", "largest", "top vendor", "supplier"]):
            try:
                # Detect which quarter is being asked about
                quarter_map = {"q1": (1, 3), "q2": (4, 6), "q3": (7, 9), "q4": (10, 12),
                               "first quarter": (1, 3), "second quarter": (4, 6),
                               "third quarter": (7, 9), "fourth quarter": (10, 12)}
                month_start, month_end = 1, 12  # default: full year
                quarter_label = "full year"
                for kw, (ms, me) in quarter_map.items():
                    if kw in q_lower:
                        month_start, month_end = ms, me
                        quarter_label = kw.upper()
                        break

                query = """
                MATCH (i:Invoice)
                WHERE i.date IS NOT NULL
                  AND i.date.month >= $month_start
                  AND i.date.month <= $month_end
                RETURN i.vendor AS vendor,
                       count(i) AS invoice_count,
                       sum(i.amount) AS total_amount
                ORDER BY total_amount DESC
                LIMIT 10
                """
                with self.graph.driver.session() as session:
                    result = session.run(query, month_start=month_start, month_end=month_end)
                    rows = [dict(r) for r in result]

                if rows:
                    lines = [f"VENDOR TOTALS ({quarter_label}, by invoice amount):"]
                    for r in rows:
                        lines.append(
                            f"  {r.get('vendor','?')}: "
                            f"{r.get('total_amount', 0):,.0f} EUR "
                            f"({r.get('invoice_count', 0)} invoices)"
                        )
                    parts.append("\n".join(lines))
            except Exception:
                pass

        # Contract context
        if any(w in q_lower for w in ["contract", "contrat", "expir", "vendor", "fournisseur"]):
            try:
                contracts = self.graph.get_all_contracts_raw()
                active = [c for c in contracts if (c.get("days_until_expiry") or 9999) > 0]
                expiring_soon = [c for c in active if (c.get("days_until_expiry") or 9999) <= 365]
                total_value = sum(c.get("annual_value", 0) or 0 for c in active)
                lines = [
                    f"CONTRACTS ({len(active)} active, total annual value: {total_value:,.0f} EUR):"
                ]
                if expiring_soon:
                    lines.append(f"  Expiring within 365 days ({len(expiring_soon)} contracts):")
                    for c in sorted(expiring_soon, key=lambda x: x.get("days_until_expiry", 999))[:8]:
                        lines.append(
                            f"    {c.get('vendor','?')}: "
                            f"{c.get('annual_value',0):,.0f} EUR/yr, "
                            f"expires in {c.get('days_until_expiry','?')} days"
                        )
                else:
                    lines.append("  No contracts expiring within 365 days.")
                parts.append("\n".join(lines))
            except Exception:
                pass

        return "\n\n".join(parts)

    # ============================================
    # Graph Relationship Traversal
    # ============================================

    def get_contract_with_invoices(self, contract_id: str) -> Dict[str, Any]:
        """
        Graph traversal: fetch a contract and all its generated invoices.
        Demonstrates the Contract → Invoice relationship in RAGraph.

        Args:
            contract_id: Contract node ID

        Returns:
            Dict with contract data and list of invoice nodes
        """
        query = """
        MATCH (c:Contract {id: $contract_id})
        OPTIONAL MATCH (c)-[:GENERATES]->(i:Invoice)
        RETURN c.id AS contract_id, c.vendor AS vendor,
               c.annual_value AS annual_value,
               collect({
                   id: i.id,
                   amount: i.amount,
                   status: i.status,
                   days_overdue: CASE WHEN i.due_date IS NOT NULL
                                 THEN duration.inDays(i.due_date, date()).days
                                 ELSE 0 END
               }) AS invoices
        """
        with self.graph.driver.session() as session:
            result = session.run(query, contract_id=contract_id)
            record = result.single()
            return dict(record) if record else {}

    def get_vendor_financial_summary(self, vendor: str) -> Dict[str, Any]:
        """
        Graph traversal: aggregate all financial data for a vendor.
        Crosses Contract, Invoice, and EpisodicMemory nodes.

        Args:
            vendor: Vendor name

        Returns:
            Aggregated vendor financial summary
        """
        query = """
        OPTIONAL MATCH (c:Contract {vendor: $vendor})
        OPTIONAL MATCH (i:Invoice {vendor: $vendor})
        OPTIONAL MATCH (m:EpisodicMemory {subject: $vendor})
        RETURN count(DISTINCT c) AS contract_count,
               sum(DISTINCT c.annual_value) AS total_contract_value,
               count(DISTINCT i) AS invoice_count,
               sum(DISTINCT i.amount) AS total_invoiced,
               collect(DISTINCT m.description) AS patterns
        """
        with self.graph.driver.session() as session:
            result = session.run(query, vendor=vendor)
            record = result.single()
            return dict(record) if record else {}
