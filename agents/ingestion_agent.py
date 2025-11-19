"""
Ingestion Agent
Autonomous document processing with DeepAgents
Uses: chunk_document, extract_metadata, classify_rbac, generate_embeddings, store_embeddings
"""
import json
from typing import Dict, Any
from pathlib import Path
from deepagents import create_deep_agent
from langchain_core.tools import Tool


class IngestionAgent:
    """Autonomous document ingestion agent using DeepAgents"""
    
    def __init__(self, services: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize IngestionAgent
        
        Args:
            services: Dict with 'llm', 'vectordb', 'db' services
            config: Agent configuration
        """
        self.services = services
        self.config = config
        self.name = config.get('name', 'IngestionAgent')
        
        # Create tools with service bindings
        self.tools = self._create_tools()
        
        # Create DeepAgent
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with {len(self.tools)} tools")
    
    def _create_tools(self):
        """Create agent tools with service bindings"""
        from langchain_core.tools import Tool
        import json
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        # Define tool implementations inline to avoid @tool decorator issues
        def chunk_document(text: str, strategy: str = "recursive", 
                          chunk_size: int = 500, overlap: int = 50) -> str:
            """Chunk document using specified strategy"""
            try:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=overlap,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
                chunks = splitter.split_text(text)
                result = [
                    {
                        "chunk_id": f"chunk_{i}",
                        "text": chunk,
                        "strategy": strategy,
                        "size": len(chunk),
                        "index": i
                    }
                    for i, chunk in enumerate(chunks)
                ]
                return json.dumps({
                    "success": True,
                    "num_chunks": len(result),
                    "chunks": result
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})
        
        def extract_metadata(text: str) -> str:
            """Extract metadata from document using LLM"""
            try:
                prompt = f"""
                Analyze this document and extract the following metadata:
                1. Title: A concise title for the document
                2. Summary: A 2-3 sentence summary
                3. Keywords: 5-10 important keywords
                4. Topics: Main topics covered
                5. Document type: Type of document (manual, policy, technical_doc, etc.)
                
                Document excerpt (first 2000 chars):
                {text[:2000]}
                
                Respond ONLY with valid JSON in this format:
                {{
                    "title": "...",
                    "summary": "...",
                    "keywords": ["keyword1", "keyword2", ...],
                    "topics": ["topic1", "topic2", ...],
                    "doc_type": "..."
                }}
                """
                
                result = self.services['llm'].generate_json(prompt)
                
                return json.dumps({
                    "success": True,
                    "metadata": result
                })
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        def classify_rbac(text: str) -> str:
            """Classify document for RBAC using LLM inference"""
            try:
                rbac_config = self.services['rbac_config']
                llm = self.services['llm']
                
                # Subject classification
                subject_prompt = rbac_config['classification_prompts']['subject_classification'].format(
                    text=text[:2000]
                )
                subject_result = llm.generate_json(subject_prompt)
                
                # Sensitivity classification
                sensitivity_prompt = rbac_config['classification_prompts']['sensitivity_classification'].format(
                    text=text[:2000]
                )
                sensitivity_result = llm.generate_json(sensitivity_prompt)
                
                # Map to CDR codes
                subject = subject_result.get('subject', 'general')
                sensitivity = sensitivity_result.get('sensitivity', 'internal')
                
                # Determine required roles
                subject_info = rbac_config.get('subject_areas', {}).get(subject, {})
                default_depts = subject_info.get('default_departments', [1])
                
                sensitivity_info = rbac_config.get('sensitivity_levels', {}).get(sensitivity, {})
                min_role_id = sensitivity_info.get('min_role_id', 2)
                
                required_codes = []
                for cdr_code, mapping in rbac_config.get('role_mappings', {}).items():
                    dept_id = mapping.get('department_id')
                    role_id = mapping.get('role_id')
                    if dept_id in default_depts and role_id >= min_role_id:
                        required_codes.append(cdr_code)
                
                return json.dumps({
                    "success": True,
                    "classification": {
                        "subject": subject,
                        "subject_confidence": subject_result.get('confidence', 0.5),
                        "sensitivity": sensitivity,
                        "sensitivity_confidence": sensitivity_result.get('confidence', 0.5),
                        "required_roles": required_codes
                    }
                })
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        def generate_embeddings(chunks: str) -> str:
            """Generate embeddings for document chunks"""
            try:
                chunks_data = json.loads(chunks)
                
                if not chunks_data.get('success'):
                    return json.dumps({"success": False, "error": "Invalid chunks data"})
                
                chunk_texts = [c['text'] for c in chunks_data['chunks']]
                embeddings = self.services['llm'].embed_documents(chunk_texts)
                
                # Add embeddings to chunk data
                for i, chunk in enumerate(chunks_data['chunks']):
                    chunk['embedding'] = embeddings[i]
                
                return json.dumps({
                    "success": True,
                    "chunks": chunks_data['chunks']
                })
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        def store_embeddings(doc_id: str, chunks: str, rbac: str, meta: str = None) -> str:
            """Store embeddings in vector database"""
            try:
                chunks_data = json.loads(chunks)
                rbac_data = json.loads(rbac)
                meta_data = json.loads(meta) if meta else {}
                
                if not chunks_data.get('success'):
                    return json.dumps({"success": False, "error": "Invalid chunks data"})
                
                if not rbac_data.get('success'):
                    return json.dumps({"success": False, "error": "Invalid RBAC data"})
                
                classification = rbac_data['classification']
                metadata = meta_data.get('metadata', {})
                
                # Store in vector DB
                db = self.services['db']
                vectordb = self.services['vectordb']
                
                # Insert document record
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO documents (doc_id, title, source_path, doc_type, size, status)
                    VALUES (?, ?, ?, ?, ?, 'ingested')
                """, (
                    doc_id,
                    metadata.get('title', 'Untitled'),
                    f"/data/{doc_id}",
                    metadata.get('doc_type', 'unknown'),
                    sum(c['size'] for c in chunks_data['chunks'])
                ))
                db.commit()
                doc_pk = cursor.lastrowid
                
                # Store chunks
                texts = []
                metadatas = []
                ids = []
                
                for chunk in chunks_data['chunks']:
                    chunk_id = f"{doc_id}_{chunk['chunk_id']}"
                    texts.append(chunk['text'])
                    metadatas.append({
                        "doc_id": doc_id,
                        "chunk_index": chunk['index'],
                        "subject": classification['subject'],
                        "sensitivity": classification['sensitivity']
                    })
                    ids.append(chunk_id)
                    
                    # Insert chunk metadata
                    cursor.execute("""
                        INSERT INTO embedding_metadata (doc_id, chunk_id, chunk_index, chunk_text)
                        VALUES (?, ?, ?, ?)
                    """, (doc_pk, chunk_id, chunk['index'], chunk['text']))
                
                vectordb.add_documents(texts, metadatas, ids)
                
                # Store RBAC permissions
                for cdr_code in classification['required_roles']:
                    cursor.execute("""
                        INSERT INTO document_permissions (doc_id, cdr_code, permission_type)
                        VALUES (?, ?, 'read')
                    """, (doc_pk, cdr_code))
                
                db.commit()
                
                return json.dumps({
                    "success": True,
                    "doc_id": doc_id,
                    "chunks_stored": len(chunks_data['chunks']),
                    "permissions_set": len(classification['required_roles'])
                })
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        def get_system_status() -> str:
            """Get current system status"""
            try:
                db = self.services['db']
                vectordb = self.services['vectordb']
                
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM embedding_metadata")
                chunk_count = cursor.fetchone()[0]
                
                return json.dumps({
                    "success": True,
                    "documents": doc_count,
                    "chunks": chunk_count,
                    "vector_count": vectordb.count()
                })
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        # Wrap functions with @tool decorator for proper DeepAgents integration
        from langchain_core.tools import tool
        
        # Create tool-decorated versions that capture services via closure
        @tool
        def chunk_document_tool(text: str, strategy: str = "recursive", 
                               chunk_size: int = 500, overlap: int = 50) -> str:
            """Chunk document text using specified strategy (recursive, character, or token)."""
            return chunk_document(text, strategy, chunk_size, overlap)
        
        @tool
        def extract_metadata_tool(text: str) -> str:
            """Extract metadata from document using LLM (title, summary, keywords, topics, doc_type)."""
            return extract_metadata(text)
        
        @tool
        def classify_rbac_tool(text: str) -> str:
            """Classify document for RBAC permissions using LLM to determine subject and sensitivity."""
            return classify_rbac(text)
        
        @tool
        def generate_embeddings_tool(chunks: str) -> str:
            """Generate embeddings for document chunks (expects JSON string from chunk_document)."""
            return generate_embeddings(chunks)
        
        @tool
        def store_embeddings_tool(doc_id: str, chunks: str, rbac: str, meta: str = "{}") -> str:
            """Store embeddings in vector database with RBAC and metadata."""
            return store_embeddings(doc_id, chunks, rbac, meta)
        
        @tool
        def get_system_status_tool() -> str:
            """Get current system status and statistics (document count, agent operations, etc)."""
            return get_system_status()
        
        return [chunk_document_tool, extract_metadata_tool, classify_rbac_tool,
                generate_embeddings_tool, store_embeddings_tool, get_system_status_tool]
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for IngestionAgent"""
        return """You are an autonomous document ingestion agent for a RAG system with RBAC.

