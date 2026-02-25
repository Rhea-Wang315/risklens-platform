"""Configuration management for RiskLens Platform."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = False

    # Database
    database_url: str = "postgresql://risklens:password@localhost:5432/risklens"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_alerts: str = "risklens.alerts"
    kafka_topic_decisions: str = "risklens.decisions"
    kafka_consumer_group: str = "risklens-platform"

    # Whale-Sentry Integration
    whale_sentry_path: str = "../whale-sentry"
    whale_sentry_data_dir: str = "../whale-sentry/data"

    # Alert Manager
    slack_webhook_url: str | None = None
    pagerduty_api_key: str | None = None
    alert_rate_limit_per_hour: int = 100

    # Rule Engine
    rules_config_path: str = "./configs/rules.yaml"
    risk_score_weights_path: str = "./configs/score_weights.yaml"

    # Monitoring
    prometheus_port: int = 9090
    grafana_port: int = 3000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    api_key_header: str = "X-API-Key"
    admin_api_key: str = "change_me_in_production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
