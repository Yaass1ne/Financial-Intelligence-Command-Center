"""
Cash Flow Forecasting Simulator

Predicts future liquidity and cash flow positions.
Accounts for payment delays, seasonal variations, and multiple scenarios.

Examples:
    >>> forecast = forecast_cashflow(months_ahead=3)
    >>> print(f"Liquidity at T+90: {forecast['base']['final_balance']}")
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def forecast_cashflow(
    months_ahead: int = 3,
    scenarios: Optional[List[str]] = None,
    starting_balance: float = 100000,
    historical_data: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Forecast cash flow for different scenarios.

    Args:
        months_ahead: Number of months to forecast
        scenarios: List of scenarios (default: ["optimistic", "base", "pessimistic"])
        starting_balance: Starting cash balance
        historical_data: Historical cash flow data (optional)

    Returns:
        Dictionary mapping scenario names to DataFrames with forecasts

    Examples:
        >>> forecast = forecast_cashflow(months_ahead=3)
        >>> print(forecast['base']['final_balance'])
        95000.0
    """
    if scenarios is None:
        scenarios = ["optimistic", "base", "pessimistic"]

    logger.info(f"Forecasting cash flow for {months_ahead} months with scenarios: {scenarios}")

    # Load historical data if not provided
    if historical_data is None:
        historical_data = _get_default_cashflow_data()

    # Calculate baseline metrics from historical data
    baseline_metrics = _calculate_baseline_cashflow_metrics(historical_data)

    # Generate forecasts for each scenario
    results = {}

    for scenario in scenarios:
        scenario_params = _get_scenario_parameters(scenario, baseline_metrics)
        forecast_df = _generate_cashflow_forecast(
            months_ahead=months_ahead,
            starting_balance=starting_balance,
            params=scenario_params,
            historical_data=historical_data
        )

        results[scenario] = {
            'forecast': forecast_df,
            'final_balance': forecast_df.iloc[-1]['ending_balance'],
            'min_balance': forecast_df['ending_balance'].min(),
            'max_balance': forecast_df['ending_balance'].max(),
            'total_inflows': forecast_df['inflows'].sum(),
            'total_outflows': forecast_df['outflows'].sum(),
            'net_cashflow': forecast_df['net_cashflow'].sum(),
            'liquidity_crisis': forecast_df['ending_balance'].min() < 0
        }

    # Add summary
    results['summary'] = {
        'starting_balance': starting_balance,
        'months_ahead': months_ahead,
        'scenarios_compared': scenarios,
        'baseline_metrics': baseline_metrics
    }

    # Log warnings for potential issues
    for scenario, data in results.items():
        if scenario != 'summary' and data.get('liquidity_crisis'):
            logger.warning(f"⚠️  Liquidity crisis predicted in {scenario} scenario (min balance: {data['min_balance']:.2f})")

    return results


