"""
Test Agent Thought Process Visualization
Demonstrates the thought visualization capabilities including animations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.thought_visualizer import ThoughtVisualizer, ThoughtProcess


def test_simple_visualization():
    """Test simple ASCII visualization"""
    print("\n" + "="*70)
    print("TEST: Simple ASCII Visualization")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Process Query")
    
    # Add steps
    step1 = thought.add_step(
        "Vector Search",
        "Query vector database for similar documents",
        {"query": "What are benefits?", "top_k": 10}
    )
    thought.start_step(step1)
    thought.complete_step(step1, 250)
    
    step2 = thought.add_step(
        "RBAC Check",
        "Verify user permissions",
        {"user_id": "user_123", "chunks_checked": 10}
    )
    thought.start_step(step2)
    thought.complete_step(step2, 50)
    
    step3 = thought.add_step(
        "Synthesis",
        "Generate final answer",
        {"answer_length": 234, "sources": 3}
    )
    thought.start_step(step3)
    thought.complete_step(step3, 180)
    
    thought.set_metadata("total_time_ms", 480)
    thought.set_metadata("accuracy", 0.92)
    
    print(thought.visualize_simple())


def test_animated_simple():
    """Test animated simple visualization"""
    print("\n" + "="*70)
    print("TEST: Animated Simple Visualization (with 0.3s delay)")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Animated Query")
    
    step1 = thought.add_step("Load Parameters", "Initialize query processing", {"params": "loaded"})
    thought.start_step(step1)
    thought.complete_step(step1, 100)
    
    step2 = thought.add_step("Vector Search", "Find relevant documents", {"results": 10})
    thought.start_step(step2)
    thought.complete_step(step2, 250)
    
    step3 = thought.add_step("Verify Access", "Check RBAC permissions", {"allowed": 10})
    thought.start_step(step3)
    thought.complete_step(step3, 50)
    
    thought.set_metadata("success", True)
    thought.animate_simple(delay=0.3)


def test_animated_progress():
    """Test animated progress bar"""
    print("\n" + "="*70)
    print("TEST: Animated Progress Bar")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("IngestionAgent", "Ingest Document")
    
    steps = [
        ("Read File", "Load document from disk"),
        ("Chunking", "Split into chunks"),
        ("Embedding", "Generate embeddings"),
        ("Storage", "Store in database"),
    ]
    
    for title, desc in steps:
        step = thought.add_step(title, desc)
        thought.start_step(step)
        thought.complete_step(step, 200)
    
    thought.animate_progress_bar(delay=0.5)


def test_animated_cascading():
    """Test cascading animation"""
    print("\n" + "="*70)
    print("TEST: Cascading Animation")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("HealingAgent", "Optimize System")
    
    steps = [
        ("Analyze", "Analyze system health"),
        ("Detect", "Find problems"),
        ("Fix", "Apply optimizations"),
        ("Verify", "Check improvements"),
    ]
    
    for title, desc in steps:
        step = thought.add_step(title, desc)
        thought.start_step(step)
        thought.complete_step(step, 300)
    
    thought.animate_cascading(delay=0.3)


def test_animated_spinner():
    """Test spinner animation"""
    print("\n" + "="*70)
    print("TEST: Spinner Animation")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Complex Query")
    
    steps = ["Initialize", "Search", "Filter", "Rank", "Synthesize"]
    for title in steps:
        step = thought.add_step(title, f"Step: {title}")
        thought.start_step(step)
        thought.complete_step(step, 200)
    
    thought.animate_spinner(delay=0.4)


def test_detailed_visualization():
    """Test detailed visualization"""
    print("\n" + "="*70)
    print("TEST: Detailed Visualization")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("IngestionAgent", "Ingest Document")
    
    steps = [
        ("Read File", "Load document from disk", {"file_size_kb": 256}),
        ("Chunking", "Split into 500-token chunks", {"chunks": 12}),
        ("Embedding", "Generate embeddings", {"model": "all-MiniLM"}),
        ("Storage", "Store in vector DB", {"stored_chunks": 12}),
    ]
    
    for i, (title, desc, details) in enumerate(steps):
        step = thought.add_step(title, desc, details)
        thought.start_step(step)
        thought.complete_step(step, 100 + i * 50)
    
    thought.set_metadata("document_id", "doc_12345")
    thought.set_metadata("status", "completed")
    
    print(thought.visualize_detailed())


def test_animated_detailed():
    """Test animated detailed visualization"""
    print("\n" + "="*70)
    print("TEST: Animated Detailed Visualization (with 0.4s delay)")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Detailed Analysis")
    
    step1 = thought.add_step("Analysis", "Deep analysis", {"depth": "high"})
    thought.start_step(step1)
    thought.complete_step(step1, 300)
    
    step2 = thought.add_step("Verification", "Verify results", {"verified": True})
    thought.start_step(step2)
    thought.complete_step(step2, 100)
    
    step3 = thought.add_step("Report", "Generate report", {"format": "detailed"})
    thought.start_step(step3)
    thought.complete_step(step3, 150)
    
    thought.animate_detailed(delay=0.4)


def test_flowchart_visualization():
    """Test flowchart visualization"""
    print("\n" + "="*70)
    print("TEST: Flowchart Visualization")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("HealingAgent", "Healing Cycle")
    
    steps = [
        ("Initialize", "Load system parameters"),
        ("Analyze", "Analyze query heatmap"),
        ("Detect", "Detect low-quality regions"),
        ("Optimize", "Apply healing strategies"),
        ("Verify", "Verify improvements"),
    ]
    
    for title, desc in steps:
        step = thought.add_step(title, desc)
        thought.start_step(step)
        thought.complete_step(step, 500)
    
    print(thought.visualize_flowchart())


def test_tree_visualization():
    """Test tree-style visualization"""
    print("\n" + "="*70)
    print("TEST: Tree-Style Visualization")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Complex Query")
    
    step1 = thought.add_step(
        "Search",
        "Vector search",
        {
            "results": ["doc1", "doc2", "doc3"],
            "scores": [0.95, 0.87, 0.76],
            "duration": "250ms"
        }
    )
    thought.start_step(step1)
    thought.complete_step(step1, 250)
    
    step2 = thought.add_step(
        "Filter",
        "Apply RBAC filters",
        {
            "allowed": 2,
            "denied": 1,
            "policy": "hr_only"
        }
    )
    thought.start_step(step2)
    thought.complete_step(step2, 50)
    
    print(thought.visualize_tree())


def test_error_handling():
    """Test error handling in thought process"""
    print("\n" + "="*70)
    print("TEST: Error Handling")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("RetrievalAgent", "Query with Error")
    
    step1 = thought.add_step(
        "Initialize",
        "Prepare query processing"
    )
    thought.start_step(step1)
    thought.complete_step(step1, 100)
    
    step2 = thought.add_step(
        "Search",
        "Query vector database"
    )
    thought.start_step(step2)
    thought.error_step(step2, "Connection timeout after 5000ms")
    
    thought.set_metadata("error_type", "network")
    thought.set_metadata("retry_count", 2)
    
    print(thought.visualize_simple())


def test_export_json():
    """Test JSON export"""
    print("\n" + "="*70)
    print("TEST: JSON Export")
    print("="*70)
    
    thought = ThoughtVisualizer.create_process("TestAgent", "Test Operation")
    
    step = thought.add_step("Test Step", "Testing export")
    thought.start_step(step)
    thought.complete_step(step, 100)
    
    thought.set_metadata("version", "1.0")
    
    import json
    exported = json.loads(thought.to_json())
    
    print("\nExported JSON Structure:")
    print(f"  Agent: {exported['agent']}")
    print(f"  Operation: {exported['operation']}")
    print(f"  Steps: {len(exported['steps'])}")
    print(f"  Metadata: {exported['metadata']}")
    
    print("\nFull JSON:")
    print(thought.to_json())


def main():
    """Run all visualization tests"""
    print("\n" + "="*70)
    print("AGENT THOUGHT PROCESS VISUALIZATION TESTS (ANIMATED)")
    print("="*70)
    
    try:
        test_simple_visualization()
        test_animated_simple()
        test_detailed_visualization()
        test_animated_detailed()
        test_flowchart_visualization()
        test_tree_visualization()
        test_animated_progress()
        test_animated_cascading()
        test_animated_spinner()
        test_error_handling()
        test_export_json()
        
        print("\n" + "="*70)
        print("✓ ALL VISUALIZATION TESTS COMPLETED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
