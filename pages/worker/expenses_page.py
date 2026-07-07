import flet as ft
import theme
from constants import TODAY
from widgets import glass_card, section_title, primary_button, show_snack
from services import Services, SalesError


class WorkerExpensesPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.desc_field = ft.TextField(label="Description", expand=True, border_radius=theme.RADIUS_INPUT)
        self.amount_field = ft.TextField(label="Amount (KES)", keyboard_type=ft.KeyboardType.NUMBER,
                                          expand=True, border_radius=theme.RADIUS_INPUT)

    def _log_expense(self, e):
        desc = (self.desc_field.value or "").strip()
        try:
            amount = float(self.amount_field.value or 0)
            if amount <= 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Valid amount required.", theme.DANGER)
            return
        if not desc:
            show_snack(self.page, "Enter description.", theme.DANGER)
            return
        try:
            self.services.sales.record_expense(desc, amount, is_capital=False)
        except SalesError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        self.desc_field.value = ""
        self.amount_field.value = ""
        show_snack(self.page, "Expense logged!")
        self.on_navigate("expenses")

    def build(self) -> list:
        todays = [e for e in self.services.state.daily_expenses if e["date"] == TODAY.isoformat()]
        total = sum(e["amount"] for e in todays)
        rows = [
            glass_card(
                ft.Row([
                    ft.Column([ft.Text(e["description"], size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                               ft.Text(e["time"], size=11, color=theme.TEXT_DIM)],
                              spacing=2, expand=True),
                    ft.Text(f"KES {e['amount']:,.0f}", size=14, weight=ft.FontWeight.W_700, color=theme.WARNING),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12,
            ) for e in reversed(todays)
        ] or [ft.Text("No expenses today.", size=13, color=theme.TEXT_DIM)]

        return [
            section_title("Log Daily Expense", ft.Icons.RECEIPT_LONG_OUTLINED),
            glass_card(
                ft.Column([
                    self.desc_field, self.amount_field,
                    primary_button("Log Expense", ft.Icons.SAVE_OUTLINED, self._log_expense,
                                   bgcolor=theme.GOLD, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.GOLD,
            ),
            section_title("Today's Expenses", ft.Icons.LIST_ALT),
            ft.Column(rows, spacing=10),
            glass_card(
                ft.Row([
                    ft.Text("Total", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ft.Text(f"KES {total:,.0f}", size=16, weight=ft.FontWeight.W_700, color=theme.WARNING),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=14,
            ),
        ]
