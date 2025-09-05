FROM python:3.12-slim


COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --locked

COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]