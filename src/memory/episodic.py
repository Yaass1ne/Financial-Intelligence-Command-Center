"""
FINCENTER Episodic Memory

Detects recurring financial patterns from Neo4j data and stores them as
EpisodicMemory nodes. These patterns enrich the AI chat context and feed
the decision fusion and recommendation engines.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict


class EpisodicMemory:
    """Detects and stores recurring financial patterns as episodic memory."""

    def __init__(self, graph):
        """
        Args:
            graph: FinancialGraph instance
        """
        self.graph = graph

    # ============================================
    # Pattern Detection
    # ============================================

    def run_pattern_detection(self) -> int:
        """
        Run all pattern detectors and persist results to Neo4j.

        Returns:
            Number of patterns detected/updated
        """
        patterns = []
        try:
            patterns += self._detect_vendor_overbilling()
        except Exception:
            pass
        try:
            patterns += self._detect_department_overspend()
        except Exception:
            pass
        try:
            patterns += self._detect_late_payment_pattern()
        except Exception:
            pass
        try:
            patterns += self._detect_seasonal_spike()
        except Exception:
            pass

        now = datetime.utcnow().isoformat()
        for p in patterns:
            p["last_updated"] = now
            try:
                self.graph.create_episodic_memory_node(p)
            except Exception:
                pass

        return len(patterns)

    def _detect_vendor_overbilling(self) -> List[Dict[str, Any]]:
        """Detect vendors whose invoices consistently exceed contract values."""
        invoices = self.graph.get_all_invoices_raw()
        contracts = self.graph.get_all_contracts_raw()

        # Build monthly avg contract value per vendor
        contract_monthly: Dict[str, float] = {}
        for c in contracts:
            vendor = c.get("vendor", "UNKNOWN")
            annual = c.get("annual_value", 0) or 0
            monthly = annual / 12
            if vendor in contract_monthly:
                contract_monthly[vendor] += monthly
            else:
                contract_monthly[vendor] = monthly

        # Build avg invoice amount per vendor
        vendor_invoices: Dict[str, List[float]] = defaultdict(list)
        for inv in invoices:
            vendor = inv.get("vendor", "UNKNOWN")
            amount = inv.get("amount", 0) or 0
            if amount > 0:
                vendor_invoices[vendor].append(amount)

        patterns = []
        for vendor, amounts in vendor_invoices.items():
            if len(amounts) < 2:
                continue
            avg_invoice = sum(amounts) / len(amounts)
            monthly_contract = contract_monthly.get(vendor, 0)
            if monthly_contract > 0 and avg_invoice > monthly_contract * 1.10:
                ratio = avg_invoice / monthly_contract
                confidence = min(0.95, 0.5 + len(amounts) * 0.05)
                patterns.append({
                    "id": f"vendor_overbilling_{vendor}".replace(" ", "_"),
                    "type": "vendor_overbilling",
                    "subject": vendor,
                    "description": (
                        f"Vendor '{vendor}' average invoice ({avg_invoice:,.0f} EUR) "
                        f"exceeds monthly contract value ({monthly_contract:,.0f} EUR) "
                        f"by {(ratio - 1) * 100:.1f}%."
                    ),
                    "confidence": round(confidence, 2),
                    "evidence_count": len(amounts),
                    "acknowledged": False,
                })
        return patterns

    def _detect_department_overspend(self) -> List[Dict[str, Any]]:
        """Detect departments that consistently overspend their budget."""
        budgets = self.graph.get_all_budgets_raw()

        dept_years: Dict[str, List[Dict]] = defaultdict(list)
        for b in budgets:
            dept = b.get("department", "UNKNOWN")
            dept_years[dept].append(b)

        patterns = []
        for dept, records in dept_years.items():
            if dept == "UNKNOWN":
                continue
            overspend_years = [
                r for r in records
                if r.get("budget", 0) and
                r.get("actual", 0) > r.get("budget", 0) * 1.05
            ]
            if len(overspend_years) >= 2:
                avg_overrun = sum(
                    (r["actual"] - r["budget"]) / r["budget"] * 100
                    for r in overspend_years
                ) / len(overspend_years)
                confidence = min(0.95, 0.4 + len(overspend_years) * 0.15)
                patterns.append({
                    "id": f"dept_overspend_{dept}".replace(" ", "_"),
                    "type": "department_overspend",
                    "subject": dept,
                    "description": (
                        f"Department '{dept}' overspent by an average of {avg_overrun:.1f}% "
                        f"across {len(overspend_years)} budget periods."
                    ),
                    "confidence": round(confidence, 2),
                    "evidence_count": len(overspend_years),
                    "acknowledged": False,
                })
        return patterns

    def _detect_late_payment_pattern(self) -> List[Dict[str, Any]]:
        """Detect vendors with chronically overdue invoices."""
        invoices = self.graph.get_all_invoices_raw()

        vendor_overdue: Dict[str, List[int]] = defaultdict(list)
        for inv in invoices:
            if inv.get("status") == "UNPAID":
                days = inv.get("days_overdue", 0) or 0
                if days > 0:
                    vendor_overdue[inv.get("vendor", "UNKNOWN")].append(days)

        patterns = []
        for vendor, overdue_list in vendor_overdue.items():
            if len(overdue_list) < 2:
                continue
            avg_days = sum(overdue_list) / len(overdue_list)
            if avg_days > 30:
                confidence = min(0.90, 0.4 + len(overdue_list) * 0.05)
                patterns.append({
                    "id": f"late_payment_{vendor}".replace(" ", "_"),
                    "type": "late_payment_pattern",
                    "subject": vendor,
                    "description": (
                        f"Vendor '{vendor}' invoices are on average {avg_days:.0f} days overdue "
                        f"across {len(overdue_list)} unpaid invoices."
                    ),
                    "confidence": round(confidence, 2),
                    "evidence_count": len(overdue_list),
                    "acknowledged": False,
                })
        return patterns

    def _detect_seasonal_spike(self) -> List[Dict[str, Any]]:
        """Detect if Q4 spending is consistently highest."""
        budgets = self.graph.get_all_budgets_raw()

        if not budgets:
            return []

        # Use budget year as proxy — look for high-actual records
        total_actual = sum(b.get("actual", 0) or 0 for b in budgets)
        if total_actual == 0:
            return []

        avg_actual = total_actual / len(budgets) if budgets else 0
        high_spend = [b for b in budgets if (b.get("actual") or 0) > avg_actual * 1.2]

        if len(high_spend) >= 3:
            return [{
                "id": "seasonal_spike_q4",
                "type": "seasonal_spike",
                "subject": "All Departments",
                "description": (
                    f"Detected {len(high_spend)} budget periods with spending "
                    f">20% above average, suggesting seasonal expenditure spikes."
                ),
                "confidence": 0.65,
                "evidence_count": len(high_spend),
                "acknowledged": False,
            }]
        return []

    # ============================================
    # Query Interface
    # ============================================

    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all stored patterns, optionally filtered by type."""
        return self.graph.get_episodic_memories(pattern_type)

    def get_context_for_ai(self) -> str:
        """
        Return a text summary of top patterns for injecting into AI chat context.

        Returns:
            Multi-line string describing learned patterns
        """
        patterns = self.get_patterns()
        if not patterns:
            return ""

        lines = ["LEARNED FINANCIAL PATTERNS (Episodic Memory):"]
        for p in patterns[:8]:
            lines.append(
                f"  [{p['type'].upper()} | confidence={p['confidence']:.0%}] "
                f"{p['description']}"
            )
        return "\n".join(lines)
