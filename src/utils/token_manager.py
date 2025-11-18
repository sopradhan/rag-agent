"""
Token Manager with Tiktoken
Handles token counting, caching, and token-aware chunking
"""

import tiktoken
from typing import List, Dict, Any, Optional
from pathlib import Path
import os


class TokenManager:
    """Manages token counting and caching using tiktoken."""
    
    # Token limits for common models
    TOKEN_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "claude-2": 100000,
        "claude-instant": 100000,
        "llama2": 4096,
        "mistral": 8192,
    }
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        cache_dir: str = "data/tiktoken_cache"
    ):
        """
        Initialize TokenManager.
        
        Args:
            model: Model name for token encoding
            cache_dir: Directory for tiktoken cache
        """
        self.model = model
        self.cache_dir = cache_dir
        
        # Set tiktoken cache directory
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["TIKTOKEN_CACHE_DIR"] = cache_dir
        
        # Get encoding for the model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.token_limit = self.TOKEN_LIMITS.get(model, 4096)
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens
        
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        Count tokens for multiple texts.
        
        Args:
            texts: List of texts
        
        Returns:
            List of token counts
        """
        return [self.count_tokens(text) for text in texts]
    
    def chunk_by_tokens(
        self,
        text: str,
        max_tokens: int = 512,
        overlap_tokens: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Chunk text by token count with overlap.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks
        
        Returns:
            List of chunk dictionaries with text, token_count, chunk_id
        """
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        if total_tokens <= max_tokens:
            return [{
                "text": text,
                "token_count": total_tokens,
                "chunk_id": 0,
                "total_chunks": 1,
                "start_token": 0,
                "end_token": total_tokens
            }]
        
        chunks = []
        chunk_id = 0
        start = 0
        
        while start < total_tokens:
            # Get chunk tokens
            end = min(start + max_tokens, total_tokens)
            chunk_tokens = tokens[start:end]
            
            # Decode chunk
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append({
                "text": chunk_text,
                "token_count": len(chunk_tokens),
                "chunk_id": chunk_id,
                "total_chunks": 0,  # Will be updated after loop
                "start_token": start,
                "end_token": end
            })
            
            chunk_id += 1
            start = end - overlap_tokens if end < total_tokens else end
        
        # Update total_chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks
        
        return chunks
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = None
    ) -> Dict[str, float]:
        """
        Estimate cost for token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name (uses self.model if None)
        
        Returns:
            Dictionary with cost breakdown
        """
        model = model or self.model
        
        # Pricing per 1K tokens (as of 2024)
        PRICING = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
            "claude-2": {"prompt": 0.008, "completion": 0.024},
            "claude-instant": {"prompt": 0.0008, "completion": 0.0024},
        }
        
        pricing = PRICING.get(model, {"prompt": 0.001, "completion": 0.002})
        
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_cost": round(prompt_cost, 6),
            "completion_cost": round(completion_cost, 6),
            "total_cost": round(total_cost, 6),
            "currency": "USD"
        }
    
    def fits_in_context(
        self,
        texts: List[str],
        reserve_tokens: int = 1000
    ) -> bool:
        """
        Check if texts fit within model's context window.
        
        Args:
            texts: List of texts to check
            reserve_tokens: Reserve tokens for completion
        
        Returns:
            True if fits, False otherwise
        """
        total_tokens = sum(self.count_tokens(text) for text in texts)
        return total_tokens + reserve_tokens <= self.token_limit
    
    def truncate_to_limit(
        self,
        text: str,
        max_tokens: int = None,
        from_end: bool = False
    ) -> str:
        """
        Truncate text to fit token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens (uses model limit if None)
            from_end: If True, truncate from end; otherwise from start
        
        Returns:
            Truncated text
        """
        max_tokens = max_tokens or self.token_limit
        tokens = self.encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        if from_end:
            truncated_tokens = tokens[:max_tokens]
        else:
            truncated_tokens = tokens[-max_tokens:]
        
        return self.encoding.decode(truncated_tokens)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token manager statistics."""
        return {
            "model": self.model,
            "encoding": self.encoding.name,
            "token_limit": self.token_limit,
            "cache_dir": self.cache_dir,
            "cache_exists": os.path.exists(self.cache_dir)
        }


class TokenAwareChunker:
    """
    Token-aware document chunker for RAG systems.
    Combines token counting with semantic boundaries.
    """
    
    def __init__(
        self,
        token_manager: TokenManager,
        chunk_size: int = 512,
        overlap: int = 50,
        respect_boundaries: bool = True
    ):
        """
        Initialize TokenAwareChunker.
        
        Args:
            token_manager: TokenManager instance
            chunk_size: Target chunk size in tokens
            overlap: Overlap size in tokens
            respect_boundaries: Try to split at sentence boundaries
        """
        self.token_manager = token_manager
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_boundaries = respect_boundaries
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document with token awareness.
        
        Args:
            text: Document text
            metadata: Document metadata
        
        Returns:
            List of chunks with metadata
        """
        if self.respect_boundaries:
            # Split into sentences first
            sentences = self._split_sentences(text)
            chunks = self._chunk_sentences(sentences)
        else:
            # Simple token-based chunking
            chunks = self.token_manager.chunk_by_tokens(
                text,
                max_tokens=self.chunk_size,
                overlap_tokens=self.overlap
            )
        
        # Add metadata to chunks
        if metadata:
            for chunk in chunks:
                chunk["metadata"] = metadata.copy()
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences (simple implementation)."""
        import re
        # Split on period, exclamation, question mark followed by space
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _chunk_sentences(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """Chunk sentences while respecting token limits."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_id = 0
        
        for sentence in sentences:
            sentence_tokens = self.token_manager.count_tokens(sentence)
            
            # If single sentence exceeds limit, split it
            if sentence_tokens > self.chunk_size:
                if current_chunk:
                    # Save current chunk
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "token_count": current_tokens,
                        "chunk_id": chunk_id,
                        "total_chunks": 0
                    })
                    chunk_id += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by tokens
                long_chunks = self.token_manager.chunk_by_tokens(
                    sentence,
                    max_tokens=self.chunk_size,
                    overlap_tokens=self.overlap
                )
                for lc in long_chunks:
                    lc["chunk_id"] = chunk_id
                    chunks.append(lc)
                    chunk_id += 1
                
                continue
            
            # Check if adding sentence exceeds limit
            if current_tokens + sentence_tokens > self.chunk_size:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "token_count": current_tokens,
                    "chunk_id": chunk_id,
                    "total_chunks": 0
                })
                chunk_id += 1
                
                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    # Keep last few sentences for overlap
                    overlap_text = []
                    overlap_tokens = 0
                    for s in reversed(current_chunk):
                        s_tokens = self.token_manager.count_tokens(s)
                        if overlap_tokens + s_tokens <= self.overlap:
                            overlap_text.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break
                    current_chunk = overlap_text
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "token_count": current_tokens,
                "chunk_id": chunk_id,
                "total_chunks": 0
            })
        
        # Update total_chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks
        
        return chunks
