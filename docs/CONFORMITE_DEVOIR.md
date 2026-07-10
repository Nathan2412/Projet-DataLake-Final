# Vérification par rapport au sujet

Sujet : Data Lakes & Data Integration, projet final EFREI 2025-2026.

Cette page relie les demandes du sujet aux fichiers et aux résultats observés le 10 juillet 2026.

## Data lake de bout en bout

Le flux exécuté est le suivant :

```text
Deux sources --> Raw --> Staging --> Curated --> API
```

Preuves dans le dépôt :

- ingestion : `ingestion/ingest_file.py` et `ingestion/ingest_api.py` ;
- transformation : `transformation/staging/transform_staging.py` et `transformation/curated/transform_curated.py` ;
- stockage : `docker-compose.yml` et `scripts/init_db.sql` ;
- orchestration : `airflow/dags/financial_pipeline_dag.py` ;
- exposition : `api/main.py` et `api/routers/`.

## Deux sources

Le projet utilise réellement :

- `data/finance_dataset.csv` comme source fichier versionnée ;
- Yahoo Finance par la bibliothèque `yfinance` comme source API.

L'exécution contrôlée a produit 200 objets dans le bucket fichier et 42 objets dans le bucket API.

## Trois zones

Raw utilise deux stockages :

- MinIO pour les objets CSV et JSON ;
- Elasticsearch pour les lignes brutes interrogeables.

Staging utilise la table PostgreSQL `staging_ohlcv`.

Curated utilise la table PostgreSQL `curated_analysis`.

Après l'exécution, Staging et Curated contenaient chacun 1 243 lignes.

## Pipeline Airflow

Le DAG `financial_data_lake_pipeline` exécute sept tâches. Le run `docs_20260710T171652Z` s'est terminé en 55 secondes avec sept statuts `success`.

La capture se trouve dans `docs/captures/airflow-execution.png`.

Le planning du code est `0 6 * * 1-5`, soit 6 h UTC du lundi au vendredi.

## API Gateway

FastAPI expose les routes demandées :

- `/raw` ;
- `/staging` ;
- `/curated` ;
- `/health` ;
- `/stats`.

Le projet ajoute aussi `/raw/objects`, `/staging/tickers`, `/curated/anomalies/summary`, `/curated/signals`, `/ingest` et `/ingest_fast`.

La capture Swagger se trouve dans `docs/captures/api-swagger.png`.

## Traitement avancé

La zone Curated applique Isolation Forest à quatre variables et enregistre le score, le booléen d'anomalie et son type. Elle calcule aussi une tendance et un signal.

L'état observé contenait 37 anomalies sur 1 243 lignes Curated.

## Ingestion optimisée

`/ingest` traite les téléchargements séquentiellement.

`/ingest_fast` utilise :

- huit threads pour les téléchargements ;
- huit threads pour les envois MinIO ;
- une écriture Elasticsearch groupée ;
- `execute_values` pour l'upsert PostgreSQL.

Le benchmark enregistré compare les deux routes avec trois répétitions.

Pour 100 tickers, la médiane passe de 104 825,65 ms à 12 230,36 ms. Le gain mesuré est 88,33 %. Les mesures et statuts de chaque appel sont dans `livrables/benchmark_ingest_vs_ingest_fast.json`.

## Documentation et captures

Le dépôt contient :

- le guide de lancement dans `README.md` ;
- le rapport dans `livrables/RAPPORT_TECHNIQUE.md` ;
- cette vérification ;
- la description du CSV dans `data/README.md` ;
- cinq captures dans `docs/captures/` ;
- deux PDF produits par `scripts/generate_pdf_deliverables.py`.

## Contrôles exécutés

```bash
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/stats
docker compose exec airflow-scheduler airflow dags trigger financial_data_lake_pipeline
PYTHONPATH=.:api .venv/bin/python -m pytest -q
```

Résultats :

- services PostgreSQL, MinIO et Elasticsearch en état `ok` ;
- run Airflow terminé avec sept tâches en succès ;
- endpoints Raw, Staging et Curated accessibles ;
- 12 tests réussis.
