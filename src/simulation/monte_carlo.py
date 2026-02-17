"""
Monte Carlo Probabilistic Simulator

Runs probabilistic simulations to model uncertainty in financial outcomes.
Returns distribution of possible outcomes with percentiles.

Examples:
    >>> result = run_monte_carlo({'revenue': 100000}, {'revenue': 0.15})
    >>> print(f"P50: {result['percentiles']['p50']}")
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    mean: float
    median: float
    std: float
    percentiles: Dict[str, float]
    distribution: np.ndarray
    iterations: int
    converged: bool

    def __repr__(self) -> str:
        return (
            f"MonteCarloResult(mean={self.mean:.2f}, "
            f"std={self.std:.2f}, "
            f"P5={self.percentiles['p5']:.2f}, "
            f"P50={self.percentiles['p50']:.2f}, "
            f"P95={self.percentiles['p95']:.2f})"
        )


def run_monte_carlo(
    base_params: Dict[str, float],
    volatility: Dict[str, float],
    iterations: int = 10000,
    distribution_type: str = 'normal',
    early_stopping: bool = True,
    convergence_threshold: float = 0.01
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation.

    Args:
        base_params: Base parameter values (e.g., {'revenue': 100000, 'costs': 80000})
        volatility: Standard deviation for each parameter (e.g., {'revenue': 0.15, 'costs': 0.10})
        iterations: Number of iterations (default: 10000)
        distribution_type: Distribution type ('normal', 'lognormal', 'uniform')
        early_stopping: Enable early stopping when converged
        convergence_threshold: Convergence threshold for early stopping

    Returns:
        Dictionary with simulation results:
        {
            "mean": float,
            "std": float,
            "percentiles": {"p5": float, "p50": float, "p95": float},
            "distribution": np.ndarray,
            "converged": bool
        }

    Examples:
        >>> result = run_monte_carlo(
        ...     {'revenue': 100000, 'costs': 80000},
        ...     {'revenue': 0.15, 'costs': 0.10}
        ... )
        >>> print(f"Expected profit: {result['mean']:.2f}")
    """
    logger.info(f"Running Monte Carlo simulation with {iterations} iterations")

    # Validate inputs
    if not base_params:
        raise ValueError("base_params cannot be empty")

    if set(base_params.keys()) != set(volatility.keys()):
        raise ValueError("base_params and volatility must have the same keys")

    # Initialize results array
    results = np.zeros(iterations)

    # Track convergence
    running_means = []
    converged_at = None

    # Run simulations
    for i in range(iterations):
        # Sample from distributions
        sampled_params = _sample_parameters(
            base_params,
            volatility,
            distribution_type
        )

        # Calculate outcome (revenue - costs in this example)
        outcome = sampled_params.get('revenue', 0) - sampled_params.get('costs', 0)
        results[i] = outcome

        # Check convergence every 100 iterations (after first 1000)
        if early_stopping and i > 1000 and i % 100 == 0:
            running_mean = np.mean(results[:i])
            running_means.append(running_mean)

            if len(running_means) > 10:
                # Check if mean has stabilized
                recent_means = running_means[-10:]
                mean_change = np.std(recent_means) / abs(running_mean) if running_mean != 0 else float('inf')

                if mean_change < convergence_threshold:
                    converged_at = i
                    logger.info(f"Converged early at iteration {i} (threshold: {convergence_threshold})")
                    results = results[:i]
                    break

    # Calculate statistics
    mean = float(np.mean(results))
    median = float(np.median(results))
    std = float(np.std(results))

    # Calculate percentiles
    percentiles = {
        'p1': float(np.percentile(results, 1)),
        'p5': float(np.percentile(results, 5)),
        'p10': float(np.percentile(results, 10)),
        'p25': float(np.percentile(results, 25)),
        'p50': float(np.percentile(results, 50)),
        'p75': float(np.percentile(results, 75)),
        'p90': float(np.percentile(results, 90)),
        'p95': float(np.percentile(results, 95)),
        'p99': float(np.percentile(results, 99)),
    }

    # Calculate probability of positive outcome
    prob_positive = float(np.sum(results > 0) / len(results))

    result = {
        'mean': round(mean, 2),
        'median': round(median, 2),
        'std': round(std, 2),
        'min': round(float(np.min(results)), 2),
        'max': round(float(np.max(results)), 2),
        'percentiles': {k: round(v, 2) for k, v in percentiles.items()},
        'distribution': results,
        'iterations': len(results),
        'converged': converged_at is not None,
        'converged_at': converged_at,
        'probability_positive': round(prob_positive, 4),
        'base_params': base_params,
        'volatility': volatility,
        'distribution_type': distribution_type
    }

    logger.info(f"Simulation complete: mean={mean:.2f}, std={std:.2f}, P(>0)={prob_positive:.2%}")

    return result


