"""Authentication. Two modes, chosen by the same BACKEND env var as the
data layer:

  BACKEND=memory   -> mocked accounts below, no network, good for dev/demo.
  BACKEND=supabase -> real Supabase Auth (email+password), with the role
                      read from the `profiles` table (see supabase_schema.sql).

Either way, pages only ever call `AuthService.authenticate(email, password)`
and get back a User or None -- nothing above this file needs to know which
mode is active.
"""
from typing import Optional
from models import User, Role
import config

_MOCK_USERS = {
    "partner@example.com": {"name": "Amina Hassan", "role": Role.PARTNER},
    "worker@example.com": {"name": "Brian Kimani", "role": Role.WORKER},
}


class AuthService:
    def __init__(self):
        self._client = None
        if config.BACKEND == "supabase" and config.SUPABASE_URL and config.SUPABASE_KEY:
            from supabase import create_client
            self._client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        email = (email or "").strip().lower()
        password = (password or "").strip()
        if not email or not password:
            return None
        if self._client:
            return self._authenticate_supabase(email, password)
        return self._authenticate_mock(email, password)

    def _authenticate_mock(self, email: str, password: str) -> Optional[User]:
        record = _MOCK_USERS.get(email)
        if not record:
            return None
        # Mock rule: any non-empty password is accepted for the demo accounts.
        return User(email=email, name=record["name"], role=record["role"])

    def _authenticate_supabase(self, email: str, password: str) -> Optional[User]:
        try:
            result = self._client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception:
            return None
        if not result or not result.user:
            return None
        profile_rows = self._client.table("profiles").select("*").eq("id", result.user.id).execute().data
        if not profile_rows:
            return None
        profile = profile_rows[0]
        return User(email=profile["email"], name=profile["name"], role=Role(profile["role"]))
