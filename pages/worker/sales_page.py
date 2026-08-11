"""Sales page — record water refills, physical product sales, and services.

Water flow: choose a size (5L / 10L / 20L / Custom) from the configured
water pricing. Cost, revenue, and profit are computed automatically from
the per-litre configuration — the worker never enters a water price.

Physical Product flow: choose a physical product (bottle, pump, cap, tap).
Buying price, selling price, and stock are used automatically from the
stored product data.

Service flow: choose a Service (Delivery, Installation, Cleaning). No
stock involved — only the selling price is charged.
"""
import flet as ft
import theme
from constants import BODA_FEE, PAYMENT_METHODS
from widgets import glass_card, hero_card, section_title, primary_button, show_snack
from services import Services, SalesError


TRANSACTION_LABELS = {
    "water": "Water",
    "product": "Physical Product",
    "service": "Service",
}


class WorkerSalesPage:
    """One page, three ways to sell — each backed by the right catalog
    entity (Water config, Physical Product, Service)."""

    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.tx_type = "water"

        # Water controls — sizes come from the water configuration
        self.water_size_dd = ft.Dropdown(
            label="Size",
            options=[],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.water_liters_field = ft.TextField(
            label="Custom Litres", value="",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT, visible=False,
        )
        self.water_price_display = ft.Text(
            "", size=theme.Type.BODY, weight=ft.FontWeight.W_700,
            color=theme.GOLD,
        )

        # Product controls — loaded from DB (active physical products only)
        self.product_dd = ft.Dropdown(
            label="Product",
            options=[],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Service controls — loaded from DB (active services only)
        self.service_dd = ft.Dropdown(
            label="Service",
            options=[],
            expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # Shared controls
        self.qty_field = ft.TextField(
            label="Quantity", value="1", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.payment_dd = ft.Dropdown(
            label="Payment Method",
            options=[ft.DropdownOption(key=m, text=m) for m in PAYMENT_METHODS],
            value="Cash", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.boda_checkbox = ft.Checkbox(
            label=f"Boda delivery (+KES {BODA_FEE})", value=False,
            active_color=theme.ACCENT,
        )
        self.on_credit_switch = ft.Switch(
            label="On credit (bill a customer)", value=False,
            active_color=theme.ACCENT,
        )
        self.customer_dd = ft.Dropdown(
            label="Customer",
            options=[ft.DropdownOption(key=c.id, text=c.name)
                     for c in self.services.customers.list_customers()],
            expand=True, border_radius=theme.RADIUS_INPUT, visible=False,
        )

        def _toggle_customer_visibility(e):
            self.customer_dd.visible = self.on_credit_switch.value
            self.page.update()

        self.on_credit_switch.on_change = _toggle_customer_visibility

    # -----------------------------------------------------------
    def _refresh_dropdowns(self):
        """Load active products/services and the water sizes from config."""
        active_products = self.services.state.list_active_products()
        self.product_dd.options = [
            ft.DropdownOption(key=p.name, text=f"{p.name}  ({p.qty:g} in stock)")
            for p in active_products
        ]
        active_services = self.services.state.list_active_services()
        self.service_dd.options = [
            ft.DropdownOption(key=s.name, text=s.name)
            for s in active_services
        ]

        config = self.services.water_config.get()
        sizes = config.refill_sizes
        if config.custom_allowed:
            sizes = sizes + [0]  # 0 = custom
        self.water_size_dd.options = [
            ft.DropdownOption(
                key=str(s) if s else "custom",
                text="Custom" if not s else f"{int(s)}L" if s == int(s) else f"{s}L",
            )
            for s in sizes
        ]
        if self.water_size_dd.options:
            self.water_size_dd.value = self.water_size_dd.options[0].key

    def _set_type(self, tx_type: str):
        self.tx_type = tx_type
        self.on_navigate("sales")

    def _fields_for_type(self) -> list:
        if self.tx_type == "water":
            return [self.water_size_dd, self.water_liters_field,
                    self.water_price_display, self.payment_dd, self.boda_checkbox]
        if self.tx_type == "product":
            return [self.product_dd, self.qty_field, self.payment_dd]
        if self.tx_type == "service":
            return [self.service_dd, self.payment_dd, self.boda_checkbox]
        return []

    def _confirm(self, e):
        try:
            customer_id = self.customer_dd.value if self.on_credit_switch.value else None
            on_credit = self.on_credit_switch.value
            if on_credit and not customer_id:
                show_snack(self.page, "Select a customer for credit sales.", theme.DANGER)
                return

            if self.tx_type == "water":
                if self.water_size_dd.value == "custom":
                    liters = float(self.water_liters_field.value or 0)
                else:
                    liters = float(self.water_size_dd.value)
                if liters <= 0:
                    show_snack(self.page, "Enter a valid water amount.", theme.DANGER)
                    return
                tx = self.services.sales.record_water_refill(
                    liters, self.payment_dd.value, boda=self.boda_checkbox.value,
                    customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Water refill: {liters:g}L (KES {tx.amount:,.0f})")

            elif self.tx_type == "product":
                qty = float(self.qty_field.value or 0)
                tx = self.services.sales.record_product_sale(
                    self.product_dd.value, qty, self.payment_dd.value,
                    customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Sale: {qty:g} x {self.product_dd.value} (KES {tx.amount:,.0f})")

            elif self.tx_type == "service":
                tx = self.services.sales.record_service_sale(
                    self.service_dd.value, self.payment_dd.value,
                    customer_id=customer_id, on_credit=on_credit,
                )
                show_snack(self.page, f"Service: {self.service_dd.value} (KES {tx.amount:,.0f})")

        except SalesError as err:
            show_snack(self.page, str(err), theme.DANGER)
            return
        except (ValueError, TypeError):
            show_snack(self.page, "Please fill in all fields correctly.", theme.DANGER)
            return

        self.qty_field.value = "1"
        self.water_liters_field.value = ""
        self.boda_checkbox.value = False
        self.on_credit_switch.value = False
        self.customer_dd.visible = False
        self.water_price_display.value = ""
        self.on_navigate("sales")

    # -----------------------------------------------------------
    def _hero(self) -> ft.Container:
        return hero_card(
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.POINT_OF_SALE_OUTLINED,
                                    color=ft.Colors.BLACK, size=22),
                    width=44, height=44, border_radius=theme.RADIUS_MD,
                    alignment=ft.Alignment.CENTER,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                        colors=[theme.ACCENT, ft.Colors.BLUE_400],
                    ),
                ),
                ft.Column([
                    ft.Text("Sales", size=theme.Type.TITLE,
                            weight=ft.FontWeight.W_800, color=theme.text_primary()),
                    ft.Text("What do I want to sell right now?",
                            size=theme.Type.CAPTION, color=theme.text_dim()),
                ], spacing=2, expand=True),
            ], spacing=theme.SPACING_SM, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_LG, accent=theme.ACCENT,
        )

    def _type_selector(self) -> ft.Row:
        chips = []
        for key, label in TRANSACTION_LABELS.items():
            selected = key == self.tx_type
            chips.append(
                ft.Container(
                    content=ft.Text(label, size=theme.Type.CAPTION,
                                    weight=ft.FontWeight.W_700,
                                    color=ft.Colors.BLACK if selected else theme.TEXT_MID),
                    padding=ft.Padding(16, 10, 16, 10),
                    border_radius=theme.RADIUS_PILL,
                    bgcolor=theme.ACCENT if selected else ft.Colors.TRANSPARENT,
                    border=None if selected else ft.Border.all(1, theme.SURFACE_BORDER),
                    on_click=lambda e, k=key: self._set_type(k),
                )
            )
        return ft.Row(chips, spacing=theme.SPACING_XS, wrap=True)

    def _empty_state(self) -> ft.Container:
        return hero_card(
            ft.Column([
                ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=52, color=theme.TEXT_DIM),
                ft.Text("Nothing to sell yet.", size=theme.Type.SECTION,
                        weight=ft.FontWeight.W_700, color=theme.text_primary()),
                ft.Text("Ask your owner to add products and services to the catalog.",
                        size=theme.Type.CAPTION, color=theme.text_dim()),
            ], spacing=theme.SPACING_SM, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_XL, accent=theme.ACCENT,
        )

    def build(self) -> list:
        self._refresh_dropdowns()
        active_products = self.services.state.list_active_products()
        active_services = self.services.state.list_active_services()

        if not active_products and not active_services:
            return [
                self._hero(),
                self._empty_state(),
            ]

        return [
            self._hero(),
            section_title("Sell", ft.Icons.CATEGORY_OUTLINED),
            self._type_selector(),
            glass_card(
                ft.Column([
                    *self._fields_for_type(),
                    ft.Divider(height=1, color=theme.SURFACE_BORDER),
                    self.on_credit_switch,
                    self.customer_dd,
                    ft.Container(height=theme.SPACING_XS),
                    primary_button("Confirm Sale", ft.Icons.CHECK_CIRCLE_OUTLINE,
                                   self._confirm, width=float("inf")),
                ], spacing=theme.SPACING_SM),
                padding=theme.SPACING_MD, accent=theme.ACCENT,
            ),
        ]   