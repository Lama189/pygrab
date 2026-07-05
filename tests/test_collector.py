import pytest
from unittest.mock import AsyncMock, MagicMock

from app.application.collector.labels import DockerLabelsExtractor
from app.application.collector.parser import LogParser
from app.domain.enums import LogLevel


class TestLogParser:
    def setup_method(self):
        self.parser = LogParser()

    def test_parse_info_level(self):
        assert self.parser.parse_level("INFO Starting server") == LogLevel.INFO

    def test_parse_error_level(self):
        assert self.parser.parse_level("ERROR Connection failed") == LogLevel.ERROR

    def test_parse_warn_level(self):
        assert self.parser.parse_level("WARNING Deprecated usage") == LogLevel.WARN

    def test_parse_debug_level(self):
        assert self.parser.parse_level("DEBUG Loading config") == LogLevel.DEBUG

    def test_parse_fatal_level(self):
        assert self.parser.parse_level("FATAL Out of memory") == LogLevel.FATAL

    def test_parse_critical_level(self):
        assert self.parser.parse_level("CRITICAL Disk full") == LogLevel.FATAL

    def test_parse_trace_level(self):
        assert self.parser.parse_level("TRACE Entering function") == LogLevel.TRACE

    def test_parse_unknown_defaults_to_info(self):
        assert self.parser.parse_level("Random text without level") == LogLevel.INFO

    def test_parse_case_insensitive(self):
        assert self.parser.parse_level("info lowercase") == LogLevel.INFO
        assert self.parser.parse_level("Error mixed case") == LogLevel.ERROR

    def test_parse_level_in_middle_of_message(self):
        assert self.parser.parse_level("Something INFO happened") == LogLevel.INFO


class TestDockerLabelsExtractor:
    def test_extract_basic_labels(self):
        container_info = {
            "Id": "abc123",
            "Name": "/my-container",
            "Config": {
                "Image": "nginx:latest",
                "Labels": {
                    "com.docker.compose.project": "myproject",
                    "com.docker.compose.service": "web",
                },
            },
        }

        labels = DockerLabelsExtractor.extract(container_info, "stdout")

        assert labels["container_id"] == "abc123"
        assert labels["container_name"] == "my-container"
        assert labels["image"] == "nginx:latest"
        assert labels["compose_project"] == "myproject"
        assert labels["compose_service"] == "web"
        assert labels["service"] == "web"
        assert labels["stream"] == "stdout"

    def test_extract_stderr_stream(self):
        container_info = {
            "Id": "def456",
            "Name": "/app",
            "Config": {"Image": "app:latest", "Labels": {}},
        }

        labels = DockerLabelsExtractor.extract(container_info, "stderr")
        assert labels["stream"] == "stderr"

    def test_extract_no_compose_labels(self):
        container_info = {
            "Id": "ghi789",
            "Name": "/standalone",
            "Config": {
                "Image": "redis:7",
                "Labels": {},
            },
        }

        labels = DockerLabelsExtractor.extract(container_info, "stdout")
        assert labels["compose_project"] == "default"
        assert labels["compose_service"] == "standalone"
        assert labels["service"] == "standalone"

    def test_extract_strips_leading_slash(self):
        container_info = {
            "Id": "jkl012",
            "Name": "/container-with-slash",
            "Config": {"Image": "img", "Labels": {}},
        }

        labels = DockerLabelsExtractor.extract(container_info, "stdout")
        assert labels["container_name"] == "container-with-slash"
