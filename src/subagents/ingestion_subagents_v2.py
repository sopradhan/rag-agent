"""
Ingestion Subagents using LangChain DeepAgents
Handles document chunking, metadata extraction, RBAC, and embedding.
"""

from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain.agents.middleware import AgentMiddleware
from langgraph.prebuilt import ToolNode
from ..abstraction import Document, LLMManager, RBACManager


# ============================================================================
# Chunking Tools
# ============================================================================

@tool
def chunk_document(document_content: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Chunk a document into smaller pieces using recursive character splitting.
    
    Args:
        document_content: The full document content
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of document chunks
    """
    chunks = []
    start = 0
    text_len = len(document_content)
    
    while start < text_len:
        end = start + chunk_size
        chunk = document_content[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
    
    return chunks


# ============================================================================
# Metadata Extraction Tools
# ============================================================================

@tool
def extract_keywords(text: str, llm_manager: LLMManager) -> List[str]:
    """
    Extract keywords from text using LLM.
    
    Args:
        text: Text to extract keywords from
        llm_manager: LLM manager instance
    
    Returns:
        List of keywords
    """
    if len(text) > 500:
        text = text[:500]
    
    prompt = f"""Extract 5-10 important keywords from the following text.
Return only the keywords as a comma-separated list.

Text: {text}

Keywords:"""
    
    try:
        response = llm_manager.invoke(prompt)
        keywords = [k.strip() for k in response.split(",")]
        return keywords[:10]
    except Exception as e:
        print(f"Keyword extraction failed: {e}")
        # Fallback to simple word frequency
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:
                word_freq[word] = word_freq.get(word, 0) + 1
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:10]


@tool
def summarize_text(text: str, llm_manager: LLMManager) -> str:
    """
    Generate a summary of text using LLM.
    
    Args:
        text: Text to summarize
        llm_manager: LLM manager instance
    
    Returns:
        Summary string
    """
    if len(text) > 1000:
        text = text[:1000]
    
    prompt = f"""Provide a brief one-sentence summary of the following text.

Text: {text}

Summary:"""
    
    try:
        return llm_manager.invoke(prompt)
    except Exception as e:
        print(f"Summary extraction failed: {e}")
        return text[:200] + "..."


# ============================================================================
# RBAC Classification Tool
# ============================================================================

@tool
def classify_document_rbac(content: str, rbac_manager: RBACManager) -> Dict[str, Any]:
    """
    Classify document for RBAC access control.
    
    Args:
        content: Document content
        rbac_manager: RBAC manager instance
    
    Returns:
        Classification metadata
    """
    doc_access = rbac_manager.classify_document(content)
    
    return {
        "classification": doc_access.classification,
        "min_access_level": doc_access.min_access_level,
        "required_permissions": list(doc_access.required_permissions)
    }


# ============================================================================
# Embedding Generation Tool
# ============================================================================

@tool
def generate_embedding(text: str, llm_manager: LLMManager) -> List[float]:
    """
    Generate embeddings for text.
    
    Args:
        text: Text to embed
        llm_manager: LLM manager instance
    
    Returns:
        Embedding vector
    """
    try:
        return llm_manager.embed_text(text)
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return []


# ============================================================================
# Ingestion Middleware
# ============================================================================

class IngestionMiddleware(AgentMiddleware):
    """Middleware that provides ingestion tools to DeepAgent."""
    
    def __init__(self, llm_manager: LLMManager, rbac_manager: RBACManager):
        super().__init__()
        self.llm_manager = llm_manager
        self.rbac_manager = rbac_manager
        
        # Define tools with bound dependencies
        self.tools = [
            chunk_document,
            lambda text: extract_keywords(text, self.llm_manager),
            lambda text: summarize_text(text, self.llm_manager),
            lambda content: classify_document_rbac(content, self.rbac_manager),
            lambda text: generate_embedding(text, self.llm_manager)
        ]


# ============================================================================
# Ingestion Subagent Configuration
# ============================================================================

CHUNKER_SUBAGENT = {
    "name": "chunker",
    "description": "Splits documents into smaller chunks for processing",
    "system_prompt": """You are a document chunking specialist. 
    Use the chunk_document tool to split documents into appropriate chunks.
    Consider document structure and maintain context.""",
    "tools": [chunk_document]
}

METADATA_SUBAGENT = {
    "name": "metadata-extractor",
    "description": "Extracts keywords and summaries from document chunks",
    "system_prompt": """You are a metadata extraction specialist.
    Extract meaningful keywords and generate concise summaries for documents.""",
    "tools": []  # Tools will be added with LLM manager dependency
}

RBAC_SUBAGENT = {
    "name": "rbac-classifier",
    "description": "Classifies documents for access control",
    "system_prompt": """You are an access control specialist.
    Classify documents based on their content to determine appropriate access levels.""",
    "tools": []  # Tools will be added with RBAC manager dependency
}

EMBEDDING_SUBAGENT = {
    "name": "embedder",
    "description": "Generates vector embeddings for documents",
    "system_prompt": """You are an embedding generation specialist.
    Generate high-quality vector embeddings for document chunks.""",
    "tools": []  # Tools will be added with LLM manager dependency
}
