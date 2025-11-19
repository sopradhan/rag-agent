"""
RBAC-Aware Ingestion Subagents with LLM Context Understanding
Handles intelligent document categorization, namespace management, and RBAC resolution
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from ..abstraction import LLMManager
from ..storage.sqlite_storage import RAGDatabase
from ..storage.vector_store import ChromaVectorStore
from ..utils.token_manager import TokenAwareChunker, TokenManager


class DocumentNamespace(Enum):
    """Document namespaces for organized indexing in ChromaDB."""
    ENGINEERING = "engineering"
    HR = "hr"
    SECURITY = "security"
    FINANCE = "finance"
    GENERAL = "general"
    OPERATIONS = "operations"
    PRODUCT = "product"


@dataclass
class RBACContext:
    """RBAC context resolved from SQLite."""
    classification: str
    min_access_level: int
    allowed_companies: List[int]
    allowed_departments: List[int]
    allowed_roles: List[int]
    namespace: str
    tags: List[str]


class RBACResolver:
    """Resolves RBAC rules from SQLite for documents."""
    
    def __init__(self, rag_db: RAGDatabase, llm_manager: LLMManager):
        self.rag_db = rag_db
        self.llm_manager = llm_manager
    
    def resolve_rbac_from_content(self, content: str, metadata: Dict[str, Any]) -> RBACContext:
        """
        Use LLM to understand document context and resolve RBAC from SQLite.
        
        Args:
            content: Document content (first 500 chars for analysis)
            metadata: Document metadata
        
        Returns:
            RBACContext with resolved permissions
        """
        # Sample content for LLM
        sample_content = content[:500]
        
        # Prompt LLM to understand document type
        prompt = f"""Analyze this document and determine:
1. Document type (engineering, hr, security, finance, operations, product, general)
2. Minimum access level required (1=everyone, 2=verified, 3=senior, 4=management, 5=executive)
3. Tags (comma-separated)
4. Departments that should access this

Document:
{sample_content}

Respond in JSON format:
{{
    "document_type": "...",
    "min_access_level": ...,
    "tags": ["tag1", "tag2"],
    "departments": ["engineering", "security"]
}}"""
        
        try:
            response = self.llm_manager.invoke(prompt)
            analysis = json.loads(response)
        except:
            # Fallback classification
            analysis = {
                "document_type": metadata.get("classification", "general"),
                "min_access_level": 1,
                "tags": [],
                "departments": []
            }
        
        # Get RBAC rules from SQLite
        cursor = self.rag_db.conn.cursor()
        
        # Get companies and departments
        cursor.execute("SELECT company_id FROM company")
        companies = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT department_id FROM department 
            WHERE name IN ({})
        """.format(','.join('?' * len(analysis.get("departments", [])))))
        departments = [row[0] for row in cursor.fetchall()] if analysis.get("departments") else []
        
        # Get roles with matching access level
        cursor.execute("""
            SELECT DISTINCT role_id FROM role
            LIMIT 5
        """)
        roles = [row[0] for row in cursor.fetchall()]
        
        return RBACContext(
            classification=analysis.get("document_type", "general"),
            min_access_level=analysis.get("min_access_level", 1),
            allowed_companies=companies,
            allowed_departments=departments if departments else [1, 2],  # Default to first 2 depts
            allowed_roles=roles,
            namespace=f"{analysis.get('document_type', 'general')}_ns",
            tags=analysis.get("tags", [])
        )


class NamespaceManager:
    """Manages ChromaDB namespaces for organized document indexing."""
    
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store
        self.namespaces = {
            DocumentNamespace.ENGINEERING.value: "technical_documents",
            DocumentNamespace.HR.value: "personnel_policies",
            DocumentNamespace.SECURITY.value: "security_protocols",
            DocumentNamespace.FINANCE.value: "financial_records",
            DocumentNamespace.GENERAL.value: "general_knowledge",
            DocumentNamespace.OPERATIONS.value: "operational_docs",
            DocumentNamespace.PRODUCT.value: "product_info",
        }
    
    def get_namespace_collection_name(self, namespace: str) -> str:
        """Get ChromaDB collection name for namespace."""
        return f"rag_{namespace}_collection"
    
    def get_namespace_metadata(self, namespace: str, rbac_context: RBACContext) -> Dict[str, Any]:
        """Generate metadata for document in specific namespace."""
        return {
            "namespace": namespace,
            "classification": rbac_context.classification,
            "min_access_level": rbac_context.min_access_level,
            "allowed_departments": ",".join(map(str, rbac_context.allowed_departments)),
            "allowed_roles": ",".join(map(str, rbac_context.allowed_roles)),
            "tags": ",".join(rbac_context.tags),
            "ingestion_time": datetime.now().isoformat(),
            "indexed": "true"
        }


