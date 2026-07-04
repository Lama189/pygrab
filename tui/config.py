import os
from pathlib import Path
from dataclasses import dataclass
import tomli as tomllib

DEFAULT_SERVER_NAME = "local"
DEFAULT_SERVER_URL = "http://localhost:8000"
CONFIG_DIR_NAME = ".pygrab"
CONFIG_FILE_NAME = "config.toml"

DEFAULT_CONFIG_CONTENT = """# pygrab TUI configuration

[[servers]]
name = "local"
url = "http://localhost:8000"
"""

@dataclass
class ServerEntry:
    name: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "url": self.url}

class Config:
    def __init__(self, servers: list[ServerEntry]):
        self.servers = servers


def config_dir() -> Path | None:
    home = Path.home()
    if not home:
        return None
    return home / CONFIG_DIR_NAME


def config_path() -> Path | None:
    cdir = config_dir()
    if not cdir:
        return None
    return cdir / CONFIG_FILE_NAME


def ensure_default_config():
    cdir = config_dir()
    if not cdir:
        return

    path = cdir / CONFIG_FILE_NAME
    if path.exists():
        return

    try:
        cdir.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG_CONTENT, encoding="utf-8")
    except Exception:
        pass


def load_file_config() -> dict[str, object]:
    cpath = config_path()
    if not cpath or not cpath.exists():
        return {}

    try:
        contents = cpath.read_text(encoding="utf-8")
        return tomllib.loads(contents)
    except Exception:
        return {}


def build_server_list(file_cfg: dict[str, object]) -> list[ServerEntry]:
    servers_raw = file_cfg.get("servers")

    if servers_raw and isinstance(servers_raw, list):
        return [
            ServerEntry(
                name=s.get("name", "unknown"),
                url=s.get("url", DEFAULT_SERVER_URL),
            )
            for s in servers_raw
            if "name" in s or "url" in s
        ]

    return [ServerEntry(name=DEFAULT_SERVER_NAME, url=DEFAULT_SERVER_URL)]


def load(cli_server: str | None = None) -> Config:
    ensure_default_config()
    file_cfg = load_file_config()
    servers = build_server_list(file_cfg)

    if cli_server:
        servers.insert(0, ServerEntry(name="cli", url=cli_server))

    return Config(servers=servers)