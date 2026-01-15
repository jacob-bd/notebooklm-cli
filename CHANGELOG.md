# Changelog

All notable changes to this project will be documented in this file.
## [0.1.5] - 2026-01-15

### Added
- **Config CLI**: New `nlm config` command group to view and edit configuration.
  - `nlm config show`: Display current config (TOML/JSON).
  - `nlm config get <key>`: specific setting.
  - `nlm config set <key> <value>`: Update setting.

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