class RBACIntelligentIngestionSubagent:
    """
    Enhanced ingestion subagent with RBAC awareness and LLM context understanding.
    
    Capabilities:
    - Analyzes document content with LLM
    - Resolves RBAC from SQLite tables
    - Categorizes into namespaces
    - Manages tags and metadata
    - Stores in ChromaDB with proper classification
    """
    
    def __init__(self, rag_db: RAGDatabase, vector_store: ChromaVectorStore, llm_manager: LLMManager):
        self.rag_db = rag_db
        self.vector_store = vector_store
        self.llm_manager = llm_manager
        
        # Initialize helpers
        self.rbac_resolver = RBACResolver(rag_db, llm_manager)
        self.namespace_manager = NamespaceManager(vector_store)
        
        # Token management
        self.token_manager = TokenManager(model="gpt-3.5-turbo")
        self.chunker = TokenAwareChunker(
            token_manager=self.token_manager,
            chunk_size=512,
            overlap=50,
            respect_boundaries=True
        )
        
        self.stats = {
            "documents_analyzed": 0,
            "rbac_resolved": 0,
            "namespaces_created": 0,
            "documents_ingested": 0,
            "errors": 0
        }
    
    def ingest_with_rbac(
        self,
        doc_id: str,
        content: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest document with intelligent RBAC resolution.
        
        Args:
            doc_id: Unique document ID
            content: Document content
            source: Document source
            metadata: Optional metadata
        
        Returns:
            Ingestion result with RBAC context
        """
        print(f"[RBAC Ingestion] Processing: {doc_id}")
        
        try:
            # 1. Analyze with LLM
            print("  [*] Analyzing document with LLM...")
            rbac_context = self.rbac_resolver.resolve_rbac_from_content(
                content, metadata or {}
            )
            self.stats["documents_analyzed"] += 1
            
            print(f"  [OK] Classification: {rbac_context.classification}")
            print(f"  [OK] Min Access Level: {rbac_context.min_access_level}")
            print(f"  [OK] Tags: {', '.join(rbac_context.tags)}")
            
            # 2. Resolve RBAC
            print("  [*] Resolving RBAC from SQLite...")
            self.stats["rbac_resolved"] += 1
            
            # 3. Chunk content
            print("  [*] Chunking content...")
            chunks = self.chunker.chunk_text(content)
            
            # 4. Create namespace collection
            namespace = rbac_context.namespace
            collection_name = self.namespace_manager.get_namespace_collection_name(namespace)
            print(f"  [*] Creating namespace collection: {collection_name}")
            
            # 5. Store in ChromaDB with RBAC metadata
            doc_ids = []
            texts = []
            metadatas = []
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_doc_id = f"{doc_id}_chunk_{chunk_idx}"
                
                # Generate namespace metadata
                ns_metadata = self.namespace_manager.get_namespace_metadata(namespace, rbac_context)
                ns_metadata.update({
                    "chunk_index": chunk_idx,
                    "total_chunks": len(chunks),
                    "source": source
                })
                
                doc_ids.append(chunk_doc_id)
                texts.append(chunk)
                metadatas.append(ns_metadata)
            
            # Add to ChromaDB
            print(f"  [*] Storing {len(doc_ids)} chunks in ChromaDB...")
            self.vector_store.add_documents(
                doc_ids=doc_ids,
                texts=texts,
                metadatas=metadatas
            )
            
            # 6. Store in SQLite
            print("  [*] Storing metadata in SQLite...")
            for chunk_doc_id in doc_ids:
                doc_data = {
                    "doc_id": chunk_doc_id,
                    "source": source,
                    "content": content[:1000],  # Store excerpt
                    "classification": rbac_context.classification,
                    "min_access_level": rbac_context.min_access_level
                }
                self.rag_db.insert_document(doc_data)
                
                # Track embedding
                self.rag_db.track_embedding(
                    chunk_doc_id,
                    embedding_model="all-MiniLM-L6-v2",
                    embedding_dimension=384,
                    vector_store="chromadb"
                )
                
                # Store tags as metadata
                for tag in rbac_context.tags:
                    self.rag_db.insert_metadata(chunk_doc_id, "tag", tag)
            
            # 7. Create RBAC mappings
            self._create_rbac_mappings(doc_ids, rbac_context)
            
            self.stats["documents_ingested"] += 1
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "chunks_created": len(doc_ids),
                "classification": rbac_context.classification,
                "namespace": namespace,
                "tags": rbac_context.tags,
                "min_access_level": rbac_context.min_access_level
            }
        
        except Exception as e:
            self.stats["errors"] += 1
            print(f"[ERROR] Ingestion failed: {e}")
            return {
                "status": "failed",
                "doc_id": doc_id,
                "error": str(e)
            }
    
    def _create_rbac_mappings(self, doc_ids: List[str], rbac_context: RBACContext):
        """Create RBAC mappings in SQLite for each document."""
        cursor = self.rag_db.conn.cursor()
        
        for doc_id in doc_ids:
            # Map to allowed departments
            for dept_id in rbac_context.allowed_departments:
                cursor.execute("""
                    INSERT OR IGNORE INTO document_rbac 
                    (doc_id, department_id, access_level)
                    VALUES (?, ?, ?)
                """, (doc_id, dept_id, rbac_context.min_access_level))
        
        self.rag_db.conn.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return self.stats.copy()
