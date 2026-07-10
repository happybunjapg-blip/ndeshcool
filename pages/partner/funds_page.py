import flet as ft
import theme
from constants import CAPITAL_EXPENSE_CATEGORIES, TODAY
from widgets import glass_card, section_title, primary_button, show_snack
from services import Services


class PartnerFundsPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.category_dd = ft.Dropdown(
            label="Category",
            options=[ft.DropdownOption(key=c, text=c) for c in CAPITAL_EXPENSE_CATEGORIES],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.desc_field = ft.TextField(label="Description", expand=True, border_radius=theme.RADIUS_INPUT)
        self.amount_field = ft.TextField(label="Amount (KES)", keyboard_type=ft.KeyboardType.NUMBER,
                                          expand=True, border_radius=theme.RADIUS_INPUT)
        self.date_field = ft.TextField(label="Date (YYYY-MM-DD)", value=TODAY.isoformat(),
                                        expand=True, border_radius=theme.RADIUS_INPUT)

    def _add_expense(self, e):
        category = self.category_dd.value
        if not category:
            show_snack(self.page, "Select category.", theme.DANGER)
            return
        try:
            amount = float(self.amount_field.value or 0)
            if amount <= 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Valid amount required.", theme.DANGER)
            return
        self.services.sales.record_expense(
            (self.desc_field.value or "—").strip() or "—", amount,
            is_capital=True, category=category,
        )
        self.category_dd.value = None
        self.desc_field.value = ""
        self.amount_field.value = ""
        self.date_field.value = TODAY.isoformat()
        show_snack(self.page, f"Capital expense of KES {amount:,.0f} recorded.")
        self.on_navigate("funds")

    def build(self) -> list:
        expenses = self.services.state.capital_expenses
        total = sum(e["amount"] for e in expenses)
        rows = [
            glass_card(
                ft.Row([
                    ft.Column([
                        ft.Text(e["category"], size=13, weight=ft.FontWeight.W_600, color=theme.text_primary()),
                        ft.Text(e["description"], size=11, color=theme.TEXT_DIM),
                        ft.Text(e["date"], size=10, color=theme.TEXT_DIM),
                    ], spacing=2, expand=True),
                    ft.Text(f"KES {e['amount']:,.0f}", size=14, weight=ft.FontWeight.W_700, color=theme.DANGER),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12,
            ) for e in reversed(expenses)
        ] or [ft.Text("No capital expenses recorded.", color=theme.TEXT_DIM)]

        return [
            section_title("Capital Expenses", ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
            glass_card(
                ft.Column([
                    self.category_dd, self.desc_field,
                    ft.Row([self.amount_field, self.date_field], spacing=10),
                    primary_button("Add Expense", ft.Icons.ADD_CIRCLE_OUTLINE, self._add_expense,
                                   bgcolor=theme.GOLD, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.GOLD,
            ),
            section_title("All Expenses", ft.Icons.LIST_ALT),
            ft.Column(rows, spacing=10),
            glass_card(
                ft.Row([
                    ft.Text("Total", size=14, weight=ft.FontWeight.W_600, color=theme.text_primary()),
                    ft.Text(f"KES {total:,.0f}", size=16, weight=ft.FontWeight.W_700, color=theme.DANGER),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=14,
            ),
        ]
