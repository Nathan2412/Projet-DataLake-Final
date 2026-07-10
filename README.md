# Data Lake financier

Projet final du cours Data Lakes & Data Integration, EFREI 2025-2026.

Auteurs :

- Artemiy Smogunov
- Nathan Smadja-Tubiana
- Patrice Ignongui

Le sujet est disponible dans `consignes/Data_Lakes_Projet_Final_EFREI_2025-2026.pdf`.

## Fonctionnement du projet

Le projet collecte des cours financiers journaliers depuis deux sources :

- le fichier versionné `data/finance_dataset.csv` ;
- Yahoo Finance, interrogé avec la bibliothèque `yfinance`.

Les données passent par trois zones.

```text
Fichier CSV ---------|
                     |--> Raw --> Staging --> Curated --> FastAPI
Yahoo Finance -------|
                         Airflow orchestre ce flux
```

Raw conserve les données reçues dans MinIO et les indexe dans Elasticsearch. Staging nettoie les lignes et calcule les indicateurs techniques dans PostgreSQL. Curated détecte les anomalies, calcule une tendance et produit un signal simplifié dans PostgreSQL.

## Services lancés par Docker Compose

- PostgreSQL, port 5432 : tables Staging, Curated, journaux d'ingestion et base Airflow.
- MinIO, ports 9000 et 9001 : objets CSV et JSON de la zone Raw.
- Elasticsearch, port 9200 : documents Raw interrogeables.
- Airflow, port 8080 : planification et suivi du DAG.
- FastAPI, port 8000 : accès aux données et déclenchement manuel des pipelines.

## Lancement

Prérequis : Docker avec Docker Compose.

```bash
git clone https://github.com/Nathan2412/Projet-DataLake-Final.git
cd Projet-DataLake-Final
docker compose up -d
```

Le premier démarrage crée les tables PostgreSQL, les deux buckets MinIO et l'utilisateur Airflow.

Vérification :

```bash
docker compose ps
curl http://localhost:8000/health
```

Interfaces :

- documentation FastAPI : http://localhost:8000/docs
- Airflow : http://localhost:8080
- MinIO : http://localhost:9001

Les identifiants de l'environnement local sont définis dans `docker-compose.yml`.

## Pipeline Airflow

Le DAG s'appelle `financial_data_lake_pipeline`. Il est planifié à 6 h UTC du lundi au vendredi.

Ordre d'exécution :

```text
start
  |-- ingest_file --|
  |                 |--> transform_staging --> transform_curated --> log_summary --> end
  |-- ingest_api  --|
```

`ingest_file` et `ingest_api` s'exécutent en parallèle. Staging commence après la fin des deux ingestions. Curated commence après Staging.

![Liste des DAGs dans Airflow](docs/captures/airflow-dags.png)

La capture montre le seul DAG du projet, son planning `0 6 * * 1-5` et sept tâches récentes terminées avec succès.

![Exécution du DAG](docs/captures/airflow-execution.png)

Cette exécution manuelle s'est terminée en 55 secondes. Les tâches `start`, `ingest_file`, `ingest_api`, `transform_staging`, `transform_curated`, `log_summary` et `end` sont toutes en succès.

## API

La page Swagger regroupe les routes utilisées par le projet.

