# CLI développeur

Outil léger pour manipuler les offres en local (swipe, stats, stub IA) sans backend.

## Prérequis
- Python 3.10+
- Aucune dépendance externe (stdlib uniquement)

## Installation rapide
```sh
cd /Users/user/Documents/code/job-tinder
python backend/cli/main.py -h
```

## Données
- `data/sample_jobs.json` : échantillon fourni.
- `data/jobs.json` : offres actives utilisées par le CLI.
- `data/state.json` : swipes et candidatures locales.
- `data/cv_variants.json` : variantes de CV simulées (stub IA).

## Commandes

### Charger l'échantillon
```sh
python backend/cli/main.py load-sample
```

### Ingestion depuis un fichier JSON
```sh
python backend/cli/main.py ingest ./data/mon_feed.json       # fusionne avec dédup sur id
python backend/cli/main.py ingest ./data/mon_feed.json --replace  # remplace entièrement jobs.json
```

### Lister (avec filtres)
```sh
python backend/cli/main.py list --status pending --query python --tag docker --remote true --type full-time
```

### Voir le détail d'une offre
```sh
python backend/cli/main.py show job-001
```

### Swiper
```sh
python backend/cli/main.py swipe job-001 yes
```

### Adapter un CV (stub)
```sh
python backend/cli/main.py adapt-cv job-001 "Backend Python" --model gpt-4.1
```

### Stats
```sh
python backend/cli/main.py stats
```

### Reset
```sh
python backend/cli/main.py reset-state --with-cv
```

## Next steps
- Brancher un stockage réel (PostgreSQL + ORM) et des connecteurs d'ingestion.
- Remplacer le stub IA par un appel modèle et stocker les rendus (S3-compatible).
- Ajouter des tests unitaires sur les filtres et la sérialisation.
