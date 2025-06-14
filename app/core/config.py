from pydantic_settings import BaseSettings, SettingsConfigDict, EnvSettingsSource
from typing import Literal

class Settings(BaseSettings):
    mysql_user: str
    mysql_password: str
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_db: str

    ollama_model: str = "mistral"
    hf_embedding_model: str = "sentence-transformers/all-mpnet-base-v2"
    
    use_vertex: bool = False

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