from datetime import datetime
import flet as ft
import theme
from constants import TODAY
from widgets import glass_card, section_title, stock_card, primary_button, show_snack
from services import Services, SalesError, BusinessDayError


class WorkerHomePage:
    """Today's meter reading and a glance at stock —
    the things a worker checks first thing in the morning."""

    def __init__(self, page: ft.Page, services: Services, on_navigate, user=None):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.user = user

        self.initial_field = ft.TextField(label="Initial Reading (L)", keyboard_type=ft.KeyboardType.NUMBER,
                                           expand=True, border_radius=theme.RADIUS_INPUT)
        self.final_field = ft.TextField(label="Final Reading (L)", keyboard_type=ft.KeyboardType.NUMBER,
                                         expand=True, border_radius=theme.RADIUS_INPUT)

    def _close_business_day(self, e):
        try:
            email = self.user.email if self.user and hasattr(self.user, 'email') else "worker"
            self.services.business_day.close_day(email)
        except BusinessDayError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        show_snack(self.page, "Business Day closed.")
        self.on_navigate("home")  # app.py will bounce back to the gate on next render

    def _business_day_card(self):
        day = self.services.business_day.current()
        if not day:
            return None
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
                ft.TextButton("Close Day", style=ft.ButtonStyle(color=theme.DANGER),
                              on_click=self._close_business_day),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=12, accent=theme.SUCCESS,
        )

    def _submit_water_reading(self, e):
        try:
            initial = float(self.initial_field.value or 0)
            final = float(self.final_field.value or 0)
        except ValueError:
            show_snack(self.page, "Enter valid numbers.", theme.DANGER)
            return
        try:
            self.services.sales.record_meter_reading(initial, final)
        except SalesError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        self.initial_field.value = ""
        self.final_field.value = ""
        show_snack(self.page, "Meter reading saved! Cleaning calculated automatically.")
        self.on_navigate("home")

    def build(self) -> list:
        products = self.services.inventory.all_products()
        stock_grid = ft.GridView(
            controls=[stock_card(item, compact=True) for item in products],
            runs_count=2, max_extent=150, spacing=8, run_spacing=8,
            child_aspect_ratio=1.1, height=220,
        )

        water_card = glass_card(
            ft.Column([
                section_title("Water Meter", ft.Icons.WATER_DROP),
                ft.Row([self.initial_field, self.final_field], spacing=10),
                primary_button(
                    "Submit Reading", ft.Icons.SAVE_OUTLINED, self._submit_water_reading,
                ),
            ], spacing=12),
            padding=16, accent=theme.ACCENT,
        )

        low_stock = self.services.inventory.low_stock()
        alert_banner = []
        if low_stock:
            names = ", ".join(i.name for i in low_stock)
            alert_banner = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=theme.WARNING, size=18),
                        ft.Text(f"Low stock: {names}", size=12, color=theme.WARNING,
                                weight=ft.FontWeight.W_600, expand=True),
                    ], spacing=8),
                    bgcolor=ft.Colors.with_opacity(0.1, theme.WARNING),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.3, theme.WARNING)),
                    border_radius=14, padding=12,
                )
            ]

        return [*alert_banner, self._business_day_card(), water_card,
                section_title("Stock Glance", ft.Icons.INVENTORY_2_OUTLINED),
                stock_grid]