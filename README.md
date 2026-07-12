# Data Lake financier

Projet final du cours Data Lakes & Data Integration, EFREI 2025-2026.

Auteurs :

- Artemiy Smogunov
- Nathan Smadja-Tubiana
- Patrice Ignongui

Le sujet est conservé dans `consignes/Data_Lakes_Projet_Final_EFREI_2025-2026.pdf`.

## Ce que fait le projet

Le projet collecte des cours financiers journaliers depuis deux sources :

- `data/finance_dataset.csv` pour la source fichier ;
- Yahoo Finance avec `yfinance` pour la source API.

Les données passent dans trois zones.

```text
CSV -----------|
               |--> Raw --> Staging --> Curated --> FastAPI
Yahoo Finance -|             Airflow orchestre le flux
```

Raw conserve les objets dans MinIO et les documents dans Elasticsearch. Staging nettoie les données et calcule les indicateurs financiers dans PostgreSQL. Curated ajoute la détection d'anomalies, la tendance et le signal. FastAPI donne accès aux trois zones.

## Organisation du dépôt

```text
api/                         application FastAPI et routes HTTP
airflow/dags/                définition du DAG
src/financial_data_lake/     package Python réutilisable
  config/                    configuration commune
  ingestion/                 ingestion fichier et Yahoo Finance
  transformation/staging/    nettoyage et indicateurs
  transformation/curated/    anomalies, tendances et signaux
data/                        fichier CSV versionné
scripts/                     initialisation, benchmark et génération PDF
tests/                       tests Python
docs/captures/               captures de l'exécution vérifiée
livrables/                   rapport Markdown et PDF
```

Le code métier est dans `src/financial_data_lake`. L'API et le DAG l'importent comme un package Python. Cette structure évite de recopier les fonctions dans plusieurs scripts et permet aussi de les importer depuis un autre projet après installation du package.

## Environnement Python avec uv

Les dépendances se trouvent dans `pyproject.toml`. Le fichier `uv.lock` conserve les versions exactes résolues.

Prérequis : Python 3.11 ou 3.12 et `uv`.

```bash
git clone https://github.com/Nathan2412/Projet-DataLake-Final.git
cd Projet-DataLake-Final
uv sync --frozen
uv run pytest -q
```

`uv sync --frozen` crée `.venv`, installe le package `financial-data-lake` depuis `src` et installe les dépendances de développement. Lors de notre vérification, uv a utilisé Python 3.11.15. Les 13 tests ont réussi.

## Lancement avec Docker Compose

Prérequis : Docker et Docker Compose.

```bash
docker compose up -d --build
```

Le premier démarrage crée les tables PostgreSQL, les buckets MinIO et l'utilisateur Airflow.

Contrôle des conteneurs et de l'API :

```bash
docker compose ps
curl http://localhost:8000/health
```

Interfaces locales :

- FastAPI : http://localhost:8000/docs
- Airflow : http://localhost:8080
- MinIO : http://localhost:9001

Les identifiants utilisés pour cet environnement local sont dans `docker-compose.yml`.

## Services Docker

PostgreSQL écoute sur le port 5432. Il contient les tables Staging, Curated, les journaux d'ingestion et la base interne d'Airflow.

MinIO écoute sur les ports 9000 et 9001. Les buckets `raw-financial-data` et `raw-api-data` conservent les objets Raw.

Elasticsearch 8.11.0 écoute sur le port 9200. L'index `raw_financial_events` contient les lignes Raw utilisées par l'API et la transformation Staging.

Airflow 2.8.1 écoute sur le port 8080. Le scheduler exécute le DAG et le webserver affiche les exécutions.

FastAPI écoute sur le port 8000. L'image copie `src/` dans `/app/src` et utilise ce chemin dans `PYTHONPATH`.

## Pipeline Airflow

Le DAG s'appelle `financial_data_lake_pipeline`. Il est planifié à 6 h UTC du lundi au vendredi.

```text
start
  |-- ingest_file --|
  |                 |--> transform_staging --> transform_curated --> log_summary --> end
  |-- ingest_api  --|
```

Les deux ingestions commencent en parallèle. Elles placent les tickers réussis dans XCom. Staging traite l'union de ces tickers. Curated traite ensuite les tickers réussis dans Staging.

![Liste des DAGs dans Airflow](docs/captures/airflow-dags.png)

Cette capture a été prise après la reconstruction de la stack. Elle montre le DAG chargé par Airflow. La commande `airflow dags list-import-errors` n'a retourné aucune erreur.

![Exécution du DAG](docs/captures/airflow-execution.png)

Cette capture correspond au run `docs_20260712T080930Z`. Le run a commencé à 08:10:15 UTC et s'est terminé à 08:11:00 UTC. Les sept tâches ont le statut `success`.

## Pourquoi les imports du DAG sont dans les tâches

Airflow lit souvent le fichier du DAG pour afficher son graphe. Les imports des modules métier restent donc dans les fonctions `task_*`. Les bibliothèques d'ingestion et de transformation sont chargées lorsque la tâche démarre, pas à chaque lecture du fichier. Un commentaire simple dans `airflow/dags/financial_pipeline_dag.py` explique ce choix.

## Zone Raw

L'ingestion fichier lit `data/finance_dataset.csv`. Elle vérifie les colonnes obligatoires, convertit les dates et les nombres, enlève les lignes incomplètes et garde la dernière ligne pour un doublon `(ticker, date)`.

L'ingestion API télécharge les cours avec `yfinance`. Elle conserve un JSON complet dans MinIO puis indexe les lignes dans Elasticsearch.

L'identifiant Elasticsearch suit la forme `source_ticker_date`. Une nouvelle ingestion de la même source, du même ticker et de la même date met à jour le document existant.

