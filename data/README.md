# Fichier finance_dataset.csv

`finance_dataset.csv` est la source fichier utilisée par `ingestion/ingest_file.py` et par le DAG Airflow.

Contenu vérifié :

- ticker : AAPL ;
- 732 lignes ;
- première date : 3 janvier 2022 ;
- dernière date : 29 novembre 2024 ;
- granularité : quotidienne ;
- colonnes : `ticker`, `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume` ;
- aucune valeur manquante ;
- aucun doublon sur `(ticker, date)`.

Le fichier vient du dépôt `FarhanAli97/Apple-AAPL-Stock-Data-1980-to-December-2024`, publié sous licence Apache 2.0 :

https://github.com/FarhanAli97/Apple-AAPL-Stock-Data-1980-to-December-2024

Nous conservons ce fichier dans le dépôt afin que l'ingestion fichier utilise toujours le même historique. Il reste distinct des données récupérées au moment de l'exécution avec `yfinance`.
