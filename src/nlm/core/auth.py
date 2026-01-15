"""Authentication management for NLM CLI."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nlm.core.exceptions import AuthenticationError, ProfileNotFoundError
from nlm.utils.browser import (
    cookies_to_header,
    parse_cookies_from_file,
    validate_notebooklm_cookies,
)
from nlm.utils.config import get_profile_dir, get_profiles_dir


class Profile:
    """Represents an authentication profile."""

    def __init__(
        self,
        name: str,
        cookies: dict[str, str],
        csrf_token: str | None = None,
        session_id: str | None = None,
        email: str | None = None,
        last_validated: datetime | None = None,
    ) -> None:
        self.name = name
        self.cookies = cookies
        self.csrf_token = csrf_token
        self.session_id = session_id
        self.email = email
        self.last_validated = last_validated

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self.name,
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "email": self.email,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        """Create profile from dictionary."""
        last_validated = None
        if data.get("last_validated"):
            try:
                last_validated = datetime.fromisoformat(data["last_validated"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            name=data.get("name", "default"),
            cookies=data.get("cookies", {}),
            csrf_token=data.get("csrf_token"),
            session_id=data.get("session_id"),
            email=data.get("email"),
            last_validated=last_validated,
        )


class AuthManager:
    """Manages authentication profiles and credentials."""

    def __init__(self, profile_name: str = "default") -> None:
        self.profile_name = profile_name
        self._profile: Profile | None = None

    @property
    def profile_dir(self) -> Path:
        """Get the directory for the current profile."""
        return get_profile_dir(self.profile_name)

    @property
    def cookies_file(self) -> Path:
        """Get the cookies file path."""
        return self.profile_dir / "cookies.json"

    @property
    def metadata_file(self) -> Path:
        """Get the metadata file path."""
        return self.profile_dir / "metadata.json"

    def profile_exists(self) -> bool:
        """Check if the profile exists."""
        return self.cookies_file.exists()

    def load_profile(self, force_reload: bool = False) -> Profile:
        """Load the current profile from disk."""
        if self._profile is not None and not force_reload:
            return self._profile
        
        if not self.profile_exists():
            raise ProfileNotFoundError(self.profile_name)
        
        try:
            cookies = json.loads(self.cookies_file.read_text())
            metadata = {}
            if self.metadata_file.exists():
                metadata = json.loads(self.metadata_file.read_text())
            
            self._profile = Profile(
                name=self.profile_name,
                cookies=cookies,
                csrf_token=metadata.get("csrf_token"),
                session_id=metadata.get("session_id"),
                email=metadata.get("email"),
                last_validated=datetime.fromisoformat(metadata["last_validated"])
                if metadata.get("last_validated") else None,
            )
            return self._profile
        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to load profile '{self.profile_name}': {e}",
                hint="The profile may be corrupted. Try 'nlm login' to re-authenticate.",
            ) from e

    def save_profile(
        self,
        cookies: dict[str, str],
        csrf_token: str | None = None,
        session_id: str | None = None,
        email: str | None = None,
    ) -> Profile:
        """Save credentials to the current profile."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on the directory
        self.profile_dir.chmod(0o700)
        
        # Save cookies
        self.cookies_file.write_text(json.dumps(cookies, indent=2))
        self.cookies_file.chmod(0o600)
        
        # Save metadata
        metadata = {
            "csrf_token": csrf_token,
            "session_id": session_id,
            "email": email,
            "last_validated": datetime.now().isoformat(),
        }
        self.metadata_file.write_text(json.dumps(metadata, indent=2))
        self.metadata_file.chmod(0o600)
        
        self._profile = Profile(
            name=self.profile_name,
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            email=email,
            last_validated=datetime.now(),
        )
        return self._profile

    def delete_profile(self) -> None:
        """Delete the current profile."""
        if self.profile_dir.exists():
            import shutil
            shutil.rmtree(self.profile_dir)
        self._profile = None

    def get_cookies(self) -> dict[str, str]:
        """Get cookies for the current profile."""
        profile = self.load_profile()
        return profile.cookies

    def get_cookie_header(self) -> str:
        """Get Cookie header value for HTTP requests."""
        return cookies_to_header(self.get_cookies())

    def get_headers(self) -> dict[str, str]:
        """Get headers for NotebookLM API requests."""
        profile = self.load_profile()
        headers = {
            "Cookie": cookies_to_header(profile.cookies),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://notebooklm.google.com",
            "Referer": "https://notebooklm.google.com/",
        }
        if profile.csrf_token:
            headers["X-Goog-Csrf-Token"] = profile.csrf_token
        return headers

    @staticmethod
    def list_profiles() -> list[str]:
        """List all available profiles."""
        profiles_dir = get_profiles_dir()
        if not profiles_dir.exists():
            return []
        return [d.name for d in profiles_dir.iterdir() if d.is_dir()]

    def login_with_file(self, file_path: str | Path) -> Profile:
        """
        Parse cookies from file and save to profile.
        
        Args:
            file_path: Path to file containing cookies.
        
        Returns:
            The saved profile.
        """
        cookies = parse_cookies_from_file(file_path)
        
        if not validate_notebooklm_cookies(cookies):
            raise AuthenticationError(
                message="Parsed cookies don't appear to be valid for NotebookLM",
                hint="Make sure the file contains cookies from a NotebookLM session.",
            )
        
        return self.save_profile(cookies)


def get_auth_manager(profile: str | None = None) -> AuthManager:
    """Get an AuthManager for the specified or default profile."""
    from nlm.utils.config import get_config
    
    if profile is None:
        profile = get_config().auth.default_profile
    
    return AuthManager(profile)
