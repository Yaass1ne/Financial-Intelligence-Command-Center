"""
Budget Simulation Engine

Simulates impact of budget changes on financial outcomes.
Uses historical data for baseline predictions and returns confidence intervals.

Examples:
    >>> result = simulate_budget_change("Marketing", 10, months=12)
    >>> print(f"Projected ROI: {result['roi']:.2%}")
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def simulate_budget_change(
    department: str,
    change_percent: float,
    months: int = 12,
    historical_data: Optional[pd.DataFrame] = None,
    confidence_level: float = 0.95
) -> Dict[str, Any]:
    """
    Simulate impact of budget change.

    Args:
        department: Department name
        change_percent: Percentage change (+10 for +10%, -10 for -10%)
        months: Number of months to simulate
        historical_data: Historical budget data (optional)
        confidence_level: Confidence level for intervals (default: 0.95)

    Returns:
        Dictionary with simulation results:
        {
            "projected_revenue": float,
            "projected_costs": float,
            "roi": float,
            "confidence_interval": (float, float),
            "monthly_projections": List[Dict],
            "assumptions": Dict
        }

    Examples:
        >>> result = simulate_budget_change("Marketing", 10, months=12)
        >>> print(f"ROI: {result['roi']:.2%}")
        0.15
    """
    logger.info(f"Simulating {change_percent:+.1f}% budget change for {department} over {months} months")

    # Load historical data if not provided
    if historical_data is None:
        historical_data = _get_default_historical_data(department)

    # Calculate baseline metrics
    baseline = _calculate_baseline_metrics(department, historical_data)

    # Apply budget change
    new_budget = baseline['monthly_budget'] * (1 + change_percent / 100)
    budget_diff = new_budget - baseline['monthly_budget']

    # Estimate impact based on department type
    impact_multiplier = _get_department_impact_multiplier(department)

    # Project revenue impact (some departments generate revenue, others save costs)
    revenue_impact = budget_diff * impact_multiplier['revenue_multiplier']
    cost_savings = budget_diff * impact_multiplier['cost_efficiency']

    # Calculate monthly projections
    monthly_projections = []
    cumulative_revenue = 0
    cumulative_costs = 0

    for month in range(1, months + 1):
        # Apply growth curve (impact increases over time for some departments)
        month_factor = _calculate_month_factor(month, months, department)

        month_revenue = revenue_impact * month_factor
        month_cost = new_budget  # Budget spent each month

        cumulative_revenue += month_revenue
        cumulative_costs += month_cost

        monthly_projections.append({
            'month': month,
            'revenue': round(month_revenue, 2),
            'cost': round(month_cost, 2),
            'cumulative_revenue': round(cumulative_revenue, 2),
            'cumulative_costs': round(cumulative_costs, 2),
            'roi': round((cumulative_revenue - cumulative_costs) / cumulative_costs, 4) if cumulative_costs > 0 else 0
        })

    # Calculate final ROI
    total_revenue = cumulative_revenue
    total_costs = cumulative_costs
    roi = (total_revenue - total_costs) / total_costs if total_costs > 0 else 0

    # Calculate confidence interval based on historical variance
    variance = baseline.get('variance', 0.15)  # Default 15% variance
    z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%

    lower_bound = roi - (z_score * variance)
    upper_bound = roi + (z_score * variance)

    result = {
        'department': department,
        'change_percent': change_percent,
        'simulation_months': months,
        'projected_revenue': round(total_revenue, 2),
        'projected_costs': round(total_costs, 2),
        'roi': round(roi, 4),
        'confidence_interval': (round(lower_bound, 4), round(upper_bound, 4)),
        'confidence_level': confidence_level,
        'monthly_projections': monthly_projections,
        'baseline': baseline,
        'assumptions': {
            'revenue_multiplier': impact_multiplier['revenue_multiplier'],
            'cost_efficiency': impact_multiplier['cost_efficiency'],
            'historical_variance': variance
        }
    }

    logger.info(f"Simulation complete: ROI = {roi:.2%}, CI = [{lower_bound:.2%}, {upper_bound:.2%}]")

    return result


def compare_budget_scenarios(
    department: str,
    change_percentages: List[float],
    months: int = 12,
    historical_data: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Compare multiple budget change scenarios.

    Args:
        department: Department name
        change_percentages: List of percentage changes to compare
        months: Number of months to simulate
        historical_data: Historical budget data (optional)

    Returns:
        Dictionary with comparison results

    Examples:
        >>> scenarios = compare_budget_scenarios("Marketing", [-20, -10, 0, 10, 20])
        >>> print(scenarios['best_scenario'])
    """
    results = []

    for change_pct in change_percentages:
        scenario_result = simulate_budget_change(
            department=department,
            change_percent=change_pct,
            months=months,
            historical_data=historical_data
        )
        results.append(scenario_result)

    # Find best scenario by ROI
    best_scenario = max(results, key=lambda x: x['roi'])
    worst_scenario = min(results, key=lambda x: x['roi'])

    return {
        'department': department,
        'scenarios': results,
        'best_scenario': best_scenario,
        'worst_scenario': worst_scenario,
        'recommendation': _generate_recommendation(results)
    }


