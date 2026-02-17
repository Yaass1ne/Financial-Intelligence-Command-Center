"""
Financial Amount Parser

Extracts and normalizes monetary amounts from financial documents.
Handles multiple formats, currencies, and tax calculations.

Examples:
    >>> parse_amount("1,250.50 EUR")
    1250.50

    >>> parse_amount("1.250,50 €")
    1250.50

    >>> detect_currency("Total: $1,500.00")
    'USD'

    >>> parse_tax_rate("TVA 20%")
    0.20
"""

import re
from typing import Optional, Dict, Tuple
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


# Currency symbol mappings
CURRENCY_SYMBOLS = {
    '€': 'EUR',
    '$': 'USD',
    '£': 'GBP',
    '¥': 'JPY',
    'Fr': 'CHF',
}

# Currency code patterns
CURRENCY_CODES = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'CNY']


def parse_amount(text: str) -> Optional[float]:
    """
    Parse messy amount string to float.

    Handles various formats:
    - European: 1.250,50 (thousands: dot, decimal: comma)
    - American: 1,250.50 (thousands: comma, decimal: dot)
    - Simple: 1250.50 or 1250,50
    - With currency: $1,250.50 or 1.250,50 EUR

    Args:
        text: String containing monetary amount

    Returns:
        Parsed amount as float, or None if parsing fails

    Examples:
        >>> parse_amount("1,250.50")
        1250.5
        >>> parse_amount("1.250,50")
        1250.5
        >>> parse_amount("€ 1 250,50")
        1250.5
    """
    if not text or not isinstance(text, str):
        return None

    # Remove currency symbols and codes
    cleaned = text.strip()
    for symbol in CURRENCY_SYMBOLS.keys():
        cleaned = cleaned.replace(symbol, '')
    for code in CURRENCY_CODES:
        cleaned = cleaned.replace(code, '')

    # Remove whitespace
    cleaned = cleaned.strip()

    # Remove any non-numeric characters except dots, commas, and minus
    cleaned = re.sub(r'[^\d.,-]', '', cleaned)

    if not cleaned:
        return None

    try:
        # Determine format based on separators
        has_dot = '.' in cleaned
        has_comma = ',' in cleaned

        if has_dot and has_comma:
            # Both separators present - determine which is decimal
            last_dot = cleaned.rfind('.')
            last_comma = cleaned.rfind(',')

            if last_dot > last_comma:
                # Dot is decimal separator (American format: 1,250.50)
                cleaned = cleaned.replace(',', '')
            else:
                # Comma is decimal separator (European format: 1.250,50)
                cleaned = cleaned.replace('.', '').replace(',', '.')

        elif has_comma:
            # Only comma - check if it's decimal or thousands separator
            comma_parts = cleaned.split(',')
            if len(comma_parts) == 2 and len(comma_parts[1]) == 2:
                # Likely decimal separator (e.g., 1250,50)
                cleaned = cleaned.replace(',', '.')
            elif len(comma_parts) == 2 and len(comma_parts[1]) == 3:
                # Could be thousands separator (e.g., 1,250)
                cleaned = cleaned.replace(',', '')
            else:
                # Assume decimal separator
                cleaned = cleaned.replace(',', '.')

        # Try to convert to float
        amount = float(cleaned)
        return round(amount, 2)

    except (ValueError, InvalidOperation) as e:
        logger.warning(f"Could not parse amount '{text}': {e}")
        return None


def detect_currency(text: str) -> str:
    """
    Detect currency from text.

    Looks for currency symbols and ISO codes.

    Args:
        text: Text containing currency information

    Returns:
        ISO currency code (EUR, USD, etc.) or 'UNKNOWN'

    Examples:
        >>> detect_currency("Total: $1,500.00")
        'USD'
        >>> detect_currency("1.250,50 EUR")
        'EUR'
    """
    if not text:
        return 'UNKNOWN'

    # Check for currency symbols
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code

    # Check for currency codes
    text_upper = text.upper()
    for code in CURRENCY_CODES:
        if code in text_upper:
            return code

    # Default to EUR for European context
    return 'EUR'


def parse_tax_rate(text: str) -> Optional[float]:
    """
    Parse tax rate from text.

    Handles formats like:
    - TVA 20%
    - VAT 5.5%
    - Tax: 19.6%

    Args:
        text: Text containing tax rate

    Returns:
        Tax rate as decimal (0.20 for 20%), or None if not found

    Examples:
        >>> parse_tax_rate("TVA 20%")
        0.2
        >>> parse_tax_rate("VAT 5.5%")
        0.055
    """
    if not text:
        return None

    # Pattern to match percentage values
    pattern = r'(\d+\.?\d*)\s*%'
    match = re.search(pattern, text)

    if match:
        try:
            rate = float(match.group(1)) / 100
            return round(rate, 4)
        except ValueError:
            return None

    return None