def simulate_revenue_uncertainty(
    expected_revenue: float,
    revenue_volatility: float,
    expected_costs: float,
    cost_volatility: float,
    iterations: int = 10000
) -> MonteCarloResult:
    """
    Simulate revenue and cost uncertainty to predict profit distribution.

    Args:
        expected_revenue: Expected revenue
        revenue_volatility: Revenue standard deviation (as fraction, e.g., 0.15 for 15%)
        expected_costs: Expected costs
        cost_volatility: Cost standard deviation
        iterations: Number of simulations

    Returns:
        MonteCarloResult with profit distribution

    Examples:
        >>> result = simulate_revenue_uncertainty(100000, 0.15, 80000, 0.10)
        >>> print(result)
    """
    result = run_monte_carlo(
        base_params={'revenue': expected_revenue, 'costs': expected_costs},
        volatility={'revenue': revenue_volatility, 'costs': cost_volatility},
        iterations=iterations
    )

    return MonteCarloResult(
        mean=result['mean'],
        median=result['median'],
        std=result['std'],
        percentiles=result['percentiles'],
        distribution=result['distribution'],
        iterations=result['iterations'],
        converged=result['converged']
    )


def simulate_payment_delays(
    num_invoices: int,
    avg_invoice_amount: float,
    avg_payment_delay: int,
    delay_std: int,
    iterations: int = 10000
) -> Dict[str, Any]:
    """
    Simulate impact of payment delays on cash flow.

    Args:
        num_invoices: Number of invoices to simulate
        avg_invoice_amount: Average invoice amount
        avg_payment_delay: Average payment delay in days
        delay_std: Standard deviation of payment delay
        iterations: Number of simulations

    Returns:
        Dictionary with payment delay simulation results

    Examples:
        >>> result = simulate_payment_delays(100, 5000, 15, 10)
        >>> print(f"Expected DSO: {result['avg_dso']:.1f} days")
    """
    logger.info(f"Simulating payment delays for {num_invoices} invoices")

    dso_results = []  # Days Sales Outstanding

    for _ in range(iterations):
        # Generate invoice amounts
        invoice_amounts = np.random.normal(avg_invoice_amount, avg_invoice_amount * 0.2, num_invoices)
        invoice_amounts = np.maximum(invoice_amounts, 0)  # Ensure non-negative

        # Generate payment delays
        payment_delays = np.random.normal(avg_payment_delay, delay_std, num_invoices)
        payment_delays = np.maximum(payment_delays, 0)  # Ensure non-negative

        # Calculate weighted average DSO
        total_revenue = np.sum(invoice_amounts)
        weighted_dso = np.sum(invoice_amounts * payment_delays) / total_revenue if total_revenue > 0 else 0

        dso_results.append(weighted_dso)

    dso_array = np.array(dso_results)

    result = {
        'avg_dso': float(np.mean(dso_array)),
        'median_dso': float(np.median(dso_array)),
        'std_dso': float(np.std(dso_array)),
        'percentiles': {
            'p5': float(np.percentile(dso_array, 5)),
            'p50': float(np.percentile(dso_array, 50)),
            'p95': float(np.percentile(dso_array, 95)),
        },
        'num_invoices': num_invoices,
        'avg_invoice_amount': avg_invoice_amount,
        'iterations': iterations
    }

    logger.info(f"Average DSO: {result['avg_dso']:.1f} days (P5={result['percentiles']['p5']:.1f}, P95={result['percentiles']['p95']:.1f})")

    return result


def simulate_budget_variance(
    departments: List[str],
    budgets: List[float],
    variance_rates: List[float],
    iterations: int = 10000
) -> Dict[str, Any]:
    """
    Simulate budget variance across multiple departments.

    Args:
        departments: List of department names
        budgets: List of budget amounts
        variance_rates: List of variance rates (std as fraction of budget)
        iterations: Number of simulations

    Returns:
        Dictionary with variance simulation results

    Examples:
        >>> result = simulate_budget_variance(
        ...     ['Marketing', 'Sales'],
        ...     [50000, 75000],
        ...     [0.15, 0.10]
        ... )
    """
    if len(departments) != len(budgets) or len(departments) != len(variance_rates):
        raise ValueError("departments, budgets, and variance_rates must have same length")

    logger.info(f"Simulating budget variance for {len(departments)} departments")

    total_variance_results = []
    dept_results = {dept: [] for dept in departments}

    for _ in range(iterations):
        total_actual = 0

        for i, dept in enumerate(departments):
            budget = budgets[i]
            variance_rate = variance_rates[i]

            # Sample actual spending
            actual = np.random.normal(budget, budget * variance_rate)
            actual = max(0, actual)  # Ensure non-negative

            dept_variance = actual - budget
            dept_results[dept].append(dept_variance)

            total_actual += actual

        total_budget = sum(budgets)
        total_variance = total_actual - total_budget
        total_variance_results.append(total_variance)

    # Aggregate results
    result = {
        'total_budget': sum(budgets),
        'total_variance': {
            'mean': float(np.mean(total_variance_results)),
            'std': float(np.std(total_variance_results)),
            'percentiles': {
                'p5': float(np.percentile(total_variance_results, 5)),
                'p50': float(np.percentile(total_variance_results, 50)),
                'p95': float(np.percentile(total_variance_results, 95)),
            }
        },
        'departments': {}
    }

    for dept in departments:
        dept_variance_array = np.array(dept_results[dept])
        result['departments'][dept] = {
            'mean_variance': float(np.mean(dept_variance_array)),
            'std_variance': float(np.std(dept_variance_array)),
            'prob_overbudget': float(np.sum(dept_variance_array > 0) / len(dept_variance_array))
        }

    return result


