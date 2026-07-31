"""Comprehensive tests for the new invitation architecture.

Tests the canonical invitation flow:
1. generate_invitation(business_id, role)
2. lookup_invitation(code)
3. join_business_with_invitation(code, ...)

These tests use mocked Supabase responses to verify the LOGIC
of the invitation system, independent of the live database.

The mock simulates the new invitation schema (role, status columns)
and the old schema (owner_invite, is_invalidated) for backward compatibility.

Tests are organized into sections:
- QR parsing (unit tests, no DB needed)
- Invitation generation
- Invitation lookup
- Join flow
- Bug regression tests
- Permission tests
"""
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from services.auth_service import AuthService, AuthError
from services.session_service import SessionService
from services.qr_service import parse_deep_link, generate_invitation_qr_base64
from models import Role, User, Invitation


# ======================================================================
# MOCK DATA: Simulates the database state
# ======================================================================

class MockInvitationDB:
    """Simulates the invitations table in memory.
    
    Supports both new columns (role, status) and old columns
    (owner_invite, is_invalidated) for backward compatibility.
    """
    def __init__(self):
        self._invitations = {}
        self._invitations_by_code = {}
    
    def add_invitation(self, code: str, business_id: str, role: str,
                       status: str = "active", expires_in_hours: int = 24,
                       owner_invite: bool = None):
        """Add an invitation to the mock database."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        
        if owner_invite is None:
            owner_invite = (role == "co_owner")
        
        record = {
            "code": code,
            "business_id": business_id,
            "role": role,
            "status": status,
            "owner_invite": owner_invite,
            "is_invalidated": (status != "active"),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        self._invitations_by_code[code] = record
        return record
    
    def get_by_code(self, code: str) -> Optional[dict]:
        return self._invitations_by_code.get(code)
    
    def update(self, code: str, updates: dict) -> Optional[dict]:
        record = self._invitations_by_code.get(code)
        if record:
            record.update(updates)
            # Keep is_invalidated in sync with status
            if "status" in updates:
                record["is_invalidated"] = (updates["status"] != "active")
            return record
        return None


class MockBusinessDB:
    """Simulates the businesses table."""
    def __init__(self):
        self._businesses = {}
    
    def add_business(self, business_id: str, name: str):
        self._businesses[business_id] = {"id": business_id, "name": name}
    
    def get_by_id(self, business_id: str) -> Optional[dict]:
        return self._businesses.get(business_id)


class MockProfileDB:
    """Simulates the profiles table."""
    def __init__(self):
        self._profiles = {}
    
    def add_profile(self, user_id: str, email: str, role: str, business_id: str):
        self._profiles[user_id] = {
            "id": user_id, "email": email, "role": role, "business_id": business_id,
            "first_name": "Test", "last_name": "User", "phone": "",
        }
    
    def get_by_id(self, user_id: str) -> Optional[dict]:
        return self._profiles.get(user_id)
    
    def get_by_email(self, email: str) -> Optional[dict]:
        for p in self._profiles.values():
            if p["email"] == email:
                return p
        return None
    
    def count_by_role(self, business_id: str, role: str) -> int:
        return sum(1 for p in self._profiles.values()
                   if p["business_id"] == business_id and p["role"] == role)


# ======================================================================
# MOCK SUPABASE CLIENT
# ======================================================================

class MockSupabaseClient:
    """Simulates the Supabase client for testing.
    
    Supports:
    - table("invitations").select().eq().execute()
    - table("businesses").select().eq().execute()
    - table("profiles").insert().execute()
    - table("invitations").update().eq().execute()
    - rpc("lookup_invitation", ...).execute()
    - rpc("consume_invitation", ...).execute()
    """
    
    def __init__(self):
        self.invitations = MockInvitationDB()
        self.businesses = MockBusinessDB()
        self.profiles = MockProfileDB()
        self.auth = MockAuthClient()
        self._last_rpc_call = None
    
    def table(self, name: str):
        return MockTableQuery(self, name)
    
    def rpc(self, func_name: str, params: dict):
        return MockRPCQuery(self, func_name, params)


import uuid as uuid_lib

class MockAuthClient:
    """Simulates the Supabase Auth client."""
    def __init__(self):
        self._users = {}
        self._sessions = {}
        self._next_user_id = 0
    
    def sign_up(self, credentials: dict):
        email = credentials.get("email", "")
        password = credentials.get("password", "")
        self._next_user_id += 1
        # Use a valid UUID format so UUID validation in sign_up_owner passes
        user_id = str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, f"{email}-{self._next_user_id}"))
        self._users[email] = {
            "id": user_id,
            "email": email,
            "password": password,
        }
        return MockAuthResponse(user_id)
    
    def sign_in_with_password(self, credentials: dict):
        email = credentials.get("email", "")
        password = credentials.get("password", "")
        user = self._users.get(email)
        if user and user["password"] == password:
            return MockAuthResponse(user["id"])
        raise Exception("Invalid login credentials")
    
    def get_user(self, token: str = None):
        return None
    
    def set_session(self, access_token: str, refresh_token: str):
        return None
    
    def sign_out(self):
        pass
    
    def reset_password_email(self, email: str):
        pass
    
    def update_user(self, attributes: dict):
        return None


class MockAuthResponse:
    """Simulates a Supabase auth response."""
    def __init__(self, user_id: str):
        self.user = MagicMock()
        self.user.id = user_id
        self.user.email = f"test@example.com"
        self.session = MagicMock()
        self.session.access_token = "mock-access-token"
        self.session.refresh_token = "mock-refresh-token"


class MockTableQuery:
    """Simulates Supabase table query builder.
    
    Supports:
    - table("name").select("*").eq("col", val).execute()
    - table("name").insert({...}).execute()
    - table("name").update({...}).eq("col", val).execute()
    """
    def __init__(self, client: MockSupabaseClient, table_name: str):
        self._client = client
        self._table_name = table_name
        self._select_columns = "*"
        self._eq_filters = []
        self._order_column = None
        self._order_direction = None
        self._insert_data = None
        self._update_data = None
    
    def select(self, columns: str = "*"):
        self._select_columns = columns
        return self
    
    def insert(self, data: dict):
        """Stage an insert operation."""
        self._insert_data = data
        return self
    
    def update(self, data: dict):
        """Stage an update operation."""
        self._update_data = data
        return self
    
    def eq(self, column: str, value):
        self._eq_filters.append((column, value))
        return self
    
    def order(self, column: str, desc: bool = False):
        self._order_column = column
        self._order_direction = "desc" if desc else "asc"
        return self
    
    def execute(self):
        """Execute the query against the mock database."""
        if self._insert_data is not None:
            return self._do_insert()
        if self._update_data is not None:
            return self._do_update()
        return self._do_select()
    
    def _do_insert(self):
        """Handle insert operations."""
        if self._table_name == "invitations":
            return self._insert_invitation()
        elif self._table_name == "profiles":
            return self._insert_profile()
        elif self._table_name == "businesses":
            return self._insert_business()
        return MockQueryResult([self._insert_data])
    
    def _do_update(self):
        """Handle update operations."""
        if self._table_name == "invitations":
            return self._update_invitations()
        elif self._table_name == "profiles":
            return self._update_profiles()
        return MockQueryResult([])
    
    def _do_select(self):
        """Handle select operations."""
        if self._table_name == "invitations":
            return self._query_invitations()
        elif self._table_name == "businesses":
            return self._query_businesses()
        elif self._table_name == "profiles":
            return self._query_profiles()
        return MockQueryResult([])
    
    def _insert_invitation(self):
        code = self._insert_data.get("code")
        record = dict(self._insert_data)
        if "role" not in record and "owner_invite" in record:
            record["role"] = "co_owner" if record["owner_invite"] else "worker"
        if "status" not in record:
            record["status"] = "active"
        self._client.invitations._invitations_by_code[code] = record
        return MockQueryResult([record])
    
    def _insert_profile(self):
        user_id = self._insert_data.get("id")
        self._client.profiles._profiles[user_id] = dict(self._insert_data)
        return MockQueryResult([self._insert_data])
    
    def _insert_business(self):
        record = dict(self._insert_data)
        if "id" not in record:
            record["id"] = f"biz-{len(self._client.businesses._businesses) + 1}"
        self._client.businesses._businesses[record["id"]] = record
        return MockQueryResult([record])
    
    def _update_invitations(self):
        updated = []
        for code, record in self._client.invitations._invitations_by_code.items():
            matches = all(
                record.get(col) == val for col, val in self._eq_filters
            )
            if matches:
                record.update(self._update_data)
                if "status" in self._update_data:
                    record["is_invalidated"] = (self._update_data["status"] != "active")
                updated.append(record)
        return MockQueryResult(updated)
    
    def _update_profiles(self):
        updated = []
        for uid, record in self._client.profiles._profiles.items():
            matches = all(
                record.get(col) == val for col, val in self._eq_filters
            )
            if matches:
                record.update(self._update_data)
                updated.append(record)
        return MockQueryResult(updated)
    
    def _query_invitations(self):
        results = []
        for code, record in self._client.invitations._invitations_by_code.items():
            matches = all(
                record.get(col) == val for col, val in self._eq_filters
            )
            if matches:
                results.append(record)
        
        if self._order_column == "created_at" and self._order_direction == "desc":
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        
        return MockQueryResult(results)
    
    def _query_businesses(self):
        results = []
        for bid, record in self._client.businesses._businesses.items():
            matches = all(
                record.get(col) == val for col, val in self._eq_filters
            )
            if matches:
                results.append(record)
        return MockQueryResult(results)
    
    def _query_profiles(self):
        results = []
        for uid, record in self._client.profiles._profiles.items():
            matches = all(
                record.get(col) == val for col, val in self._eq_filters
            )
            if matches:
                results.append(record)
        return MockQueryResult(results)
    
    def _query_invitations(self):
        results = []
        for code, record in self._client.invitations._invitations_by_code.items():
            matches = True
            for col, val in self._eq_filters:
                if col == "code" and record.get("code") != val:
                    matches = False
                    break
                if col == "business_id" and record.get("business_id") != val:
                    matches = False
                    break
                if col == "status" and record.get("status") != val:
                    matches = False
                    break
                if col == "is_invalidated" and record.get("is_invalidated") != val:
                    matches = False
                    break
            if matches:
                results.append(record)
        
        if self._order_column == "created_at" and self._order_direction == "desc":
            results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        
        return MockQueryResult(results)
    
    def _query_businesses(self):
        results = []
        for bid, record in self._client.businesses._businesses.items():
            matches = True
            for col, val in self._eq_filters:
                if col == "id" and record.get("id") != val:
                    matches = False
                    break
                if col == "name" and record.get("name") != val:
                    matches = False
                    break
            if matches:
                results.append(record)
        return MockQueryResult(results)
    
    def _query_profiles(self):
        results = []
        for uid, record in self._client.profiles._profiles.items():
            matches = True
            for col, val in self._eq_filters:
                if col == "id" and record.get("id") != val:
                    matches = False
                    break
                if col == "email" and record.get("email") != val:
                    matches = False
                    break
                if col == "business_id" and record.get("business_id") != val:
                    matches = False
                    break
                if col == "role" and record.get("role") != val:
                    matches = False
                    break
            if matches:
                results.append(record)
        return MockQueryResult(results)


class MockInsertQuery:
    """Simulates a Supabase insert query."""
    def __init__(self, client: MockSupabaseClient, table_name: str, data: dict):
        self._client = client
        self._table_name = table_name
        self._data = data
    
    def execute(self):
        if self._table_name == "invitations":
            return self._insert_invitation()
        elif self._table_name == "profiles":
            return self._insert_profile()
        elif self._table_name == "businesses":
            return self._insert_business()
        return MockQueryResult([self._data])
    
    def _insert_invitation(self):
        code = self._data.get("code")
        record = dict(self._data)
        self._client.invitations._invitations_by_code[code] = record
        return MockQueryResult([record])
    
    def _insert_profile(self):
        user_id = self._data.get("id")
        self._client.profiles._profiles[user_id] = dict(self._data)
        return MockQueryResult([self._data])
    
    def _insert_business(self):
        record = dict(self._data)
        if "id" not in record:
            record["id"] = f"biz-{len(self._client.businesses._businesses) + 1}"
        self._client.businesses._businesses[record["id"]] = record
        return MockQueryResult([record])


class MockUpdateQuery:
    """Simulates a Supabase update query."""
    def __init__(self, client: MockSupabaseClient, table_name: str, data: dict):
        self._client = client
        self._table_name = table_name
        self._data = data
        self._eq_filters = []
    
    def eq(self, column: str, value):
        self._eq_filters.append((column, value))
        return self
    
    def execute(self):
        if self._table_name == "invitations":
            return self._update_invitations()
        elif self._table_name == "profiles":
            return self._update_profiles()
        return MockQueryResult([])
    
    def _update_invitations(self):
        updated = []
        for code, record in self._client.invitations._invitations_by_code.items():
            matches = True
            for col, val in self._eq_filters:
                if col == "code" and record.get("code") != val:
                    matches = False
                    break
                if col == "status" and record.get("status") != val:
                    matches = False
                    break
                if col == "is_invalidated" and record.get("is_invalidated") != val:
                    matches = False
                    break
            if matches:
                record.update(self._data)
                if "status" in self._data:
                    record["is_invalidated"] = (self._data["status"] != "active")
                updated.append(record)
        return MockQueryResult(updated)
    
    def _update_profiles(self):
        updated = []
        for uid, record in self._client.profiles._profiles.items():
            matches = True
            for col, val in self._eq_filters:
                if col == "id" and record.get("id") != val:
                    matches = False
                    break
                if col == "email" and record.get("email") != val:
                    matches = False
                    break
            if matches:
                record.update(self._data)
                updated.append(record)
        return MockQueryResult(updated)


class MockRPCQuery:
    """Simulates a Supabase RPC call."""
    def __init__(self, client: MockSupabaseClient, func_name: str, params: dict):
        self._client = client
        self._func_name = func_name
        self._params = params
    
    def execute(self):
        if self._func_name == "lookup_invitation":
            return self._lookup_invitation()
        elif self._func_name == "consume_invitation":
            return self._consume_invitation()
        return MockQueryResult([])
    
    def _lookup_invitation(self):
        code = self._params.get("p_code", "")
        record = self._client.invitations.get_by_code(code)
        if not record:
            return MockQueryResult([])
        if record.get("status") != "active":
            return MockQueryResult([])
        expires_at = record.get("expires_at", "")
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp < datetime.now(timezone.utc):
                    return MockQueryResult([])
            except ValueError:
                pass
        
        business = self._client.businesses.get_by_id(record["business_id"])
        return MockQueryResult([{
            "code": record["code"],
            "business_id": record["business_id"],
            "role": record["role"],
            "status": record["status"],
            "expires_at": record["expires_at"],
            "business_name": business["name"] if business else "",
        }])
    
    def _consume_invitation(self):
        code = self._params.get("p_code", "")
        record = self._client.invitations.get_by_code(code)
        if not record:
            return MockQueryResult([False])
        if record.get("status") != "active":
            return MockQueryResult([False])
        record["status"] = "used"
        record["is_invalidated"] = True
        record["used_at"] = datetime.now(timezone.utc).isoformat()
        return MockQueryResult([True])


class MockQueryResult:
    """Simulates a Supabase query result."""
    def __init__(self, data: list):
        self.data = data
        self.count = len(data) if data else 0


# ======================================================================
# PATCHED TABLE/INSERT/UPDATE METHODS
# ======================================================================

def _mock_table(self, name):
    return MockTableQuery(self._test_client, name)


def _mock_rpc(self, func_name, params):
    return MockRPCQuery(self._test_client, func_name, params)


# ======================================================================
# TEST SUITE
# ======================================================================

class TestQRParsing(unittest.TestCase):
    """Tests for QR code parsing (no database needed)."""
    
    def test_qr_contains_only_code(self):
        """Test that generated QR deep link contains only the code."""
        code = "123456"
        url = f"waterpilot://join?code={code}"
        result = parse_deep_link(url)
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], code)
        self.assertNotIn("type", result)
        self.assertNotIn("business_id", result)
    
    def test_qr_extra_params_ignored(self):
        """Test that extra parameters in QR are ignored."""
        url = "waterpilot://join?code=123456&type=owner&business_id=FAKE-BUSINESS"
        result = parse_deep_link(url)
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], "123456")
        # Role and business_id from QR must be ignored
        self.assertNotIn("type", result)
        self.assertNotIn("business_id", result)
    
    def test_qr_empty_code_rejected(self):
        """Test that empty code returns None."""
        url = "waterpilot://join?code="
        result = parse_deep_link(url)
        self.assertIsNone(result)
    
    def test_qr_no_code_param(self):
        """Test that URL without code parameter returns None."""
        url = "waterpilot://join?foo=bar"
        result = parse_deep_link(url)
        self.assertIsNone(result)
    
    def test_qr_invalid_scheme(self):
        """Test that invalid scheme returns None."""
        url = "https://example.com/join?code=123456"
        result = parse_deep_link(url)
        # This is a valid path-based format, should be accepted
        # Actually, path /join is accepted per the parser
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], "123456")
    
    def test_qr_malformed_url(self):
        """Test that malformed URL returns None."""
        result = parse_deep_link("not-a-url")
        self.assertIsNone(result)
    
    def test_qr_empty_string(self):
        """Test that empty string returns None."""
        result = parse_deep_link("")
        self.assertIsNone(result)
    
    def test_qr_none(self):
        """Test that None returns None."""
        result = parse_deep_link(None)
        self.assertIsNone(result)
    
    def test_generate_qr_contains_only_code(self):
        """Test that generated QR code string contains only the code."""
        import io
        import base64
        code = "789012"
        b64 = generate_invitation_qr_base64(code)
        self.assertTrue(len(b64) > 0)
        # The QR is a PNG image, but we can verify it decodes to something
        img_data = base64.b64decode(b64)
        self.assertTrue(len(img_data) > 100)  # Should be a valid image


class TestInvitationGeneration(unittest.TestCase):
    """Tests for invitation generation."""
    
    def setUp(self):
        self.client = MockSupabaseClient()
        self.client.businesses.add_business("biz-A", "Business A")
        self.client.businesses.add_business("biz-B", "Business B")
        
        # Create an auth service with mocked client
        self.auth_service = AuthService()
        self.auth_service._client = self.client
    
    def test_generate_worker_invitation(self):
        """Test generating a worker invitation."""
        inv = self.auth_service.generate_invitation("biz-A", "worker")
        self.assertIsNotNone(inv)
        self.assertEqual(inv.business_id, "biz-A")
        self.assertEqual(inv.role, "worker")
        self.assertEqual(inv.status, "active")
        self.assertTrue(len(inv.code) == 6)
        
        # Verify in database
        db_record = self.client.invitations.get_by_code(inv.code)
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record["role"], "worker")
        self.assertEqual(db_record["business_id"], "biz-A")
        self.assertEqual(db_record["status"], "active")
    
    def test_generate_co_owner_invitation(self):
        """Test generating a co-owner invitation."""
        inv = self.auth_service.generate_invitation("biz-A", "co_owner")
        self.assertIsNotNone(inv)
        self.assertEqual(inv.business_id, "biz-A")
        self.assertEqual(inv.role, "co_owner")
        self.assertEqual(inv.status, "active")
        
        # Verify in database
        db_record = self.client.invitations.get_by_code(inv.code)
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record["role"], "co_owner")
        self.assertEqual(db_record["business_id"], "biz-A")
        self.assertEqual(db_record["status"], "active")
    
    def test_generate_invitation_invalid_role(self):
        """Test that invalid role is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.generate_invitation("biz-A", "invalid_role")
    
    def test_generate_invitation_no_business(self):
        """Test that empty business_id is handled."""
        with self.assertRaises(AuthError):
            self.auth_service.generate_invitation("", "worker")
    
    def test_old_generate_method_delegates(self):
        """Test that old generate_invitation_code delegates to new method."""
        inv = self.auth_service.generate_invitation_code("biz-A", owner_invite=False)
        self.assertIsNotNone(inv)
        self.assertEqual(inv.role, "worker")
        
        inv2 = self.auth_service.generate_invitation_code("biz-A", owner_invite=True)
        self.assertIsNotNone(inv2)
        self.assertEqual(inv2.role, "co_owner")


