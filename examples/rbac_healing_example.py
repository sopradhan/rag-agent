"""
Example: RBAC-Aware Healing and Optimization
Demonstrates namespace rebalancing, chunk analysis, and optimization
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.sqlite_storage import RAGDatabase
from src.storage.vector_store import ChromaVectorStore
from src.subagents.rbac_healing_subagent import RBACHealingSubagent
import json


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def print_json(data, indent=2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def main():
    """Run RBAC-aware healing examples."""
    
    print("=" * 80)
    print("RBAC-AWARE HEALING & OPTIMIZATION - EXAMPLE")
    print("=" * 80)
    
    # Initialize storage
    db_path = "data/rag_system.db"
    chroma_path = "data/chroma_db"
    
    try:
        rag_db = RAGDatabase(db_path)
        vector_store = ChromaVectorStore(chroma_path)
        healing_agent = RBACHealingSubagent(rag_db, vector_store)
        
        print("\n✓ Storage initialized successfully")
        
        # Example 1: Get system health status
        print_section("EXAMPLE 1: System Health Status")
        
        status = healing_agent.get_healing_status()
        print("\nSystem Health Report:")
        print(f"  Status Timestamp: {status['timestamp']}")
        print(f"  System Health: {status['system_health']}")
        print(f"\nHealing Operations Performed:")
        for op_type, count in status['healing_operations'].items():
            print(f"  - {op_type}: {count}")
        
        print(f"\nNamespace Statistics:")
        for ns, stats in status['namespace_statistics'].items():
            print(f"  {ns}:")
            print(f"    - Documents: {stats['doc_count']}")
            print(f"    - Avg Access Level: {stats['avg_access_level']:.1f}")
            print(f"    - Max Access Level: {stats['max_access_level']}")
        
        print(f"\nChunk Statistics:")
        chunk_stats = status['chunk_statistics']
        print(f"  - Total Chunks: {chunk_stats['total_chunks']}")
        print(f"  - Avg Chunk Size: {chunk_stats['avg_chunk_size']:.0f} bytes")
        print(f"  - Min Chunk Size: {chunk_stats['min_chunk_size']} bytes")
        print(f"  - Max Chunk Size: {chunk_stats['max_chunk_size']} bytes")
        print(f"  - Std Deviation: {chunk_stats['std_deviation']:.0f}" if chunk_stats['std_deviation'] else "  - Std Deviation: N/A")
        
        # Example 2: Namespace optimization
        print_section("EXAMPLE 2: Namespace Optimization")
        
        ns_results = healing_agent.run_namespace_optimization()
        print("\nNamespace Optimization Results:")
        print(f"  Operation Status: {ns_results['status']}")
        print(f"  Documents Rebalanced: {ns_results['rebalance_results']['rebalance_count']}")
        
        if ns_results['rebalance_results']['moved_documents']:
            print(f"\n  Moved Documents:")
            for doc in ns_results['rebalance_results']['moved_documents'][:5]:
                print(f"    - {doc['doc_id']}: {doc['from']} → {doc['to']}")
            if len(ns_results['rebalance_results']['moved_documents']) > 5:
                print(f"    ... and {len(ns_results['rebalance_results']['moved_documents']) - 5} more")
        
        print(f"\n  Access Pattern Summary:")
        patterns = ns_results['access_patterns']
        for ns, depts in list(patterns.items())[:3]:
            print(f"    {ns}: {len(depts)} departments accessing")
        
        # Example 3: Chunk analysis and recommendations
        print_section("EXAMPLE 3: Chunk Analysis & Optimization")
        
        chunk_results = healing_agent.run_chunk_optimization()
        print("\nChunk Optimization Results:")
        print(f"  Status: {chunk_results['status']}")
        
        analysis = chunk_results['chunk_analysis']
        print(f"\n  Chunk Distribution:")
        print(f"    - Total: {analysis['total_chunks']}")
        print(f"    - Average Size: {analysis['avg_chunk_size']:.0f} bytes")
        print(f"    - Range: {analysis['min_chunk_size']} - {analysis['max_chunk_size']} bytes")
        
        large = chunk_results['large_chunks']
        small = chunk_results['small_chunks']
        
        print(f"\n  Large Chunks (> 5KB): {len(large)}")
        if large:
            for chunk in large[:3]:
                print(f"    - {chunk['source']}: {chunk['size']} bytes")
            if len(large) > 3:
                print(f"    ... and {len(large) - 3} more")
        
        print(f"\n  Small Chunks (< 200B): {len(small)}")
        if small:
            for chunk in small[:3]:
                print(f"    - {chunk['source']}: {chunk['size']} bytes")
            if len(small) > 3:
                print(f"    ... and {len(small) - 3} more")
        
        rec = chunk_results['recommendations']['recommendation']
        print(f"\n  Recommendations:")
        print(f"    - Should Split: {rec['should_split']}")
        print(f"    - Should Merge: {rec['should_merge']}")
        print(f"    - Target Avg Size: {rec['target_avg_size']} bytes")
        
        # Example 4: Access pattern analysis
        print_section("EXAMPLE 4: Access Pattern Analysis")
        
        patterns = healing_agent.shuffler.analyze_access_patterns()
        print("\nAccess Patterns by Namespace:")
        for ns, dept_access in list(patterns.items())[:3]:
            print(f"\n  {ns}:")
            for dept, count in list(dept_access.items())[:3]:
                print(f"    - {dept}: {count} accesses")
            if len(dept_access) > 3:
                print(f"    ... and {len(dept_access) - 3} more departments")
        
        # Example 5: Namespace affinity calculation
        print_section("EXAMPLE 5: Namespace Affinity Analysis")
        
        print("\nAnalyzing document namespace affinity...")
        cursor = rag_db.conn.cursor()
        cursor.execute("SELECT doc_id, classification, namespace FROM documents LIMIT 10")
        docs = cursor.fetchall()
        
        affinity_mismatches = []
        for doc in docs:
            recommended = healing_agent.shuffler.calculate_namespace_affinity(doc['doc_id'])
            if recommended != doc['namespace']:
                affinity_mismatches.append({
                    'doc_id': doc['doc_id'],
                    'current': doc['namespace'],
                    'recommended': recommended,
                    'classification': doc['classification']
                })
        
        if affinity_mismatches:
            print(f"\nFound {len(affinity_mismatches)} namespace affinity mismatches:")
            for mismatch in affinity_mismatches[:5]:
                print(f"  - {mismatch['doc_id']}")
                print(f"    Classification: {mismatch['classification']}")
                print(f"    Current: {mismatch['current']} → Recommended: {mismatch['recommended']}")
        else:
            print("\n✓ All documents are in optimal namespaces!")
        
        print("\n" + "=" * 80)
        print("Healing example completed successfully!")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
