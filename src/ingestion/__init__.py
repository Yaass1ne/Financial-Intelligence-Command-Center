"""
FINCENTER Ingestion Module

Document ingestion and processing for financial documents.
"""

from .pipeline import ingest_directory, IngestionPipeline

__all__ = ['ingest_directory', 'IngestionPipeline']
