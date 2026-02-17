"""
FINCENTER Vector Store

This module handles vector embeddings and semantic search across financial documents.
"""

from typing import List, Dict, Any
import numpy as np
from pathlib import Path
import json

from sentence_transformers import SentenceTransformer
from src.config import settings


class VectorStore:
    """Vector store for semantic search using FAISS."""
    
    def __init__(self):
        """Initialize the vector store and embedding model."""
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.vector_path = Path(settings.VECTOR_STORE_PATH)
        self.vector_path.mkdir(parents=True, exist_ok=True)
        
        # Metadata store (document_id -> metadata)
        self.metadata_path = self.vector_path / "metadata.json"
        self.metadata = self._load_metadata()
        
        print(f"[SUCCESS] VectorStore initialized with model: {settings.EMBEDDING_MODEL}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from disk."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save metadata to disk."""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        """
        Add a document to the vector store.
        
        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Additional metadata (type, date, etc.)
        """
        # Generate embedding
        embedding = self.embed_text(text)
        
        # Save embedding to disk
        embedding_path = self.vector_path / f"{doc_id}.npy"
        np.save(embedding_path, embedding)
        
        # Store metadata
        self.metadata[doc_id] = {
            "text": text[:500],  # Store first 500 chars
            **metadata
        }
        self._save_metadata()
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search across all documents.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of search results with scores
        """
        # Generate query embedding
        query_embedding = self.embed_text(query)
        
        # Compute similarity with all documents
        results = []
        for doc_id, metadata in self.metadata.items():
            # Load document embedding
            embedding_path = self.vector_path / f"{doc_id}.npy"
            if not embedding_path.exists():
                continue
            
            doc_embedding = np.load(embedding_path)
            
            # Compute cosine similarity
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            
            results.append({
                "document_id": doc_id,
                "document_type": metadata.get("type", "unknown"),
                "content": metadata.get("text", ""),
                "score": float(similarity),
                "metadata": metadata
            })
        
        # Sort by similarity score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    def inspect_embedding(self, doc_id: str) -> Dict[str, Any]:
        """
        Inspect embedding for a document (for debugging).
        
        Args:
            doc_id: Document ID
        
        Returns:
            Embedding information
        """
        embedding_path = self.vector_path / f"{doc_id}.npy"
        
        if not embedding_path.exists():
            return {"error": f"Document {doc_id} not found"}
        
        embedding = np.load(embedding_path)
        
        return {
            "document_id": doc_id,
            "embedding_shape": embedding.shape,
            "embedding_norm": float(np.linalg.norm(embedding)),
            "metadata": self.metadata.get(doc_id, {})
        }
