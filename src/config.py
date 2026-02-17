"""
FINCENTER Configuration Management

Centralized configuration using Pydantic settings with environment variable support.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")
    
    # Neo4j
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="fincenter2024")
    NEO4J_DATABASE: str = Field(default="neo4j")
    
    # PostgreSQL
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="fincenter")
    POSTGRES_USER: str = Field(default="fincenter")
    POSTGRES_PASSWORD: str = Field(default="fincenter2024")
    DATABASE_URL: str = Field(default="postgresql://fincenter:fincenter2024@localhost:5432/fincenter")
    
    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="fincenter2024")
    REDIS_DB: int = Field(default=0)
    REDIS_URL: str = Field(default="redis://:fincenter2024@localhost:6379/0")
    
    # API
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8080)
    API_RELOAD: bool = Field(default=True)
    CORS_ORIGINS: List[str] = Field(default=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
    ])
    
    # Vector Store
    VECTOR_STORE_TYPE: str = Field(default="faiss")
    VECTOR_STORE_PATH: str = Field(default="./data/vectors/")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-mpnet-base-v2")
    EMBEDDING_DIMENSION: int = Field(default=768)
    
    # NLP
    SPACY_MODEL: str = Field(default="fr_core_news_lg")
    NER_MODEL_PATH: str = Field(default="./models/financial_ner_v1.pkl")
    
    # Data Processing
    BATCH_SIZE: int = Field(default=50)
    MAX_WORKERS: int = Field(default=4)
    CHUNK_SIZE: int = Field(default=1000)
    
    # Simulation
    MONTE_CARLO_ITERATIONS: int = Field(default=10000)
    SIMULATION_CONFIDENCE_LEVEL: float = Field(default=0.95)
    
    # Cache
    CACHE_TTL_SECONDS: int = Field(default=300)
    CACHE_ENABLED: bool = Field(default=True)
    
    # Groq LLM
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_MAX_TOKENS: int = Field(default=4096)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
