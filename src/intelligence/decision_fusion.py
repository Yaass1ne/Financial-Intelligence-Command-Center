"""
FINCENTER Decision Fusion

Aggregates signals from all intelligence modules, ranks tactical decisions
by priority score, and returns actionable recommendations.
"""

from typing import List, Dict, Any


SEVERITY_WEIGHTS = {
    "critical": 3,
    "warning": 2,
    "info": 1,
}


class DecisionFusion:
    """Aggregates and ranks tactical decisions from all intelligence sources."""

    def __init__(self, graph):
        """
        Args:
            graph: FinancialGraph instance
        """
        self.graph = graph

    def get_ranked_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Pull signals from all sources and return top ranked decisions.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of ranked decision dicts sorted by priority_score desc
        """
        # Collect from each source, cap per-source to ensure diversity
        PER_SOURCE_CAP = 5
        all_decisions: List[Dict[str, Any]] = []

        for source_fn in [
            self._invoice_decisions,
            self._budget_decisions,
            self._contract_decisions,
            self._episodic_decisions,
            self._weak_signal_decisions,
        ]:
            items = source_fn()
            items.sort(key=lambda d: d["priority_score"], reverse=True)
            all_decisions += items[:PER_SOURCE_CAP]

        # Global sort and return top N
        all_decisions.sort(key=lambda d: d["priority_score"], reverse=True)
        return all_decisions[:limit]

    # ============================================
    # Signal Sources
    # ============================================

    def _budget_decisions(self) -> List[Dict[str, Any]]:
        decisions = []
        try:
            budgets = self.graph.get_all_budgets_raw()
            for b in budgets:
                budget_amt = b.get("budget", 0) or 0
                actual_amt = b.get("actual", 0) or 0
                if budget_amt <= 0:
                    continue
                overrun = actual_amt - budget_amt
                overrun_pct = overrun / budget_amt * 100 if budget_amt else 0

                if overrun_pct > 20:
                    severity = "critical"
                elif overrun_pct > 5:
                    severity = "warning"
                else:
                    continue

                financial_impact = min(1.0, abs(overrun) / 500000)
                urgency = 1.0
                score = self._score(severity, financial_impact, urgency)

                decisions.append({
                    "id": f"budget_overrun_{b.get('department', 'dept')}",
                    "source": "Budget",
                    "severity": severity,
                    "title": f"Budget overrun: {b.get('department', '?')}",
                    "description": (
                        f"Department '{b.get('department', '?')}' actual spend "
                        f"({actual_amt:,.0f} EUR) exceeds budget ({budget_amt:,.0f} EUR) "
                        f"by {overrun_pct:.1f}%."
                    ),
                    "recommended_action": (
                        "Review discretionary spending and freeze non-critical purchases. "
                        "Request variance explanation from department head."
                    ),
                    "financial_impact_eur": round(abs(overrun), 2),
                    "priority_score": round(score, 1),
                })
        except Exception:
            pass
        return decisions

    def _invoice_decisions(self) -> List[Dict[str, Any]]:
        decisions = []
        try:
            invoices = self.graph.get_all_invoices_raw()
            for inv in invoices:
                days = inv.get("days_overdue", 0) or 0
                if days <= 0:
                    continue
                if days >= 60:
                    severity = "critical"
                elif days >= 30:
                    severity = "warning"
                else:
                    continue

                amount = inv.get("amount", 0) or 0
                financial_impact = min(1.0, amount / 100000)
                urgency = 1 + min(days / 100, 1.0)
                score = self._score(severity, financial_impact, urgency)

                decisions.append({
                    "id": f"overdue_invoice_{inv.get('invoice_id', 'inv')}",
                    "source": "Invoice",
                    "severity": severity,
                    "title": f"Overdue invoice: {inv.get('vendor', '?')}",
                    "description": (
                        f"Invoice from '{inv.get('vendor', '?')}' for {amount:,.0f} EUR "
                        f"is {days} days overdue."
                    ),
                    "recommended_action": (
                        "Contact vendor to resolve payment. "
                        "Escalate to finance director if > 90 days."
                    ),
                    "financial_impact_eur": round(amount, 2),
                    "priority_score": round(score, 1),
                })
        except Exception:
            pass
        return decisions

    def _contract_decisions(self) -> List[Dict[str, Any]]:
        decisions = []
        try:
            contracts = self.graph.get_all_contracts_raw()
            for c in contracts:
                days_left = c.get("days_until_expiry", 999) or 999
                if days_left > 90 or days_left < 0:
                    continue

                if days_left <= 30:
                    severity = "critical"
                elif days_left <= 60:
                    severity = "warning"
                else:
                    severity = "info"

                annual_value = c.get("annual_value", 0) or 0
                financial_impact = min(1.0, annual_value / 500000)
                urgency = 1 + (90 - days_left) / 100
                score = self._score(severity, financial_impact, urgency)

                decisions.append({
                    "id": f"expiring_contract_{c.get('contract_id', 'ctr')}",
                    "source": "Contract",
                    "severity": severity,
                    "title": f"Contract expiring: {c.get('vendor', '?')}",
                    "description": (
                        f"Contract with '{c.get('vendor', '?')}' (value: {annual_value:,.0f} EUR/yr) "
                        f"expires in {days_left} days."
                    ),
                    "recommended_action": (
                        "Initiate renewal negotiations immediately. "
                        "Benchmark against market rates before signing."
                    ),
                    "financial_impact_eur": round(annual_value, 2),
                    "priority_score": round(score, 1),
                })
        except Exception:
            pass
        return decisions

    def _episodic_decisions(self) -> List[Dict[str, Any]]:
        decisions = []
        try:
            patterns = self.graph.get_episodic_memories()
            for p in patterns:
                if p.get("confidence", 0) < 0.6:
                    continue
                severity = "warning" if p.get("confidence", 0) >= 0.75 else "info"
                score = self._score(severity, p.get("confidence", 0.5), 1.0)
                decisions.append({
                    "id": f"episodic_{p['id']}",
                    "source": "Episodic Memory",
                    "severity": severity,
                    "title": f"Recurring pattern: {p.get('type', '?')} — {p.get('subject', '?')}",
                    "description": p.get("description", ""),
                    "recommended_action": "Review historical trend and take preventive action.",
                    "financial_impact_eur": 0,
                    "priority_score": round(score, 1),
                })
        except Exception:
            pass
        return decisions

    def _weak_signal_decisions(self) -> List[Dict[str, Any]]:
        decisions = []
        try:
            signals = self.graph.get_weak_signals(only_active=True)
            for ws in signals:
                score_val = ws.get("score", 0) or 0
                if score_val < 4:
                    continue
                severity = "critical" if score_val >= 7 else "warning"
                priority = self._score(severity, min(score_val / 10, 1.0), 1.2)
                decisions.append({
                    "id": f"weak_signal_{ws['id']}",
                    "source": "Weak Signal",
                    "severity": severity,
                    "title": f"Financial stress cluster detected (score: {score_val})",
                    "description": (
                        "Multiple correlated weak signals indicate hidden financial stress. "
                        "Individual signals are below alert threshold but combined score is high."
                    ),
                    "recommended_action": (
                        "Conduct holistic financial review. "
                        "Cross-check all flagged entities with management."
                    ),
                    "financial_impact_eur": 0,
                    "priority_score": round(priority, 1),
                })
        except Exception:
            pass
        return decisions

    # ============================================
    # Scoring Formula
    # ============================================

    def _score(self, severity: str, financial_impact: float, urgency: float) -> float:
        """
        priority = severity_weight * financial_impact * urgency_factor

        Args:
            severity: 'critical', 'warning', or 'info'
            financial_impact: normalized 0–1
            urgency: multiplier >= 1.0

        Returns:
            Priority score (higher = more urgent)
        """
        sw = SEVERITY_WEIGHTS.get(severity, 1)
        return sw * max(0.1, financial_impact) * urgency * 10
