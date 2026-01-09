"""Alias management for NotebookLM CLI."""

import json
from pathlib import Path
from typing import Dict, Optional

from nlm.utils.config import get_config_dir


class AliasManager:
    """Manages user-defined aliases for IDs."""

    def __init__(self) -> None:
        self.config_dir = get_config_dir()
        self.aliases_file = self.config_dir / "aliases.json"
        self._aliases: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load aliases from disk."""
        if not self.aliases_file.exists():
            return
        
        try:
            content = self.aliases_file.read_text()
            if content:
                self._aliases = json.loads(content)
        except Exception:
            # On error, start with empty map
            self._aliases = {}

    def _save(self) -> None:
        """Save aliases to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.aliases_file.write_text(json.dumps(self._aliases, indent=2))

    def set_alias(self, name: str, value: str) -> None:
        """Set an alias."""
        self._aliases[name] = value
        self._save()

    def get_alias(self, name: str) -> Optional[str]:
        """Get an alias value."""
        return self._aliases.get(name)

    def delete_alias(self, name: str) -> bool:
        """Delete an alias. Returns True if deleted."""
        if name in self._aliases:
            del self._aliases[name]
            self._save()
            return True
        return False

    def list_aliases(self) -> Dict[str, str]:
        """List all aliases."""
        return self._aliases.copy()

    def resolve(self, id_or_alias: str) -> str:
        """
        Resolve an ID or alias to its value.
        If the input matches a known alias, return the aliased value.
        Otherwise return the input as-is.
        """
        return self._aliases.get(id_or_alias, id_or_alias)


# Global instance
_alias_manager: Optional[AliasManager] = None


def get_alias_manager() -> AliasManager:
    """Get the global alias manager instance."""
    global _alias_manager
    if _alias_manager is None:
        _alias_manager = AliasManager()
    return _alias_manager
