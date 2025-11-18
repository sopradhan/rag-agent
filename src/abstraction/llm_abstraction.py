"""
LLM Abstraction Layer
Provides a unified interface for multiple LLM providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import yaml


class BaseLLM(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        pass


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=os.getenv(config.get("api_key_env", "OPENAI_API_KEY"))
            )
            self.model = config.get("model", "gpt-4")
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {e}")
    
    def embed(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI embedding failed: {e}")


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import anthropic
            self.client = anthropic.Anthropic(
                api_key=os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
            )
            self.model = config.get("model", "claude-3-sonnet-20240229")
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic generation failed: {e}")
    
    def embed(self, text: str) -> List[float]:
        """Anthropic doesn't provide embeddings, fallback to sentence-transformers."""
        raise NotImplementedError("Use OpenAI or sentence-transformers for embeddings")


class OllamaLLM(BaseLLM):
    """Ollama local LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            import requests
            self.base_url = config.get("base_url", "http://localhost:11434")
            self.model = config.get("model", "llama2")
            self.session = requests.Session()
        except ImportError:
            raise ImportError("Please install requests: pip install requests")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using Ollama API."""
        try:
            import requests
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": kwargs.get("temperature", self.temperature),
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise Exception(f"Ollama generation failed: {e}")
    
    def embed(self, text: str) -> List[float]:
        """Generate embeddings using Ollama API."""
        try:
            import requests
            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            raise Exception(f"Ollama embedding failed: {e}")


class HuggingFaceLLM(BaseLLM):
    """HuggingFace LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(
                token=os.getenv(config.get("api_key_env", "HUGGINGFACE_API_TOKEN"))
            )
            self.model = config.get("model", "google/flan-t5-large")
        except ImportError:
            raise ImportError("Please install huggingface-hub: pip install huggingface-hub")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using HuggingFace API."""
        try:
            response = self.client.text_generation(
                prompt,
                model=self.model,
                max_new_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            return response
        except Exception as e:
            raise Exception(f"HuggingFace generation failed: {e}")
    
    def embed(self, text: str) -> List[float]:
        """Generate embeddings using HuggingFace feature extraction."""
        try:
            response = self.client.feature_extraction(text)
            return response[0] if isinstance(response, list) else response
        except Exception as e:
            raise Exception(f"HuggingFace embedding failed: {e}")


class SentenceTransformersEmbedding:
    """Local embedding using sentence-transformers."""
    
    def __init__(self, config: Dict[str, Any]):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(
                config.get("model", "all-MiniLM-L6-v2")
            )
        except ImportError:
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")
    
    def embed(self, text: str) -> List[float]:
        """Generate embeddings using sentence-transformers."""
        return self.model.encode(text).tolist()


class LLMFactory:
    """Factory for creating LLM instances."""
    
    _providers = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "ollama": OllamaLLM,
        "huggingface": HuggingFaceLLM,
    }
    
    _embedding_providers = {
        "openai": OpenAILLM,
        "sentence_transformers": SentenceTransformersEmbedding,
        "ollama": OllamaLLM,
        "huggingface": HuggingFaceLLM,
    }
    
    @classmethod
    def create_llm(cls, provider: str, config: Dict[str, Any]) -> BaseLLM:
        """Create an LLM instance based on provider type."""
        if provider not in cls._providers:
            raise ValueError(f"Unknown LLM provider: {provider}")
        return cls._providers[provider](config)
    
    @classmethod
    def create_embedding(cls, provider: str, config: Dict[str, Any]):
        """Create an embedding instance based on provider type."""
        if provider not in cls._embedding_providers:
            raise ValueError(f"Unknown embedding provider: {provider}")
        return cls._embedding_providers[provider](config)


class LLMManager:
    """Manages LLM configuration and provides unified access."""
    
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.default_provider = self.config.get("default_provider", "openai")
        self.default_embedding_provider = self.config.get("default_embedding_provider", "openai")
        
        self._llm_cache = {}
        self._embedding_cache = {}
    
    def get_llm(self, provider: Optional[str] = None) -> BaseLLM:
        """Get LLM instance for specified provider."""
        provider = provider or self.default_provider
        
        if provider not in self._llm_cache:
            provider_config = self.config["llm_providers"].get(provider)
            if not provider_config or not provider_config.get("enabled", False):
                raise ValueError(f"Provider {provider} is not enabled")
            
            self._llm_cache[provider] = LLMFactory.create_llm(
                provider_config["type"], provider_config
            )
        
        return self._llm_cache[provider]
    
    def get_embedding(self, provider: Optional[str] = None):
        """Get embedding instance for specified provider."""
        provider = provider or self.default_embedding_provider
        
        if provider not in self._embedding_cache:
            provider_config = self.config["embedding_providers"].get(provider)
            if not provider_config or not provider_config.get("enabled", False):
                raise ValueError(f"Embedding provider {provider} is not enabled")
            
            self._embedding_cache[provider] = LLMFactory.create_embedding(
                provider_config["type"], provider_config
            )
        
        return self._embedding_cache[provider]
    
    def generate(self, prompt: str, provider: Optional[str] = None, **kwargs) -> str:
        """Generate text using specified or default LLM."""
        llm = self.get_llm(provider)
        return llm.generate(prompt, **kwargs)
    
    def embed(self, text: str, provider: Optional[str] = None) -> List[float]:
        """Generate embeddings using specified or default provider."""
        embedding = self.get_embedding(provider)
        return embedding.embed(text)
