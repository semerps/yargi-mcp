# Build stage — installs all dependencies
FROM python:3.11-slim AS builder

# Install uv (pip-based, supports all platforms)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files first for layer cache
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv (project not installed yet)
RUN uv sync --frozen --no-install-project --extra asgi --extra production

# Copy full source
COPY . .

# Install the project itself
RUN uv sync --frozen --extra asgi --extra production


# Runtime stage — lean image with only what's needed to run
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/mcp_server_main.py .
COPY --from=builder /app/asgi_app.py .
COPY --from=builder /app/__main__.py .
COPY --from=builder /app/yargitay_mcp_module ./yargitay_mcp_module
COPY --from=builder /app/bedesten_mcp_module ./bedesten_mcp_module
COPY --from=builder /app/danistay_mcp_module ./danistay_mcp_module
COPY --from=builder /app/emsal_mcp_module ./emsal_mcp_module
COPY --from=builder /app/uyusmazlik_mcp_module ./uyusmazlik_mcp_module
COPY --from=builder /app/anayasa_mcp_module ./anayasa_mcp_module
COPY --from=builder /app/kik_mcp_module ./kik_mcp_module
COPY --from=builder /app/rekabet_mcp_module ./rekabet_mcp_module
COPY --from=builder /app/sayistay_mcp_module ./sayistay_mcp_module
COPY --from=builder /app/sigorta_tahkim_mcp_module ./sigorta_tahkim_mcp_module

# Create logs directory with correct ownership
RUN mkdir -p logs && chown -R appuser:appuser /app

USER appuser

# Make venv the active Python environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# ASGI web service (override with "yargi-mcp" for stdio/MCP mode)
CMD ["uvicorn", "asgi_app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
