from backend.state import AppState
import config
from .auth_service import AuthService
from .inventory_service import InventoryService
from .sales_service import SalesService, SalesError
from .customer_service import CustomerService
from .analytics_service import AnalyticsService
from .business_day_service import BusinessDayService, BusinessDayError


class Services:
    """A single object carrying every service, built once per app session
    and threaded through pages instead of pages reaching for globals.

    The persistence backend (in-memory vs Supabase) is chosen entirely by
    `config.py` / the BACKEND env var -- nothing here needs to know which
    one is active.
    """

    def __init__(self):
        repository = config.build_repository()
        self.state = AppState(repository)
        self.auth = AuthService()
        self.inventory = InventoryService(self.state)
        self.sales = SalesService(self.state, self.inventory)
        self.customers = CustomerService(self.state)
        self.analytics = AnalyticsService(self.state)
        self.business_day = BusinessDayService(self.state)


__all__ = ["Services", "AuthService", "InventoryService", "SalesService", "SalesError",
           "CustomerService", "AnalyticsService", "BusinessDayService", "BusinessDayError"]
