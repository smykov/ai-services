from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ai-services"
    minio_secure: bool = False

    database_url: str | None = None

    api_keys: set[str] = set()
    mcp_bearer_token: str | None = None

    task_timeout: int = 120
    task_result_ttl: int = 3600

    mcp_server_name: str = "ecosystem-ai-services"
    mcp_server_version: str = "0.1.0"

    max_upload_size_mb: int = 100

    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:7b"
    default_nlp_system_prompt: str = (
        "You are a helpful AI assistant. "
        "When asked to analyze or process a request, respond in JSON "
        "with intent, entities, and classification fields."
    )

    model_config = SettingsConfigDict(env_prefix="AI_")


settings = Settings()
