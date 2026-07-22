"""Session persistence for Supabase Auth tokens.

Stores access and refresh tokens so users stay signed in across app restarts.
Uses a simple JSON file in the app's data directory.

The "Remember Me" checkbox controls whether tokens are persisted.
"""
import json
import os
from pathlib import Path
from typing import Optional


# Store session data in a platform-appropriate location
def _get_session_path() -> Path:
    """Get the path to the session file."""
    # Use the app's directory for simplicity
    return Path(__file__).resolve().parent.parent / ".session"


class SessionService:
    """Manages session token persistence for auto-login."""

    def __init__(self, session_path: Optional[Path] = None):
        self._session_path = session_path or _get_session_path()

    def save_session(self, access_token: str, refresh_token: str) -> None:
        """Save session tokens to disk."""
        try:
            data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
            self._session_path.write_text(json.dumps(data))
        except Exception:
            pass  # Non-critical; user can log in again

    def get_access_token(self) -> Optional[str]:
        """Get the saved access token, if any."""
        try:
            if self._session_path.exists():
                data = json.loads(self._session_path.read_text())
                return data.get("access_token")
        except Exception:
            pass
        return None

    def get_refresh_token(self) -> Optional[str]:
        """Get the saved refresh token, if any."""
        try:
            if self._session_path.exists():
                data = json.loads(self._session_path.read_text())
                return data.get("refresh_token")
        except Exception:
            pass
        return None

    def clear_session(self) -> None:
        """Remove saved session tokens."""
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except Exception:
            pass

    def has_session(self) -> bool:
        """Check if a session file exists."""
        return self._session_path.exists()