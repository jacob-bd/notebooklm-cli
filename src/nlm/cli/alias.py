"""Alias CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from nlm.core.alias import get_alias_manager, detect_id_type

console = Console()
app = typer.Typer(
    help="Manage ID aliases",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("set")
def set_alias(
    name: str = typer.Argument(..., help="Alias name (e.g. 'my-notebook')"),
    value: str = typer.Argument(..., help="ID value (e.g. valid UUID)"),
    alias_type: str = typer.Option(
        None, "--type", "-t",
        help="Type: notebook, source, artifact, task (auto-detected if not specified)",
    ),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to use for detection"),
) -> None:
    """Create or update an alias for an ID."""
    manager = get_alias_manager()
    
    # Auto-detect type if not provided
    if not alias_type:
        with console.status("[dim]Detecting ID type...[/dim]"):
            alias_type = detect_id_type(value, profile)
    
    manager.set_alias(name, value, alias_type)
    
    type_display = f"[dim]({alias_type})[/dim]" if alias_type != "unknown" else ""
    console.print(f"[green]✓[/green] Alias set: [bold]{name}[/bold] -> {value} {type_display}")


@app.command("get")
def get_alias(
    name: str = typer.Argument(..., help="Alias name"),
) -> None:
    """Get the value of an alias."""
    manager = get_alias_manager()
    entry = manager.get_entry(name)
    
    if entry:
        console.print(entry.value)
    else:
        console.print(f"[red]Error:[/red] Alias '{name}' not found")
        raise typer.Exit(1)


@app.command("list")
def list_aliases() -> None:
    """List all aliases."""
    manager = get_alias_manager()
    aliases = manager.list_aliases()
    
    if not aliases:
        console.print("No aliases defined.")
        return

    table = Table(title="Aliases")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Value", style="green")
    
    # Type icons for visual distinction
    type_icons = {
        "notebook": "📓",
        "source": "📄",
        "artifact": "🎨",
        "task": "🔍",
        "unknown": "❓",
    }
    
    for name, entry in sorted(aliases.items()):
        icon = type_icons.get(entry.type, "❓")
        table.add_row(name, f"{icon} {entry.type}", entry.value)
    
    console.print(table)


@app.command("delete")
def delete_alias(
    name: str = typer.Argument(..., help="Alias name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
) -> None:
    """Delete an alias."""
    if not confirm:
        typer.confirm(f"Are you sure you want to delete alias '{name}'?", abort=True)
        
    manager = get_alias_manager()
    if manager.delete_alias(name):
        console.print(f"[green]✓[/green] Deleted alias: {name}")
    else:
        console.print(f"[yellow]⚠[/yellow] Alias '{name}' not found")
        raise typer.Exit(1)



