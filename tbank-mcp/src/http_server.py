"""Authenticated Streamable HTTP entrypoint for the unified T-Bank MCP."""
from __future__ import annotations

import hmac
import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from .server import mcp


class BearerAuthApp:
    """Require one deployment token for every MCP protocol request."""

    def __init__(self, app: object, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)  # type: ignore[misc]
            return

        if scope.get("path") in {"/", "/health"}:
            response = JSONResponse({"ok": True, "service": "tbank-mcp"})
            await response(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"authorization", b"").decode("latin-1")
        expected = f"Bearer {self.token}"
        if not hmac.compare_digest(supplied, expected):
            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)  # type: ignore[misc]


def main() -> None:
    token = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if not token:
        raise SystemExit("MCP_AUTH_TOKEN is required for the HTTP server")

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8765")))

    # TLS and Host validation are handled by the Timeweb ingress. Protocol
    # requests still require the deployment Bearer token above.
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    app = BearerAuthApp(mcp.streamable_http_app(), token)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
