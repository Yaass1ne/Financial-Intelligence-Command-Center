"""
PDF Invoice Parser with OCR Fallback

Extracts structured data from invoice PDFs using pdfplumber.
Falls back to pytesseract OCR for scanned documents.

Examples:
    >>> from pathlib import Path
    >>> invoice = parse_invoice_pdf(Path("invoice_001.pdf"))
    >>> print(invoice['total_ttc'])
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logging.warning("pdfplumber not installed, PDF parsing will be limited")

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logging.warning("pytesseract or pdf2image not installed, OCR fallback unavailable")

from src.ingestion.extractors.amounts import extract_amounts_from_text, parse_amount
from src.ingestion.extractors.dates import extract_dates_from_text, parse_date

logger = logging.getLogger(__name__)


class PDFParseError(Exception):
    """Exception raised when PDF parsing fails."""
    pass


def parse_invoice_pdf(
    pdf_path: Path,
    use_ocr: bool = False,
    lang: str = 'fra'
) -> Dict[str, Any]:
    """
    Extract structured data from invoice PDF.

    Uses pdfplumber for text extraction, falls back to OCR if text is empty.

    Args:
        pdf_path: Path to PDF file
        use_ocr: Force use of OCR even if text extraction works
        lang: OCR language ('fra' for French, 'eng' for English)

    Returns:
        Normalized invoice dictionary with extracted fields

    Raises:
        PDFParseError: If PDF cannot be parsed

    Examples:
        >>> invoice = parse_invoice_pdf(Path("invoice_001.pdf"))
        >>> print(f"Invoice {invoice['invoice_id']}: {invoice['total_ttc']} {invoice['currency']}")
    """
    if not pdf_path.exists():
        raise PDFParseError(f"File not found: {pdf_path}")

    try:
        # Extract text from PDF
        if use_ocr or not HAS_PDFPLUMBER:
            text = _extract_text_with_ocr(pdf_path, lang)
            logger.info(f"Extracted text from {pdf_path.name} using OCR")
        else:
            text = _extract_text_with_pdfplumber(pdf_path)

            # If text is empty or too short, fall back to OCR
            if not text or len(text.strip()) < 50:
                logger.warning(f"Text extraction returned little content for {pdf_path.name}, trying OCR")
                if HAS_OCR:
                    text = _extract_text_with_ocr(pdf_path, lang)
                else:
                    raise PDFParseError(f"No text extracted and OCR not available for {pdf_path}")

        # Extract tables if available
        tables = _extract_tables_with_pdfplumber(pdf_path) if HAS_PDFPLUMBER else []

        # Parse extracted text into structured data
        invoice = _parse_invoice_from_text(text, tables, pdf_path)

        logger.info(f"Successfully parsed invoice from {pdf_path.name}")
        return invoice

    except Exception as e:
        raise PDFParseError(f"Error parsing {pdf_path}: {e}")


def _extract_text_with_pdfplumber(pdf_path: Path) -> str:
    """
    Extract text from PDF using pdfplumber.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text
    """
    if not HAS_PDFPLUMBER:
        raise PDFParseError("pdfplumber not installed")

    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        return text.strip()

    except Exception as e:
        logger.error(f"Error extracting text with pdfplumber from {pdf_path}: {e}")
        return ""


def _extract_text_with_ocr(pdf_path: Path, lang: str = 'fra') -> str:
    """
    Extract text from PDF using OCR (pytesseract).

    Args:
        pdf_path: Path to PDF file
        lang: OCR language code

    Returns:
        Extracted text
    """
    if not HAS_OCR:
        raise PDFParseError("OCR dependencies not installed (pytesseract, pdf2image)")

    try:
        # Convert PDF to images
        images = pdf2image.convert_from_path(pdf_path)

        text = ""
        for i, image in enumerate(images):
            # Perform OCR on each page
            page_text = pytesseract.image_to_string(image, lang=lang)
            text += page_text + "\n"

            logger.debug(f"OCR processed page {i + 1}/{len(images)} of {pdf_path.name}")

        return text.strip()

    except Exception as e:
        logger.error(f"Error performing OCR on {pdf_path}: {e}")
        return ""


def _extract_tables_with_pdfplumber(pdf_path: Path) -> List[List[List[str]]]:
    """
    Extract tables from PDF using pdfplumber.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of tables (each table is a list of rows)
    """
    if not HAS_PDFPLUMBER:
        return []

    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

        logger.debug(f"Extracted {len(tables)} tables from {pdf_path.name}")
        return tables

    except Exception as e:
        logger.error(f"Error extracting tables from {pdf_path}: {e}")
        return []


def _parse_invoice_from_text(
    text: str,
    tables: List[List[List[str]]],
    source_file: Path
) -> Dict[str, Any]:
    """
    Parse invoice data from extracted text and tables.

    Args:
        text: Extracted text from PDF
        tables: Extracted tables from PDF
        source_file: Source PDF file path

    Returns:
        Normalized invoice dictionary
    """
    invoice = {
        'source_file': str(source_file),
        'document_type': 'invoice',
        'raw_text': text[:500]  # Store first 500 chars for reference
    }

    # Extract invoice ID/number
    invoice['invoice_id'] = _extract_invoice_id(text)

    # Extract dates
    dates = extract_dates_from_text(text, prefer_european=True)
    if dates:
        invoice['date'] = dates[0]  # First date is usually invoice date
        if len(dates) > 1:
            invoice['due_date'] = dates[1]  # Second date is usually due date
        else:
            invoice['due_date'] = None
    else:
        invoice['date'] = None
        invoice['due_date'] = None

    # Extract vendor/client information
    invoice['vendor'] = _extract_vendor_info(text)
    invoice['client'] = _extract_client_info(text)

    # Extract amounts
    amount_info = extract_amounts_from_text(text)
    invoice.update({
        'total_ht': amount_info.get('amount_ht'),
        'tax_rate': amount_info.get('tax_rate'),
        'tax_amount': amount_info.get('tax_amount'),
        'total_ttc': amount_info.get('amount_ttc'),
        'currency': amount_info.get('currency', 'EUR')
    })

    # Extract line items from tables
    if tables:
        invoice['items'] = _extract_line_items_from_tables(tables)
    else:
        invoice['items'] = []

    # Extract payment terms
    invoice['payment_terms'] = _extract_payment_terms(text)

    # Try to determine status
    invoice['status'] = _extract_status(text)

    return invoice


def _extract_invoice_id(text: str) -> Optional[str]:
    """
    Extract invoice ID/number from text.

    Looks for patterns like:
    - Invoice #12345
    - Facture N° 2024-0001
    - INV-2024-0001

    Args:
        text: Text to search

    Returns:
        Invoice ID or None
    """
    patterns = [
        r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'Facture\s*N°?\s*:?\s*([A-Z0-9-]+)',
        r'INV[-_]?(\d{4}[-_]\d{4})',
        r'INVOICE\s*NUMBER\s*:?\s*([A-Z0-9-]+)',
        r'N°\s*FACTURE\s*:?\s*([A-Z0-9-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # If no pattern matches, look for any ID-like string near "invoice" or "facture"
    words = text.split()
    for i, word in enumerate(words):
        if word.lower() in ['invoice', 'facture', 'inv']:
            # Check next few words for ID-like pattern
            for j in range(i + 1, min(i + 5, len(words))):
                if re.match(r'^[A-Z0-9-]{4,}$', words[j]):
                    return words[j]

    return None


def _extract_vendor_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract vendor/supplier information from text.

    Args:
        text: Text to search

    Returns:
        Dictionary with vendor information
    """
    vendor = {
        'name': None,
        'address': None,
        'siret': None,
        'vat_number': None
    }

    # Try to find vendor name (usually at top of invoice)
    lines = text.split('\n')
    if lines:
        # First non-empty line is often the vendor name
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 3 and not any(skip in line.lower() for skip in ['invoice', 'facture', 'date']):
                vendor['name'] = line
                break

    # Extract SIRET (French company ID: 14 digits)
    siret_match = re.search(r'SIRET\s*:?\s*(\d{14})', text, re.IGNORECASE)
    if siret_match:
        vendor['siret'] = siret_match.group(1)

    # Extract VAT number
    vat_patterns = [
        r'TVA\s*:?\s*([A-Z]{2}\d{11})',
        r'VAT\s*:?\s*([A-Z]{2}\d{11})',
        r'N°\s*TVA\s*:?\s*([A-Z]{2}\d{11})',
    ]
    for pattern in vat_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vendor['vat_number'] = match.group(1)
            break

    return vendor


