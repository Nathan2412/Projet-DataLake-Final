# Plan d'amélioration — Étape 4A (docs source)

## Statut global

- **Branche** : `improve/assignment-compliance`
- **Objectif de cette phase** : documents de conformité en français naturel, factuel, vérifiables.
- **État** : **RÉALISÉ** (README, conformité, rapport technique, plan).

## 1) Réécriture des documents sources

### 1.1 README (obligatoire)
- **But** : conserver uniquement les infos utiles à la correction.
- **Actions réalisées**
  - raccourcir le document (objectif < 240 lignes) et retirer les doublons,
  - conserver `groupe`, `lien devoir`, architecture, mapping exigences,
  - fixer les commandes d'installation/démarrage, services/ports, endpoints, exemples d'ingestion,
  - ajouter tests passés localement et rappel de rerun Docker complet.
- **Statut** : **Terminé**

### 1.2 Conformité du devoir
- **But** : matrice claire *mandatory / optional* avec preuve et statut.
- **Actions réalisées**
  - création de `docs/CONFORMITE_DEVOIR.md`,
  - ajout des preuves (`fichier`, `commande`, `statut`),
  - séparation claire entre « implémenté » et « needs live rerun ».
- **Statut** : **Terminé**

### 1.3 Rapport technique source
- **But** : rédaction technique concise (5-8 pages max), sans chiffres figés de benchmark.
- **Actions réalisées**
  - création de `livrables/RAPPORT_TECHNIQUE.md`,
  - couverture : problème, choix, raw/staging/curated, sources, Airflow, comparaison `/ingest` vs `/ingest_fast`, tests, limites, reproductibilité,
  - mention explicite que l'objectif 30% doit être revalidé après corrections.
- **Statut** : **Terminé**

## 2) Contrôle de conformité des écritures

### 2.1 Interdits et corrections
- **But** : supprimer les assertions non justifiables.
- **Actions réalisées**
  - suppression des affirmations sur gains exacts anciens,
  - suppression de toute valeur fixe de benchmark non rerun,
  - retrait des fausses promesses (cache Redis/vectorisation systématique).
- **Statut** : **Terminé**

### 2.2 Vérifications finales (post-édition)
- **But** : garantir que les textes citent des chemins réels.
- **Actions réalisées**
  - vérification des chemins clés dans le repo,
  - vérification de `stale claims` dans les docs modifiées,
  - validation des lignes et format markdown.
- **Statut** : **Terminé**

## 3) Vérifications restantes

- rerun Docker complet,
- exécution live de tous les endpoints,
- benchmark `/ingest` vs `/ingest_fast` sur la branche actuelle,
- capture des résultats dans le JSON de run de la branche.
