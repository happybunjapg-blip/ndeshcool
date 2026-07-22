"""Tests for the AuthService.

Since the production auth depends on Supabase connectivity, these tests
verify that the service initializes and handles missing configuration gracefully.
"""
import unittest
from unittest.mock import patch, MagicMock

from services.auth_service import AuthService
from services.session_service import SessionService
from models import Role


class AuthServiceTests(unittest.TestCase):
    def test_requires_supabase_configured(self):
        """AuthService raises AuthError when Supabase is not configured."""
        from services.auth_service import AuthError
        
        with patch("config.SUPABASE_URL", ""), patch("config.SUPABASE_KEY", ""):
            service = AuthService()
            with self.assertRaises(AuthError):
                service.authenticate("test@example.com", "password")

    def test_init_without_session(self):
        """AuthService should initialize even without session tokens."""
        service = AuthService()
        # Should not crash
        self.assertIsNotNone(service)

    def test_get_saved_session_no_token(self):
        """get_saved_session returns None when no token is saved."""
        service = AuthService()
        result = service.get_saved_session()
        self.assertIsNone(result)

    def test_sign_out_clears_session(self):
        """sign_out should clear session without crashing."""
        service = AuthService()
        # Should not raise
        service.sign_out()


if __name__ == "__main__":
    unittest.main()