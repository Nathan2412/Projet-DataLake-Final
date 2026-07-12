"""Configuration centralisée du data lake financier."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FINANCIAL_DATASET_PATH = os.getenv(
    "FINANCIAL_DATASET_PATH",
    str(PROJECT_ROOT / "data" / "finance_dataset.csv"),
)

# PostgreSQL
POSTGRES = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "user":     os.getenv("POSTGRES_USER", "airflow"),
    "password": os.getenv("POSTGRES_PASSWORD", "airflow"),
    "dbname":   os.getenv("POSTGRES_DB", "airflow"),
}

POSTGRES_DSN = (
    f"postgresql://{POSTGRES['user']}:{POSTGRES['password']}"
    f"@{POSTGRES['host']}:{POSTGRES['port']}/{POSTGRES['dbname']}"
)

# MinIO
MINIO = {
    "endpoint":   f"{os.getenv('MINIO_HOST', 'localhost')}:{os.getenv('MINIO_PORT', '9000')}",
    "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    "secure":     False,
}
MINIO_BUCKET_RAW_FILE = "raw-financial-data"
MINIO_BUCKET_RAW_API  = "raw-api-data"

# Elasticsearch
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", 9200))
ES_URL  = f"http://{ES_HOST}:{ES_PORT}"
ES_INDEX_RAW = "raw_financial_events"

# Tickers suivis
SP500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "BRK-B", "JPM", "JNJ",
]
INDEX_TICKERS = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
ALL_TICKERS   = SP500_TICKERS + INDEX_TICKERS

# Paramètres d'ingestion
DEFAULT_PERIOD     = "2y"    # historique initial
DEFAULT_INTERVAL   = "1d"    # granularité journalière