## Zone Staging

Staging relit les documents Elasticsearch par ticker. Le code trie les dates, enlève les doublons et ignore les lignes sans cours de clôture.

Les indicateurs calculés sont :

- SMA 20 et SMA 50 ;
- EMA 12 et EMA 26 ;
- RSI 14 ;
- MACD et ligne de signal ;
- bandes de Bollinger ;
- rendement journalier ;
- volatilité sur 20 périodes.

PostgreSQL utilise la clé unique `(ticker, date)`. Une nouvelle exécution met la ligne à jour au lieu de la dupliquer.

## Zone Curated

Curated lit les lignes Staging par ticker. Isolation Forest utilise le rendement journalier, la volatilité, le z-score du volume et le RSI. Le modèle utilise 100 arbres, `random_state=42` et une contamination de 5 %. Il ne démarre pas sous 30 lignes pour un ticker.

Les types d'anomalies sont attribués avec les règles du fichier `src/financial_data_lake/transformation/curated/transform_curated.py` :

- rendement sous -5 % : `flash_crash` ;
- rendement au-dessus de 5 % : `price_spike` ;
- z-score absolu du volume au-dessus de 3 : `volume_spike` ;
- volatilité au-dessus de 4 % : `high_volatility` ;
- autre point isolé : `unknown_anomaly`.

La tendance compare le cours, la SMA 20 et la SMA 50. Le signal combine le RSI et le MACD. Le signal vaut `buy`, `sell` ou `hold`. Il s'agit d'une sortie technique du projet, pas d'un conseil financier.

## API

![Routes Swagger](docs/captures/api-swagger.png)

La capture montre les routes réellement enregistrées dans FastAPI :

- `GET /health` contrôle PostgreSQL, MinIO et Elasticsearch ;
- `GET /stats` retourne les volumes des trois zones ;
- `GET /raw` et `GET /raw/objects` lisent la zone Raw ;
- `GET /staging` et `GET /staging/tickers` lisent Staging ;
- `GET /curated`, `/curated/anomalies/summary` et `/curated/signals` lisent Curated ;
- `POST /ingest` exécute le pipeline séquentiel ;
- `POST /ingest_fast` utilise des téléchargements et des écritures groupés.

Exemples :

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stats
curl "http://localhost:8000/raw?ticker=AAPL&limit=1"
curl "http://localhost:8000/staging?ticker=AAPL&limit=1"
curl "http://localhost:8000/curated?ticker=AAPL&limit=1"
```

## Exécution vérifiée après la migration vers src

Le 12 juillet 2026, nous avons reconstruit les images et les conteneurs avec `docker compose up -d --build --force-recreate`. Nous avons ensuite déclenché le run Airflow `docs_20260712T080930Z`.

![Résultats de l'exécution](docs/captures/resultats-execution.png)

Résultats relevés après le run :

- API : `ok` ;
- PostgreSQL : `ok` ;
- MinIO : `ok` ;
- Elasticsearch 8.11.0 : `ok` ;
- 271 objets MinIO, dont 201 objets fichier et 70 objets API ;
- 1 777 documents Elasticsearch ;
- 1 254 lignes Staging ;
- 1 254 lignes Curated ;
- 37 anomalies ;
- sept tâches Airflow réussies.

MinIO contient davantage d'objets après chaque exécution car les objets API sont horodatés. Elasticsearch utilise des identifiants stables et ne duplique pas une même combinaison source, ticker et date. Staging et Curated ont le même nombre de lignes car Curated enrichit chaque ligne Staging.

## Exemple AAPL dans les trois zones

![AAPL dans Raw, Staging et Curated](docs/captures/zones-aapl.png)

Les trois routes ont retourné une ligne AAPL datée du 10 juillet 2026.

Raw contient le cours reçu, le volume, la source et l'heure d'ingestion. Staging contient les indicateurs recalculés depuis l'historique disponible. Curated reprend la ligne Staging et ajoute l'anomalie, la tendance et le signal.

Dans le résultat observé, Curated classe la ligne comme `high_volatility`. La tendance vaut `bullish` et le signal reste `hold`. Les valeurs Raw et Staging ne sont pas strictement identiques car plusieurs sources peuvent exister pour la même date et Staging déduplique par `(ticker, date)` après lecture de l'index.

## Tests et vérifications

```bash
uv run pytest -q
sudo docker compose config -q
sudo docker compose exec -T airflow-scheduler airflow dags list-import-errors
```

Résultat final : 13 tests réussis et aucune erreur d'import Airflow.

Les tests couvrent les indicateurs, les tendances, les signaux, la préparation Staging, les identifiants Raw, le chargement du CSV, le benchmark et la présence du package sous `src`.

## Limites observées

Yahoo Finance est externe au projet. Une requête peut être lente ou ne retourner aucune ligne.

Le RSI demande quatorze observations. Un petit lot de cinq jours ne suffit pas pour calculer cet indicateur seul.

Isolation Forest ne s'exécute pas sous 30 lignes pour un ticker. La contamination de 5 % règle la proportion attendue de points isolés ; elle ne prouve pas qu'un mouvement de marché est une erreur.

Les signaux n'ont pas été évalués comme stratégie d'investissement.

Les mots de passe du fichier Compose servent uniquement à l'environnement local du cours.

## Livrables

- `livrables/RAPPORT_TECHNIQUE.md`
- `livrables/Documentation_Technique_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf`
- `livrables/Rapport_DataLake_Finance_Artemiy_Smogunov_Nathan_Smadja-Tubiana_Patrice_Ignongui.pdf`
- `docs/CONFORMITE_DEVOIR.md`

Régénération des PDF :

```bash
uv run python scripts/generate_pdf_deliverables.py
```
