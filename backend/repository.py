"""Repository is the contract every persistence backend must satisfy.

Services and AppState only ever talk to this interface. Today two classes
implement it: MemoryRepository (fast, no network, used for dev/tests) and
SupabaseRepository (the real production backend). Adding a third backend
later (e.g. a custom FastAPI service) means writing one more class here --
nothing above this layer changes.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models import Product, Customer, Transaction, BusinessDay


class Repository(ABC):
    # ---- Products / inventory -------------------------------------
    @abstractmethod
    def list_products(self) -> List[Product]: ...

    @abstractmethod
    def get_product(self, name: str) -> Optional[Product]: ...

    @abstractmethod
    def save_product(self, product: Product) -> None:
        """Persist a product's current qty/batches/prices after mutation."""

    # ---- Customers (credit customers only) -------------------------
    @abstractmethod
    def list_customers(self) -> List[Customer]: ...

    @abstractmethod
    def get_customer(self, customer_id: str) -> Optional[Customer]: ...

    @abstractmethod
    def save_customer(self, customer: Customer) -> None: ...

    @abstractmethod
    def add_customer(self, customer: Customer) -> None: ...

    # ---- Transactions (sales, refills, deliveries, payments) --------
    @abstractmethod
    def list_transactions(self) -> List[Transaction]: ...

    @abstractmethod
    def add_transaction(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def next_transaction_id(self) -> str: ...

    # ---- Expenses -----------------------------------------------------
    @abstractmethod
    def list_daily_expenses(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_daily_expense(self, record: Dict[str, Any]) -> None: ...

    @abstractmethod
    def list_capital_expenses(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_capital_expense(self, record: Dict[str, Any]) -> None: ...

    # ---- Timeline / audit log ------------------------------------------
    @abstractmethod
    def list_timeline(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_timeline_event(self, record: Dict[str, Any]) -> None: ...

    # ---- Water meter readings -------------------------------------------
    @abstractmethod
    def list_water_readings(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_water_reading(self, record: Dict[str, Any]) -> None: ...

    @abstractmethod
    def upsert_today_water_reading(self, record: Dict[str, Any]) -> None: ...

    # ---- Business Day ----------------------------------------------------
    @abstractmethod
    def get_open_business_day(self) -> Optional[BusinessDay]: ...

    @abstractmethod
    def list_business_days(self) -> List[BusinessDay]: ...

    @abstractmethod
    def open_business_day(self, business_day: BusinessDay) -> None: ...

    @abstractmethod
    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None: ...

    # ---- Real-time -----------------------------------------------------
    def subscribe(self, on_change) -> None:
        """Optional: backends that support push updates (e.g. Supabase
        realtime) call `on_change()` whenever remote data changes so the UI
        can refresh. MemoryRepository is a no-op since there's nothing to
        subscribe to (there's only one process)."""
        return None
