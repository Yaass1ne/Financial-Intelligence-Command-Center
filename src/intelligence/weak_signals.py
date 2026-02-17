"""
FINCENTER Weak Signal Detector

Correlates below-threshold signals from multiple financial sources to detect
hidden financial stress that would not trigger individual alerts.
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Any


# Signal weights
SIGNAL_WEIGHTS = {
    "budget_slightly_over": 1,       # 5-15% over budget
    "invoice_moderately_overdue": 1,  # 15-30 days overdue
    "contract_expiring_medium": 1,    # 61-90 days until expiry
    "vendor_slight_overbilling": 1,   # < 10% above contract value
    "new_episodic_pattern": 2,        # new pattern detected this week
}

STRESS_THRESHOLD = 4  # combined weight >= 4 → alert raised


class WeakSignalDetector:
    """Detects hidden financial stress by correlating weak signals."""

    def __init__(self, graph):
        """
        Args:
            graph: FinancialGraph instance
        """
        self.graph = graph

    def run_detection(self) -> List[Dict[str, Any]]:
        """
        Run weak signal detection across all data sources.

        Returns:
            List of WeakSignal records that were created/updated
        """
        signals_found = self._collect_signals()
        if not signals_found:
            return []

        score = sum(s["weight"] for s in signals_found)
        if score < STRESS_THRESHOLD:
            return []

        signal_id = f"ws_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        signal_data = {
            "id": signal_id,
            "score": score,
            "signals_json": json.dumps(signals_found),
            "detected_at": datetime.utcnow().isoformat(),
            "acknowledged": False,
        }
        self.graph.create_weak_signal_node(signal_data)
        return [signal_data]

    def _collect_signals(self) -> List[Dict[str, Any]]:
        """Gather all individual weak signals from live data."""
        signals = []

        # 1. Budget slightly over (5–15%)
        try:
            budgets = self.graph.get_all_budgets_raw()
            for b in budgets:
                budget_amt = b.get("budget", 0) or 0
                actual_amt = b.get("actual", 0) or 0
                if budget_amt > 0:
                    overrun_pct = (actual_amt - budget_amt) / budget_amt * 100
                    if 5 <= overrun_pct <= 15:
                        signals.append({
                            "type": "budget_slightly_over",
                            "subject": b.get("department", "?"),
                            "detail": f"{overrun_pct:.1f}% over budget",
                            "weight": SIGNAL_WEIGHTS["budget_slightly_over"],
                        })
        except Exception:
            pass

        # 2. Invoices 15-30 days overdue
        try:
            invoices = self.graph.get_all_invoices_raw()
            for inv in invoices:
                days = inv.get("days_overdue", 0) or 0
                if 15 <= days <= 30:
                    signals.append({
                        "type": "invoice_moderately_overdue",
                        "subject": inv.get("vendor", "?"),
                        "detail": f"{days} days overdue",
                        "weight": SIGNAL_WEIGHTS["invoice_moderately_overdue"],
                    })
        except Exception:
            pass

        # 3. Contracts expiring 61-90 days
        try:
            contracts = self.graph.get_all_contracts_raw()
            for c in contracts:
                days_left = c.get("days_until_expiry", 999) or 999
                if 61 <= days_left <= 90:
                    signals.append({
                        "type": "contract_expiring_medium",
                        "subject": c.get("vendor", "?"),
                        "detail": f"{days_left} days until expiry",
                        "weight": SIGNAL_WEIGHTS["contract_expiring_medium"],
                    })
        except Exception:
            pass

        # 4. Episodic patterns (new_episodic_pattern weight = 2)
        try:
            patterns = self.graph.get_episodic_memories()
            if patterns:
                signals.append({
                    "type": "new_episodic_pattern",
                    "subject": "System",
                    "detail": f"{len(patterns)} learned patterns active",
                    "weight": SIGNAL_WEIGHTS["new_episodic_pattern"],
                })
        except Exception:
            pass

        return signals

    def get_active_signals(self) -> List[Dict[str, Any]]:
        """Return all active (unacknowledged) weak signal clusters."""
        raw = self.graph.get_weak_signals(only_active=True)
        result = []
        for r in raw:
            try:
                signals_list = json.loads(r.get("signals_json", "[]"))
            except Exception:
                signals_list = []
            result.append({
                "id": r["id"],
                "score": r["score"],
                "signals": signals_list,
                "detected_at": r["detected_at"],
                "acknowledged": r["acknowledged"],
            })
        return result
