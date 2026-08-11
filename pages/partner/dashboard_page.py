import flet as ft
import theme
from widgets import glass_card, hero_card, section_title, kpi_card, stock_card, primary_button, show_snack
from services import Services, BusinessDayError


class PartnerDashboardPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate, user=None):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.user = user
        self.period = "daily"

    def _close_day(self, e):
        try:
            email = self.user.email if self.user and hasattr(self.user, 'email') else "owner"
            self.services.business_day.close_day(
                email, "Closed remotely by owner",
            )
        except BusinessDayError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        show_snack(self.page, "Business Day closed.")
        self.on_navigate("dashboard")

    def _hero(self) -> ft.Container:
        """One focal point: 'How is my business doing today?'"""
        return hero_card(
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.DASHBOARD_OUTLINED,
                                    color=ft.Colors.BLACK, size=22),
                    width=44, height=44, border_radius=theme.RADIUS_MD,
                    alignment=ft.Alignment.CENTER,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                        colors=[theme.ACCENT, ft.Colors.BLUE_400],
                    ),
                ),
                ft.Column([
                    ft.Text("Dashboard", size=theme.Type.TITLE,
                            weight=ft.FontWeight.W_800, color=theme.text_primary()),
                    ft.Text("How is my business doing today?",
                            size=theme.Type.CAPTION, color=theme.text_dim()),
                ], spacing=2, expand=True),
            ], spacing=theme.SPACING_SM, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_LG, accent=theme.ACCENT,
        )

    def _business_day_card(self):
        day = self.services.business_day.current()
        if day:
            opened_time = day.opened_at.split("T")[-1][:5] if "T" in day.opened_at else day.opened_at
            return hero_card(
                ft.Row([
                    ft.Row([
                        ft.Container(width=10, height=10, border_radius=5, bgcolor=theme.SUCCESS),
                        ft.Column([
                            ft.Text("Business Day OPEN", size=theme.Type.BODY,
                                    weight=ft.FontWeight.W_700, color=theme.text_primary()),
                            ft.Text(f"Opened {opened_time} by {day.opened_by}",
                                    size=theme.Type.CAPTION, color=theme.text_dim()),
                        ], spacing=2),
                    ], spacing=theme.SPACING_SM),
                    ft.TextButton("Close Day", style=ft.ButtonStyle(color=theme.DANGER),
                                  on_click=self._close_day),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.SPACING_MD, accent=theme.SUCCESS,
            )
        return hero_card(
            ft.Row([
                ft.Container(width=10, height=10, border_radius=5, bgcolor=theme.TEXT_DIM),
                ft.Text("Business Day CLOSED — waiting for a worker to open it",
                        size=theme.Type.CAPTION, color=theme.text_dim()),
            ], spacing=theme.SPACING_SM),
            padding=theme.SPACING_MD,
        )

    def _revenue_hero(self, current, previous) -> ft.Container:
        """The ONE hero metric — Revenue — as the page's focal point."""
        trend = self.services.analytics.trend(current["revenue"], previous["revenue"])
        trend_color = theme.SUCCESS if trend and trend.startswith("+") else theme.DANGER
        return hero_card(
            ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED,
                                        color=theme.SUCCESS, size=20),
                        width=40, height=40, border_radius=theme.RADIUS_MD,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=ft.Colors.with_opacity(0.14, theme.SUCCESS),
                    ),
                    ft.Text("Today's Revenue", size=theme.Type.CAPTION,
                            weight=ft.FontWeight.W_600, color=theme.text_secondary(), expand=True),
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_UPWARD if trend and trend.startswith("+")
                                else ft.Icons.ARROW_DOWNWARD, size=14, color=trend_color),
                        ft.Text(trend or "—", size=theme.Type.CAPTION,
                                weight=ft.FontWeight.W_700, color=trend_color),
                    ], spacing=2) if trend else ft.Container(),
                ], spacing=theme.SPACING_SM, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(f"KES {current['revenue']:,.0f}", size=theme.Type.DISPLAY,
                        weight=ft.FontWeight.W_800, color=theme.text_primary()),
                ft.Text("vs prior period", size=theme.Type.MICRO, color=theme.text_dim()),
            ], spacing=theme.SPACING_XS),
            padding=theme.SPACING_LG, accent=theme.SUCCESS,
        )

    def build(self) -> list:
        data = self.services.analytics.current_vs_previous(self.period)
        current, previous = data["current"], data["previous"]
        outstanding = self.services.customers.total_outstanding()

        # Secondary KPIs — smaller, below the Revenue hero
        kpi_grid = ft.GridView(
            controls=[
                kpi_card("Profit", f"KES {current['profit']:,.0f}", ft.Icons.TRENDING_UP, theme.ACCENT,
                         trend=self.services.analytics.trend(current["profit"], previous["profit"])),
                kpi_card("Losses", f"KES {current['losses']:,.0f}", ft.Icons.TRENDING_DOWN, theme.DANGER,
                         trend=self.services.analytics.trend(current["losses"], previous["losses"], invert=True)),
                kpi_card("Water Sold", f"{current['water_sold']:,.0f}L", ft.Icons.WATER_DROP, theme.GOLD,
                         trend=self.services.analytics.trend(current["water_sold"], previous["water_sold"])),
            ],
            runs_count=3, max_extent=120, spacing=8, run_spacing=8, child_aspect_ratio=0.9, height=150,
        )

        outstanding_card = glass_card(
            ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=theme.WARNING),
                ft.Text("Outstanding Customer Balances", size=theme.Type.CAPTION,
                        color=theme.text_secondary(), expand=True),
                ft.Text(f"KES {outstanding:,.0f}", size=theme.Type.SECTION,
                        weight=ft.FontWeight.W_700, color=theme.WARNING),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_MD, accent=theme.WARNING,
        )

        water_card = glass_card(
            ft.Column([
                ft.Row([ft.Icon(ft.Icons.WATER_DROP, color=theme.ACCENT),
                        ft.Text("Water Usage", size=theme.Type.BODY,
                                weight=ft.FontWeight.W_600, color=theme.text_primary())],
                       spacing=theme.SPACING_XS),
                ft.Row([
                    ft.Text(f"Total: {current['water_total']}L", size=theme.Type.CAPTION,
                            color=theme.text_secondary()),
                    ft.Text(f"Cleaning: {current['water_cleaning']}L", size=theme.Type.CAPTION,
                            color=theme.WARNING),
                    ft.Text(f"Sold: {current['water_sold']}L", size=theme.Type.CAPTION,
                            color=theme.SUCCESS),
                ], spacing=theme.SPACING_LG),
                ft.ProgressBar(
                    value=current["water_sold"] / max(current["water_total"], 1),
                    color=theme.ACCENT, bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                    bar_height=8, border_radius=4,
                ),
                ft.Text(f"Efficiency: {current['water_sold'] / max(current['water_total'], 1) * 100:.0f}% sold",
                        size=theme.Type.CAPTION, color=theme.text_dim()),
            ], spacing=theme.SPACING_XS),
            padding=theme.SPACING_MD, accent=theme.ACCENT,
        )

        products = self.services.inventory.all_products()
        stock_grid = ft.GridView(
            controls=[stock_card(item) for item in products],
            runs_count=2, max_extent=150, spacing=8, run_spacing=8, child_aspect_ratio=1.0, height=220,
        )

        return [
            self._hero(),
            self._business_day_card(),
            self._revenue_hero(current, previous),
            kpi_grid,
            outstanding_card,
            water_card,
            section_title("Stock Levels", ft.Icons.INVENTORY_2_OUTLINED),
            stock_grid,
        ]