import unittest

from postgrest.exceptions import APIError

from backend.supabase_repository import SupabaseRepository
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


if __name__ == "__main__":
    unittest.main()
