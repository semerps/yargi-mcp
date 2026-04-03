"""
ASGI application for Yargı MCP Server

This module provides ASGI/HTTP access to the Yargı MCP server,
allowing it to be deployed as a web service with FastAPI wrapper.

Usage:
    uvicorn asgi_app:app --host 0.0.0.0 --port 8000
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.datastructures import MutableHeaders

# Load .env file from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
from starlette.middleware.cors import CORSMiddleware
import uuid

from mcp_server_main import create_app

# Setup logging
logger = logging.getLogger(__name__)


# Configure CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*").strip()
if allowed_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.debug(f"CORS Origins configured: {cors_origins}")

# Create MCP app
mcp_server = create_app()

# Create MCP Starlette sub-application with JSON response (no SSE)
_mcp_app = mcp_server.http_app(
    path="/",
    transport="http",
    json_response=True,  # Return plain JSON instead of SSE
    stateless_http=True
)


# Configure JSON encoder for proper Turkish character support
class UTF8JSONResponse(JSONResponse):
    def __init__(self, content=None, status_code=200, headers=None, **kwargs):
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/json; charset=utf-8"
        super().__init__(content, status_code, headers, **kwargs)

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


# Create FastAPI wrapper application
app = FastAPI(
    title="Yargı MCP Server",
    description="MCP server for Turkish legal databases",
    version="0.1.0",
    default_response_class=UTF8JSONResponse,
    redirect_slashes=False,
)

# Add middlewares in reverse order (last added = first called)
app.add_middleware(CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=[
        "Content-Type",
        "X-Request-ID",
        "X-Session-ID",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=["Content-Type", "X-Request-ID", "X-Session-ID"],
    max_age=3600,  # 1 hour
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
    }


@app.api_route("/mcp", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def redirect_to_slash(request: Request):
    """Redirect /mcp to /mcp/ preserving HTTP method with 308"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/mcp/", status_code=308)


# Session-ID preserving ASGI wrapper class
class MCPAsgiApp:
    """ASGI app wrapper that extracts/creates session ID and passes in request state."""

    def __init__(self, mcp_app):
        self.mcp_app = mcp_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract session ID from headers or create new one
            headers = list(scope.get("headers", []))
            session_id = None

            # Look for session ID in headers (case-insensitive)
            for header_name, header_value in headers:
                if header_name.lower() == b"x-session-id":
                    session_id = header_value.decode() if isinstance(header_value, bytes) else header_value
                    break

            # Create new session ID if not found
            if not session_id:
                session_id = str(uuid.uuid4())

            # Add/update session ID in headers for consistency
            headers = [(h[0], h[1]) for h in headers if h[0].lower() != b"x-session-id"]
            headers.append((b"x-session-id", session_id.encode()))

            scope["headers"] = headers

            # Also set in state for the application
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["session_id"] = session_id

        # Forward to actual MCP app
        await self.mcp_app(scope, receive, send)


# Mount ASGI app at /mcp/ (without wrapper - let FastMCP handle it directly)
app.mount("/mcp", _mcp_app)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Yargı MCP Server",
        "description": "MCP server for Turkish legal databases",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
            "status": "/status",
        },
        "transports": {
            "http": "/mcp"
        },
        "supported_databases": [
            "Yargıtay (Court of Cassation)",
            "Danıştay (Council of State)",
            "Emsal (Precedent)",
            "Uyuşmazlık Mahkemesi (Court of Jurisdictional Disputes)",
            "Anayasa Mahkemesi (Constitutional Court)",
            "Kamu İhale Kurulu (Public Procurement Authority)",
            "Rekabet Kurumu (Competition Authority)",
            "Sayıştay (Court of Accounts)",
            "KVKK (Personal Data Protection Authority)",
            "BDDK (Banking Regulation and Supervision Agency)",
            "Bedesten API (Multiple courts)",
            "Sigorta Tahkim Komisyonu (Insurance Arbitration Commission)",
        ],
    }


@app.get("/status")
async def status():
    """Status endpoint with detailed information"""
    return {
        "status": "operational",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "transport": "streamable_http",
        "note": "Use /mcp endpoint for MCP requests",
    }


# Get lifespan context from MCP app (for startup/shutdown)
app.router.lifespan_context = _mcp_app.lifespan

# Export for uvicorn
__all__ = ["app"]
