#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('data/rag_system.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print('Tables in database:')
for t in tables:
    print(f'  - {t[0]}')
print(f'\nTotal tables: {len(tables)}')

# Check key table counts
tables_to_check = [
    'agent_operations',
    'query_heatmap', 
    'healing_operations',
    'agent_memory',
    'agent_spawns',
    'llm_token_usage'
]

print('\nRow counts:')
for table in tables_to_check:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f'  {table}: {count}')
    except Exception as e:
        print(f'  {table}: ERROR - {str(e)}')

conn.close()
