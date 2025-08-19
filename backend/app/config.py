from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = str(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # App
    env: str = "dev"
    log_level: str = "info"
    port: int = 8000
    docs_enabled: bool = True

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_embedding_dim: int = 3072
    openai_temperature: float = 0.1

    # Pinecone
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "construction-rag"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_metric: str = "cosine"
    pinecone_namespace: str = "default"

    # Supabase
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    # Data
    data_dir: str = "data/raw"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

