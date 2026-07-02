import clickhouse_connect

from app.core.config import AppConfig


class ClickHouseClient:
    def __init__(self, settings: AppConfig) -> None:
        self._settings = settings
        self._client = None

    def get(self):
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=self._settings.clickhouse_host,
                port=self._settings.clickhouse_port,
                username=self._settings.clickhouse_user,
                password=self._settings.clickhouse_password,
                database=self._settings.clickhouse_db
            )

        return self._client