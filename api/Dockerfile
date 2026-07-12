FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app/src

# Installation des dépendances
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code de l'API et modules partagés
COPY api/           /app/
COPY data/          /app/data/
COPY src/           /app/src/
COPY tests/         /app/tests/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
