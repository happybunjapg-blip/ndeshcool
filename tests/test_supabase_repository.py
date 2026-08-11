import unittest

from postgrest.exceptions import APIError

from backend.supabase_repository import SupabaseRepository
from backend.repository import DuplicateBusinessDayError
from models import BusinessDay, BusinessDayStatus


class FakeTable:
    def __init__(self, error=None):
        self.error = error

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.error:
            raise self.error
        return type("Result", (), {"data": []})()


class FakeClient:
    def __init__(self, error=None):
        self.error = error

    def table(self, *_args, **_kwargs):
        return FakeTable(self.error)


class SupabaseRepositoryTests(unittest.TestCase):
    def test_list_products_returns_empty_when_tables_are_missing(self):
        repo = SupabaseRepository.__new__(SupabaseRepository)
        repo.client = FakeClient(APIError({"message": "Could not find the table", "code": "PGRST205"}))
        repo._change_callback = None

        self.assertEqual(repo.list_products(), [])

    def test_open_business_day_ignores_missing_table(self):
        repo = SupabaseRepository.__new__(SupabaseRepository)
        repo.client = FakeClient(APIError({"message": "Could not find the table", "code": "PGRST205"}))
        repo._change_callback = None

        business_day = BusinessDay(
            id="BD-TEST",
            opened_at="2026-07-09T00:00:00",
            opened_by="tester",
            status=BusinessDayStatus.OPEN,
            opening_note="",
        )

        repo.open_business_day(business_day)

    def test_open_business_day_translates_unique_violation(self):
        """The one_open_business_day_per_business constraint firing (e.g.
        a co-owner/other worker opened a day first) must surface as
        DuplicateBusinessDayError, not a raw Postgrest APIError, so the
        service layer can recover by reusing the existing day instead of
        treating it as an unexpected failure."""
        repo = SupabaseRepository.__new__(SupabaseRepository)
        repo.client = FakeClient(APIError({
            "message": 'duplicate key value violates unique constraint '
                        '"one_open_business_day_per_business"',
            "code": "23505",
        }))
        repo._business_id = "biz-1"
        repo._change_callback = None

        business_day = BusinessDay(
            id="BD-TEST", opened_at="2026-07-09T00:00:00", opened_by="worker@biz.com",
            status=BusinessDayStatus.OPEN, opening_note="",
        )

        with self.assertRaises(DuplicateBusinessDayError):
            repo.open_business_day(business_day)

    def test_open_business_day_reraises_other_api_errors(self):
        """Unrelated Postgrest errors (RLS rejection, network, schema
        mismatch, a different unique/check constraint, etc.) must NOT be
        swallowed or mistaken for the business-day race -- they should
        propagate unchanged."""
        repo = SupabaseRepository.__new__(SupabaseRepository)
        repo.client = FakeClient(APIError({
            "message": "permission denied for table business_days",
            "code": "42501",
        }))
        repo._business_id = "biz-1"
        repo._change_callback = None

        business_day = BusinessDay(
            id="BD-TEST", opened_at="2026-07-09T00:00:00", opened_by="worker@biz.com",
            status=BusinessDayStatus.OPEN, opening_note="",
        )

        with self.assertRaises(APIError):
            repo.open_business_day(business_day)


if __name__ == "__main__":
    unittest.main()