def calculate_total_with_tax(amount_ht: float, tax_rate: float) -> float:
    """
    Calculate total amount including tax (HT → TTC).

    Args:
        amount_ht: Amount excluding tax (Hors Taxe)
        tax_rate: Tax rate as decimal (e.g., 0.20 for 20%)

    Returns:
        Total amount including tax (Toutes Taxes Comprises)

    Examples:
        >>> calculate_total_with_tax(100.0, 0.20)
        120.0
    """
    total = amount_ht * (1 + tax_rate)
    return round(total, 2)


def calculate_amount_without_tax(amount_ttc: float, tax_rate: float) -> float:
    """
    Calculate amount excluding tax (TTC → HT).

    Args:
        amount_ttc: Amount including tax (Toutes Taxes Comprises)
        tax_rate: Tax rate as decimal (e.g., 0.20 for 20%)

    Returns:
        Amount excluding tax (Hors Taxe)

    Examples:
        >>> calculate_amount_without_tax(120.0, 0.20)
        100.0
    """
    amount_ht = amount_ttc / (1 + tax_rate)
    return round(amount_ht, 2)


def extract_amounts_from_text(text: str) -> Dict[str, Optional[float]]:
    """
    Extract all amount-related information from text.

    Looks for:
    - Amount HT (excluding tax)
    - Amount TTC (including tax)
    - Tax rate
    - Currency

    Args:
        text: Text containing financial information

    Returns:
        Dictionary with extracted amounts and metadata

    Examples:
        >>> extract_amounts_from_text("Total HT: 1,000.00 EUR, TVA 20%, Total TTC: 1,200.00 EUR")
        {'amount_ht': 1000.0, 'amount_ttc': 1200.0, 'tax_rate': 0.2, 'currency': 'EUR'}
    """
    result = {
        'amount_ht': None,
        'amount_ttc': None,
        'tax_rate': None,
        'tax_amount': None,
        'currency': 'EUR'
    }

    # Detect currency
    result['currency'] = detect_currency(text)

    # Extract tax rate
    result['tax_rate'] = parse_tax_rate(text)

    # Pattern for amount HT (Hors Taxe / Excluding Tax)
    ht_patterns = [
        r'(?:montant\s+)?HT\s*:?\s*([\d.,\s€$£]+)',
        r'(?:total\s+)?HT\s*:?\s*([\d.,\s€$£]+)',
        r'net\s*:?\s*([\d.,\s€$£]+)',
    ]

    for pattern in ht_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['amount_ht'] = parse_amount(match.group(1))
            break

    # Pattern for amount TTC (Toutes Taxes Comprises / Including Tax)
    ttc_patterns = [
        r'(?:montant\s+)?TTC\s*:?\s*([\d.,\s€$£]+)',
        r'(?:total\s+)?TTC\s*:?\s*([\d.,\s€$£]+)',
        r'total\s*:?\s*([\d.,\s€$£]+)',
        r'amount\s*due\s*:?\s*([\d.,\s€$£]+)',
    ]

    for pattern in ttc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['amount_ttc'] = parse_amount(match.group(1))
            break

    # Pattern for tax amount
    tax_patterns = [
        r'(?:montant\s+)?TVA\s*:?\s*([\d.,\s€$£]+)',
        r'(?:montant\s+)?VAT\s*:?\s*([\d.,\s€$£]+)',
        r'tax\s*amount\s*:?\s*([\d.,\s€$£]+)',
    ]

    for pattern in tax_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['tax_amount'] = parse_amount(match.group(1))
            break

    # Calculate missing values if possible
    if result['amount_ht'] and result['tax_rate'] and not result['amount_ttc']:
        result['amount_ttc'] = calculate_total_with_tax(result['amount_ht'], result['tax_rate'])

    if result['amount_ttc'] and result['tax_rate'] and not result['amount_ht']:
        result['amount_ht'] = calculate_amount_without_tax(result['amount_ttc'], result['tax_rate'])

    if result['amount_ht'] and result['amount_ttc'] and not result['tax_amount']:
        result['tax_amount'] = round(result['amount_ttc'] - result['amount_ht'], 2)

    return result


def normalize_amount_format(amount: float, currency: str = 'EUR', locale: str = 'fr') -> str:
    """
    Format amount according to locale conventions.

    Args:
        amount: Amount to format
        currency: ISO currency code
        locale: Locale ('fr' for French, 'en' for English)

    Returns:
        Formatted amount string

    Examples:
        >>> normalize_amount_format(1250.50, 'EUR', 'fr')
        '1 250,50 €'
        >>> normalize_amount_format(1250.50, 'USD', 'en')
        '$1,250.50'
    """
    if locale == 'fr':
        # French format: 1 250,50 €
        formatted = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
        symbol = CURRENCY_SYMBOLS.get(currency, currency) if currency in ['EUR', 'USD', 'GBP'] else currency
        return f"{formatted} {symbol}"
    else:
        # English format: $1,250.50
        formatted = f"{amount:,.2f}"
        if currency == 'EUR':
            return f"€{formatted}"
        elif currency == 'USD':
            return f"${formatted}"
        elif currency == 'GBP':
            return f"£{formatted}"
        else:
            return f"{formatted} {currency}"