def _extract_client_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract client/customer information from text.

    Args:
        text: Text to search

    Returns:
        Dictionary with client information
    """
    client = {
        'name': None,
        'address': None
    }

    # Look for client section markers
    client_markers = ['client', 'customer', 'bill to', 'facturé à', 'billto']

    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Check if this line contains a client marker
        if any(marker in line_lower for marker in client_markers):
            # Get next non-empty line as client name
            for j in range(i + 1, min(i + 10, len(lines))):
                potential_name = lines[j].strip()
                if potential_name and len(potential_name) > 3:
                    # Skip if it's another label
                    if ':' not in potential_name and not any(skip in potential_name.lower() for skip in ['address', 'tel', 'email']):
                        client['name'] = potential_name
                        break
            break

    return client


def _extract_line_items_from_tables(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    """
    Extract line items from PDF tables.

    Args:
        tables: List of extracted tables

    Returns:
        List of line item dictionaries
    """
    items = []

    for table in tables:
        if not table or len(table) < 2:  # Need at least header + 1 row
            continue

        # Try to identify column indices
        header = table[0] if table else []
        header_lower = [str(h).lower() if h else '' for h in header]

        # Find column indices
        desc_col = _find_column_index(header_lower, ['description', 'designation', 'item', 'article'])
        qty_col = _find_column_index(header_lower, ['quantity', 'qty', 'quantité', 'qté'])
        price_col = _find_column_index(header_lower, ['unit price', 'price', 'prix unitaire', 'pu'])
        total_col = _find_column_index(header_lower, ['total', 'amount', 'montant'])

        # Parse data rows
        for row in table[1:]:
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue

            item = {
                'description': None,
                'quantity': None,
                'unit_price': None,
                'total': None
            }

            if desc_col is not None and desc_col < len(row):
                item['description'] = str(row[desc_col]).strip()

            if qty_col is not None and qty_col < len(row):
                qty_value = row[qty_col]
                if qty_value:
                    item['quantity'] = _parse_table_number(qty_value)

            if price_col is not None and price_col < len(row):
                price_value = row[price_col]
                if price_value:
                    item['unit_price'] = parse_amount(str(price_value))

            if total_col is not None and total_col < len(row):
                total_value = row[total_col]
                if total_value:
                    item['total'] = parse_amount(str(total_value))

            # Calculate total if missing
            if item['total'] is None and item['quantity'] and item['unit_price']:
                item['total'] = round(item['quantity'] * item['unit_price'], 2)

            # Only add if we have at least a description
            if item['description'] and item['description'] != 'None':
                items.append(item)

    return items


def _find_column_index(header: List[str], keywords: List[str]) -> Optional[int]:
    """
    Find column index by matching keywords in header.

    Args:
        header: List of header cell values (lowercase)
        keywords: List of keywords to match

    Returns:
        Column index or None
    """
    for i, cell in enumerate(header):
        cell_str = str(cell).lower() if cell else ''
        if any(keyword in cell_str for keyword in keywords):
            return i

    return None


def _parse_table_number(value: Any) -> Optional[float]:
    """
    Parse numeric value from table cell.

    Args:
        value: Cell value

    Returns:
        Parsed number or None
    """
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return float(value)

        value_str = str(value).strip()
        # Remove whitespace and try to parse
        value_str = value_str.replace(' ', '')
        return float(value_str)

    except (ValueError, TypeError):
        return None


def _extract_payment_terms(text: str) -> Optional[str]:
    """
    Extract payment terms from text.

    Args:
        text: Text to search

    Returns:
        Payment terms string or None
    """
    patterns = [
        r'Payment terms?\s*:?\s*([^\n]+)',
        r'Terms?\s*:?\s*([^\n]+)',
        r'Net\s+(\d+)\s*days?',
        r'Paiement\s*:?\s*([^\n]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            terms = match.group(1).strip()
            return terms if len(terms) < 100 else terms[:100]

    return None


def _extract_status(text: str) -> str:
    """
    Try to determine invoice status from text.

    Args:
        text: Text to search

    Returns:
        Status string (PAID, UNPAID, OVERDUE)
    """
    text_lower = text.lower()

    if 'paid' in text_lower or 'payé' in text_lower or 'réglé' in text_lower:
        return 'PAID'
    elif 'overdue' in text_lower or 'en retard' in text_lower:
        return 'OVERDUE'
    else:
        return 'UNPAID'  # Default


def extract_all_text_from_pdf(pdf_path: Path, use_ocr: bool = False) -> str:
    """
    Extract all text from PDF for general use.

    Args:
        pdf_path: Path to PDF file
        use_ocr: Use OCR instead of text extraction

    Returns:
        Extracted text
    """
    if use_ocr or not HAS_PDFPLUMBER:
        return _extract_text_with_ocr(pdf_path)
    else:
        text = _extract_text_with_pdfplumber(pdf_path)
        if not text or len(text.strip()) < 50:
            if HAS_OCR:
                return _extract_text_with_ocr(pdf_path)
        return text


def get_pdf_metadata(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with PDF metadata
    """
    if not HAS_PDFPLUMBER:
        return {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            metadata = {
                'num_pages': len(pdf.pages),
                'metadata': pdf.metadata,
                'file_size': pdf_path.stat().st_size,
                'file_name': pdf_path.name
            }

            # Check if first page has text
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text()
                metadata['has_text'] = bool(first_page_text and len(first_page_text.strip()) > 10)
            else:
                metadata['has_text'] = False

            return metadata

    except Exception as e:
        logger.error(f"Error extracting PDF metadata from {pdf_path}: {e}")
        return {}
