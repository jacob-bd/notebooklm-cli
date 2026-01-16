"""Chat configuration CLI commands."""

from typing import Optional

import typer
from rich.console import Console

from nlm.core.alias import get_alias_manager
from nlm.core.client import NotebookLMClient
from nlm.core.exceptions import NLMError

console = Console()
app = typer.Typer(
    help="Configure chat settings",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def get_client(profile: str | None = None) -> NotebookLMClient:
    """Get a client instance."""
    return NotebookLMClient(profile=profile)


@app.command("configure")
def configure_chat(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    goal: str = typer.Option(
        "default", "--goal", "-g",
        help="Chat goal: default, learning_guide, or custom",
    ),
    prompt: Optional[str] = typer.Option(
        None, "--prompt",
        help="Custom prompt (required when goal=custom, max 10000 chars)",
    ),
    response_length: str = typer.Option(
        "default", "--response-length", "-r",
        help="Response length: default, longer, or shorter",
    ),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Configure how AI responds in notebook chat.
    
    Goals:
    - default: Standard helpful responses
    - learning_guide: Educational, step-by-step explanations
    - custom: Use your own prompt to guide the AI
    """
    notebook_id = get_alias_manager().resolve(notebook_id)

    # Validate goal
    valid_goals = ["default", "learning_guide", "custom"]
    if goal not in valid_goals:
        console.print(f"[red]Error:[/red] Invalid goal. Must be one of: {', '.join(valid_goals)}")
        raise typer.Exit(1)
    
    # Validate custom prompt requirement
    if goal == "custom" and not prompt:
        console.print("[red]Error:[/red] --prompt is required when goal is 'custom'")
        raise typer.Exit(1)
    
    # Validate prompt length
    if prompt and len(prompt) > 10000:
        console.print("[red]Error:[/red] Custom prompt must be 10000 characters or less")
        raise typer.Exit(1)
    
    # Validate response length
    valid_lengths = ["default", "longer", "shorter"]
    if response_length not in valid_lengths:
        console.print(f"[red]Error:[/red] Invalid response length. Must be one of: {', '.join(valid_lengths)}")
        raise typer.Exit(1)
    
    try:
        with get_client(profile) as client:
            config = client.configure_chat(
                notebook_id,
                goal=goal,
                custom_prompt=prompt,
                response_length=response_length,
            )
        
        console.print("[green]✓[/green] Chat configuration updated")
        console.print(f"  Goal: {config.get('goal', goal)}")
        if config.get('custom_prompt'):
            cp = config['custom_prompt']
            preview = cp[:50] + "..." if len(cp) > 50 else cp
            console.print(f"  Prompt: {preview}")
        console.print(f"  Response length: {config.get('response_length', response_length)}")
    except NLMError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"\n[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("start")
def start_chat(
    notebook_id: str = typer.Argument(..., help="Notebook ID"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """
    Start interactive chat session with a notebook.
    
    Enter a REPL where you can have multi-turn conversations.
    Use /help for commands, /exit to quit.
    """
    from nlm.cli.repl import run_chat_repl
    run_chat_repl(notebook_id, profile)

