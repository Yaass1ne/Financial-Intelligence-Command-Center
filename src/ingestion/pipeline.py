"""
Main Ingestion Pipeline

Orchestrates the entire document ingestion process:
1. Reads files from input directory
2. Processes each file type (budgets, invoices, contracts)
3. Extracts entities and creates graph nodes
4. Generates vector embeddings
5. Handles errors gracefully with logging

Examples:
    >>> from pathlib import Path
    >>> stats = ingest_directory(Path("data/synthetic/"), Path("data/processed/"))
    >>> print(f"Processed {stats['files_processed']} files")
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    logging.warning("tqdm not installed, progress bars disabled")

from src.config import settings
from src.ingestion.parsers.json import parse_invoice_json, parse_contract_json, parse_json_batch
from src.ingestion.parsers.excel import parse_budget_excel, parse_multi_sheet_budget
from src.ingestion.parsers.pdf import parse_invoice_pdf
from src.ingestion.extractors.ner import extract_financial_entities
from src.ingestion.validators import batch_validate, validate_invoice, validate_contract, validate_budget

# Try to import RAG components (may not be fully implemented yet)
try:
    from src.rag.graph import FinancialGraph
    from src.rag.vectorstore import VectorStore
    HAS_RAG = True
except ImportError:
    HAS_RAG = False
    logging.warning("RAG components not available, skipping graph/vector operations")

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Main ingestion pipeline orchestrator."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        batch_size: int = 50,
        use_multiprocessing: bool = True,
        max_workers: Optional[int] = None
    ):
        """
        Initialize ingestion pipeline.

        Args:
            input_dir: Root directory with source documents
            output_dir: Directory for processed data
            batch_size: Number of documents per batch
            use_multiprocessing: Enable parallel processing
            max_workers: Maximum worker processes (default: CPU count)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.use_multiprocessing = use_multiprocessing
        self.max_workers = max_workers or mp.cpu_count()

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "vectors").mkdir(exist_ok=True)
        (self.output_dir / "metadata").mkdir(exist_ok=True)
        (self.output_dir / "errors").mkdir(exist_ok=True)

        # Initialize RAG components if available
        if HAS_RAG:
            try:
                self.graph = FinancialGraph()
                self.vectorstore = VectorStore()
                logger.info("Initialized RAG components (graph + vectorstore)")
            except Exception as e:
                logger.warning(f"Could not initialize RAG components: {e}")
                self.graph = None
                self.vectorstore = None
        else:
            self.graph = None
            self.vectorstore = None

        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'invoices': 0,
            'contracts': 0,
            'budgets': 0,
            'errors': []
        }

    def ingest(self) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ingestion from {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Batch size: {self.batch_size}, Workers: {self.max_workers}")

        start_time = datetime.now()

        # Discover all files
        all_files = self._discover_files()
        logger.info(f"Discovered {len(all_files)} files to process")

        if not all_files:
            logger.warning("No files found to process")
            return self.stats

        # Process files in batches
        batches = [all_files[i:i + self.batch_size] for i in range(0, len(all_files), self.batch_size)]

        if HAS_TQDM:
            progress_bar = tqdm(total=len(all_files), desc="Ingesting documents")
        else:
            progress_bar = None

        for batch in batches:
            if self.use_multiprocessing and len(batch) > 1:
                self._process_batch_parallel(batch, progress_bar)
            else:
                self._process_batch_sequential(batch, progress_bar)

        if progress_bar:
            progress_bar.close()

        # Generate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.stats['duration_seconds'] = duration
        self.stats['files_per_second'] = self.stats['files_processed'] / duration if duration > 0 else 0

        logger.info(f"Ingestion complete: {self.stats['files_processed']} files in {duration:.2f}s")
        logger.info(f"  Invoices: {self.stats['invoices']}")
        logger.info(f"  Contracts: {self.stats['contracts']}")
        logger.info(f"  Budgets: {self.stats['budgets']}")
        logger.info(f"  Errors: {self.stats['files_failed']}")

        # Save statistics
        self._save_statistics()

        return self.stats

    def _discover_files(self) -> List[Dict[str, Any]]:
        """
        Discover all processable files in input directory.

        Returns:
            List of file metadata dictionaries
        """
        files = []

        # Look for invoices
        invoice_dir = self.input_dir / "invoices"
        if invoice_dir.exists():
            for file_path in invoice_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.json', '.pdf']:
                    files.append({
                        'path': file_path,
                        'type': 'invoice',
                        'format': file_path.suffix[1:].lower()
                    })

        # Look for contracts
        contract_dir = self.input_dir / "contracts"
        if contract_dir.exists():
            for file_path in contract_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.json', '.pdf']:
                    files.append({
                        'path': file_path,
                        'type': 'contract',
                        'format': file_path.suffix[1:].lower()
                    })

        # Look for budgets
        budget_dir = self.input_dir / "budgets"
        if budget_dir.exists():
            for file_path in budget_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.xlsx', '.xls']:
                    files.append({
                        'path': file_path,
                        'type': 'budget',
                        'format': file_path.suffix[1:].lower()
                    })

        # Look for accounting entries
        accounting_dir = self.input_dir / "accounting"
        if accounting_dir.exists():
            for file_path in accounting_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.csv', '.json']:
                    files.append({
                        'path': file_path,
                        'type': 'accounting',
                        'format': file_path.suffix[1:].lower()
                    })

        return files

    def _process_batch_sequential(self, batch: List[Dict[str, Any]], progress_bar=None):
        """Process batch of files sequentially."""
        for file_info in batch:
            try:
                self._process_file(file_info)
                self.stats['files_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing {file_info['path']}: {e}")
                self.stats['files_failed'] += 1
                self.stats['errors'].append({
                    'file': str(file_info['path']),
                    'error': str(e)
                })

            if progress_bar:
                progress_bar.update(1)

    def _process_batch_parallel(self, batch: List[Dict[str, Any]], progress_bar=None):
        """Process batch of files in parallel using ProcessPoolExecutor."""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_file, file_info): file_info for file_info in batch}

            for future in as_completed(futures):
                file_info = futures[future]
                try:
                    future.result()
                    self.stats['files_processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing {file_info['path']}: {e}")
                    self.stats['files_failed'] += 1
                    self.stats['errors'].append({
                        'file': str(file_info['path']),
                        'error': str(e)
                    })

                if progress_bar:
                    progress_bar.update(1)

    def _process_file(self, file_info: Dict[str, Any]):
        """
        Process a single file.

        Args:
            file_info: File metadata dictionary
        """
        file_path = file_info['path']
        doc_type = file_info['type']
        file_format = file_info['format']

        logger.debug(f"Processing {doc_type} file: {file_path.name}")

        # Parse document based on type and format
        if doc_type == 'invoice':
            if file_format == 'json':
                document = parse_invoice_json(file_path)
            elif file_format == 'pdf':
                document = parse_invoice_pdf(file_path)
            else:
                raise ValueError(f"Unsupported invoice format: {file_format}")

            # Validate
            validation = validate_invoice(document)
            if not validation.is_valid:
                logger.warning(f"Invoice validation failed for {file_path.name}: {validation.errors}")

            self.stats['invoices'] += 1

        elif doc_type == 'contract':
            if file_format == 'json':
                document = parse_contract_json(file_path)
            elif file_format == 'pdf':
                # For now, extract text and treat as unstructured
                from src.ingestion.parsers.pdf import extract_all_text_from_pdf
                text = extract_all_text_from_pdf(file_path)
                document = {
                    'contract_id': file_path.stem,
                    'source_file': str(file_path),
                    'document_type': 'contract',
                    'raw_text': text
                }
            else:
                raise ValueError(f"Unsupported contract format: {file_format}")

            # Validate
            if 'raw_text' not in document:  # Only validate structured contracts
                validation = validate_contract(document)
                if not validation.is_valid:
                    logger.warning(f"Contract validation failed for {file_path.name}: {validation.errors}")

            self.stats['contracts'] += 1

        elif doc_type == 'budget':
            if file_format in ['xlsx', 'xls']:
                budget_df = parse_budget_excel(file_path)
                # Convert to list of dictionaries for processing
                document = {
                    'source_file': str(file_path),
                    'document_type': 'budget',
                    'data': budget_df.to_dict('records')
                }
            else:
                raise ValueError(f"Unsupported budget format: {file_format}")

            self.stats['budgets'] += 1

        elif doc_type == 'accounting':
            if file_format == 'csv':
                df = pd.read_csv(file_path)
                document = {
                    'source_file': str(file_path),
                    'document_type': 'accounting',
                    'data': df.to_dict('records')
                }
            else:
                raise ValueError(f"Unsupported accounting format: {file_format}")

        # Extract entities (if text available)
        if 'raw_text' in document and document['raw_text']:
            document['entities'] = extract_financial_entities(document['raw_text'])

        # Save processed document
        self._save_document(document, file_path)

        # Add to graph (if available)
        if self.graph:
            try:
                self._add_to_graph(document)
            except Exception as e:
                logger.warning(f"Could not add {file_path.name} to graph: {e}")

        # Generate embeddings (if available)
        if self.vectorstore:
            try:
                self._generate_embeddings(document)
            except Exception as e:
                logger.warning(f"Could not generate embeddings for {file_path.name}: {e}")

    def _save_document(self, document: Dict[str, Any], source_path: Path):
        """
        Save processed document to output directory.

        Args:
            document: Processed document dictionary
            source_path: Original source file path
        """
        # Create output filename
        output_filename = source_path.stem + "_processed.json"
        output_path = self.output_dir / "metadata" / output_filename

        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(document, f, indent=2, default=str)

        logger.debug(f"Saved processed document to {output_path}")

    def _add_to_graph(self, document: Dict[str, Any]):
        """
        Add document to Neo4j graph.

        Args:
            document: Processed document dictionary
        """
        if not self.graph:
            return

        doc_type = document.get('document_type')

        if doc_type == 'invoice':
            # Create invoice node and relationships
            self.graph.create_invoice_node(document)

        elif doc_type == 'contract':
            # Create contract node and relationships
            self.graph.create_contract_node(document)

        elif doc_type == 'budget':
            # Create budget nodes (one per department/category)
            for budget_item in document.get('data', []):
                self.graph.create_budget_node(budget_item)

    def _generate_embeddings(self, document: Dict[str, Any]):
        """
        Generate vector embeddings for document.

        Args:
            document: Processed document dictionary
        """
        if not self.vectorstore:
            return

        # Generate text representation for embedding
        text_parts = []

        if 'raw_text' in document:
            text_parts.append(document['raw_text'][:500])  # Limit to 500 chars

        if document.get('document_type') == 'invoice':
            if 'vendor' in document and document['vendor']:
                vendor_name = document['vendor'].get('name') if isinstance(document['vendor'], dict) else document['vendor']
                if vendor_name:
                    text_parts.append(f"Vendor: {vendor_name}")

        text = " ".join(text_parts)

        if text:
            # Generate and store embedding
            doc_id = document.get('invoice_id') or document.get('contract_id') or document.get('source_file')
            self.vectorstore.add_document(doc_id, text, metadata=document)

    def _save_statistics(self):
        """Save ingestion statistics to file."""
        stats_path = self.output_dir / "ingestion_stats.json"

        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, default=str)

        logger.info(f"Saved ingestion statistics to {stats_path}")


