#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
import html

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.store import get_store

console = Console()

def render_decision_icon(decision: str) -> str:
    if decision == "yes":
        return "✅"
    elif decision == "no":
        return "❌"
    return "⏳"

def cmd_load_sample(_: argparse.Namespace):
    store = get_store()
    try:
        count = store.load_sample()
    except NotImplementedError:
        console.print("[red]load-sample n'est pas disponible pour STORE=pg. Utilisez ingest.[/red]")
        raise SystemExit(1)
    except (FileNotFoundError, ValueError) as err:
        console.print(f"[red]Erreur:[/red] {err}")
        raise SystemExit(1)
    console.print(f"[green]Chargé {count} offres depuis l'échantillon.[/green]")


def read_jobs_from_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        console.print(f"[red]Fichier introuvable: {path}[/red]")
        raise SystemExit(1)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        console.print("[red]Le fichier doit contenir une liste JSON d'offres[/red]")
        raise SystemExit(1)
    for item in data:
        if "id" not in item:
            console.print("[red]Chaque offre doit avoir un champ 'id'[/red]")
            raise SystemExit(1)
    return data


def cmd_ingest(args: argparse.Namespace):
    new_jobs = read_jobs_from_file(Path(args.file))
    store = get_store()
    result = store.ingest(new_jobs, replace=args.replace)
    if result.get("mode") == "replace":
        console.print(f"[green]Ingestion terminée:[/green] {result.get('total')} offres (remplacement)")
    else:
        console.print(
            f"[green]Ingestion terminée:[/green] {len(new_jobs)} nouvelles entrées, total {result.get('total')} (dédup sur id)."
        )


def cmd_list(args: argparse.Namespace):
    store = get_store()
    
    # Sorting logic (simple in-memory sort for now, ideally pushed to store)
    jobs = store.list_jobs(
        status=args.status,
        query=args.query,
        company=args.company,
        tags=args.tag or [],
        remote=args.remote,
        emp_type=args.type,
    )
    
    # Apply sort
    if args.sort == "date":
        jobs.sort(key=lambda x: str(x.get("published_at") or ""), reverse=True)
    elif args.sort == "salary":
        # Crude sort by max salary if available
        jobs.sort(key=lambda x: x.get("salary_max") or 0, reverse=True)
    
    if args.limit:
        jobs = jobs[: args.limit]

    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
        return

    if not jobs:
        console.print("Aucune offre à afficher.")
        return

    table = Table(title=f"Offres ({len(jobs)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Titre", style="magenta")
    table.add_column("Entreprise", style="green")
    table.add_column("Loc", style="yellow")
    table.add_column("Remote", justify="center")
    table.add_column("Salaire")

    for job in jobs:
        decision = job.get("decision", "pending")
        salary = job.get("salary") or "-"
        if not salary and job.get("salary_min"):
             salary = f"{job.get('salary_min')} - {job.get('salary_max')}"
        
        table.add_row(
            job.get("id")[:8],
            render_decision_icon(decision),
            html.unescape(job.get("title") or "N/A"),
            html.unescape(job.get("company") or "N/A"),
            job.get("location") or "N/A",
            "Yes" if job.get("is_remote") else "No",
            str(salary)[:20]
        )

    console.print(table)


def cmd_swipe(args: argparse.Namespace):
    store = get_store()
    try:
        store.swipe(args.job_id, args.decision)
    except KeyError:
        console.print(f"[red]Offre introuvable: {args.job_id}[/red]")
        raise SystemExit(1)
    console.print(f"[green]Swipe enregistré:[/green] {args.job_id} -> {args.decision}")


