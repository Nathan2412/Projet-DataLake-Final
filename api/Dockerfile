FROM python:3.11.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

WORKDIR /app

# uv installe exactement les versions du verrou dans un environnement isolé.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --group api --no-install-project

# Code de l'API et modules partagés
COPY api/           /app/
COPY config/        /app/config/
COPY data/          /app/data/
COPY ingestion/     /app/ingestion/
COPY transformation/ /app/transformation/
COPY tests/          /app/tests/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
