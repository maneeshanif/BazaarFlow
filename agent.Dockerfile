# Agent service image (ADR 0003): contains only agent_service. No alembic, no models, no database code,
# and no database variable is passed to it (docker-compose.yml), so it cannot reach Postgres.
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runner
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY agent_service/ ./agent_service/
RUN addgroup --system --gid 1001 appgroup && adduser --system --uid 1001 --gid 1001 appuser && chown -R appuser:appgroup /app
USER appuser
EXPOSE 8100
CMD ["uvicorn", "agent_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100"]
