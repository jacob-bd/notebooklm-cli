"""Authentication CLI commands."""

import typer
from rich.console import Console

from nlm.core.auth import AuthManager
from nlm.core.exceptions import NLMError

console = Console()
app = typer.Typer(
    help="Authentication commands",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("status")
def status(
    profile: str = typer.Option(
        "default", "--profile", "-p",
        help="Profile to check",
    ),
) -> None:
    """Show authentication status and profile information.
    
    Validates credentials by making a real API call to list notebooks.
    """
    from nlm.core.client import NotebookLMClient
    
    auth = AuthManager(profile)
    
    try:
        p = auth.load_profile()
    except NLMError as e:
        console.print(f"[red]✗[/red] Not authenticated")
        console.print(f"  {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(2)
    
    # Actually validate by making a real API call
    console.print(f"[dim]Validating credentials for profile: {p.name}...[/dim]")
    
    try:
        with NotebookLMClient(profile=profile) as client:
            notebooks = client.list_notebooks()
        
        # Update last_validated timestamp
        auth.save_profile(
            cookies=p.cookies,
            csrf_token=p.csrf_token,
            session_id=p.session_id,
            email=p.email,
        )
        
        console.print(f"[green]✓[/green] Authenticated")
        console.print(f"  Email: {p.email or 'Unknown'}")
        console.print(f"  Profile: {p.name}")
        console.print(f"  Notebooks accessible: {len(notebooks)}")
        console.print(f"  Credentials path: {auth.profile_dir}")
        
    except NLMError as e:
        console.print(f"[red]✗[/red] Authentication expired or invalid")
        console.print(f"  {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        console.print(f"\n[dim]Run 'nlm login' to re-authenticate.[/dim]")
        raise typer.Exit(2)


@app.command("list")
def list_profiles() -> None:
    """List all available profiles."""
    profiles = AuthManager.list_profiles()
    
    if not profiles:
        console.print("[dim]No profiles found.[/dim]")
        console.print("\nRun 'nlm login' to create a profile.")
        return
    
    console.print("[bold]Available profiles:[/bold]")
    for name in profiles:
        try:
            auth = AuthManager(name)
            p = auth.load_profile()
            email = p.email or "Unknown"
            console.print(f"  [cyan]{name}[/cyan]: {email}")
        except Exception:
            console.print(f"  [cyan]{name}[/cyan]: [dim](invalid)[/dim]")


@app.command("delete")
def delete_profile(
    profile: str = typer.Argument(..., help="Profile name to delete"),
    confirm: bool = typer.Option(
        False, "--confirm", "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete a profile and its credentials."""
    auth = AuthManager(profile)
    
    if not auth.profile_exists():
        console.print(f"[red]Error:[/red] Profile '{profile}' not found")
        raise typer.Exit(1)
    
    if not confirm:
        typer.confirm(
            f"Are you sure you want to delete profile '{profile}'?",
            abort=True,
        )
    
    auth.delete_profile()
    console.print(f"[green]✓[/green] Deleted profile: {profile}")
