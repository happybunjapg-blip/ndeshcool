import unittest

from services.auth_service import AuthService
from models import Role


class DummyAuth:
    def __init__(self, fail=False):
        self.fail = fail

    def sign_in_with_password(self, _credentials):
        if self.fail:
            raise RuntimeError("supabase auth unavailable")
        return type("Result", (), {"user": None})()


class DummyTable:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Result", (), {"data": self._rows})()


class DummyClient:
    def __init__(self, fail=False, rows=None):
        self.auth = DummyAuth(fail=fail)
        self._rows = rows or []

    def table(self, *_args, **_kwargs):
        return DummyTable(self._rows)


class AuthServiceTests(unittest.TestCase):
    def test_demo_accounts_fallback_when_supabase_auth_fails(self):
        service = AuthService.__new__(AuthService)
        service._client = DummyClient(fail=True)

        user = service._authenticate_supabase("partner@example.com", "anything")

        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.PARTNER)
        self.assertEqual(user.name, "Amina Hassan")

    def test_unknown_account_still_fails_when_supabase_auth_fails(self):
        service = AuthService.__new__(AuthService)
        service._client = DummyClient(fail=True)

        user = service._authenticate_supabase("unknown@example.com", "anything")

        self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