![Documentation Swagger de l'API](docs/captures/api-swagger.png)

Routes disponibles :

- `GET /health` vérifie PostgreSQL, MinIO et Elasticsearch.
- `GET /stats` compte les objets Raw, les documents Elasticsearch et les lignes PostgreSQL.
- `GET /raw` lit les documents Raw dans Elasticsearch.
- `GET /raw/objects` liste les objets MinIO.
- `GET /staging` lit les cours nettoyés et les indicateurs techniques.
- `GET /staging/tickers` donne les tickers et leurs plages de dates.
- `GET /curated` lit les anomalies, tendances et signaux.
- `GET /curated/anomalies/summary` regroupe les anomalies par ticker et par type.
- `GET /curated/signals` retourne les derniers signaux `buy` ou `sell`.
- `POST /ingest` exécute le pipeline séquentiel.
- `POST /ingest_fast` télécharge et écrit les données par lots parallèles.

Exemple de lecture :

```bash
curl "http://localhost:8000/raw?ticker=AAPL&limit=3"
curl "http://localhost:8000/staging?ticker=AAPL&limit=3"
curl "http://localhost:8000/curated?ticker=AAPL&limit=3"
```

Exemple d'ingestion manuelle :

```bash
curl -X POST http://localhost:8000/ingest_fast \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "tickers": ["AAPL", "MSFT", "NVDA"],
      "period": "5d",
      "run_staging": true,
      "run_curated": true
    }
  }'
```

## Passage dans les trois zones

![Exemple AAPL dans Raw, Staging et Curated](docs/captures/zones-aapl.png)

La capture suit la dernière ligne AAPL disponible au moment du test.

- Raw contient le cours reçu, le volume, la source et la date d'ingestion.
- Staging contient le même cours après normalisation, avec la moyenne mobile, le MACD, le rendement journalier et la volatilité.
- Curated ajoute le score d'anomalie, le type de tendance et le signal.

Pour cette ligne, `is_anomaly` vaut `false`, la tendance est `neutral` et le signal est `hold`. Le pipeline n'a donc pas classé ce point comme anormal et n'a produit ni signal d'achat ni signal de vente.

## Résultat de l'exécution contrôlée

Le 10 juillet 2026, nous avons lancé la stack puis déclenché le DAG `financial_data_lake_pipeline` avec l'identifiant `docs_20260710T171652Z`.

Résultat observé :

- état général de l'API : `ok` ;
- PostgreSQL : `ok` ;
- MinIO : `ok` ;
- Elasticsearch 8.11.0 : `ok` ;
- 242 objets dans MinIO, dont 200 objets issus du fichier et 42 objets issus de l'API ;
- 1 763 documents dans Elasticsearch ;
- 1 243 lignes dans Staging ;
- 1 243 lignes dans Curated ;
- 37 lignes marquées comme anomalies ;
- sept tâches Airflow terminées avec le statut `success`.

![Résumé de l'exécution](docs/captures/resultats-execution.png)

Les nombres Staging et Curated sont identiques parce que Curated enrichit chaque ligne Staging au lieu de filtrer le jeu de données. Les 37 anomalies viennent d'Isolation Forest configuré avec une contamination de 5 %. Ce nombre dépend donc du paramètre du modèle et du contenu chargé.

## Transformations Staging

Pour chaque ticker, le code lit les documents Elasticsearch, trie les dates, retire les doublons et ignore les lignes sans cours de clôture. Il calcule ensuite :

- SMA sur 20 et 50 périodes ;
- EMA sur 12 et 26 périodes ;
- RSI sur 14 périodes ;
- MACD et ligne de signal ;
- bandes de Bollinger sur 20 périodes ;
- rendement journalier ;
- volatilité glissante sur 20 périodes.

La clé unique `(ticker, date)` permet de rejouer une ingestion sans créer une nouvelle ligne pour la même date.

## Transformations Curated

Isolation Forest utilise quatre variables : rendement journalier, volatilité sur 20 périodes, z-score du volume et RSI. Le modèle ne se lance qu'à partir de 30 lignes pour un ticker. Sa contamination est fixée à 5 %.

Les types d'anomalies sont attribués par des règles visibles dans `transformation/curated/transform_curated.py` :

- baisse journalière inférieure à -5 % : `flash_crash` ;
- hausse supérieure à 5 % : `price_spike` ;
- z-score absolu du volume supérieur à 3 : `volume_spike` ;
- volatilité supérieure à 4 % : `high_volatility` ;
- autre point isolé : `unknown_anomaly`.

La tendance compare le cours, la SMA 20 et la SMA 50. Le signal combine le RSI et le croisement MACD. Il vaut `buy`, `sell` ou `hold`. Ce signal est une sortie technique du projet, pas une recommandation financière.

## Comparaison des deux ingestions

`scripts/benchmark_endpoints.py` compare `/ingest` et `/ingest_fast` avec des lots de 1 et 100 tickers. Le mode rapide utilise huit threads pour les téléchargements et les envois MinIO, une écriture groupée dans Elasticsearch et `execute_values` pour PostgreSQL.

Le fichier `livrables/benchmark_ingest_vs_ingest_fast.json` contient trois répétitions par mode et par taille de lot.

Résultat enregistré :

- lot de 1 ticker : 1 073,29 ms contre 989,86 ms, soit 7,77 % de gain ;
- lot de 100 tickers : 104 825,65 ms contre 12 230,36 ms, soit 88,33 % de gain.

Le gain est faible sur un seul ticker. Sur 100 tickers, les opérations réseau parallèles et les écritures groupées réduisent fortement le temps total.

## Tests

```bash
python -m pytest -q
```

Résultat vérifié : 12 tests réussis.

Les tests couvrent les calculs RSI, les tendances, les signaux, la préparation Staging, les identifiants Raw, le chargement du CSV et le calcul du benchmark.

## Limites observées

- Yahoo Finance est un service externe. La durée et le nombre de lignes disponibles changent selon sa réponse.
- Le mode rapide calcule les indicateurs Staging sur le lot téléchargé. Avec une période de cinq jours, le RSI 14 reste vide car le lot ne contient pas quatorze observations.
- Isolation Forest ne s'exécute pas sous 30 lignes pour un ticker.
- Les signaux Curated n'ont pas été évalués comme stratégie financière.
- Les identifiants présents dans Docker Compose sont prévus pour cet environnement local de cours.

## Documentation

- `livrables/RAPPORT_TECHNIQUE.md` décrit le fonctionnement et les résultats.
- `docs/CONFORMITE_DEVOIR.md` relie le projet aux demandes du sujet.
- `data/README.md` décrit le fichier CSV versionné.
- `docs/captures/` contient les captures utilisées dans la documentation.

Régénération des PDF :

```bash
.venv/bin/pip install -r scripts/requirements-docs.txt
.venv/bin/python scripts/generate_pdf_deliverables.py
```
