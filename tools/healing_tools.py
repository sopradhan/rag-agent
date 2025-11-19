"""
Healing Tools
Tools for REFRAG self-healing: heatmap analysis, quality detection, reindexing
"""
import json
import hashlib
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


@tool
def analyze_heatmap_tool(db_service) -> str:
    """
    Analyze query heatmap to find optimization opportunities.
    
    Args:
        db_service: Database service instance
        
    Returns:
        JSON string with heatmap analysis
    """
    try:
        analysis = db_service.get_heatmap_analysis()
        
        # Calculate statistics
        total_queries = db_service.query(
            "SELECT COUNT(*) as count FROM query_heatmap"
        )[0]['count']
        
        avg_feedback = db_service.query("""
            SELECT AVG(avg_user_feedback) as avg_fb 
            FROM query_heatmap 
            WHERE avg_user_feedback IS NOT NULL
        """)
        avg_fb = avg_feedback[0]['avg_fb'] if avg_feedback else 0
        
        # Generate recommendations
        recommendations = []
        
        if analysis['cold_spots']:
            recommendations.append({
                "type": "cold_spots",
                "count": len(analysis['cold_spots']),
                "action": "Generate synthetic questions for low-frequency queries"
            })
        
        if analysis['poor_quality']:
            recommendations.append({
                "type": "poor_quality",
                "count": len(analysis['poor_quality']),
                "action": "Reindex documents with poor retrieval accuracy"
            })
        
        if analysis['slow_queries']:
            recommendations.append({
                "type": "slow_queries",
                "count": len(analysis['slow_queries']),
                "action": "Optimize chunking strategy for slow queries"
            })
        
        return json.dumps({
            "success": True,
            "total_queries": total_queries,
            "avg_user_feedback": round(avg_fb, 2) if avg_fb else None,
            "cold_spots": analysis['cold_spots'][:5],
            "poor_quality": analysis['poor_quality'][:5],
            "slow_queries": analysis['slow_queries'][:5],
            "recommendations": recommendations
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def detect_low_quality_tool(threshold: float, db_service) -> str:
    """
    Detect low-quality embeddings that need reindexing.
    
    Args:
        threshold: Quality score threshold (0.0-1.0)
        db_service: Database service instance
        
    Returns:
        JSON string with low-quality documents
    """
    try:
        low_quality = db_service.query("""
            SELECT DISTINCT document_id, AVG(quality_score) as avg_quality, COUNT(*) as num_chunks
            FROM embedding_metadata
            GROUP BY document_id
            HAVING avg_quality < ?
            ORDER BY avg_quality ASC
            LIMIT 20
        """, (threshold,))
        
        return json.dumps({
            "success": True,
            "threshold": threshold,
            "num_documents": len(low_quality),
            "documents": [
                {
                    "document_id": doc['document_id'],
                    "avg_quality": round(doc['avg_quality'], 3),
                    "num_chunks": doc['num_chunks']
                }
                for doc in low_quality
            ]
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def generate_synthetic_questions_tool(doc_id: str, count: int, llm_service, db_service) -> str:
    """
    Generate synthetic questions for a document to improve retrieval.
    
    Args:
        doc_id: Document ID
        count: Number of questions to generate
        llm_service: LLM service instance
        db_service: Database service instance
        
    Returns:
        JSON string with generated questions
    """
    try:
        # Get document content
        doc = db_service.query(
            "SELECT content FROM documents WHERE id = ?",
            (doc_id,)
        )
        
        if not doc:
            return json.dumps({
                "success": False,
                "error": f"Document not found: {doc_id}"
            })
        
        content = doc[0]['content'][:3000]  # Limit to first 3000 chars
        
        # Generate questions
        prompt = f"""Generate {count} diverse, realistic questions that this document could answer.

Make questions vary in:
- Complexity (simple facts to multi-hop reasoning)
- Specificity (broad overview to specific details)
- Phrasing (different ways to ask the same thing)

Document excerpt:
{content}

Respond ONLY with valid JSON in this format:
{{
    "questions": ["question1", "question2", ...]
}}
"""
        
        result = llm_service.generate_json(prompt)
        questions = result.get('questions', [])
        
        # Store synthetic questions
        for question in questions:
            db_service.execute("""
                INSERT INTO synthetic_queries (doc_id, question)
                VALUES (?, ?)
            """, (doc_id, question))
        
        return json.dumps({
            "success": True,
            "doc_id": doc_id,
            "num_questions": len(questions),
            "questions": questions
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def reindex_documents_tool(doc_ids: str, new_strategy: str, 
                          vectordb_service, db_service, llm_service) -> str:
    """
    Re-chunk and re-embed documents with new strategy.
    
    Args:
        doc_ids: JSON list of document IDs
        new_strategy: New chunking strategy ('recursive', 'semantic', etc.)
        vectordb_service: Vector DB service instance
        db_service: Database service instance
        llm_service: LLM service instance
        
    Returns:
        JSON string with reindexing results
    """
    try:
        doc_id_list = json.loads(doc_ids)
        
        results = {
            "reindexed_count": 0,
            "total_new_chunks": 0,
            "documents": []
        }
        
        for doc_id in doc_id_list:
            # Get document
            doc = db_service.query(
                "SELECT content FROM documents WHERE id = ?",
                (doc_id,)
            )
            
            if not doc:
                continue
            
            content = doc[0]['content']
            
            # Delete old embeddings
            vectordb_service.delete_by_document(doc_id)
            
            # Re-chunk (using ingestion tools)
            from tools.ingestion_tools import chunk_document_tool, generate_embeddings_tool
            
            chunks_result = chunk_document_tool(content, new_strategy, 500, 50)
            embeddings_result = generate_embeddings_tool(chunks_result, llm_service)
            
            chunks_data = json.loads(embeddings_result)
            
            if chunks_data.get('success'):
                num_chunks = chunks_data['num_embeddings']
                
                # Update reindex count
                db_service.execute("""
                    UPDATE embedding_metadata
                    SET reindex_count = reindex_count + 1,
                        chunk_strategy = ?,
                        last_modified = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (new_strategy, doc_id))
                
                results['reindexed_count'] += 1
                results['total_new_chunks'] += num_chunks
                results['documents'].append({
                    "doc_id": doc_id,
                    "num_chunks": num_chunks,
                    "strategy": new_strategy
                })
        
        return json.dumps({
            "success": True,
            "new_strategy": new_strategy,
            **results
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def optimize_chunk_strategy_tool(doc_id: str, vectordb_service, db_service, llm_service) -> str:
    """
    Test different chunking strategies and select the best one.
    
    Args:
        doc_id: Document ID
        vectordb_service: Vector DB service instance
        db_service: Database service instance
        llm_service: LLM service instance
        
    Returns:
        JSON string with optimization results
    """
    try:
        # Get document
        doc = db_service.query(
            "SELECT content FROM documents WHERE id = ?",
            (doc_id,)
        )
        
        if not doc:
            return json.dumps({
                "success": False,
                "error": f"Document not found: {doc_id}"
            })
        
        content = doc[0]['content']
        
        # Test different strategies
        strategies = ['recursive', 'character', 'token']
        results = []
        
        from tools.ingestion_tools import chunk_document_tool
        
        for strategy in strategies:
            chunks_result = chunk_document_tool(content, strategy, 500, 50)
            chunks_data = json.loads(chunks_result)
            
            if chunks_data.get('success'):
                results.append({
                    "strategy": strategy,
                    "num_chunks": chunks_data['num_chunks'],
                    "avg_chunk_size": sum(c['size'] for c in chunks_data['chunks']) / chunks_data['num_chunks']
                })
        
        # Select best strategy (fewest chunks with reasonable size)
        best = min(results, key=lambda x: abs(x['avg_chunk_size'] - 500))
        
        return json.dumps({
            "success": True,
            "doc_id": doc_id,
            "tested_strategies": results,
            "recommended_strategy": best['strategy'],
            "reasoning": f"Best average chunk size: {best['avg_chunk_size']:.0f} chars"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
