# Local development image: the API plus what is needed to provision, migrate and seed a throwaway database.
# Not for production (that is backend.Dockerfile).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
