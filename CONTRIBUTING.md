# Contributing to NotebookLM CLI

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jacob-bd/notebooklm-cli.git
cd notebooklm-cli

# Install with development dependencies
uv pip install -e ".[dev]"

# Verify setup
uv run pytest
```

## Project Structure

```
src/nlm/
├── cli/         # Typer command definitions (one file per command group)
├── core/        # Business logic: client.py (API), auth.py, exceptions.py
├── output/      # Formatters for table/JSON/quiet output
├── utils/       # Helpers: config.py, cdp.py (Chrome DevTools)
└── ai_docs.py   # Content for `nlm --ai` flag
```

**Where to add features:**
- New commands → `cli/` (create new file, register in `cli/main.py`)
- API methods → `core/client.py`
- Output formatting → `output/formatters.py`

## Code Style

We use **Ruff** for linting and formatting. Configuration is in `pyproject.toml`.

```bash
# Check for issues
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/
```

**Key conventions:**
- Line length: 100 characters
- Target Python: 3.10+
- Imports: sorted by Ruff (isort-compatible)

## Testing

### Unit Tests
```bash
uv run pytest
```

### End-to-End Tests
```bash
# Requires valid authentication
uv run python tests/run_e2e_tests.py
```

**Testing requirements:**
- New features should include unit tests
- API-dependent tests should be in `tests/run_e2e_tests.py`
- Tests must pass before PR merge

## Pull Request Process

1. **Fork** the repository
2. **Create a feature branch** (`git checkout -b feature/my-feature`)
3. **Make your changes** with descriptive commits
4. **Run tests** (`uv run pytest`)
5. **Run linter** (`uv run ruff check src/`)
6. **Open a PR** with a clear description

**Commit message format:**
```
<type>: <short description>

<optional body with details>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Example: `feat: add --skip-freshness flag to source list`

## Release Process (Maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with new version section
3. Commit: `chore: bump version to X.Y.Z`
4. Tag: `git tag vX.Y.Z && git push --tags`
5. GitHub Actions will publish to PyPI

## Questions?

Open an issue or start a discussion on GitHub. We're happy to help!
