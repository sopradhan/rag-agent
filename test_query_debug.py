"""Debug query processing"""

import sys
sys.path.insert(0, 'e:\\rag_agent')

from src.subagents.langchain_subagents import AnalyzerSubagent, SearcherSubagent

print("="*70)
print("DEBUG: Query Processing")
print("="*70)

# Test Analyzer
analyzer = AnalyzerSubagent()
query = "how to roll back database"
print(f"\n[*] Testing Analyzer with: '{query}'")
result = analyzer.execute(query)
print(f"Result: {result}")

# Test Searcher
print(f"\n[*] Testing Searcher...")
searcher = SearcherSubagent()
search_result = searcher.execute(query, top_k=5)
print(f"Documents found: {search_result.get('documents_found')}")
if search_result.get('documents'):
    for i, doc in enumerate(search_result['documents'][:2], 1):
        print(f"  {i}. {doc['content'][:60]}...")
else:
    print("  No documents found!")

print("\n" + "="*70)