def _sample_parameters(
    base_params: Dict[str, float],
    volatility: Dict[str, float],
    distribution_type: str
) -> Dict[str, float]:
    """
    Sample parameter values from distributions.

    Args:
        base_params: Base parameter values
        volatility: Volatility for each parameter
        distribution_type: Type of distribution

    Returns:
        Dictionary with sampled values
    """
    sampled = {}

    for param, base_value in base_params.items():
        vol = volatility.get(param, 0)

        if distribution_type == 'normal':
            # Normal distribution
            sampled_value = np.random.normal(base_value, base_value * vol)

        elif distribution_type == 'lognormal':
            # Log-normal distribution (ensures positive values)
            mu = np.log(base_value)
            sigma = vol
            sampled_value = np.random.lognormal(mu, sigma)

        elif distribution_type == 'uniform':
            # Uniform distribution
            lower = base_value * (1 - vol)
            upper = base_value * (1 + vol)
            sampled_value = np.random.uniform(lower, upper)

        else:
            raise ValueError(f"Unknown distribution type: {distribution_type}")

        # Ensure non-negative for financial parameters
        sampled[param] = max(0, sampled_value)

    return sampled


def calculate_value_at_risk(
    distribution: np.ndarray,
    confidence_level: float = 0.95
) -> float:
    """
    Calculate Value at Risk (VaR) from distribution.

    Args:
        distribution: Array of simulation results
        confidence_level: Confidence level (e.g., 0.95 for 95%)

    Returns:
        VaR value

    Examples:
        >>> dist = np.random.normal(10000, 2000, 10000)
        >>> var = calculate_value_at_risk(dist, 0.95)
        >>> print(f"95% VaR: {var:.2f}")
    """
    percentile = (1 - confidence_level) * 100
    var = np.percentile(distribution, percentile)

    logger.info(f"Value at Risk ({confidence_level:.0%}): {var:.2f}")

    return float(var)


def calculate_conditional_value_at_risk(
    distribution: np.ndarray,
    confidence_level: float = 0.95
) -> float:
    """
    Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

    CVaR is the expected value of losses beyond the VaR threshold.

    Args:
        distribution: Array of simulation results
        confidence_level: Confidence level

    Returns:
        CVaR value

    Examples:
        >>> dist = np.random.normal(10000, 2000, 10000)
        >>> cvar = calculate_conditional_value_at_risk(dist, 0.95)
    """
    var = calculate_value_at_risk(distribution, confidence_level)

    # Get all values below VaR (worst outcomes)
    tail_losses = distribution[distribution <= var]

    # Calculate average of tail losses
    cvar = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var

    logger.info(f"Conditional VaR ({confidence_level:.0%}): {cvar:.2f}")

    return cvar


def optimize_portfolio_allocation(
    assets: List[str],
    expected_returns: List[float],
    volatilities: List[float],
    correlations: Optional[np.ndarray] = None,
    iterations: int = 10000
) -> Dict[str, Any]:
    """
    Use Monte Carlo to find optimal portfolio allocation.

    Args:
        assets: List of asset names
        expected_returns: Expected return for each asset
        volatilities: Volatility for each asset
        correlations: Correlation matrix (optional)
        iterations: Number of simulations

    Returns:
        Dictionary with optimal allocation

    Examples:
        >>> result = optimize_portfolio_allocation(
        ...     ['Stocks', 'Bonds'],
        ...     [0.10, 0.05],
        ...     [0.20, 0.08]
        ... )
    """
    n_assets = len(assets)

    if correlations is None:
        # Use identity matrix (no correlations)
        correlations = np.eye(n_assets)

    best_sharpe = -float('inf')
    best_allocation = None
    best_return = 0
    best_risk = 0

    for _ in range(iterations):
        # Generate random allocation
        weights = np.random.random(n_assets)
        weights /= np.sum(weights)  # Normalize to sum to 1

        # Calculate portfolio return
        portfolio_return = np.dot(weights, expected_returns)

        # Calculate portfolio risk (simplified)
        portfolio_risk = np.sqrt(np.dot(weights ** 2, np.array(volatilities) ** 2))

        # Calculate Sharpe ratio (assuming risk-free rate = 0)
        sharpe = portfolio_return / portfolio_risk if portfolio_risk > 0 else 0

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_allocation = weights
            best_return = portfolio_return
            best_risk = portfolio_risk

    allocation_dict = {asset: float(weight) for asset, weight in zip(assets, best_allocation)}

    result = {
        'optimal_allocation': allocation_dict,
        'expected_return': round(best_return, 4),
        'expected_risk': round(best_risk, 4),
        'sharpe_ratio': round(best_sharpe, 4)
    }

    logger.info(f"Optimal allocation found: Sharpe={best_sharpe:.4f}, Return={best_return:.2%}, Risk={best_risk:.2%}")

    return result