def cmd_show(args: argparse.Namespace):
    store = get_store()
    try:
        job = store.get_job(args.job_id)
    except KeyError:
        console.print(f"[red]Offre introuvable: {args.job_id}[/red]")
        raise SystemExit(1)
    
    if args.json:
        print(json.dumps(job, indent=2, ensure_ascii=False))
        return

    decision = job.get("decision", "pending")
    
    # Header info
    info = f"""
    [bold]Entreprise:[/bold] {job.get('company')}
    [bold]Lieu:[/bold] {job.get('location')}
    [bold]Type:[/bold] {job.get('employment_type')} | [bold]Remote:[/bold] {job.get('is_remote')}
    [bold]Salaire:[/bold] {job.get('salary') or 'Non spécifié'}
    [bold]Publié le:[/bold] {job.get('published_at')}
    [bold]Décision:[/bold] {decision} {render_decision_icon(decision)}
    [bold]Tags:[/bold] {', '.join(job.get('tags') or [])}
    [bold]URL:[/bold] {job.get('url')}
    """
    
    console.print(Panel(info, title=f"{job.get('title')} ({job.get('id')})", expand=False))
    
    description = job.get("description") or "Pas de description."
    console.print(Panel(Markdown(description), title="Description"))

def cmd_session(args: argparse.Namespace):
    """Interactive session to swipe pending jobs."""
    store = get_store()
    
    # Get pending jobs
    jobs = store.list_jobs(
        status="pending",
        query=args.query,
        company=None,
        tags=args.tag or [],
        remote=args.remote,
        emp_type=None,
    )
    
    if not jobs:
        console.print("[yellow]Aucune offre en attente à traiter.[/yellow]")
        return
        
    console.print(f"[bold green]Démarrage de la session: {len(jobs)} offres en attente.[/bold green]")
    console.print("Commandes: [bold]y[/bold]=yes, [bold]n[/bold]=no, [bold]s[/bold]=skip, [bold]q[/bold]=quit\n")
    
    swiped_count = 0
    
    for job in jobs:
        console.clear()
        console.rule(f"[bold cyan]{job.get('title')}[/bold cyan] @ {job.get('company')}")
        
        # Display simplified details
        details = (
            f"Location: {job.get('location')} | Remote: {job.get('is_remote')}\n"
            f"Salary: {job.get('salary') or 'N/A'} | Type: {job.get('employment_type')}\n"
            f"Tags: {', '.join(job.get('tags')[:5])}\n"
            f"Link: {job.get('url')}"
        )
        console.print(details)
        console.print("-" * 30)
        
        # Show first 500 chars of description
        desc = job.get("description", "")[:500] + "..."
        console.print(desc)
        console.print("\n")
        
        while True:
            choice = Prompt.ask("Action", choices=["y", "n", "s", "q"], default="s")
            
            if choice == "q":
                console.print(f"Session terminée. {swiped_count} offres traitées.")
                return
            
            if choice == "s":
                console.print("[dim]Skipped[/dim]")
                break
                
            if choice in ["y", "n"]:
                decision = "yes" if choice == "y" else "no"
                store.swipe(job.get("id"), decision)
                console.print(f"[bold]{decision.upper()}[/bold] enregistré.")
                swiped_count += 1
                break

    console.print(f"[bold green]Toutes les offres ont été traitées! ({swiped_count} swipes)[/bold green]")


def cmd_adapt_cv(args: argparse.Namespace):
    store = get_store()
    try:
        variant = store.adapt_cv(args.job_id, args.profile_label, args.model)
    except KeyError:
        console.print(f"[red]Offre introuvable: {args.job_id}[/red]")
        raise SystemExit(1)
    console.print(f"[green]CV adapté (stub) enregistré:[/green] id {variant['id']}")


def cmd_stats(_: argparse.Namespace):
    store = get_store()
    stats = store.stats()
    
    table = Table(title="Statistiques")
    table.add_column("Statut")
    table.add_column("Nombre", justify="right")
    
    table.add_row("Total", str(stats.get('total', 0)))
    table.add_row("Yes", str(stats.get('yes', 0)), style="green")
    table.add_row("No", str(stats.get('no', 0)), style="red")
    table.add_row("Pending", str(stats.get('pending', 0)), style="yellow")
    
    console.print(table)


