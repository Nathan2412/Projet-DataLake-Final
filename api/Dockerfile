FROM python:3.11-slim

WORKDIR /app

# uv installe exactement les versions enregistrées dans uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src/ /app/src/
RUN uv sync --frozen --no-dev

# Code de l'API et modules partagés
COPY api/           /app/
COPY data/          /app/data/
COPY tests/         /app/tests/

EXPOSE 8000

CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
