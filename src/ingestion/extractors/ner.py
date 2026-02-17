"""
Financial Named Entity Recognition (NER)

Extracts financial entities from text using spaCy and custom patterns.
Handles French and English text, tags entity types (CLIENT, VENDOR, BANK, etc.).

Examples:
    >>> entities = extract_financial_entities("Facture de ACME Corp pour 1,250€")
    >>> for entity in entities:
    ...     print(f"{entity['text']} ({entity['type']})")
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

try:
    import spacy
    from spacy.matcher import Matcher
    from spacy.tokens import Doc
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False
    logging.warning("spaCy not installed, NER functionality will be limited")

logger = logging.getLogger(__name__)


class NERExtractor:
    """Financial Named Entity Recognition extractor."""

    def __init__(self, model_name: str = 'fr_core_news_lg', use_custom_patterns: bool = True):
        """
        Initialize NER extractor.

        Args:
            model_name: spaCy model name ('fr_core_news_lg' or 'en_core_web_lg')
            use_custom_patterns: Whether to use custom financial entity patterns

        Raises:
            ImportError: If spaCy is not installed
        """
        if not HAS_SPACY:
            raise ImportError("spaCy is required for NER extraction. Install with: pip install spacy")

        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model '{model_name}' not found, trying to load default model")
            try:
                # Try French model
                self.nlp = spacy.load('fr_core_news_sm')
            except OSError:
                # Try English model as fallback
                try:
                    self.nlp = spacy.load('en_core_web_sm')
                except OSError:
                    raise OSError(
                        "No spaCy model found. Download with: "
                        "python -m spacy download fr_core_news_lg"
                    )

        self.matcher = Matcher(self.nlp.vocab)

        if use_custom_patterns:
            self._add_financial_patterns()

    def _add_financial_patterns(self):
        """Add custom patterns for financial entities."""

        # Pattern for company suffixes
        company_patterns = [
            [{"LOWER": {"IN": ["sa", "sarl", "sas", "sasu", "eurl", "sci"]}}, {"IS_PUNCT": True, "OP": "?"}],
            [{"LOWER": {"IN": ["ltd", "llc", "inc", "corp", "gmbh", "ag"]}}, {"IS_PUNCT": True, "OP": "?"}],
        ]

        # Pattern for SIRET (French company ID: 14 digits)
        siret_pattern = [
            [{"TEXT": {"REGEX": r"^\d{14}$"}}]
        ]

        # Pattern for amounts
        amount_pattern = [
            [
                {"TEXT": {"REGEX": r"^[\d\s,.]+$"}},
                {"LOWER": {"IN": ["€", "eur", "usd", "$", "£", "gbp"]}, "OP": "?"}
            ]
        ]

        # Add patterns to matcher
        self.matcher.add("COMPANY", company_patterns)
        self.matcher.add("SIRET", siret_pattern)
        self.matcher.add("AMOUNT", amount_pattern)

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.

        Args:
            text: Text to analyze

        Returns:
            List of entities with type, text, start, end positions

        Examples:
            >>> extractor = NERExtractor()
            >>> entities = extractor.extract_entities("ACME Corp a envoyé une facture de 1,250 EUR")
            >>> print(entities)
            [{'text': 'ACME Corp', 'type': 'ORG', 'start': 0, 'end': 9, ...}]
        """
        if not text:
            return []

        doc = self.nlp(text)
        entities = []

        # Extract standard spaCy entities
        for ent in doc.ents:
            entity = {
                'text': ent.text,
                'type': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 0.8  # Default confidence for spaCy entities
            }

            # Map spaCy labels to financial entity types
            entity['financial_type'] = self._map_to_financial_type(ent.label_, ent.text)

            entities.append(entity)

        # Extract custom pattern matches
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            entity = {
                'text': span.text,
                'type': self.nlp.vocab.strings[match_id],
                'start': span.start_char,
                'end': span.end_char,
                'confidence': 0.9,  # Higher confidence for pattern matches
                'financial_type': self.nlp.vocab.strings[match_id]
            }
            entities.append(entity)

        # De-duplicate entities (keep higher confidence ones)
        entities = self._deduplicate_entities(entities)

        return entities

    def _map_to_financial_type(self, spacy_label: str, text: str) -> str:
        """
        Map spaCy entity labels to financial entity types.

        Args:
            spacy_label: spaCy entity label (ORG, PERSON, etc.)
            text: Entity text

        Returns:
            Financial entity type (VENDOR, CLIENT, BANK, etc.)
        """
        text_lower = text.lower()

        # Check for specific keywords to determine role
        if any(keyword in text_lower for keyword in ['banque', 'bank', 'crédit', 'credit']):
            return 'BANK'

        if any(keyword in text_lower for keyword in ['fournisseur', 'supplier', 'vendor']):
            return 'VENDOR'

        if any(keyword in text_lower for keyword in ['client', 'customer', 'acheteur', 'buyer']):
            return 'CLIENT'

        # Map based on spaCy label
        mapping = {
            'ORG': 'ORGANIZATION',
            'PERSON': 'PERSON',
            'PER': 'PERSON',
            'LOC': 'LOCATION',
            'GPE': 'LOCATION',
            'MONEY': 'AMOUNT',
            'DATE': 'DATE',
            'CARDINAL': 'NUMBER',
        }

        return mapping.get(spacy_label, spacy_label)

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate entities, keeping ones with higher confidence.

        Args:
            entities: List of entities

        Returns:
            Deduplicated list of entities
        """
        if not entities:
            return []

        # Sort by start position, then by confidence (descending)
        sorted_entities = sorted(entities, key=lambda x: (x['start'], -x['confidence']))

        unique_entities = []
        used_spans = set()

        for entity in sorted_entities:
            span = (entity['start'], entity['end'])

            # Check if this span overlaps with any used span
            overlaps = False
            for used_start, used_end in used_spans:
                if not (entity['end'] <= used_start or entity['start'] >= used_end):
                    overlaps = True
                    break

            if not overlaps:
                unique_entities.append(entity)
                used_spans.add(span)

        # Sort by position
        unique_entities.sort(key=lambda x: x['start'])

        return unique_entities


def extract_financial_entities(text: str, lang: str = 'fr') -> List[Dict[str, Any]]:
    """
    Extract named entities from financial text.

    Convenience function that creates an extractor and extracts entities.

    Args:
        text: Text to analyze
        lang: Language code ('fr' for French, 'en' for English)

    Returns:
        List of entities with type, text, start, end positions

    Examples:
        >>> entities = extract_financial_entities("Facture de ACME Corp pour 1,250 EUR")
        >>> for entity in entities:
        ...     print(f"{entity['text']} ({entity['type']})")
    """
    model_name = 'fr_core_news_lg' if lang == 'fr' else 'en_core_web_lg'

    try:
        extractor = NERExtractor(model_name=model_name)
        return extractor.extract_entities(text)
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        # Fall back to regex-based extraction
        return extract_entities_with_regex(text)


def extract_entities_with_regex(text: str) -> List[Dict[str, Any]]:
    """
    Simple regex-based entity extraction (fallback when spaCy unavailable).

    Args:
        text: Text to analyze

    Returns:
        List of entities

    Examples:
        >>> entities = extract_entities_with_regex("SIRET: 12345678901234")
        >>> print(entities[0]['text'])
        '12345678901234'
    """
    entities = []

    # SIRET pattern (14 digits)
    siret_matches = re.finditer(r'\b\d{14}\b', text)
    for match in siret_matches:
        entities.append({
            'text': match.group(),
            'type': 'SIRET',
            'financial_type': 'COMPANY_ID',
            'start': match.start(),
            'end': match.end(),
            'confidence': 0.9
        })

    # VAT number pattern (e.g., FR12345678901)
    vat_matches = re.finditer(r'\b[A-Z]{2}\d{11}\b', text)
    for match in vat_matches:
        entities.append({
            'text': match.group(),
            'type': 'VAT_NUMBER',
            'financial_type': 'TAX_ID',
            'start': match.start(),
            'end': match.end(),
            'confidence': 0.9
        })

    # Company name patterns (simplified)
    company_patterns = [
        r'\b([A-ZÉÈÊË][A-Za-zéèêëàâùûôîïç\s&-]+)\s+(SA|SARL|SAS|SASU|EURL|SCI)\b',
        r'\b([A-Z][A-Za-z\s&-]+)\s+(Ltd|LLC|Inc|Corp|GmbH|AG)\b',
    ]

    for pattern in company_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            entities.append({
                'text': match.group(),
                'type': 'ORGANIZATION',
                'financial_type': 'ORGANIZATION',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.7
            })

    # Email addresses
    email_matches = re.finditer(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    for match in email_matches:
        entities.append({
            'text': match.group(),
            'type': 'EMAIL',
            'financial_type': 'CONTACT',
            'start': match.start(),
            'end': match.end(),
            'confidence': 0.95
        })

    # Phone numbers (French format)
    phone_matches = re.finditer(r'\b(?:0|\+33\s?)[1-9](?:[\s.-]?\d{2}){4}\b', text)
    for match in phone_matches:
        entities.append({
            'text': match.group(),
            'type': 'PHONE',
            'financial_type': 'CONTACT',
            'start': match.start(),
            'end': match.end(),
            'confidence': 0.9
        })

    return entities


def extract_vendor_entities(text: str) -> Dict[str, Any]:
    """
    Extract vendor-specific entities from text.

    Args:
        text: Text to analyze (typically from invoice header)

    Returns:
        Dictionary with vendor information

    Examples:
        >>> vendor = extract_vendor_entities("ACME Corp SARL\\nSIRET: 12345678901234\\nTVA: FR12345678901")
        >>> print(vendor['name'])
        'ACME Corp SARL'
    """
    entities = extract_financial_entities(text) if HAS_SPACY else extract_entities_with_regex(text)

    vendor = {
        'name': None,
        'siret': None,
        'vat_number': None,
        'email': None,
        'phone': None
    }

    # Find first organization as vendor name
    for entity in entities:
        if entity['financial_type'] in ['ORGANIZATION', 'ORG'] and not vendor['name']:
            vendor['name'] = entity['text']

        if entity['financial_type'] == 'COMPANY_ID' or entity['type'] == 'SIRET':
            vendor['siret'] = entity['text']

        if entity['financial_type'] == 'TAX_ID' or entity['type'] == 'VAT_NUMBER':
            vendor['vat_number'] = entity['text']

        if entity['type'] == 'EMAIL':
            vendor['email'] = entity['text']

        if entity['type'] == 'PHONE':
            vendor['phone'] = entity['text']

    return vendor


def extract_client_entities(text: str) -> Dict[str, Any]:
    """
    Extract client-specific entities from text.

    Args:
        text: Text to analyze (typically from invoice "Bill To" section)

    Returns:
        Dictionary with client information
    """
    entities = extract_financial_entities(text) if HAS_SPACY else extract_entities_with_regex(text)

    client = {
        'name': None,
        'email': None,
        'phone': None
    }

    # Find first organization or person as client name
    for entity in entities:
        if entity['financial_type'] in ['ORGANIZATION', 'ORG', 'PERSON'] and not client['name']:
            client['name'] = entity['text']

        if entity['type'] == 'EMAIL':
            client['email'] = entity['text']

        if entity['type'] == 'PHONE':
            client['phone'] = entity['text']

    return client


def tag_entity_roles(entities: List[Dict[str, Any]], context: str = '') -> List[Dict[str, Any]]:
    """
    Tag entities with their roles (VENDOR, CLIENT, etc.) based on context.

    Args:
        entities: List of extracted entities
        context: Context string that may contain role markers

    Returns:
        Entities with added 'role' field

    Examples:
        >>> entities = [{'text': 'ACME Corp', 'type': 'ORG'}]
        >>> tagged = tag_entity_roles(entities, context="Vendor: ACME Corp")
        >>> print(tagged[0]['role'])
        'VENDOR'
    """
    context_lower = context.lower() if context else ''

    # Define role markers
    vendor_markers = ['vendor', 'fournisseur', 'supplier', 'from', 'de la part de']
    client_markers = ['client', 'customer', 'bill to', 'facturé à', 'pour']
    bank_markers = ['bank', 'banque', 'iban', 'bic', 'swift']

    for entity in entities:
        entity_text = entity['text'].lower()

        # Check entity text for role indicators
        if any(marker in entity_text for marker in bank_markers):
            entity['role'] = 'BANK'
        elif any(marker in entity_text for marker in vendor_markers):
            entity['role'] = 'VENDOR'
        elif any(marker in entity_text for marker in client_markers):
            entity['role'] = 'CLIENT'
        else:
            # Check context around the entity
            start = max(0, entity['start'] - 50)
            end = min(len(context), entity['end'] + 50)
            surrounding_text = context[start:end].lower() if context else ''

            if any(marker in surrounding_text for marker in vendor_markers):
                entity['role'] = 'VENDOR'
            elif any(marker in surrounding_text for marker in client_markers):
                entity['role'] = 'CLIENT'
            elif any(marker in surrounding_text for marker in bank_markers):
                entity['role'] = 'BANK'
            else:
                entity['role'] = 'UNKNOWN'

    return entities


def get_entity_relationships(entities: List[Dict[str, Any]]) -> List[Tuple[Dict, str, Dict]]:
    """
    Identify relationships between entities.

    Args:
        entities: List of extracted entities

    Returns:
        List of (entity1, relationship_type, entity2) tuples

    Examples:
        >>> entities = [
        ...     {'text': 'ACME Corp', 'type': 'ORG', 'role': 'VENDOR'},
        ...     {'text': 'Client Inc', 'type': 'ORG', 'role': 'CLIENT'}
        ... ]
        >>> relationships = get_entity_relationships(entities)
        >>> print(relationships[0][1])  # relationship type
        'BILLS'
    """
    relationships = []

    # Find vendors and clients
    vendors = [e for e in entities if e.get('role') == 'VENDOR']
    clients = [e for e in entities if e.get('role') == 'CLIENT']

    # Create BILLS relationships (vendor bills client)
    for vendor in vendors:
        for client in clients:
            relationships.append((vendor, 'BILLS', client))

    return relationships
