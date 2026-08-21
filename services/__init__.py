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
        if hasattr(self.state.repo, "set_session_provider"):
            self.state.repo.set_session_provider(self._get_auth_tokens_for_repository)
        self.inventory = InventoryService(self.state)
        self.sales = SalesService(self.state, self.inventory)
        self.customers = CustomerService(self.state)
        self.analytics = AnalyticsService(self.state)
        self.business_day = BusinessDayService(self.state)
        self.services_catalog = ServiceService(self.state)
        self.water_config = WaterConfigService(self.state)

    def _get_auth_tokens_for_repository(self):
        """Best-effort source of current auth tokens for repository sync."""
        if self.auth._client:
            try:
                result = self.auth._client.auth.get_session()
                session = getattr(result, "session", None)
                if session and session.access_token:
                    return session.access_token, session.refresh_token
            except Exception:
                pass

        access_token = self.session.get_access_token()
        refresh_token = self.session.get_refresh_token()
        return access_token, refresh_token

    def sync_repository_session(self):
        """Propagate the authenticated Supabase session (access + refresh
        tokens) from AuthService's client onto the repository's own
        Supabase client.

        AuthService and SupabaseRepository each hold their own, independent
        Supabase `Client` instance. Authenticating via AuthService (e.g.
        restoring a saved session on splash, or signing in) only updates
        AuthService's client -- the repository's client remains anonymous
        until this is called, which causes writes gated by RLS/table grants
        (e.g. UPDATE business_days) to fail with 42501 permission denied
        even though the user is "logged in".

        Must be called after any successful authentication/session restore
        and before any authenticated repository operation.
        """
        if not hasattr(self.state.repo, "set_session"):
            return

        access_token, refresh_token = self._get_auth_tokens_for_repository()
        if access_token:
            self.state.repo.set_session(access_token, refresh_token)


__all__ = ["Services", "AuthService", "InventoryService", "SalesService", "SalesError",
           "CustomerService", "AnalyticsService", "BusinessDayService", "BusinessDayError",
           "SessionService", "ServiceService", "WaterConfigService"]
