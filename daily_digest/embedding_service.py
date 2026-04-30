"""
Embedding service for Daily Digest Vibe.
Provides a unified interface for generating text embeddings using various providers.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import numpy as np
from dataclasses import dataclass, field
from enum import Enum

from .config import get_config


# Configure logging
logger = logging.getLogger(__name__)


class EmbeddingProviderType(Enum):
    """Types of embedding providers."""
    OPENAI = "openai"
    LOCAL = "local"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    MOCK = "mock"


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    embeddings: List[List[float]]
    model: str
    provider: str
    input_texts: List[str]
    success: bool = True
    error_message: Optional[str] = None
    latency_seconds: float = 0.0
    tokens_used: int = 0


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service."""
    provider: EmbeddingProviderType = EmbeddingProviderType.MOCK
    model_name: str = "text-embedding-ada-002"
    api_key: Optional[str] = None
    local_model_path: Optional[str] = None
    batch_size: int = 100
    max_retries: int = 3
    rate_limit_delay: float = 0.1  # seconds between batches
    cache_enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: Path("data/embedding_cache"))


class EmbeddingCache:
    """Simple file-based cache for embeddings."""
    
    def __init__(self, cache_dir: Path, enabled: bool = True):
        """Initialize embedding cache."""
        self.cache_dir = cache_dir
        self.enabled = enabled
        self._cache: Dict[str, List[float]] = {}
        
        if enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        import json
        cache_file = self.cache_dir / "embedding_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} embeddings from cache")
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        import json
        cache_file = self.cache_dir / "embedding_cache.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text."""
        if not self.enabled:
            return None
        return self._cache.get(text)
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Cache embedding for text."""
        if not self.enabled:
            return
        self._cache[text] = embedding
        # Periodically save to disk
        if len(self._cache) % 100 == 0:
            self._save_cache()
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        if self.enabled:
            import shutil
            cache_file = self.cache_dir / "embedding_cache.json"
            if cache_file.exists():
                cache_file.unlink()


class BaseEmbeddingProvider:
    """Base class for embedding providers."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize embedding provider."""
        self.config = config
        self.cache = EmbeddingCache(config.cache_dir, config.cache_enabled)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        # Check cache first
        cached = self.cache.get(text)
        if cached is not None:
            return cached
        
        embedding = self._generate_embedding(text)
        self.cache.set(text, embedding)
        return embedding
    
    def batch_embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a batch of texts."""
        start_time = time.time()
        
        # Check cache for each text
        uncached_texts = []
        uncached_indices = []
        cached_embeddings = []
        
        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                cached_embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            new_embeddings = self._batch_generate_embeddings(uncached_texts)
            for idx, embedding in zip(uncached_indices, new_embeddings):
                self.cache.set(texts[idx], embedding)
        
        # Reconstruct the result in original order
        all_embeddings = [None] * len(texts)
        for i, embedding in cached_embeddings:
            all_embeddings[i] = embedding
        for i, embedding in zip(uncached_indices, new_embeddings):
            all_embeddings[i] = embedding
        
        latency = time.time() - start_time
        
        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.config.model_name,
            provider=self.config.provider.value,
            input_texts=texts,
            success=True,
            latency_seconds=latency
        )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text (to be implemented by subclasses)."""
        raise NotImplementedError
    
    def _batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts (to be implemented by subclasses)."""
        return [self._generate_embedding(text) for text in texts]
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.cache.clear()


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize OpenAI embedding provider."""
        super().__init__(config)
        
        if not config.api_key:
            config.api_key = os.getenv("OPENAI_API_KEY")
        
        if not config.api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            import openai
            self.client = openai.Client(api_key=config.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI embeddings")
    
    def _generate_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """Generate embedding using OpenAI API."""
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.config.model_name,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate embedding after {max_retries} attempts: {e}")
                    raise
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Failed to generate embedding")
    
    def _batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self.config.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"Batch embedding failed, falling back to individual requests: {e}")
            return super()._batch_generate_embeddings(texts)


