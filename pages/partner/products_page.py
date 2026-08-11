"""Product Management page (V1 Product Setup).

Owner and Co-owner can:
  - Add Product
  - Edit Product
  - Archive / Activate Product

Workers have read-only access (they see the list but no edit controls).

Products are scoped to the current business and only active products
appear on the Sales screen.
"""
import flet as ft
import theme
from models import Product
from widgets import glass_card, hero_card, section_title, primary_button, show_snack
from services import Services


class PartnerProductsPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate, user=None):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.user = user
        self._can_edit = user is not None and user.role.value in ("owner", "co_owner")

        # Add / Edit form fields
        self.name_field = ft.TextField(
            label="Product Name", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.price_field = ft.TextField(
            label="Selling Price (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.track_inventory_switch = ft.Switch(
            label="Track inventory", value=True, active_color=theme.ACCENT,
        )
        self._editing_id = None  # None = add mode, else product id being edited

    # ---------------------------------------------------------------
    # Form helpers
    # ---------------------------------------------------------------
    def _reset_form(self):
        self.name_field.value = ""
        self.price_field.value = ""
        self.track_inventory_switch.value = True
        self._editing_id = None

    def _validate(self) -> bool:
        name = (self.name_field.value or "").strip()
        if not name:
            show_snack(self.page, "Product name is required.", theme.DANGER)
            return False
        try:
            price = float(self.price_field.value or 0)
            if price < 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Enter a valid selling price.", theme.DANGER)
            return False
        return True

    # ---------------------------------------------------------------
    # CRUD actions
    # ---------------------------------------------------------------
    def _save_product(self, e):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage products.", theme.DANGER)
            return
        if not self._validate():
            return
        name = (self.name_field.value or "").strip()
        price = float(self.price_field.value or 0)
        track = self.track_inventory_switch.value

        if self._editing_id:
            product = self.services.state.get_product_by_id(self._editing_id)
            if not product:
                show_snack(self.page, "Product not found.", theme.DANGER)
                return
            product.name = name
            product.selling_price = price
            product.track_inventory = track
            self.services.state.update_product(product)
            show_snack(self.page, f"Product '{name}' updated.")
        else:
            product = Product(
                name=name,
                selling_price=price,
                track_inventory=track,
                active=True,
            )
            self.services.state.add_product(product)
            show_snack(self.page, f"Product '{name}' added.")

        self._reset_form()
        self.on_navigate("products")

    def _start_edit(self, product_id: str):
        product = self.services.state.get_product_by_id(product_id)
        if not product:
            return
        self._editing_id = product_id
        self.name_field.value = product.name
        self.price_field.value = str(product.selling_price)
        self.track_inventory_switch.value = product.track_inventory
        self.on_navigate("products")

    def _toggle_active(self, product_id: str, active: bool):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage products.", theme.DANGER)
            return
        product = self.services.state.get_product_by_id(product_id)
        if not product:
            return
        self.services.state.set_product_active(product_id, active)
        action = "activated" if active else "archived"
        show_snack(self.page, f"Product '{product.name}' {action}.")
        self.on_navigate("products")

    # ---------------------------------------------------------------
    # UI builders
    # ---------------------------------------------------------------
    def _hero(self) -> ft.Container:
        """One focal point: 'What do I sell?' with a primary Add action."""
        add_btn = None
        if self._can_edit:
            add_btn = primary_button(
                "Add Product", ft.Icons.ADD_CIRCLE_OUTLINE,
                lambda e: self._reset_form() or self.on_navigate("products"),
                width=float("inf"),
            )
        return hero_card(
            ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.INVENTORY_2_OUTLINED,
                                        color=ft.Colors.BLACK, size=22),
                        width=44, height=44, border_radius=theme.RADIUS_MD,
                        alignment=ft.Alignment.CENTER,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                            colors=[theme.ACCENT, ft.Colors.BLUE_400],
                        ),
                    ),
                    ft.Column([
                        ft.Text("Products", size=theme.Type.TITLE,
                                weight=ft.FontWeight.W_800, color=theme.text_primary()),
                        ft.Text("What do I sell?", size=theme.Type.CAPTION,
                                color=theme.text_dim()),
                    ], spacing=2, expand=True),
                ], spacing=theme.SPACING_SM),
                ft.Container(height=theme.SPACING_XS),
                add_btn or ft.Container(),
            ], spacing=0),
            padding=theme.SPACING_LG, accent=theme.ACCENT,
        )

    def _product_card(self, product: Product) -> ft.Container:
        status_color = theme.SUCCESS if product.active else theme.TEXT_DIM
        status_text = "Active" if product.active else "Archived"

        # Single small Edit action — minimal visual noise
        actions = []
        if self._can_edit:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_color=theme.ACCENT,
                    tooltip="Edit",
                    on_click=lambda e, pid=product.id: self._start_edit(pid),
                    width=36, height=36,
                )
            )
            if product.active:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.ARCHIVE_OUTLINED,
                        icon_color=theme.TEXT_DIM,
                        tooltip="Archive",
                        on_click=lambda e, pid=product.id: self._toggle_active(pid, False),
                        width=36, height=36,
                    )
                )
            else:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.UNARCHIVE_OUTLINED,
                        icon_color=theme.SUCCESS,
                        tooltip="Activate",
                        on_click=lambda e, pid=product.id: self._toggle_active(pid, True),
                        width=36, height=36,
                    )
                )

        return glass_card(
            ft.Row([
                ft.Column([
                    ft.Text(product.name, size=theme.Type.BODY,
                            weight=ft.FontWeight.W_700, color=theme.text_primary()),
                    ft.Row([
                        ft.Text(f"KES {product.selling_price:,.0f}", size=theme.Type.SECTION,
                                weight=ft.FontWeight.W_800, color=theme.GOLD),
                        ft.Container(
                            content=ft.Text(status_text, size=theme.Type.MICRO,
                                            weight=ft.FontWeight.W_700, color=ft.Colors.BLACK),
                            bgcolor=status_color, padding=ft.Padding(8, 3, 8, 3),
                            border_radius=theme.RADIUS_PILL,
                        ),
                    ], spacing=theme.SPACING_SM),
                ], spacing=theme.SPACING_XS, expand=True),
                ft.Row(actions, spacing=2),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_MD, accent=theme.ACCENT if product.active else None,
        )

    def _empty_state(self) -> ft.Container:
        add_btn = None
        if self._can_edit:
            add_btn = primary_button(
                "Add Product", ft.Icons.ADD_CIRCLE_OUTLINE,
                lambda e: self._reset_form() or self.on_navigate("products"),
                width=float("inf"),
            )
        return hero_card(
            ft.Column([
                ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=52, color=theme.TEXT_DIM),
                ft.Text("No products yet.", size=theme.Type.SECTION,
                        weight=ft.FontWeight.W_700, color=theme.text_primary()),
                ft.Text("Add your first product to start selling.",
                        size=theme.Type.CAPTION, color=theme.text_dim()),
                ft.Container(height=theme.SPACING_XS),
                add_btn or ft.Container(),
            ], spacing=theme.SPACING_SM, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.SPACING_XL, accent=theme.ACCENT,
        )

    def _form_card(self) -> ft.Container:
        if not self._can_edit:
            return ft.Container()
        title = "Edit Product" if self._editing_id else "Add Product"
        return glass_card(
            ft.Column([
                section_title(title, ft.Icons.ADD_BUSINESS_OUTLINED),
                self.name_field,
                self.price_field,
                ft.Column([
                    self.track_inventory_switch,
                    ft.Text(
                        "Enable this only for products whose stock is physically tracked.",
                        size=theme.Type.MICRO, color=theme.text_dim(),
                    ),
                ], spacing=2),
                ft.Container(height=theme.SPACING_XS),
                primary_button(
                    "Save Product", ft.Icons.SAVE_OUTLINED, self._save_product,
                    width=float("inf"),
                ),
                ft.OutlinedButton(
                    "Cancel",
                    on_click=lambda e: (self._reset_form(), self.on_navigate("products")),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_INPUT),
                        padding=ft.Padding(20, 16, 20, 16),
                    ),
                ),
            ], spacing=theme.SPACING_SM),
            padding=theme.SPACING_MD, accent=theme.ACCENT,
        )

    # ---------------------------------------------------------------
    # Build
    # ---------------------------------------------------------------
    def build(self) -> list:
        products = self.services.inventory.all_products()
        active_products = [p for p in products if p.active]
        archived_products = [p for p in products if not p.active]

        controls = [self._hero()]

        if self._can_edit:
            controls.append(self._form_card())

        if not products:
            controls.append(self._empty_state())
        else:
            if active_products:
                controls.append(section_title("Active", ft.Icons.CHECK_CIRCLE_OUTLINE))
                controls.extend(self._product_card(p) for p in active_products)
            if archived_products:
                controls.append(section_title("Archived", ft.Icons.ARCHIVE_OUTLINED))
                controls.extend(self._product_card(p) for p in archived_products)

        return controls