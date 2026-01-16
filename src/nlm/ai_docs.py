"""AI-friendly documentation output for the --ai flag."""

from nlm import __version__

AI_DOCS = """# NLM CLI - AI Assistant Guide

You are interacting with `nlm`, a command-line interface for Google NotebookLM.
This documentation teaches you how to use the tool effectively.

## Version

nlm version {version}

---

## CRITICAL: Authentication

**Sessions last approximately 20 minutes.** Before ANY operation, you MUST ensure the user is authenticated.

### First-Time Setup / Re-Authentication
```bash
nlm login
```
This opens NotebookLM in Chrome and extracts cookies automatically.
Output on success: `✓ Successfully authenticated!`

### Check If Already Authenticated
```bash
nlm auth status
```
Validates credentials by making a real API call (lists notebooks).
Shows: `✓ Authenticated` with notebook count, or error if expired.

### Auto-Authentication Recovery (Automatic)
The CLI includes 3-layer automatic recovery:
1. **CSRF/Session Refresh**: Automatically refreshes tokens on 401 errors
2. **Token Reload**: Reloads tokens from disk if updated externally (e.g., by another session)
3. **Headless Auth**: If Chrome profile has saved login, attempts headless authentication

This means most session expirations are handled automatically. You only need to manually run `nlm login` if all recovery layers fail.

### Session Expired?
If ANY command returns:
- "Cookies have expired"
- "authentication may have expired"

Run:
```bash
nlm login
```

---

## Quick Reference

```
nlm <command> [subcommand] [options]
```

### All Top-Level Commands

| Command | Description |
|---------|-------------|
| `nlm login` | Authenticate with NotebookLM (**START HERE**) |
| `nlm auth` | Check authentication status (status, list, delete) |
| `nlm config` | View/edit configuration (show, get, set) |
| `nlm notebook` | Manage notebooks (list, create, get, describe, rename, delete, query) |
| `nlm source` | Manage sources (list, add, get, describe, content, delete, stale, sync) |
| `nlm chat` | Chat with notebooks (start, configure) |
| `nlm studio` | Manage artifacts (status, delete) |
| `nlm research` | Research and discover sources (start, status, import) |
| `nlm alias` | Manage ID shortcuts (set, get, list, delete) |
| `nlm audio` | Create audio overviews/podcasts (create) |
| `nlm report` | Create reports (create) |
| `nlm quiz` | Create quizzes (create) |
| `nlm flashcards` | Create flashcards (create) |
| `nlm mindmap` | Create mind maps (create) |
| `nlm slides` | Create slide decks (create) |
| `nlm infographic` | Create infographics (create) |
| `nlm video` | Create video overviews (create) |
| `nlm data-table` | Create data tables (create) |

---

## Alias System (Shortcuts for UUIDs)

Create memorable names for long UUIDs:

```bash
# Set an alias
nlm alias set myproject abc123-def456-...

# Use aliases anywhere an ID is expected
nlm notebook get myproject
nlm source list myproject  
nlm audio create myproject --confirm

# Manage aliases
nlm alias list                    # List all
nlm alias get myproject           # Resolve to UUID
nlm alias delete myproject        # Remove
```

---

## Complete Command Reference

### Login & Auth

```bash
nlm login                              # Authenticate (opens browser)
nlm login --profile work               # Named profile
nlm login --manual --file <path>       # Import cookies from file
nlm login --check                      # Only check if auth valid

nlm auth status                        # Check current auth
nlm auth status --profile work         # Check specific profile
nlm auth list                          # List all profiles
nlm auth delete work --confirm         # Delete a profile
```

### Config Commands

```bash
nlm config show                        # Display current config (TOML)
nlm config show --json                 # Display as JSON
nlm config get <key>                   # Get specific setting
nlm config set <key> <value>           # Update setting
```

### Notebook Commands

```bash
nlm notebook list                      # List all notebooks
nlm notebook list --json               # JSON output
nlm notebook list --quiet              # IDs only
nlm notebook list --title              # "ID: Title" format
nlm notebook list --full               # All columns

nlm notebook create "Title"            # Create new notebook

nlm notebook get <id>                  # Get notebook details

nlm notebook describe <id>             # AI summary with topics

nlm notebook rename <id> "New Title"   # Rename notebook

nlm notebook delete <id> --confirm     # Delete permanently

nlm notebook query <id> "question"     # Chat with sources
nlm notebook query <id> "follow up" --conversation-id <cid>
nlm notebook query <id> "question" --source-ids <id1,id2>
```

### Source Commands

```bash
nlm source list <notebook-id>          # List sources
nlm source list <notebook-id> --full   # Full details
nlm source list <notebook-id> --url    # "ID: URL" format
nlm source list <notebook-id> --drive  # Show Drive sources with freshness
nlm source list <notebook-id> --drive --skip-freshness  # Faster, skip freshness checks

nlm source add <notebook-id> --url "https://..."           # Add URL
nlm source add <notebook-id> --url "https://youtube.com/..." # Add YouTube
nlm source add <notebook-id> --text "content" --title "Title"  # Add text
nlm source add <notebook-id> --drive <doc-id>              # Add Drive doc
nlm source add <notebook-id> --drive <doc-id> --type slides  # Add Drive slides
# Types: doc, slides, sheets, pdf

nlm source get <source-id>             # Get source metadata

nlm source describe <source-id>        # AI summary + keywords

nlm source content <source-id>         # Raw text content
nlm source content <source-id> --output file.txt  # Export to file

nlm source delete <source-id> --confirm  # Delete source

nlm source stale <notebook-id>         # List stale Drive sources
nlm source sync <notebook-id> --confirm  # Sync all stale
nlm source sync <notebook-id> --source-ids <ids> --confirm  # Sync specific
```

### Chat Commands

```bash
# Interactive REPL (multi-turn conversation)
nlm chat start <notebook-id>           # Start interactive session
# In REPL:
#   /sources - List sources
#   /clear   - Reset conversation
#   /help    - Show commands
#   /exit    - Exit

# Configure chat behavior
nlm chat configure <notebook-id> --goal default
nlm chat configure <notebook-id> --goal learning_guide
nlm chat configure <notebook-id> --goal custom --prompt "Act as a tutor..."
nlm chat configure <notebook-id> --response-length longer   # longer, default, shorter
```

### Research Commands

```bash
# Start research (--notebook-id is REQUIRED)
nlm research start "query" --notebook-id <id>                    # Fast web (default)
nlm research start "query" --notebook-id <id> --mode deep        # Deep web (~5min)
nlm research start "query" --notebook-id <id> --source drive     # Fast drive
nlm research start "query" --notebook-id <id> --force            # Override pending

# Check progress
nlm research status <notebook-id>                    # Poll until done (5min max)
nlm research status <notebook-id> --max-wait 0       # Single check
nlm research status <notebook-id> --task-id <tid>    # Specific task
nlm research status <notebook-id> --full             # Full details

# Import discovered sources
nlm research import <notebook-id> <task-id>              # Import all
nlm research import <notebook-id> <task-id> --indices 0,2,5  # Import specific
```

**Research Modes:**
- `fast`: ~30 seconds, ~10 sources (web or drive)
- `deep`: ~5 minutes, ~40-80 sources (web only)

### Generation Commands (Studio)

**All generation commands support:**
- `--confirm` or `-y`: Skip confirmation (REQUIRED for automation)
- `--source-ids <id1,id2>`: Limit to specific sources
- `--language <code>`: BCP-47 code (en, es, fr, de, ja)
- `--profile <name>`: Use specific auth profile

#### Audio (Podcast)
```bash
nlm audio create <notebook-id> --confirm
nlm audio create <notebook-id> --format deep_dive --length default --confirm
nlm audio create <notebook-id> --format brief --focus "key topic" --confirm
# Formats: deep_dive, brief, critique, debate
# Lengths: short, default, long
```

#### Report
```bash
nlm report create <notebook-id> --confirm
nlm report create <notebook-id> --format "Study Guide" --confirm
nlm report create <notebook-id> --format "Create Your Own" --prompt "Summary..." --confirm
# Formats: "Briefing Doc", "Study Guide", "Blog Post", "Create Your Own"
```

#### Quiz
```bash
nlm quiz create <notebook-id> --confirm
nlm quiz create <notebook-id> --count 5 --difficulty 3 --confirm
# Count: number of questions (default: 2)
# Difficulty: 1-5 (1=easy, 5=hard, default: 2)
```

#### Flashcards
```bash
nlm flashcards create <notebook-id> --confirm
nlm flashcards create <notebook-id> --difficulty hard --confirm
# Difficulty: easy, medium, hard (default: medium)
```

#### Mind Map
```bash
nlm mindmap create <notebook-id> --confirm
nlm mindmap create <notebook-id> --title "Topic Overview" --confirm
```

#### Slides
```bash
nlm slides create <notebook-id> --confirm
nlm slides create <notebook-id> --format presenter --length short --confirm
# Formats: detailed, presenter (default: detailed)
# Lengths: short, default
```

#### Infographic
```bash
nlm infographic create <notebook-id> --confirm
nlm infographic create <notebook-id> --orientation portrait --detail detailed --confirm
# Orientations: landscape, portrait, square (default: landscape)
# Detail: concise, standard, detailed (default: standard)
```

#### Video
```bash
nlm video create <notebook-id> --confirm
nlm video create <notebook-id> --format brief --style whiteboard --confirm
# Formats: explainer, brief (default: explainer)
# Styles: auto_select, classic, whiteboard, kawaii, anime, watercolor, retro_print, heritage, paper_craft
```

#### Data Table
```bash
nlm data-table create <notebook-id> "Extract all dates and events" --confirm
# DESCRIPTION is REQUIRED as second argument
```

### Studio Commands (Artifact Management)

```bash
nlm studio status <notebook-id>                    # List all artifacts + status
nlm studio status <notebook-id> --json             # JSON output
nlm studio status <notebook-id> --full             # All details

nlm studio delete <notebook-id> <artifact-id> --confirm  # Delete artifact
```

### Alias Commands

```bash
nlm alias set <name> <uuid>     # Create/update alias (auto-detects type)
nlm alias get <name>            # Get UUID for alias
nlm alias list                  # List all aliases
nlm alias delete <name>         # Remove (no --confirm needed)
```

---

## Output Formats

List commands support multiple formats:

| Flag | Description |
|------|-------------|
| (none) | Rich table (human-readable) |
| `--json` | JSON output (for parsing) |
| `--quiet` | IDs only (for piping) |
| `--title` | "ID: Title" format |
| `--url` | "ID: URL" format (sources only) |
| `--full` | All columns/details |

---

## Error Handling

| Error Message | Cause | Solution |
|--------------|-------|----------|
| "Cookies have expired" | Session expired | Run `nlm login` |
| "authentication may have expired" | Session expired | Run `nlm login` |
| "Notebook not found" | Invalid ID | Run `nlm notebook list` |
| "Source not found" | Invalid ID | Run `nlm source list <notebook-id>` |
| "Rate limit exceeded" | Too many API calls | Wait 30 seconds, retry |
| "Research already in progress" | Pending research | Use `--force` or import first |

---

## Complete Task Sequences

### Sequence 1: Research → Podcast

```bash
# 1. Authenticate
nlm login

# 2. Create notebook
nlm notebook create "AI Research 2026"
# ID: abc123...

# 3. Set alias for convenience
nlm alias set ai abc123...

# 4. Start deep research
nlm research start "agentic AI trends 2026" --notebook-id ai --mode deep
# Task ID: task456...

# 5. Wait for completion
nlm research status ai --max-wait 300

# 6. Import all sources
nlm research import ai task456...

# 7. Generate podcast
nlm audio create ai --format deep_dive --confirm

# 8. Check status until completed
nlm studio status ai
```

### Sequence 2: Quick Source Ingestion

```bash
# Add multiple URLs
nlm source add <notebook-id> --url "https://example1.com"
nlm source add <notebook-id> --url "https://example2.com"
nlm source add <notebook-id> --text "My notes here" --title "Notes"
nlm source list <notebook-id>
```

### Sequence 3: Generate Study Materials

```bash
nlm quiz create <notebook-id> --count 10 --difficulty 3 --confirm
nlm flashcards create <notebook-id> --difficulty hard --confirm
nlm report create <notebook-id> --format "Study Guide" --confirm
```

---

## Tips for AI Assistants

1. **Always run `nlm login` first** if any auth error occurs
2. **Use `--confirm` for all generation/delete commands** to avoid blocking prompts
3. **Capture IDs from create outputs** - you'll need them for subsequent operations
4. **Use aliases** for frequently-used notebooks to simplify commands
5. **Poll for long operations** - audio/video takes 1-5 minutes; use `nlm studio status`
6. **Research requires `--notebook-id`** - the flag is mandatory
7. **Session lifetime is ~20 minutes** - re-login if operations start failing
8. **Use `--max-wait 0`** for single status poll instead of blocking
"""


def print_ai_docs() -> None:
    """Print the AI-friendly documentation."""
    print(AI_DOCS.format(version=__version__))
