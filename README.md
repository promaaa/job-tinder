# Job Tinder (prototype)

Centralise des offres, swipe yes/no, stub d'adaptation de CV via CLI et API FastAPI.

## Structure
- `backend/cli`: outil local (list, swipe, adapt-cv stub, ingest JSON).
- `backend/api`: FastAPI exposant jobs/swipes/adapt/ingest.
- `data/`: stockage JSON par défaut (surchargé via `JOB_TINDER_ROOT`).
- `docs/`: schémas, stratégie ingestion/scraping, usage CLI.

## Prérequis
- Python 3.11+
- (Optionnel) `JOB_TINDER_ROOT` pour isoler les données (tests ou sandboxes)

## Installation
```sh
cd /Users/user/Documents/code/job-tinder
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
# ou via Makefile
make install
```

## CLI
Voir `docs/cli.md` pour tous les exemples.
```sh
python backend/cli/main.py load-sample
python backend/cli/main.py list --status pending
python backend/cli/main.py list --limit 10 --json
python backend/cli/main.py swipe job-001 yes
python backend/cli/main.py adapt-cv job-001 "Backend" --model gpt-4.1
python backend/cli/main.py ingest ./data/mon_feed.json --replace
```

## API (dev)
```sh
export JOB_TINDER_ROOT=$PWD  # optionnel
uvicorn backend.api.app:app --reload
# endpoints: /health, /jobs, /jobs/{id}, /swipes (POST), /adapt-cv (POST), /ingest (POST), /stats
# ou
make api
```

UI: une interface légère est servie sur `/ui` (liste, recherche, swipe yes/no, stats live, modal détail + bouton "Adapt CV" qui appelle `/adapt-cv` avec profil/modèle) quand `frontend/` est présent.

Store:
- Par défaut `STORE=json` (fichiers dans `data/`).
- Pour Postgres: exporter `STORE=pg` et `PG_DSN`/`DATABASE_URL` (voir .env.example), appliquer le schéma (`python -m backend.db.pg --init-schema`), puis `load-sample` ou `ingest`.

## Tests
```sh
/Users/user/Documents/code/job-tinder/.venv/bin/python -m pytest backend/tests
# ou
make test
```

## Postgres (optionnel)
Option 1 — Docker Compose prêt à l'emploi :
```sh
make pg-up                                  # démarre Postgres 15 (user/pass/db: jobtinder/jobtinder/job_tinder)
make pg-init                                # applique docs/schema.sql (via PG_DSN par défaut)
make pg-seed                                # charge data/sample_jobs.json
make pg-list                                # visualise les offres
make pg-reset                               # drop volume + redémarrage (réinitialise la base)
STORE=pg PG_DSN=postgres://jobtinder:jobtinder@localhost:5432/job_tinder make api  # API en mode pg
```
Stopper la base: `make pg-down`. Logs: `make pg-logs`.

Option 2 — Postgres existant:
1) Exporter `PG_DSN` ou `DATABASE_URL` (ex: `postgres://user:pass@localhost:5432/job_tinder`).
2) Appliquer le schéma et (optionnel) seeder depuis l'échantillon :
```sh
python -m backend.db.pg --init-schema
python -m backend.db.pg --seed data/sample_jobs.json
```
3) Lister rapidement ce qui est en base :
```sh
python -m backend.db.pg --list
```
4) Une fois le schéma appliqué, `python backend/cli/main.py load-sample` fonctionne aussi en mode pg (remplace les offres et swipes associés via TRUNCATE).

### Basculer JSON ↔ PG rapidement
1) Choisir le store:
	- JSON : `export STORE=json`
	- Postgres : `export STORE=pg` + `export PG_DSN=postgres://user:pass@localhost:5432/job_tinder`
2) (PG uniquement) appliquer le schéma une fois: `python -m backend.db.pg --init-schema`
3) Charger des données:
	- JSON : `python backend/cli/main.py load-sample`
	- PG : `python backend/cli/main.py load-sample` (TRUNCATE + reload) ou `python backend/cli/main.py ingest fichier.json`
4) API/CLI utiliseront automatiquement le store choisi. Optionnel: `JOB_TINDER_ROOT` pour isoler les fichiers JSON (tests/sandboxes).

## Notes
- Stockage par défaut: fichiers JSON; Postgres en option via `STORE=pg` + `PG_DSN`.
- Adaptation de CV est un stub; à remplacer par un appel modèle + stockage objet.
- Ingestion: privilégier APIs/feeds; voir `docs/ingestion.md` pour la stratégie anti-scraping.
