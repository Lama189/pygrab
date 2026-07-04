import clickhouse_connect

from app.core.config import AppConfig


class ClickHouseClientFactory:
    def __init__(self, settings: AppConfig):
        self._settings = settings

    def create_raw(self):
        return clickhouse_connect.get_client(
            host=self._settings.clickhouse_host,
            port=self._settings.clickhouse_port,
            username=self._settings.clickhouse_user,
            password=self._settings.clickhouse_password,
            database=self._settings.clickhouse_db,
        )