"""
Date Parser and Normalizer

Extracts and normalizes dates from financial documents.
Handles multiple date formats and resolves ambiguities.

Examples:
    >>> parse_date("15/03/2024")
    datetime(2024, 3, 15)

    >>> parse_date("2024-03-15")
    datetime(2024, 3, 15)

    >>> parse_relative_date("Q1 2024")
    datetime(2024, 3, 31)
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


def parse_date(
    text: str,
    prefer_european: bool = True,
    default_year: Optional[int] = None
) -> Optional[datetime]:
    """
    Parse messy date string to datetime object.

    Supports multiple formats:
    - DD/MM/YYYY or MM/DD/YYYY (ambiguity resolved by prefer_european)
    - YYYY-MM-DD (ISO format)
    - DD.MM.YYYY
    - DD-MM-YYYY
    - Month DD, YYYY (e.g., "March 15, 2024")
    - DD Month YYYY (e.g., "15 mars 2024")

    Args:
        text: String containing date
        prefer_european: If True, interpret DD/MM/YYYY; else MM/DD/YYYY
        default_year: Year to use for partial dates (default: current year)

    Returns:
        Parsed datetime object, or None if parsing fails

    Examples:
        >>> parse_date("15/03/2024", prefer_european=True)
        datetime(2024, 3, 15, 0, 0)
        >>> parse_date("03/15/2024", prefer_european=False)
        datetime(2024, 3, 15, 0, 0)
        >>> parse_date("2024-03-15")
        datetime(2024, 3, 15, 0, 0)
    """
    if not text or not isinstance(text, str):
        return None

    # Clean the input
    text = text.strip()

    if not default_year:
        default_year = datetime.now().year

    # Try different date formats in order of specificity
    formats_to_try = [
        # ISO format (unambiguous)
        ('%Y-%m-%d', r'^\d{4}-\d{2}-\d{2}$'),
        ('%Y/%m/%d', r'^\d{4}/\d{2}/\d{2}$'),

        # Dotted formats
        ('%d.%m.%Y', r'^\d{2}\.\d{2}\.\d{4}$'),
        ('%d.%m.%y', r'^\d{2}\.\d{2}\.\d{2}$'),

        # Slashed formats with 4-digit year
        ('%d/%m/%Y', r'^\d{2}/\d{2}/\d{4}$'),  # European
        ('%m/%d/%Y', r'^\d{2}/\d{2}/\d{4}$'),  # American

        # Dashed formats
        ('%d-%m-%Y', r'^\d{2}-\d{2}-\d{4}$'),
        ('%d-%m-%y', r'^\d{2}-\d{2}-\d{2}$'),

        # Written month formats (English)
        ('%B %d, %Y', r'^\w+ \d{1,2}, \d{4}$'),  # March 15, 2024
        ('%d %B %Y', r'^\d{1,2} \w+ \d{4}$'),    # 15 March 2024
        ('%b %d, %Y', r'^\w+ \d{1,2}, \d{4}$'),  # Mar 15, 2024
        ('%d %b %Y', r'^\d{1,2} \w+ \d{4}$'),    # 15 Mar 2024

        # Written month formats (French)
        # These require special handling due to accents
    ]

    # Try ISO format first (unambiguous)
    for fmt, pattern in formats_to_try[:2]:
        if re.match(pattern, text):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass

    # Try dotted format (European convention)
    for fmt, pattern in formats_to_try[2:4]:
        if re.match(pattern, text):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass

    # Try slashed formats (ambiguous)
    if re.match(r'^\d{2}/\d{2}/\d{4}$', text):
        parts = text.split('/')
        try:
            if prefer_european:
                # DD/MM/YYYY
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                # MM/DD/YYYY
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])

            # Validate day and month ranges
            if 1 <= day <= 31 and 1 <= month <= 12:
                return datetime(year, month, day)
            elif 1 <= month <= 31 and 1 <= day <= 12:
                # Swap if out of range
                return datetime(year, day, month)
        except ValueError:
            pass

    # Try dashed formats
    for fmt, pattern in formats_to_try[6:8]:
        if re.match(pattern, text):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass

    # Try written month formats
    for fmt, pattern in formats_to_try[8:]:
        if re.match(pattern, text, re.IGNORECASE):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass

    # Try French month names
    french_months = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12,
        'janv': 1, 'févr': 2, 'avr': 4, 'juil': 7,
        'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12
    }

    text_lower = text.lower()
    for month_name, month_num in french_months.items():
        if month_name in text_lower:
            # Extract day and year
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                day = int(numbers[0])
                year = int(numbers[1]) if len(numbers[1]) == 4 else int(numbers[1]) + 2000
                try:
                    return datetime(year, month_num, day)
                except ValueError:
                    pass

    logger.warning(f"Could not parse date: '{text}'")
    return None


def parse_relative_date(text: str) -> Optional[datetime]:
    """
    Parse relative date expressions.

    Handles:
    - Q1 2024, Q2 2024, etc. (quarters)
    - H1 2024, H2 2024 (half-years)
    - "30 days net" → 30 days from now
    - "net 30" → 30 days from now
    - "end of month", "end of year"

    Args:
        text: Text containing relative date

    Returns:
        Parsed datetime object, or None if parsing fails

    Examples:
        >>> parse_relative_date("Q1 2024")
        datetime(2024, 3, 31, 0, 0)
        >>> parse_relative_date("H2 2024")
        datetime(2024, 12, 31, 0, 0)
    """
    if not text:
        return None

    text_lower = text.lower().strip()

    # Quarter patterns (Q1, Q2, Q3, Q4)
    quarter_match = re.search(r'q([1-4])\s*(\d{4})', text_lower)
    if quarter_match:
        quarter = int(quarter_match.group(1))
        year = int(quarter_match.group(2))

        # Last day of quarter
        quarter_end_month = quarter * 3
        if quarter_end_month == 3:
            return datetime(year, 3, 31)
        elif quarter_end_month == 6:
            return datetime(year, 6, 30)
        elif quarter_end_month == 9:
            return datetime(year, 9, 30)
        else:  # quarter_end_month == 12
            return datetime(year, 12, 31)

    # Half-year patterns (H1, H2)
    half_year_match = re.search(r'h([12])\s*(\d{4})', text_lower)
    if half_year_match:
        half = int(half_year_match.group(1))
        year = int(half_year_match.group(2))

        if half == 1:
            return datetime(year, 6, 30)
        else:
            return datetime(year, 12, 31)

    # Net payment terms (e.g., "30 days net", "net 30")
    net_match = re.search(r'(?:net\s*)?(\d+)\s*(?:days?|jours?)?(?:\s*net)?', text_lower)
    if net_match and ('net' in text_lower or 'days' in text_lower or 'jours' in text_lower):
        days = int(net_match.group(1))
        return datetime.now() + timedelta(days=days)

    # End of month
    if 'end of month' in text_lower or 'fin de mois' in text_lower or 'eom' in text_lower:
        now = datetime.now()
        # Get last day of current month
        if now.month == 12:
            return datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            return datetime(now.year, now.month + 1, 1) - timedelta(days=1)

    # End of year
    if 'end of year' in text_lower or 'fin d\'année' in text_lower or 'eoy' in text_lower:
        return datetime(datetime.now().year, 12, 31)

    return None


def extract_dates_from_text(text: str, prefer_european: bool = True) -> List[datetime]:
    """
    Extract all dates from text.

    Args:
        text: Text containing dates
        prefer_european: Prefer European date format (DD/MM/YYYY)

    Returns:
        List of extracted datetime objects

    Examples:
        >>> extract_dates_from_text("Invoice dated 15/03/2024, due 15/04/2024")
        [datetime(2024, 3, 15, 0, 0), datetime(2024, 4, 15, 0, 0)]
    """
    if not text:
        return []

    dates = []

    # Pattern to match common date formats
    patterns = [
        r'\d{4}-\d{2}-\d{2}',      # ISO format
        r'\d{2}/\d{2}/\d{4}',      # Slashed
        r'\d{2}\.\d{2}\.\d{4}',    # Dotted
        r'\d{2}-\d{2}-\d{4}',      # Dashed
        r'\w+ \d{1,2}, \d{4}',     # Month DD, YYYY
        r'\d{1,2} \w+ \d{4}',      # DD Month YYYY
    ]

    combined_pattern = '|'.join(f'({p})' for p in patterns)
    matches = re.findall(combined_pattern, text)

    for match in matches:
        # match is a tuple of groups, find the non-empty one
        date_str = next((m for m in match if m), None)
        if date_str:
            parsed = parse_date(date_str, prefer_european=prefer_european)
            if parsed:
                dates.append(parsed)

    return dates


def validate_date_sequence(start_date: datetime, end_date: datetime) -> bool:
    """
    Validate that start_date comes before end_date.

    Args:
        start_date: Starting date
        end_date: Ending date

    Returns:
        True if sequence is valid, False otherwise

    Examples:
        >>> validate_date_sequence(datetime(2024, 1, 1), datetime(2024, 12, 31))
        True
        >>> validate_date_sequence(datetime(2024, 12, 31), datetime(2024, 1, 1))
        False
    """
    return start_date < end_date


def calculate_days_between(start_date: datetime, end_date: datetime) -> int:
    """
    Calculate number of days between two dates.

    Args:
        start_date: Starting date
        end_date: Ending date

    Returns:
        Number of days (can be negative if end_date < start_date)

    Examples:
        >>> calculate_days_between(datetime(2024, 1, 1), datetime(2024, 1, 31))
        30
    """
    delta = end_date - start_date
    return delta.days


def is_overdue(due_date: datetime, reference_date: Optional[datetime] = None) -> bool:
    """
    Check if a date is overdue.

    Args:
        due_date: Due date to check
        reference_date: Reference date (default: now)

    Returns:
        True if overdue, False otherwise

    Examples:
        >>> is_overdue(datetime(2024, 1, 1), datetime(2024, 1, 15))
        True
    """
    if not reference_date:
        reference_date = datetime.now()

    return due_date < reference_date


def calculate_payment_delay(
    invoice_date: datetime,
    payment_date: datetime,
    payment_terms_days: int = 30
) -> Tuple[int, bool]:
    """
    Calculate payment delay relative to terms.

    Args:
        invoice_date: Invoice issue date
        payment_date: Actual payment date
        payment_terms_days: Payment terms in days (default: 30)

    Returns:
        Tuple of (delay_in_days, is_late)

    Examples:
        >>> calculate_payment_delay(datetime(2024, 1, 1), datetime(2024, 2, 15), 30)
        (15, True)  # 15 days late
        >>> calculate_payment_delay(datetime(2024, 1, 1), datetime(2024, 1, 20), 30)
        (-11, False)  # 11 days early (due Jan 31, paid Jan 20)
    """
    due_date = invoice_date + timedelta(days=payment_terms_days)
    delay = (payment_date - due_date).days
    is_late = delay > 0

    return delay, is_late


def format_date(dt: datetime, format_type: str = 'iso') -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime object to format
        format_type: Format type ('iso', 'european', 'american', 'french')

    Returns:
        Formatted date string

    Examples:
        >>> format_date(datetime(2024, 3, 15), 'iso')
        '2024-03-15'
        >>> format_date(datetime(2024, 3, 15), 'european')
        '15/03/2024'
        >>> format_date(datetime(2024, 3, 15), 'american')
        '03/15/2024'
    """
    if format_type == 'iso':
        return dt.strftime('%Y-%m-%d')
    elif format_type == 'european':
        return dt.strftime('%d/%m/%Y')
    elif format_type == 'american':
        return dt.strftime('%m/%d/%Y')
    elif format_type == 'french':
        # Format: 15 mars 2024
        french_months = [
            'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
            'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
        ]
        return f"{dt.day} {french_months[dt.month - 1]} {dt.year}"
    else:
        return dt.isoformat()


def get_quarter(dt: datetime) -> int:
    """
    Get quarter number (1-4) for a given date.

    Args:
        dt: Datetime object

    Returns:
        Quarter number (1, 2, 3, or 4)

    Examples:
        >>> get_quarter(datetime(2024, 3, 15))
        1
        >>> get_quarter(datetime(2024, 7, 1))
        3
    """
    return (dt.month - 1) // 3 + 1


def get_fiscal_year(dt: datetime, fiscal_year_start_month: int = 1) -> int:
    """
    Get fiscal year for a given date.

    Args:
        dt: Datetime object
        fiscal_year_start_month: Month when fiscal year starts (1-12)

    Returns:
        Fiscal year

    Examples:
        >>> get_fiscal_year(datetime(2024, 3, 15), fiscal_year_start_month=1)
        2024
        >>> get_fiscal_year(datetime(2024, 3, 15), fiscal_year_start_month=4)
        2023
    """
    if dt.month >= fiscal_year_start_month:
        return dt.year
    else:
        return dt.year - 1
