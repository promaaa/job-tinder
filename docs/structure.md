# Structure du projet

- `frontend/` : client web/mobile (à définir, ex. Next.js ou Expo).
- `backend/` : API, logique métier, ingestion, IA.
  - `cli/` : outil CLI pour tester la logique (liste/offres, swipe, adaptation CV simulée).
  - `db/` : schémas SQL, migrations.
  - `ingestion/` : connecteurs et pipelines (à créer).
  - `ai/` : prompts, appels modèles, post-traitements (à créer).
  - `services/` : règles métier (matching, scoring, notifications) (à créer).
- `docs/` : documentation (schémas, runbooks, stratégie scraping).
- `infra/` : IaC, déploiement, secrets.
- `scripts/` : utilitaires DevOps / maintenance.
- `data/` : données locales (échantillons, cache JSON) pour la CLI.

## Flux minimal CLI (dev)
- Charger un échantillon d'offres dans `data/jobs.json`.
- Lister les offres, faire un swipe yes/no, stocker l'état dans `data/state.json`.
- Simuler l'adaptation de CV (stub IA) et tracer le résultat dans `data/cv_variants.json`.

## À venir
- API REST/GraphQL, auth, storage S3-compatible pour CV rendus.
- Ingestion connecteurs (APIs officielles en priorité, scraping en dernier recours).
- Orchestration candidatures (file d'attente, retrys, audit trail).
