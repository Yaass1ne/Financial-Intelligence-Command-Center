"""
JSON Document Parser

Parses invoice and contract JSON files with schema validation.
Handles missing required fields and data normalization.

Examples:
    >>> from pathlib import Path
    >>> invoice = parse_invoice_json(Path("invoice_001.json"))
    >>> contract = parse_contract_json(Path("contract_001.json"))
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.ingestion.extractors.amounts import parse_amount, detect_currency
from src.ingestion.extractors.dates import parse_date

logger = logging.getLogger(__name__)


class JSONParseError(Exception):
    """Exception raised when JSON parsing fails."""
    pass


def parse_invoice_json(json_path: Path) -> Dict[str, Any]:
    """
    Parse invoice JSON file into structured data.

    Expected schema (with some flexibility):
    {
        "invoice_id": str,
        "date": str,
        "due_date": str,
        "vendor": {
            "name": str,
            "address": str (optional),
            "siret": str (optional)
        },
        "client": {
            "name": str,
            "address": str (optional)
        },
        "items": [
            {
                "description": str,
                "quantity": float,
                "unit_price": float,
                "total": float
            }
        ],
        "total_ht": float,
        "tax_rate": float,
        "tax_amount": float,
        "total_ttc": float,
        "currency": str (optional, default: EUR)
    }

    Args:
        json_path: Path to JSON file

    Returns:
        Normalized invoice dictionary

    Raises:
        JSONParseError: If required fields are missing or JSON is invalid

    Examples:
        >>> invoice = parse_invoice_json(Path("data/invoices/inv_001.json"))
        >>> print(invoice['invoice_id'])
        'INV-2024-0001'
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Invalid JSON in {json_path}: {e}")
    except FileNotFoundError:
        raise JSONParseError(f"File not found: {json_path}")
    except Exception as e:
        raise JSONParseError(f"Error reading {json_path}: {e}")

    # Validate and normalize invoice data
    normalized = {
        'source_file': str(json_path),
        'document_type': 'invoice'
    }

    # Required fields
    try:
        normalized['invoice_id'] = str(data['invoice_id'])
    except KeyError:
        # Try alternative field names
        normalized['invoice_id'] = data.get('id') or data.get('number') or f"UNKNOWN_{json_path.stem}"
        logger.warning(f"Missing invoice_id in {json_path}, using: {normalized['invoice_id']}")

    # Parse dates
    normalized['date'] = _parse_date_field(data, ['date', 'invoice_date', 'issue_date'], json_path)
    normalized['due_date'] = _parse_date_field(data, ['due_date', 'payment_due', 'deadline'], json_path)

    # Parse vendor/supplier information
    vendor = data.get('vendor') or data.get('supplier') or data.get('from') or {}
    if isinstance(vendor, str):
        # Vendor is just a name string
        normalized['vendor'] = {
            'name': vendor,
            'address': None,
            'siret': None,
            'vat_number': None
        }
    else:
        normalized['vendor'] = {
            'name': vendor.get('name') or vendor.get('company_name') or 'UNKNOWN',
            'address': vendor.get('address'),
            'siret': vendor.get('siret') or vendor.get('company_id'),
            'vat_number': vendor.get('vat_number') or vendor.get('tva')
        }

    # Parse client information
    client = data.get('client') or data.get('customer') or data.get('to') or {}
    if isinstance(client, str):
        normalized['client'] = {
            'name': client,
            'address': None
        }
    else:
        normalized['client'] = {
            'name': client.get('name') or client.get('company_name') or 'UNKNOWN',
            'address': client.get('address')
        }

    # Parse line items
    items = data.get('items') or data.get('lines') or data.get('line_items') or []
    normalized['items'] = []
    for item in items:
        normalized_item = {
            'description': item.get('description') or item.get('label') or 'NO DESCRIPTION',
            'quantity': _parse_numeric_field(item, ['quantity', 'qty'], default=1.0),
            'unit_price': _parse_numeric_field(item, ['unit_price', 'price', 'rate']),
            'total': _parse_numeric_field(item, ['total', 'amount', 'subtotal'])
        }
        # Calculate total if missing
        if normalized_item['total'] is None and normalized_item['unit_price'] is not None:
            normalized_item['total'] = normalized_item['quantity'] * normalized_item['unit_price']

        normalized['items'].append(normalized_item)

    # Parse amounts
    normalized['total_ht'] = _parse_numeric_field(
        data,
        ['total_ht', 'subtotal', 'amount_ht', 'net_amount', 'total_before_tax']
    )
    normalized['tax_rate'] = _parse_numeric_field(
        data,
        ['tax_rate', 'vat_rate', 'tva_rate'],
        transform=lambda x: x / 100 if x > 1 else x  # Convert percentage to decimal if needed
    )
    normalized['tax_amount'] = _parse_numeric_field(
        data,
        ['tax_amount', 'vat_amount', 'tva_amount', 'tax']
    )
    normalized['total_ttc'] = _parse_numeric_field(
        data,
        ['total_ttc', 'total', 'amount_ttc', 'total_amount', 'amount_due', 'grand_total']
    )

    # Detect currency
    currency = data.get('currency') or data.get('devise')
    if currency:
        normalized['currency'] = currency.upper()
    else:
        # Try to detect from amounts
        amount_text = str(data.get('total_ttc', ''))
        normalized['currency'] = detect_currency(amount_text)

    # Calculate missing values if possible
    if normalized['total_ht'] and normalized['tax_rate'] and not normalized['total_ttc']:
        normalized['total_ttc'] = round(normalized['total_ht'] * (1 + normalized['tax_rate']), 2)

    if normalized['total_ttc'] and normalized['tax_rate'] and not normalized['total_ht']:
        normalized['total_ht'] = round(normalized['total_ttc'] / (1 + normalized['tax_rate']), 2)

    if normalized['total_ht'] and normalized['total_ttc'] and not normalized['tax_amount']:
        normalized['tax_amount'] = round(normalized['total_ttc'] - normalized['total_ht'], 2)

    # Payment information (optional)
    normalized['payment_terms'] = data.get('payment_terms') or data.get('terms')
    normalized['payment_method'] = data.get('payment_method') or data.get('method')
    normalized['status'] = data.get('status', 'UNPAID').upper()

    # Additional metadata
    normalized['notes'] = data.get('notes') or data.get('comments')
    normalized['reference'] = data.get('reference') or data.get('po_number')

    logger.info(f"Parsed invoice {normalized['invoice_id']} from {json_path.name}")
    return normalized


