"""
Command-Line Interface for REFRAG System
Orchestrates ingestion, retrieval, healing, and system management
"""
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import MasterOrchestrator


def setup_services() -> Dict[str, Any]:
    """Initialize all services"""
    print("🚀 Initializing REFRAG system...")
    configs = load_all_configs('config')
    
    services = {
        'llm': LLMService(configs['llm']),
        'db': DatabaseService('data/rag_system.db'),
        'vectordb': VectorDBService('data/chroma_db'),
        'rbac_config': configs['rbac']
    }
    
    # Setup RBAC
    for cdr_code, mapping in configs['rbac'].get('role_mappings', {}).items():
        services['db'].execute("""
            INSERT OR REPLACE INTO role_mappings 
            (company_id, department_id, role_id, cdr_code, company_name, 
             department_name, role_name, access_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping['company_id'], mapping['department_id'], mapping['role_id'],
            cdr_code, mapping['company_name'], mapping['department_name'],
            mapping['role_name'], mapping['access_level']
        ))
    
    print("✅ Services initialized")
    return services, configs


def cmd_ingest_table(orchestrator, args):
    """Ingest data from a SQLite table"""
    print(f"\n📥 Ingesting table: {args.table}")
    
    # Get table configuration from data_sources.yaml
    db_path = args.db_path or "data/test_sources/sqlite_sources/knowledge_base.db"
    
    # For now, ingest as text files from the table
    # TODO: Implement direct SQLite table ingestion in orchestrator
    result = orchestrator.route_request({
        'action': 'ingest',
        'source': 'sqlite',
        'db_path': db_path,
        'table': args.table
    })
    
    print(f"\n✅ Result: {result}")


def cmd_batch_ingest(orchestrator, args):
    """Batch ingest multiple tables"""
    print(f"\n📥 Batch ingesting {len(args.tables)} tables...")
    
    results = []
    for table in args.tables:
        print(f"\n  Processing: {table}")
        args.table = table
        result = cmd_ingest_table(orchestrator, args)
        results.append({table: result})
    
    print(f"\n✅ Batch complete: {len(results)} tables processed")


def cmd_ingest_directory(orchestrator, args):
    """Ingest all files from a directory"""
    print(f"\n📥 Ingesting directory: {args.directory}")
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"❌ Directory not found: {args.directory}")
        return
    
    files = list(directory.rglob('*.*'))
    print(f"Found {len(files)} files")
    
    results = []
    for file_path in files:
        if file_path.suffix in ['.txt', '.md', '.pdf', '.docx', '.csv', '.json']:
            print(f"  Processing: {file_path.name}")
            result = orchestrator.route_request({
                'action': 'ingest',
                'source': 'file',
                'file_path': str(file_path),
                'metadata': {
                    'subject': args.subject or 'general',
                    'sensitivity': args.sensitivity or 'internal'
                }
            })
            results.append({file_path.name: result})
    
    print(f"\n✅ Ingested {len(results)} files")


def cmd_retrieve(orchestrator, args):
    """Retrieve information with RBAC"""
    print(f"\n🔍 Query: {args.query}")
    print(f"   Role: {args.role}")
    print(f"   Classification: {args.classification or 'any'}")
    
    # Map role to user_id (for demo purposes)
    user_mapping = {
        'engineer': 'alice@acmecorp.com',
        'hr': 'bob@acmecorp.com',
        'executive': 'carol@acmecorp.com',
        'admin': 'admin@acmecorp.com'
    }
    
    user_id = user_mapping.get(args.role.lower(), 'alice@acmecorp.com')
    
    result = orchestrator.route_request({
        'action': 'retrieve',
        'query': args.query,
        'user_id': user_id,
        'classification': args.classification
    })
    
    print(f"\n📄 Answer:\n{result.get('answer', 'No answer found')}")
    
    if result.get('sources'):
        print(f"\n📚 Sources:")
        for i, source in enumerate(result['sources'][:5], 1):
            print(f"  {i}. {source.get('title', 'Unknown')} (score: {source.get('score', 0):.2f})")


def cmd_learning(orchestrator, args):
    """Analyze system learning and performance"""
    print("\n📊 Analyzing system learning...")
    
    result = orchestrator.route_request({
        'action': 'analyze',
        'type': 'learning'
    })
    
    print("\n📈 Learning Metrics:")
    print(f"  Total queries: {result.get('total_queries', 0)}")
    print(f"  Avg accuracy: {result.get('avg_accuracy', 0):.2%}")
    print(f"  Avg response time: {result.get('avg_response_time', 0):.0f}ms")
    print(f"  User satisfaction: {result.get('avg_feedback', 0):.1f}/5.0")


def cmd_heal(orchestrator, args):
    """Run healing process"""
    print("\n🔧 Running healing process...")
    
    result = orchestrator.route_request({
        'action': 'heal',
        'strategy': args.strategy or 'auto'
    })
    
    print(f"\n✅ Healing complete:")
    print(f"  Improvements: {result.get('improvements', 0)}")
    print(f"  Reindexed: {result.get('reindexed_docs', 0)} documents")


def cmd_status(orchestrator, services):
    """Show system status"""
    print("\n📊 REFRAG System Status")
    print("=" * 60)
    
    # Database stats
    db = services['db']
    
    doc_count = db.query("SELECT COUNT(*) as cnt FROM documents")[0]['cnt']
    chunk_count = db.query("SELECT COUNT(*) as cnt FROM embedding_metadata")[0]['cnt']
    operation_count = db.query("SELECT COUNT(*) as cnt FROM agent_operations")[0]['cnt']
    
    print(f"\n📚 Content:")
    print(f"  Documents: {doc_count}")
    print(f"  Chunks: {chunk_count}")
    print(f"  Operations: {operation_count}")
    
    # Vector DB stats
    vectordb_count = services['vectordb'].count()
    print(f"\n🔢 Vector Store:")
    print(f"  Embeddings: {vectordb_count}")
    
    # Recent operations
    recent = db.query("""
        SELECT agent_name, operation_type, COUNT(*) as cnt
        FROM agent_operations
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY agent_name, operation_type
        ORDER BY cnt DESC
        LIMIT 5
    """)
    
    if recent:
        print(f"\n📈 Recent Activity (7 days):")
        for row in recent:
            print(f"  {row['agent_name']}.{row['operation_type']}: {row['cnt']} operations")
    
    # RBAC stats
    role_count = db.query("SELECT COUNT(DISTINCT cdr_code) as cnt FROM role_mappings")[0]['cnt']
    user_count = db.query("SELECT COUNT(DISTINCT user_id) as cnt FROM user_roles")[0]['cnt']
    
    print(f"\n🔐 RBAC:")
    print(f"  Roles: {role_count}")
    print(f"  Users: {user_count}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='REFRAG System - Enterprise RAG with RBAC and Self-Healing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest from SQLite table
  python orchestrator.py --command ingest --table knowledge_base
  
  # Ingest directory
  python orchestrator.py --command ingest-dir --directory data/test_sources/hr
  
  # Batch ingest multiple tables
  python orchestrator.py --command batch-ingest --tables knowledge_base incidents procedures
  
  # Retrieve with RBAC
  python orchestrator.py --command retrieve --query "database performance" --role engineer
  
  # Run healing
  python orchestrator.py --command heal
  
  # System status
  python orchestrator.py --command status
        """
    )
    
    parser.add_argument('--command', '-c', required=True,
                       choices=['ingest', 'batch-ingest', 'ingest-dir', 'retrieve', 
                               'learning', 'heal', 'status'],
                       help='Command to execute')
    
    # Ingest options
    parser.add_argument('--table', help='SQLite table name to ingest')
    parser.add_argument('--tables', nargs='+', help='Multiple tables for batch ingest')
    parser.add_argument('--directory', help='Directory to ingest')
    parser.add_argument('--db-path', help='SQLite database path')
    parser.add_argument('--subject', help='Document subject for RBAC')
    parser.add_argument('--sensitivity', help='Document sensitivity level')
    
    # Retrieve options
    parser.add_argument('--query', '-q', help='Search query')
    parser.add_argument('--role', help='User role (engineer, hr, executive, admin)')
    parser.add_argument('--classification', help='Classification filter')
    
    # Heal options
    parser.add_argument('--strategy', help='Healing strategy')
    
    args = parser.parse_args()
    
    # Initialize services
    services, configs = setup_services()
    orchestrator = MasterOrchestrator(services, configs.get('agent', {}))
    
    # Execute command
    try:
        if args.command == 'ingest':
            if not args.table:
                print("❌ Error: --table required for ingest command")
                return 1
            cmd_ingest_table(orchestrator, args)
            
        elif args.command == 'batch-ingest':
            if not args.tables:
                print("❌ Error: --tables required for batch-ingest command")
                return 1
            cmd_batch_ingest(orchestrator, args)
            
        elif args.command == 'ingest-dir':
            if not args.directory:
                print("❌ Error: --directory required for ingest-dir command")
                return 1
            cmd_ingest_directory(orchestrator, args)
            
        elif args.command == 'retrieve':
            if not args.query or not args.role:
                print("❌ Error: --query and --role required for retrieve command")
                return 1
            cmd_retrieve(orchestrator, args)
            
        elif args.command == 'learning':
            cmd_learning(orchestrator, args)
            
        elif args.command == 'heal':
            cmd_heal(orchestrator, args)
            
        elif args.command == 'status':
            cmd_status(orchestrator, services)
        
        print("\n✅ Command completed successfully")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
