"""Alias CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from nlm.core.alias import get_alias_manager

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
) -> None:
    """Create or update an alias for an ID."""
    manager = get_alias_manager()
    manager.set_alias(name, value)
    console.print(f"[green]✓[/green] Alias set: [bold]{name}[/bold] -> {value}")


@app.command("get")
def get_alias(
    name: str = typer.Argument(..., help="Alias name"),
) -> None:
    """Get the value of an alias."""
    manager = get_alias_manager()
    value = manager.get_alias(name)
    
    if value:
        console.print(value)
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
    table.add_column("Value", style="green")
    
    for name, value in sorted(aliases.items()):
        table.add_row(name, value)
    
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
