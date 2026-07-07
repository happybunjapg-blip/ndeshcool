from datetime import datetime
from typing import List, Optional, Dict, Any
from models import Product, Customer, Transaction, BusinessDay
from .repository import Repository
from . import seed_data


class MemoryRepository(Repository):
    """Same-process, no-network backend. Good for local dev, unit tests, and
    offline mode. Every method mirrors what SupabaseRepository does against
    real tables, just against Python lists instead."""

    def __init__(self):
        self._products: List[Product] = seed_data.seed_products()
        self._customers: List[Customer] = seed_data.seed_customers()
        self._transactions: List[Transaction] = []
        self._daily_expenses: List[Dict[str, Any]] = []
        self._capital_expenses: List[Dict[str, Any]] = []
        self._timeline: List[Dict[str, Any]] = seed_data.seed_timeline()
        self._water_readings: List[Dict[str, Any]] = seed_data.seed_water_readings()
        self._business_days: List[BusinessDay] = []

    # ---- Products ----------------------------------------------------
    def list_products(self) -> List[Product]:
        return list(self._products)

    def get_product(self, name: str) -> Optional[Product]:
        return next((p for p in self._products if p.name == name), None)

    def save_product(self, product: Product) -> None:
        pass  # already mutated in place; no-op for in-memory

    # ---- Customers -----------------------------------------------------
    def list_customers(self) -> List[Customer]:
        return list(self._customers)

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return next((c for c in self._customers if c.id == customer_id), None)

    def save_customer(self, customer: Customer) -> None:
        pass  # already mutated in place

    def add_customer(self, customer: Customer) -> None:
        self._customers.append(customer)

    # ---- Transactions ----------------------------------------------------
    def list_transactions(self) -> List[Transaction]:
        return list(self._transactions)

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    def next_transaction_id(self) -> str:
        return f"T{len(self._transactions) + 1:05d}"

    # ---- Expenses -----------------------------------------------------
    def list_daily_expenses(self) -> List[Dict[str, Any]]:
        return list(self._daily_expenses)

    def add_daily_expense(self, record: Dict[str, Any]) -> None:
        self._daily_expenses.append(record)

    def list_capital_expenses(self) -> List[Dict[str, Any]]:
        return list(self._capital_expenses)

    def add_capital_expense(self, record: Dict[str, Any]) -> None:
        self._capital_expenses.append(record)

    # ---- Timeline -----------------------------------------------------
    def list_timeline(self) -> List[Dict[str, Any]]:
        return list(self._timeline)

    def add_timeline_event(self, record: Dict[str, Any]) -> None:
        self._timeline.append(record)

    # ---- Water readings -------------------------------------------------
    def list_water_readings(self) -> List[Dict[str, Any]]:
        return list(self._water_readings)

    def add_water_reading(self, record: Dict[str, Any]) -> None:
        self._water_readings.append(record)

    def upsert_today_water_reading(self, record: Dict[str, Any]) -> None:
        today = record["date"]
        existing = next((r for r in self._water_readings if r["date"] == today), None)
        if existing:
            existing.update(record)
        else:
            self._water_readings.append(record)

    # ---- Business Day ----------------------------------------------------
    def get_open_business_day(self) -> Optional[BusinessDay]:
        return next((b for b in self._business_days if b.status == "OPEN"), None)

    def list_business_days(self) -> List[BusinessDay]:
        return list(self._business_days)

    def open_business_day(self, business_day: BusinessDay) -> None:
        self._business_days.append(business_day)

    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None:
        day = next((b for b in self._business_days if b.id == business_day_id), None)
        if day:
            day.status = "CLOSED"
            day.closed_at = closed_at
            day.closed_by = closed_by
            day.closing_note = closing_note