def parse_contract_json(json_path: Path) -> Dict[str, Any]:
    """
    Parse contract JSON file into structured data.

    Expected schema:
    {
        "contract_id": str,
        "title": str,
        "start_date": str,
        "end_date": str,
        "parties": [
            {
                "name": str,
                "role": str (e.g., "client", "vendor")
            }
        ],
        "amount": float,
        "currency": str,
        "clauses": [
            {
                "type": str,
                "description": str
            }
        ],
        "auto_renew": bool,
        "renewal_notice_days": int
    }

    Args:
        json_path: Path to JSON file

    Returns:
        Normalized contract dictionary

    Raises:
        JSONParseError: If required fields are missing or JSON is invalid
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Invalid JSON in {json_path}: {e}")
    except FileNotFoundError:
        raise JSONParseError(f"File not found: {json_path}")
    except Exception as e:
        raise JSONParseError(f"Error reading {json_path}: {e}")

    # Normalize contract data
    normalized = {
        'source_file': str(json_path),
        'document_type': 'contract'
    }

    # Required fields
    normalized['contract_id'] = (
        data.get('contract_id') or
        data.get('id') or
        data.get('number') or
        f"CONTRACT_{json_path.stem}"
    )

    normalized['title'] = (
        data.get('title') or
        data.get('name') or
        data.get('description') or
        'Untitled Contract'
    )

    # Parse dates
    normalized['start_date'] = _parse_date_field(
        data,
        ['start_date', 'effective_date', 'commencement_date'],
        json_path
    )
    normalized['end_date'] = _parse_date_field(
        data,
        ['end_date', 'expiry_date', 'termination_date'],
        json_path
    )

    # Parse parties
    parties = data.get('parties') or data.get('signatories') or []
    normalized['parties'] = []
    for party in parties:
        if isinstance(party, str):
            normalized['parties'].append({
                'name': party,
                'role': 'UNKNOWN'
            })
        else:
            normalized['parties'].append({
                'name': party.get('name') or party.get('company_name') or 'UNKNOWN',
                'role': party.get('role', 'UNKNOWN').upper(),
                'address': party.get('address'),
                'representative': party.get('representative') or party.get('signatory')
            })

    # Parse financial terms
    normalized['amount'] = _parse_numeric_field(
        data,
        ['amount', 'total_amount', 'contract_value', 'value']
    )
    normalized['currency'] = (data.get('currency') or 'EUR').upper()

    # Billing information
    normalized['billing_frequency'] = data.get('billing_frequency') or data.get('payment_schedule')
    normalized['payment_terms_days'] = _parse_numeric_field(
        data,
        ['payment_terms_days', 'payment_terms', 'net_days'],
        default=30
    )

    # Parse clauses
    clauses = data.get('clauses') or data.get('terms') or []
    normalized['clauses'] = []
    for clause in clauses:
        if isinstance(clause, str):
            normalized['clauses'].append({
                'type': 'GENERAL',
                'description': clause
            })
        else:
            normalized['clauses'].append({
                'type': clause.get('type', 'GENERAL').upper(),
                'description': clause.get('description') or clause.get('text') or 'NO DESCRIPTION',
                'value': clause.get('value')
            })

    # Renewal information
    normalized['auto_renew'] = data.get('auto_renew', False)
    normalized['renewal_notice_days'] = _parse_numeric_field(
        data,
        ['renewal_notice_days', 'notice_period_days'],
        default=90
    )

    # Additional metadata
    normalized['status'] = data.get('status', 'ACTIVE').upper()
    normalized['category'] = data.get('category') or data.get('type')
    normalized['notes'] = data.get('notes') or data.get('comments')

    logger.info(f"Parsed contract {normalized['contract_id']} from {json_path.name}")
    return normalized


def parse_accounting_entry_json(json_path: Path) -> Dict[str, Any]:
    """
    Parse accounting entry JSON file.

    Expected schema:
    {
        "entry_id": str,
        "date": str,
        "description": str,
        "account_code": str,
        "debit": float,
        "credit": float,
        "category": str
    }

    Args:
        json_path: Path to JSON file

    Returns:
        Normalized accounting entry dictionary
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise JSONParseError(f"Error reading {json_path}: {e}")

    normalized = {
        'source_file': str(json_path),
        'document_type': 'accounting_entry',
        'entry_id': data.get('entry_id') or data.get('id') or f"ENTRY_{json_path.stem}",
        'date': _parse_date_field(data, ['date', 'entry_date', 'transaction_date'], json_path),
        'description': data.get('description') or data.get('label') or 'NO DESCRIPTION',
        'account_code': data.get('account_code') or data.get('account'),
        'debit': _parse_numeric_field(data, ['debit', 'debit_amount'], default=0.0),
        'credit': _parse_numeric_field(data, ['credit', 'credit_amount'], default=0.0),
        'category': data.get('category') or data.get('type'),
        'reference': data.get('reference') or data.get('document_ref'),
        'notes': data.get('notes')
    }

    return normalized


