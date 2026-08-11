"""Repository is the contract every persistence backend must satisfy.

Services and AppState only ever talk to this interface. Today two classes
implement it: MemoryRepository (fast, no network, used for dev/tests) and
SupabaseRepository (the real production backend). Adding a third backend
later (e.g. a custom FastAPI service) means writing one more class here --
nothing above this layer changes.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models import Product, Customer, Transaction, BusinessDay, Service, WaterConfiguration


class DuplicateBusinessDayError(Exception):
    """Raised by a Repository's open_business_day() when the database
    rejects the insert because a Business Day is already OPEN for this
    business (the `one_open_business_day_per_business` unique constraint).

    This is a narrow, expected race: e.g. two devices both saw "no open
    day" and both tried to open one at nearly the same instant. It is
    distinct from other/unexpected errors so callers can safely recover by
    re-fetching the day that actually won, instead of treating it as a
    generic failure.
    """


class Repository(ABC):
    """Repository interface for data persistence.
    
    All backends must implement these methods.
    The `business_id` property is set by the app when a user logs in,
    so all queries are scoped to the authenticated user's business.
    """
    
    def __init__(self):
        self._business_id: Optional[str] = None

    def set_business_id(self, business_id: str) -> None:
        """Set the business_id for scoping all queries."""
        self._business_id = business_id

    def get_business_id(self) -> Optional[str]:
        """Get the current business_id."""
        return self._business_id

    # ---- Products / inventory -------------------------------------
    @abstractmethod
    def list_products(self) -> List[Product]: ...

    @abstractmethod
    def get_product(self, name: str) -> Optional[Product]: ...

    @abstractmethod
    def save_product(self, product: Product) -> None:
        """Persist a product's current qty/batches/prices after mutation."""

    # ---- Product Management (V1 Product Setup) ----------------------
    @abstractmethod
    def add_product(self, product: Product) -> None:
        """Create a new product owned by the current business."""

    @abstractmethod
    def update_product(self, product: Product) -> None:
        """Update a product's name/selling_price/track_inventory/active."""

    @abstractmethod
    def set_product_active(self, product_id: str, active: bool) -> None:
        """Archive (active=False) or activate (active=True) a product."""

    def list_active_products(self) -> List[Product]:
        """Products visible to the Sales screen: active only, scoped to
        the current business. Default implementation filters list_products();
        backends may override for a more efficient query."""
        return [p for p in self.list_products() if p.active]

    # ---- Water Configuration -----------------------------------------
    @abstractmethod
    def get_water_config(self) -> Optional[WaterConfiguration]:
        """Return the current business's water configuration, or None if
        it hasn't been created yet."""

    @abstractmethod
    def save_water_config(self, config: WaterConfiguration) -> None:
        """Persist the water configuration for the current business."""

    # ---- Services ------------------------------------------------------
    @abstractmethod
    def list_services(self) -> List[Service]:
        """List all services for the current business."""

    @abstractmethod
    def add_service(self, service: Service) -> None:
        """Create a new service owned by the current business."""

    @abstractmethod
    def update_service(self, service: Service) -> None:
        """Update a service's name/cost/selling_price/active."""

    @abstractmethod
    def set_service_active(self, service_id: str, active: bool) -> None:
        """Archive (active=False) or activate (active=True) a service."""

    def list_active_services(self) -> List[Service]:
        """Services visible to the Sales screen: active only, scoped to
        the current business. Default implementation filters list_services();
        backends may override for a more efficient query."""
        return [s for s in self.list_services() if s.active]

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
