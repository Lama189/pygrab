from typing import Any
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    clickhouse_db: str = ""
    clickhouse_user: str = ""
    clickhouse_password: str = ""
    clickhouse_host: str = ""
    clickhouse_port: int = 8123

    batch_size: int = 1000
    flush_interval_secs: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DockerConfig(BaseSettings):
    docker_enabled: bool = True
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_containers: list[str] | None = None

    @field_validator("docker_containers", mode="before")
    @classmethod
    def parse_containers_list(cls, v: Any):
        if isinstance(v, str) and v.strip():
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig()


@lru_cache
def get_docker_config() -> DockerConfig:
    return DockerConfig()