<div align="center">
  <img src="assets/logo.png" alt="NotebookLM CLI Logo" width="600">
  <h1>NLM - NotebookLM CLI</h1>
  <p><strong>A powerful command-line interface for Google NotebookLM</strong></p>

  [![PyPI version](https://img.shields.io/pypi/v/notebooklm-cli.svg)](https://pypi.org/project/notebooklm-cli/)
  [![Python](https://img.shields.io/pypi/pyversions/notebooklm-cli.svg)](https://pypi.org/project/notebooklm-cli/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
</div>

> ⚠️ **Important Disclaimer**: This CLI uses **internal APIs** that are undocumented and may change without notice. Not affiliated with or endorsed by Google. Use at your own risk for personal/experimental purposes. See also: [notebooklm-mcp](https://github.com/jacob-bd/notebooklm-mcp) for MCP server integration.

---

## ✨ Features

- **Full NotebookLM API Coverage** — Notebooks, sources, audio podcasts, reports, quizzes, flashcards, mind maps, slides, infographics, videos, and data tables
- **Seamless Authentication** — Uses Chrome DevTools Protocol for reliable, automatic cookie extraction
- **AI-Teachable** — Run `nlm --ai` to output comprehensive documentation that AI assistants can consume
- **Alias System** — Create memorable shortcuts for long UUIDs (e.g., `myproject` instead of `abc123-def456-...`)
- **Multiple Output Formats** — Rich tables, JSON, quiet (IDs only), or full details
- **Profile Support** — Manage multiple Google accounts with named profiles
- **Research Integration** — Deep web search or Google Drive search to discover and import sources

---

## 📦 Installation

Install from PyPI using your preferred package manager:

```bash
# Using pip
pip install notebooklm-cli

# Using pipx (recommended for CLI tools)
pipx install notebooklm-cli

# Using uv
uv tool install notebooklm-cli
```

**Requirements:**
- Python 3.10+
- Google Chrome (for authentication)

---

## 🚀 Quick Start

### 1. Authenticate

```bash
nlm login
```

This launches Chrome, navigates to NotebookLM, and automatically extracts your session cookies. You'll need to log in to your Google account if not already signed in.

### 2. List Your Notebooks

```bash
nlm notebook list
```

### 3. Create a Notebook and Add Sources

```bash
# Create a new notebook
nlm notebook create "My Research"
# Output: Created notebook: abc123-def456-...

# Add a URL source
nlm source add abc123-def456 --url "https://example.com/article"

# Add a YouTube video
nlm source add abc123-def456 --url "https://youtube.com/watch?v=..."

# Add pasted text
nlm source add abc123-def456 --text "Your content here" --title "My Notes"
```

### 4. Generate a Podcast

```bash
nlm audio create abc123-def456 --confirm
```

### 5. Check Generation Status

```bash
nlm studio status abc123-def456
```

---

## 🏷️ Aliases (UUID Shortcuts)

Tired of typing long UUIDs? Create aliases:

```bash
# Set an alias
nlm alias set myproject abc123-def456-... # Types are auto-detected!

# Now use the alias anywhere
nlm notebook get myproject
nlm source list myproject
nlm audio create myproject --confirm

# Manage aliases
nlm alias list              # List all aliases
nlm alias get myproject     # Resolve to UUID
nlm alias delete myproject  # Remove alias
```

---

## 🤖 AI Integration

The `--ai` flag outputs comprehensive, structured documentation designed for AI assistants:

```bash
nlm --ai
```

This prints a 380+ line guide covering:
- All commands with exact syntax
- Authentication flow
- Error handling
- Complete task sequences
- Tips for automation

**Use case:** Paste the output of `nlm --ai` into your AI assistant's context to teach it how to use the CLI on your behalf.

---

## 📚 Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `nlm login` | Authenticate with NotebookLM (opens Chrome) |
| `nlm auth status` | Check if current session is valid |
| `nlm notebook list` | List all notebooks |
| `nlm notebook create "Title"` | Create a new notebook |
| `nlm notebook get <id>` | Get notebook details |
| `nlm notebook describe <id>` | Get AI-generated summary |
| `nlm notebook query <id> "question"` | Chat with your sources |
| `nlm notebook delete <id> --confirm` | Delete a notebook |

### Source Management

| Command | Description |
|---------|-------------|
| `nlm source list <notebook-id>` | List sources in a notebook |
| `nlm source list <notebook-id> --drive` | Show Drive sources with freshness |
| `nlm source list <notebook-id> --drive -S` | Faster listing, skip freshness checks |
| `nlm source add <id> --url "..."` | Add URL or YouTube source |
| `nlm source add <id> --text "..." --title "..."` | Add pasted text |
| `nlm source add <id> --drive <doc-id>` | Add Google Drive document |
| `nlm source describe <source-id>` | Get AI summary of source |
| `nlm source content <source-id>` | Get raw text content |
| `nlm source stale <notebook-id>` | List outdated Drive sources |
| `nlm source sync <notebook-id> --confirm` | Sync Drive sources |

### Research (Discover New Sources)

| Command | Description |
|---------|-------------|
| `nlm research start "query" --notebook-id <id>` | Start web search (~30s) |
| `nlm research start "query" --notebook-id <id> --mode deep` | Deep research (~5min) |
| `nlm research start "query" --notebook-id <id> --source drive` | Search Google Drive |
| `nlm research status <notebook-id>` | Check research progress |
| `nlm research import <notebook-id> <task-id>` | Import discovered sources |

### Content Generation

All generation commands require `--confirm` (or `-y`) to execute:

| Command | Description |
|---------|-------------|
| `nlm audio create <id> --confirm` | Generate podcast/audio overview |
| `nlm report create <id> --confirm` | Generate briefing doc or study guide |
| `nlm quiz create <id> --confirm` | Generate quiz questions |
| `nlm flashcards create <id> --confirm` | Generate flashcards |
| `nlm mindmap create <id> --confirm` | Generate mind map |
| `nlm slides create <id> --confirm` | Generate slide deck |
| `nlm infographic create <id> --confirm` | Generate infographic |
| `nlm video create <id> --confirm` | Generate video overview |
| `nlm data-table create <id> "description" --confirm` | Extract data as table |

### Studio (Artifact Management)

| Command | Description |
|---------|-------------|
| `nlm studio status <notebook-id>` | List all generated artifacts |
| `nlm studio delete <notebook-id> <artifact-id> --confirm` | Delete an artifact |

### Chat (Interactive Q&A)

| Command | Description |
|---------|-------------|
| `nlm chat start <notebook-id>` | Start interactive REPL session |
| `nlm chat configure <notebook-id>` | Configure chat goal and response style |
| `nlm notebook query <id> "question"` | One-shot question (no session) |

**Chat REPL commands:** `/sources`, `/clear`, `/help`, `/exit`

### Configuration

| Command | Description |
|---------|-------------|
| `nlm config show` | Show current configuration |
| `nlm config get <key>` | Get a specific setting |
| `nlm config set <key> <value>` | Update a setting |

### Authentication

| Command | Description |
|---------|-------------|
| `nlm login` | Authenticate with Chrome |
| `nlm login --check` | Verify current credentials |
| `nlm auth status` | Check session validity |
| `nlm auth list` | List all profiles |
| `nlm auth delete <profile> --confirm` | Delete a profile |

## 🎛️ Output Formats

Most list commands support multiple output formats:

```bash
nlm notebook list              # Rich table (default)
nlm notebook list --json       # JSON output
nlm notebook list --quiet      # IDs only (for scripting)
nlm notebook list --title      # "ID: Title" format
nlm source list --url          # "ID: URL" format
nlm notebook list --full       # All columns
```

---

## 👤 Profiles (Multiple Accounts)

Manage multiple Google accounts with named profiles:

```bash
# Login to a specific profile
nlm login --profile work
nlm login --profile personal

# Use a profile for commands
nlm notebook list --profile work

# List all profiles
nlm auth list

# Delete a profile
nlm auth delete work --confirm
```

---

## ⌨️ Shell Completion

Enable tab completion for faster command entry:

```bash
# Auto-install for your current shell
nlm --install-completion

# Or show the completion script to install manually
nlm --show-completion
```

---

## ⚠️ Session Lifetime

NotebookLM sessions typically last **~20 minutes**. If commands start failing with authentication errors, simply re-run:

```bash
nlm login
```

---

## 🔧 Troubleshooting

Having issues? See the [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for solutions to common problems including authentication, network issues, and OpenAI Codex sandbox configuration.

---

## 📖 Documentation

For detailed technical documentation on the internal API and advanced usage, see the [`docs/`](docs/) folder:

- [Troubleshooting](docs/TROUBLESHOOTING.md) — Common issues and solutions
- [CLI Test Plan](docs/CLI_TEST_PLAN.md) — End-to-end testing procedures
- [Technical Deep Dive](docs/TECHNICAL_DEEP_DIVE.md) — Internal API details

For AI assistants, run `nlm --ai` to get the full command reference.

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Quick start for contributors
git clone https://github.com/jacob-bd/notebooklm-cli.git
cd notebooklm-cli
uv pip install -e ".[dev]"
uv run pytest
```

---

## ⚠️ Limitations

- **Rate limits**: Free tier has ~50 queries/day
- **No official support**: API may change without notice
- **Cookie expiration**: Need to re-authenticate every few weeks

---

## 🎨 Vibe Coding Alert

Full transparency: this project was built by a non-developer using AI coding assistants. If you're an experienced Python developer, you might look at this codebase and wince. That's okay.

The goal here was to scratch an itch—programmatic access to NotebookLM—and learn along the way. The code works, but it's likely missing patterns, optimizations, or elegance that only years of experience can provide.

**This is where you come in.** If you see something that makes you cringe, please consider contributing rather than just closing the tab. PRs and issues are welcome.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
