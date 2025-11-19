"""
Vector Store Abstraction Layer
Provides abstract interface for all vector database operations (Chroma).
Decouples agents from direct Chroma client calls.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import chromadb
from chromadb.config import Settings
import json


class VectorStoreType(Enum):
    """Vector store types."""
    CHROMA = "chroma"
    FAISS = "faiss"
    WEAVIATE = "weaviate"


@dataclass
class Document:
    """Represents a document in vector store."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Represents a search result."""
    document_id: str
    content: str
    metadata: Dict[str, Any]
    distance: float
    similarity_score: float


class BaseVectorStore(ABC):
    """Abstract base class for vector store implementations."""
    
    @abstractmethod
    def ingest(self, documents: List[Document], namespace: str) -> List[str]:
        """Ingest documents into vector store."""
        pass
    
    @abstractmethod
    def search(self, query: str, namespace: str, top_k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search documents in vector store."""
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str, namespace: str) -> Optional[Document]:
        """Retrieve document by ID."""
        pass
    
    @abstractmethod
    def delete_document(self, doc_id: str, namespace: str) -> bool:
        """Delete document from vector store."""
        pass
    
    @abstractmethod
    def update_document(self, doc_id: str, namespace: str, document: Document) -> bool:
        """Update document in vector store."""
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """List all collections."""
        pass
    
    @abstractmethod
    def get_collection_stats(self, namespace: str) -> Dict[str, Any]:
        """Get collection statistics."""
        pass
    
    @abstractmethod
    def delete_collection(self, namespace: str) -> bool:
        """Delete entire collection."""
        pass


class ChromaVectorStore(BaseVectorStore):
    """Chroma vector store implementation."""
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """Initialize Chroma client."""
        self.settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False,
        )
        self.client = chromadb.Client(self.settings)
        self.persist_directory = persist_directory
    
    def ingest(self, documents: List[Document], namespace: str) -> List[str]:
        """Ingest documents into Chroma collection."""
        collection = self.client.get_or_create_collection(
            name=namespace,
            metadata={"hnsw:space": "cosine"}
        )
        
        ids = []
        documents_list = []
        metadatas = []
        
        for doc in documents:
            ids.append(doc.id)
            documents_list.append(doc.content)
            metadatas.append(doc.metadata)
        
        collection.add(
            ids=ids,
            documents=documents_list,
            metadatas=metadatas
        )
        
        return ids
    
    def search(self, query: str, namespace: str, top_k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search documents in Chroma collection."""
        try:
            collection = self.client.get_collection(name=namespace)
        except Exception as e:
            print(f"Collection {namespace} not found: {e}")
            return []
        
        where_filter = None
        if filters:
            where_filter = filters
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )
        
        search_results = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0.0
                # Convert distance to similarity score (0-1)
                similarity_score = 1 / (1 + distance) if distance >= 0 else 0.5
                
                search_results.append(SearchResult(
                    document_id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=distance,
                    similarity_score=similarity_score
                ))
        
        return search_results
    
    def get_document(self, doc_id: str, namespace: str) -> Optional[Document]:
        """Retrieve document by ID from Chroma."""
        try:
            collection = self.client.get_collection(name=namespace)
            result = collection.get(ids=[doc_id])
            
            if result["ids"] and len(result["ids"]) > 0:
                return Document(
                    id=doc_id,
                    content=result["documents"][0] if result["documents"] else "",
                    metadata=result["metadatas"][0] if result["metadatas"] else {}
                )
        except Exception as e:
            print(f"Error retrieving document {doc_id}: {e}")
        
        return None
    
    def delete_document(self, doc_id: str, namespace: str) -> bool:
        """Delete document from Chroma collection."""
        try:
            collection = self.client.get_collection(name=namespace)
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False
    
    def update_document(self, doc_id: str, namespace: str, document: Document) -> bool:
        """Update document in Chroma collection."""
        try:
            collection = self.client.get_collection(name=namespace)
            collection.update(
                ids=[doc_id],
                documents=[document.content],
                metadatas=[document.metadata]
            )
            return True
        except Exception as e:
            print(f"Error updating document {doc_id}: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """List all Chroma collections."""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []
    
    def get_collection_stats(self, namespace: str) -> Dict[str, Any]:
        """Get Chroma collection statistics."""
        try:
            collection = self.client.get_collection(name=namespace)
            count = collection.count()
            
            return {
                "namespace": namespace,
                "document_count": count,
                "embedding_dim": None,  # Chroma doesn't expose this directly
                "indexed": True
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {}
    
    def delete_collection(self, namespace: str) -> bool:
        """Delete entire Chroma collection."""
        try:
            self.client.delete_collection(name=namespace)
            return True
        except Exception as e:
            print(f"Error deleting collection {namespace}: {e}")
            return False
    
    def get_or_create_collection(self, namespace: str) -> Any:
        """Get or create a collection (for direct access if needed)."""
        return self.client.get_or_create_collection(
            name=namespace,
            metadata={"hnsw:space": "cosine"}
        )
    
    def persist(self):
        """Persist Chroma database."""
        try:
            self.client.persist()
        except Exception as e:
            print(f"Error persisting Chroma: {e}")


class VectorStoreManager:
    """Manages vector store abstraction and operations."""
    
    def __init__(self, store_type: str = "chroma", persist_directory: str = "data/chroma_db"):
        """Initialize vector store manager."""
        if store_type.lower() == "chroma":
            self.store = ChromaVectorStore(persist_directory)
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
        
        self.store_type = store_type
    
    # Ingestion operations
    def ingest_documents(self, documents: List[Dict[str, Any]], namespace: str) -> List[str]:
        """
        Ingest documents into vector store.
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
            namespace: Collection name
        
        Returns:
            List of ingested document IDs
        """
        doc_objects = [
            Document(
                id=doc.get("id"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            )
            for doc in documents
        ]
        
        return self.store.ingest(doc_objects, namespace)
    
    def ingest_single_document(self, doc_id: str, content: str, 
                               metadata: Dict[str, Any], namespace: str) -> bool:
        """Ingest a single document."""
        doc = Document(id=doc_id, content=content, metadata=metadata)
        result = self.store.ingest([doc], namespace)
        return len(result) > 0
    
    # Retrieval operations
    def search(self, query: str, namespace: str, top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search vector store.
        
        Args:
            query: Search query string
            namespace: Collection name
            top_k: Number of results to return
            filters: Optional Chroma where filters
        
        Returns:
            List of search results with scores
        """
        results = self.store.search(query, namespace, top_k, filters)
        
        return [
            {
                "document_id": r.document_id,
                "content": r.content,
                "metadata": r.metadata,
                "similarity_score": r.similarity_score,
                "distance": r.distance
            }
            for r in results
        ]
    
    def search_with_metadata_filter(self, query: str, namespace: str, 
                                    filter_dict: Dict[str, Any], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search with metadata filtering."""
        return self.search(query, namespace, top_k, filter_dict)
    
    def search_by_department(self, query: str, namespace: str, 
                            department_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search documents by department."""
        filters = {"department_id": {"$eq": department_id}}
        return self.search_with_metadata_filter(query, namespace, filters, top_k)
    
    def search_by_access_level(self, query: str, namespace: str, 
                               access_level: int, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search documents by access level."""
        filters = {"min_access_level": {"$lte": access_level}}
        return self.search_with_metadata_filter(query, namespace, filters, top_k)
    
    # Document operations
    def get_document(self, doc_id: str, namespace: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        doc = self.store.get_document(doc_id, namespace)
        if doc:
            return {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata
            }
        return None
    
    def delete_document(self, doc_id: str, namespace: str) -> bool:
        """Delete document."""
        return self.store.delete_document(doc_id, namespace)
    
    def update_document(self, doc_id: str, content: str, 
                        metadata: Dict[str, Any], namespace: str) -> bool:
        """Update document."""
        doc = Document(id=doc_id, content=content, metadata=metadata)
        return self.store.update_document(doc_id, namespace, doc)
    
    # Collection operations
    def list_collections(self) -> List[str]:
        """List all collections."""
        return self.store.list_collections()
    
    def get_collection_stats(self, namespace: str) -> Dict[str, Any]:
        """Get collection statistics."""
        return self.store.get_collection_stats(namespace)
    
    def delete_collection(self, namespace: str) -> bool:
        """Delete entire collection."""
        return self.store.delete_collection(namespace)
    
    def create_collection(self, namespace: str) -> bool:
        """Create a new collection."""
        try:
            self.store.get_or_create_collection(namespace)
            return True
        except Exception as e:
            print(f"Error creating collection {namespace}: {e}")
            return False
    
    # Batch operations
    def batch_search(self, queries: List[str], namespace: str, 
                     top_k: int = 10) -> List[List[Dict[str, Any]]]:
        """Search multiple queries."""
        return [self.search(q, namespace, top_k) for q in queries]
    
    def batch_delete(self, doc_ids: List[str], namespace: str) -> int:
        """Delete multiple documents."""
        deleted = 0
        for doc_id in doc_ids:
            if self.delete_document(doc_id, namespace):
                deleted += 1
        return deleted
    
    # Statistics and maintenance
    def get_namespace_statistics(self, namespace: str) -> Dict[str, Any]:
        """Get detailed namespace statistics."""
        stats = self.get_collection_stats(namespace)
        return stats
    
    def list_namespace_documents(self, namespace: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents in namespace (if supported by backend)."""
        # Note: Chroma doesn't support direct listing, so we'll return empty
        # In a real implementation, this would query the database
        return []
    
    def persist(self):
        """Persist vector store to disk."""
        if hasattr(self.store, 'persist'):
            self.store.persist()
