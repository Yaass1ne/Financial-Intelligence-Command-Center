"""
Data Validators

Validates financial document data quality and detects duplicates.

Examples:
    >>> result = validate_invoice(invoice_data)
    >>> if not result.is_valid:
    ...     print(result.errors)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        parts = [f"Validation: {status}"]

        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
            for error in self.errors:
                parts.append(f"  - {error}")

        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                parts.append(f"  - {warning}")

        return "\n".join(parts)


def validate_invoice(invoice: Dict[str, Any]) -> ValidationResult:
    """
    Validate invoice data quality.

    Checks:
    - Required fields are present
    - Amounts are positive and consistent
    - Dates are valid and in correct sequence
    - Vendor and client information exists

    Args:
        invoice: Invoice dictionary

    Returns:
        ValidationResult with errors and warnings

    Examples:
        >>> invoice = {'invoice_id': 'INV-001', 'total_ttc': -100}
        >>> result = validate_invoice(invoice)
        >>> print(result.is_valid)
        False
    """
    result = ValidationResult(is_valid=True)

    # Check required fields
    required_fields = ['invoice_id', 'vendor', 'total_ttc']
    for field in required_fields:
        if field not in invoice or invoice[field] is None:
            result.add_error(f"Missing required field: {field}")

    # Validate invoice ID format
    if 'invoice_id' in invoice and invoice['invoice_id']:
        invoice_id = invoice['invoice_id']
        if len(str(invoice_id)) < 3:
            result.add_warning(f"Invoice ID '{invoice_id}' seems too short")

    # Validate amounts
    if 'total_ttc' in invoice and invoice['total_ttc'] is not None:
        if invoice['total_ttc'] < 0:
            result.add_error(f"Total TTC cannot be negative: {invoice['total_ttc']}")
        elif invoice['total_ttc'] == 0:
            result.add_warning("Total TTC is zero")

    if 'total_ht' in invoice and invoice['total_ht'] is not None:
        if invoice['total_ht'] < 0:
            result.add_error(f"Total HT cannot be negative: {invoice['total_ht']}")

    # Validate amount consistency
    if all(k in invoice and invoice[k] is not None for k in ['total_ht', 'tax_rate', 'total_ttc']):
        expected_ttc = round(invoice['total_ht'] * (1 + invoice['tax_rate']), 2)
        actual_ttc = round(invoice['total_ttc'], 2)

        if abs(expected_ttc - actual_ttc) > 0.1:  # Allow 0.1 rounding error
            result.add_warning(
                f"Amount inconsistency: HT={invoice['total_ht']} * (1+{invoice['tax_rate']}) "
                f"should equal {expected_ttc}, but TTC={actual_ttc}"
            )

    # Validate tax rate
    if 'tax_rate' in invoice and invoice['tax_rate'] is not None:
        tax_rate = invoice['tax_rate']
        if tax_rate < 0 or tax_rate > 1:
            result.add_error(f"Tax rate should be between 0 and 1 (got {tax_rate})")

        # Common VAT rates in Europe
        common_rates = [0.0, 0.055, 0.10, 0.20, 0.21]
        if not any(abs(tax_rate - rate) < 0.001 for rate in common_rates):
            result.add_warning(f"Unusual tax rate: {tax_rate} (expected one of {common_rates})")

    # Validate dates
    if 'date' in invoice and 'due_date' in invoice:
        if invoice['date'] and invoice['due_date']:
            if isinstance(invoice['date'], datetime) and isinstance(invoice['due_date'], datetime):
                if invoice['due_date'] < invoice['date']:
                    result.add_error(
                        f"Due date ({invoice['due_date']}) cannot be before invoice date ({invoice['date']})"
                    )

    # Validate vendor information
    if 'vendor' in invoice:
        vendor = invoice['vendor']
        if isinstance(vendor, dict):
            if not vendor.get('name'):
                result.add_error("Vendor name is missing")
        elif not vendor:
            result.add_error("Vendor information is missing")

    # Validate client information
    if 'client' in invoice:
        client = invoice['client']
        if isinstance(client, dict):
            if not client.get('name'):
                result.add_warning("Client name is missing")

    # Validate line items
    if 'items' in invoice and invoice['items']:
        for i, item in enumerate(invoice['items']):
            if not item.get('description'):
                result.add_warning(f"Line item {i+1} missing description")

            if 'quantity' in item and item['quantity'] is not None:
                if item['quantity'] <= 0:
                    result.add_warning(f"Line item {i+1} has invalid quantity: {item['quantity']}")

            if 'unit_price' in item and item['unit_price'] is not None:
                if item['unit_price'] < 0:
                    result.add_warning(f"Line item {i+1} has negative unit price: {item['unit_price']}")

    result.info['document_type'] = invoice.get('document_type', 'invoice')
    result.info['invoice_id'] = invoice.get('invoice_id')

    return result


def validate_contract(contract: Dict[str, Any]) -> ValidationResult:
    """
    Validate contract data quality.

    Args:
        contract: Contract dictionary

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(is_valid=True)

    # Required fields
    required_fields = ['contract_id', 'title', 'start_date', 'parties']
    for field in required_fields:
        if field not in contract or contract[field] is None:
            result.add_error(f"Missing required field: {field}")

    # Validate date sequence
    if 'start_date' in contract and 'end_date' in contract:
        if contract['start_date'] and contract['end_date']:
            if isinstance(contract['start_date'], datetime) and isinstance(contract['end_date'], datetime):
                if contract['end_date'] < contract['start_date']:
                    result.add_error(
                        f"End date ({contract['end_date']}) cannot be before start date ({contract['start_date']})"
                    )

    # Validate amount
    if 'amount' in contract and contract['amount'] is not None:
        if contract['amount'] < 0:
            result.add_error(f"Contract amount cannot be negative: {contract['amount']}")
        elif contract['amount'] == 0:
            result.add_warning("Contract amount is zero")

    # Validate parties
    if 'parties' in contract:
        parties = contract['parties']
        if not parties:
            result.add_error("Contract must have at least one party")
        elif len(parties) < 2:
            result.add_warning("Contract typically has at least two parties")

        # Check party roles
        if isinstance(parties, list):
            roles = [p.get('role') for p in parties if isinstance(p, dict)]
            if roles and all(r == 'UNKNOWN' for r in roles):
                result.add_warning("No party roles identified")

    result.info['document_type'] = contract.get('document_type', 'contract')
    result.info['contract_id'] = contract.get('contract_id')

    return result


