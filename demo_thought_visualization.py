"""
Agent Thought Visualization - Quick Demo
Shows how agent thought processes appear with animations in real operations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.thought_visualizer import ThoughtVisualizer


def demo_retrieval_thought():
    """Demo: What RetrievalAgent's thought looks like"""
    print("\n" + "="*70)
    print("DEMO: RetrievalAgent Processing a Query")
    print("="*70)
    print("\nQuery: 'What are the company benefits?'")
    print("User: john.doe@company.com\n")
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Process Query: What are the company benefits?")
    
    # Step 1: Initialize
    step1 = thought.add_step(
        "Initialize",
        "Load parameters and prepare for query processing",
        {"user_id": "john.doe", "top_k": 10, "threshold": 0.7}
    )
    thought.start_step(step1)
    thought.complete_step(step1, 45)
    
    # Step 2: Vector Search
    step2 = thought.add_step(
        "Vector Search",
        "Search vector database for top 10 relevant chunks",
        {"query_tokens": 5, "results_found": 10, "avg_score": 0.82}
    )
    thought.start_step(step2)
    thought.complete_step(step2, 234)
    
    # Step 3: RBAC Check
    step3 = thought.add_step(
        "RBAC Enforcement",
        "Verify john.doe can access all retrieved chunks",
        {"chunks_checked": 10, "allowed": 10, "denied": 0}
    )
    thought.start_step(step3)
    thought.complete_step(step3, 52)
    
    # Step 4: Synthesis
    step4 = thought.add_step(
        "Synthesis",
        "Generate final answer from allowed results",
        {"sources_used": 10, "response_length": 287, "citations": 3}
    )
    thought.start_step(step4)
    thought.complete_step(step4, 156)
    
    thought.set_metadata("total_time", "487ms")
    thought.set_metadata("accuracy", "0.92")
    thought.set_metadata("user_satisfied", "expected_yes")
    
    thought.animate_simple(delay=0.4)


def demo_ingestion_thought():
    """Demo: What IngestionAgent's thought looks like"""
    print("\n" + "="*70)
    print("DEMO: IngestionAgent Ingesting a Document")
    print("="*70)
    print("\nDocument: company_handbook.txt (47 KB)")
    print("Category: HR Documentation\n")
    
    thought = ThoughtVisualizer.create_process("IngestionAgent", "Ingest: company_handbook.txt")
    
    # Step 1: Read
    step1 = thought.add_step(
        "Read Document",
        "Read document from disk",
        {"file_size": "47 KB", "encoding": "utf-8", "type": "text"}
    )
    thought.start_step(step1)
    thought.complete_step(step1, 78)
    
    # Step 2: Chunking
    step2 = thought.add_step(
        "Chunking",
        "Split document into 500-token chunks with 50-token overlap",
        {"total_tokens": 8234, "chunks_created": 16, "avg_chunk_size": 514}
    )
    thought.start_step(step2)
    thought.complete_step(step2, 145)
    
    # Step 3: Embedding
    step3 = thought.add_step(
        "Embedding",
        "Generate embeddings using all-MiniLM-L6-v2 model",
        {"model": "all-MiniLM-L6-v2", "dims": 384, "chunks_embedded": 16}
    )
    thought.start_step(step3)
    thought.complete_step(step3, 312)
    
    # Step 4: Storage
    step4 = thought.add_step(
        "Storage",
        "Store embeddings in ChromaDB and metadata in SQLite",
        {"embeddings_stored": 16, "metadata_records": 16}
    )
    thought.start_step(step4)
    thought.complete_step(step4, 89)
    
    thought.set_metadata("doc_id", "doc_20251120_001")
    thought.set_metadata("total_time", "624ms")
    thought.set_metadata("status", "completed")
    
    thought.animate_progress_bar(delay=0.3)


def demo_healing_thought():
    """Demo: What HealingAgent's thought looks like"""
    print("\n" + "="*70)
    print("DEMO: HealingAgent Running Optimization Cycle")
    print("="*70)
    print("\nStrategies: reindex_low_quality, add_synthetic_questions, adjust_chunk_size")
    print("Profile: high_precision\n")
    
    thought = ThoughtVisualizer.create_process("HealingAgent", "Healing Cycle")
    
    # Step 1: Analyze
    step1 = thought.add_step(
        "System Analysis",
        "Analyze query heatmap and system metrics",
        {"low_quality_regions": 3, "avg_accuracy": 0.72, "problem_docs": 8}
    )
    thought.start_step(step1)
    thought.complete_step(step1, 234)
    
    # Step 2: Optimize
    step2 = thought.add_step(
        "Apply Optimizations",
        "Execute healing strategies on problematic documents",
        {"strategies": 3, "docs_improved": 8, "avg_improvement": 0.18}
    )
    thought.start_step(step2)
    thought.complete_step(step2, 567)
    
    # Step 3: Synthetic Q&A
    step3 = thought.add_step(
        "Generate Questions",
        "Create synthetic Q&A pairs for better coverage",
        {"qa_pairs_created": 24, "docs_enhanced": 8}
    )
    thought.start_step(step3)
    thought.complete_step(step3, 456)
    
    # Step 4: Verification
    step4 = thought.add_step(
        "Verification",
        "Verify improvements with test queries",
        {"test_queries": 50, "improvement_confirmed": "45/50", "new_avg_accuracy": 0.88}
    )
    thought.start_step(step4)
    thought.complete_step(step4, 178)
    
    thought.set_metadata("total_time", "1435ms")
    thought.set_metadata("overall_improvement", "0.16 (+16%)")
    thought.set_metadata("recommendation", "Run again in 2 hours")
    
    thought.animate_cascading(delay=0.35)


def demo_error_scenario():
    """Demo: What error handling looks like"""
    print("\n" + "="*70)
    print("DEMO: Error Scenario - Connection Timeout")
    print("="*70)
    print("\nQuery: Complex multi-hop question")
    print("Status: Processing error\n")
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Complex Query (Failed)")
    
    # Step 1: Initialize - Success
    step1 = thought.add_step(
        "Initialize",
        "Load parameters",
        {"params_loaded": True}
    )
    thought.start_step(step1)
    thought.complete_step(step1, 35)
    
    # Step 2: Vector Search - Error
    step2 = thought.add_step(
        "Vector Search",
        "Query ChromaDB vector database",
        {"attempt": 1}
    )
    thought.start_step(step2)
    thought.error_step(step2, "Connection timeout to ChromaDB after 5000ms")
    
    thought.set_metadata("error_type", "network_timeout")
    thought.set_metadata("retry_count", 0)
    thought.set_metadata("recommendation", "Check ChromaDB service health")
    
    thought.animate_simple(delay=0.3)


def main():
    """Run all demos"""
    print("\n" + "█"*70)
    print("█ AGENT THOUGHT VISUALIZATION DEMOS")
    print("█ See how agents think and visualize their reasoning")
    print("█"*70)
    
    try:
        demo_retrieval_thought()
        demo_ingestion_thought()
        demo_healing_thought()
        demo_error_scenario()
        
        print("\n" + "="*70)
        print("[SUCCESS] ALL DEMOS COMPLETED")
        print("="*70)
        print("\nThought visualizations appear in real-time during agent operations.")
        print("Each demo shows how agents are thinking step-by-step!\n")
        
    except Exception as e:
        print(f"\n[ERROR] DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
