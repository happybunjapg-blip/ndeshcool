import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.sales_service import SalesService


class DummyRepo:
    def __init__(self):
        self.transactions = []
        self.water_readings = []

    def add_transaction(self, transaction):
        self.transactions.append(transaction)

    def upsert_today_water_reading(self, reading):
        self.water_readings.append(reading)

    def save_customer(self, customer):
        pass

    def add_daily_expense(self, record):
        pass

    def add_capital_expense(self, record):
        pass


class DummyState:
    def __init__(self):
        self.repo = DummyRepo()
        self.transactions = []
        self.water_readings = []
        self.daily_expenses = []
        self.capital_expenses = []
        self._next_id = 1

    def is_business_day_open(self):
        return True

    def next_transaction_id(self):
        value = self._next_id
        self._next_id += 1
        return value

    def get_customer(self, customer_id):
        return None

    def log_timeline(self, *args, **kwargs):
        return None

    def get_product(self, name):
        return None


class SalesServiceTests(unittest.TestCase):
    def test_record_water_refill_uses_custom_water_pricing(self):
        state = DummyState()
        service = SalesService(state, inventory=SimpleNamespace())

        tx = service.record_water_refill(6.5, "Cash")

        self.assertAlmostEqual(tx.amount, 65.0)
        self.assertAlmostEqual(tx.profit, 58.5)
        self.assertAlmostEqual(state.water_readings[0]["sold_water"], 6.5)


if __name__ == "__main__":
    unittest.main()
