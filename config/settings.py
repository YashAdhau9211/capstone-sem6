"""Application settings and configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "causal_ai_db"
    postgres_user: str = "causal_user"
    postgres_password: str = "causal_pass"

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # InfluxDB Configuration
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "causal-ai-token-123"
    influxdb_org: str = "causal-ai"
    influxdb_bucket: str = "sensor_data"

    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "causal-ai-consumers"

    # Application Configuration
    app_env: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
