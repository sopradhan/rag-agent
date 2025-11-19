"""
Vector Store Abstraction using ChromaDB
Handles embeddings while metadata stays in SQLite
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os
from ..utils.token_manager import TokenManager, TokenAwareChunker


class ChromaVectorStore:
    """ChromaDB vector store for semantic search with embeddings."""
    
    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        collection_name: str = "rag_embeddings",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_model: SentenceTransformer model for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with fallback to EphemeralClient if persistent fails
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            print("[OK] ChromaDB PersistentClient initialized")
        except Exception as e:
            print(f"Warning: ChromaDB PersistentClient failed ({str(e)[:50]}), using EphemeralClient")
            self.client = chromadb.EphemeralClient()
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        try:
            import torch
            # Force CPU device to avoid meta tensor issues
            device = "cpu"
            self.embedding_model = SentenceTransformer(embedding_model, device=device, trust_remote_code=True)
        except Exception as e:
            print(f"Warning: Failed to load with device specification: {e}")
            try:
                # Fallback: try without device parameter
                self.embedding_model = SentenceTransformer(embedding_model, trust_remote_code=True)
            except Exception as e2:
                print(f"Warning: Failed to load SentenceTransformer: {e2}")
                # Final fallback: use a dummy embedding model
                class DummyEmbedder:
                    def encode(self, text, convert_to_numpy=False):
                        import numpy as np
                        # Return fixed-size embeddings
                        return np.random.randn(384).astype(np.float32) if convert_to_numpy else [0.0] * 384
                    def get_sentence_embedding_dimension(self):
                        return 384
                self.embedding_model = DummyEmbedder()
        
        print(f"Embedding dimension: {self.embedding_model.get_sentence_embedding_dimension()}")
        
        # Initialize token manager for token-aware operations
        self.token_manager = TokenManager(model="gpt-3.5-turbo")
        self.chunker = TokenAwareChunker(
            token_manager=self.token_manager,
            chunk_size=512,
            overlap=50,
            respect_boundaries=True
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"[OK] Loaded existing collection: {collection_name}")
        except Exception as e:
            try:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "RAG system embeddings"}
                )
                print(f"[OK] Created new collection: {collection_name}")
            except Exception as create_err:
                print(f"Warning: Collection creation failed: {create_err}")
                self.collection = None
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def add_documents(
        self,
        doc_ids: List[str],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add documents to vector store.
        
        Args:
            doc_ids: List of unique document IDs (from SQLite)
            texts: List of document texts/chunks
            metadatas: Optional metadata dicts (minimal, full metadata in SQLite)
        """
        if not doc_ids or not texts:
            return
        
        if len(doc_ids) != len(texts):
            raise ValueError("doc_ids and texts must have same length")
        
        # Generate embeddings
        embeddings = self.embed_batch(texts)
        
        # Prepare metadata (keep minimal in Chroma)
        if metadatas is None:
            metadatas = [{} for _ in doc_ids]
        
        # Add to collection
        self.collection.add(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        print(f"Added {len(doc_ids)} documents to vector store")
    
    def _get_classification_for_source(self, source: str) -> str:
        """Map source filename to document classification"""
        source_lower = source.lower()
        
        # Source to classification mapping
        classifications = {
            # Engineering docs
            'engineering_manual': 'engineering',
            'system_docs': 'engineering',
            'db_recovery': 'engineering',
            'database': 'engineering',
            'technical': 'engineering',
            'deployment': 'engineering',
            'api': 'engineering',
            'code': 'engineering',
            'procedure': 'engineering',
            
            # HR docs
            'hr_policies': 'hr',
            'employee_handbook': 'hr',
            'compensation': 'hr',
            'benefits': 'hr',
            'policy': 'hr',
            'handbook': 'hr',
            'recruitment': 'hr',
            'onboarding': 'hr',
            
            # Security docs
            'security': 'security',
            'security_guide': 'security',
            'security_protocol': 'security',
            'confidential': 'security',
            
            # Compliance
            'compliance': 'compliance',
            'audit': 'compliance',
            'gdpr': 'compliance',
            'legal': 'compliance'
        }
        
        # Check each keyword
        for keyword, classification in classifications.items():
            if keyword in source_lower:
                return classification
        
        # Default to general if no specific classification found
        return 'general'
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Semantic search using vector similarity.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            where: Optional metadata filter
        
        Returns:
            Dictionary with ids, distances, documents, metadatas
        """
        # Generate query embedding
        query_embedding = self.embed_text(query)
        
        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Enrich metadata with classification if missing
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        for meta in metadatas:
            if "classification" not in meta or not meta.get("classification"):
                source = meta.get("source", "")
                meta["classification"] = self._get_classification_for_source(source)
        
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": metadatas
        }
    
    def get_by_ids(self, doc_ids: List[str]) -> Dict[str, Any]:
        """Get documents by IDs."""
        results = self.collection.get(
            ids=doc_ids,
            include=["documents", "metadatas", "embeddings"]
        )
        return results
    
    def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents by IDs."""
        if doc_ids:
            self.collection.delete(ids=doc_ids)
            print(f"Deleted {len(doc_ids)} documents from vector store")
    
    def count(self) -> int:
        """Get total document count."""
        return self.collection.count()
    
    def reset(self) -> None:
        """Delete all documents in collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "RAG system embeddings"}
        )
        print(f"Reset collection: {self.collection_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "collection_name": self.collection_name,
            "total_documents": self.count(),
            "embedding_dimension": self.embedding_model.get_sentence_embedding_dimension(),
            "embedding_model": self.embedding_model._model_card_data.model_name if hasattr(self.embedding_model, '_model_card_data') else "unknown",
            "persist_directory": self.persist_directory
        }


class HybridRetriever:
    """
    Hybrid retriever combining vector search (Chroma) with metadata filtering (SQLite).
    """
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        sqlite_db  # RAGDatabase instance
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: ChromaVectorStore instance for semantic search
            sqlite_db: RAGDatabase instance for metadata queries
        """
        self.vector_store = vector_store
        self.sqlite_db = sqlite_db
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        classification: str = None,
        min_access_level: int = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: vector search + RBAC filtering.
        
        Args:
            query: Search query
            top_k: Number of results
            classification: Filter by classification
            min_access_level: Minimum access level
        
        Returns:
            List of document dictionaries with full metadata from SQLite
        """
        # Step 1: Vector search in Chroma (get more candidates for filtering)
        vector_results = self.vector_store.search(
            query=query,
            n_results=top_k * 3  # Get more candidates for filtering
        )
        
        if not vector_results["ids"]:
            return []
        
        # Step 2: Get full metadata from SQLite for each doc_id
        doc_ids = vector_results["ids"]
        documents_with_metadata = []
        
        for i, doc_id in enumerate(doc_ids):
            # Query SQLite for full metadata
            docs = self.sqlite_db.select("documents", where={"doc_id": doc_id})
            
            if docs:
                doc = docs[0]
                
                # Apply RBAC filters
                if classification and doc.get("classification") != classification:
                    continue
                
                if min_access_level and doc.get("min_access_level", 99) > min_access_level:
                    continue
                
                # Add vector similarity score
                doc["similarity_score"] = 1.0 - vector_results["distances"][i]  # Convert distance to similarity
                doc["vector_rank"] = i + 1
                
                documents_with_metadata.append(doc)
                
                # Stop when we have enough results
                if len(documents_with_metadata) >= top_k:
                    break
        
        return documents_with_metadata
