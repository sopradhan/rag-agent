#!/usr/bin/env python
"""Quick test to see if healing operations are being logged"""
import sys
sys.path.insert(0, 'e:/rag_agent')

from core.services.database_service import DatabaseService

# Create service
db = DatabaseService('data/rag_system.db')

# Try to log a healing operation
try:
    result = db.log_healing_operation(
        strategy='test_strategy',
        target_docs=['doc1', 'doc2'],
        reason='Testing logging',
        actions_taken={'test': 'value'},
        before_metrics={'metric1': 0.5},
        after_metrics={'metric1': 0.7},
        improvement_delta=0.2
    )
    print(f"[OK] Insert successful, ID: {result}")
    
    # Check if it's actually there
    rows = db.query("SELECT * FROM healing_operations WHERE strategy = ?", ('test_strategy',))
    print(f"[OK] Query returned {len(rows)} rows")
    if rows:
        print(f"  Row data: {dict(rows[0])}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
