import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import Product, Customer, Transaction, BusinessDay, Service, WaterConfiguration

try:
    from .repository import Repository, DuplicateBusinessDayError
except ImportError:  # allow running this file directly as a script
    from backend.repository import Repository, DuplicateBusinessDayError


class MemoryRepository(Repository):
    """Same-process, no-network backend. Good for local dev, unit tests, and
    offline mode. Every method mirrors what SupabaseRepository does against
    real tables, just against Python lists instead."""

    def __init__(self):
        super().__init__()
        self._products: List[Product] = []
        self._customers: List[Customer] = []
        self._transactions: List[Transaction] = []
        self._daily_expenses: List[Dict[str, Any]] = []
        self._capital_expenses: List[Dict[str, Any]] = []
        self._timeline: List[Dict[str, Any]] = []
        self._water_readings: List[Dict[str, Any]] = []
        self._business_days: List[BusinessDay] = []
        self._water_config: Optional[WaterConfiguration] = None
        self._services: List[Service] = []

    # ---- Products ----------------------------------------------------
    def list_products(self) -> List[Product]:
        if self._business_id:
            return [p for p in self._products if p.business_id == self._business_id]
        return list(self._products)

    def get_product(self, name: str) -> Optional[Product]:
        products = self.list_products()
        return next((p for p in products if p.name == name), None)

    def save_product(self, product: Product) -> None:
        pass  # already mutated in place; no-op for in-memory

    # ---- Product Management (V1 Product Setup) ----------------------
    def add_product(self, product: Product) -> None:
        product.business_id = self._business_id or product.business_id
        self._products.append(product)

    def update_product(self, product: Product) -> None:
        existing = next((p for p in self._products if p.id == product.id), None)
        if existing:
            existing.name = product.name
            existing.selling_price = product.selling_price
            existing.track_inventory = product.track_inventory
            existing.active = product.active
            existing.updated_at = product.updated_at

    def set_product_active(self, product_id: str, active: bool) -> None:
        product = next((p for p in self._products if p.id == product_id), None)
        if product:
            product.active = active
            from datetime import datetime
            product.updated_at = datetime.now().isoformat()

    # ---- Water Configuration -----------------------------------------
    def get_water_config(self) -> Optional[WaterConfiguration]:
        if self._business_id and self._water_config:
            if self._water_config.business_id == self._business_id:
                return self._water_config
            return None
        return self._water_config

    def save_water_config(self, config: WaterConfiguration) -> None:
        config.business_id = self._business_id or config.business_id
        self._water_config = config

    # ---- Services ------------------------------------------------------
    def list_services(self) -> List[Service]:
        if self._business_id:
            return [s for s in self._services if s.business_id == self._business_id]
        return list(self._services)

    def add_service(self, service: Service) -> None:
        service.business_id = self._business_id or service.business_id
        self._services.append(service)

    def update_service(self, service: Service) -> None:
        existing = next((s for s in self._services if s.id == service.id), None)
        if existing:
            existing.name = service.name
            existing.cost = service.cost
            existing.selling_price = service.selling_price
            existing.active = service.active
            existing.updated_at = service.updated_at

    def set_service_active(self, service_id: str, active: bool) -> None:
        service = next((s for s in self._services if s.id == service_id), None)
        if service:
            service.active = active
            from datetime import datetime
            service.updated_at = datetime.now().isoformat()

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
        # Mirror the real database's one_open_business_day_per_business
        # unique constraint so this backend behaves identically for tests
        # and local/offline dev.
        if any(b.status == "OPEN" for b in self._business_days):
            raise DuplicateBusinessDayError(
                "duplicate key value violates unique constraint "
                '"one_open_business_day_per_business"'
            )
        self._business_days.append(business_day)

    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None:
        day = next((b for b in self._business_days if b.id == business_day_id), None)
        if day:
            day.status = "CLOSED"
            day.closed_at = closed_at
            day.closed_by = closed_by
            day.closing_note = closing_note