def cmd_reset_state(args: argparse.Namespace):
    store = get_store()
    store.reset_state(args.with_cv)
    console.print("[yellow]State réinitialisé (swipes/applications" + ("/cv" if args.with_cv else "") + ").[/yellow]")


def cmd_fetch(args: argparse.Namespace):
    """Fetch jobs from real sources."""
    from backend.ingestion.scheduler import JobScheduler
    
    store = get_store()
    
    # Determine sources
    sources = [s.strip() for s in args.source.split(",")] if args.source else None
    
    # Determine queries
    queries = [args.query] if args.query else None
    
    async def do_fetch():
        scheduler = JobScheduler()
        
        with console.status("[bold green]Recherche en cours...[/bold green]") as status:
            summary = await scheduler.fetch_all(
                store=store if not args.dry_run else None,
                override_queries=queries,
                override_sources=sources,
                limit=args.limit or 10
            )
        
        console.print(f"\n[bold]📊 Résultat de la recherche:[/bold]")
        console.print(f"Total brut: {summary['total_fetched']}")
        console.print(f"Uniques: {summary['unique_jobs']}")
        
        if not args.dry_run:
            console.print(f"[green]✅ Sauvegardé: {summary['saved_to_store']} nouveaux jobs[/green]")
        else:
             console.print("[yellow]ℹ️  Mode dry-run: pas de sauvegarde[/yellow]")

        console.print("\n[bold]Détails par source:[/bold]")
        for source, stats in summary['sources'].items():
             icon = "❌" if stats['errors'] > 0 else "✅"
             console.print(f"   {icon} {source}: {stats['total']} jobs")

    asyncio.run(do_fetch())


def cmd_sources(_: argparse.Namespace):
    """List available job sources."""
    from backend.ingestion.aggregator import JobAggregator
    
    aggregator = JobAggregator()
    sources = aggregator.list_sources()
    
    table = Table(title="Sources disponibles")
    table.add_column("Nom", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Gratuit", justify="center")
    table.add_column("Notes")

    for src in sources:
        name = src["name"]
        status = src["status"]
        free = "✅" if src.get("free") else "❌"
        note = src.get("note", "")
        
        status_icon = "🟢" if status == "available" else ("🟡" if status == "scraper" else "🔴")
        table.add_row(name, f"{status_icon} {status}", free, note)
    
    console.print(table)


# --- CONTACTS & OUTREACH COMMANDS ---

def cmd_contacts_load(_: argparse.Namespace):
    store = get_store()
    try:
        count = store.load_contacts_sample()
        console.print(f"[green]Chargé {count} contacts exemples.[/green]")
    except AttributeError:
         # Fallback if method not on PgStore yet
         console.print("[red]Not implemented for this store.[/red]")

def cmd_contacts_import(args: argparse.Namespace):
    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]Fichier introuvable: {path}[/red]")
        return

    store = get_store()
    contacts = []
    
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                contacts = data
            else:
                console.print("[red]Le JSON doit contenir une liste.[/red]")
                return
        elif path.suffix.lower() == ".csv":
            import csv
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                contacts = list(reader)
        else:
            console.print("[red]Format non supporté (utilisez .json ou .csv)[/red]")
            return
    except Exception as e:
        console.print(f"[red]Erreur de lecture: {e}[/red]")
        return

    count = 0
    for c in contacts:
        # Basic validation
        if not c.get("name") or not c.get("email"):
            continue
            
        store.add_contact(c)
        count += 1
    
    console.print(f"[green]Importé {count} contacts depuis {path.name}.[/green]")

def cmd_contacts_list(_: argparse.Namespace):
    store = get_store()
    try:
        contacts = store.list_contacts()
    except AttributeError:
        console.print("[red]Store does not support contacts.[/red]")
        return
        
    if not contacts:
        console.print("Aucun contact.")
        return
        
    table = Table(title=f"Contacts ({len(contacts)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Company", style="green")
    table.add_column("Role", style="magenta")
    table.add_column("Email", style="blue")
    
    for c in contacts:
        table.add_row(
            c.get("id"),
            c.get("name"),
            c.get("company"),
            c.get("role"),
            c.get("email")
        )
    console.print(table)

