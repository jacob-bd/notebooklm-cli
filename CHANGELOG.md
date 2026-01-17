# Changelog

All notable changes to this project will be documented in this file.

## [0.1.8] - 2026-01-17

### Added
- **Documentation**: New `docs/TROUBLESHOOTING.md` with common issues and solutions.
  - Includes OpenAI Codex sandbox network access configuration.
- **Source Types**: Added support for `uploaded_file`, `image`, and `word_doc` source types.

### Fixed
- **URL Parsing**: Fixed URL extraction for different source types in `source list`:
  - YouTube videos now correctly extract URL from metadata index 5.
  - Web pages correctly extract URL from metadata index 7.
  - Drive documents now generate proper Drive URLs from document IDs.

## [0.1.7] - 2026-01-16

### Added
- **Performance**: Added `--skip-freshness/-S` flag to `nlm source list --drive`.
  - Skips N+1 HTTP requests for freshness checks, significantly faster for notebooks with many Drive sources.
- **Export**: Added `--output/-o` flag to `nlm source content` to export source text directly to file.
- **Developer Docs**: Added `CONTRIBUTING.md` with development setup, code style, testing, and PR guidelines.
- **Shell Completion**: Documented `nlm --install-completion` for tab completion setup.

### Changed
- **UX**: Generation commands now show progress spinners during API calls (audio, report, quiz, flashcards, mindmap, slides, infographic, video, data-table).
- **UX**: Artifact status table now uses Unicode symbols (✓, ●, ✗) for faster visual scanning.

## [0.1.6] - 2026-01-16

### Fixed
- **Chrome Port Conflict**: `nlm login` now works when port 9222 is already in use (Issue #5).
  - Automatically finds an available port in range 9222-9231.
  - Reconnects to existing NLM auth Chrome if already running.
  - Improved error messages for stale profile locks.

## [0.1.5] - 2026-01-15

### Added
- **Config CLI**: New `nlm config` command group to view and edit configuration.
  - `nlm config show`: Display current config (TOML/JSON).
  - `nlm config get <key>`: specific setting.
  - `nlm config set <key> <value>`: Update setting.
- **Interactive Chat REPL**: New `nlm chat start <notebook-id>` for multi-turn conversations.
  - Maintains conversation context across turns
  - Slash commands: `/exit`, `/clear`, `/sources`, `/help`
  - Rich Markdown rendering for AI responses

### Fixed
- **Citation Display**: Fixed incorrect source titles in REPL citation legend.
  - Citations now correctly map to source UUIDs via backend metadata.
  - Multiple citations referencing the same source are grouped together.

## [0.1.4] - 2026-01-15

### Added
- **Auto-Authentication**: Ported robust 3-layer authentication recovery from `notebooklm-mcp`.
  - Layer 1: Automatic CSRF/Session ID refresh.
  - Layer 2: Automatic reload of tokens from disk if updated externally.
  - Layer 3: Headless Chrome authentication if profile has saved login.
- Added `auth_refresh.py` module for handling headless auth.

### Changed
- Refactored `client.py` to use `CodeMapper` pattern and centralized `constants.py` for better maintainability (Issue #3).


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-01-15

### 🐛 Fixed
- Extended timeout for Drive source operations from 30s to 120s (fixes #4).
  - Large Google Slides presentations (100+ slides) no longer timeout during upload.

## [0.1.2] - 2026-01-10

### 🚀 Added
- Added `--url` flag to `nlm source list` for a simplified "ID: URL" output format.
- Added `url` field to JSON source output (now always present).

### 💅 Changed
- Improved `nlm source list --full` table layout:
    - Expanded URL column width to 80 chars and enabled wrapping.
    - Tightened Title column to 30 chars with ellipsis.
- Updated documentation (`README.md` and `nlm --ai`) to reflect new source list features.

## [0.1.1] - 2026-01-10

### 🚀 Added
- Auto-detection of alias types when setting aliases (`nlm alias set`).
- Type icons/emojis in `nlm alias list` output.
- Support for `notebook`, `source`, `artifact`, `task` types in alias storage.

### 🧹 Changed
- Removed manual `detect-types` command (superseded by auto-detection on creation).
- Updated documentation to reflect alias system improvements.

## [0.1.0] - 2026-01-09

### 🎉 Initial Release
- Core commands: `notebook`, `source`, `studio`, `auth`, `research`.
- Chrome DevTools Protocol authentication.
- `--ai` flag for AI-friendly documentation.
