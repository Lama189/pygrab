from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class Tab(Enum):
    LOGS = "logs"
    TRACES = "traces"

class InputMode(Enum):
    NORMAL = "normal"
    SEARCH = "search"

class LogLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

@dataclass
class LogEntry:
    timestamp: int
    level: LogLevel
    message: str
    labels: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: datetime
    status: str

@dataclass
class TraceGroup:
    trace_id: str
    root_operation: str = ""
    root_service: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    total_duration_ms: float = 0.0
    span_count: int = 0
    has_error: bool = False

@dataclass
class ServerEntry:
    name: str
    url: str

class SidebarItem:
    def __init__(self, item_type: str, text: str, label_key: str = "", is_selected: bool = False):
        self.type = item_type
        self.text = text
        self.label_key = label_key
        self.is_selected = is_selected

class AppState:
    def __init__(self, servers: list[dict[str, str]]):
        self.servers = [ServerEntry(name=s["name"], url=s["url"]) for s in servers]
        self.active_server: int = 0
        self.server_changed: bool = False
        self.tab: Tab = Tab.LOGS
        self.logs: list[LogEntry] = []
        self.traces: list[Span] = []
        self.trace_spans: dict[str, list[Span]] = {}
        self.labels: list[str] = []
        self.label_values: dict[str, list[str]] = {}
        self.selected_labels: dict[str, str] = {}
        self.search: str = ""
        self.input_mode: InputMode = InputMode.NORMAL
        self.expanded_trace: str | None = None
        self.live_tail: bool = True
        self.has_more: bool = True
        self.should_quit: bool = False
        self.error: str | None = None
        self.connected: bool = False
        self.level_enabled: dict[LogLevel, bool] = {level: True for level in LogLevel}
        self.newest_first: bool = True

    @property
    def server_url(self) -> str:
        return self.servers[self.active_server].url

    @property
    def server_name(self) -> str:
        return self.servers[self.active_server].name

    def select_server(self, idx: int):
        if idx < len(self.servers) and idx != self.active_server:
            self.active_server = idx
            self.server_changed = True
            self.reset_state()

    def reset_state(self):
        self.logs.clear()
        self.traces.clear()
        self.trace_spans.clear()
        self.labels.clear()
        self.label_values.clear()
        self.selected_labels.clear()
        self.search = ""
        self.expanded_trace = None
        self.has_more = True
        self.error = None
        self.connected = False

    def toggle_level(self, level: LogLevel):
        self.level_enabled[level] = not self.level_enabled[level]

    def filtered_logs(self) -> list[LogEntry]:
        result = [log for log in self.logs if self._log_matches_filters(log)]
        if self.newest_first:
            return result
        return list(reversed(result))

    def _log_matches_filters(self, log: LogEntry) -> bool:
        if not self.level_enabled.get(log.level, True):
            return False

        if self.search:
            search_lower = self.search.lower()
            in_msg = search_lower in log.message.lower()
            in_labels = any(
                search_lower in k.lower() or search_lower in v.lower()
                for k, v in log.labels.items()
            )
            if not (in_msg or in_labels):
                return False

        for key, val in self.selected_labels.items():
            if log.labels.get(key) != val:
                return False

        return True

    def unique_traces(self) -> list[TraceGroup]:
        groups: dict[str, TraceGroup] = {}

        for span in self.traces:
            if span.trace_id not in groups:
                groups[span.trace_id] = TraceGroup(
                    trace_id=span.trace_id,
                    start_time=span.start_time
                )

            group = groups[span.trace_id]
            group.span_count += 1

            if span.parent_span_id is None:
                group.root_operation = span.operation_name
                group.root_service = span.service_name
                group.start_time = span.start_time
                duration = span.end_time - span.start_time
                group.total_duration_ms = duration.total_seconds() * 1000.0

            if span.status == "ERROR":
                group.has_error = True

        return sorted(groups.values(), key=lambda t: t.start_time, reverse=True)

    def sidebar_items(self) -> list[SidebarItem]:
        services = self.label_values.get("service", [])
        environments = self.label_values.get("environment", [])
        items = []

        if services:
            for svc in services:
                items.append(SidebarItem("label", svc))
                items.append(
                    SidebarItem(
                        "value",
                        svc,
                        "service",
                        self.selected_labels.get("service") == svc
                    )
                )
                for env in environments:
                    items.append(
                        SidebarItem(
                            "value",
                            env,
                            "environment",
                            self.selected_labels.get("environment") == env
                        )
                    )
        elif environments:
            items.append(SidebarItem("label", "environment"))
            for env in environments:
                items.append(
                    SidebarItem(
                        "value",
                        env,
                        "environment",
                        self.selected_labels.get("environment") == env
                    )
                )

        return items

    def toggle_label(self, label_key: str, value: str):
        if self.selected_labels.get(label_key) == value:
            self.selected_labels.pop(label_key, None)
        else:
            self.selected_labels[label_key] = value