"""
Enhanced Data Source Ingestion with PDF and JSON Support

Supports:
- PDF files (text extraction, page-by-page)
- JSON files (nested structure flattening)
- Text files (existing)
- Integration with DeepClassifier for intelligent classification
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PDF libraries not installed. Run: pip install PyPDF2 pdfplumber")

from src.agents.deep_classifier import DeepClassifier, ClassificationResult
from src.storage import RAGDatabase
from src.storage.vector_store import ChromaVectorStore
from src.subagents.sqlite_ingestion_subagent import SQLiteIngestionSubagent


class PDFIngestionAgent:
    """
    Handles PDF document ingestion with page-level granularity
    Documents + embeddings → ChromaDB | Metadata → SQLite
    """
    
    def __init__(self, use_deep_classifier: bool = True):
        self.db = RAGDatabase()
        self.vector_store = ChromaVectorStore(db_path='data/chroma_db')
        self.deep_classifier = DeepClassifier() if use_deep_classifier else None
        
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF libraries not available. Install: pip install PyPDF2 pdfplumber")
    
    def ingest_pdf(self, pdf_path: str, extract_images: bool = False) -> List[str]:
        """
        Ingest a PDF file with page-by-page extraction
        
        Args:
            pdf_path: Path to PDF file
            extract_images: Whether to extract images (future enhancement)
            
        Returns:
            List of document IDs created
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"\n📄 Ingesting PDF: {pdf_path}")
        
        # Extract metadata and content
        metadata = self._extract_pdf_metadata(pdf_path)
        pages = self._extract_pdf_pages(pdf_path)
        
        print(f"   Extracted {len(pages)} pages")
        
        # Combine all pages for classification
        full_content = "\n\n".join([page['text'] for page in pages if page['text'].strip()])
        
        # Classify document
        if self.deep_classifier:
            classification = self.deep_classifier.classify_document(
                content=full_content,
                source=pdf_path,
                metadata=metadata
            )
            print(f"   Classification: {classification.classification} (confidence: {classification.confidence:.2f})")
            print(f"   Namespace: {classification.namespace}")
        else:
            # Fallback classification
            classification = ClassificationResult(
                classification="general",
                confidence=0.5,
                method="default",
                namespace="general/documents",
                min_access_level=1,
                reasoning="No deep classifier available",
                sub_categories=[],
                metadata={}
            )
        
        # Create parent doc_id
        filename = Path(pdf_path).stem
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        parent_doc_id = f"pdf_{filename}_{timestamp}"
        
        # Store each page as a chunk
        doc_ids = []
        total_pages = len(pages)
        chroma_doc_ids = []
        chroma_texts = []
        chroma_metadatas = []
        
        for page_data in pages:
            page_num = page_data['page_num']
            page_text = page_data['text']
            
            if not page_text.strip():
                continue  # Skip empty pages
            
            doc_id = f"{parent_doc_id}_page_{page_num}"
            
            # Insert to SQLite (metadata)
            self.db.insert_document(
                doc_id=doc_id,
                source=f"{pdf_path}#page={page_num}",
                content=page_text,
                chunk_id=page_num,
                total_chunks=total_pages,
                classification=classification.classification,
                min_access_level=classification.min_access_level,
                namespace=classification.namespace,
                parent_doc_id=parent_doc_id
            )
            
            # Collect for ChromaDB (document + embedding)
            chroma_doc_ids.append(doc_id)
            chroma_texts.append(page_text)
            chroma_metadatas.append({
                "title": f"{Path(pdf_path).name} - Page {page_num}",
                "category": classification.classification,
                "source": f"{Path(pdf_path).name}#page={page_num}",
                "access_level": str(classification.min_access_level),
                "page_number": str(page_num),
                "total_pages": str(total_pages)
            })
            
            # Store page metadata in SQLite
            page_metadata = {
                "page_number": str(page_num),
                "total_pages": str(total_pages),
                "file_name": Path(pdf_path).name,
                "classification_confidence": str(classification.confidence),
                "classification_method": classification.method,
                **{f"pdf_{k}": str(v) for k, v in metadata.items()}
            }
            
            for key, value in page_metadata.items():
                self.db.insert("metadata", {
                    "doc_id": doc_id,
                    "key": key,
                    "value": value,
                    "created_at": datetime.now().isoformat()
                })
            
            doc_ids.append(doc_id)
        
        # Add all documents to ChromaDB at once (with embeddings)
        if chroma_doc_ids:
            try:
                self.vector_store.add_documents(
                    doc_ids=chroma_doc_ids,
                    texts=chroma_texts,
                    metadatas=chroma_metadatas
                )
                print(f"   ✅ Added {len(chroma_doc_ids)} pages to ChromaDB (with embeddings)")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not add to ChromaDB: {e}")
        
        # Build tree index
        if self.deep_classifier:
            self.deep_classifier.build_tree_index(
                classification.classification,
                classification.namespace,
                parent_doc_id
            )
        
        # Log operation
        self.db.log_operation(
            operation_type="pdf_ingestion",
            agent_name="PDFIngestionAgent",
            status="success",
            input_data=json.dumps({
                "file": pdf_path,
                "pages": total_pages
            }),
            output_data=json.dumps({
                "parent_doc_id": parent_doc_id,
                "doc_ids": doc_ids,
                "classification": classification.classification,
                "namespace": classification.namespace
            })
        )
        
        print(f"   ✅ Created {len(doc_ids)} document chunks")
        return doc_ids
    
    def _extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                info = reader.metadata
                
                if info:
                    metadata['title'] = info.get('/Title', '')
                    metadata['author'] = info.get('/Author', '')
                    metadata['subject'] = info.get('/Subject', '')
                    metadata['creator'] = info.get('/Creator', '')
                    metadata['producer'] = info.get('/Producer', '')
                    metadata['creation_date'] = info.get('/CreationDate', '')
                
                metadata['page_count'] = len(reader.pages)
        except Exception as e:
            print(f"   Warning: Could not extract PDF metadata: {e}")
        
        return metadata
    
    def _extract_pdf_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text from each page using pdfplumber (better quality)"""
        pages = []
        
        try:
            # Try pdfplumber first (better text extraction)
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    
                    pages.append({
                        'page_num': page_num,
                        'text': text,
                        'width': page.width,
                        'height': page.height
                    })
        except Exception as e:
            print(f"   Warning: pdfplumber failed, falling back to PyPDF2: {e}")
            
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(reader.pages, start=1):
                        text = page.extract_text() or ""
                        
                        pages.append({
                            'page_num': page_num,
                            'text': text,
                            'width': None,
                            'height': None
                        })
            except Exception as e2:
                print(f"   Error: Both PDF extraction methods failed: {e2}")
                raise
        
        return pages


class JSONIngestionAgent:
    """
    Handles JSON document ingestion with nested structure support
    Documents + embeddings → ChromaDB | Metadata → SQLite
    """
    
    def __init__(self, use_deep_classifier: bool = True):
        self.db = RAGDatabase()
        self.vector_store = ChromaVectorStore(db_path='data/chroma_db')
        self.deep_classifier = DeepClassifier() if use_deep_classifier else None
    
    def ingest_json(self, json_path: str, flatten: bool = True) -> List[str]:
        """
        Ingest a JSON file
        
        Args:
            json_path: Path to JSON file
            flatten: Whether to flatten nested structures
            
        Returns:
            List of document IDs created
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        print(f"\n📊 Ingesting JSON: {json_path}")
        
        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            # Array of objects
            print(f"   Found array with {len(data)} items")
            return self._ingest_json_array(json_path, data, flatten)
        elif isinstance(data, dict):
            # Single object or nested structure
            print(f"   Found object with {len(data)} keys")
            return self._ingest_json_object(json_path, data, flatten)
        else:
            raise ValueError(f"Unsupported JSON structure: {type(data)}")
    
    def _ingest_json_array(self, json_path: str, data: List[Dict], flatten: bool) -> List[str]:
        """Ingest JSON array (e.g., list of records)"""
        filename = Path(json_path).stem
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        parent_doc_id = f"json_{filename}_{timestamp}"
        
        doc_ids = []
        total_items = len(data)
        chroma_doc_ids = []
        chroma_texts = []
        chroma_metadatas = []
        
        for idx, item in enumerate(data, start=1):
            # Convert item to text
            if flatten:
                text = self._flatten_json_to_text(item)
            else:
                text = json.dumps(item, indent=2)
            
            # Classify item
            if self.deep_classifier:
                classification = self.deep_classifier.classify_document(
                    content=text,
                    source=f"{json_path}[{idx-1}]"
                )
            else:
                classification = ClassificationResult(
                    classification="general",
                    confidence=0.5,
                    method="default",
                    namespace="general/json",
                    min_access_level=1,
                    reasoning="No classifier",
                    sub_categories=[],
                    metadata={}
                )
            
            doc_id = f"{parent_doc_id}_item_{idx}"
            
            # Insert to SQLite (metadata)
            self.db.insert_document(
                doc_id=doc_id,
                source=f"{json_path}[{idx-1}]",
                content=text,
                chunk_id=idx,
                total_chunks=total_items,
                classification=classification.classification,
                min_access_level=classification.min_access_level,
                namespace=classification.namespace,
                parent_doc_id=parent_doc_id
            )
            
            # Collect for ChromaDB (document + embedding)
            chroma_doc_ids.append(doc_id)
            chroma_texts.append(text)
            chroma_metadatas.append({
                "title": f"Item {idx} from {Path(json_path).name}",
                "category": classification.classification,
                "source": f"{Path(json_path).name}[{idx-1}]",
                "access_level": str(classification.min_access_level),
                "json_index": str(idx-1),
                "total_items": str(total_items)
            })
            
            # Store metadata in SQLite
            metadata_entries = {
                "json_index": str(idx-1),
                "total_items": str(total_items),
                "file_name": Path(json_path).name,
                "classification_method": classification.method
            }
            
            # Extract key fields from item
            if isinstance(item, dict):
                for key in ['id', 'name', 'title', 'type', 'category']:
                    if key in item:
                        metadata_entries[f"json_{key}"] = str(item[key])
            
            for key, value in metadata_entries.items():
                self.db.insert("metadata", {
                    "doc_id": doc_id,
                    "key": key,
                    "value": value,
                    "created_at": datetime.now().isoformat()
                })
            
            doc_ids.append(doc_id)
        
        # Add all documents to ChromaDB at once (with embeddings)
        if chroma_doc_ids:
            try:
                self.vector_store.add_documents(
                    doc_ids=chroma_doc_ids,
                    texts=chroma_texts,
                    metadatas=chroma_metadatas
                )
                print(f"   ✅ Added {len(chroma_doc_ids)} items to ChromaDB (with embeddings)")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not add to ChromaDB: {e}")
        
        # Log operation
        self.db.log_operation(
            operation_type="json_ingestion",
            agent_name="JSONIngestionAgent",
            status="success",
            input_data=json.dumps({"file": json_path, "items": total_items}),
            output_data=json.dumps({"parent_doc_id": parent_doc_id, "doc_ids": doc_ids})
        )
        
        print(f"   ✅ Created {len(doc_ids)} document chunks")
        return doc_ids
    
    def _ingest_json_object(self, json_path: str, data: Dict, flatten: bool) -> List[str]:
        """Ingest single JSON object (may contain nested data)"""
        filename = Path(json_path).stem
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        parent_doc_id = f"json_{filename}_{timestamp}"
        
        # Convert to text
        if flatten:
            text = self._flatten_json_to_text(data)
        else:
            text = json.dumps(data, indent=2)
        
        # Classify
        if self.deep_classifier:
            classification = self.deep_classifier.classify_document(
                content=text,
                source=json_path
            )
        else:
            classification = ClassificationResult(
                classification="general",
                confidence=0.5,
                method="default",
                namespace="general/json",
                min_access_level=1,
                reasoning="No classifier",
                sub_categories=[],
                metadata={}
            )
        
        # Insert to SQLite (metadata)
        self.db.insert_document(
            doc_id=parent_doc_id,
            source=json_path,
            content=text,
            chunk_id=1,
            total_chunks=1,
            classification=classification.classification,
            min_access_level=classification.min_access_level,
            namespace=classification.namespace,
            parent_doc_id=None
        )
        
        # Add to ChromaDB (document + embedding)
        try:
            self.vector_store.add_documents(
                doc_ids=[parent_doc_id],
                texts=[text],
                metadatas=[{
                    "title": Path(json_path).name,
                    "category": classification.classification,
                    "source": Path(json_path).name,
                    "access_level": str(classification.min_access_level),
                    "json_keys": json.dumps(list(data.keys())[:20])
                }]
            )
            print(f"   ✅ Added to ChromaDB (with embedding)")
        except Exception as e:
            print(f"   ⚠️ Warning: Could not add to ChromaDB: {e}")
        
        # Store metadata in SQLite
        metadata_entries = {
            "file_name": Path(json_path).name,
            "json_keys": json.dumps(list(data.keys())[:20]),  # First 20 keys
            "classification_method": classification.method
        }
        
        for key, value in metadata_entries.items():
            self.db.insert("metadata", {
                "doc_id": parent_doc_id,
                "key": key,
                "value": value,
                "created_at": datetime.now().isoformat()
            })
        
        # Log operation
        self.db.log_operation(
            operation_type="json_ingestion",
            agent_name="JSONIngestionAgent",
            status="success",
            input_data=json.dumps({"file": json_path, "type": "object"}),
            output_data=json.dumps({"doc_id": parent_doc_id})
        )
        
        print(f"   ✅ Created 1 document")
        return [parent_doc_id]
    
    def _flatten_json_to_text(self, data: Any, prefix: str = "") -> str:
        """Flatten nested JSON to readable text"""
        lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, (dict, list)):
                    lines.append(f"{full_key}:")
                    lines.append(self._flatten_json_to_text(value, full_key))
                else:
                    lines.append(f"{full_key}: {value}")
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{idx}]:")
                    lines.append(self._flatten_json_to_text(item, f"{prefix}[{idx}]"))
                else:
                    lines.append(f"{prefix}[{idx}]: {item}")
        else:
            lines.append(str(data))
        
        return "\n".join(lines)


