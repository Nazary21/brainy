"""
Configuration settings for the Brainy application.
"""
from typing import Optional, Dict, Any
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    # API Keys
    TELEGRAM_BOT_TOKEN: str = Field("", description="Telegram Bot API token")
    OPENAI_API_KEY: str = Field("", description="OpenAI API key")
    GROK_API_KEY: str = Field("", description="Grok API key")
    
    # AI Provider settings
    DEFAULT_AI_PROVIDER: str = Field("openai", description="Default AI provider to use")
    OPENAI_MODEL: str = Field("gpt-3.5-turbo", description="Default OpenAI model to use")
    OPENAI_TEMPERATURE: float = Field(0.7, description="Temperature for OpenAI API calls")
    OPENAI_MAX_TOKENS: int = Field(1000, description="Max tokens for OpenAI API calls")
    GROK_MODEL: str = Field("grok-1", description="Default Grok model to use")
    GROK_TEMPERATURE: float = Field(0.7, description="Temperature for Grok API calls")
    GROK_MAX_TOKENS: int = Field(1000, description="Max tokens for Grok API calls")
    
    # Database
    DATABASE_URL: Optional[str] = Field(
        None, description="Database connection string"
    )
    
    # Vector DB
    VECTOR_DB_PATH: str = Field(
        "./data/vectordb", description="Path to vector database storage"
    )
    
    # Memory settings
    USE_CONTEXT_SEARCH: bool = Field(True, description="Enable vector search for context retrieval")
    MAX_CONTEXT_MESSAGES: int = Field(10, description="Maximum number of messages to include in context")
    MAX_SIMILAR_MESSAGES: int = Field(3, description="Maximum number of similar messages to retrieve")
    MAX_CONTEXT_LENGTH: int = Field(10, description="Maximum length of context in messages")
    
    # Logging
    LOG_LEVEL: str = Field(
        "INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # Application settings
    DEBUG: bool = Field(False, description="Debug mode")
    
    # Railway
    RAILWAY_PROJECT_ID: Optional[str] = Field(
        None, description="Railway project ID for deployment"
    )
    
    # Character settings
    DEFAULT_CHARACTER_ID: str = Field(
        "default", description="Default character ID to use"
    )
    
    # Embedding settings
    EMBEDDING_MODEL: str = Field(
        "all-MiniLM-L6-v2", description="SentenceTransformer model to use for embeddings"
    )
    EMBEDDING_DIMENSIONS: int = Field(
        384, description="Dimensionality of the embeddings"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @model_validator(mode='after')
    def validate_debug(self):
        """Validate and convert DEBUG field if needed."""
        # If DEBUG is a string (from .env file), convert it to bool
        if isinstance(self.DEBUG, str):
            self.DEBUG = self.DEBUG.lower() in ('true', 'yes', '1', 't', 'y')
        return self
    
    def get_ai_provider_config(self, provider_type: str = None) -> Dict[str, Any]:
        """
        Get the configuration for an AI provider.
        
        Args:
            provider_type: Type of provider to get config for.
                If not provided, the default provider will be used.
                
        Returns:
            Dictionary of configuration values for the provider
        """
        if provider_type is None:
            provider_type = self.DEFAULT_AI_PROVIDER
        
        if provider_type == "openai":
            return {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "temperature": self.OPENAI_TEMPERATURE,
                "max_tokens": self.OPENAI_MAX_TOKENS
            }
        
        if provider_type == "grok":
            return {
                "api_key": self.GROK_API_KEY,
                "model": self.GROK_MODEL,
                "temperature": self.GROK_TEMPERATURE,
                "max_tokens": self.GROK_MAX_TOKENS
            }
        
        # Add other provider configurations as needed
        
        raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @property
    def debug(self) -> bool:
        """Property for backward compatibility with lowercase debug."""
        return self.DEBUG


# Create global settings instance
settings = Settings() 