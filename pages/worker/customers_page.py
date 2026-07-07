import flet as ft
import theme
from widgets import glass_card, section_title, primary_button, customer_card, show_snack
from services import Services, SalesError


class WorkerCustomersPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.selected_customer_id = None

        self.payment_amount_field = ft.TextField(label="Amount (KES)", keyboard_type=ft.KeyboardType.NUMBER,
                                                   expand=True, border_radius=theme.RADIUS_INPUT)
        self.new_name_field = ft.TextField(label="Customer name", expand=True, border_radius=theme.RADIUS_INPUT)
        self.new_phone_field = ft.TextField(label="Phone", expand=True, border_radius=theme.RADIUS_INPUT)

    def _select(self, customer_id: str):
        self.selected_customer_id = customer_id
        self.on_navigate("customers")

    def _take_payment(self, e):
        if not self.selected_customer_id:
            show_snack(self.page, "Select a customer first.", theme.DANGER)
            return
        try:
            amount = float(self.payment_amount_field.value or 0)
            self.services.sales.record_customer_payment(self.selected_customer_id, amount)
        except (SalesError, ValueError) as err:
            show_snack(self.page, str(err) if isinstance(err, SalesError) else "Enter a valid amount.", theme.DANGER)
            return
        self.payment_amount_field.value = ""
        show_snack(self.page, f"Payment of KES {amount:,.0f} recorded.")
        self.on_navigate("customers")

    def _add_customer(self, e):
        name = (self.new_name_field.value or "").strip()
        if not name:
            show_snack(self.page, "Enter a customer name.", theme.DANGER)
            return
        self.services.customers.add_customer(name, phone=(self.new_phone_field.value or "").strip())
        self.new_name_field.value = ""
        self.new_phone_field.value = ""
        show_snack(self.page, f"{name} added.")
        self.on_navigate("customers")

    def build(self) -> list:
        customers = self.services.customers.list_customers()
        selected = next((c for c in customers if c.id == self.selected_customer_id), None)

        cards = [customer_card(c, on_click=lambda e, cid=c.id: self._select(cid)) for c in customers]

        payment_section = []
        if selected:
            payment_section = [
                section_title(f"Record Payment — {selected.name}", ft.Icons.PAYMENTS_OUTLINED),
                glass_card(
                    ft.Column([
                        ft.Text(f"Outstanding balance: KES {selected.balance:,.0f}", size=13, color=theme.TEXT_MID),
                        self.payment_amount_field,
                        primary_button("Record Payment", ft.Icons.CHECK_CIRCLE_OUTLINE,
                                       self._take_payment, bgcolor=theme.SUCCESS, width=float("inf")),
                    ], spacing=12),
                    padding=16, accent=theme.SUCCESS,
                ),
            ]

        return [
            section_title("Customers", ft.Icons.PEOPLE_OUTLINE),
            ft.Column(cards, spacing=10) if cards else ft.Text("No customers yet.", color=theme.TEXT_DIM),
            *payment_section,
            section_title("Add Customer", ft.Icons.PERSON_ADD_OUTLINED),
            glass_card(
                ft.Column([
                    self.new_name_field,
                    self.new_phone_field,
                    primary_button("Add Customer", ft.Icons.ADD_CIRCLE_OUTLINE,
                                   self._add_customer, bgcolor=theme.GOLD, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.GOLD,
            ),
        ]