def _get_default_historical_data(department: str) -> pd.DataFrame:
    """
    Generate default historical data for simulation.

    Args:
        department: Department name

    Returns:
        DataFrame with historical budget data
    """
    # Generate synthetic historical data (in real implementation, load from database)
    months = 12
    base_budget = {
        'Marketing': 50000,
        'Sales': 75000,
        'IT': 60000,
        'R&D': 100000,
        'HR': 30000,
        'Operations': 80000
    }.get(department, 50000)

    data = []
    for i in range(months):
        # Add some realistic variance
        monthly_budget = base_budget * (1 + np.random.normal(0, 0.05))
        monthly_actual = monthly_budget * (1 + np.random.normal(0, 0.10))

        data.append({
            'month': i + 1,
            'department': department,
            'budget': monthly_budget,
            'actual': monthly_actual,
            'variance': monthly_actual - monthly_budget
        })

    return pd.DataFrame(data)


def _calculate_baseline_metrics(department: str, historical_data: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate baseline metrics from historical data.

    Args:
        department: Department name
        historical_data: Historical budget DataFrame

    Returns:
        Dictionary with baseline metrics
    """
    if historical_data.empty:
        return {
            'monthly_budget': 50000,
            'avg_actual': 50000,
            'variance': 0.15
        }

    dept_data = historical_data[historical_data['department'] == department] if 'department' in historical_data.columns else historical_data

    monthly_budget = dept_data['budget'].mean()
    avg_actual = dept_data['actual'].mean() if 'actual' in dept_data.columns else monthly_budget
    variance_std = dept_data['variance'].std() if 'variance' in dept_data.columns else monthly_budget * 0.15

    # Calculate relative variance
    relative_variance = variance_std / monthly_budget if monthly_budget > 0 else 0.15

    return {
        'monthly_budget': monthly_budget,
        'avg_actual': avg_actual,
        'variance': relative_variance
    }


def _get_department_impact_multiplier(department: str) -> Dict[str, float]:
    """
    Get impact multipliers for different department types.

    Args:
        department: Department name

    Returns:
        Dictionary with revenue_multiplier and cost_efficiency
    """
    # Department-specific multipliers based on typical ROI patterns
    multipliers = {
        'Marketing': {
            'revenue_multiplier': 3.0,  # $1 marketing spend → $3 revenue (typical)
            'cost_efficiency': 0.8
        },
        'Sales': {
            'revenue_multiplier': 5.0,  # Sales typically has high ROI
            'cost_efficiency': 0.9
        },
        'IT': {
            'revenue_multiplier': 0.5,  # IT is cost center, some efficiency gains
            'cost_efficiency': 1.5  # But improves operational efficiency
        },
        'R&D': {
            'revenue_multiplier': 10.0,  # High risk, high reward
            'cost_efficiency': 0.6
        },
        'HR': {
            'revenue_multiplier': 0.3,  # Indirect revenue impact
            'cost_efficiency': 1.2  # Improves productivity
        },
        'Operations': {
            'revenue_multiplier': 1.0,
            'cost_efficiency': 1.3
        }
    }

    return multipliers.get(department, {
        'revenue_multiplier': 1.0,
        'cost_efficiency': 1.0
    })


def _calculate_month_factor(month: int, total_months: int, department: str) -> float:
    """
    Calculate impact factor for a given month.

    Some departments see immediate impact, others ramp up over time.

    Args:
        month: Current month (1-indexed)
        total_months: Total simulation months
        department: Department name

    Returns:
        Impact factor (0-1)
    """
    # Departments with immediate impact
    immediate_departments = ['Sales', 'Operations']

    # Departments with gradual ramp-up
    gradual_departments = ['Marketing', 'R&D']

    if department in immediate_departments:
        # Immediate but increasing impact
        return min(1.0, 0.7 + (month / total_months) * 0.3)

    elif department in gradual_departments:
        # Slow ramp-up (S-curve)
        progress = month / total_months
        return 1 / (1 + np.exp(-10 * (progress - 0.5)))

    else:
        # Linear ramp-up
        return month / total_months


def _generate_recommendation(scenarios: List[Dict[str, Any]]) -> str:
    """
    Generate recommendation based on scenario comparison.

    Args:
        scenarios: List of scenario results

    Returns:
        Recommendation string
    """
    best = max(scenarios, key=lambda x: x['roi'])
    change_pct = best['change_percent']
    roi = best['roi']

    if change_pct > 0:
        return f"Recommend increasing budget by {change_pct:.0f}% for expected ROI of {roi:.1%}"
    elif change_pct < 0:
        return f"Recommend decreasing budget by {abs(change_pct):.0f}% (ROI: {roi:.1%})"
    else:
        return f"Recommend maintaining current budget (ROI: {roi:.1%})"


def calculate_breakeven_point(
    department: str,
    initial_investment: float,
    monthly_return: float,
    months: int = 24
) -> Optional[int]:
    """
    Calculate how many months until investment breaks even.

    Args:
        department: Department name
        initial_investment: Initial investment amount
        monthly_return: Expected monthly return
        months: Maximum months to calculate

    Returns:
        Month number when breakeven is reached, or None if not reached

    Examples:
        >>> breakeven = calculate_breakeven_point("Marketing", 100000, 15000)
        >>> print(f"Breakeven in {breakeven} months")
    """
    cumulative_return = 0

    for month in range(1, months + 1):
        cumulative_return += monthly_return

        if cumulative_return >= initial_investment:
            logger.info(f"Breakeven reached at month {month}")
            return month

    logger.warning(f"Breakeven not reached within {months} months")
    return None
