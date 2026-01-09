# NLM - NotebookLM CLI

A powerful command-line interface for Google NotebookLM.

## Installation

```bash
pip install nlm
# or
pipx install nlm
# or
uv tool install nlm
```

## Quick Start

```bash
# Authenticate
nlm login

# List notebooks
nlm notebook list

# Create a notebook and add sources
nlm notebook create "My Research"
nlm source add <notebook-id> --url "https://example.com"

# Use Aliases for easier management
nlm alias set my-nb <notebook-id>
nlm source list my-nb

# Sync Drive sources
nlm source stale my-nb
nlm source sync my-nb

# Generate a podcast
nlm audio create <notebook-id>

# Get AI-friendly documentation
nlm --ai
```

## Features

- **Full NotebookLM API coverage** - notebooks, sources, audio, reports, quizzes, and more
- **Cross-browser authentication** - Chrome, Firefox, Safari, Edge, Brave
- **Multiple output formats** - tables, JSON, compact
- **AI-teachable** - `nlm --ai` outputs documentation for AI assistants
- **Profile support** - manage multiple accounts

## Documentation

See the [full documentation](https://github.com/jacob-bd/notebooklm-cli) for complete usage guide.

## License

MIT