# Helper functions

def _parse_date_field(
    data: Dict[str, Any],
    field_names: List[str],
    source_file: Path
) -> Optional[datetime]:
    """
    Try to parse date from multiple possible field names.

    Args:
        data: Data dictionary
        field_names: List of possible field names to try
        source_file: Source file path (for logging)

    Returns:
        Parsed datetime or None
    """
    for field_name in field_names:
        value = data.get(field_name)
        if value:
            parsed = parse_date(str(value))
            if parsed:
                return parsed
            else:
                logger.warning(f"Could not parse date '{value}' from field '{field_name}' in {source_file.name}")

    logger.warning(f"No valid date found in fields {field_names} in {source_file.name}")
    return None


def _parse_numeric_field(
    data: Dict[str, Any],
    field_names: List[str],
    default: Optional[float] = None,
    transform=None
) -> Optional[float]:
    """
    Try to parse numeric value from multiple possible field names.

    Args:
        data: Data dictionary
        field_names: List of possible field names to try
        default: Default value if parsing fails
        transform: Optional function to transform the parsed value

    Returns:
        Parsed float or default value
    """
    for field_name in field_names:
        value = data.get(field_name)
        if value is not None:
            try:
                if isinstance(value, (int, float)):
                    result = float(value)
                else:
                    # Try to parse as amount
                    result = parse_amount(str(value))

                if result is not None:
                    if transform:
                        result = transform(result)
                    return result
            except (ValueError, TypeError):
                continue

    return default


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that required fields are present in data.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Returns:
        True if all required fields present, False otherwise
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        logger.error(f"Missing required fields: {missing_fields}")
        return False

    return True


def parse_json_batch(json_paths: List[Path], document_type: str = 'auto') -> List[Dict[str, Any]]:
    """
    Parse multiple JSON files in batch.

    Args:
        json_paths: List of paths to JSON files
        document_type: Type of document ('invoice', 'contract', 'accounting', 'auto')

    Returns:
        List of normalized dictionaries
    """
    results = []

    for json_path in json_paths:
        try:
            if document_type == 'auto':
                # Auto-detect document type from filename or content
                filename_lower = json_path.name.lower()
                if 'invoice' in filename_lower or 'facture' in filename_lower:
                    doc = parse_invoice_json(json_path)
                elif 'contract' in filename_lower or 'contrat' in filename_lower:
                    doc = parse_contract_json(json_path)
                else:
                    # Try to detect from content
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if 'invoice_id' in data or 'vendor' in data:
                        doc = parse_invoice_json(json_path)
                    elif 'contract_id' in data or 'parties' in data:
                        doc = parse_contract_json(json_path)
                    else:
                        logger.warning(f"Could not auto-detect type for {json_path.name}, skipping")
                        continue
            elif document_type == 'invoice':
                doc = parse_invoice_json(json_path)
            elif document_type == 'contract':
                doc = parse_contract_json(json_path)
            elif document_type == 'accounting':
                doc = parse_accounting_entry_json(json_path)
            else:
                raise ValueError(f"Unknown document type: {document_type}")

            results.append(doc)

        except Exception as e:
            logger.error(f"Error parsing {json_path}: {e}")
            continue

    logger.info(f"Successfully parsed {len(results)} out of {len(json_paths)} JSON files")
    return results
