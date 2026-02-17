"""
FINCENTER Recommendation Engine

Builds a scored recommendation feed from all intelligence sources.
Each recommendation has a priority_score (0–100) computed from
financial impact, urgency, and confidence.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any


class RecommendationEngine:
    """Generates and scores actionable financial recommendations."""

    def __init__(self, graph):
        """
        Args:
            graph: FinancialGraph instance
        """
        self.graph = graph

    # ============================================
    # Public Interface
    # ============================================

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate all recommendations, persist to Neo4j, and return them.

        Returns:
            List of recommendation dicts sorted by priority_score desc
        """
        recs: List[Dict[str, Any]] = []
        recs += self._cost_reduction_recs()
        recs += self._risk_mitigation_recs()
        recs += self._revenue_optimization_recs()

        now = datetime.utcnow().isoformat()
        for rec in recs:
            rec["created_at"] = now
            rec["acknowledged"] = False
            try:
                self.graph.create_recommendation_node(rec)
            except Exception:
                pass

        recs.sort(key=lambda r: r["priority_score"], reverse=True)
        return recs

    def get_recommendations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch stored recommendations from Neo4j."""
        return self.graph.get_recommendations(limit=limit)

    def acknowledge(self, rec_id: str):
        """Mark a recommendation as seen/actioned."""
        self.graph.acknowledge_recommendation(rec_id)

    # ============================================
    # Recommendation Generators
    # ============================================

    def _cost_reduction_recs(self) -> List[Dict[str, Any]]:
        recs = []
        try:
            budgets = self.graph.get_all_budgets_raw()
            for b in budgets:
                budget_amt = b.get("budget", 0) or 0
                actual_amt = b.get("actual", 0) or 0
                if budget_amt <= 0:
                    continue
                overrun = actual_amt - budget_amt
                overrun_pct = overrun / budget_amt * 100

                if overrun_pct > 10:
                    impact_eur = abs(overrun)
                    financial = min(1.0, impact_eur / 500_000)
                    urgency = min(1.0, overrun_pct / 50)
                    confidence = 0.85
                    score = self._priority_score(financial, urgency, confidence)

                    recs.append({
                        "id": f"rec_cost_{b.get('department', 'dept')}_{uuid.uuid4().hex[:6]}",
                        "category": "cost_reduction",
                        "title": f"Reduce spend in {b.get('department', '?')} department",
                        "description": (
                            f"Department is {overrun_pct:.1f}% over budget "
                            f"({overrun:,.0f} EUR). Implement spend controls and "
                            f"freeze discretionary purchases."
                        ),
                        "priority_score": round(score, 1),
                        "expected_impact_eur": round(impact_eur * 0.5, 0),
                        "confidence": confidence,
                        "supporting_evidence": [
                            f"Budget: {budget_amt:,.0f} EUR",
                            f"Actual: {actual_amt:,.0f} EUR",
                            f"Overrun: {overrun_pct:.1f}%",
                        ],
                    })
        except Exception:
            pass

        # Vendor overbilling → cost reduction
        try:
            patterns = self.graph.get_episodic_memories("vendor_overbilling")
            for p in patterns:
                if p.get("confidence", 0) < 0.6:
                    continue
                score = self._priority_score(0.5, 0.6, p.get("confidence", 0.7))
                recs.append({
                    "id": f"rec_overbilling_{p['subject'].replace(' ', '_')}_{uuid.uuid4().hex[:6]}",
                    "category": "cost_reduction",
                    "title": f"Renegotiate contract with {p.get('subject', '?')}",
                    "description": p.get("description", ""),
                    "priority_score": round(score, 1),
                    "expected_impact_eur": 0,
                    "confidence": p.get("confidence", 0.7),
                    "supporting_evidence": [p.get("description", "")],
                })
        except Exception:
            pass

        return recs

    def _risk_mitigation_recs(self) -> List[Dict[str, Any]]:
        recs = []

        # Expiring contracts
        try:
            contracts = self.graph.get_all_contracts_raw()
            for c in contracts:
                days_left = c.get("days_until_expiry", 999) or 999
                if not (0 < days_left <= 90):
                    continue
                annual_value = c.get("annual_value", 0) or 0
                financial = min(1.0, annual_value / 500_000)
                urgency = min(1.0, (90 - days_left) / 90)
                confidence = 0.95
                score = self._priority_score(financial, urgency, confidence)

                recs.append({
                    "id": f"rec_contract_{c.get('contract_id', 'ctr')}_{uuid.uuid4().hex[:6]}",
                    "category": "risk_mitigation",
                    "title": f"Renew contract: {c.get('vendor', '?')}",
                    "description": (
                        f"Contract with '{c.get('vendor', '?')}' (value: {annual_value:,.0f} EUR/yr) "
                        f"expires in {days_left} days. Failure to renew risks service disruption."
                    ),
                    "priority_score": round(score, 1),
                    "expected_impact_eur": round(annual_value, 0),
                    "confidence": confidence,
                    "supporting_evidence": [
                        f"Days until expiry: {days_left}",
                        f"Annual value: {annual_value:,.0f} EUR",
                    ],
                })
        except Exception:
            pass

        # Overdue invoices
        try:
            invoices = self.graph.get_all_invoices_raw()
            for inv in invoices:
                days = inv.get("days_overdue", 0) or 0
                if days < 30:
                    continue
                amount = inv.get("amount", 0) or 0
                financial = min(1.0, amount / 100_000)
                urgency = min(1.0, days / 120)
                confidence = 0.90
                score = self._priority_score(financial, urgency, confidence)

                recs.append({
                    "id": f"rec_invoice_{inv.get('invoice_id', 'inv')}_{uuid.uuid4().hex[:6]}",
                    "category": "risk_mitigation",
                    "title": f"Resolve overdue invoice: {inv.get('vendor', '?')}",
                    "description": (
                        f"Invoice of {amount:,.0f} EUR from '{inv.get('vendor', '?')}' "
                        f"is {days} days overdue. Escalate to prevent vendor relationship damage."
                    ),
                    "priority_score": round(score, 1),
                    "expected_impact_eur": round(amount, 0),
                    "confidence": confidence,
                    "supporting_evidence": [
                        f"Days overdue: {days}",
                        f"Amount: {amount:,.0f} EUR",
                    ],
                })
        except Exception:
            pass

        # Weak signals
        try:
            signals = self.graph.get_weak_signals(only_active=True)
            if signals:
                max_score = max(s.get("score", 0) for s in signals)
                score = self._priority_score(min(max_score / 10, 1.0), 0.7, 0.75)
                recs.append({
                    "id": f"rec_weaksignal_{uuid.uuid4().hex[:8]}",
                    "category": "risk_mitigation",
                    "title": "Financial stress cluster requires holistic review",
                    "description": (
                        f"{len(signals)} correlated weak signal cluster(s) detected. "
                        "Combined score indicates elevated financial risk."
                    ),
                    "priority_score": round(score, 1),
                    "expected_impact_eur": 0,
                    "confidence": 0.70,
                    "supporting_evidence": [
                        f"Active clusters: {len(signals)}",
                        f"Max stress score: {max_score}",
                    ],
                })
        except Exception:
            pass

        return recs

    def _revenue_optimization_recs(self) -> List[Dict[str, Any]]:
        recs = []
        try:
            budgets = self.graph.get_all_budgets_raw()
            for b in budgets:
                budget_amt = b.get("budget", 0) or 0
                actual_amt = b.get("actual", 0) or 0
                if budget_amt <= 0:
                    continue
                underrun_pct = (budget_amt - actual_amt) / budget_amt * 100
                if underrun_pct >= 15:
                    savings = budget_amt - actual_amt
                    financial = min(1.0, savings / 300_000)
                    score = self._priority_score(financial, 0.4, 0.80)
                    recs.append({
                        "id": f"rec_reallocate_{b.get('department', 'dept')}_{uuid.uuid4().hex[:6]}",
                        "category": "revenue_optimization",
                        "title": f"Reallocate surplus from {b.get('department', '?')}",
                        "description": (
                            f"Department '{b.get('department', '?')}' is {underrun_pct:.1f}% under budget "
                            f"({savings:,.0f} EUR available). Reallocate to high-growth areas."
                        ),
                        "priority_score": round(score, 1),
                        "expected_impact_eur": round(savings * 0.8, 0),
                        "confidence": 0.80,
                        "supporting_evidence": [
                            f"Surplus: {savings:,.0f} EUR",
                            f"Under-budget: {underrun_pct:.1f}%",
                        ],
                    })
        except Exception:
            pass
        return recs

    # ============================================
    # Scoring Formula
    # ============================================

    @staticmethod
    def _priority_score(financial_impact: float, urgency: float, confidence: float) -> float:
        """
        priority_score = (financial_impact * 0.4) + (urgency * 0.4) + (confidence * 0.2)
        Scaled to 0–100.
        """
        raw = (financial_impact * 0.4) + (urgency * 0.4) + (confidence * 0.2)
        return min(100.0, raw * 100)
