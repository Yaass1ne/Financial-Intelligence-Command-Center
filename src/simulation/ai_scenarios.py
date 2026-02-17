"""
FINCENTER AI Scenario Generator

Uses Groq/Llama to generate named financial scenarios from live data.
Falls back gracefully if LLM returns malformed JSON.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from src.config import settings


# ============================================
# Fallback Scenarios (used when LLM fails)
# ============================================

FALLBACK_SCENARIOS = [
    {
        "name": "Supply Chain Stress",
        "probability": 0.35,
        "description": (
            "Key vendor contracts expire without renewal while multiple invoices "
            "remain unpaid, straining supplier relationships and procurement capacity."
        ),
        "budget_impact_pct": -12,
        "cashflow_impact_pct": -18,
        "key_risks": [
            "Vendor service interruption",
            "Emergency procurement at premium prices",
            "Operational delays",
        ],
        "recommended_actions": [
            "Expedite contract renewals",
            "Clear overdue invoices",
            "Identify alternative vendors",
        ],
    },
    {
        "name": "Budget Overrun Cascade",
        "probability": 0.28,
        "description": (
            "Departments exceeding budget targets create a cascading effect "
            "on quarterly forecasts, triggering emergency cost-cutting measures."
        ),
        "budget_impact_pct": -15,
        "cashflow_impact_pct": -10,
        "key_risks": [
            "FY target miss",
            "Reduced investment capacity",
            "Staff morale impact from cuts",
        ],
        "recommended_actions": [
            "Freeze discretionary spending",
            "Reallocate under-budget department funds",
            "Monthly variance reviews",
        ],
    },
    {
        "name": "Controlled Recovery",
        "probability": 0.42,
        "description": (
            "Proactive contract renewals and invoice resolution reduce financial stress, "
            "freeing capital for strategic investment in Q2."
        ),
        "budget_impact_pct": 5,
        "cashflow_impact_pct": 8,
        "key_risks": [
            "Execution risk on action plan",
            "Market conditions",
        ],
        "recommended_actions": [
            "Execute top-priority recommendations",
            "Monthly KPI tracking",
            "Engage strategic vendors for multi-year deals",
        ],
    },
]


class AIScenarioGenerator:
    """Generates named financial scenarios using Groq LLM or fallback logic."""

    def __init__(self, graph):
        """
        Args:
            graph: FinancialGraph instance
        """
        self.graph = graph

    def generate_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate 3 AI-named financial scenarios from current data.

        Returns:
            List of scenario dicts (stored in Neo4j as Scenario nodes)
        """
        context = self._build_context()
        scenarios = self._call_llm(context)

        # Persist to Neo4j
        now = datetime.utcnow().isoformat()
        saved = []
        for s in scenarios:
            scenario_id = f"scenario_{uuid.uuid4().hex[:8]}"
            node_data = {
                "id": scenario_id,
                "name": s.get("name", "Unnamed Scenario"),
                "probability": s.get("probability", 0.33),
                "description": s.get("description", ""),
                "budget_impact_pct": s.get("budget_impact_pct", 0),
                "cashflow_impact_pct": s.get("cashflow_impact_pct", 0),
                "key_risks": json.dumps(s.get("key_risks", [])),
                "recommended_actions": json.dumps(s.get("recommended_actions", [])),
                "created_at": now,
                "source": "ai_generated",
            }
            try:
                self._save_scenario(node_data)
            except Exception:
                pass
            saved.append({**s, "id": scenario_id, "created_at": now})

        return saved

    # ============================================
    # Context Building
    # ============================================

    def _build_context(self) -> str:
        """Build a financial context summary for the LLM prompt."""
        lines = ["=== CURRENT FINANCIAL CONTEXT ==="]

        try:
            budgets = self.graph.get_all_budgets_raw()
            if budgets:
                over = [b for b in budgets if (b.get("actual") or 0) > (b.get("budget") or 0)]
                total_overrun = sum(
                    (b.get("actual", 0) or 0) - (b.get("budget", 0) or 0)
                    for b in over
                )
                lines.append(
                    f"BUDGETS: {len(budgets)} departments tracked, "
                    f"{len(over)} over budget, total overrun: {total_overrun:,.0f} EUR"
                )
        except Exception:
            pass

        try:
            invoices = self.graph.get_all_invoices_raw()
            overdue = [i for i in invoices if (i.get("days_overdue") or 0) > 0]
            total_overdue_amt = sum(i.get("amount", 0) or 0 for i in overdue)
            if overdue:
                lines.append(
                    f"INVOICES: {len(overdue)} overdue invoices, "
                    f"total outstanding: {total_overdue_amt:,.0f} EUR, "
                    f"oldest: {max(i.get('days_overdue', 0) or 0 for i in overdue)} days"
                )
        except Exception:
            pass

        try:
            contracts = self.graph.get_all_contracts_raw()
            expiring = [c for c in contracts if 0 < (c.get("days_until_expiry") or 999) <= 90]
            total_contract_value = sum(c.get("annual_value", 0) or 0 for c in expiring)
            if expiring:
                lines.append(
                    f"CONTRACTS: {len(expiring)} expiring in <90 days, "
                    f"total annual value at risk: {total_contract_value:,.0f} EUR"
                )
        except Exception:
            pass

        return "\n".join(lines)

    # ============================================
    # LLM Call
    # ============================================

    def _call_llm(self, context: str) -> List[Dict[str, Any]]:
        """Call Groq to generate 3 named scenarios. Returns fallback on failure."""
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)

            prompt = f"""You are a senior financial risk analyst.

Based on the following financial data summary, generate exactly 3 named financial scenarios.
Return ONLY a valid JSON array (no markdown, no explanation) with this schema:
[
  {{
    "name": "Scenario Name",
    "probability": 0.35,
    "description": "2-3 sentence description of the scenario",
    "budget_impact_pct": -12,
    "cashflow_impact_pct": -18,
    "key_risks": ["risk 1", "risk 2", "risk 3"],
    "recommended_actions": ["action 1", "action 2", "action 3"]
  }}
]

{context}

Generate 3 distinct scenarios: one pessimistic, one base case, one optimistic.
Ensure probabilities sum to approximately 1.0.
"""
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            scenarios = json.loads(raw)
            if isinstance(scenarios, list) and len(scenarios) >= 1:
                return scenarios[:3]
        except Exception:
            pass

        return FALLBACK_SCENARIOS

    # ============================================
    # Persistence
    # ============================================

    def _save_scenario(self, node_data: Dict[str, Any]):
        """Save a Scenario node to Neo4j."""
        query = """
        MERGE (s:Scenario {id: $id})
        SET s.name = $name,
            s.probability = $probability,
            s.description = $description,
            s.budget_impact_pct = $budget_impact_pct,
            s.cashflow_impact_pct = $cashflow_impact_pct,
            s.key_risks = $key_risks,
            s.recommended_actions = $recommended_actions,
            s.created_at = $created_at,
            s.source = $source
        RETURN s
        """
        with self.graph.driver.session() as session:
            session.run(query, **node_data)
