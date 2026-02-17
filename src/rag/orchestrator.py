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

    def __init__(self, graph, vectorstore, llm_fn, memory=None):
        """
        Args:
            graph:       FinancialGraph instance (Neo4j)
            vectorstore: VectorStore instance (FAISS embeddings)
            llm_fn:      Callable(question, context) -> str  (e.g. groq_client.answer_question)
            memory:      EpisodicMemory instance (optional, for pattern injection)
        """
        self.graph = graph
        self.vectorstore = vectorstore
        self.llm_fn = llm_fn
        self.memory = memory

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

        # Graph context (synchronous Neo4j queries)
        try:
            graph_context = self._graph_context_sync(question)
            if graph_context:
                context_parts.append(graph_context)
                sources.append({"type": "graph", "id": "neo4j_live"})
        except Exception:
            pass

        # Episodic memory
        if self.memory:
            try:
                mem = self.memory.get_context_for_ai()
                if mem:
                    context_parts.append(mem)
                    sources.append({"type": "memory", "id": "episodic"})
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
        if any(w in q_lower for w in ["budget", "spend", "dépense", "overspend", "variance"]):
            try:
                budgets = self.graph.get_all_budgets_raw()
                if budgets:
                    over = [b for b in budgets if (b.get("actual") or 0) > (b.get("budget") or 0)]
                    lines = [f"LIVE BUDGET DATA ({len(budgets)} departments):"]
                    for b in budgets[:8]:
                        variance = (b.get("actual") or 0) - (b.get("budget") or 0)
                        lines.append(
                            f"  {b.get('department','?')}: "
                            f"budget={b.get('budget',0):,.0f}, "
                            f"actual={b.get('actual',0):,.0f}, "
                            f"variance={variance:+,.0f}"
                        )
                    if over:
                        lines.append(f"  → {len(over)} departments over budget")
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

        # Contract context
        if any(w in q_lower for w in ["contract", "contrat", "expir", "vendor", "fournisseur"]):
            try:
                contracts = self.graph.get_all_contracts_raw()
                expiring = [c for c in contracts if 0 < (c.get("days_until_expiry") or 999) <= 90]
                if expiring:
                    lines = [f"EXPIRING CONTRACTS (<90 days, {len(expiring)} total):"]
                    for c in expiring[:5]:
                        lines.append(
                            f"  {c.get('vendor','?')}: "
                            f"{c.get('annual_value',0):,.0f} EUR/yr, "
                            f"expires in {c.get('days_until_expiry','?')} days"
                        )
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
