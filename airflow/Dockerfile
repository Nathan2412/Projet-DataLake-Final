FROM apache/airflow:slim-2.8.1-python3.11

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /usr/local/bin/uv

WORKDIR /opt/airflow/project

COPY --chown=airflow:root pyproject.toml uv.lock .python-version ./
COPY --chown=airflow:root airflow/constraints.txt ./airflow-constraints.txt

# Airflow garde trois bibliothèques de son socle qui ont des contraintes
# plus strictes. Toutes les autres dépendances métier viennent du verrou uv.
RUN uv export --frozen --no-dev --no-emit-project \
        --no-emit-package rich \
        --no-emit-package protobuf \
        --no-emit-package markdown-it-py \
        --no-hashes \
        --output-file /tmp/requirements.txt \
    && pip install --no-cache-dir --user \
        --constraint airflow-constraints.txt \
        --requirement /tmp/requirements.txt \
    && pip check \
    && rm /tmp/requirements.txt

WORKDIR /opt/airflow