def ingest_directory(
    input_dir: Path,
    output_dir: Path,
    batch_size: int = 50,
    use_multiprocessing: bool = True
) -> Dict[str, Any]:
    """
    Ingest all documents from input directory.

    Args:
        input_dir: Root directory with synthetic data
        output_dir: Where to save processed data
        batch_size: Number of documents per batch
        use_multiprocessing: Enable parallel processing

    Returns:
        Dictionary with ingestion statistics (files_processed, errors, etc.)

    Examples:
        >>> from pathlib import Path
        >>> stats = ingest_directory(Path("data/synthetic/"), Path("data/processed/"))
        >>> print(f"Processed {stats['files_processed']} files")
    """
    pipeline = IngestionPipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        batch_size=batch_size,
        use_multiprocessing=use_multiprocessing
    )

    return pipeline.ingest()


def main():
    """Command-line interface for ingestion pipeline."""
    parser = argparse.ArgumentParser(description="FINCENTER Ingestion Pipeline")
    parser.add_argument("--input", type=str, required=True, help="Input directory with source documents")
    parser.add_argument("--output", type=str, required=True, help="Output directory for processed data")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--no-multiprocessing", action="store_true", help="Disable parallel processing")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", type=str, help="Log file path")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    if args.log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(args.log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(level=log_level, format=log_format)

    # Run ingestion
    stats = ingest_directory(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        batch_size=args.batch_size,
        use_multiprocessing=not args.no_multiprocessing
    )

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files failed: {stats['files_failed']}")
    print(f"Invoices: {stats['invoices']}")
    print(f"Contracts: {stats['contracts']}")
    print(f"Budgets: {stats['budgets']}")
    print(f"Duration: {stats.get('duration_seconds', 0):.2f}s")
    print(f"Speed: {stats.get('files_per_second', 0):.2f} files/sec")
    print("=" * 60)


if __name__ == "__main__":
    main()