def predict_liquidity(
    days_ahead: int = 90,
    include_payment_delays: bool = True,
    client_payment_patterns: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Predict liquidity at T+N days.

    Args:
        days_ahead: Number of days ahead to predict
        include_payment_delays: Account for typical client payment delays
        client_payment_patterns: Dictionary mapping client names to average delay days

    Returns:
        Dictionary with liquidity prediction

    Examples:
        >>> liquidity = predict_liquidity(days_ahead=90)
        >>> print(f"Expected balance: {liquidity['expected_balance']}")
    """
    logger.info(f"Predicting liquidity at T+{days_ahead} days")

    # Default payment patterns if not provided
    if client_payment_patterns is None:
        client_payment_patterns = {
            'Client A': 15,  # Pays 15 days late on average
            'Client B': 5,   # Pays 5 days late
            'Client C': -3,  # Pays 3 days early
            'Client D': 30   # Pays 30 days late (problem client)
        }

    # Simulate expected receivables
    expected_receivables = _calculate_expected_receivables(
        days_ahead=days_ahead,
        payment_patterns=client_payment_patterns,
        include_delays=include_payment_delays
    )

    # Simulate expected payables
    expected_payables = _calculate_expected_payables(days_ahead=days_ahead)

    # Calculate net position
    starting_balance = 100000  # Default starting balance
    expected_balance = starting_balance + expected_receivables - expected_payables

    result = {
        'days_ahead': days_ahead,
        'prediction_date': (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d'),
        'starting_balance': starting_balance,
        'expected_receivables': expected_receivables,
        'expected_payables': expected_payables,
        'expected_balance': expected_balance,
        'liquidity_ratio': expected_balance / expected_payables if expected_payables > 0 else float('inf'),
        'payment_delays_included': include_payment_delays,
        'client_patterns': client_payment_patterns
    }

    # Add risk assessment
    if expected_balance < 0:
        result['risk_level'] = 'CRITICAL'
        result['recommendation'] = 'Immediate action required - seek additional financing'
    elif expected_balance < expected_payables * 0.2:
        result['risk_level'] = 'HIGH'
        result['recommendation'] = 'Low liquidity - accelerate collections or defer payments'
    elif expected_balance < expected_payables * 0.5:
        result['risk_level'] = 'MEDIUM'
        result['recommendation'] = 'Monitor closely and follow up on late payments'
    else:
        result['risk_level'] = 'LOW'
        result['recommendation'] = 'Healthy liquidity position'

    logger.info(f"Liquidity prediction: {expected_balance:.2f} ({result['risk_level']} risk)")

    return result


def analyze_seasonal_variations(
    historical_data: Optional[pd.DataFrame] = None,
    years: int = 2
) -> Dict[str, Any]:
    """
    Analyze seasonal cash flow patterns.

    Args:
        historical_data: Historical cash flow data
        years: Number of years of data to analyze

    Returns:
        Dictionary with seasonal analysis

    Examples:
        >>> analysis = analyze_seasonal_variations()
        >>> print(analysis['peak_month'])
        'December'
    """
    if historical_data is None:
        historical_data = _get_default_cashflow_data(months=years * 12)

    # Add month column if not present
    if 'month' not in historical_data.columns and 'date' in historical_data.columns:
        historical_data['month'] = pd.to_datetime(historical_data['date']).dt.month

    # Group by month
    monthly_avg = historical_data.groupby('month').agg({
        'inflows': 'mean',
        'outflows': 'mean',
        'net_cashflow': 'mean'
    }).round(2)

    # Find peak and trough months
    peak_month = monthly_avg['net_cashflow'].idxmax()
    trough_month = monthly_avg['net_cashflow'].idxmin()

    # Calculate seasonality index (relative to annual average)
    annual_avg = historical_data['net_cashflow'].mean()
    monthly_avg['seasonality_index'] = (monthly_avg['net_cashflow'] / annual_avg).round(2)

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    result = {
        'monthly_averages': monthly_avg.to_dict('index'),
        'peak_month': month_names[peak_month - 1],
        'peak_value': monthly_avg.loc[peak_month, 'net_cashflow'],
        'trough_month': month_names[trough_month - 1],
        'trough_value': monthly_avg.loc[trough_month, 'net_cashflow'],
        'annual_average': annual_avg,
        'volatility': historical_data['net_cashflow'].std()
    }

    logger.info(f"Seasonal analysis: Peak in {result['peak_month']}, Trough in {result['trough_month']}")

    return result


def _get_default_cashflow_data(months: int = 12) -> pd.DataFrame:
    """
    Generate default historical cash flow data.

    Args:
        months: Number of months of data

    Returns:
        DataFrame with historical cash flow
    """
    data = []
    base_inflows = 200000
    base_outflows = 180000

    for i in range(months):
        # Add seasonal variation
        month = (i % 12) + 1
        seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * month / 12)  # Peak in June, trough in December

        # Add random variation
        inflows = base_inflows * seasonal_factor * (1 + np.random.normal(0, 0.15))
        outflows = base_outflows * (1 + np.random.normal(0, 0.10))

        data.append({
            'month': month,
            'period': i + 1,
            'inflows': round(inflows, 2),
            'outflows': round(outflows, 2),
            'net_cashflow': round(inflows - outflows, 2)
        })

    return pd.DataFrame(data)


def _calculate_baseline_cashflow_metrics(historical_data: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate baseline metrics from historical cash flow data.

    Args:
        historical_data: Historical DataFrame

    Returns:
        Dictionary with baseline metrics
    """
    return {
        'avg_monthly_inflows': historical_data['inflows'].mean(),
        'avg_monthly_outflows': historical_data['outflows'].mean(),
        'avg_net_cashflow': historical_data['net_cashflow'].mean(),
        'inflows_std': historical_data['inflows'].std(),
        'outflows_std': historical_data['outflows'].std(),
        'net_cashflow_std': historical_data['net_cashflow'].std()
    }


def _get_scenario_parameters(scenario: str, baseline: Dict[str, float]) -> Dict[str, float]:
    """
    Get parameters for different scenarios.

    Args:
        scenario: Scenario name
        baseline: Baseline metrics

    Returns:
        Dictionary with scenario parameters
    """
    if scenario == "optimistic":
        return {
            'inflows_multiplier': 1.15,
            'outflows_multiplier': 0.95,
            'inflows_volatility': baseline['inflows_std'] * 0.8,
            'outflows_volatility': baseline['outflows_std'] * 0.8,
            'payment_delay_factor': 0.7  # Clients pay faster
        }
    elif scenario == "pessimistic":
        return {
            'inflows_multiplier': 0.85,
            'outflows_multiplier': 1.10,
            'inflows_volatility': baseline['inflows_std'] * 1.3,
            'outflows_volatility': baseline['outflows_std'] * 1.2,
            'payment_delay_factor': 1.5  # Clients pay slower
        }
    else:  # base
        return {
            'inflows_multiplier': 1.0,
            'outflows_multiplier': 1.0,
            'inflows_volatility': baseline['inflows_std'],
            'outflows_volatility': baseline['outflows_std'],
            'payment_delay_factor': 1.0
        }


def _generate_cashflow_forecast(
    months_ahead: int,
    starting_balance: float,
    params: Dict[str, float],
    historical_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate cash flow forecast for given parameters.

    Args:
        months_ahead: Number of months to forecast
        starting_balance: Starting balance
        params: Scenario parameters
        historical_data: Historical data

    Returns:
        DataFrame with forecast
    """
    baseline = _calculate_baseline_cashflow_metrics(historical_data)

    forecast_data = []
    current_balance = starting_balance

    for month in range(1, months_ahead + 1):
        # Calculate seasonal factor
        calendar_month = (datetime.now().month + month - 1) % 12 + 1
        seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * calendar_month / 12)

        # Generate inflows with scenario adjustments
        expected_inflows = baseline['avg_monthly_inflows'] * params['inflows_multiplier'] * seasonal_factor
        actual_inflows = expected_inflows + np.random.normal(0, params['inflows_volatility'])

        # Generate outflows
        expected_outflows = baseline['avg_monthly_outflows'] * params['outflows_multiplier']
        actual_outflows = expected_outflows + np.random.normal(0, params['outflows_volatility'])

        # Ensure non-negative values
        actual_inflows = max(0, actual_inflows)
        actual_outflows = max(0, actual_outflows)

        # Calculate balances
        net_cashflow = actual_inflows - actual_outflows
        ending_balance = current_balance + net_cashflow

        forecast_data.append({
            'month': month,
            'starting_balance': round(current_balance, 2),
            'inflows': round(actual_inflows, 2),
            'outflows': round(actual_outflows, 2),
            'net_cashflow': round(net_cashflow, 2),
            'ending_balance': round(ending_balance, 2)
        })

        current_balance = ending_balance

    return pd.DataFrame(forecast_data)


def _calculate_expected_receivables(
    days_ahead: int,
    payment_patterns: Dict[str, int],
    include_delays: bool
) -> float:
    """
    Calculate expected receivables accounting for payment delays.

    Args:
        days_ahead: Number of days ahead
        payment_patterns: Client payment delay patterns
        include_delays: Whether to include delays

    Returns:
        Expected receivables amount
    """
    # Simulate invoices issued
    monthly_revenue = 200000
    daily_revenue = monthly_revenue / 30

    # Expected revenue for the period
    total_revenue = daily_revenue * days_ahead

    if include_delays:
        # Adjust for payment delays
        avg_delay = sum(payment_patterns.values()) / len(payment_patterns)
        # Revenue received = revenue from (days_ahead - avg_delay) days ago
        adjusted_days = max(0, days_ahead - avg_delay)
        total_revenue = daily_revenue * adjusted_days

    return round(total_revenue, 2)


def _calculate_expected_payables(days_ahead: int) -> float:
    """
    Calculate expected payables for period.

    Args:
        days_ahead: Number of days ahead

    Returns:
        Expected payables amount
    """
    monthly_expenses = 180000
    daily_expenses = monthly_expenses / 30

    total_payables = daily_expenses * days_ahead

    return round(total_payables, 2)


def stress_test_cashflow(
    shock_scenarios: Optional[List[Dict[str, Any]]] = None,
    starting_balance: float = 100000
) -> Dict[str, Any]:
    """
    Stress test cash flow under various shock scenarios.

    Args:
        shock_scenarios: List of shock scenario definitions
        starting_balance: Starting cash balance

    Returns:
        Dictionary with stress test results

    Examples:
        >>> results = stress_test_cashflow()
        >>> print(results['revenue_drop_50']['survives'])
    """
    if shock_scenarios is None:
        shock_scenarios = [
            {'name': 'revenue_drop_30', 'inflows_multiplier': 0.7, 'outflows_multiplier': 1.0},
            {'name': 'revenue_drop_50', 'inflows_multiplier': 0.5, 'outflows_multiplier': 1.0},
            {'name': 'cost_spike_20', 'inflows_multiplier': 1.0, 'outflows_multiplier': 1.2},
            {'name': 'combined_crisis', 'inflows_multiplier': 0.6, 'outflows_multiplier': 1.15},
        ]

    results = {}

    for scenario in shock_scenarios:
        # Simulate 6 months under shock conditions
        params = {
            'inflows_multiplier': scenario['inflows_multiplier'],
            'outflows_multiplier': scenario['outflows_multiplier'],
            'inflows_volatility': 10000,
            'outflows_volatility': 8000,
            'payment_delay_factor': 1.0
        }

        historical_data = _get_default_cashflow_data()
        forecast = _generate_cashflow_forecast(
            months_ahead=6,
            starting_balance=starting_balance,
            params=params,
            historical_data=historical_data
        )

        min_balance = forecast['ending_balance'].min()
        survives = min_balance >= 0

        results[scenario['name']] = {
            'survives': survives,
            'min_balance': min_balance,
            'final_balance': forecast.iloc[-1]['ending_balance'],
            'months_until_crisis': None
        }

        # Find month when balance goes negative
        if not survives:
            negative_months = forecast[forecast['ending_balance'] < 0]
            if not negative_months.empty:
                results[scenario['name']]['months_until_crisis'] = negative_months.iloc[0]['month']

    logger.info(f"Stress test complete: {sum(1 for r in results.values() if r['survives'])}/{len(results)} scenarios survived")

    return results
