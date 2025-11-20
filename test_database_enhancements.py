#!/usr/bin/env python
"""
Comprehensive test for database logging enhancements
Tests: agent_spawns, llm_token_usage, agent_memory, healing_operations, query_heatmap usage
"""
import sys
import json
sys.path.insert(0, 'e:/rag_agent')

from core.services.database_service import DatabaseService
from core.config.loader import load_all_configs
from agents.master_orchestrator import MasterOrchestrator

def test_database_logging():
    """Test all database logging mechanisms"""
    
    # Initialize services
    db = DatabaseService('data/rag_system.db')
    config = load_all_configs()
    
    print("=" * 60)
    print("DATABASE LOGGING TEST")
    print("=" * 60)
    
    # Test 1: Agent Spawns
    print("\n[TEST 1] Agent Spawns Logging")
    try:
        spawn_id = db.log_agent_spawn('MasterOrchestrator', 'RetrievalAgent', 'Test query processing')
        spawns = db.query("SELECT * FROM agent_spawns WHERE spawn_id = ?", (spawn_id,))
        if spawns:
            print(f"[OK] Agent spawn logged: {dict(spawns[0])}")
        else:
            print("✗ Spawn ID not found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 2: LLM Token Usage
    print("\n[TEST 2] LLM Token Usage Logging")
    try:
        token_id = db.log_token_usage('RetrievalAgent', 1, 'ollama', 'qwen2.5:0.5b', 100, 50, 0.0)
        tokens = db.query("SELECT * FROM llm_token_usage WHERE agent_name = 'RetrievalAgent' LIMIT 1")
        if tokens:
            print(f"[OK] Token usage logged: agent={tokens[0]['agent_name']}, prompt={tokens[0]['prompt_tokens']}, completion={tokens[0]['completion_tokens']}")
        else:
            print("✗ Token record not found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Agent Memory
    print("\n[TEST 3] Agent Memory Storage")
    try:
        mem_id = db.store_agent_memory('TestAgent', 'query_123', json.dumps({"test": "data"}), 'query_result')
        memory = db.query("SELECT * FROM agent_memory WHERE agent_name = 'TestAgent' LIMIT 1")
        if memory:
            print(f"[OK] Memory stored: agent={memory[0]['agent_name']}, key={memory[0]['memory_key']}")
        else:
            print("✗ Memory record not found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Query Heatmap
    print("\n[TEST 4] Query Heatmap Analysis")
    try:
        heatmap = db.get_heatmap_analysis()
        print(f"[OK] Heatmap analysis retrieved:")
        print(f"  - Cold spots: {len(heatmap['cold_spots'])} queries with low frequency")
        print(f"  - Poor quality: {len(heatmap['poor_quality'])} queries with low feedback")
        print(f"  - Slow queries: {len(heatmap['slow_queries'])} queries with high latency")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 5: Comprehensive counts
    print("\n[TEST 5] Final Database State")
    tables_to_check = {
        'agent_operations': 'Agent operations',
        'query_heatmap': 'Query heatmap entries',
        'healing_operations': 'Healing operations',
        'agent_memory': 'Agent memory entries',
        'agent_spawns': 'Agent spawns',
        'llm_token_usage': 'LLM token usage records',
        'query_history': 'Query history'
    }
    
    for table, label in tables_to_check.items():
        try:
            result = db.query(f"SELECT COUNT(*) as cnt FROM {table}")
            count = result[0]['cnt'] if result else 0
            symbol = "[OK]" if count > 0 else "○"
            print(f"{symbol} {label}: {count} rows")
        except Exception as e:
            print(f"✗ {label}: ERROR - {str(e)}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_database_logging()