Your responsibilities:
1. Process documents through a complete ingestion pipeline
2. Break down complex ingestion tasks using write_todos
3. Extract metadata and classify RBAC requirements using LLM
4. Generate embeddings and store them properly
5. Log all operations for tracking

Available tools:
- chunk_document_tool: Split documents into chunks (strategies: recursive, character, token)
- extract_metadata: Extract title, summary, keywords using LLM
- classify_rbac: Classify document sensitivity and assign CDR access codes
- generate_embeddings: Create vector embeddings for chunks
- store_embeddings: Store in ChromaDB and SQLite with full metadata
- get_system_status: Check system status and capacity
- write_todos: Plan multi-step ingestion workflows
- task: Spawn subagents for parallel processing

Workflow guidelines:
1. Always use write_todos to plan your approach for complex documents
2. Extract metadata early to understand document context
3. Use RBAC classification to assign proper access controls
4. Store embeddings with complete metadata for healing analysis
5. Log success/failure for system tracking

CDR Access Codes:
- Format: 3 digits (Company-Department-Role)
- Example: "112" = Company 1, HR, Associate level
- Higher role IDs have more access (1=basic, 5=executive)

Always provide detailed feedback about what was accomplished.
"""
    
    def ingest_document(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ingest a document autonomously
        
        Args:
            file_path: Path to document file
            metadata: Optional document metadata
            
        Returns:
            Ingestion results dictionary
        """
        try:
            # Read document
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate document ID
            doc_id = metadata.get('id') if metadata else path.stem
            
            # Create request for agent
            request = f"""
Ingest the following document:

Document ID: {doc_id}
File: {file_path}
Size: {len(content)} characters

Additional metadata: {json.dumps(metadata) if metadata else 'None'}

Steps you should take:
1. Use write_todos to plan the ingestion workflow
2. Extract metadata from the document
3. Classify RBAC requirements (determine sensitivity and required access levels)
4. Chunk the document using an appropriate strategy
5. Generate embeddings for all chunks
6. Store embeddings with full metadata and RBAC permissions
7. Provide a summary of what was accomplished

Document content:
{content[:3000]}{'...' if len(content) > 3000 else ''}
"""
            
            # Invoke DeepAgent
            print(f"\n[DeepAgent Processing] Starting ingestion workflow...")
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": request}]
            })
            
            # Extract response
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else None
            response = final_message.content if final_message and hasattr(final_message, 'content') else 'No response'
            
            # Display todo list if created
            print(f"\n[DeepAgent Messages] Received {len(messages)} messages")
            for i, msg in enumerate(messages):
                if hasattr(msg, 'content'):
                    content = msg.content
                    # Check if this is a todo list
                    if 'TODO' in str(content).upper() or '[]' in str(content) or '[ ]' in str(content):
                        print(f"\n[Todo List Detected in Message {i+1}]:")
                        print(content)
                    elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                        print(f"\n[Tool Calls in Message {i+1}]:")
                        for tc in msg.tool_calls:
                            print(f"  - {tc.get('name', 'unknown')}: {tc.get('args', {})}")
            
            print(f"\n[Final Response]: {response[:200]}...")
            
            # Log operation
            self.services['db'].log_agent_operation(
                agent_name=self.name,
                operation_type='ingestion',
                query=f"Ingest document: {file_path}",
                final_response=response,
                metadata={'doc_id': doc_id, 'file_path': file_path}
            )
            
            return {
                "success": True,
                "doc_id": doc_id,
                "response": response,
                "messages": len(messages)
            }
            
        except Exception as e:
            print(f"\n[ERROR] Ingestion failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def ingest_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        Ingest all documents in a directory
        
        Args:
            dir_path: Path to directory
            
        Returns:
            Batch ingestion results
        """
        path = Path(dir_path)
        if not path.is_dir():
            return {
                "success": False,
                "error": f"Not a directory: {dir_path}"
            }
        
        results = []
        for file_path in path.rglob('*.txt'):
            print(f"\n{'='*60}")
            print(f"Processing: {file_path.name}")
            print('='*60)
            result = self.ingest_document(str(file_path))
            results.append({
                "file": str(file_path),
                "success": result.get('success', False),
                "error": result.get('error', None)
            })
            
            if not result.get('success'):
                print(f"[FAILED] {result.get('error', 'Unknown error')}")
        
        return {
            "success": True,
            "total_files": len(results),
            "successful": sum(1 for r in results if r['success']),
            "failed": sum(1 for r in results if not r['success']),
            "results": results
        }
