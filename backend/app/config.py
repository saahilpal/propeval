from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PropEval"
    environment: str = "development"
    debug: bool = False

    # Database: Local Postgres 17 on port 5433
    database_url: str = Field(
        default="postgresql+asyncpg://propeval_user:propeval_pass@localhost:5433/propeval"
    )
    database_url_sync: str = Field(
        default="postgresql://propeval_user:propeval_pass@localhost:5433/propeval"
    )
    pg_pool_min_size: int = 2
    pg_pool_max_size: int = 15

    # Security & Tenancy
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    admin_api_key: str = "propeval_admin_secret_key"

    # Queue & Worker
    worker_id: str = "worker-local-01"
    job_lease_sec: int = 60
    job_heartbeat_interval_sec: int = 20
    max_job_wall_sec: int = 300
    max_per_tenant_jobs: int = 20

    # Telemetry
    otlp_endpoint: str = "http://localhost:4318/v1/traces"


settings = Settings()
