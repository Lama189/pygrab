import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Tabs, Tab, Input, ListView, ListItem, Label, Static, Footer, RichLog
from textual.reactive import reactive
from textual.binding import Binding
from textual import work
from rich.markup import escape

from tui.app import AppState, Tab as AppTab, LogLevel, LogEntry
from tui.api_client import ApiClient


class RGrabTUI(App):
    CSS_PATH = "tui.css"

    BINDINGS = [
        Binding("tab", "toggle_tab", "Switch Tab"),
        Binding("slash", "focus_search", "Search Mode"),
        Binding("escape", "blur_search", "Exit Search"),
        Binding("s", "toggle_sort", "Toggle Sort"),
        Binding("l", "toggle_live", "Live Tail"),
        Binding("r", "refresh_all", "Manual Refresh"),
        Binding("q", "quit_app", "Quit"),
        Binding("alt+1", "change_server(0)", "Server 1", show=False),
        Binding("alt+2", "change_server(1)", "Server 2", show=False),
        Binding("alt+3", "change_server(2)", "Server 3", show=False),
        Binding("alt+4", "change_server(3)", "Server 4", show=False),
        Binding("alt+5", "change_server(4)", "Server 5", show=False),
        Binding("1", "toggle_trace", "Trace", show=False),
        Binding("2", "toggle_debug", "Debug", show=False),
        Binding("3", "toggle_info", "Info", show=False),
        Binding("4", "toggle_warn", "Warn", show=False),
        Binding("5", "toggle_error", "Error", show=False),
        Binding("6", "toggle_fatal", "Fatal", show=False),
    ]

    def __init__(self, state: AppState, client: ApiClient):
        super().__init__()
        self.state = state
        self.client = client
        self.is_loading_more = False

    def compose(self) -> ComposeResult:
        with Container(id="app-grid"):
            with Vertical(id="server-panel"):
                for i, server in enumerate(self.state.servers):
                    active_class = "active" if i == self.state.active_server else ""
                    yield Label(f" 🖳  {i+1} ", id=f"srv-{i}", classes=f"server-item {active_class}")

            with Vertical(id="main-area"):
                yield Tabs(Tab("Logs", id="tab-logs"), Tab("Traces", id="tab-traces"))
                yield Static(self.render_level_tabs(), id="level-tabs")
                yield Input(placeholder="search...", value=self.state.search, id="search-bar")

                with Container(id="body-area"):
                    yield ListView(id="sidebar")
                    yield RichLog(id="log-list", markup=True, auto_scroll=True)

                with Vertical(id="footer-area"):
                    yield Footer()
                    yield Static(self.render_status_text(), id="status-bar")

        yield Container(
            Vertical(
                Label("No connection to server", id="err-title"),
                Label(self.state.server_url, id="err-url"),
                Label("connecting...", id="err-desc"),
                id="disconnected-box"
            ),
            id="disconnected-overlay"
        )

    def on_mount(self) -> None:
        self.title = f"pygrab [{self.state.server_name}]"
        self.update_server_ui_title()

        self.run_background_refresh()
        self.set_interval(2.0, self.on_live_tail_tick)

    def update_server_ui_title(self):
        self.title = f"pygrab v1.0.0 [{self.state.server_name}]"

    def build_logql_query(self) -> str:
        if not self.state.selected_labels:
            return "{}"
        parts = [f'{k}="{v}"' for k, v in self.state.selected_labels.items()]
        return "{" + ", ".join(parts) + "}"

    @work(exclusive=True, thread=True)
    async def run_background_refresh(self) -> None:
        try:
            current_query = self.build_logql_query()
            raw_logs = await self.client.fetch_logs(query=current_query, limit=200)
            self.state.logs = self.parse_loki_logs(raw_logs)

            self.state.labels = await self.client.fetch_labels()

            for key in ("service", "environment", "container_name"):
                try:
                    self.state.label_values[key] = await self.client.fetch_label_values(key)
                except Exception:
                    self.state.label_values[key] = []

            self.state.connected = True
            self.state.error = None

        except Exception as e:
            self.state.connected = False
            self.state.error = str(e)

        self.call_from_thread(self.refresh_ui_elements)

    @work(exclusive=True, thread=True)
    async def run_load_more(self) -> None:
        if not self.state.logs or self.is_loading_more:
            return

        self.is_loading_more = True

        try:
            current_query = self.build_logql_query()
            oldest_ns = (
                self.state.logs[-1].timestamp
                if self.state.newest_first
                else self.state.logs[0].timestamp
            )

            raw_logs = await self.client.fetch_logs(
                query=current_query,
                limit=200,
                start_ns=oldest_ns,
            )

            additional_logs = self.parse_loki_logs(raw_logs)

            if additional_logs:
                self.state.logs.extend(additional_logs)
                self.state.logs = list({log.timestamp: log for log in self.state.logs}.values())
                self.state.logs.sort(key=lambda l: l.timestamp, reverse=self.state.newest_first)
            else:
                self.state.has_more = False

        except Exception as e:
            self.state.error = str(e)

        finally:
            self.is_loading_more = False
            self.call_from_thread(self.refresh_ui_elements)

    async def on_live_tail_tick(self) -> None:
        if self.state.live_tail and self.state.connected:
            self.run_background_refresh()

    def parse_loki_logs(self, raw_data: dict) -> list[LogEntry]:
        parsed: list[LogEntry] = []

        streams = raw_data.get("data", {}).get("result", [])

        for stream_item in streams:
            labels = stream_item.get("stream", {})

            for val in stream_item.get("values", []):
                ts = int(val[0])
                msg = val[1]

                lvl = LogLevel.INFO
                for l in LogLevel:
                    if l.value in msg.upper():
                        lvl = l
                        break

                parsed.append(LogEntry(timestamp=ts, level=lvl, message=msg, labels=labels))

        parsed.sort(key=lambda l: l.timestamp, reverse=self.state.newest_first)
        return parsed

    def refresh_ui_elements(self) -> None:
        overlay = self.query_one("#disconnected-overlay")
        if self.state.connected:
            overlay.styles.display = "none"
        else:
            overlay.styles.display = "block"
            if self.state.error:
                self.query_one("#err-desc", Label).update(self.state.error)
                return

        filtered = self.state.filtered_logs()
        log_widget = self.query_one("#log-list", RichLog)
        log_widget.clear()

        for log in filtered:
            color = self.get_level_rich_color(log.level)
            ts_str = datetime.fromtimestamp(log.timestamp / 1_000_000_000).strftime("%H:%M:%S.%f")[:-3]
            container_name = log.labels.get("container_name") or log.labels.get("service") or log.labels.get("container") or "unknown"
            
            clean_msg = log.message
            upper_msg = clean_msg.upper()
            
            if upper_msg.startswith(f"{log.level.value}:"):
                clean_msg = clean_msg[len(log.level.value) + 1:].lstrip()
            elif upper_msg.startswith(f"{log.level.value} "):
                clean_msg = clean_msg[len(log.level.value) + 1:].lstrip()
                
            line_text = f"[gray]{ts_str}[/gray] [cyan]\\[{escape(container_name)}][/cyan] [{color}]{log.level.value:<5}[/{color}] {escape(clean_msg)}"
            log_widget.write(line_text)

        sidebar_view = self.query_one("#sidebar", ListView)
        sidebar_items = self.state.sidebar_items()

        if len(sidebar_view.children) == len(sidebar_items):
            for index, item in enumerate(sidebar_items):
                if item.type == "label":
                    line_text = f"[cyan][bold]{item.text}[/cyan][/bold]"
                else:
                    prefix = " > " if item.is_selected else "   "
                    color = "green" if item.is_selected else "white"
                    line_text = f"[{color}]{prefix}{item.text}[/{color}]"
                sidebar_view.children[index].query_one(Label).update(line_text)
        else:
            sidebar_view.clear()
            for item in sidebar_items:
                if item.type == "label":
                    sidebar_view.append(ListItem(Label(f"[cyan][bold]{item.text}[/cyan][/bold]")))
                else:
                    prefix = " > " if item.is_selected else "   "
                    color = "green" if item.is_selected else "white"
                    sidebar_view.append(ListItem(Label(f"[{color}]{prefix}{item.text}[/{color}]")))

        self.query_one("#level-tabs", Static).update(self.render_level_tabs())
        self.query_one("#status-bar", Static).update(self.render_status_text())

    def on_list_view_scroll_changed(self, event) -> None:
        if event.list_view.id == "log-list":
            scroll_y = event.list_view.scroll_y
            max_scroll_y = event.list_view.max_scroll_y

            if max_scroll_y > 0 and (max_scroll_y - scroll_y) < 20:
                if self.state.has_more and not self.is_loading_more:
                    self.run_load_more()

    def on_list_view_selected(self, event) -> None:
        if event.list_view.id == "sidebar":
            items = self.state.sidebar_items()
            idx = event.list_view.index

            if idx is not None and idx < len(items):
                item = items[idx]
                if item.type == "value":
                    self.state.toggle_label(item.label_key, item.text)
                    self.state.logs.clear()
                    self.query_one("#log-list", RichLog).clear()
                    self.run_background_refresh()

    def action_change_server(self, idx: int) -> None:
        if idx < len(self.state.servers):
            self.query_one(f"#srv-{self.state.active_server}", Label).remove_class("active")

            self.state.select_server(idx)
            self.client = ApiClient(base_url=self.state.server_url)

            self.update_server_ui_title()
            self.query_one(f"#srv-{idx}", Label).add_class("active")

            self.run_background_refresh()

    def action_toggle_tab(self) -> None:
        self.state.tab = AppTab.TRACES if self.state.tab == AppTab.LOGS else AppTab.LOGS
        self.refresh_ui_elements()

    def action_focus_search(self) -> None:
        self.query_one("#search-bar", Input).focus()

    def action_blur_search(self) -> None:
        self.query_one("#log-list", RichLog).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-bar":
            self.state.search = event.value
            self.refresh_ui_elements()

    def action_toggle_sort(self) -> None:
        self.state.newest_first = not self.state.newest_first

        if self.state.logs:
            self.state.logs.sort(key=lambda l: l.timestamp, reverse=self.state.newest_first)

        self.refresh_ui_elements()

    def action_toggle_live(self) -> None:
        self.state.live_tail = not self.state.live_tail
        self.refresh_ui_elements()

    def action_refresh_all(self) -> None:
        self.run_background_refresh()

    def action_toggle_trace(self) -> None: self._toggle_lvl("TRACE")
    def action_toggle_debug(self) -> None: self._toggle_lvl("DEBUG")
    def action_toggle_info(self) -> None: self._toggle_lvl("INFO")
    def action_toggle_warn(self) -> None: self._toggle_lvl("WARN")
    def action_toggle_error(self) -> None: self._toggle_lvl("ERROR")
    def action_toggle_fatal(self) -> None: self._toggle_lvl("FATAL")

    def _toggle_lvl(self, level_str: str) -> None:
        self.state.toggle_level(LogLevel[level_str])
        self.refresh_ui_elements()

    def action_quit_app(self) -> None:
        self.exit()

    def render_level_tabs(self) -> str:
        return "  ".join(
            f"[{self.get_level_rich_color(level)}][{i+1}] {level.value}[/{self.get_level_rich_color(level)}]"
            for i, level in enumerate(LogLevel)
        )

    def render_status_text(self) -> str:
        filtered = self.state.filtered_logs()
        sort_order = "newest" if self.state.newest_first else "oldest"
        return f"  {len(filtered)} lines | {sort_order} first | live tail: {'ON' if self.state.live_tail else 'OFF'}"

    def get_level_rich_color(self, level: LogLevel) -> str:
        return {
            LogLevel.TRACE: "bright_black",
            LogLevel.DEBUG: "white",
            LogLevel.INFO: "blue",
            LogLevel.WARN: "yellow",
            LogLevel.ERROR: "red",
            LogLevel.FATAL: "bright_red",
        }.get(level, "white")