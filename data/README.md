# Dataset financier versionné

`finance_dataset.csv` est la source fichier du pipeline.

## Contenu vérifié

- 732 lignes ;
- un ticker : AAPL ;
- première date : 3 janvier 2022 ;
- dernière date : 29 novembre 2024 ;
- aucune valeur manquante ;
- aucun doublon sur `(ticker, date)`.

Empreinte SHA-256 :

```text
490C50E6C83B4CE94222342DD5AC8E38D733318A46D614F3CD17C5C9BDB346FC
```

Cette empreinte permet de vérifier que le fichier utilisé correspond à celui décrit ici.

## Colonnes

`ticker` contient le symbole financier.

`date` contient la date de cotation au format `YYYY-MM-DD`.

`open`, `high`, `low` et `close` contiennent les cours d'ouverture, maximum, minimum et clôture.

`adj_close` contient le cours de clôture ajusté.

`volume` contient le nombre de titres échangés.

## Utilisation dans le pipeline

La tâche Airflow `ingest_file` charge ce fichier. Le code vérifie les colonnes obligatoires, normalise le ticker et la date, convertit les champs numériques et retire les lignes invalides.

Un CSV AAPL est écrit dans le bucket MinIO `raw-financial-data`. Les 732 lignes sont aussi indexées dans Elasticsearch avec la source `yfinance_file`.

Staging lit ensuite ces documents dans Elasticsearch et calcule les indicateurs techniques. Curated ajoute les anomalies, la tendance et le signal.

## Limite de période

Le fichier s'arrête au 29 novembre 2024. Le run de validation du 12 juillet 2026 ajoute une ligne API AAPL datée du 10 juillet 2026. Le pipeline trie les deux sources puis calcule le rendement avec la ligne précédente. Il compare donc ces deux dates éloignées.

Cette rupture explique le rendement de 32,86 % et l'anomalie `price_spike` sur la première ligne API AAPL du run final. Le dataset n'est pas mis à jour automatiquement dans Git. Les données récentes viennent uniquement de Yahoo Finance pendant l'exécution.
