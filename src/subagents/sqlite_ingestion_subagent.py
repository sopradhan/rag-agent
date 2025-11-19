"""
SQLite3 Data Source Ingestion Subagent
Extracts data from SQLite databases and converts to RAG documents.
Supports table-based and query-based extraction.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from ..storage.sqlite_storage import RAGDatabase
from ..storage.vector_store import ChromaVectorStore
from ..utils.token_manager import TokenAwareChunker, TokenManager


@dataclass
class SQLiteSource:
    """Represents a SQLite data source configuration."""
    db_path: str
    table_name: Optional[str] = None
    query: Optional[str] = None
    text_columns: List[str] = None
    metadata_columns: List[str] = None
    classification: str = "general"
    min_access_level: int = 1


class SQLiteIngestionSubagent:
    """
    Ingests data from SQLite3 databases into the RAG system.
    
    Features:
    - Table-based extraction (entire tables)
    - Query-based extraction (custom SQL)
    - Document generation from records
    - Automatic chunking for large text fields
    - Metadata extraction and RBAC assignment
    - Embedding generation and storage
    """
    
    def __init__(self, rag_db: RAGDatabase, vector_store: ChromaVectorStore):
        """
        Initialize SQLite ingestion subagent.
        
        Args:
            rag_db: RAGDatabase instance for storing metadata
            vector_store: ChromaVectorStore for embeddings
        """
        self.rag_db = rag_db
        self.vector_store = vector_store
        
        # Token management for chunking
        self.token_manager = TokenManager(model="gpt-3.5-turbo")
        self.chunker = TokenAwareChunker(
            token_manager=self.token_manager,
            chunk_size=512,
            overlap=50,
            respect_boundaries=True
        )
        
        self.stats = {
            "records_processed": 0,
            "documents_created": 0,
            "errors": 0,
            "total_tokens": 0
        }
    
    def ingest_from_table(
        self,
        db_path: str,
        table_name: str,
        text_columns: List[str],
        metadata_columns: Optional[List[str]] = None,
        classification: str = "general",
        min_access_level: int = 1,
        chunk_strategy: str = "per_record"
    ) -> Dict[str, Any]:
        """
        Ingest data from a SQLite table.
        
        Args:
            db_path: Path to SQLite database
            table_name: Table to ingest
            text_columns: Columns containing text content
            metadata_columns: Columns for metadata extraction
            classification: Document classification
            min_access_level: RBAC minimum access level
            chunk_strategy: "per_record" or "combined"
        
        Returns:
            Ingestion result with statistics
        """
        print(f"[SQLite Ingestion] Reading table: {table_name}")
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all records from table
            cursor.execute(f"SELECT * FROM {table_name}")
            records = cursor.fetchall()
            
            print(f"  [*] Found {len(records)} records")
            
            documents = []
            doc_ids = []
            texts = []
            metadatas = []
            
            for record in records:
                record_dict = dict(record)
                
                # Extract text content
                text_content = self._combine_text_fields(
                    record_dict, text_columns
                )
                
                if not text_content or not text_content.strip():
                    self.stats["errors"] += 1
                    continue
                
                # Extract metadata
                metadata = self._extract_metadata(
                    record_dict, 
                    metadata_columns, 
                    table_name,
                    classification,
                    db_path
                )
                
                # Chunk text if needed
                if chunk_strategy == "per_record":
                    chunks = self.chunker.chunk_text(text_content)
                else:
                    chunks = [text_content]
                
                for chunk_idx, chunk in enumerate(chunks):
                    doc_id = self._generate_doc_id(
                        table_name,
                        record_dict,
                        chunk_idx
                    )
                    
                    documents.append({
                        "doc_id": doc_id,
                        "source": f"sqlite://{db_path}#{table_name}",
                        "content": chunk,
                        "chunk_id": chunk_idx,
                        "total_chunks": len(chunks),
                        "classification": classification,
                        "min_access_level": min_access_level
                    })
                    
                    doc_ids.append(doc_id)
                    texts.append(chunk)
                    metadatas.append(metadata)
                    
                    self.stats["documents_created"] += 1
                
                self.stats["records_processed"] += 1
            
            # Store in vector store and database
            if texts:
                print(f"  [*] Storing {len(texts)} document chunks in vector store...")
                self.vector_store.add_documents(
                    doc_ids=doc_ids,
                    texts=texts,
                    metadatas=metadatas
                )
                
                print(f"  [*] Storing metadata in RAG database...")
                for doc in documents:
                    self.rag_db.insert_document(doc)
            
            conn.close()
            
            return {
                "status": "success",
                "table": table_name,
                "records_processed": self.stats["records_processed"],
                "documents_created": self.stats["documents_created"],
                "errors": self.stats["errors"]
            }
        
        except Exception as e:
            print(f"[ERROR] Failed to ingest from table {table_name}: {e}")
            return {
                "status": "failed",
                "table": table_name,
                "error": str(e)
            }
    
    def ingest_from_query(
        self,
        db_path: str,
        query: str,
        text_columns: List[str],
        metadata_columns: Optional[List[str]] = None,
        classification: str = "general",
        min_access_level: int = 1,
        query_name: str = "custom_query"
    ) -> Dict[str, Any]:
        """
        Ingest data from a custom SQL query.
        
        Args:
            db_path: Path to SQLite database
            query: SQL query to execute
            text_columns: Result columns containing text
            metadata_columns: Result columns for metadata
            classification: Document classification
            min_access_level: RBAC minimum access level
            query_name: Name of this query for tracking
        
        Returns:
            Ingestion result with statistics
        """
        print(f"[SQLite Ingestion] Executing query: {query_name}")
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Execute query
            cursor.execute(query)
            records = cursor.fetchall()
            
            print(f"  [*] Found {len(records)} records from query")
            
            documents = []
            doc_ids = []
            texts = []
            metadatas = []
            
            for record_idx, record in enumerate(records):
                record_dict = dict(record)
                
                # Extract text content
                text_content = self._combine_text_fields(
                    record_dict, text_columns
                )
                
                if not text_content or not text_content.strip():
                    self.stats["errors"] += 1
                    continue
                
                # Extract metadata
                metadata = self._extract_metadata(
                    record_dict,
                    metadata_columns,
                    query_name,
                    classification,
                    db_path
                )
                
                # Chunk if needed
                chunks = self.chunker.chunk_text(text_content)
                
                for chunk_idx, chunk in enumerate(chunks):
                    doc_id = self._generate_doc_id(
                        query_name,
                        {"record_idx": record_idx},
                        chunk_idx
                    )
                    
                    documents.append({
                        "doc_id": doc_id,
                        "source": f"sqlite://{db_path}?{query_name}",
                        "content": chunk,
                        "chunk_id": chunk_idx,
                        "total_chunks": len(chunks),
                        "classification": classification,
                        "min_access_level": min_access_level
                    })
                    
                    doc_ids.append(doc_id)
                    texts.append(chunk)
                    metadatas.append(metadata)
                    
                    self.stats["documents_created"] += 1
                
                self.stats["records_processed"] += 1
            
            # Store in vector store and database
            if texts:
                print(f"  [*] Storing {len(texts)} document chunks...")
                self.vector_store.add_documents(
                    doc_ids=doc_ids,
                    texts=texts,
                    metadatas=metadatas
                )
                
                for doc in documents:
                    self.rag_db.insert_document(doc)
            
            conn.close()
            
            return {
                "status": "success",
                "query_name": query_name,
                "records_processed": self.stats["records_processed"],
                "documents_created": self.stats["documents_created"],
                "errors": self.stats["errors"]
            }
        
        except Exception as e:
            print(f"[ERROR] Query execution failed: {e}")
            return {
                "status": "failed",
                "query_name": query_name,
                "error": str(e)
            }
    
    def _combine_text_fields(
        self,
        record: Dict[str, Any],
        text_columns: List[str]
    ) -> str:
        """Combine multiple text columns into single document."""
        parts = []
        for col in text_columns:
            if col in record and record[col]:
                value = str(record[col])
                if value.strip():
                    parts.append(f"{col.title()}: {value}")
        
        return "\n".join(parts)
    
    def _extract_metadata(
        self,
        record: Dict[str, Any],
        metadata_columns: Optional[List[str]],
        source_name: str,
        classification: str,
        db_path: str
    ) -> Dict[str, Any]:
        """Extract metadata from record."""
        metadata = {
            "source": source_name,
            "classification": classification,
            "database": Path(db_path).name,
            "ingestion_time": datetime.now().isoformat()
        }
        
        if metadata_columns:
            for col in metadata_columns:
                if col in record:
                    value = record[col]
                    if value is not None:
                        metadata[f"field_{col}"] = str(value)
        
        return metadata
    
    def _generate_doc_id(
        self,
        source_name: str,
        record_dict: Dict[str, Any],
        chunk_idx: int
    ) -> str:
        """Generate unique document ID."""
        record_str = "_".join(
            f"{k}_{v}".replace(" ", "_")
            for k, v in list(record_dict.items())[:2]
        )
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"sqlite_{source_name}_{record_str}_{chunk_idx}_{timestamp}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.stats = {
            "records_processed": 0,
            "documents_created": 0,
            "errors": 0,
            "total_tokens": 0
        }
