"""
Example: RBAC-Aware Retrieval with Tags
Demonstrates searching documents with RBAC filtering and tag association
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.sqlite_storage import RAGDatabase
from src.storage.vector_store import ChromaVectorStore
from src.subagents.rbac_retrieval_subagent import RBACSearchSubagent


def main():
    """Run RBAC-aware retrieval examples."""
    
    print("=" * 80)
    print("RBAC-AWARE RETRIEVAL WITH TAGS - EXAMPLE")
    print("=" * 80)
    
    # Initialize storage
    db_path = "data/rag_system.db"
    chroma_path = "data/chroma_db"
    
    try:
        rag_db = RAGDatabase(db_path)
        vector_store = ChromaVectorStore(chroma_path)
        search_agent = RBACSearchSubagent(rag_db, vector_store)
        
        print("\n✓ Storage initialized successfully")
        
        # Example 1: Search for user 1 (Engineering)
        print("\n" + "-" * 80)
        print("EXAMPLE 1: Search for Engineering Department User")
        print("-" * 80)
        
        user_id = 1
        query = "database architecture"
        
        print(f"\nUser ID: {user_id}")
        print(f"Search Query: '{query}'")
        
        results = search_agent.search_with_rbac_and_tags(
            query=query,
            user_id=user_id,
            top_k=5
        )
        
        print(f"\nFound {len(results)} accessible documents:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Document: {result['source']}")
            print(f"   Classification: {result['classification']}")
            print(f"   Similarity Score: {result['similarity_score']:.3f}")
            print(f"   Tags: {', '.join(result['tags']) if result['tags'] else 'None'}")
            print(f"   Your Access Level: {result['user_access_level']}")
            print(f"   Required Access Level: {result['min_access_level']}")
            print(f"   Content Preview: {result['content'][:100]}...")
        
        # Example 2: Search with tag filtering
        print("\n" + "-" * 80)
        print("EXAMPLE 2: Search with Tag Filtering")
        print("-" * 80)
        
        query = "company policies"
        tags_filter = ["policy", "important"]
        
        print(f"\nSearch Query: '{query}'")
        print(f"Tag Filter: {tags_filter}")
        
        results = search_agent.search_with_rbac_and_tags(
            query=query,
            user_id=user_id,
            top_k=5,
            tags_filter=tags_filter
        )
        
        print(f"\nFound {len(results)} documents with matching tags:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['source']}")
            print(f"   Tags: {', '.join(result['tags'])}")
            print(f"   Relevance: {result['similarity_score']:.3f}")
        
        # Example 3: RBAC filtering details
        print("\n" + "-" * 80)
        print("EXAMPLE 3: RBAC Context for User")
        print("-" * 80)
        
        rbac_filter = search_agent.rbac_filter
        user_rbac = rbac_filter.get_user_rbac_context(user_id)
        
        if user_rbac:
            print(f"\nUser RBAC Context:")
            print(f"  Company: {user_rbac['company_name']} (ID: {user_rbac['company_id']})")
            print(f"  Department: {user_rbac['department_name']} (ID: {user_rbac['department_id']})")
            print(f"  Role: {user_rbac['role_name']}")
            print(f"  Access Level: {user_rbac['access_level']}")
        
        # Example 4: Get tag suggestions
        print("\n" + "-" * 80)
        print("EXAMPLE 4: Tag Suggestions")
        print("-" * 80)
        
        search_query = "engineering"
        tag_suggestions = search_agent.tag_retriever.get_tag_suggestions(
            search_query,
            limit=5
        )
        
        print(f"\nTag suggestions for query '{search_query}':")
        for suggestion in tag_suggestions:
            print(f"  - {suggestion['tag']} (used in {suggestion['frequency']} documents)")
        
        print("\n" + "=" * 80)
        print("Example completed successfully!")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
