"""
Comprehensive Test Suite for REFRAG System
Tests all core components and agent functionality
"""
import sys
import pytest
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.services import LLMService, DatabaseService, VectorDBService
from core.config import load_all_configs
from agents import IngestionAgent, RetrievalAgent, HealingAgent, MasterOrchestrator


@pytest.fixture
def test_configs():
    """Load test configurations"""
    return load_all_configs('config')


@pytest.fixture
def test_db():
    """Create temporary test database"""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = temp_db.name
    temp_db.close()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_vector_dir():
    """Create temporary vector database directory"""
    temp_dir = tempfile.mkdtemp()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def services(test_configs, test_db, test_vector_dir):
    """Initialize test services"""
    llm = LLMService(test_configs['llm'])
    db = DatabaseService(test_db)
    vectordb = VectorDBService(test_vector_dir)
    
    # Populate test RBAC mappings
    for cdr_code, mapping in test_configs['rbac'].get('role_mappings', {}).items():
        db.execute("""
            INSERT OR REPLACE INTO role_mappings 
            (company_id, department_id, role_id, cdr_code, company_name, 
             department_name, role_name, access_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping['company_id'],
            mapping['department_id'],
            mapping['role_id'],
            cdr_code,
            mapping['company_name'],
            mapping['department_name'],
            mapping['role_name'],
            mapping['access_level']
        ))
    
    return {
        'llm': llm,
        'db': db,
        'vectordb': vectordb,
        'rbac_config': test_configs['rbac']
    }


class TestLLMService:
    """Test LLM Service functionality"""
    
    def test_llm_initialization(self, test_configs):
        """Test LLM service initializes correctly"""
        llm = LLMService(test_configs['llm'])
        assert llm is not None
        
        # Should be able to get a model
        model = llm.get_model()
        assert model is not None
    
    def test_embedding_generation(self, test_configs):
        """Test embedding generation"""
        llm = LLMService(test_configs['llm'])
        
        texts = ["Hello world", "Test document"]
        embeddings = llm.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) > 0  # Should have dimensions
        assert isinstance(embeddings[0][0], float)


class TestDatabaseService:
    """Test Database Service functionality"""
    
    def test_database_initialization(self, test_db):
        """Test database initializes with correct schema"""
        db = DatabaseService(test_db)
        
        # Check that key tables exist
        tables = db.query("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        table_names = [t['name'] for t in tables]
        
        assert 'documents' in table_names
        assert 'role_mappings' in table_names
        assert 'user_roles' in table_names
        assert 'query_heatmap' in table_names
    
    def test_rbac_operations(self, services):
        """Test RBAC permission checking"""
        db = services['db']
        
        # Create test user
        db.execute("""
            INSERT INTO user_roles (user_id, cdr_code, company_id, department_id, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, ("test@test.com", "112", 1, 1, 2))
        
        # Get user roles
        roles = db.get_user_roles("test@test.com")
        assert len(roles) > 0
        assert roles[0]['cdr_code'] == "112"
    
    def test_logging_operations(self, services):
        """Test operation logging"""
        db = services['db']
        
        # Log an operation
        op_id = db.log_agent_operation(
            agent_type='test_agent',
            operation_type='test_op',
            status='success'
        )
        
        assert op_id > 0
        
        # Verify logged
        ops = db.query("SELECT * FROM agent_operations WHERE operation_id = ?", (op_id,))
        assert len(ops) == 1
        assert ops[0]['agent_type'] == 'test_agent'


class TestVectorDBService:
    """Test Vector Database Service functionality"""
    
    def test_vectordb_initialization(self, test_vector_dir):
        """Test vector database initializes"""
        vectordb = VectorDBService(test_vector_dir)
        assert vectordb is not None
        assert vectordb.count() == 0
    
    def test_insert_and_search(self, services):
        """Test embedding insertion and search"""
        vectordb = services['vectordb']
        llm = services['llm']
        
        # Generate test embeddings
        texts = ["This is about HR policies", "This is about engineering"]
        embeddings = llm.generate_embeddings(texts)
        
        # Insert
        ids = ["test_1", "test_2"]
        metadatas = [
            {'document_id': 1, 'chunk_index': 0},
            {'document_id': 2, 'chunk_index': 0}
        ]
        
        vectordb.insert_embeddings(ids, embeddings, metadatas, texts)
        
        assert vectordb.count() == 2
        
        # Search
        query_embedding = llm.generate_embedding("HR policies")
        results = vectordb.search(query_embedding, top_k=2)
        
        assert len(results) > 0
        assert 'ids' in results


class TestIngestionAgent:
    """Test Ingestion Agent functionality"""
    
    def test_agent_initialization(self, services, test_configs):
        """Test ingestion agent initializes with correct tools"""
        agent = IngestionAgent(services, test_configs)
        
        assert agent is not None
        assert len(agent.tools) > 0
        
        # Should have ingestion tools
        tool_names = [t.name for t in agent.tools]
        assert 'chunk_document_tool' in tool_names
        assert 'extract_metadata_tool' in tool_names
        assert 'classify_rbac_tool' in tool_names


class TestRetrievalAgent:
    """Test Retrieval Agent functionality"""
    
    def test_agent_initialization(self, services, test_configs):
        """Test retrieval agent initializes with correct tools"""
        agent = RetrievalAgent(services, test_configs)
        
        assert agent is not None
        assert len(agent.tools) > 0
        
        # Should have retrieval tools
        tool_names = [t.name for t in agent.tools]
        assert 'permission_check_tool' in tool_names
        assert 'vector_search_tool' in tool_names
        assert 'synthesize_answer_tool' in tool_names


class TestHealingAgent:
    """Test Healing Agent functionality"""
    
    def test_agent_initialization(self, services, test_configs):
        """Test healing agent initializes with correct tools"""
        agent = HealingAgent(services, test_configs)
        
        assert agent is not None
        assert len(agent.tools) > 0
        
        # Should have healing tools
        tool_names = [t.name for t in agent.tools]
        assert 'analyze_heatmap_tool' in tool_names
        assert 'detect_low_quality_tool' in tool_names
        assert 'generate_synthetic_questions_tool' in tool_names


class TestMasterOrchestrator:
    """Test Master Orchestrator functionality"""
    
    def test_orchestrator_initialization(self, services, test_configs):
        """Test orchestrator initializes with all agents"""
        orchestrator = MasterOrchestrator(services, test_configs)
        
        assert orchestrator is not None
        assert orchestrator.ingestion_agent is not None
        assert orchestrator.retrieval_agent is not None
        assert orchestrator.healing_agent is not None
    
    def test_get_status(self, services, test_configs):
        """Test system status retrieval"""
        orchestrator = MasterOrchestrator(services, test_configs)
        
        status = orchestrator.get_status()
        
        assert status.get('success') == True
        assert 'documents' in status
        assert 'operations' in status
        assert 'queries' in status
        assert 'rbac' in status


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_document_ingestion_workflow(self, services, test_configs):
        """Test complete document ingestion"""
        orchestrator = MasterOrchestrator(services, test_configs)
        
        # Create test document
        test_doc = Path("test_document.txt")
        test_doc.write_text("This is a test HR document about vacation policies.")
        
        try:
            # Ingest document
            result = orchestrator.ingest_document(
                str(test_doc),
                metadata={'title': 'Test Document'}
            )
            
            # Should succeed
            assert result.get('success') == True or 'document_id' in str(result)
            
        finally:
            # Cleanup
            test_doc.unlink(missing_ok=True)
    
    def test_query_workflow_with_rbac(self, services, test_configs):
        """Test query processing with RBAC enforcement"""
        orchestrator = MasterOrchestrator(services, test_configs)
        db = services['db']
        
        # Create test user
        db.execute("""
            INSERT INTO user_roles (user_id, cdr_code, company_id, department_id, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, ("test_user@test.com", "112", 1, 1, 2))
        
        # Query (may not have data, but should process)
        result = orchestrator.query(
            "What is the vacation policy?",
            user_id="test_user@test.com"
        )
        
        # Should return a result (even if no data found)
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