def cmd_outreach_generate(args: argparse.Namespace):
    from backend.outreach.generator import EmailGenerator
    store = get_store()
    
    try:
        contact = store.get_contact(args.contact_id)
        profile = store.get_cv_profile()
    except KeyError:
        console.print(f"[red]Contact introuvable: {args.contact_id}[/red]")
        return
    except AttributeError:
        console.print("[red]Store not ready.[/red]")
        return
        
    generator = EmailGenerator()
    content = generator.generate(contact, profile)
    
    attachments = []
    # Check for CV file in profile
    uploaded_cv = profile.get("uploaded_file")
    if uploaded_cv and "path" in uploaded_cv:
        cv_path = uploaded_cv["path"]
        if Path(cv_path).exists():
             choice = Prompt.ask(f"Attacher le CV ({uploaded_cv['filename']}) ?", choices=["y", "n"], default="y")
             if choice == "y":
                 attachments.append(cv_path)
    
    msg = store.create_outreach(
        contact_id=args.contact_id,
        subject=content["subject"],
        body=content["body"],
        generated_via="stub-ai",
        attachments=attachments
    )
    
    console.print(Panel(content["body"], title=f"Draft created: {msg['id']} - {content['subject']}"))
    if attachments:
        console.print(f"[blue]📎 Attachments:[/blue] {', '.join([Path(p).name for p in attachments])}")
    console.print(f"[green]Message draft stored as {msg['id']}[/green]")

def cmd_outreach_list(_: argparse.Namespace):
    store = get_store()
    try:
        msgs = store.list_outreach()
    except AttributeError:
        return
        
    table = Table(title="Outreach Messages")
    table.add_column("ID", style="cyan")
    table.add_column("To", style="bold")
    table.add_column("Subject")
    table.add_column("Status", justify="center")
    
    for m in msgs:
        status_style = "green" if m["status"] == "sent" else "yellow"
        table.add_row(
            m["id"],
            f"{m.get('contact_name')} ({m.get('company')})",
            m.get("subject"),
            f"[{status_style}]{m['status']}[/{status_style}]"
        )
    console.print(table)

