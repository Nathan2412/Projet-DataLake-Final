# Plan d’amélioration minimal — Conformité du devoir

## Objectif
Régler uniquement ce qui bloque la conformité du devoir sur la branche actuelle, avec le plus petit nombre de fichiers possible et sans refactor large.

## Non-objectifs
- Pas de mise en production.
- Pas d’authentification/authorisation supplémentaire.
- Pas de nouvelle infra (pas de nouveau service).
- Pas de nouvelle dépendance si on peut faire pareil avec la stdlib ou ce qui est déjà installé.
- Pas de gros refactor.


## Phase 1 — Tests + pipeline commun minimal

### Exigences couvertes
- `/raw`, `/staging`, `/curated`, `/health`, `/stats` restent disponibles.
- Les deux pipelines (`/ingest` et `/ingest_fast`) doivent produire des sorties cohérentes (même structure métier).
- Réduction de la divergence standard/fast détectée.
- Base de test minimale pour valider les futures modifications.

### Fichiers probables à toucher
- `tests/test_financial_logic.py` (ajout de tests d’équivalence entre pipelines)
- `ingestion/ingest_file.py` (si nécessaire pour exposer une logique commune exploitable)
- `api/routers/ingest.py`
- `api/routers/ingest_fast.py`
- `transformation/staging/transform_staging.py` (si adaptation de signature commune)
- `api/routers/raw.py` (si besoin pour aligner la sortie `_id`/provenance déjà testée après phase 2)

### Tâches (petites, RED → GREEN)
1. **Ajouter un test de non-régression de cohérence**
   - **RED** : test qui compare le JSON attendu de `/ingest` et `/ingest_fast` sur une petite fixture (tickers mockés).
   - Vérifier que `pipeline_steps.raw.success` > 0, même `tickers` traités, mêmes erreurs par ticker.
2. **Ajouter un test d’écart de comportement staging**
   - **RED** : test qui vérifie que pour un même DataFrame, les indicateurs requis existent et ne sortent pas d’alignement entre calcul standard et fast.
3. **Mettre en place un chemin commun minimal**
   - **GREEN** : créer une fonction commune légère (sans abstractions superflues) utilisée par `/ingest` et `/ingest_fast` pour préparer la liste de tickers, les options et le format de retour.
4. **Aligner la propagation d’erreur minimale**
   - **GREEN** : les deux endpoints renvoient le même format d’erreurs (`step`, `ticker`, `error`) pour un même cas d’échec.

### Critères de sortie (phase 1)
- Les tests existent et passent.
- Les différences de base entre standard et fast sont isolées au niveau des optimisations (parallélisme/cache).
- Aucun changement de contrat public non demandé (`/raw`, `/staging`, `/curated`, `/health`, `/stats` inchangés).


## Phase 2 — Provenance + cache

### Exigences couvertes
- Corriger la perte de provenance constatée.
- Cacher plus proprement sans casser les runs (problème de cache qui “sautait”).
- Supprimer les collisions Elasticsearch (`_id`) quand date + source ne sont pas suffisantes.
- Mieux tracer la source/ingestion pour audit.

### Fichiers probables à toucher
- `api/routers/ingest.py`
- `api/routers/ingest_fast.py`
- `api/routers/raw.py`
- `ingestion/ingest_api.py`
- `ingestion/ingest_file.py`
- `tests/test_financial_logic.py`

### Tâches (petites, RED → GREEN)
1. **Corriger les IDs Elasticsearch conflictuels**
   - **RED** : test qui envoie le même ticker/date avec deux variantes de source et exige deux docs distincts.
   - **GREEN** : `_id` devient unique (`<source>:<ticker>:<date>:<ingest_mode>`) dans les chemins raw pertinents.
2. **Ajouter la provenance dans les docs bruts et indexés**
   - **RED** : test qui vérifie présence de champs `pipeline`, `ingested_by`, `ingested_run_id`, `source`.
   - **GREEN** : chaque doc raw contient un blob de provenance minimal, stable et non bloquant.
3. **Cache déterministe dans `/ingest_fast`**
   - **RED** : test qui force un appel double avec `use_cache=true` puis vérifie la conservation de la réponse et une logique de cache lisible.
   - **GREEN** : clé Redis claire et stable (ticker, period, interval), fallback gracieux si Redis indisponible.
4. **Propagation homogène vers les couches suivantes**
   - **RED** : test qui vérifie qu’un même run est traçable de `/ingest_fast` vers staging/curated quand la route passe par `run_staging`/`run_curated`.
   - **GREEN** : la provenance minimale suit le flux dans les tables/sorties pertinentes.

