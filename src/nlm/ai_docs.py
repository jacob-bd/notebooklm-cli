"""AI-friendly documentation output for the --ai flag."""

from nlm import __version__

AI_DOCS = """# NLM CLI - AI Assistant Guide

You are interacting with `nlm`, a command-line interface for Google NotebookLM.
This documentation teaches you how to use the tool effectively.

## Version

nlm version {version}

## Quick Reference

```
nlm <command> [subcommand] [options]
```

### Main Commands

| Command | Description |
|---------|-------------|
| `nlm login` | Authenticate with NotebookLM |
| `nlm notebook` | Manage notebooks |
| `nlm source` | Manage sources within notebooks |
| `nlm chat configure` | Configure chat settings |
| `nlm audio create` | Create audio overviews (podcasts) |
| `nlm report create` | Create reports |
| `nlm quiz create` | Create quizzes |
| `nlm flashcards create` | Create flashcards |
| `nlm mindmap create` | Create mind maps |
| `nlm slides create` | Create slide decks |
| `nlm infographic create` | Create infographics |
| `nlm video create` | Create video overviews |
| `nlm data-table create` | Create data tables |
| `nlm studio status` | Check generation status |
| `nlm research` | Research and discover sources |

## Authentication

Before using any commands, ensure the user is authenticated:

```bash
# Check auth status
nlm auth status

# If not authenticated, guide through login
nlm login
# This opens NotebookLM in the browser
# User logs in, then presses ENTER
# Cookies are automatically extracted

# For manual login (if auto-extraction fails)
nlm login --manual --file ~/.nlm/cookies.txt
```

## Common Workflows

### Create a notebook and add sources

```bash
# Create a new notebook
nlm notebook create "Research Project"
# Output: Created notebook: Research Project
#         ID: abc123def456...

# Add URL sources
nlm source add abc123def456 --url "https://example.com/article"

# Add text content
nlm source add abc123def456 --text "Important notes here" --title "My Notes"

# Add YouTube video
nlm source add abc123def456 --url "https://youtube.com/watch?v=..."

# List sources
nlm source list abc123def456
```

### Generate a podcast from a notebook

```bash
# Create audio overview
nlm audio create abc123def456 --format deep_dive --length default --confirm

# Check status
nlm studio status abc123def456
# Wait for status: completed

# Audio formats: deep_dive, brief, critique, debate
# Length options: short, default, long
```

### Query a notebook (chat with sources)

```bash
nlm notebook query abc123def456 "What are the main themes discussed?"

# For follow-up questions, use the conversation ID
nlm notebook query abc123def456 "Tell me more about theme 1" --conversation-id xyz789
```

### Research and discover new sources

```bash
# Start web research
nlm research start "quantum computing applications" --source web --mode fast

# Check research progress
nlm research status abc123def456

# Import discovered sources
nlm research import abc123def456 task123 --indices 0,2,5
```

## Output Formats

All list commands support multiple output formats:

```bash
# Default: Rich table (human-readable)
nlm notebook list

# JSON (for scripting)
nlm notebook list --json

# Quiet (IDs only, for piping)
nlm notebook list --quiet

# Title format (ID: Title)
nlm notebook list --title

# Full details
nlm notebook list --full
```

**Important**: When output is piped to another command, JSON format is used automatically.

## Error Handling

| Error Message | Cause | Solution |
|--------------|-------|----------|
| "Not authenticated" | No valid session | Run `nlm login` |
| "Notebook not found" | Invalid notebook ID | Run `nlm notebook list` to get valid IDs |
| "Source not found" | Invalid source ID | Run `nlm source list <notebook-id>` |
| "Rate limit exceeded" | Too many requests | Wait and retry |

## Command Quick Reference

### Notebook Commands

```bash
nlm notebook list [--full] [--json] [--quiet] [--title]
nlm notebook create "Title"
nlm notebook get <id>
nlm notebook describe <id>      # AI summary
nlm notebook rename <id> "New Title"
nlm notebook delete <id> [--confirm]
nlm notebook query <id> "question" [--conversation-id <cid>]
```

### Source Commands

```bash
nlm source list <notebook-id> [--full] [--drive]
nlm source add <notebook-id> --url "https://..."
nlm source add <notebook-id> --text "content" --title "Title"
nlm source add <notebook-id> --drive <doc-id> --type doc|slides|sheets|pdf
nlm source get <source-id>
nlm source describe <source-id>  # AI summary
nlm source content <source-id>   # Raw text
nlm source delete <source-id> [--confirm]
nlm source stale <notebook-id>   # List stale Drive sources
nlm source sync <notebook-id> [--source-ids <ids>] [--confirm]
```

### Chat Configuration

```bash
nlm chat configure <notebook-id> --goal default|learning_guide|custom
nlm chat configure <notebook-id> --goal custom --prompt "Act as a tutor..."
nlm chat configure <notebook-id> --response-length default|longer|shorter
```

### Generation Commands

All generation commands support:
- `--source-ids <id1,id2>` to limit to specific sources
- `--confirm` to skip confirmation prompt
- `--profile <name>` to use specific profile

```bash
# Audio
nlm audio create <id> --format deep_dive|brief|critique|debate --length short|default|long

# Report
nlm report create <id> --format "Briefing Doc"|"Study Guide"|"Blog Post"|"Create Your Own"

# Quiz
nlm quiz create <id> --count <n> --difficulty 1-5

# Flashcards
nlm flashcards create <id> --difficulty easy|medium|hard

# Mind Map
nlm mindmap create <id> --title "Title"
nlm mindmap list <id>

# Slides
nlm slides create <id> --format detailed|presenter --length short|default

# Infographic
nlm infographic create <id> --orientation landscape|portrait|square --detail concise|standard|detailed

# Video
nlm video create <id> --format explainer|brief --style auto_select|classic|whiteboard|kawaii|anime|watercolor|retro_print|heritage|paper_craft

# Data Table
nlm data-table create <id> "Description of table to create"

# Check status
nlm studio status <notebook-id>
nlm studio delete <notebook-id> <artifact-id>
```

### Research Commands

```bash
nlm research start "query" --source web|drive --mode fast|deep
nlm research status <notebook-id> [--compact|--full] [--max-wait 300]
nlm research import <notebook-id> <task-id> [--indices 0,2,5]
```

## Profile Management

```bash
nlm login --profile work           # Create/update 'work' profile
nlm auth status --profile work     # Check specific profile
nlm auth list                      # List all profiles
nlm auth delete work [--confirm]   # Delete profile
export NLM_PROFILE=work            # Set default profile
```

## Best Practices

1. **Always check auth first**: Run `nlm auth status` before operations
2. **Use --json for scripting**: Easier to parse in scripts
3. **Use --confirm for automation**: Skip confirmation prompts
4. **Use profiles for multiple accounts**: `nlm login --profile work`
5. **Check studio status after generation**: Some operations take time

## Tips for AI Assistants

1. When listing resources, prefer `--json` for easier parsing
2. Always capture and use the returned IDs from create operations
3. For long-running operations (audio, video), poll `nlm studio status`
4. Use `--confirm` flag to avoid blocking on user prompts
5. Parse errors carefully - hints are provided in error messages
"""


def print_ai_docs() -> None:
    """Print the AI-friendly documentation."""
    print(AI_DOCS.format(version=__version__))