class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using Sentence Transformers."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize Sentence Transformers embedding provider."""
        super().__init__(config)
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers package is required")
        
        # Load model
        model_path = config.local_model_path or config.model_name
        logger.info(f"Loading Sentence Transformers model: {model_path}")
        self.model = SentenceTransformer(model_path)
        logger.info(f"Model loaded successfully")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Sentence Transformers."""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def _batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts using Sentence Transformers."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider for testing and fallback."""
    
    def __init__(self, config: EmbeddingConfig, embedding_size: int = 1536):
        """Initialize mock embedding provider."""
        super().__init__(config)
        self.embedding_size = embedding_size
        self._text_to_hash: Dict[str, int] = {}
    
    def _text_to_hash_value(self, text: str) -> int:
        """Convert text to a consistent hash value."""
        if text not in self._text_to_hash:
            hash_val = 0
            for char in text:
                hash_val = (hash_val * 31 + ord(char)) % (2**32)
            self._text_to_hash[text] = hash_val
        return self._text_to_hash[text]
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding."""
        hash_val = self._text_to_hash_value(text)
        np.random.seed(hash_val)
        return np.random.randn(self.embedding_size).tolist()


class EmbeddingService:
    """Main embedding service that manages providers and caching."""
    
    _instance: Optional['EmbeddingService'] = None
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize embedding service."""
        if config is None:
            config = self._load_config()
        
        self.config = config
        self.provider: Optional[BaseEmbeddingProvider] = None
        self._initialize_provider()
    
    @classmethod
    def get_instance(cls) -> 'EmbeddingService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance."""
        if cls._instance:
            cls._instance.provider.clear_cache()
        cls._instance = None
    
    def _load_config(self) -> EmbeddingConfig:
        """Load configuration from settings."""
        from .config import get_config
        config = get_config()
        
        provider_type = EmbeddingProviderType.MOCK
        if config.ai.use_local_embeddings:
            provider_type = EmbeddingProviderType.SENTENCE_TRANSFORMERS
        elif config.openai_api_key:
            provider_type = EmbeddingProviderType.OPENAI
        
        return EmbeddingConfig(
            provider=provider_type,
            model_name=config.ai.embedding_model,
            api_key=config.openai_api_key,
            local_model_path=config.ai.local_model_path,
            batch_size=100,
            max_retries=3,
            cache_enabled=True,
            cache_dir=Path("data/embedding_cache")
        )
    
    def _initialize_provider(self) -> None:
        """Initialize the appropriate embedding provider."""
        try:
            if self.config.provider == EmbeddingProviderType.OPENAI:
                self.provider = OpenAIEmbeddingProvider(self.config)
                logger.info("Using OpenAI embedding provider")
            elif self.config.provider == EmbeddingProviderType.SENTENCE_TRANSFORMERS:
                self.provider = SentenceTransformersEmbeddingProvider(self.config)
                logger.info("Using Sentence Transformers embedding provider")
            else:
                self.provider = MockEmbeddingProvider(self.config)
                logger.info("Using Mock embedding provider")
        except Exception as e:
            logger.warning(f"Failed to initialize {self.config.provider.value} provider: {e}")
            # Fall back to mock
            self.config.provider = EmbeddingProviderType.MOCK
            self.provider = MockEmbeddingProvider(self.config)
            logger.info("Falling back to Mock embedding provider")
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        return self.provider.embed(text)
    
    def batch_embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a batch of texts."""
        if not self.provider:
            raise RuntimeError("Embedding provider not initialized")
        return self.provider.batch_embed(texts)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider."""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model_name,
            "cache_enabled": self.config.cache_enabled
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        if self.provider:
            self.provider.clear_cache()


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    return EmbeddingService.get_instance()


def create_embedding_service(config: Optional[EmbeddingConfig] = None) -> EmbeddingService:
    """Create a new embedding service instance."""
    return EmbeddingService(config)
