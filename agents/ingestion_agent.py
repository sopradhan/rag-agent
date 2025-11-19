"""
Ingestion Agent
Autonomous document processing with DeepAgents
5-step workflow: chunk → metadata → RBAC → embeddings → store
"""
import json
from typing import Dict, Any
from pathlib import Path
from deepagents import create_deep_agent
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config.loader import load_all_configs


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
        
        # Load configuration with system prompts
        try:
            self.prompts_config = load_all_configs('config').get('prompts', {})
        except:
            self.prompts_config = {}
        
        # Create tools with service bindings
        self.tools = self._create_tools()
        
        # Create DeepAgent with system prompt from config
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with {len(self.tools)} tools (prompts from config)")
    
    def _create_tools(self):
        """Create the single ingestion tool with complete 5-step workflow"""
        
        # Capture services via closure
        llm_service = self.services['llm']
        vectordb_service = self.services['vectordb']
        db_service = self.services['db']
        rbac_config = self.services.get('rbac_config', {})
        
        @tool
        def ingest_document_from_file(doc_id: str, file_path: str) -> str:
            """
            Complete 5-step document ingestion:
            1. Read & chunk document
            2. Extract metadata
            3. Classify RBAC
            4. Generate embeddings
            5. Store in database
            """
            try:
                # Read file
                path = Path(file_path)
                if not path.exists():
                    return json.dumps({"success": False, "error": f"File not found: {file_path}"})
                
                with open(path, 'r', encoding='utf-8') as f:
                    document_text = f.read()
                
                print(f"\n[1/5] Chunking {doc_id}...", flush=True)
                # Step 1: Chunk document
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=50,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
                chunks = splitter.split_text(document_text)
                chunks_data = [
                    {
                        "chunk_id": f"chunk_{i}",
                        "text": chunk,
                        "strategy": "recursive",
                        "size": len(chunk),
                        "index": i
                    }
                    for i, chunk in enumerate(chunks)
                ]
                print(f"  ✓ {len(chunks_data)} chunks", flush=True)
                
                print(f"[2/5] Metadata...", flush=True)
                # Step 2: Extract metadata
                metadata_prompt = f"""Analyze this document and extract metadata:
1. Title (concise)
2. Summary (2-3 sentences)
3. Keywords (5-10 important)
4. Topics (main topics)
5. Document type (manual, policy, etc)

Document (first 2000 chars):
{document_text[:2000]}

Respond ONLY with JSON:
{{"title": "...", "summary": "...", "keywords": [...], "topics": [...], "doc_type": "..."}}
"""
                metadata = llm_service.generate_json(metadata_prompt)
                title = metadata.get('title', 'Untitled')
                print(f"  ✓ {title}", flush=True)
                
                print(f"[3/5] RBAC...", flush=True)
                # Step 3: Classify RBAC
                subject_prompt = rbac_config.get('classification_prompts', {}).get('subject_classification', 
                                                 'Classify subject').format(text=document_text[:2000])
                subject_result = llm_service.generate_json(subject_prompt)
                
                sensitivity_prompt = rbac_config.get('classification_prompts', {}).get('sensitivity_classification',
                                                    'Classify sensitivity').format(text=document_text[:2000])
                sensitivity_result = llm_service.generate_json(sensitivity_prompt)
                
                subject = subject_result.get('subject', 'general')
                sensitivity = sensitivity_result.get('sensitivity', 'internal')
                
                # Map to CDR codes
                subject_info = rbac_config.get('subject_areas', {}).get(subject, {})
                default_depts = subject_info.get('default_departments', [1])
                sensitivity_info = rbac_config.get('sensitivity_levels', {}).get(sensitivity, {})
                min_role_id = sensitivity_info.get('min_role_id', 2)
                
                required_codes = []
                for cdr_code, mapping in rbac_config.get('role_mappings', {}).items():
                    if mapping.get('department_id') in default_depts and mapping.get('role_id') >= min_role_id:
                        required_codes.append(cdr_code)
                
                print(f"  ✓ {subject} / {sensitivity} ({len(required_codes)} roles)", flush=True)
                
                print(f"[4/5] Embeddings...", flush=True)
                # Step 4: Generate embeddings
                texts = [c['text'] for c in chunks_data]
                embeddings = llm_service.generate_embeddings(texts)
                for i, chunk in enumerate(chunks_data):
                    chunk['embedding'] = embeddings[i]
                print(f"  ✓ {len(embeddings)} embeddings", flush=True)
                
                print(f"\n[5/5] Storing...", flush=True)
                # Step 5: Store in database
                
                # Store document record (use 'id' as primary key)
                doc_pk = db_service.insert_and_get_id(
                    """INSERT INTO documents (id, title, source, doc_type)
                       VALUES (?, ?, ?, ?)""",
                    (doc_id, title, f"/data/{doc_id}", metadata.get('doc_type', 'unknown'))
                )
                print(f"  ✓ Document record stored", flush=True)
                print(f"  ✓ Document record stored", flush=True)
                
                # Store chunks metadata in SQLite (NO embedding vectors, only metadata)
                for i, chunk in enumerate(chunks_data):
                    chunk_id = f"{doc_id}_{chunk['chunk_id']}"
                    db_service.insert_embedding_metadata(
                        document_id=doc_pk or doc_id,
                        chunk_id=chunk_id,
                        chunk_strategy='recursive',
                        chunk_size=chunk['size'],
                        overlap=50,
                        embedding_model='sentence-transformers/all-MiniLM-L6-v2',
                        embedding_version='v1'
                    )
                print(f"  ✓ {len(chunks_data)} chunk metadata records stored (embeddings in ChromaDB only)", flush=True)
                
                # Store embeddings in ChromaDB with comprehensive metadata
                ids = [f"{doc_id}_{c['chunk_id']}" for c in chunks_data]
                embeddings_list = embeddings  # The vector embeddings from step 4
                
                # Build metadata with RBAC and content info
                metadatas = [
                    {
                        "document_id": doc_id,
                        "document_title": title,
                        "document_type": metadata.get('doc_type', 'unknown'),
                        "chunk_index": c['index'],
                        "chunk_size": c['size'],
                        "subject": subject,
                        "sensitivity": sensitivity,
                        "keywords": ",".join(metadata.get('keywords', [])),
                        "topics": ",".join(metadata.get('topics', [])),
                        "cdr_codes": ",".join(required_codes)
                    }
                    for c in chunks_data
                ]
                documents = [c['text'] for c in chunks_data]
                
                # Add documents to ChromaDB with embeddings
                print(f"  ✓ Adding {len(ids)} embeddings to ChromaDB", flush=True)
                vectordb_service.add_documents(
                    ids=ids,
                    embeddings=embeddings_list,
                    metadatas=metadatas,
                    documents=documents
                )
                print(f"  ✓ {len(ids)} embeddings stored with metadata", flush=True)
                
                # Store RBAC permissions in SQLite
                print(f"  ✓ Setting {len(required_codes)} RBAC permissions", flush=True)
                for cdr_code in required_codes:
                    db_service.assign_document_permission(
                        doc_id=doc_pk or doc_id,
                        cdr_code=cdr_code,
                        sensitivity=sensitivity,
                        subject=subject,
                        assigned_by='ingestion_agent'
                    )
                print(f"  ✓ RBAC permissions saved", flush=True)
                
                # Store extracted metadata in SQLite for agent/LLM metadata tracking (key-value format)
                try:
                    # Store metadata as key-value pairs in document_metadata table
                    metadata_pairs = [
                        (doc_id, 'summary', metadata.get('summary', '')),
                        (doc_id, 'keywords', ','.join(metadata.get('keywords', []))),
                        (doc_id, 'topics', ','.join(metadata.get('topics', []))),
                        (doc_id, 'keywords_json', json.dumps(metadata.get('keywords', []))),
                        (doc_id, 'topics_json', json.dumps(metadata.get('topics', []))),
                        (doc_id, 'embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
                        (doc_id, 'embedding_dimension', '384'),
                        (doc_id, 'chunking_strategy', 'recursive'),
                        (doc_id, 'chunk_size', '500'),
                        (doc_id, 'chunk_overlap', '50'),
                    ]
                    for document_id, key, value in metadata_pairs:
                        db_service.execute(
                            """INSERT OR REPLACE INTO document_metadata (document_id, key, value)
                               VALUES (?, ?, ?)""",
                            (document_id, key, str(value))
                        )
                    print(f"  ✓ Document metadata + LLM metadata stored", flush=True)
                except Exception as e:
                    print(f"  ⚠ Document metadata table issue: {str(e)}", flush=True)
                
                print(f"\n  ✓✓✓ INGESTION COMPLETE ✓✓✓", flush=True)
                
                return json.dumps({
                    "success": True,
                    "doc_id": doc_id,
                    "file_path": file_path,
                    "chunks_created": len(chunks_data),
                    "chunks_stored": len(chunks_data),
                    "embeddings_generated": len(embeddings),
                    "embeddings_stored": len(ids),
                    "permissions_set": len(required_codes),
                    "title": title,
                    "summary": metadata.get('summary', ''),
                    "keywords": metadata.get('keywords', []),
                    "topics": metadata.get('topics', []),
                    "subject": subject,
                    "sensitivity": sensitivity,
                    "storage": {
                        "documents_table": "1 record",
                        "embedding_metadata_table": f"{len(chunks_data)} records (metadata only, embeddings in ChromaDB)",
                        "chromadb_embeddings": f"{len(ids)} vectors with full metadata",
                        "document_permissions_table": f"{len(required_codes)} RBAC records",
                        "document_metadata_table": "1 record (agent/LLM/embedding metadata)"
                    },
                    "message": f"Successfully ingested {doc_id}: {len(chunks_data)} chunks, {len(embeddings)} embeddings, {len(required_codes)} RBAC roles"
                })
                
            except Exception as e:
                print(f"  ERROR: {str(e)}", flush=True)
                import traceback
                traceback.print_exc()
                return json.dumps({"success": False, "error": str(e)})
        
        return [ingest_document_from_file]
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for IngestionAgent from config"""
        # Try to get from config first
        if self.prompts_config.get('ingestion_agent', {}).get('system_prompt'):
            return self.prompts_config['ingestion_agent']['system_prompt']
        
        # Fallback prompt
        return """You are a document ingestion agent. Your job:

1. User provides doc_id and file_path
2. Call: ingest_document_from_file(doc_id, file_path)
3. Report results

DO NOT delay. CALL THE TOOL NOW.
"""
    
    def ingest_document(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ingest a document using the agent
        
        Args:
            file_path: Path to document file
            metadata: Optional document metadata
            
        Returns:
            Ingestion results dictionary
        """
        try:
            # Verify file exists
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            # Generate document ID
            doc_id = metadata.get('id') if metadata else path.stem
            
            # Create direct request - tell agent to call the tool NOW
            request = f"""Ingest document.
doc_id: {doc_id}
file_path: {file_path}

Call ingest_document_from_file("{doc_id}", "{file_path}") NOW."""
            
            # Invoke agent
            print(f"[{doc_id}] Ingesting...", flush=True)
            
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": request}]
            })
            
            # Extract response
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else None
            response = final_message.content if final_message and hasattr(final_message, 'content') else 'No response'
            
            # Log
            self.services['db'].log_agent_operation(
                agent_name=self.name,
                operation_type='ingestion',
                query=f"Ingest: {file_path}",
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
            print(f"[ERROR] {str(e)}", flush=True)
            return {"success": False, "error": str(e)}
    
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
