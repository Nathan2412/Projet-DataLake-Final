# Conformité au sujet

Ce document relie les demandes du sujet au fonctionnement vérifié du dépôt. Les résultats chiffrés viennent du run `documentation_verified_20260712T075000Z` exécuté le 12 juillet 2026 sur des volumes Docker vides.

## Deux sources de données

Le projet utilise un fichier CSV versionné et Yahoo Finance.

Le fichier contient 732 lignes AAPL du 3 janvier 2022 au 29 novembre 2024. L'ingestion Yahoo Finance traite quatorze tickers configurés. Le run final compte une ingestion fichier réussie et quatorze ingestions API réussies, sans erreur.

## Zone Raw

MinIO stocke les objets reçus. Elasticsearch indexe les lignes financières pour la recherche.

Après le run final, MinIO contient un objet dans `raw-financial-data` et quatorze objets dans `raw-api-data`. Elasticsearch contient 746 documents.

Preuves : réponses `/stats`, `/raw`, console MinIO et captures 03, 05 et 10.

## Zone Staging

Staging normalise les types, trie les dates, retire les doublons et calcule SMA, EMA, RSI, MACD, bandes de Bollinger, rendement et volatilité.

PostgreSQL contient 746 lignes Staging après le run. La clé `(ticker, date)` permet de rejouer le pipeline sans multiplier les lignes d'une date existante.

Preuves : route `/staging`, route `/staging/tickers` et capture 06.

## Zone Curated

Curated utilise Isolation Forest lorsque le ticker possède au moins 30 lignes. Le modèle travaille avec le rendement, la volatilité, le z-score du volume et le RSI. Le code ajoute le type d'anomalie, la tendance et le signal.

PostgreSQL contient 746 lignes Curated et 37 anomalies après le run final. Les 37 anomalies concernent AAPL, seul ticker qui possède assez d'historique lors de ce run.

Preuves : routes `/curated`, `/curated/anomalies/summary`, `/curated/signals` et capture 07.

## Orchestration Airflow

Le DAG `financial_data_lake_pipeline` contient sept tâches. Les deux ingestions s'exécutent en parallèle. Staging, Curated et le résumé s'exécutent ensuite dans cet ordre.

Le planning est `0 6 * * 1-5`. Le run final a terminé les sept tâches en 49,3 secondes.

Preuves : liste des DAGs, vue Grid et log `PIPELINE SUMMARY`, captures 08 et 09.

## API

FastAPI fournit onze routes métier pour contrôler les services, consulter les zones, lire les compteurs et lancer les deux modes d'ingestion manuelle.

Preuves : schéma OpenAPI et capture 01.

## Optimisation de l'ingestion

Le mode standard traite les tickers séquentiellement. Le mode rapide parallélise les téléchargements et les envois MinIO, groupe l'indexation Elasticsearch et utilise `execute_values` pour PostgreSQL.

Le benchmark versionné effectue trois répétitions pour 1 et 100 tickers. Le gain médian est de 7,77 % pour un ticker et de 88,33 % pour 100 tickers. Le seuil de 30 % est donc atteint uniquement sur le lot de 100.

## Reproductibilité

Le dépôt contient `pyproject.toml`, `.python-version` et `uv.lock` à la racine. `uv sync --frozen --all-groups` crée l'environnement local. FastAPI et Airflow utilisent les mêmes versions métier verrouillées.

Les anciens fichiers de dépendances séparés ont été retirés pour éviter deux sources de vérité. Les builds Docker exécutent un contrôle de compatibilité.

## Tests

La suite contient 14 tests réussis. Elle couvre les indicateurs, les tendances, les signaux, la préparation du CSV, la déduplication, les identifiants Raw, l'indexation simulée et le benchmark.

La validation Docker complète les tests unitaires avec les vraies connexions et un run Airflow.

## Commentaire sur les imports différés

Le DAG contient un commentaire près des fonctions PythonOperator. Il explique qu'Airflow réimporte régulièrement le fichier et que les dépendances lourdes restent chargées au moment de l'exécution des tâches. Ce choix réduit le travail de parsing et évite qu'une dépendance métier empêche la découverte du DAG.

## Organisation en package src

La recommandation `src` n'est pas implémentée. Le sujet précise que ce point est hors notation. Le projet reste organisé dans les dossiers `config`, `ingestion` et `transformation`. La documentation ne présente donc pas le dépôt comme un package Python réutilisable à l'extérieur.

## Points partiellement couverts

Le taux d'anomalies dépend du paramètre de contamination fixé à 5 % et du contenu chargé.

Le signal n'a pas été évalué sur une stratégie financière.

La continuité entre le CSV de 2024 et les données API de 2026 n'est pas corrigée. Cette rupture produit un rendement artificiel sur la première ligne API AAPL.

Les identifiants et le CORS sont adaptés à un environnement local de cours, pas à une exposition publique.
