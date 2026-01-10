"""Research CLI commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from nlm.core.alias import get_alias_manager
from nlm.core.client import NotebookLMClient
from nlm.core.exceptions import NLMError

console = Console()
app = typer.Typer(
    help="Research and discover sources",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def get_client(profile: str | None = None) -> NotebookLMClient:
    """Get a client instance."""
    return NotebookLMClient(profile=profile)


@app.command("start")
def start_research(
    query: str = typer.Argument(..., help="What to search for"),
    source: str = typer.Option(
        "web", "--source", "-s",
        help="Where to search: web or drive",
    ),
    mode: str = typer.Option(
        "fast", "--mode", "-m",
        help="Research mode: fast (~30s, ~10 sources) or deep (~5min, ~40 sources, web only)",
    ),
    notebook_id: Optional[str] = typer.Option(
        None, "--notebook-id", "-n",
        help="Add to existing notebook",
    ),
    title: Optional[str] = typer.Option(
        None, "--title", "-t",
        help="Title for new notebook",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Start new research even if one is already pending",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Start a research task to find new sources.
    
    This searches the web or Google Drive to discover relevant sources
    for your research topic. Use 'nlm research status' to check progress
    and 'nlm research import' to add discovered sources to your notebook.
    """
    # Validate source
    if source not in ["web", "drive"]:
        console.print("[red]Error:[/red] Source must be 'web' or 'drive'")
        raise typer.Exit(1)
    
    # Validate mode
    if mode not in ["fast", "deep"]:
        console.print("[red]Error:[/red] Mode must be 'fast' or 'deep'")
        raise typer.Exit(1)
    
    # Validate deep mode restriction
    if mode == "deep" and source != "web":
        console.print("[red]Error:[/red] Deep research mode is only available for web sources")
        console.print("[dim]Use --mode fast for Drive search, or --source web for deep research.[/dim]")
        raise typer.Exit(1)
    
    try:
        # notebook_id is required for research
        if not notebook_id:
            console.print("[red]Error:[/red] --notebook-id is required for research")
            raise typer.Exit(1)
            
        notebook_id = get_alias_manager().resolve(notebook_id)
        
        with get_client(profile) as client:
            # Check for existing research before starting new one
            if not force:
                existing = client.poll_research(notebook_id)
                if existing and existing.get("status") == "in_progress":
                    console.print("[yellow]Warning:[/yellow] Research already in progress for this notebook.")
                    console.print(f"  Task ID: {existing.get('task_id', 'unknown')}")
                    console.print(f"  Sources found so far: {existing.get('source_count', 0)}")
                    console.print("\n[dim]Use --force to start a new research anyway (will overwrite pending results).[/dim]")
                    console.print("[dim]Or run 'nlm research status' to check progress / 'nlm research import' to save results.[/dim]")
                    raise typer.Exit(1)
                elif existing and existing.get("status") == "completed" and existing.get("source_count", 0) > 0:
                    console.print("[yellow]Warning:[/yellow] Previous research completed with sources not yet imported.")
                    console.print(f"  Task ID: {existing.get('task_id', 'unknown')}")
                    console.print(f"  Sources available: {existing.get('source_count', 0)}")
                    console.print("\n[dim]Use --force to start a new research (will discard existing results).[/dim]")
                    console.print("[dim]Or run 'nlm research import' to save the existing results first.[/dim]")
                    raise typer.Exit(1)
            
            task = client.start_research(
                notebook_id=notebook_id,
                query=query,
                source=source,
                mode=mode,
            )
        
        if not task:
            console.print("[red]Error:[/red] Failed to start research")
            raise typer.Exit(1)
        
        console.print("[green]✓[/green] Research started")
        console.print(f"  Query: {query}")
        console.print(f"  Source: {source}")
        console.print(f"  Mode: {mode}")
        console.print(f"  Notebook ID: {notebook_id}")
        console.print(f"  Task ID: {task.get('task_id', 'unknown')}")
        
        estimate = "~30 seconds" if mode == "fast" else "~5 minutes"
        console.print(f"\n[dim]Estimated time: {estimate}[/dim]")
        console.print(f"[dim]Run 'nlm research status {notebook_id}' to check progress.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("status")
def research_status(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    task_id: Optional[str] = typer.Option(None, "--task-id", "-t", help="Specific task ID to check"),
    compact: bool = typer.Option(
        True, "--compact/--full",
        help="Show compact or full details",
    ),
    poll_interval: int = typer.Option(
        30, "--poll-interval",
        help="Seconds between status checks",
    ),
    max_wait: int = typer.Option(
        300, "--max-wait",
        help="Maximum seconds to wait (0 for single check)",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Check research task progress.
    
    By default, polls until the task completes or times out.
    Use --max-wait 0 for a single status check.
    """
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        if task_id:
            task_id = get_alias_manager().resolve(task_id)

        if max_wait > 0:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Waiting for research to complete...", total=None)
                
                with get_client(profile) as client:
                    task = client.get_research_status(
                        notebook_id,
                        poll_interval=poll_interval,
                        max_wait=max_wait,
                        compact=compact,
                        task_id=task_id,
                    )
        else:
            with get_client(profile) as client:
                task = client.get_research_status(
                    notebook_id,
                    poll_interval=poll_interval,
                    max_wait=0,
                    compact=compact,
                    task_id=task_id,
                )
        
        # Handle dict response from client
        if isinstance(task, dict):
            status = task.get('status', 'unknown')
            sources_found = task.get('sources_found', task.get('source_count', 0))
            report = task.get('report', '')
            sources = task.get('sources', [])
            all_tasks = task.get('tasks', [])
        else:
            status = getattr(task, 'status', 'unknown')
            sources_found = getattr(task, 'sources_found', 0)
            report = getattr(task, 'report', '')
            sources = getattr(task, 'sources', [])
            all_tasks = []
        
        status_style = {
            "completed": "green",
            "pending": "yellow",
            "running": "yellow",
            "in_progress": "yellow",
            "no_research": "dim",
            "failed": "red",
        }.get(status, "")
        
        console.print(f"\n[bold]Research Status:[/bold]")
        
        # Display all tasks if multiple exist
        if len(all_tasks) > 1:
            console.print(f"  Tasks found: {len(all_tasks)}")
            console.print(f"  Overall status: [{status_style}]{status}[/{status_style}]" if status_style else f"  Overall status: {status}")
            console.print()
            for i, t in enumerate(all_tasks):
                t_status = t.get("status", "unknown")
                t_style = {"completed": "green", "in_progress": "yellow"}.get(t_status, "")
                console.print(f"  [{i+1}] Task ID: {t.get('task_id', 'unknown')}")
                console.print(f"      Status: [{t_style}]{t_status}[/{t_style}]" if t_style else f"      Status: {t_status}")
                console.print(f"      Sources: {t.get('source_count', 0)}")
        else:
            if status_style:
                console.print(f"  Status: [{status_style}]{status}[/{status_style}]")
            else:
                console.print(f"  Status: {status}")
            console.print(f"  Sources found: {sources_found}")
        
        if report and not compact:
            console.print(f"\n[bold]Report:[/bold]")
            console.print(report)
        
        if sources and not compact:
            console.print(f"\n[bold]Discovered Sources:[/bold]")
            for i, src in enumerate(sources):
                if isinstance(src, dict):
                    title = src.get("title", "Untitled")
                    url = src.get("url", "")
                else:
                    title = getattr(src, 'title', 'Untitled')
                    url = getattr(src, 'url', '')
                console.print(f"  [{i}] {title}")
                if url:
                    console.print(f"      [dim]{url}[/dim]")
        
        if status == "completed":
            console.print(f"\n[dim]Run 'nlm research import {notebook_id} <task-id>' to import sources.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("import")
def import_research(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    task_id: str = typer.Argument(..., help="Research task ID"),
    indices: Optional[str] = typer.Option(
        None, "--indices", "-i",
        help="Comma-separated indices of sources to import (default: all)",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Import discovered sources from a completed research task."""
    try:
        source_indices = None
        if indices:
            source_indices = [int(i.strip()) for i in indices.split(",")]
        
        notebook_id = get_alias_manager().resolve(notebook_id)
        task_id = get_alias_manager().resolve(task_id)
        
        with get_client(profile) as client:
            sources = client.import_research(notebook_id, task_id, source_indices)
        
        console.print(f"[green]✓[/green] Imported {len(sources) if sources else 0} source(s)")
        if sources:
            for src in sources:
                if isinstance(src, dict):
                    console.print(f"  • {src.get('title', 'Unknown')}")
                else:
                    console.print(f"  • {getattr(src, 'title', 'Unknown')}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid indices. Use comma-separated numbers like: 0,2,5")
        raise typer.Exit(1)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
