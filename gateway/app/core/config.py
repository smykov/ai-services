from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ai-services"
    database_url: str | None = None

    api_keys: dict[str, str] = {}

    task_timeout: int = 120
    task_result_ttl: int = 3600

    mcp_server_name: str = "ecosystem-ai-services"
    mcp_server_version: str = "0.1.0"

    model_config = {"env_prefix": "AI_"}


settings = Settings()
