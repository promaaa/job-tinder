#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.store import get_store


def render_job_line(job: Dict[str, object]) -> str:
    decision = job.get("decision", "pending")
    title = job.get("title") or "(titre inconnu)"
    company = job.get("company") or "?"
    location = job.get("location") or "?"
    return f"{job.get('id')} [{decision}] - {title} @ {company} ({location})"


def cmd_load_sample(_: argparse.Namespace):
    store = get_store()
    try:
        count = store.load_sample()
    except NotImplementedError:
        raise SystemExit("load-sample n'est pas disponible pour STORE=pg. Utilisez ingest.")
    except (FileNotFoundError, ValueError) as err:
        raise SystemExit(str(err))
    print(f"Chargé {count} offres depuis l'échantillon.")


def read_jobs_from_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Fichier introuvable: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit("Le fichier doit contenir une liste JSON d'offres")
    for item in data:
        if "id" not in item:
            raise SystemExit("Chaque offre doit avoir un champ 'id'")
    return data


def cmd_ingest(args: argparse.Namespace):
    new_jobs = read_jobs_from_file(Path(args.file))
    store = get_store()
    result = store.ingest(new_jobs, replace=args.replace)
    if result.get("mode") == "replace":
        print(f"Ingestion terminée: {result.get('total')} offres (remplacement)")
    else:
        print(
            f"Ingestion terminée: {len(new_jobs)} nouvelles entrées, total {result.get('total')} (dédup sur id)."
        )


def cmd_list(args: argparse.Namespace):
    store = get_store()
    jobs = store.list_jobs(
        status=args.status,
        query=args.query,
        company=args.company,
        tags=args.tag or [],
        remote=args.remote,
        emp_type=args.type,
    )
    if args.limit:
        jobs = jobs[: args.limit]
    if not jobs:
        print("Aucune offre à afficher.")
        return
    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
        return
    for job in jobs:
        print(render_job_line(job))


def cmd_swipe(args: argparse.Namespace):
    store = get_store()
    try:
        store.swipe(args.job_id, args.decision)
    except KeyError:
        raise SystemExit(f"Offre introuvable: {args.job_id}")
    print(f"Swipe enregistré: {args.job_id} -> {args.decision}")


def cmd_show(args: argparse.Namespace):
    store = get_store()
    try:
        job = store.get_job(args.job_id)
    except KeyError:
        raise SystemExit(f"Offre introuvable: {args.job_id}")
    if args.json:
        print(json.dumps(job, indent=2, ensure_ascii=False))
        return
    decision = job.get("decision", "pending")
    decided_at = job.get("decided_at")
    print(render_job_line(job))
    if decided_at:
        print(f"Décidé le: {decided_at}")
    print(f"Type: {job.get('employment_type')} | Remote: {job.get('is_remote')} | Seniority: {job.get('seniority')}")
    print(f"Publié le: {job.get('published_at')} | URL: {job.get('url')}")
    tags = ", ".join(job.get("tags") or [])
    if tags:
        print(f"Tags: {tags}")
    description = job.get("description") or ""
    print("Description:\n" + description)


def cmd_adapt_cv(args: argparse.Namespace):
    store = get_store()
    try:
        variant = store.adapt_cv(args.job_id, args.profile_label, args.model)
    except KeyError:
        raise SystemExit(f"Offre introuvable: {args.job_id}")
    print(f"CV adapté (stub) enregistré sous id {variant['id']} pour {args.job_id}")


def cmd_stats(_: argparse.Namespace):
    store = get_store()
    stats = store.stats()
    print(f"Total offres: {stats.get('total', 0)}")
    for key in ["yes", "no", "pending"]:
        print(f"{key}: {stats.get(key, 0)}")


def cmd_reset_state(args: argparse.Namespace):
    store = get_store()
    store.reset_state(args.with_cv)
    print("State réinitialisé (swipes/applications" + ("/cv" if args.with_cv else "") + ").")


def cmd_fetch(args: argparse.Namespace):
    """Fetch jobs from real sources."""
    from backend.ingestion.aggregator import JobAggregator
    from backend.ingestion.scheduler import JobScheduler
    
    store = get_store()
    
    # Determine sources
    if args.source:
        sources = [s.strip() for s in args.source.split(",")]
    else:
        sources = ["remoteok", "jobicy", "himalayas"]  # Free sources
    
    # Determine queries
    if args.query:
        queries = [args.query]
    else:
        queries = JobScheduler.DEFAULT_QUERIES[:3]  # Default: python, javascript, data
    
    async def do_fetch():
        aggregator = JobAggregator()
        all_jobs = []
        
        for query in queries:
            print(f"🔍 Recherche: {query}...")
            try:
                result = await aggregator.search(
                    query=query,
                    sources=sources,
                    limit_per_source=args.limit or 10,
                )
                jobs = result.get("jobs", [])
                all_jobs.extend(jobs)
                
                # Show stats per source
                for src, stats in result.get("sources", {}).items():
                    status = "✅" if stats.get("status") == "ok" else "❌"
                    print(f"   {status} {src}: {stats.get('count', 0)} jobs")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        # Deduplicate
        seen = set()
        unique = []
        for job in all_jobs:
            key = job.get("url") or f"{job.get('title')}-{job.get('company')}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        
        print(f"\n📊 Total: {len(unique)} offres uniques trouvées")
        
        if args.dry_run:
            print("(--dry-run: pas d'import)")
            return
        
        # Import to store
        existing = store.list_jobs(status="all", query=None, company=None, tags=[], remote="any", emp_type=None)
        existing_urls = {j.get("url") for j in existing if j.get("url")}
        
        new_jobs = []
        for job in unique:
            if job.get("url") not in existing_urls:
                job["id"] = store._generate_id() if hasattr(store, "_generate_id") else f"fetch-{len(new_jobs)}"
                job["decision"] = "pending"
                new_jobs.append(job)
        
        if new_jobs:
            all_jobs_final = existing + new_jobs
            if hasattr(store, "_save_jobs"):
                store._save_jobs(all_jobs_final)
            print(f"✅ Importé {len(new_jobs)} nouvelles offres (total: {len(all_jobs_final)})")
        else:
            print("ℹ️  Aucune nouvelle offre à importer")
    
    asyncio.run(do_fetch())


