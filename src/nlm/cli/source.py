"""Source CLI commands."""

from typing import Optional

import typer
from rich.console import Console

from nlm.core.alias import get_alias_manager
from nlm.core.client import NotebookLMClient
from nlm.core.exceptions import NLMError
from nlm.output.formatters import detect_output_format, get_formatter

console = Console()
app = typer.Typer(
    help="Manage sources",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def get_client(profile: str | None = None) -> NotebookLMClient:
    """Get a client instance."""
    return NotebookLMClient(profile=profile)


@app.command("list")
def list_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    full: bool = typer.Option(False, "--full", "-a", help="Show all columns"),
    drive: bool = typer.Option(False, "--drive", "-d", help="Show Drive sources with freshness status"),
    skip_freshness: bool = typer.Option(False, "--skip-freshness", "-S", help="Skip freshness checks (faster, use with --drive)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Output IDs only"),
    url: bool = typer.Option(False, "--url", "-u", help="Output as ID: URL"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List sources in a notebook."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            if drive:
                sources = client.list_drive_sources(notebook_id, check_freshness=not skip_freshness)
            else:
                sources = client.list_sources(notebook_id)
        
        fmt = detect_output_format(json_output, quiet, url_flag=url)
        formatter = get_formatter(fmt, console)
        formatter.format_sources(sources, full=full or drive, url_only=url)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("add")
def add_source(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to add (website or YouTube)"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text content to add"),
    drive: Optional[str] = typer.Option(None, "--drive", "-d", help="Google Drive document ID"),
    youtube: Optional[str] = typer.Option(None, "--youtube", "-y", help="YouTube URL"),
    title: str = typer.Option("", "--title", help="Title for the source"),
    doc_type: str = typer.Option("doc", "--type", help="Drive doc type: doc, slides, sheets, pdf"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Add a source to a notebook."""
    notebook_id = get_alias_manager().resolve(notebook_id)
    
    # Validate that exactly one source type is provided
    source_count = sum(1 for x in [url, text, drive, youtube] if x)
    if source_count == 0:
        console.print("[red]Error:[/red] Please specify a source: --url, --text, --drive, or --youtube")
        raise typer.Exit(1)
    if source_count > 1:
        console.print("[red]Error:[/red] Please specify only one source type at a time")
        raise typer.Exit(1)
    
    try:
        with get_client(profile) as client:
            if url:
                result = client.add_source_url(notebook_id, url)
                source_desc = url
            elif youtube:
                result = client.add_source_url(notebook_id, youtube)
                source_desc = youtube
            elif text:
                result = client.add_source_text(notebook_id, text, title=title or "Pasted Text")
                source_desc = title or "Pasted Text"
            elif drive:
                if not title:
                    title = f"Drive Document ({drive[:8]}...)"
                result = client.add_source_drive(notebook_id, drive, title, doc_type)
                source_desc = title
            else:
                raise typer.Exit(1)  # Should never reach here
        
        # API returns raw result, not a Source object
        if result is not None:
            console.print(f"[green]✓[/green] Added source: {source_desc}")
        else:
            console.print(f"[yellow]⚠[/yellow] Source may have been added (no confirmation from API)")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("get")
def get_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get source details."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            source = client.get_source(source_id)
        
        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_item(source, title="Source Details")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("describe")
def describe_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get AI-generated source summary with keywords."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            summary = client.describe_source(source_id)
        
        console.print("[bold]Summary:[/bold]")
        console.print(summary.summary)
        
        if summary.keywords:
            console.print("\n[bold]Keywords:[/bold]")
            console.print(", ".join(summary.keywords))
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("content")
def get_source_content(
    source_id: str = typer.Argument(..., help="Source ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write content to file"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Get raw source content (no AI processing)."""
    try:
        source_id = get_alias_manager().resolve(source_id)
        with get_client(profile) as client:
            content = client.get_source_content(source_id)
        
        if output:
            # Write raw content to file
            from pathlib import Path
            Path(output).write_text(content.content)
            console.print(f"[green]✓[/green] Wrote {content.char_count:,} characters to {output}")
        else:
            # Display to console
            console.print(f"[bold]Title:[/bold] {content.title}")
            console.print(f"[bold]Type:[/bold] {content.source_type}")
            console.print(f"[bold]Characters:[/bold] {content.char_count:,}")
            console.print("\n[bold]Content:[/bold]")
            console.print(content.content)
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("delete")
def delete_source(
    source_id: str = typer.Argument(..., help="Source ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Delete a source permanently."""
    source_id = get_alias_manager().resolve(source_id)
    
    if not confirm:
        typer.confirm(
            f"Are you sure you want to delete source {source_id}?",
            abort=True,
        )
    
    try:
        with get_client(profile) as client:
            client.delete_source(source_id)
        
        console.print(f"[green]✓[/green] Deleted source: {source_id}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("stale")
def list_stale_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """List Drive sources that need syncing."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        with get_client(profile) as client:
            sources = client.list_drive_sources(notebook_id)
        
        stale_sources = [s for s in sources if s.is_stale]
        
        if not stale_sources:
            console.print("[green]✓[/green] All Drive sources are up to date.")
            return
        
        console.print(f"[yellow]⚠[/yellow] {len(stale_sources)} source(s) need syncing:")
        
        fmt = detect_output_format(json_output)
        formatter = get_formatter(fmt, console)
        formatter.format_sources(stale_sources, full=True)
        
        console.print("\n[dim]Run 'nlm source sync <notebook-id>' to sync all stale sources.[/dim]")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("sync")
def sync_sources(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    source_ids: Optional[str] = typer.Option(
        None, "--source-ids", "-s",
        help="Comma-separated source IDs to sync (default: all stale)",
    ),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Sync Drive sources with latest content."""
    try:
        notebook_id = get_alias_manager().resolve(notebook_id)
        
        with get_client(profile) as client:
            if source_ids:
                ids_to_sync = [get_alias_manager().resolve(sid.strip()) for sid in source_ids.split(",")]
            else:
                # Get all stale sources
                sources = client.list_drive_sources(notebook_id)
                ids_to_sync = [s.id for s in sources if s.is_stale]
        
        if not ids_to_sync:
            console.print("[green]✓[/green] No sources need syncing.")
            return
        
        if not confirm:
            typer.confirm(
                f"Sync {len(ids_to_sync)} source(s)?",
                abort=True,
            )
        
        with get_client(profile) as client:
            client.sync_sources(ids_to_sync)
        
        console.print(f"[green]✓[/green] Synced {len(ids_to_sync)} source(s)")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
