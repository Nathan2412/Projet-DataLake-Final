# Conformité du devoir

Sujet : EFREI Data Lakes & Data Integration 2025-2026

Vérifications réalisées le 10 juillet 2026 sur la stack Docker.

## Exigences obligatoires

1. Data Lake de bout en bout

Le projet couvre l'ingestion, le stockage, les transformations et l'exposition par API. Les tests passent et les endpoints répondent.

2. Zones Raw, Staging et Curated

Raw utilise MinIO et Elasticsearch. Staging et Curated utilisent PostgreSQL.

3. Deux sources de données

Le pipeline utilise `data/finance_dataset.csv` et Yahoo Finance via `yfinance`. Les deux sources sont visibles dans la zone Raw.

4. Pipeline Airflow

Le DAG `financial_data_lake_pipeline` a été exécuté avec l'identifiant `manual_final_20260710T132822Z`. Les sept tâches se sont terminées avec le statut `success`.

5. API Gateway

Les endpoints `/raw`, `/staging`, `/curated`, `/health` et `/stats` ont été testés sur la stack Docker.

6. Livrables

Le dépôt contient le README, le rapport technique, la documentation technique, les deux PDF et le résultat du benchmark.

## Niveau avancé

Les endpoints `/ingest` et `/ingest_fast` ont été testés.

Le benchmark compare des lots de 1 et 100 tickers avec trois répétitions et un ordre alterné. Les douze appels ont réussi.

Pour 100 tickers, le temps médian passe de 104 825,65 ms à 12 230,36 ms. Le gain mesuré est de 88,33 %, supérieur à la cible de 30 %.

Les mesures sont enregistrées dans `livrables/benchmark_ingest_vs_ingest_fast.json`. Le fichier indique le commit testé `85aa820` et contient chaque échantillon.

## Commandes de vérification

```bash
python -m pytest tests/test_financial_logic.py tests/test_benchmark.py
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/stats
curl "http://localhost:8000/raw?limit=5"
curl "http://localhost:8000/staging?limit=5"
curl "http://localhost:8000/curated?limit=5"
python scripts/benchmark_endpoints.py --base-url http://localhost:8000 --period 5d --repeats 3
```
