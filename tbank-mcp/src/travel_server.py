"""Read-only travel entrypoint for the T-Bank MCP server.

The environment must be selected before importing :mod:`src.server`, because
FastMCP registers decorated functions while that module is imported.  This tiny
entrypoint is therefore deliberately separate from the full banking server.
"""
from __future__ import annotations

import os


def main() -> None:
    os.environ["TBANK_TOOLSET"] = "travel"
    # Travel experiments must not create a persistent call trace unless the
    # operator explicitly opts back in.
    os.environ.setdefault("TBANK_TRACE", "0")
    from .server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
