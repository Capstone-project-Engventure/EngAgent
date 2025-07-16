from pydantic_settings import BaseSettings, SettingsConfigDict, EnvSettingsSource
from typing import Literal

class Settings(BaseSettings):
    mysql_user: str 
    mysql_password: str
    mysql_host: str 
    mysql_port: int
    mysql_db: str

    # Ollama Configuration with smaller default model
    ollama_model: str = "llama3.2:1b"  # Changed from mistral to smaller model
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: int = 120
    
    # Alternative model options for different memory requirements
    ollama_small_model: str = "llama3.2:1b"  # ~1.3GB
    ollama_medium_model: str = "llama3.2:3b"  # ~2.0GB
    ollama_large_model: str = "mistral"  # ~4.8GB
    
    # DeepSeek Configuration
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    
    hf_embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    
    use_vertex: bool = True
    use_deepseek: bool = False

    # if you insist on separate naming
    vertex_project: str | None = None
    vertex_location: Literal[
        "asia-southeast1","asia-southeast2","asia-east2","asia-northeast1","us-central1"
    ] | None = None
    vertex_llm_model: str | None = None
    vertex_embedding_model: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()