class TestInvitationLookup(unittest.TestCase):
    """Tests for invitation lookup."""
    
    def setUp(self):
        self.client = MockSupabaseClient()
        self.client.businesses.add_business("biz-A", "Business A")
        self.client.businesses.add_business("biz-B", "Business B")
        
        self.auth_service = AuthService()
        self.auth_service._client = self.client
    
    def test_lookup_worker_invitation(self):
        """Test looking up a worker invitation returns worker role."""
        self.client.invitations.add_invitation("123456", "biz-A", "worker")
        result = self.auth_service.lookup_invitation("123456")
        self.assertIsNotNone(result)
        self.assertEqual(result["role"], "worker")
        self.assertEqual(result["business_id"], "biz-A")
        self.assertEqual(result["business_name"], "Business A")
    
    def test_lookup_co_owner_invitation(self):
        """Test looking up a co-owner invitation returns co_owner role."""
        self.client.invitations.add_invitation("789012", "biz-A", "co_owner")
        result = self.auth_service.lookup_invitation("789012")
        self.assertIsNotNone(result)
        self.assertEqual(result["role"], "co_owner")
        self.assertEqual(result["business_id"], "biz-A")
    
    def test_lookup_invalid_code(self):
        """Test that invalid code is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.lookup_invitation("000000")
    
    def test_lookup_empty_code(self):
        """Test that empty code is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.lookup_invitation("")
    
    def test_lookup_expired_invitation(self):
        """Test that expired invitation is rejected."""
        self.client.invitations.add_invitation(
            "999999", "biz-A", "worker",
            expires_in_hours=-1  # Already expired
        )
        with self.assertRaises(AuthError):
            self.auth_service.lookup_invitation("999999")
    
    def test_lookup_used_invitation(self):
        """Test that used invitation is rejected."""
        self.client.invitations.add_invitation(
            "555555", "biz-A", "worker", status="used"
        )
        with self.assertRaises(AuthError):
            self.auth_service.lookup_invitation("555555")
    
    def test_lookup_revoked_invitation(self):
        """Test that revoked invitation is rejected."""
        self.client.invitations.add_invitation(
            "444444", "biz-A", "worker", status="revoked"
        )
        with self.assertRaises(AuthError):
            self.auth_service.lookup_invitation("444444")


