"""MCP server entrypoint for stdio and Streamable HTTP.

Run: python -m src.travel_mcp
     python -m src.travel_mcp --http --port 8765
"""
from __future__ import annotations

import argparse
import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..server import mcp


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    """Expose the health endpoint used by the deployment platform."""
    return JSONResponse({"ok": True, "service": "travel-nova-mcp"})

_DEFAULT_HTTP_HOST = "127.0.0.1"
_DEFAULT_HTTP_PORT = 8765


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Travel Nova MCP (stdio or Streamable HTTP)")
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument(
        "--stdio",
        action="store_true",
        help="Serve over stdio (default unless TRAVEL_MCP_TRANSPORT=http)",
    )
    transport.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on --host/--port (path /mcp)",
    )
    parser.add_argument("--host", default=os.environ.get("TRAVEL_MCP_HOST", _DEFAULT_HTTP_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get(
            "PORT", os.environ.get("TRAVEL_MCP_PORT", str(_DEFAULT_HTTP_PORT))
        )),
    )
    return parser.parse_args(argv)


def _want_http(args: argparse.Namespace) -> bool:
    if args.http:
        return True
    if args.stdio:
        return False
    env = os.environ.get("TRAVEL_MCP_TRANSPORT", "stdio").strip().lower()
    return env in {"http", "streamable-http", "streamable_http"}


def _http_transport_security(bind_host: str) -> object | None:
    """Replace FastMCP's localhost-only Host check when we bind beyond loopback.

    FastMCP enables DNS-rebinding protection at construction time based on the
    default host (127.0.0.1). We later change ``settings.host`` for ``--http``,
    so the leftover allow-list still rejects Traefik's public Host header.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    relax = os.environ.get("TRAVEL_MCP_RELAX_DNS_REBINDING", "").strip().lower()
    if relax in {"1", "true", "yes"}:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    public = os.environ.get("TRAVEL_MCP_PUBLIC_HOST", "").strip()
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
    ]
    if bind_host not in {"127.0.0.1", "localhost", "::1"}:
        hosts.append(f"{bind_host}:*")
    if public:
        hosts.extend([public, f"{public}:*"])
        origins.extend(
            [
                f"https://{public}",
                f"https://{public}:*",
                f"http://{public}",
                f"http://{public}:*",
            ]
        )
    extra_origins = os.environ.get("TRAVEL_MCP_ALLOWED_ORIGINS", "").strip()
    if extra_origins:
        origins.extend(item.strip() for item in extra_origins.split(",") if item.strip())
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def main(argv: list[str] | None = None) -> None:
    """Serve the registered MCP tools over stdio or Streamable HTTP."""
    args = _parse_args(argv)
    if _want_http(args):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.transport_security = _http_transport_security(args.host)
        mcp.run(transport="streamable-http")
        return
    mcp.run()


if __name__ == "__main__":
    main()
