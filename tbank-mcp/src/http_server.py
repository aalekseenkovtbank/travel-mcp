"""Streamable HTTP entrypoint for the unified T-Bank MCP."""
from __future__ import annotations

import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from .server import mcp


class HealthApp:
    """Expose a lightweight health endpoint alongside the MCP application."""

    def __init__(self, app: object) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)  # type: ignore[misc]
            return

        if scope.get("path") in {"/", "/health"}:
            response = JSONResponse({"ok": True, "service": "tbank-mcp"})
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)  # type: ignore[misc]


def main() -> None:
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8765")))

    # TLS and Host validation are handled by the Timeweb ingress.
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    app = HealthApp(mcp.streamable_http_app())
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