class UnifiedIngestionAgent:
    """
    Unified ingestion agent supporting all file types
    Documents + embeddings → ChromaDB | Metadata → SQLite
    """
    
    def __init__(self, use_deep_classifier: bool = True):
        self.pdf_agent = PDFIngestionAgent(use_deep_classifier) if PDF_AVAILABLE else None
        self.json_agent = JSONIngestionAgent(use_deep_classifier)
        self.deep_classifier = DeepClassifier() if use_deep_classifier else None
        self.db = RAGDatabase()
        self.vector_store = ChromaVectorStore(db_path='data/chroma_db')
        self.sqlite_agent = SQLiteIngestionSubagent(self.db, self.vector_store)
    
    def ingest_file(self, file_path: str) -> List[str]:
        """
        Auto-detect file type and ingest appropriately
        
        Args:
            file_path: Path to file
            
        Returns:
            List of document IDs created
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = Path(file_path).suffix.lower()
        
        if extension == '.pdf':
            if not self.pdf_agent:
                raise RuntimeError("PDF support not available. Install: pip install PyPDF2 pdfplumber")
            return self.pdf_agent.ingest_pdf(file_path)
        
        elif extension == '.json':
            return self.json_agent.ingest_json(file_path)
        
        elif extension in ['.txt', '.md', '.text']:
            return self._ingest_text_file(file_path)
        
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    def ingest_from_sqlite(
        self,
        db_path: str,
        table_name: str,
        text_columns: List[str],
        metadata_columns: Optional[List[str]] = None,
        classification: str = "general",
        min_access_level: int = 1
    ) -> Dict[str, Any]:
        """
        Ingest data from SQLite database table.
        
        Args:
            db_path: Path to SQLite database
            table_name: Table to ingest
            text_columns: Columns containing text content
            metadata_columns: Columns for metadata extraction
            classification: Document classification
            min_access_level: RBAC minimum access level
        
        Returns:
            Ingestion result with statistics
        """
        print(f"\n🗄️ Ingesting from SQLite table: {table_name}")
        
        result = self.sqlite_agent.ingest_from_table(
            db_path=db_path,
            table_name=table_name,
            text_columns=text_columns,
            metadata_columns=metadata_columns,
            classification=classification,
            min_access_level=min_access_level
        )
        
        if result["status"] == "success":
            print(f"   ✅ Ingestion successful!")
            print(f"      Records: {result['records_processed']}")
            print(f"      Documents: {result['documents_created']}")
            print(f"      Errors: {result['errors']}")
        else:
            print(f"   ❌ Ingestion failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def ingest_from_sqlite_query(
        self,
        db_path: str,
        query: str,
        text_columns: List[str],
        metadata_columns: Optional[List[str]] = None,
        classification: str = "general",
        min_access_level: int = 1,
        query_name: str = "custom_query"
    ) -> Dict[str, Any]:
        """
        Ingest data from custom SQLite query.
        
        Args:
            db_path: Path to SQLite database
            query: SQL query to execute
            text_columns: Query result columns containing text
            metadata_columns: Query result columns for metadata
            classification: Document classification
            min_access_level: RBAC minimum access level
            query_name: Name for tracking
        
        Returns:
            Ingestion result with statistics
        """
        print(f"\n🗄️ Ingesting from SQLite query: {query_name}")
        
        result = self.sqlite_agent.ingest_from_query(
            db_path=db_path,
            query=query,
            text_columns=text_columns,
            metadata_columns=metadata_columns,
            classification=classification,
            min_access_level=min_access_level,
            query_name=query_name
        )
        
        if result["status"] == "success":
            print(f"   ✅ Ingestion successful!")
            print(f"      Records: {result['records_processed']}")
            print(f"      Documents: {result['documents_created']}")
            print(f"      Errors: {result['errors']}")
        else:
            print(f"   ❌ Ingestion failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def ingest_directory(self, directory_path: str, recursive: bool = True,
                        file_extensions: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Ingest all supported files in a directory
        
        Args:
            directory_path: Path to directory
            recursive: Whether to search subdirectories
            file_extensions: List of extensions to include (e.g., ['.pdf', '.json'])
            
        Returns:
            Dictionary mapping file paths to document IDs
        """
        if file_extensions is None:
            file_extensions = ['.pdf', '.json', '.txt', '.md']
        
        results = {}
        path_obj = Path(directory_path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all matching files
        pattern = "**/*" if recursive else "*"
        all_files = []
        
        for ext in file_extensions:
            all_files.extend(path_obj.glob(f"{pattern}{ext}"))
        
        print(f"\n📂 Found {len(all_files)} files to ingest")
        
        # Ingest each file
        for file_path in all_files:
            try:
                print(f"\n{'='*60}")
                doc_ids = self.ingest_file(str(file_path))
                results[str(file_path)] = doc_ids
            except Exception as e:
                print(f"   ❌ Error ingesting {file_path}: {e}")
                results[str(file_path)] = []
        
        print(f"\n{'='*60}")
        print(f"✅ Ingestion complete: {len([r for r in results.values() if r])} files successful")
        
        return results
    
    def _ingest_text_file(self, file_path: str) -> List[str]:
        """Ingest plain text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if self.deep_classifier:
            doc_ids = self.deep_classifier.classify_and_store(
                content=content,
                source=file_path,
                chunk_intelligently=True
            )
        else:
            # Fallback: simple storage
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            doc_id = f"text_{Path(file_path).stem}_{timestamp}"
            
            # Store in SQLite (metadata)
            self.db.insert_document(
                doc_id=doc_id,
                source=file_path,
                content=content,
                classification="general",
                namespace="general/text"
            )
            
            # Add to ChromaDB (document + embedding)
            try:
                self.vector_store.add_documents(
                    doc_ids=[doc_id],
                    texts=[content],
                    metadatas=[{
                        "title": Path(file_path).name,
                        "category": "general",
                        "source": Path(file_path).name,
                        "access_level": "1"
                    }]
                )
                print(f"   ✅ Added to ChromaDB (with embedding)")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not add to ChromaDB: {e}")
            
            doc_ids = [doc_id]
        
        print(f"   ✅ Created {len(doc_ids)} document chunks")
        return doc_ids


# Example usage
if __name__ == "__main__":
    # Test PDF ingestion
    agent = UnifiedIngestionAgent(use_deep_classifier=True)
    
    # Ingest single file
    # doc_ids = agent.ingest_file("data/sample.pdf")
    
    # Ingest directory
    # results = agent.ingest_directory("data/", recursive=True)
    
    print("Ingestion agent ready. Use agent.ingest_file() or agent.ingest_directory()")
