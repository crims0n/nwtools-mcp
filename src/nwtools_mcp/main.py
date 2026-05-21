"""Process bootstrap for stdio and HTTP transports."""

from __future__ import annotations

import logging
import os

import uvicorn

from .app import create_http_app, log_event, mcp


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(message)s")


def run() -> None:
    configure_logging()

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "streamable-http", "sse"}:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT {transport!r}; expected stdio, streamable-http, or sse"
        )

    if transport == "stdio":
        log_event("server_starting", transport=transport)
        mcp.run()
        return

    api_key = os.getenv("API_KEY")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    app = create_http_app(transport, api_key=api_key)

    log_event(
        "server_starting",
        transport=transport,
        host=host,
        port=port,
        auth_enabled=bool(api_key),
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