def cmd_sources(_: argparse.Namespace):
    """List available job sources."""
    from backend.ingestion.aggregator import JobAggregator
    
    aggregator = JobAggregator()
    sources = aggregator.list_sources()
    
    print("Sources disponibles:\n")
    print(f"{'Nom':<15} {'Status':<12} {'Gratuit':<8} Notes")
    print("-" * 60)
    
    for src in sources:
        name = src["name"]
        status = src["status"]
        free = "✅" if src.get("free") else "❌"
        note = src.get("note", "")
        
        status_icon = "🟢" if status == "available" else ("🟡" if status == "scraper" else "🔴")
        print(f"{name:<15} {status_icon} {status:<10} {free:<8} {note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI dev pour offres et swipes")
    sub = parser.add_subparsers(dest="command", required=True)

    p_load = sub.add_parser("load-sample", help="Charger les offres d'échantillon dans data/jobs.json")
    p_load.set_defaults(func=cmd_load_sample)

    p_ingest = sub.add_parser("ingest", help="Ingestion depuis un fichier JSON (liste d'offres)")
    p_ingest.add_argument("file", help="Chemin vers le fichier JSON")
    p_ingest.add_argument(
        "--replace",
        action="store_true",
        help="Remplacer complètement data/jobs.json au lieu de fusionner",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_list = sub.add_parser("list", help="Lister les offres avec filtres")
    p_list.add_argument(
        "--status",
        choices=["pending", "yes", "no", "all"],
        default="pending",
        help="Filtrer par statut de swipe",
    )
    p_list.add_argument("--query", help="Recherche texte (titre, entreprise, description, tags)")
    p_list.add_argument("--company", help="Filtrer par sous-chaîne d'entreprise")
    p_list.add_argument("--tag", action="append", help="Filtrer par tag (répéter l'option)")
    p_list.add_argument(
        "--remote",
        choices=["any", "true", "false"],
        default="any",
        help="Filtrer sur remote",
    )
    p_list.add_argument(
        "--type",
        choices=["full-time", "internship", "contract", "part-time"],
        help="Filtrer sur employment_type",
    )
    p_list.add_argument("--limit", type=int, help="Limiter le nombre de résultats")
    p_list.add_argument("--json", action="store_true", help="Sortie JSON complète")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Afficher le détail d'une offre")
    p_show.add_argument("job_id", help="Identifiant d'offre")
    p_show.add_argument("--json", action="store_true", help="Sortie JSON brute")
    p_show.set_defaults(func=cmd_show)

    p_swipe = sub.add_parser("swipe", help="Enregistrer un swipe yes/no")
    p_swipe.add_argument("job_id", help="Identifiant d'offre")
    p_swipe.add_argument("decision", choices=["yes", "no"], help="Décision")
    p_swipe.set_defaults(func=cmd_swipe)

    p_cv = sub.add_parser("adapt-cv", help="Simuler l'adaptation d'un CV (stub IA)")
    p_cv.add_argument("job_id", help="Identifiant d'offre")
    p_cv.add_argument("profile_label", help="Profil/étiquette du candidat")
    p_cv.add_argument("--model", default="gpt-4.1", help="Modèle IA ciblé (libellé informatif)")
    p_cv.set_defaults(func=cmd_adapt_cv)

    p_stats = sub.add_parser("stats", help="Statistiques sur les swipes")
    p_stats.set_defaults(func=cmd_stats)

    p_reset = sub.add_parser("reset-state", help="Réinitialiser swipes/applications (et CV si demandé)")
    p_reset.add_argument("--with-cv", action="store_true", help="Réinitialiser aussi les variantes de CV")
    p_reset.set_defaults(func=cmd_reset_state)

    # === FETCH: Real job sources ===
    p_fetch = sub.add_parser("fetch", help="Récupérer des offres depuis des sources réelles")
    p_fetch.add_argument("-q", "--query", help="Requête de recherche (ex: 'python developer')")
    p_fetch.add_argument("-s", "--source", help="Sources à utiliser (séparées par virgule: remoteok,jobicy,himalayas)")
    p_fetch.add_argument("-l", "--limit", type=int, default=10, help="Limite par source (défaut: 10)")
    p_fetch.add_argument("--dry-run", action="store_true", help="Afficher sans importer")
    p_fetch.set_defaults(func=cmd_fetch)

    p_sources = sub.add_parser("sources", help="Lister les sources de jobs disponibles")
    p_sources.set_defaults(func=cmd_sources)

    return parser


def main(argv: List[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
