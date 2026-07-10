# Conformité du devoir

## Version et état

- Sujet : EFREI Data Lakes & Data Integration 2025-2026
- Branche : `improve/assignment-compliance`
Ce tableau est le suivi des exigences du sujet, avec ce que le code met en place aujourd'hui et la façon de le vérifier.

- **implemented** = livrable/procédure présent dans le dépôt et testable.
- **needs live rerun** = la preuve dépend d'une exécution Docker/API réelle (à relancer sur hôte Docker).

## Matrice de conformité

| # | Exigence | Type | Fichiers d'implémentation | Vérification | Statut |
|---|---|---|---|---|---|
| 1 | Concevoir et implémenter un Data Lake de bout en bout (ingestion, stockage, transformation, exposition) | Obligatoire | `ingestion/*`, `transformation/*`, `api/*`, `airflow/dags/financial_pipeline_dag.py`, `scripts/init_db.sql` | `python -m pytest tests/test_financial_logic.py tests/test_benchmark.py` (couverture structurelle), puis `docker compose up -d` + GET `/health`, GET `/raw`, `/staging`, `/curated` | implemented |
| 2 | Structurer le Data Lake en zones Raw / Staging / Curated | Obligatoire | `ingestion/ingest_file.py`, `ingestion/ingest_api.py`, `transformation/staging/transform_staging.py`, `transformation/curated/transform_curated.py`, `docker-compose.yml` | `python scripts/benchmark_endpoints.py --base-url http://localhost:8000 --repeats 3` (après démarrage) | implemented |
| 3 | Utiliser Elasticsearch ou stockage type S3 pour Raw | Obligatoire | `docker-compose.yml`, `ingestion/ingest_file.py`, `ingestion/ingest_api.py`, `api/dependencies.py`, `api/routers/raw.py` | Démarrage Docker + GET `/raw`, GET `/stats` (sections `raw_elasticsearch`, `raw_minio`) | implemented |
| 4 | Utiliser deux sources de données | Obligatoire | `ingestion/ingest_file.py`, `ingestion/ingest_api.py`, `config/settings.py` | Tests des identifiants par source, puis GET `/raw?source=yfinance_file` et `/raw?source=yfinance_api` sur la stack | implemented |
| 5 | Mettre en place une pipeline d'intégration avec Airflow | Obligatoire | `airflow/dags/financial_pipeline_dag.py`, `ingestion/ingest_file.py`, `ingestion/ingest_api.py`, `transformation/staging/transform_staging.py`, `transformation/curated/transform_curated.py` | Démarrage `docker compose up -d`, check Airflow UI `http://localhost:8080`, DAG `financial_data_lake_pipeline` | needs live rerun |
| 6 | Exposer API Gateway avec `/raw`, `/staging`, `/curated`, `/health`, `/stats` | Obligatoire | `api/main.py`, `api/routers/raw.py`, `api/routers/staging.py`, `api/routers/curated.py`, `api/routers/health.py`, `api/routers/stats.py` | `curl http://localhost:8000/{health,stats,raw,staging,curated}` (avec params adaptés) | implemented |
| 7 | Niveau avancé : POST `/ingest` | Optionnel | `api/routers/ingest.py` | `curl -X POST http://localhost:8000/ingest ...` | implemented |
| 8 | Niveau avancé : POST `/ingest_fast` | Optionnel | `api/routers/ingest_fast.py` | `curl -X POST http://localhost:8000/ingest_fast ...` | implemented |
| 9 | Niveau avancé : benchmark batch 1 et 100 | Optionnel | `scripts/benchmark_endpoints.py` | `python scripts/benchmark_endpoints.py --base-url http://localhost:8000 --period 5d --repeats 3 --output ...` | needs live rerun |
| 10 | Niveau avancé : amélioration > 30% | Optionnel | `scripts/benchmark_endpoints.py`, `api/routers/ingest.py`, `api/routers/ingest_fast.py` | Vérifier dans le rapport JSON `target_met = true` après exécution sur branche courante | needs live rerun |
| 11 | Livrables complets | Obligatoire | `README.md`, `livrables/RAPPORT_TECHNIQUE.md`, PDF à régénérer après validation | Vérifier les fichiers et leurs liens | needs live rerun |

## Notes de preuve

- Les tests unitaires ne valident pas l'exécution complète des services.
- La preuve finale attendue est : "tests off-line passants + exécution Docker + endpoints + benchmark rerunnable".
- Le fichier `livrables/benchmark_ingest_vs_ingest_fast.json` est historique (mesures passées) et n'est pas une preuve de la branche actuelle.
