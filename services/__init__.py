from backend.state import AppState
import config
from .session_service import SessionService
from .auth_service import AuthService
from .inventory_service import InventoryService
from .sales_service import SalesService, SalesError
from .customer_service import CustomerService
from .analytics_service import AnalyticsService
from .business_day_service import BusinessDayService, BusinessDayError
from .service_service import ServiceService
from .water_config_service import WaterConfigService


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
        self.session = SessionService()
        self.auth = AuthService(session_service=self.session)

    def sync_repository_session(self):
            session = self.auth.get_current_session()

            if session and hasattr(self.state.repo, "set_session"):
                self.state.repo.set_session(
                    session.access_token,
                    session.refresh_token,
            )


    def sync_repository_session(self):
            """Synchronize the authenticated Supabase session with the repository."""
            if not hasattr(self.state.repo, "set_session"):
                return

            session = self.auth._client.auth.get_session()

            if session and session.session:
                self.state.repo.set_session(
                    session.session.access_token,
                    session.session.refresh_token,
                )


    def __init__(self):
        repository = config.build_repository()
        self.state = AppState(repository)
        self.session = SessionService()
        self.auth = AuthService(session_service=self.session)
        self.inventory = InventoryService(self.state)
        self.sales = SalesService(self.state, self.inventory)
        self.customers = CustomerService(self.state)
        self.analytics = AnalyticsService(self.state)
        self.business_day = BusinessDayService(self.state)
        self.services_catalog = ServiceService(self.state)
        self.water_config = WaterConfigService(self.state)


__all__ = ["Services", "AuthService", "InventoryService", "SalesService", "SalesError",
           "CustomerService", "AnalyticsService", "BusinessDayService", "BusinessDayError",
           "SessionService", "ServiceService", "WaterConfigService"]