### Critères de sortie (phase 2)
- Plus de collision brute `ticker_date` entre variantes.
- Le cache est réutilisable mais ne masque pas la trace d’un run.
- Les logs/documents permettent de dire “qui a produit quoi et quand” sans dépendre de la mémoire de l’opération.


## Phase 3 — Benchmark reproductible simple

### Exigences couvertes
- Benchmark actuel : actuellement un run unique et chiffres parfois incohérents.
- Exiger des comparaisons stables `/ingest` vs `/ingest_fast` sur batch 1 et batch 100.
- Reproduire sans bruit inutile.

### Fichiers probables à toucher
- `scripts/benchmark_endpoints.py`
- `scripts/init_db.sql` (si besoin d’une table de logs minimale pour répétition propre)
- `tests/test_financial_logic.py` (test du helper de benchmark)
- `README.md` (référencer la commande, si autorisé dans le plan d’exécution)

### Tâches (petites, RED → GREEN)
1. **Rendre le benchmark déterministe (même payload, même ordre)**
   - **RED** : test d’un helper qui vérifie que deux runs successifs avec mêmes paramètres produisent une structure comparable (différence de temps tolérée mais statut format stable).
   - **GREEN** : le script enregistre `cache_enabled`, `python_version`, `host`, `sample_tickers`, `period`, `batch_size`, `run_id`.
2. **Capturer au moins 2 runs (1 et 100) systématiques**
   - **RED** : test que la sortie contient bien deux blocs `batch_size:1` et `batch_size:100`.
   - **GREEN** : sortie JSON écrite avec horodatage et méta-stats, plus ratio gain calculé.
3. **Écrire un critère de passage automatique**
   - **RED** : test qui échoue si `fast_gain_pct <= 30` pour l’un des deux batchs.
   - **GREEN** : sortie claire et stable pour l’évaluation visuelle ou script CI locale.
4. **Éliminer les lectures ambiguës**
   - **RED** : test que `ingest` et `ingest_fast` sont lancés avec des options identiques (`run_staging=True/False`, `run_curated=True/False`, `use_cache=False` par défaut pour benchmark).
   - **GREEN** : le benchmark n’utilise qu’un seul chemin de configuration.

### Critères de sortie (phase 3)
- On a un fichier `benchmarks/benchmark_results.json` prévisible et facile à relire.
- Chaque exécution couvre au minimum batch 1 et 100.
- La comparaison `/ingest` vs `/ingest_fast` est explicite, mesurable, et ne dépend pas d’un run artisanal unique.


## Phase 4 — Docs “humanisées” + vérification

### Exigences couvertes
- Déclarer clairement ce qui a été corrigé sans jargon.
- Remplir la demande `docs/build` demandée par l’audit.
- Ajouter une vérification simple pour valider que l’ensemble est bien “à jour”.

### Fichiers probables à toucher
- `docs/PLAN_AMELIORATION.md` (ce fichier)
- `README.md` (petits ajouts d’utilisation benchmark/tests)
- `scripts/build_checks.sh` *(si nécessaire, sinon pas de nouveau fichier)*

### Tâches (petites, RED → GREEN)
1. **Rédiger une section “comment valider” en français simple**
   - **RED** : test de lecture (humain) qui ne comprend pas 2 secondes de jargon technique.
   - **GREEN** : un plan de vérification avec commandes courtes et résultats attendus.
2. **Ajouter checklist de conformité**
   - **RED** : check-list trop longue ou floue qui mélange infra/prod et code.
   - **GREEN** : checklist claire : endpoints, ingestion std/fast, provenance, benchmark 1 et 100, score +30%.
3. **Ajouter la preuve d’exécution minimale**
   - **RED** : le plan n’indique pas ce qui a été lancé.
   - **GREEN** : section “Vérifications réalisées” avec 3–5 commandes minimum et attendu.

### Critères de sortie (phase 4)
- Docs lisibles par un étudiant, pas par consultant.
- Vérification reproductible claire avant soumission.
- Un point par phase dans `docs/PLAN_AMELIORATION.md` indique “à faire / fait / bloqué”.


## Plan de vérification globale (avant merge)

- `python -m unittest discover -s tests` (ou commande projet équivalente)
- `python scripts/benchmark_endpoints.py --base-url http://localhost:8000 --period 5d`
- `python -m json.tool benchmarks/benchmark_results.json` (ou vérification équivalente)
- Un appel manuel rapide à `/raw`, `/staging`, `/curated`, `/health`, `/stats`

## Sortie attendue de cette étape
Ce document uniquement. Aucun changement applicatif.
Le commit doit montrer :
- plan lisible, prêt à être exécuté,
- phases en 4 au maximum,
- chaque phase avec exigences, fichiers probables, RED/GREEN, et critères de sortie.
