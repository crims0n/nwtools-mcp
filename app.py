"""MCP server construction and HTTP operational routes."""

from __future__ import annotations

import importlib.metadata
import json
import logging
import time
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tools import (
    check_coverage,
    cidr_to_range,
    classify_ip,
    find_gaps,
    ip_convert,
    ip_in_subnet,
    parse_cidr,
    range_to_cidrs,
    subnets_overlap,
    subtract_subnet,
    summarize_cidrs,
)

LOGGER = logging.getLogger("nwtools")

TOOL_FUNCTIONS = [
    parse_cidr,
    ip_in_subnet,
    subnets_overlap,
    cidr_to_range,
    range_to_cidrs,
    subtract_subnet,
    find_gaps,
    check_coverage,
    summarize_cidrs,
    classify_ip,
    ip_convert,
]


def _version() -> str:
    try:
        return importlib.metadata.version("nwtools-mcp")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, "service": "nwtools-mcp", **fields}
    LOGGER.info(json.dumps(payload, sort_keys=True))


def create_mcp() -> FastMCP:
    mcp = FastMCP("nwtools")
    for func in TOOL_FUNCTIONS:
        mcp.tool()(func)

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request: Request) -> Response:
        return JSONResponse(
            {
                "status": "ok",
                "service": "nwtools-mcp",
                "version": _version(),
            }
        )

    @mcp.custom_route("/readyz", methods=["GET"], include_in_schema=False)
    async def readyz(request: Request) -> Response:
        return JSONResponse(
            {
                "status": "ready",
                "service": "nwtools-mcp",
                "version": _version(),
            }
        )

    return mcp


class RequestLoggingMiddleware:
    """Minimal ASGI middleware for request IDs and structured access logs."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode()
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            client = scope.get("client")
            log_event(
                "http_request",
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
                query_string=scope.get("query_string", b"").decode(),
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client[0] if client else None,
            )


class ApiKeyMiddleware:
    """Small ASGI wrapper for shared API key protection on MCP endpoints."""

    def __init__(self, app, api_key: str, public_paths: set[str] | None = None):
        self.app = app
        self.api_key = api_key
        self.public_paths = public_paths or set()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path") in self.public_paths:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        if headers.get(b"x-api-key", b"").decode() != self.api_key:
            await JSONResponse({"error": "Unauthorized"}, status_code=401)(scope, receive, send)
            return

        await self.app(scope, receive, send)


def create_http_app(transport: str, api_key: str | None = None):
    mcp = create_mcp()
    base_app = mcp.streamable_http_app() if transport == "streamable-http" else mcp.sse_app()
    app = RequestLoggingMiddleware(base_app)
    if api_key:
        app = ApiKeyMiddleware(app, api_key, public_paths={"/healthz", "/readyz"})
    return app


mcp = create_mcp()
