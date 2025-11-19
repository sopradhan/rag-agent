"""
Ingestion Tools
Tools for document processing, chunking, metadata extraction, and RBAC classification
"""
import hashlib
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)


@tool
def chunk_document_tool(text: str, strategy: str = "recursive", 
                       chunk_size: int = 500, overlap: int = 50) -> str:
    """
    Chunk document using specified strategy.
    
    Args:
        text: Document text to chunk
        strategy: Chunking strategy ('recursive', 'character', 'token')
        chunk_size: Target chunk size
        overlap: Overlap between chunks
        
    Returns:
        JSON string with list of chunks
    """
    try:
        if strategy == "recursive":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        elif strategy == "character":
            splitter = CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                separator="\n"
            )
        elif strategy == "token":
            splitter = TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap
            )
        
        chunks = splitter.split_text(text)
        
        result = [
            {
                "chunk_id": f"chunk_{i}",
                "text": chunk,
                "strategy": strategy,
                "size": len(chunk),
                "index": i
            }
            for i, chunk in enumerate(chunks)
        ]
        
        return json.dumps({
            "success": True,
            "num_chunks": len(result),
            "chunks": result
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def extract_metadata_tool(text: str, llm_service) -> str:
    """
    Extract metadata from document using LLM.
    
    Args:
        text: Document text
        llm_service: LLM service instance
        
    Returns:
        JSON string with extracted metadata
    """
    try:
        prompt = f"""
        Analyze this document and extract the following metadata:
        1. Title: A concise title for the document
        2. Summary: A 2-3 sentence summary
        3. Keywords: 5-10 important keywords
        4. Topics: Main topics covered
        5. Document type: Type of document (manual, policy, technical_doc, etc.)
        
        Document excerpt (first 2000 chars):
        {text[:2000]}
        
        Respond ONLY with valid JSON in this format:
        {{
            "title": "...",
            "summary": "...",
            "keywords": ["keyword1", "keyword2", ...],
            "topics": ["topic1", "topic2", ...],
            "doc_type": "..."
        }}
        """
        
        result = llm_service.generate_json(prompt)
        
        return json.dumps({
            "success": True,
            "metadata": result
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def classify_rbac_tool(text: str, llm_service, rbac_config: dict) -> str:
    """
    Classify document for RBAC using LLM inference.
    
    Args:
        text: Document text
        llm_service: LLM service instance
        rbac_config: RBAC configuration dict
        
    Returns:
        JSON string with RBAC classification
    """
    try:
        # Subject classification
        subject_prompt = rbac_config['classification_prompts']['subject_classification'].format(
            text=text[:2000]
        )
        subject_result = llm_service.generate_json(subject_prompt)
        
        # Sensitivity classification
        sensitivity_prompt = rbac_config['classification_prompts']['sensitivity_classification'].format(
            text=text[:2000]
        )
        sensitivity_result = llm_service.generate_json(sensitivity_prompt)
        
        # Map to CDR codes
        subject = subject_result.get('subject', 'general')
        sensitivity = sensitivity_result.get('sensitivity', 'internal')
        
        # Determine required roles based on subject and sensitivity
        required_roles = _map_to_cdr_codes(subject, sensitivity, rbac_config)
        
        return json.dumps({
            "success": True,
            "classification": {
                "subject": subject,
                "subject_confidence": subject_result.get('confidence', 0.5),
                "subject_reasoning": subject_result.get('reasoning', ''),
                "sensitivity": sensitivity,
                "sensitivity_confidence": sensitivity_result.get('confidence', 0.5),
                "sensitivity_reasoning": sensitivity_result.get('reasoning', ''),
                "required_roles": required_roles
            }
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def _map_to_cdr_codes(subject: str, sensitivity: str, rbac_config: dict) -> List[str]:
    """
    Map subject and sensitivity to CDR codes
    
    Args:
        subject: Document subject area
        sensitivity: Sensitivity level
        rbac_config: RBAC configuration
        
    Returns:
        List of CDR codes that should have access
    """
    # Get department IDs for subject
    subject_info = rbac_config.get('subject_areas', {}).get(subject, {})
    default_depts = subject_info.get('default_departments', [1])  # Default to general
    
    # Get minimum role ID for sensitivity
    sensitivity_info = rbac_config.get('sensitivity_levels', {}).get(sensitivity, {})
    min_role_id = sensitivity_info.get('min_role_id', 2)  # Default to Associate
    
    # Find matching CDR codes from role_mappings
    required_codes = []
    for cdr_code, mapping in rbac_config.get('role_mappings', {}).items():
        dept_id = mapping.get('department_id')
        role_id = mapping.get('role_id')
        
        # Include if department matches AND role level is sufficient
        if dept_id in default_depts and role_id >= min_role_id:
            required_codes.append(cdr_code)
    
    return required_codes


@tool
def generate_embeddings_tool(chunks: str, llm_service) -> str:
    """
    Generate embeddings for document chunks.
    
    Args:
        chunks: JSON string with chunks from chunk_document_tool
        llm_service: LLM service instance
        
    Returns:
        JSON string with embeddings
    """
    try:
        chunks_data = json.loads(chunks)
        
        if not chunks_data.get('success'):
            return chunks  # Return error from chunking
        
        chunk_list = chunks_data['chunks']
        texts = [chunk['text'] for chunk in chunk_list]
        
        # Generate embeddings
        embeddings = llm_service.generate_embeddings(texts)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunk_list):
            chunk['embedding'] = embeddings[i]
        
        return json.dumps({
            "success": True,
            "num_embeddings": len(embeddings),
            "chunks": chunk_list
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def store_embeddings_tool(doc_id: str, chunks_with_embeddings: str, 
                         vectordb_service, db_service,
                         rbac_classification: str,
                         metadata: Optional[dict] = None) -> str:
    """
    Store embeddings in vector database and metadata in SQLite.
    
    Args:
        doc_id: Document ID
        chunks_with_embeddings: JSON string from generate_embeddings_tool
        vectordb_service: Vector DB service instance
        db_service: Database service instance
        rbac_classification: JSON string from classify_rbac_tool
        metadata: Optional document metadata
        
    Returns:
        JSON string with storage results
    """
    try:
        chunks_data = json.loads(chunks_with_embeddings)
        rbac_data = json.loads(rbac_classification)
        
        if not chunks_data.get('success') or not rbac_data.get('success'):
            return json.dumps({
                "success": False,
                "error": "Invalid input data"
            })
        
        chunks = chunks_data['chunks']
        classification = rbac_data['classification']
        
        # Prepare data for vector DB
        ids = [f"{doc_id}_{chunk['chunk_id']}" for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [
            {
                "document_id": doc_id,
                "chunk_index": chunk['index'],
                "chunk_size": chunk['size'],
                "subject": classification['subject'],
                "sensitivity": classification['sensitivity']
            }
            for chunk in chunks
        ]
        
        # Store in vector database
        vectordb_service.insert_embeddings(ids, embeddings, metadatas, documents)
        
        # Store embedding metadata in SQLite
        for i, chunk in enumerate(chunks):
            chunk_id = ids[i]
            db_service.insert_embedding_metadata(
                document_id=doc_id,
                chunk_id=chunk_id,
                chunk_strategy=chunk.get('strategy', 'recursive'),
                chunk_size=chunk['size'],
                overlap=0,  # TODO: Get from chunking params
                embedding_model="sentence-transformers",  # TODO: Get from config
                embedding_version="v1"
            )
        
        # Store RBAC permissions
        for cdr_code in classification['required_roles']:
            db_service.assign_document_permission(
                doc_id=doc_id,
                cdr_code=cdr_code,
                sensitivity=classification['sensitivity'],
                subject=classification['subject'],
                assigned_by='llm_inference'
            )
        
        # Store document metadata if provided
        if metadata:
            # Store in documents table
            db_service.execute("""
                INSERT OR REPLACE INTO documents (id, title, source, doc_type)
                VALUES (?, ?, ?, ?)
            """, (
                doc_id,
                metadata.get('title', 'Untitled'),
                metadata.get('source', 'unknown'),
                metadata.get('doc_type', 'document')
            ))
        
        return json.dumps({
            "success": True,
            "doc_id": doc_id,
            "num_chunks": len(chunks),
            "num_permissions": len(classification['required_roles']),
            "subject": classification['subject'],
            "sensitivity": classification['sensitivity']
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
