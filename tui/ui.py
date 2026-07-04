from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Tabs, Tab, Input, ListView, ListItem, Label, Static
from textual.reactive import reactive
from textual.binding import Binding

from datetime import datetime

from tui.app import AppState, Tab as AppTab, InputMode, LogLevel, LogEntry
from tui.api_client import ApiClient


class RGrabTUI(App):
    CSS_PATH = "tui.css"

    BINDINGS = [
        Binding("tab", "toggle_tab", "Switch Tab", show=True),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("s", "toggle_sort", "Toggle Sort", show=True),
        Binding("l", "toggle_live", "Live Tail", show=True),
        Binding("r", "refresh_data", "Refresh", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("1", "toggle_level_trace", "1:TRACE", show=False),
        Binding("2", "toggle_level_debug", "2:DEBUG", show=False),
        Binding("3", "toggle_level_info", "3:INFO", show=False),
        Binding("4", "toggle_level_warn", "4:WARN", show=False),
        Binding("5", "toggle_level_error", "5:ERROR", show=False),
        Binding("6", "toggle_level_fatal", "6:FATAL", show=False),
    ]

    def __init__(self, state: AppState, client: ApiClient):
        super().__init__()
        self.state = state
        self.client = client

    def compose(self) -> ComposeResult:
        with Container(id="app-grid"):
            with Vertical(id="server-panel"):
                for i, server in enumerate(self.state.servers):
                    is_active = "active" if i == self.state.active_server else ""
                    yield Label(f" 🖳  {i+1} ", classes=f"server-item {is_active}")

            with Vertical(id="main-area"):
                yield Tabs(
                    Tab("Logs", id="tab-logs"),
                    Tab("Traces", id="tab-traces"),
                )

                yield Static(self.render_level_tabs(), id="level-tabs")

                yield Input(
                    placeholder="search...",
                    value=self.state.search,
                    id="search-bar",
                )

                with Container(id="body-area"):
                    yield ListView(id="sidebar")
                    yield ListView(id="log-list")

                with Vertical(id="footer-area"):
                    yield Footer()
                    yield Static(self.render_status_text(), id="status-bar")

        if not self.state.connected:
            with Container(id="disconnected-overlay"):
                with Vertical(id="disconnected-box"):
                    yield Label("No connection to server", classes="error-title")
                    yield Label(self.state.server_url, classes="error-url")
                    yield Label(self.state.error or "connection refused", classes="error-desc")

    def on_mount(self) -> None:
        self.title = f"pygrab [{self.state.server_name}]"
        self.update_ui_data()
        self.set_interval(2.0, self.poll_logs_background)

    def render_level_tabs(self) -> str:
        parts = []
        for i, level in enumerate(LogLevel):
            idx = i + 1
            enabled = self.state.level_enabled.get(level, True)
            color = self.get_level_rich_color(level) if enabled else "gray"
            parts.append(f"[{color}][{idx}] {level.value}[/{color}]")
        return "  ".join(parts)

    def render_status_text(self) -> str:
        if self.state.tab == AppTab.LOGS:
            filtered = self.state.filtered_logs()
            sort_order = "newest" if self.state.newest_first else "oldest"
            return f"  {len(filtered)} lines | {sort_order} first | live: {self.state.live_tail}"
        return f"  {len(self.state.unique_traces())} traces "

    def get_level_rich_color(self, level: LogLevel) -> str:
        return {
            LogLevel.TRACE: "bright_black",
            LogLevel.DEBUG: "white",
            LogLevel.INFO: "blue",
            LogLevel.WARN: "yellow",
            LogLevel.ERROR: "red",
            LogLevel.FATAL: "bright_red",
        }.get(level, "white")

    def update_ui_data(self) -> None:
        log_list_view = self.query_one("#log-list", ListView)
        log_list_view.clear()

        for log in self.state.filtered_logs():
            color = self.get_level_rich_color(log.level)

            ts_str = datetime.fromtimestamp(
                log.timestamp / 1_000_000_000
            ).strftime("%H:%M:%S.%f")[:-3]

            line_text = (
                f"[gray]{ts_str}[/gray] "
                f"[{color}]{log.level.value:<5}[/{color}] "
                f"{log.message}"
            )
            log_list_view.append(ListItem(Label(line_text)))

        self.query_one("#status-bar", Static).update(self.render_status_text())

    def action_toggle_tab(self) -> None:
        tabs = self.query_one(Tabs)

        if self.state.tab == AppTab.LOGS:
            self.state.tab = AppTab.TRACES
            tabs.active = "tab-traces"
        else:
            self.state.tab = AppTab.LOGS
            tabs.active = "tab-logs"

        self.update_ui_data()

    def action_focus_search(self) -> None:
        self.query_one("#search-bar").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-bar":
            self.state.search = event.value
            self.update_ui_data()

    def action_toggle_sort(self) -> None:
        self.state.newest_first = not self.state.newest_first
        self.update_ui_data()

    def action_toggle_live(self) -> None:
        self.state.live_tail = not self.state.live_tail
        self.update_ui_data()

    def action_toggle_level_trace(self) -> None:
        self._toggle_lvl(LogLevel.TRACE)

    def action_toggle_level_debug(self) -> None:
        self._toggle_lvl(LogLevel.DEBUG)

    def action_toggle_level_info(self) -> None:
        self._toggle_lvl(LogLevel.INFO)

    def action_toggle_level_warn(self) -> None:
        self._toggle_lvl(LogLevel.WARN)

    def action_toggle_level_error(self) -> None:
        self._toggle_lvl(LogLevel.ERROR)

    def action_toggle_level_fatal(self) -> None:
        self._toggle_lvl(LogLevel.FATAL)

    def _toggle_lvl(self, level: LogLevel) -> None:
        self.state.toggle_level(level)
        self.query_one("#level-tabs", Static).update(self.render_level_tabs())
        self.update_ui_data()

    async def poll_logs_background(self) -> None:
        if not self.state.live_tail:
            return

        try:
            raw_data = await self.client.fetch_logs(
                query='{stream="stdout"}',
                limit=100
            )

            new_logs: list[LogEntry] = []
            streams = raw_data.get("data", {}).get("result", [])

            for stream_res in streams:
                labels = stream_res.get("stream", {})

                for val in stream_res.get("values", []):
                    ts, msg = int(val[0]), val[1]

                    lvl = LogLevel.INFO

                    if "ERROR" in msg or "ERR" in msg:
                        lvl = LogLevel.ERROR
                    elif "WARN" in msg:
                        lvl = LogLevel.WARN
                    elif "DEBUG" in msg:
                        lvl = LogLevel.DEBUG

                    new_logs.append(
                        LogEntry(
                            timestamp=ts,
                            level=lvl,
                            message=msg,
                            labels=labels,
                        )
                    )

            self.state.logs = new_logs
            self.state.connected = True
            self.state.error = None

        except Exception as e:
            self.state.connected = False
            self.state.error = str(e)

        self.update_ui_data()