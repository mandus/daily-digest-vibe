"""
Configuration management for Daily Digest Vibe.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import yaml


class AIConfig(BaseModel):
    """AI-related configuration."""
    embedding_model: str = "text-embedding-ada-002"
    cluster_algorithm: str = "kmeans"
    num_clusters: int = 10
    use_local_embeddings: bool = False
    
    # For local embeddings
    local_model_path: Optional[str] = None


class StorageConfig(BaseModel):
    """Storage configuration."""
    type: str = "sqlite"  # sqlite or json
    path: str = "data/stories.db"
    
    # For JSON storage
    stories_file: str = "data/stories.json"
    preferences_file: str = "data/preferences.json"


class ScheduleConfig(BaseModel):
    """Scheduling configuration."""
    fetch_interval: int = 3600  # seconds between fetches
    digest_time: str = "08:00"  # time to generate daily digest
    auto_fetch: bool = False


class Config(BaseModel):
    """Main configuration class."""
    
    # General settings
    top_n: int = 500
    api_base: str = "https://hacker-news.firebaseio.com/v0"
    
    # Storage
    storage: StorageConfig = Field(default_factory=StorageConfig)
    
    # AI
    ai: AIConfig = Field(default_factory=AIConfig)
    
    # Schedule
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    
    # Directories
    data_dir: Path = Path("data")
    
    # API keys (loaded from environment)
    openai_api_key: Optional[str] = None
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from file or use defaults."""
        # Default config path
        if config_path is None:
            config_path = "config.yaml"
        
        config = cls()
        
        # Load from file if exists
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    config = cls(**config_data)
        
        # Load API keys from environment
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Ensure data directory exists
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        return config
    
    def save(self, config_path: str = "config.yaml") -> None:
        """Save configuration to file."""
        config_data = self.model_dump(exclude={"openai_api_key"})
        
        # Convert Path objects to strings for YAML serialization
        if 'data_dir' in config_data:
            config_data['data_dir'] = str(config_data['data_dir'])
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    def get_storage_path(self) -> Path:
        """Get the storage path based on configuration."""
        if self.storage.type == "sqlite":
            return Path(self.storage.path)
        else:
            return Path(self.storage.stories_file)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None
