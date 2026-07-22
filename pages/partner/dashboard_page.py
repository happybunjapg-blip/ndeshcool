import flet as ft
import theme
from widgets import glass_card, section_title, kpi_card, stock_card, primary_button, show_snack
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

    def _business_day_card(self):
        day = self.services.business_day.current()
        if day:
            opened_time = day.opened_at.split("T")[-1][:5] if "T" in day.opened_at else day.opened_at
            return glass_card(
                ft.Row([
                    ft.Row([
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=theme.SUCCESS),
                        ft.Column([
                            ft.Text("Business Day OPEN", size=13, weight=ft.FontWeight.W_700, color=theme.text_primary()),
                            ft.Text(f"Opened {opened_time} by {day.opened_by}", size=11, color=theme.TEXT_DIM),
                        ], spacing=2),
                    ], spacing=8),
                    ft.TextButton("Close Day", style=ft.ButtonStyle(color=theme.DANGER), on_click=self._close_day),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12, accent=theme.SUCCESS,
            )
        return glass_card(
            ft.Row([
                ft.Container(width=8, height=8, border_radius=4, bgcolor=theme.TEXT_DIM),
                ft.Text("Business Day CLOSED — waiting for a worker to open it", size=12, color=theme.TEXT_DIM),
            ], spacing=8),
            padding=12,
        )

    def build(self) -> list:
        data = self.services.analytics.current_vs_previous(self.period)
        current, previous = data["current"], data["previous"]
        outstanding = self.services.customers.total_outstanding()

        kpi_grid = ft.GridView(
            controls=[
                kpi_card("Revenue", f"KES {current['revenue']:,.0f}", ft.Icons.MONETIZATION_ON_OUTLINED,
                         theme.SUCCESS, trend=self.services.analytics.trend(current["revenue"], previous["revenue"])),
                kpi_card("Profit", f"KES {current['profit']:,.0f}", ft.Icons.TRENDING_UP, theme.ACCENT,
                         trend=self.services.analytics.trend(current["profit"], previous["profit"])),
                kpi_card("Losses", f"KES {current['losses']:,.0f}", ft.Icons.TRENDING_DOWN, theme.DANGER,
                         trend=self.services.analytics.trend(current["losses"], previous["losses"], invert=True)),
                kpi_card("Water Sold", f"{current['water_sold']:,.0f}L", ft.Icons.WATER_DROP, theme.GOLD,
                         trend=self.services.analytics.trend(current["water_sold"], previous["water_sold"])),
            ],
            runs_count=2, max_extent=160, spacing=8, run_spacing=8, child_aspect_ratio=1.05, height=220,
        )

        outstanding_card = glass_card(
            ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=theme.WARNING),
                ft.Text("Outstanding Customer Balances", size=13, color=theme.TEXT_MID, expand=True),
                ft.Text(f"KES {outstanding:,.0f}", size=15, weight=ft.FontWeight.W_700, color=theme.WARNING),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=14, accent=theme.WARNING,
        )

        water_card = glass_card(
            ft.Column([
                ft.Row([ft.Icon(ft.Icons.WATER_DROP, color=theme.ACCENT),
                        ft.Text("Water Usage", size=16, weight=ft.FontWeight.W_600, color=theme.text_primary())],
                       spacing=8),
                ft.Row([
                    ft.Text(f"Total: {current['water_total']}L", size=13, color=theme.TEXT_MID),
                    ft.Text(f"Cleaning: {current['water_cleaning']}L", size=13, color=theme.WARNING),
                    ft.Text(f"Sold: {current['water_sold']}L", size=13, color=theme.SUCCESS),
                ], spacing=20),
                ft.ProgressBar(
                    value=current["water_sold"] / max(current["water_total"], 1),
                    color=theme.ACCENT, bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                    bar_height=8, border_radius=4,
                ),
                ft.Text(f"Efficiency: {current['water_sold'] / max(current['water_total'], 1) * 100:.0f}% sold",
                        size=12, color=theme.TEXT_DIM),
            ], spacing=8),
            padding=16, accent=theme.ACCENT,
        )

        products = self.services.inventory.all_products()
        stock_grid = ft.GridView(
            controls=[stock_card(item) for item in products],
            runs_count=2, max_extent=150, spacing=8, run_spacing=8, child_aspect_ratio=1.0, height=220,
        )

        return [
            self._business_day_card(),
            kpi_grid,
            outstanding_card,
            water_card,
            section_title("Stock Levels", ft.Icons.INVENTORY_2_OUTLINED),
            stock_grid,
        ]
