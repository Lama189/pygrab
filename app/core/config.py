from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings): 
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


@lru_cache
def get_settings() -> Settings:
    return Settings()