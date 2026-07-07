from datetime import datetime, timedelta
import flet as ft
import theme
from constants import TODAY
from widgets import glass_card, section_title, primary_button, show_snack
from services import Services


class PartnerReportsPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.from_field = ft.TextField(label="From", value=(TODAY - timedelta(days=30)).isoformat(),
                                        expand=True, border_radius=theme.RADIUS_INPUT)
        self.to_field = ft.TextField(label="To", value=TODAY.isoformat(),
                                      expand=True, border_radius=theme.RADIUS_INPUT)
        self.summary = self._compute_summary()

    def _compute_summary(self):
        try:
            start = datetime.strptime(self.from_field.value, "%Y-%m-%d").date()
            end = datetime.strptime(self.to_field.value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start, end = TODAY - timedelta(days=30), TODAY
        return self.services.state.calculate_period_metrics(start, end)

    def _generate(self, e):
        if not self.from_field.value or not self.to_field.value:
            show_snack(self.page, "Please select both dates.", theme.DANGER)
            return
        self.summary = self._compute_summary()
        show_snack(self.page, f"Report generated for {self.from_field.value} to {self.to_field.value}")
        self.on_navigate("reports")

    def build(self) -> list:
        s = self.summary
        summary_card = glass_card(
            ft.Column([
                ft.Row([ft.Text("Total Revenue", size=13, color=theme.TEXT_MID),
                        ft.Text(f"KES {s['revenue']:,.0f}", size=14, weight=ft.FontWeight.W_700, color=theme.SUCCESS)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Total Expenses", size=13, color=theme.TEXT_MID),
                        ft.Text(f"KES {s['losses']:,.0f}", size=14, weight=ft.FontWeight.W_700, color=theme.DANGER)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Net Profit", size=13, color=theme.TEXT_MID),
                        ft.Text(f"KES {s['profit'] - s['losses']:,.0f}", size=14, weight=ft.FontWeight.W_700, color=theme.ACCENT)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Water Sold", size=13, color=theme.TEXT_MID),
                        ft.Text(f"{s['water_sold']:,.0f}L", size=14, weight=ft.FontWeight.W_700, color=theme.GOLD)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10),
            padding=16,
        )

        return [
            section_title("Reports", ft.Icons.BAR_CHART_OUTLINED),
            glass_card(
                ft.Column([
                    ft.Row([self.from_field, self.to_field], spacing=10),
                    primary_button("Generate Report", ft.Icons.REFRESH, self._generate, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.ACCENT,
            ),
            section_title("Financial Summary", ft.Icons.RECEIPT_LONG_OUTLINED),
            summary_card,
        ]
