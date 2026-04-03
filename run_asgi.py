#!/usr/bin/env python
"""
Script to run the ASGI server with environment-based configuration
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Get configuration from environment
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
RELOAD = os.getenv("RELOAD", "false").lower() == "true"

# Build uvicorn command
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "asgi_app:app",
    "--host", HOST,
    "--port", str(PORT),
    "--log-level", LOG_LEVEL,
]

# Add reload flag if specified
if RELOAD:
    cmd.append("--reload")

print(f"🚀 Starting Yargı MCP Server")
print(f"   Host: {HOST}")
print(f"   Port: {PORT}")
print(f"   Log Level: {LOG_LEVEL}")
print(f"   Reload: {RELOAD}")
print(f"\n   Running: {' '.join(cmd)}\n")

# Run uvicorn
subprocess.run(cmd)
