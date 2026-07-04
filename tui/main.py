import argparse
import asyncio

from tui.config import load as load_config
from tui.app import AppState
from tui.api_client import ApiClient
from tui.tui_app import RGrabTUI


def parse_args():
    parser = argparse.ArgumentParser(description="rgrab TUI Client")
    parser.add_argument(
        "-s", "--server", 
        type=str, 
        help="Target backend server URL (overrides config.toml)"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    cfg = load_config(cli_server=args.server)
    servers_list = [s.to_dict() for s in cfg.servers]
    state = AppState(servers=servers_list)
    client = ApiClient(base_url=state.server_url)
    
    app = RGrabTUI(state=state, client=client)
    await app.run_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВыход из TUI...")