def cmd_outreach_send(args: argparse.Namespace):
    from backend.outreach.sender import EmailSender
    store = get_store()
    
    # Get message
    msgs = store.list_outreach()
    msg = next((m for m in msgs if m["id"] == args.msg_id), None)
    
    if not msg:
        console.print(f"[red]Message introuvable: {args.msg_id}[/red]")
        return
        
    if msg["status"] == "sent":
        console.print("[yellow]Message déjà envoyé![/yellow]")
        return

    # Get contact email
    try:
        contact = store.get_contact(msg["contact_id"])
    except KeyError:
        console.print("[red]Contact associé introuvable.[/red]")
        return

    sender = EmailSender()
    
    async def send_now():
        attachments = msg.get("attachments", [])
        status_msg = f"Envoi à {contact['email']}..."
        if attachments:
            status_msg += f" ({len(attachments)} attachements)"
            
        with console.status(status_msg):
            success = await sender.send(msg, contact["email"], attachments=attachments)
            
        if success:
            store.update_outreach(msg["id"], {
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat()
            })
            console.print(f"[bold green]✅ Email envoyé à {contact['email']}![/bold green]")
        else:
            console.print("[red]❌ Échec de l'envoi.[/red]")

    asyncio.run(send_now())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI dev pour offres et swipes")
    sub = parser.add_subparsers(dest="command", required=True)

    p_load = sub.add_parser("load-sample", help="Charger les offres d'échantillon")
    p_load.set_defaults(func=cmd_load_sample)

    p_ingest = sub.add_parser("ingest", help="Ingestion depuis un fichier JSON")
    p_ingest.add_argument("file", help="Chemin vers le fichier JSON")
    p_ingest.add_argument("--replace", action="store_true", help="Remplacer data/jobs.json")
    p_ingest.set_defaults(func=cmd_ingest)

    p_list = sub.add_parser("list", help="Lister les offres avec filtres")
    p_list.add_argument("--status", choices=["pending", "yes", "no", "all"], default="pending")
    p_list.add_argument("--query", help="Recherche texte")
    p_list.add_argument("--company", help="Filtre entreprise")
    p_list.add_argument("--tag", action="append", help="Filtre tag")
    p_list.add_argument("--remote", choices=["any", "true", "false"], default="any")
    p_list.add_argument("--type", choices=["full-time", "internship", "contract", "part-time"])
    p_list.add_argument("--limit", type=int, help="Limite")
    p_list.add_argument("--sort", choices=["date", "salary"], default="date", help="Tri des résultats")
    p_list.add_argument("--json", action="store_true", help="Sortie JSON")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Afficher le détail d'une offre")
    p_show.add_argument("job_id", help="Identifiant d'offre")
    p_show.add_argument("--json", action="store_true", help="Sortie JSON")
    p_show.set_defaults(func=cmd_show)

    p_swipe = sub.add_parser("swipe", help="Enregistrer un swipe yes/no")
    p_swipe.add_argument("job_id", help="Identifiant d'offre")
    p_swipe.add_argument("decision", choices=["yes", "no"], help="Décision")
    p_swipe.set_defaults(func=cmd_swipe)

    p_session = sub.add_parser("session", help="Mode interactif de swipe")
    p_session.add_argument("--query", help="Recherche texte")
    p_session.add_argument("--tag", action="append", help="Filtre tag")
    p_session.add_argument("--remote", choices=["any", "true", "false"], default="any")
    p_session.set_defaults(func=cmd_session)

    p_cv = sub.add_parser("adapt-cv", help="Simuler l'adaptation d'un CV")
    p_cv.add_argument("job_id", help="Identifiant d'offre")
    p_cv.add_argument("profile_label", help="Profil candidat")
    p_cv.add_argument("--model", default="gpt-4.1", help="Modèle IA")
    p_cv.set_defaults(func=cmd_adapt_cv)

    p_stats = sub.add_parser("stats", help="Statistiques")
    p_stats.set_defaults(func=cmd_stats)

    p_reset = sub.add_parser("reset-state", help="Réinitialiser swipes/applications")
    p_reset.add_argument("--with-cv", action="store_true", help="Réinitialiser CV")
    p_reset.set_defaults(func=cmd_reset_state)

    p_fetch = sub.add_parser("fetch", help="Récupérer des offres")
    p_fetch.add_argument("-q", "--query", help="Recherche")
    p_fetch.add_argument("-s", "--source", help="Sources")
    p_fetch.add_argument("-l", "--limit", type=int, default=10, help="Limite")
    p_fetch.add_argument("--dry-run", action="store_true", help="Afficher sans importer")
    p_fetch.set_defaults(func=cmd_fetch)

    p_sources = sub.add_parser("sources", help="Lister les sources")
    p_sources.set_defaults(func=cmd_sources)

    # Contacts
    p_contacts = sub.add_parser("contacts", help="Gérer les contacts HR")
    contact_sub = p_contacts.add_subparsers(dest="subcommand", required=True)
    
    pc_load = contact_sub.add_parser("load-sample", help="Charger des contacts exemples")
    pc_load.set_defaults(func=cmd_contacts_load)

    pc_import = contact_sub.add_parser("import", help="Importer des contacts (JSON/CSV)")
    pc_import.add_argument("file", help="Fichier source")
    pc_import.set_defaults(func=cmd_contacts_import)
    
    pc_list = contact_sub.add_parser("list", help="Lister les contacts")
    pc_list.set_defaults(func=cmd_contacts_list)

    # Outreach
    p_outreach = sub.add_parser("outreach", help="Campagnes d'emails")
    outreach_sub = p_outreach.add_subparsers(dest="subcommand", required=True)
    
    po_gen = outreach_sub.add_parser("generate", help="Générer un brouillon d'email")
    po_gen.add_argument("contact_id", help="ID du contact")
    po_gen.set_defaults(func=cmd_outreach_generate)
    
    po_list = outreach_sub.add_parser("list", help="Lister les messages")
    po_list.set_defaults(func=cmd_outreach_list)
    
    po_send = outreach_sub.add_parser("send", help="Envoyer un message")
    po_send.add_argument("msg_id", help="ID du message")
    po_send.set_defaults(func=cmd_outreach_send)

    p_dash = sub.add_parser("dashboard", help="Vue d'ensemble")
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def cmd_dashboard(_: argparse.Namespace):
    """Show a dashboard with high-level stats."""
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.align import Align
    from rich.bar import Bar
    from rich.table import Table
    from rich import box

    store = get_store()
    stats = store.stats()
    
    # Calculate percentages
    total = stats.get("total", 0)
    yes = stats.get("yes", 0)
    no = stats.get("no", 0)
    pending = stats.get("pending", 0)
    
    # Layout
    layout = Layout()
    layout.split_column(
        Layout(name="upper", size=10),
        Layout(name="lower")
    )
    
    layout["upper"].split_row(
        Layout(name="stats"),
        Layout(name="distribution")
    )
    
    # Stats Panel
    stat_table = Table.grid(padding=1)
    stat_table.add_column(style="bold cyan", justify="right")
    stat_table.add_column(style="magenta")
    stat_table.add_row("Total Jobs:", str(total))
    stat_table.add_row("Pending:", str(pending))
    stat_table.add_row("Interested:", str(yes))
    stat_table.add_row("Rejected:", str(no))
    
    layout["stats"].update(
        Panel(
            Align.center(stat_table, vertical="middle"),
            title="[bold]Global Stats[/bold]",
            border_style="cyan"
        )
    )

    # Distribution Panel (Textual bar chart)
    if total > 0:
        yes_pct = (yes / total) * 100
        no_pct = (no / total) * 100
        pending_pct = (pending / total) * 100
        
        dist_text = f"""
        [green]Yes[/green]      {yes_pct:5.1f}% {'█' * int(yes_pct/5)}
        [red]No[/red]       {no_pct:5.1f}% {'█' * int(no_pct/5)}
        [yellow]Pending[/yellow]  {pending_pct:5.1f}% {'█' * int(pending_pct/5)}
        """
    else:
        dist_text = "No data available."

    layout["distribution"].update(
        Panel(
            Align.center(dist_text, vertical="middle"),
            title="[bold]Distribution[/bold]",
            border_style="magenta"
        )
    )

    # Recent Pending Jobs
    jobs = store.list_jobs(status="pending", query=None, company=None, tags=[], remote="any", emp_type=None)
    jobs.sort(key=lambda x: str(x.get("published_at") or ""), reverse=True)
    recent = jobs[:5]
    
    recent_table = Table(box=box.SIMPLE, show_header=True, expand=True)
    recent_table.add_column("Latest Pending Jobs", style="bold white")
    recent_table.add_column("Company", style="dim white")
    recent_table.add_column("Location", style="dim white")
    
    for job in recent:
        recent_table.add_row(
            html.unescape(job.get("title") or "N/A"),
            html.unescape(job.get("company") or "N/A"),
            job.get("location") or "-"
        )
    
    if not recent:
        recent_table = Align.center("[italic]No pending jobs[/italic]")

    layout["lower"].update(
        Panel(
            recent_table,
            title="[bold]Up Next[/bold]",
            border_style="green"
        )
    )

    console.print(layout)


def main(argv: List[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()