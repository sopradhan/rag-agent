"""
Retrieval Tools
Tools for searching, permission checking, reranking, and answer synthesis
"""
import json
import hashlib
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


@tool
def permission_check_tool(user_id: str, chunk_ids: str, db_service) -> str:
    """
    Filter chunks based on user's RBAC permissions.
    
    Args:
        user_id: User identifier
        chunk_ids: JSON list of chunk IDs
        db_service: Database service instance
        
    Returns:
        JSON string with allowed chunk IDs
    """
    try:
        chunk_id_list = json.loads(chunk_ids)
        
        # Get user's CDR codes
        user_roles = set(db_service.get_user_roles(user_id))
        
        if not user_roles:
            return json.dumps({
                "success": False,
                "error": f"No roles found for user: {user_id}",
                "allowed_chunks": []
            })
        
        allowed_chunks = []
        denied_count = 0
        
        for chunk_id in chunk_id_list:
            # Extract document ID from chunk ID
            doc_id = chunk_id.rsplit('_chunk_', 1)[0]
            
            # Get required permissions
            required_roles = set(db_service.get_document_permissions(doc_id))
            
            # Check if user has any matching role
            if user_roles & required_roles:  # Set intersection
                allowed_chunks.append(chunk_id)
            else:
                denied_count += 1
        
        return json.dumps({
            "success": True,
            "user_id": user_id,
            "total_chunks": len(chunk_id_list),
            "allowed_chunks": allowed_chunks,
            "denied_count": denied_count,
            "user_roles": list(user_roles)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "allowed_chunks": []
        })


@tool
def vector_search_tool(query: str, top_k: int, llm_service, vectordb_service,
                      where_filter: Optional[str] = None) -> str:
    """
    Search vector database for similar chunks.
    
    Args:
        query: Search query text
        top_k: Number of results to return
        llm_service: LLM service instance
        vectordb_service: Vector DB service instance
        where_filter: Optional JSON filter for metadata
        
    Returns:
        JSON string with search results
    """
    try:
        # Generate query embedding
        query_embedding = llm_service.generate_embedding(query)
        
        # Parse filter if provided
        filter_dict = json.loads(where_filter) if where_filter else None
        
        # Search vector database
        results = vectordb_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            where_filter=filter_dict
        )
        
        # Format results
        chunk_ids = results['ids'][0] if results['ids'] else []
        distances = results['distances'][0] if results['distances'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        documents = results['documents'][0] if results['documents'] else []
        
        search_results = [
            {
                "chunk_id": chunk_ids[i],
                "text": documents[i],
                "distance": distances[i],
                "similarity": 1 - distances[i],  # Convert distance to similarity
                "metadata": metadatas[i]
            }
            for i in range(len(chunk_ids))
        ]
        
        return json.dumps({
            "success": True,
            "query": query,
            "num_results": len(search_results),
            "results": search_results,
            "chunk_ids": chunk_ids
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "results": []
        })


@tool
def rerank_results_tool(query: str, search_results: str, top_n: int = 5) -> str:
    """
    Rerank search results using cross-encoder or LLM.
    
    Args:
        query: Original query
        search_results: JSON string from vector_search_tool
        top_n: Number of top results to return after reranking
        
    Returns:
        JSON string with reranked results
    """
    try:
        results_data = json.loads(search_results)
        
        if not results_data.get('success'):
            return search_results  # Return original error
        
        results = results_data['results']
        
        # Simple reranking based on similarity scores
        # TODO: Implement actual cross-encoder or LLM-based reranking
        reranked = sorted(results, key=lambda x: x['similarity'], reverse=True)[:top_n]
        
        return json.dumps({
            "success": True,
            "query": query,
            "num_results": len(reranked),
            "results": reranked
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "results": []
        })


@tool
def synthesize_answer_tool(query: str, reranked_results: str, llm_service) -> str:
    """
    Synthesize final answer from retrieved chunks.
    
    Args:
        query: Original query
        reranked_results: JSON string from rerank_results_tool
        llm_service: LLM service instance
        
    Returns:
        JSON string with synthesized answer
    """
    try:
        results_data = json.loads(reranked_results)
        
        if not results_data.get('success'):
            return json.dumps({
                "success": False,
                "error": "No valid results to synthesize"
            })
        
        results = results_data['results']
        
        if not results:
            return json.dumps({
                "success": True,
                "answer": "I don't have enough information to answer that question.",
                "sources": []
            })
        
        # Build context from retrieved chunks
        context = "\n\n".join([
            f"[Source {i+1}]\n{r['text']}"
            for i, r in enumerate(results)
        ])
        
        # Generate answer
        prompt = f"""Based on the following context, answer the user's question.
        
Context:
{context}

Question: {query}

Instructions:
- Provide a clear, concise answer
- Cite sources using [Source N] notation
- If the context doesn't fully answer the question, say so
- Be accurate and don't make up information

Answer:"""
        
        answer = llm_service.generate_response(prompt)
        
        # Extract source information
        sources = [
            {
                "index": i + 1,
                "chunk_id": r['chunk_id'],
                "similarity": r['similarity'],
                "metadata": r.get('metadata', {})
            }
            for i, r in enumerate(results)
        ]
        
        return json.dumps({
            "success": True,
            "query": query,
            "answer": answer,
            "sources": sources,
            "num_sources": len(sources)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def graph_expand_tool(initial_results: str, vectordb_service, max_depth: int = 1) -> str:
    """
    Expand context by finding related chunks (graph expansion).
    
    Args:
        initial_results: JSON string with initial search results
        vectordb_service: Vector DB service instance
        max_depth: Maximum depth for expansion
        
    Returns:
        JSON string with expanded results
    """
    try:
        results_data = json.loads(initial_results)
        
        if not results_data.get('success'):
            return initial_results
        
        # For now, just return original results
        # TODO: Implement actual graph expansion using document relationships
        
        return json.dumps({
            "success": True,
            "expanded": False,
            "results": results_data['results'],
            "message": "Graph expansion not yet implemented"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