def validate_budget(budget: Dict[str, Any]) -> ValidationResult:
    """
    Validate budget data quality.

    Args:
        budget: Budget dictionary or row

    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(is_valid=True)

    # Required fields
    required_fields = ['department', 'budget']
    for field in required_fields:
        if field not in budget or budget[field] is None:
            result.add_error(f"Missing required field: {field}")

    # Validate budget amount
    if 'budget' in budget and budget['budget'] is not None:
        if budget['budget'] < 0:
            result.add_error(f"Budget amount cannot be negative: {budget['budget']}")

    # Validate actual amount
    if 'actual' in budget and budget['actual'] is not None:
        if budget['actual'] < 0:
            result.add_warning(f"Actual amount is negative (possible refund?): {budget['actual']}")

    # Validate variance consistency
    if all(k in budget and budget[k] is not None for k in ['budget', 'actual', 'variance']):
        expected_variance = budget['actual'] - budget['budget']
        if abs(expected_variance - budget['variance']) > 0.01:
            result.add_error(
                f"Variance inconsistency: {budget['actual']} - {budget['budget']} = {expected_variance}, "
                f"but variance={budget['variance']}"
            )

    result.info['document_type'] = 'budget'
    result.info['department'] = budget.get('department')

    return result


def detect_duplicates(
    documents: List[Dict[str, Any]],
    threshold: float = 0.95,
    key_fields: Optional[List[str]] = None
) -> List[Tuple[int, int, float]]:
    """
    Find duplicate documents using fuzzy matching.

    Args:
        documents: List of document dictionaries
        threshold: Similarity threshold (0-1, default 0.95)
        key_fields: Fields to compare (default: vendor, amount, date)

    Returns:
        List of (index1, index2, similarity_score) tuples for duplicates

    Examples:
        >>> docs = [
        ...     {'vendor': {'name': 'ACME'}, 'total_ttc': 100, 'date': '2024-01-01'},
        ...     {'vendor': {'name': 'ACME'}, 'total_ttc': 100, 'date': '2024-01-01'}
        ... ]
        >>> duplicates = detect_duplicates(docs)
        >>> print(len(duplicates))
        1
    """
    if key_fields is None:
        key_fields = ['vendor', 'amount', 'total_ttc', 'date']

    duplicates = []

    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            similarity = _calculate_document_similarity(
                documents[i],
                documents[j],
                key_fields
            )

            if similarity >= threshold:
                duplicates.append((i, j, similarity))
                logger.info(
                    f"Found duplicate documents: #{i} and #{j} "
                    f"(similarity: {similarity:.2%})"
                )

    return duplicates


def _calculate_document_similarity(
    doc1: Dict[str, Any],
    doc2: Dict[str, Any],
    key_fields: List[str]
) -> float:
    """
    Calculate similarity between two documents.

    Args:
        doc1: First document
        doc2: Second document
        key_fields: Fields to compare

    Returns:
        Similarity score (0-1)
    """
    scores = []

    for field in key_fields:
        val1 = _get_nested_value(doc1, field)
        val2 = _get_nested_value(doc2, field)

        if val1 is None or val2 is None:
            continue

        # Compare based on type
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # Numeric comparison (exact match or very close)
            if val1 == val2:
                scores.append(1.0)
            elif val1 == 0 or val2 == 0:
                scores.append(0.0)
            else:
                # Allow small rounding differences
                ratio = min(val1, val2) / max(val1, val2)
                scores.append(ratio if ratio > 0.99 else 0.0)

        elif isinstance(val1, datetime) and isinstance(val2, datetime):
            # Date comparison (exact match)
            scores.append(1.0 if val1 == val2 else 0.0)

        elif isinstance(val1, str) and isinstance(val2, str):
            # String comparison (fuzzy matching)
            similarity = SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
            scores.append(similarity)

        elif isinstance(val1, dict) and isinstance(val2, dict):
            # For dict values (like vendor), compare name field
            name1 = val1.get('name', '')
            name2 = val2.get('name', '')
            if name1 and name2:
                similarity = SequenceMatcher(None, str(name1).lower(), str(name2).lower()).ratio()
                scores.append(similarity)

    # Return average similarity across all compared fields
    return sum(scores) / len(scores) if scores else 0.0


def _get_nested_value(d: Dict[str, Any], key: str) -> Any:
    """
    Get value from dictionary, supporting nested keys with dot notation.

    Args:
        d: Dictionary
        key: Key (can be nested like 'vendor.name')

    Returns:
        Value or None
    """
    if '.' in key:
        keys = key.split('.')
        value = d
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    else:
        return d.get(key)


def detect_anomalies(documents: List[Dict[str, Any]], document_type: str = 'invoice') -> List[Dict[str, Any]]:
    """
    Detect anomalous values in documents.

    Args:
        documents: List of documents
        document_type: Type of document ('invoice', 'contract', 'budget')

    Returns:
        List of anomaly dictionaries

    Examples:
        >>> invoices = [
        ...     {'total_ttc': 100},
        ...     {'total_ttc': 150},
        ...     {'total_ttc': 10000}  # Anomaly
        ... ]
        >>> anomalies = detect_anomalies(invoices, 'invoice')
        >>> print(len(anomalies))
        1
    """
    anomalies = []

    if document_type == 'invoice':
        # Check for unusual amounts
        amounts = [doc.get('total_ttc') for doc in documents if doc.get('total_ttc')]
        if len(amounts) > 3:
            mean_amount = sum(amounts) / len(amounts)
            std_amount = (sum((x - mean_amount) ** 2 for x in amounts) / len(amounts)) ** 0.5

            for i, doc in enumerate(documents):
                amount = doc.get('total_ttc')
                if amount and abs(amount - mean_amount) > 3 * std_amount:
                    anomalies.append({
                        'index': i,
                        'type': 'unusual_amount',
                        'field': 'total_ttc',
                        'value': amount,
                        'message': f"Amount {amount} is unusual (mean: {mean_amount:.2f}, std: {std_amount:.2f})"
                    })

    return anomalies


def validate_date_range(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    max_days: int = 365 * 5
) -> ValidationResult:
    """
    Validate that date range is reasonable.

    Args:
        start_date: Start date
        end_date: End date
        max_days: Maximum allowed days between dates

    Returns:
        ValidationResult
    """
    result = ValidationResult(is_valid=True)

    if start_date is None and end_date is None:
        result.add_warning("Both dates are None")
        return result

    if start_date and end_date:
        if end_date < start_date:
            result.add_error(f"End date ({end_date}) before start date ({start_date})")

        days_diff = (end_date - start_date).days
        if days_diff > max_days:
            result.add_warning(f"Date range ({days_diff} days) exceeds maximum ({max_days} days)")
        elif days_diff < 0:
            result.add_error(f"Negative date range: {days_diff} days")

    return result


def validate_amount_range(
    amount: Optional[float],
    min_value: float = 0.0,
    max_value: Optional[float] = None
) -> ValidationResult:
    """
    Validate that amount is within acceptable range.

    Args:
        amount: Amount to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value (None for no limit)

    Returns:
        ValidationResult
    """
    result = ValidationResult(is_valid=True)

    if amount is None:
        result.add_warning("Amount is None")
        return result

    if amount < min_value:
        result.add_error(f"Amount {amount} is below minimum {min_value}")

    if max_value is not None and amount > max_value:
        result.add_warning(f"Amount {amount} exceeds maximum {max_value}")

    return result


def batch_validate(
    documents: List[Dict[str, Any]],
    document_type: str = 'invoice'
) -> Dict[str, Any]:
    """
    Validate a batch of documents and return summary.

    Args:
        documents: List of documents to validate
        document_type: Type of documents

    Returns:
        Dictionary with validation summary

    Examples:
        >>> invoices = [{'invoice_id': 'INV-001', 'total_ttc': 100, 'vendor': {'name': 'ACME'}}]
        >>> summary = batch_validate(invoices, 'invoice')
        >>> print(summary['valid_count'])
        1
    """
    results = []

    # Validate each document
    for doc in documents:
        if document_type == 'invoice':
            result = validate_invoice(doc)
        elif document_type == 'contract':
            result = validate_contract(doc)
        elif document_type == 'budget':
            result = validate_budget(doc)
        else:
            result = ValidationResult(is_valid=False)
            result.add_error(f"Unknown document type: {document_type}")

        results.append(result)

    # Calculate summary
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)

    # Detect duplicates
    duplicates = detect_duplicates(documents)

    summary = {
        'total_documents': len(documents),
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'total_errors': total_errors,
        'total_warnings': total_warnings,
        'duplicate_pairs': len(duplicates),
        'results': results,
        'duplicates': duplicates
    }

    logger.info(
        f"Validated {len(documents)} {document_type}s: "
        f"{valid_count} valid, {invalid_count} invalid, "
        f"{total_errors} errors, {total_warnings} warnings, "
        f"{len(duplicates)} duplicate pairs"
    )

    return summary