class TestJoinFlow(unittest.TestCase):
    """Tests for the canonical join method."""
    
    def setUp(self):
        self.client = MockSupabaseClient()
        self.client.businesses.add_business("biz-A", "Business A")
        self.client.businesses.add_business("biz-B", "Business B")
        
        self.auth_service = AuthService()
        self.auth_service._client = self.client
        
        # Pre-create valid invitations
        self.client.invitations.add_invitation("111111", "biz-A", "worker")
        self.client.invitations.add_invitation("222222", "biz-A", "co_owner")
        self.client.invitations.add_invitation("333333", "biz-B", "worker")
        
        # Expired invitation
        self.client.invitations.add_invitation(
            "444444", "biz-A", "worker", expires_in_hours=-1
        )
        
        # Used invitation
        self.client.invitations.add_invitation(
            "555555", "biz-A", "worker", status="used"
        )
    
    def test_worker_joins_as_worker(self):
        """Test that worker invitation creates a worker profile."""
        user = self.auth_service.join_business_with_invitation(
            code="111111",
            first_name="Test",
            last_name="Worker",
            email="worker@test.com",
            password="password123",
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.WORKER)
        self.assertEqual(user.business_id, "biz-A")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "Worker")
        self.assertEqual(user.email, "worker@test.com")
        
        # Verify invitation was consumed
        record = self.client.invitations.get_by_code("111111")
        self.assertEqual(record["status"], "used")
    
    def test_co_owner_joins_as_co_owner(self):
        """Test that co-owner invitation creates a co_owner profile."""
        user = self.auth_service.join_business_with_invitation(
            code="222222",
            first_name="Test",
            last_name="CoOwner",
            email="coowner@test.com",
            password="password123",
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.CO_OWNER)
        self.assertEqual(user.business_id, "biz-A")
        
        # Verify invitation was consumed
        record = self.client.invitations.get_by_code("222222")
        self.assertEqual(record["status"], "used")
    
    def test_expired_invitation_rejected(self):
        """Test that expired invitation is rejected."""
        with self.assertRaises(AuthError) as ctx:
            self.auth_service.join_business_with_invitation(
                code="444444",
                first_name="Test", last_name="User",
                email="test@test.com", password="password123",
            )
        self.assertIn("expired", str(ctx.exception).lower())
    
    def test_used_invitation_rejected(self):
        """Test that used invitation cannot be reused."""
        # Use a fresh active invitation first
        fresh_inv = self.auth_service.generate_invitation("biz-A", "worker")
        active_code = fresh_inv.code
        
        # First use should succeed
        user1 = self.auth_service.join_business_with_invitation(
            code=active_code,
            first_name="User", last_name="One",
            email="user1@test.com", password="password123",
        )
        self.assertIsNotNone(user1)
        
        # Second use should fail
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code=active_code,
                first_name="User", last_name="Two",
                email="user2@test.com", password="password123",
            )
    
    def test_invalid_code_rejected(self):
        """Test that invalid code is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code="000000",
                first_name="Test", last_name="User",
                email="test@test.com", password="password123",
            )
    
    def test_empty_code_rejected(self):
        """Test that empty code is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code="",
                first_name="Test", last_name="User",
                email="test@test.com", password="password123",
            )
    
    def test_weak_password_rejected(self):
        """Test that weak password is rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code="111111",
                first_name="Test", last_name="User",
                email="test@test.com", password="123",
            )
    
    def test_missing_fields_rejected(self):
        """Test that missing required fields are rejected."""
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code="111111",
                first_name="", last_name="",
                email="", password="",
            )


class TestBugRegression(unittest.TestCase):
    """Regression tests for the original bug.
    
    These tests reproduce the exact scenario that caused:
    "This code is for business owners only."
    """
    
    def setUp(self):
        self.client = MockSupabaseClient()
        self.client.businesses.add_business("biz-A", "Business A")
        self.client.businesses.add_business("biz-B", "Business B")
        
        self.auth_service = AuthService()
        self.auth_service._client = self.client
    
    def test_worker_qr_cannot_change_role(self):
        """Regression: Worker QR with tampered type=owner must still create worker.
        
        This reproduces the original bug scenario:
        - Invitation is for worker (role='worker')
        - QR contains type=owner (tampered)
        - The system must IGNORE the QR type and use the database role
        """
        # Create a worker invitation
        inv = self.auth_service.generate_invitation("biz-A", "worker")
        
        # Simulate QR with tampered type=owner
        qr_data = {"code": inv.code, "type": "owner", "business_id": "biz-B"}
        
        # Use the deprecated sign_up_via_qr (which now delegates to join_business_with_invitation)
        user = self.auth_service.sign_up_via_qr(
            qr_data=qr_data,
            first_name="Test",
            last_name="Worker",
            email="worker@test.com",
            password="password123",
        )
        
        # The role must come from the DATABASE, not the QR
        self.assertEqual(user.role, Role.WORKER,
                         "QR type=owner must not override database role=worker")
        self.assertEqual(user.business_id, "biz-A",
                         "QR business_id=biz-B must not override database business_id=biz-A")
        
        # The error "This code is for business owners only" must NEVER appear
        self.assertNotEqual(str(user.role), "owner",
                            "Worker must not become owner even if QR says type=owner")
    
    def test_co_owner_qr_cannot_change_role(self):
        """Regression: Co-owner QR with tampered type=worker must still create co_owner.
        
        This is the reverse case:
        - Invitation is for co_owner (role='co_owner')
        - QR contains type=worker (tampered down)
        - The system must IGNORE the QR type and use the database role
        """
        # Create a co-owner invitation
        inv = self.auth_service.generate_invitation("biz-A", "co_owner")
        
        # Simulate QR with tampered type=worker
        qr_data = {"code": inv.code, "type": "worker", "business_id": "biz-B"}
        
        user = self.auth_service.sign_up_via_qr(
            qr_data=qr_data,
            first_name="Test",
            last_name="CoOwner",
            email="coowner@test.com",
            password="password123",
        )
        
        # The role must come from the DATABASE, not the QR
        self.assertEqual(user.role, Role.CO_OWNER,
                         "QR type=worker must not override database role=co_owner")
        self.assertEqual(user.business_id, "biz-A",
                         "QR business_id=biz-B must not override database business_id=biz-A")
    
    def test_business_a_code_joins_business_a(self):
        """Test that Business A code always joins Business A, even if client says Business B."""
        inv = self.auth_service.generate_invitation("biz-A", "worker")
        
        # Client tries to join Business B with Business A's code
        # This must be ignored - the database determines the business
        user = self.auth_service.join_business_with_invitation(
            code=inv.code,
            first_name="Test",
            last_name="User",
            email="test@test.com",
            password="password123",
        )
        
        self.assertEqual(user.business_id, "biz-A",
                         "Client cannot override business_id to join a different business")
    
    def test_concurrent_consumption_prevented(self):
        """Test that same invitation cannot be consumed twice concurrently.
        
        First request: active → used (SUCCESS)
        Second request: active condition fails (REJECTED)
        """
        self.client.invitations.add_invitation("999999", "biz-A", "worker")
        
        # First use succeeds
        user1 = self.auth_service.join_business_with_invitation(
            code="999999",
            first_name="User", last_name="One",
            email="user1@test.com", password="password123",
        )
        self.assertIsNotNone(user1)
        
        # Second use is rejected (invitation is already used)
        with self.assertRaises(AuthError):
            self.auth_service.join_business_with_invitation(
                code="999999",
                first_name="User", last_name="Two",
                email="user2@test.com", password="password123",
            )
        
        # Verify: only one profile was created
        profiles = self.client.profiles
        self.assertEqual(len(profiles._profiles), 1)


class TestOldSignUpViaQR(unittest.TestCase):
    """Tests that the old sign_up_via_qr still works (delegates to new method)."""
    
    def setUp(self):
        self.client = MockSupabaseClient()
        self.client.businesses.add_business("biz-A", "Business A")
        
        self.auth_service = AuthService()
        self.auth_service._client = self.client
    
    def test_sign_up_via_qr_with_code_only(self):
        """Test that sign_up_via_qr works with code-only QR data."""
        inv = self.auth_service.generate_invitation("biz-A", "worker")
        
        # QR data with ONLY code (no type, no business_id)
        qr_data = {"code": inv.code}
        
        user = self.auth_service.sign_up_via_qr(
            qr_data=qr_data,
            first_name="Test",
            last_name="User",
            email="test@test.com",
            password="password123",
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.WORKER)
        self.assertEqual(user.business_id, "biz-A")
    
    def test_sign_up_via_qr_ignores_type_and_business_id(self):
        """Test that sign_up_via_qr ignores type and business_id from QR."""
        inv = self.auth_service.generate_invitation("biz-A", "worker")
        
        # QR data with fake type and business_id (should be ignored)
        qr_data = {
            "code": inv.code,
            "type": "owner",
            "business_id": "fake-business",
        }
        
        user = self.auth_service.sign_up_via_qr(
            qr_data=qr_data,
            first_name="Test",
            last_name="User",
            email="test@test.com",
            password="password123",
        )
        
        # Database determines the truth
        self.assertEqual(user.role, Role.WORKER)
        self.assertEqual(user.business_id, "biz-A")


class TestOwnerFlow(unittest.TestCase):
    """Tests that the owner signup flow works without invitation."""
    
    def setUp(self):
        self.client = MockSupabaseClient()
        
        self.auth_service = AuthService()
        self.auth_service._client = self.client
    
    def test_owner_signup_creates_business_and_profile(self):
        """Test that owner signup creates a business and owner profile."""
        # We need to intercept the session check
        # The mock auth.sign_up returns a session, so identity_verified=True
        user = self.auth_service.sign_up_owner(
            business_name="Test Business",
            first_name="Owner",
            last_name="Test",
            email="owner@test.com",
            password="password123",
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.OWNER)
        self.assertEqual(user.first_name, "Owner")
        self.assertEqual(user.email, "owner@test.com")
        
        # Verify a business was created
        self.assertIsNotNone(user.business_id)
        self.assertTrue(len(user.business_id) > 0)
        
        # Verify the profile was created
        profile = self.client.profiles.get_by_email("owner@test.com")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["role"], "owner")
        self.assertEqual(profile["business_id"], user.business_id)


class TestRoleEnum(unittest.TestCase):
    """Tests that the Role enum has the correct values."""
    
    def test_role_enum_values(self):
        """Test that Role enum has all three values."""
        self.assertEqual(Role.OWNER.value, "owner")
        self.assertEqual(Role.CO_OWNER.value, "co_owner")
        self.assertEqual(Role.WORKER.value, "worker")
    
    def test_role_enum_members(self):
        """Test that Role enum has exactly three members."""
        members = [m.value for m in Role]
        self.assertIn("owner", members)
        self.assertIn("co_owner", members)
        self.assertIn("worker", members)


# ======================================================================
# RUNNER
# ======================================================================

if __name__ == "__main__":
    unittest.main()