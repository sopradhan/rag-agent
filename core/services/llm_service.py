"""
LLM Service - Multi-provider LLM abstraction
Supports: OpenAI, Anthropic, HuggingFace, Ollama
"""
import os
import json
from typing import List, Dict, Optional, Any
from langchain_core.language_models import BaseChatModel


class LLMService:
    """Unified interface for multiple LLM providers"""
    
    def __init__(self, config: dict):
        """
        Initialize LLM service with configuration
        
        Args:
            config: Dictionary from llm_config.yaml
        """
        self.config = config
        self.provider = config.get('default_provider', 'openai')
        self.providers_config = config.get('llm_providers', {})
        self.embeddings_config = config.get('embedding_providers', {})
        
        self.llm = self._initialize_llm()
        self.embeddings = self._initialize_embeddings()
        
        print(f"[LLMService] Initialized with provider: {self.provider}")
    
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize chat model based on configured provider"""
        provider_config = self.providers_config.get(self.provider, {})
        
        if not provider_config.get('enabled', False):
            # Find first enabled provider
            for name, cfg in self.providers_config.items():
                if cfg.get('enabled', False):
                    self.provider = name
                    provider_config = cfg
                    break
        
        try:
            if self.provider == 'openai':
                return self._create_openai(provider_config)
            elif self.provider == 'anthropic':
                return self._create_anthropic(provider_config)
            elif self.provider == 'huggingface':
                return self._create_huggingface(provider_config)
            elif self.provider == 'ollama':
                return self._create_ollama(provider_config)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize {self.provider}: {e}")
            # Fallback to Ollama
            print("[INFO] Falling back to Ollama")
            return self._create_ollama(self.providers_config.get('ollama', {}))
    
    def _create_openai(self, config: dict) -> BaseChatModel:
        """Create OpenAI chat model"""
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv(config.get('api_key_env', 'OPENAI_API_KEY'))
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        return ChatOpenAI(
            model=config.get('model', 'gpt-4'),
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000),
            api_key=api_key
        )
    
    def _create_anthropic(self, config: dict) -> BaseChatModel:
        """Create Anthropic chat model"""
        from langchain_anthropic import ChatAnthropic
        
        api_key = os.getenv(config.get('api_key_env', 'ANTHROPIC_API_KEY'))
        if not api_key:
            raise ValueError("Anthropic API key not found")
        
        return ChatAnthropic(
            model=config.get('model', 'claude-3-sonnet-20240229'),
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 2000),
            api_key=api_key
        )
    
    def _create_huggingface(self, config: dict) -> BaseChatModel:
        """Create HuggingFace chat model using OpenAI-compatible API"""
        from langchain_openai import ChatOpenAI
        
        # Get API token - check if it's a key or env var name
        api_token = config.get('api_key_env')
        
        # If it starts with 'hf_', it's the actual key
        if api_token and api_token.startswith('hf_'):
            pass  # Use it directly
        elif api_token:
            # It's an env var name
            api_token = os.getenv(api_token)
        
        if not api_token:
            api_token = os.getenv('HUGGINGFACEHUB_API_TOKEN') or os.getenv('HF_TOKEN')
        
        if not api_token:
            raise ValueError("HuggingFace API token not found")
        
        # Use HuggingFace's router endpoint (OpenAI-compatible chat completions API)
        # Use models like: meta-llama/Llama-3.3-70B-Instruct, deepseek-ai/DeepSeek-R1
        return ChatOpenAI(
            model=config.get('model', 'meta-llama/Llama-3.3-70B-Instruct'),
            base_url="https://router.huggingface.co/v1",  # Correct path: /v1 not /v1/
            api_key=api_token,
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 512)
        )
    
    def _create_ollama(self, config: dict) -> BaseChatModel:
        """Create Ollama chat model"""
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=config.get('model', 'gemma3:4b'),
            temperature=config.get('temperature', 0.3),
            base_url=config.get('base_url', 'http://localhost:11434')
        )
    
    def _initialize_embeddings(self):
        """Initialize embedding model"""
        default_provider = self.config.get('default_embedding_provider', 'sentence_transformers')
        embed_config = self.embeddings_config.get(default_provider, {})
        
        try:
            if default_provider == 'openai':
                from langchain_openai import OpenAIEmbeddings
                api_key = os.getenv(embed_config.get('api_key_env', 'OPENAI_API_KEY'))
                return OpenAIEmbeddings(
                    model=embed_config.get('model', 'text-embedding-3-small'),
                    api_key=api_key
                )
            elif default_provider == 'sentence_transformers':
                from langchain_huggingface import HuggingFaceEmbeddings
                return HuggingFaceEmbeddings(
                    model_name=embed_config.get('model', 'all-MiniLM-L6-v2')
                )
            elif default_provider == 'huggingface':
                from langchain_huggingface import HuggingFaceEmbeddings
                return HuggingFaceEmbeddings(
                    model_name=embed_config.get('model', 'sentence-transformers/all-mpnet-base-v2')
                )
        except Exception as e:
            print(f"[ERROR] Failed to initialize embeddings: {e}")
            # Fallback to sentence transformers
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
    
    def get_model(self) -> BaseChatModel:
        """Get the initialized LLM model"""
        return self.llm
    
    def generate_response(self, prompt: str) -> str:
        """
        Generate text response from prompt
        
        Args:
            prompt: Input prompt text
            
        Returns:
            Generated text response
        """
        response = self.llm.invoke(prompt)
        return response.content
    
    def generate_json(self, prompt: str) -> dict:
        """
        Generate structured JSON response
        
        Args:
            prompt: Input prompt (should request JSON output)
            
        Returns:
            Parsed JSON dictionary
        """
        response = self.llm.invoke(prompt)
        content = response.content
        
        # Extract JSON from markdown code blocks if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"Content: {content}")
            return {}
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for list of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        return self.embeddings.embed_documents(texts)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text
        
        Args:
            text: Input text string
            
        Returns:
            Embedding vector
        """
        return self.embeddings.embed_query(text)
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Input text
            
        Returns:
            Approximate token count
        """
        # Simple approximation: ~4 chars per token
        return len(text) // 4
