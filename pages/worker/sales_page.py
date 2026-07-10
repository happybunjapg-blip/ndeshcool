import flet as ft
import theme
from constants import BODA_FEE, WATER_REFILL_PRICES, PAYMENT_METHODS, BULK_DELIVERY_SIZES, TRANSPORT_FEE_DEFAULT
from models import ProductCategory
from widgets import glass_card, section_title, primary_button, show_snack
from services import Services, SalesError

TRANSACTION_LABELS = {
    "water_refill": "Water Refill",
    "product_sale": "Product Sale",
    "bottle_water_sale": "Bottle + Water",
    "bulk_delivery": "Bulk Delivery",
}


class WorkerSalesPage:
    """One page, four real transaction types -- each enforces its own
    inventory rule instead of treating every sale the same way."""

    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.tx_type = "water_refill"

        # Water Refill controls
        self.refill_liters_dd = ft.Dropdown(
            label="Container size",
            options=[ft.DropdownOption(key=str(l), text=f"{l}L") for l in WATER_REFILL_PRICES],
            value=str(next(iter(WATER_REFILL_PRICES))),
            expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Product Sale controls
        accessory_names = [p.name for p in self.services.inventory.all_products()
                            if p.category == ProductCategory.ACCESSORY]
        self.product_dd = ft.Dropdown(
            label="Product",
            options=[ft.DropdownOption(key=n, text=n) for n in accessory_names],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Bottle + Water controls
        bottle_names = [p.name for p in self.services.inventory.all_products()
                         if p.category == ProductCategory.BOTTLE_WATER]
        self.bottle_dd = ft.Dropdown(
            label="Bottle size",
            options=[ft.DropdownOption(key=n, text=n) for n in bottle_names],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Bulk Delivery controls
        self.bulk_liters_dd = ft.Dropdown(
            label="Volume",
            options=[ft.DropdownOption(key=str(l), text=f"{l}L") for l in BULK_DELIVERY_SIZES],
            value=str(BULK_DELIVERY_SIZES[0]),
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.driver_field = ft.TextField(label="Driver / Worker", expand=True, border_radius=theme.RADIUS_INPUT)
        self.transport_fee_field = ft.TextField(
            label="Transport Fee (KES)", value=str(TRANSPORT_FEE_DEFAULT),
            keyboard_type=ft.KeyboardType.NUMBER, expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Shared controls
        self.qty_field = ft.TextField(label="Quantity", value="1", keyboard_type=ft.KeyboardType.NUMBER,
                                       expand=True, border_radius=theme.RADIUS_INPUT)
        self.payment_dd = ft.Dropdown(
            label="Payment Method",
            options=[ft.DropdownOption(key=m, text=m) for m in PAYMENT_METHODS],
            value="Cash", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.boda_checkbox = ft.Checkbox(label=f"Boda delivery (+KES {BODA_FEE})", value=False,
                                          active_color=theme.ACCENT)
        self.on_credit_switch = ft.Switch(label="On credit (bill a customer)", value=False,
                                           active_color=theme.ACCENT)
        self.customer_dd = ft.Dropdown(
            label="Customer",
            options=[ft.DropdownOption(key=c.id, text=c.name) for c in self.services.customers.list_customers()],
            expand=True, border_radius=theme.RADIUS_INPUT, visible=False,
        )

        def _toggle_customer_visibility(e):
            self.customer_dd.visible = self.on_credit_switch.value
            self.page.update()

        self.on_credit_switch.on_change = _toggle_customer_visibility

    # -----------------------------------------------------------
    def _set_type(self, tx_type: str):
        self.tx_type = tx_type
        self.on_navigate("sales")

    def _fields_for_type(self) -> list:
        if self.tx_type == "water_refill":
            return [self.qty_field, self.payment_dd, self.boda_checkbox]
        if self.tx_type == "product_sale":
            return [self.product_dd, self.qty_field, self.payment_dd]
        if self.tx_type == "bottle_water_sale":
            return [self.bottle_dd, self.qty_field, self.payment_dd, self.boda_checkbox]
        if self.tx_type == "bulk_delivery":
            return [self.bulk_liters_dd, self.driver_field, self.transport_fee_field]
        return []

    def _confirm(self, e):
        try:
            customer_id = self.customer_dd.value if self.on_credit_switch.value else None
            on_credit = self.on_credit_switch.value
            if on_credit and not customer_id:
                show_snack(self.page, "Select a customer for credit sales.", theme.DANGER)
                return

            if self.tx_type == "water_refill":
                liters = float(self.qty_field.value or 0)
                tx = self.services.sales.record_water_refill(
                    liters, self.payment_dd.value, boda=self.boda_checkbox.value,
                    customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Refill recorded: {liters:g}L (KES {tx.amount:,.0f})")

            elif self.tx_type == "product_sale":
                qty = float(self.qty_field.value or 0)
                tx = self.services.sales.record_product_sale(
                    self.product_dd.value, qty, self.payment_dd.value,
                    customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Sale recorded: {qty:g} x {self.product_dd.value} (KES {tx.amount:,.0f})")

            elif self.tx_type == "bottle_water_sale":
                qty = float(self.qty_field.value or 0)
                tx = self.services.sales.record_bottle_water_sale(
                    self.bottle_dd.value, qty, self.payment_dd.value,
                    boda=self.boda_checkbox.value, customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Sale recorded: {qty:g} x {self.bottle_dd.value} (KES {tx.amount:,.0f})")

            elif self.tx_type == "bulk_delivery":
                liters = float(self.bulk_liters_dd.value)
                fee = float(self.transport_fee_field.value or 0)
                driver = (self.driver_field.value or "").strip() or "Unassigned"
                tx = self.services.sales.record_bulk_delivery(
                    liters, fee, driver, customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Delivery logged: {liters:g}L via {driver} (KES {tx.amount:,.0f})")

        except SalesError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        except (ValueError, TypeError):
            show_snack(self.page, "Please fill in all fields correctly.", theme.DANGER)
            return

        self.qty_field.value = "1"
        self.boda_checkbox.value = False
        self.on_credit_switch.value = False
        self.customer_dd.visible = False
        self.on_navigate("sales")

    # -----------------------------------------------------------
    def _type_selector(self) -> ft.Row:
        chips = []
        for key, label in TRANSACTION_LABELS.items():
            selected = key == self.tx_type
            chips.append(
                ft.Container(
                    content=ft.Text(label, size=12, weight=ft.FontWeight.W_600,
                                     color=ft.Colors.BLACK if selected else theme.TEXT_MID),
                    padding=ft.Padding(12, 8, 12, 8),
                    border_radius=16,
                    bgcolor=theme.ACCENT if selected else ft.Colors.TRANSPARENT,
                    border=None if selected else ft.Border.all(1, theme.SURFACE_BORDER),
                    on_click=lambda e, k=key: self._set_type(k),
                )
            )
        return ft.Row(chips, spacing=8, wrap=True)

    def build(self) -> list:
        return [
            section_title("Record Sale", ft.Icons.POINT_OF_SALE_OUTLINED),
            self._type_selector(),
            glass_card(
                ft.Column([
                    *self._fields_for_type(),
                    ft.Divider(height=1, color=theme.SURFACE_BORDER),
                    self.on_credit_switch,
                    self.customer_dd,
                    primary_button("Confirm", ft.Icons.CHECK_CIRCLE_OUTLINE, self._confirm, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.ACCENT,
            ),
        ]
