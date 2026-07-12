import flet as ft
import theme
from models import Role, User
from services import Services

from pages.splash_page import build_splash
from pages.login_page import build_login
from pages.worker.business_day_page import build_business_day_gate
from pages.worker.home_page import WorkerHomePage
from pages.worker.sales_page import WorkerSalesPage
from pages.worker.customers_page import WorkerCustomersPage
from pages.worker.expenses_page import WorkerExpensesPage
from pages.partner.dashboard_page import PartnerDashboardPage
from pages.partner.settings_page import PartnerSettingsPage
from pages.partner.reports_page import PartnerReportsPage
from pages.partner.performance_page import PartnerPerformancePage
from pages.partner.funds_page import PartnerFundsPage
from widgets import page_content


ROLE_NAV = {
    Role.WORKER: [
        ("home", "Home", ft.Icons.HOME_OUTLINED, ft.Icons.HOME),
        ("sales", "Sales", ft.Icons.POINT_OF_SALE_OUTLINED, ft.Icons.POINT_OF_SALE),
        ("customers", "Customers", ft.Icons.PEOPLE_OUTLINE, ft.Icons.PEOPLE),
        ("expenses", "Expenses", ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG),
    ],
    Role.PARTNER: [
        ("dashboard", "Dashboard", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD),
        ("settings", "Settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
        ("reports", "Reports", ft.Icons.BAR_CHART_OUTLINED, ft.Icons.BAR_CHART),
        ("performance", "Performance", ft.Icons.TIMELINE_OUTLINED, ft.Icons.TIMELINE),
        ("funds", "Funds", ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, ft.Icons.ACCOUNT_BALANCE_WALLET),
    ],
}


class WaterStationApp:
    """Orchestrates the Splash -> Login -> Dashboard flow.

    The role is NEVER chosen manually: it's attached to the User object
    returned by AuthService.authenticate() and drives which nav/pages appear.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.services = Services()
        self.dark_mode = True
        self.user: User | None = None
        self.current_page_name: str | None = None
        self.page_controllers: dict = {}

        theme.DARK_MODE = True
        self._configure_page()
        self.services.state.on_change(self._handle_remote_change)
        self._show_splash()

    # =====================================================================
    # PAGE / THEME SETUP
    # =====================================================================
    def _configure_page(self):
        theme.DARK_MODE = self.dark_mode
        self.page.title = "AquaFlow"
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark_mode else ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN)
        # Page-level padding is 0; the SafeArea wrapper (see _show_shell)
        # handles system-inset protection on mobile.
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = None
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self._apply_background()

    def _apply_background(self):
        self.page.bgcolor = theme.BG_BOTTOM if self.dark_mode else theme.LIGHT_BG_BOTTOM
        self.page.decoration = ft.BoxDecoration(gradient=theme.background_gradient(self.dark_mode))

    # =====================================================================
    # SAFE AREA HELPERS
    # =====================================================================
    def _safe_top(self) -> int:
        """Return the top safe-area inset (status bar / notch height)."""
        # Minimum of 20px ensures content never touches the top edge even on
        # devices that report 0 safe-area inset (e.g. desktop, some emulators).
        return max(20, getattr(self.page, "window_top_safe_area_height", 0) or 0)

    def _safe_bottom(self) -> int:
        """Return the bottom safe-area inset (home indicator)."""
        return getattr(self.page, "window_bottom_safe_area_height", 0) or 0

    # =====================================================================
    # STAGE 1: SPLASH
    # =====================================================================
    def _show_splash(self):
        self.page.navigation_bar = None
        self.page.controls.clear()
        self.page.add(build_splash(self.page, on_finish=self._show_login))
        self.page.update()

    # =====================================================================
    # STAGE 2: LOGIN
    # =====================================================================
    def _show_login(self):
        self.page.navigation_bar = None
        self.page.controls.clear()
        self.page.add(build_login(self.page, self.services, on_login_success=self._on_login_success))
        self.page.update()

    def _on_login_success(self, user: User):
        self.user = user
        self.page_controllers = {}  # fresh controllers per session
        tabs = ROLE_NAV[user.role]
        self.current_page_name = tabs[0][0]
        if user.role == Role.WORKER and not self.services.business_day.is_open():
            self._show_business_day_gate()
        else:
            self._show_shell()

    def _show_business_day_gate(self):
        """Workers can't reach Home/Sales/Expenses/Customers until a
        Business Day is open -- there's no nav bar at all at this stage,
        matching how Login/Splash work: one focused screen, one action."""
        self.page.navigation_bar = None
        self.page.controls.clear()
        self.page.add(build_business_day_gate(self.page, self.services, self.user, on_opened=self._show_shell))
        self.page.update()

    def _handle_remote_change(self):
        """Called whenever the repository detects a remote write (another
        device's sale, expense, payment, business day open/close...). Only
        meaningful once the shell is showing -- splash/login/gate screens
        don't need a data refresh."""
        if self.user and getattr(self, "body_container", None):
            if self.user.role == Role.WORKER and not self.services.business_day.is_open():
                self._show_business_day_gate()
                return
            self._navigate_to(self.current_page_name)

    def _logout(self):
        self.user = None
        self._show_login()

    # =====================================================================
    # STAGE 3: MAIN SHELL (header + body + bottom nav)
    # =====================================================================
    def _show_shell(self):
        safe_top = self._safe_top()
        safe_bottom = self._safe_bottom()

        self.header_container = self._build_header(safe_top)
        self.body_container = ft.Container(
            expand=True,
            padding=ft.Padding(
                theme.MOBILE_PADDING_H,            # left — 16px, cards no longer touch edges
                theme.MOBILE_PADDING_V,             # top — 8px breathing room below header
                theme.MOBILE_PADDING_H,             # right — 16px
                theme.MOBILE_PADDING_V + safe_bottom,  # bottom — 8px + nav safe area
            ),
            content=self._build_page(self.current_page_name),
        )
        self.root_column = ft.Column(
            controls=[self.header_container, self.body_container],
            expand=True,
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        )
        # Wrap the entire shell in SafeArea so Android notch / status bar
        # and iOS home indicator are respected automatically.
        self.page.controls.clear()
        self.page.add(ft.SafeArea(self.root_column))
        self.page.navigation_bar = self._build_bottom_nav(safe_bottom)
        self.page.update()

    def _build_header(self, safe_top: int) -> ft.Container:
        """Two-tier header:
        - Top row: safe-area spacer + logo + app title + account icon
        - Bottom row: greeting + role badge (left), theme toggle (right)
        """
        is_dark = self.dark_mode

        # ── Logo badge ──────────────────────────────────────────────
        logo_badge = ft.Container(
            content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=22),
            width=42, height=42, border_radius=12, alignment=ft.Alignment.CENTER,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                colors=[theme.ACCENT, ft.Colors.BLUE_400],
            ),
            shadow=ft.BoxShadow(blur_radius=14, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 3)),
        )

        # ── App title ───────────────────────────────────────────────
        app_title = ft.Text(
            "AquaFlow", size=20, weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE if is_dark else theme.LIGHT_TEXT_PRIMARY,
        )

        # ── Account / profile icon ──────────────────────────────────
        account_icon = ft.IconButton(
            icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
            icon_color=theme.TEXT_MID if is_dark else theme.LIGHT_TEXT_SECONDARY,
            tooltip="Account",
            style=ft.ButtonStyle(
                bgcolor=theme.SURFACE if is_dark else ft.Colors.with_opacity(0.06, theme.LIGHT_TEXT_PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

        # ── Top bar: logo + title + account icon ────────────────────
        top_bar = ft.Row(
            controls=[
                logo_badge,
                ft.Container(content=app_title, expand=True, alignment=ft.Alignment(-0.15, 0)),
                account_icon,
            ],
            spacing=theme.SPACING_XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ── Greeting ────────────────────────────────────────────────
        greeting = ft.Text(
            f"Hi, {self.user.name.split(' ')[0]}",
            size=13,
            color=theme.TEXT_MID if is_dark else theme.LIGHT_TEXT_SECONDARY,
            weight=ft.FontWeight.W_500,
        )

        # ── Role badge ──────────────────────────────────────────────
        role_badge = ft.Container(
            content=ft.Text(
                self.user.role.value.title(), size=11,
                weight=ft.FontWeight.W_700, color=ft.Colors.BLACK,
            ),
            bgcolor=theme.ACCENT,
            padding=ft.Padding(theme.SPACING_SM, theme.SPACING_XXS, theme.SPACING_SM, theme.SPACING_XXS),
            border_radius=12,
        )

        # ── Theme toggle ────────────────────────────────────────────
        self.theme_icon_button = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE_OUTLINED if is_dark else ft.Icons.DARK_MODE_OUTLINED,
            icon_color=theme.GOLD if is_dark else theme.LIGHT_TEXT_SECONDARY,
            tooltip="Toggle theme",
            on_click=lambda e: self._toggle_theme(),
            style=ft.ButtonStyle(
                bgcolor=theme.SURFACE if is_dark else ft.Colors.with_opacity(0.06, theme.LIGHT_TEXT_PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

        # ── Logout button ───────────────────────────────────────────
        logout_button = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            icon_color=theme.TEXT_DIM if is_dark else theme.LIGHT_TEXT_DIM,
            tooltip="Log out",
            on_click=lambda e: self._logout(),
            style=ft.ButtonStyle(
                bgcolor=theme.SURFACE if is_dark else ft.Colors.with_opacity(0.06, theme.LIGHT_TEXT_PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

        # ── Bottom row: greeting + role | theme + logout ────────────
        bottom_bar = ft.Row(
            controls=[
                ft.Row([greeting, role_badge], spacing=theme.SPACING_XS),
                ft.Row([self.theme_icon_button, logout_button], spacing=theme.SPACING_XS),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ── Header background ───────────────────────────────────────
        if is_dark:
            header_bgcolor = ft.Colors.with_opacity(0.55, theme.BG_TOP)
        else:
            header_bgcolor = theme.LIGHT_HEADER_BG

        # ── Assemble header ─────────────────────────────────────────
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=safe_top),          # safe-area spacer
                    top_bar,
                    ft.Container(height=theme.SPACING_XS),  # gap between tiers
                    bottom_bar,
                ],
                spacing=0,
            ),
            padding=ft.Padding(
                theme.HEADER_PADDING_H,  # left — 16px
                0,                        # top (handled by safe-area spacer)
                theme.HEADER_PADDING_H,  # right — 16px
                theme.SPACING_SM,        # bottom
            ),
            bgcolor=header_bgcolor,
            border=ft.Border(
                bottom=ft.BorderSide(
                    1,
                    theme.SURFACE_BORDER if is_dark else theme.LIGHT_SURFACE_BORDER,
                ),
            ),
            shadow=ft.BoxShadow(
                blur_radius=18,
                color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK)
                    if is_dark else theme.LIGHT_CARD_SHADOW,
                offset=ft.Offset(0, 4),
            ),
        )

    def _build_bottom_nav(self, safe_bottom: int) -> ft.NavigationBar:
        is_dark = self.dark_mode
        tabs = ROLE_NAV[self.user.role]
        active_idx = [t[0] for t in tabs].index(self.current_page_name)
        return ft.NavigationBar(
            selected_index=active_idx,
            destinations=[
                ft.NavigationBarDestination(icon=icon, selected_icon=sel_icon, label=label)
                for (_, label, icon, sel_icon) in tabs
            ],
            on_change=self._on_nav_change,
            bgcolor=ft.Colors.with_opacity(0.9, theme.BG_TOP) if is_dark
                    else ft.Colors.with_opacity(0.98, theme.LIGHT_HEADER_BG),
            indicator_color=theme.ACCENT_SOFT,
            elevation=12,
        )

    def _on_nav_change(self, e: ft.Event):
        tabs = ROLE_NAV[self.user.role]
        page_name = tabs[e.control.selected_index][0]
        self._navigate_to(page_name)

    def _navigate_to(self, page_name: str):
        if self.user and self.user.role == Role.WORKER and not self.services.business_day.is_open():
            self._show_business_day_gate()
            return
        self.current_page_name = page_name
        self._render_body(page_name)

    def _render_body(self, page_name: str):
        self.body_container.content = self._build_page(page_name)
        if self.page.navigation_bar:
            tabs = ROLE_NAV[self.user.role]
            self.page.navigation_bar.selected_index = [t[0] for t in tabs].index(page_name)
        self.page.update()

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        theme.DARK_MODE = self.dark_mode
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark_mode else ft.ThemeMode.LIGHT
        self._apply_background()
        self._show_shell()

    # =====================================================================
    # PAGE CONTROLLER FACTORY (built once per session, cached)
    # =====================================================================
    def _get_controller(self, page_name: str):
        if page_name in self.page_controllers:
            return self.page_controllers[page_name]
        controller_classes = {
            "home": WorkerHomePage,
            "sales": WorkerSalesPage,
            "customers": WorkerCustomersPage,
            "expenses": WorkerExpensesPage,
            "dashboard": PartnerDashboardPage,
            "settings": PartnerSettingsPage,
            "reports": PartnerReportsPage,
            "performance": PartnerPerformancePage,
            "funds": PartnerFundsPage,
        }
        cls = controller_classes[page_name]
        if page_name in ("home", "dashboard"):
            controller = cls(self.page, self.services, self._navigate_to, user=self.user)
        else:
            controller = cls(self.page, self.services, self._navigate_to)
        self.page_controllers[page_name] = controller
        return controller

    def _build_page(self, page_name: str) -> ft.Column:
        controller = self._get_controller(page_name)
        # Use the reusable page_content wrapper for consistent section spacing
        return page_content(controls=controller.build())
