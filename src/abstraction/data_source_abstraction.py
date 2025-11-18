"""
Data Source Abstraction Layer
Provides unified interface for multiple data source types.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml


class Document:
    """Unified document representation."""
    
    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ):
        self.content = content
        self.metadata = metadata or {}
        self.source = source
        self.id = None  # Will be set during ingestion
    
    def __repr__(self):
        return f"Document(source={self.source}, content_length={len(self.content)})"


class BaseDataLoader(ABC):
    """Base class for all data loaders."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    def load(self, source: str) -> List[Document]:
        """Load documents from source."""
        pass
    
    @abstractmethod
    def supports(self, source: str) -> bool:
        """Check if loader supports this source."""
        pass


class PDFLoader(BaseDataLoader):
    """PDF document loader."""
    
    def supports(self, source: str) -> bool:
        return source.lower().endswith(tuple(self.config.get("supported_extensions", [".pdf"])))
    
    def load(self, source: str) -> List[Document]:
        """Load PDF document."""
        try:
            import PyPDF2
            documents = []
            
            with open(source, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        doc = Document(
                            content=text,
                            metadata={
                                "source": source,
                                "page": page_num + 1,
                                "total_pages": len(pdf_reader.pages),
                                "type": "pdf"
                            },
                            source=source
                        )
                        documents.append(doc)
            
            return documents
        except ImportError:
            raise ImportError("Please install PyPDF2: pip install PyPDF2")
        except Exception as e:
            raise Exception(f"Failed to load PDF {source}: {e}")


class ExcelLoader(BaseDataLoader):
    """Excel/CSV document loader."""
    
    def supports(self, source: str) -> bool:
        return source.lower().endswith(tuple(self.config.get("supported_extensions", [".xlsx", ".xls", ".csv"])))
    
    def load(self, source: str) -> List[Document]:
        """Load Excel/CSV document."""
        try:
            import pandas as pd
            documents = []
            
            if source.lower().endswith('.csv'):
                df = pd.read_csv(source)
                sheet_name = "csv"
            else:
                excel_file = pd.ExcelFile(source)
                sheet_name = self.config.get("sheet_name")
                
                if sheet_name:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheets = [sheet_name]
                else:
                    sheets = excel_file.sheet_names
                    dfs = {sheet: pd.read_excel(excel_file, sheet_name=sheet) for sheet in sheets}
            
            # Handle single sheet
            if source.lower().endswith('.csv') or sheet_name:
                content = df.to_string(index=False)
                doc = Document(
                    content=content,
                    metadata={
                        "source": source,
                        "sheet": sheet_name,
                        "rows": len(df),
                        "columns": list(df.columns),
                        "type": "excel"
                    },
                    source=source
                )
                documents.append(doc)
            else:
                # Handle multiple sheets
                for sheet, df in dfs.items():
                    content = df.to_string(index=False)
                    doc = Document(
                        content=content,
                        metadata={
                            "source": source,
                            "sheet": sheet,
                            "rows": len(df),
                            "columns": list(df.columns),
                            "type": "excel"
                        },
                        source=source
                    )
                    documents.append(doc)
            
            return documents
        except ImportError:
            raise ImportError("Please install pandas and openpyxl: pip install pandas openpyxl")
        except Exception as e:
            raise Exception(f"Failed to load Excel {source}: {e}")


class TextLoader(BaseDataLoader):
    """Text/Markdown document loader."""
    
    def supports(self, source: str) -> bool:
        return source.lower().endswith(tuple(self.config.get("supported_extensions", [".txt", ".md"])))
    
    def load(self, source: str) -> List[Document]:
        """Load text document."""
        try:
            with open(source, 'r', encoding='utf-8') as file:
                content = file.read()
            
            doc = Document(
                content=content,
                metadata={
                    "source": source,
                    "type": "text",
                    "encoding": "utf-8"
                },
                source=source
            )
            return [doc]
        except Exception as e:
            raise Exception(f"Failed to load text file {source}: {e}")


class SQLiteLoader(BaseDataLoader):
    """SQLite database loader."""
    
    def supports(self, source: str) -> bool:
        return source.lower().endswith('.db') or source.lower().endswith('.sqlite')
    
    def load(self, source: str, query: Optional[str] = None, table: Optional[str] = None) -> List[Document]:
        """Load data from SQLite database."""
        try:
            import sqlite3
            import pandas as pd
            
            documents = []
            conn = sqlite3.connect(source)
            
            if query:
                # Execute custom query
                df = pd.read_sql_query(query, conn)
                content = df.to_string(index=False)
                doc = Document(
                    content=content,
                    metadata={
                        "source": source,
                        "query": query,
                        "rows": len(df),
                        "type": "sqlite"
                    },
                    source=source
                )
                documents.append(doc)
            elif table:
                # Load specific table
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                content = df.to_string(index=False)
                doc = Document(
                    content=content,
                    metadata={
                        "source": source,
                        "table": table,
                        "rows": len(df),
                        "type": "sqlite"
                    },
                    source=source
                )
                documents.append(doc)
            else:
                # Load all tables
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table_name in tables:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    content = df.to_string(index=False)
                    doc = Document(
                        content=content,
                        metadata={
                            "source": source,
                            "table": table_name,
                            "rows": len(df),
                            "type": "sqlite"
                        },
                        source=source
                    )
                    documents.append(doc)
            
            conn.close()
            return documents
        except ImportError:
            raise ImportError("Please install pandas: pip install pandas")
        except Exception as e:
            raise Exception(f"Failed to load SQLite {source}: {e}")


class JSONLoader(BaseDataLoader):
    """JSON document loader."""
    
    def supports(self, source: str) -> bool:
        return source.lower().endswith('.json')
    
    def load(self, source: str) -> List[Document]:
        """Load JSON document."""
        try:
            import json
            
            with open(source, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Convert to readable string
            content = json.dumps(data, indent=2)
            
            doc = Document(
                content=content,
                metadata={
                    "source": source,
                    "type": "json"
                },
                source=source
            )
            return [doc]
        except Exception as e:
            raise Exception(f"Failed to load JSON {source}: {e}")


class IncidentKnowledgeLoader:
    """Specialized loader for incident knowledge SQLite tables with auto-classification."""
    
    def __init__(self, classifier=None):
        """Initialize with optional classifier."""
        from src.utils.incident_classifier import IncidentClassifier
        self.classifier = classifier or IncidentClassifier()
    
    def load_incidents(
        self,
        db_path: str,
        table_name: str = "incident_knowledge",
        limit: Optional[int] = None
    ) -> List[Document]:
        """
        Load incidents from SQLite table with auto-classification.
        
        Expected columns:
            - platform: str
            - incident_description: str
            - incident_severity: str
            - resource_type: str
            - l1_triage: str
            - l2_triage: str
            - final_resolution: str
            - impacted_dollar: float
        
        Returns:
            List of Document objects with auto-assigned RBAC and metadata
        """
        try:
            # Import here to avoid circular dependency
            from src.storage.sqlite_storage import RAGDatabase
            
            documents = []
            
            # Use RAGDatabase to access unified database
            db = RAGDatabase(db_path)
            incidents = db.get_all_incidents(limit)
            db.close()
            
            for idx, incident in enumerate(incidents):
                # Classify incident
                classification_result = self.classifier.classify_incident(incident)
                
                # Build document content
                content = self._format_incident_content(incident)
                
                # Create document with enriched metadata
                metadata = {
                    "source": f"{db_path}::incident_knowledge",
                    "table": table_name,
                    "row_id": incident.get("id", idx),
                    "type": "incident_knowledge",
                    "classification": classification_result["classification"],
                    "min_access_level": classification_result["min_access_level"],
                    "confidence_score": classification_result["confidence_score"],
                    "reasoning": classification_result["reasoning"],
                }
                
                # Merge with auto-generated tags
                metadata.update(classification_result["metadata_tags"])
                
                # Add original incident fields
                metadata["incident_data"] = incident
                
                doc = Document(
                    content=content,
                    metadata=metadata,
                    source=f"{db_path}::incident_knowledge::row_{incident.get('id', idx)}"
                )
                
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to load incidents from {db_path}: {e}")
    
    def _format_incident_content(self, incident: Dict[str, Any]) -> str:
        """Format incident as readable text for embedding."""
        lines = [
            f"INCIDENT REPORT",
            f"Platform: {incident.get('platform', 'N/A')}",
            f"Severity: {incident.get('incident_severity', 'N/A')}",
            f"Resource: {incident.get('resource_type', 'N/A')}",
            f"",
            f"Description:",
            f"{incident.get('incident_description', 'N/A')}",
            f"",
            f"L1 Triage:",
            f"{incident.get('l1_triage', 'N/A')}",
        ]
        
        if incident.get('l2_triage'):
            lines.extend([
                f"",
                f"L2 Triage:",
                f"{incident.get('l2_triage')}"
            ])
        
        if incident.get('final_resolution'):
            lines.extend([
                f"",
                f"Final Resolution:",
                f"{incident.get('final_resolution')}"
            ])
        
        if incident.get('impacted_dollar'):
            lines.extend([
                f"",
                f"Financial Impact: ${incident.get('impacted_dollar'):,.2f}"
            ])
        
        return "\n".join(lines)


class DataSourceManager:
    """Manages data sources and provides unified loading interface."""
    
    def __init__(self, config_path: str = "config/data_sources.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize loaders
        self.loaders: List[BaseDataLoader] = []
        
        ds_config = self.config.get("data_sources", {})
        
        if ds_config.get("pdf", {}).get("enabled", False):
            self.loaders.append(PDFLoader(ds_config["pdf"]))
        
        if ds_config.get("excel", {}).get("enabled", False):
            self.loaders.append(ExcelLoader(ds_config["excel"]))
        
        if ds_config.get("text", {}).get("enabled", False):
            self.loaders.append(TextLoader(ds_config["text"]))
        
        if ds_config.get("sqlite", {}).get("enabled", False):
            self.loaders.append(SQLiteLoader(ds_config["sqlite"]))
        
        if ds_config.get("json", {}).get("enabled", False):
            self.loaders.append(JSONLoader(ds_config["json"]))
        
        # Initialize incident knowledge loader
        self.incident_loader = IncidentKnowledgeLoader()
    
    def load_document(self, source: str, **kwargs) -> List[Document]:
        """Load document from any supported source."""
        for loader in self.loaders:
            if loader.supports(source):
                return loader.load(source, **kwargs)
        
        raise ValueError(f"No loader found for source: {source}")
    
    def load_documents(self, sources: List[str]) -> List[Document]:
        """Load multiple documents."""
        all_documents = []
        for source in sources:
            documents = self.load_document(source)
            all_documents.extend(documents)
        return all_documents
    
    def load_incident_knowledge(
        self,
        db_path: str,
        table_name: str = "incident_knowledge",
        limit: Optional[int] = None
    ) -> List[Document]:
        """Load incidents from knowledge base with auto-classification."""
        return self.incident_loader.load_incidents(db_path, table_name, limit)
    
    def get_vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration."""
        return self.config.get("vector_store", {})
    
    def get_graph_store_config(self) -> Dict[str, Any]:
        """Get graph store configuration."""
        return self.config.get("graph_store", {})
