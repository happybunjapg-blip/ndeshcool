"""Catalog page — the professional ERP hub for a water station.

Catalog
├── Physical Products   (inventory: bottles, pumps, caps, taps)
├── Services            (no stock: delivery, installation, cleaning)
└── Water Configuration (the station's core commodity — config, not a product)

Owner and Co-owner can add/edit/archive physical products and services,
and edit the water configuration. Workers have read-only access.
"""
import flet as ft
import theme
from models import Product, Service
from widgets import glass_card, hero_card, section_title, primary_button, show_snack
from services import Services


class PartnerCatalogPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate, user=None):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.user = user
        self._can_edit = user is not None and user.role.value in ("owner", "co_owner")

        # Add dialog state
        self._dialog_open = False
        self._dialog_type = "product"

        # Product edit state
        self._editing_product_id = None
        self._editing_service_id = None

        # --- Product form fields ---
        self.product_name_field = ft.TextField(
            label="Product Name", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.product_buy_field = ft.TextField(
            label="Buying Price (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.product_sell_field = ft.TextField(
            label="Selling Price (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.product_stock_field = ft.TextField(
            label="Opening Stock", keyboard_type=ft.KeyboardType.NUMBER,
            value="0", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.product_low_field = ft.TextField(
            label="Low Stock Alert", keyboard_type=ft.KeyboardType.NUMBER,
            value="0", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.product_track_switch = ft.Switch(
            label="Track inventory", value=True, active_color=theme.ACCENT,
        )

        # --- Service form fields ---
        self.service_name_field = ft.TextField(
            label="Service Name", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.service_cost_field = ft.TextField(
            label="Cost (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            value="0", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.service_sell_field = ft.TextField(
            label="Selling Price (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            value="0", expand=True, border_radius=theme.RADIUS_INPUT,
        )

        # --- Water config fields ---
        self.water_cost_field = ft.TextField(
            label="Cost Per Litre (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.water_sell_field = ft.TextField(
            label="Selling Price Per Litre (KES)", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.water_custom_switch = ft.Switch(
            label="Allow custom size", value=True, active_color=theme.ACCENT,
        )

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------
    def _reset_forms(self):
        self._editing_product_id = None
        self._editing_service_id = None
        self.product_name_field.value = ""
        self.product_buy_field.value = "0"
        self.product_sell_field.value = "0"
        self.product_stock_field.value = "0"
        self.product_low_field.value = "0"
        self.product_track_switch.value = True
        self.service_name_field.value = ""
        self.service_cost_field.value = "0"
        self.service_sell_field.value = "0"

    def _load_water_config(self):
        config = self.services.water_config.get()
        self.water_cost_field.value = str(config.cost_per_litre)
        self.water_sell_field.value = str(config.selling_price_per_litre)
        self.water_custom_switch.value = config.custom_allowed

    # ---------------------------------------------------------------
    # Add dialog
    # ---------------------------------------------------------------
    def _open_add_dialog(self):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage the catalog.", theme.DANGER)
            return
        self._reset_forms()
        self._dialog_open = True
        self._dialog_type = "product"
        self.on_navigate("catalog")

    def _save_dialog(self, e):
        if self._dialog_type == "product":
            self._save_product()
        else:
            self._save_service()
        self._dialog_open = False
        self.on_navigate("catalog")

    def _set_dialog_type(self, dialog_type: str):
        self._dialog_type = dialog_type
        self.on_navigate("catalog")

    def _cancel_dialog(self, e):
        self._dialog_open = False
        self.on_navigate("catalog")

    # ---------------------------------------------------------------
    # Product CRUD
    # ---------------------------------------------------------------
    def _validate_product(self) -> bool:
        name = (self.product_name_field.value or "").strip()
        if not name:
            show_snack(self.page, "Product name is required.", theme.DANGER)
            return False
        try:
            buy = float(self.product_buy_field.value or 0)
            sell = float(self.product_sell_field.value or 0)
            stock = float(self.product_stock_field.value or 0)
            low = float(self.product_low_field.value or 0)
            if buy < 0 or sell < 0 or stock < 0 or low < 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Enter valid prices and stock.", theme.DANGER)
            return False
        return True

    def _save_product(self):
        if not self._validate_product():
            return
        name = (self.product_name_field.value or "").strip()
        buy = float(self.product_buy_field.value or 0)
        sell = float(self.product_sell_field.value or 0)
        stock = float(self.product_stock_field.value or 0)
        low = float(self.product_low_field.value or 0)
        track = self.product_track_switch.value

        if self._editing_product_id:
            product = self.services.state.get_product_by_id(self._editing_product_id)
            if not product:
                show_snack(self.page, "Product not found.", theme.DANGER)
                return
            product.name = name
            product.buying_price = buy
            product.selling_price = sell
            product.opening_stock = stock
            product.threshold = low
            product.track_inventory = track
            self.services.state.update_product(product)
            show_snack(self.page, f"Product '{name}' updated.")
        else:
            product = Product(
                name=name,
                buying_price=buy,
                selling_price=sell,
                opening_stock=stock,
                threshold=low,
                track_inventory=track,
                active=True,
            )
            product.qty = stock  # opening stock becomes current stock
            self.services.state.add_product(product)
            show_snack(self.page, f"Product '{name}' added.")

    def _start_edit_product(self, product_id: str):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage the catalog.", theme.DANGER)
            return
        product = self.services.state.get_product_by_id(product_id)
        if not product:
            return
        self._reset_forms()
        self._editing_product_id = product_id
        self._dialog_type = "product"
        self._dialog_open = True
        self.product_name_field.value = product.name
        self.product_buy_field.value = str(product.buying_price)
        self.product_sell_field.value = str(product.selling_price)
        self.product_stock_field.value = str(product.opening_stock)
        self.product_low_field.value = str(product.threshold)
        self.product_track_switch.value = product.track_inventory
        self.on_navigate("catalog")

    def _toggle_product_active(self, product_id: str, active: bool):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage the catalog.", theme.DANGER)
            return
        self.services.state.set_product_active(product_id, active)
        show_snack(self.page, "Product updated.")
        self.on_navigate("catalog")

    # ---------------------------------------------------------------
    # Service CRUD
    # ---------------------------------------------------------------
    def _validate_service(self) -> bool:
        name = (self.service_name_field.value or "").strip()
        if not name:
            show_snack(self.page, "Service name is required.", theme.DANGER)
            return False
        try:
            cost = float(self.service_cost_field.value or 0)
            sell = float(self.service_sell_field.value or 0)
            if cost < 0 or sell < 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Enter valid cost and selling price.", theme.DANGER)
            return False
        return True

    def _save_service(self):
        if not self._validate_service():
            return
        name = (self.service_name_field.value or "").strip()
        cost = float(self.service_cost_field.value or 0)
        sell = float(self.service_sell_field.value or 0)

        if self._editing_service_id:
            service = self.services.state.get_service_by_id(self._editing_service_id)
            if not service:
                show_snack(self.page, "Service not found.", theme.DANGER)
                return
            service.name = name
            service.cost = cost
            service.selling_price = sell
            self.services.state.update_service(service)
            show_snack(self.page, f"Service '{name}' updated.")
        else:
            self.services.services_catalog.add_service(name, cost, sell)
            show_snack(self.page, f"Service '{name}' added.")

    def _start_edit_service(self, service_id: str):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage the catalog.", theme.DANGER)
            return
        service = self.services.state.get_service_by_id(service_id)
        if not service:
            return
        self._reset_forms()
        self._editing_service_id = service_id
        self._dialog_type = "service"
        self._dialog_open = True
        self.service_name_field.value = service.name
        self.service_cost_field.value = str(service.cost)
        self.service_sell_field.value = str(service.selling_price)
        self.on_navigate("catalog")

    def _toggle_service_active(self, service_id: str, active: bool):
        if not self._can_edit:
            show_snack(self.page, "Only owners can manage the catalog.", theme.DANGER)
            return
        self.services.state.set_service_active(service_id, active)
        show_snack(self.page, "Service updated.")
        self.on_navigate("catalog")

    # ---------------------------------------------------------------
    # Water configuration save
    # ---------------------------------------------------------------
    def _save_water_config(self, e):
        if not self._can_edit:
            show_snack(self.page, "Only owners can change water config.", theme.DANGER)
            return
        try:
            cost = float(self.water_cost_field.value or 0)
            sell = float(self.water_sell_field.value or 0)
            if cost < 0 or sell < 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Enter valid per-litre prices.", theme.DANGER)
            return
        config = self.services.water_config.get()
        config.cost_per_litre = cost
        config.selling_price_per_litre = sell
        config.custom_allowed = self.water_custom_switch.value
        self.services.state.save_water_config(config)
        show_snack(self.page, "Water configuration saved.")
        self.on_navigate("catalog")

    # ---------------------------------------------------------------
    # UI builders
    # ---------------------------------------------------------------
    def _hero(self) -> ft.Container:
        add_btn = None
        if self._can_edit:
            add_btn = primary_button(
                "Add Item", ft.Icons.ADD_CIRCLE_OUTLINE,
                lambda e: self._open_add_dialog(),
                width=float("inf"),
            )
        return hero_card(
            ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.STORE_OUTLINED,
                                        color=ft.Colors.BLACK, size=22),
                        width=44, height=44, border_radius=theme.RADIUS_MD,
                        alignment=ft.Alignment.CENTER,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                            colors=[theme.ACCENT, ft.Colors.BLUE_400],
                        ),
                    ),
                    ft.Column([
                        ft.Text("Catalog", size=theme.Type.TITLE,
                                weight=ft.FontWeight.W_800, color=theme.text_primary()),
                        ft.Text("Everything your station sells",
                                size=theme.Type.CAPTION, color=theme.text_dim()),
                    ], spacing=2, expand=True),
                ], spacing=theme.SPACING_SM),
                ft.Container(height=theme.SPACING_XS),
                add_btn or ft.Container(),
            ], spacing=0),
            padding=theme.SPACING_LG, accent=theme.ACCENT,
        )

    def _add_dialog(self) -> ft.Container:
        if not self._can_edit or not self._dialog_open:
            return ft.Container()
        type_title = "Edit Product" if self._editing_product_id else \
            ("Edit Service" if self._editing_service_id else "Add Item")

        # Type selector
        type_selector = ft.Row([
            ft.Container(
                content=ft.Text("Physical Product", size=theme.Type.CAPTION,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.BLACK if self._dialog_type == "product" else theme.TEXT_MID),
                padding=ft.Padding(14, 8, 14, 8), border_radius=theme.RADIUS_PILL,
                bgcolor=theme.ACCENT if self._dialog_type == "product" else ft.Colors.TRANSPARENT,
                border=None if self._dialog_type == "product" else ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=lambda e: self._set_dialog_type("product"),
            ),
            ft.Container(
                content=ft.Text("Service", size=theme.Type.CAPTION,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.BLACK if self._dialog_type == "service" else theme.TEXT_MID),
                padding=ft.Padding(14, 8, 14, 8), border_radius=theme.RADIUS_PILL,
                bgcolor=theme.ACCENT if self._dialog_type == "service" else ft.Colors.TRANSPARENT,
                border=None if self._dialog_type == "service" else ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=lambda e: self._set_dialog_type("service"),
            ),
        ], spacing=theme.SPACING_XS)

        # Common fields
        fields = [type_selector]

        if self._dialog_type == "product":
            fields += [
                self.product_name_field,
                ft.Row([self.product_buy_field, self.product_sell_field], spacing=10),
                ft.Row([self.product_stock_field, self.product_low_field], spacing=10),
                self.product_track_switch,
            ]
        else:
            fields += [
                self.service_name_field,
                ft.Row([self.service_cost_field, self.service_sell_field], spacing=10),
            ]

        fields += [
            ft.Container(height=theme.SPACING_XS),
            primary_button("Save", ft.Icons.SAVE_OUTLINED, self._save_dialog,
                           width=float("inf")),
            ft.OutlinedButton(
                "Cancel",
                on_click=self._cancel_dialog,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_INPUT),
                    padding=ft.Padding(20, 16, 20, 16),
                ),
            ),
        ]

        return glass_card(
            ft.Column(fields, spacing=theme.SPACING_SM),
            padding=theme.SPACING_MD, accent=theme.ACCENT,
        )

    def _product_card(self, product: Product) -> ft.Container:
        status_color = theme.SUCCESS if product.active else theme.TEXT_DIM
        status_text = "Active" if product.active else "Archived"

        actions = []
        if self._can_edit:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED, icon_color=theme.ACCENT, tooltip="Edit",
                    on_click=lambda e, pid=product.id: self._start_edit_product(pid),
                    width=36, height=36,
                )
            )
            if product.active:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.ARCHIVE_OUTLINED, icon_color=theme.TEXT_DIM, tooltip="Archive",
                        on_click=lambda e, pid=product.id: self._toggle_product_active(pid, False),
                        width=36, height=36,
                    )
                )
            else:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.UNARCHIVE_OUTLINED, icon_color=theme.SUCCESS, tooltip="Activate",
                        on_click=lambda e, pid=product.id: self._toggle_product_active(pid, True),
                        width=36, height=36,
                    )
                )

        return glass_card(
            ft.Row([
                ft.Column([
                    ft.Text(product.name, size=theme.Type.BODY,
                            weight=ft.FontWeight.W_700, color=theme.text_primary()),
                    ft.Row([
                        ft.Text(f"Sell KES {product.selling_price:,.0f}",
                                size=theme.Type.SECTION, weight=ft.FontWeight.W_800, color=theme.GOLD),
                        ft.Text(f"Buy KES {product.buying_price:,.0f}",
                                size=theme.Type.CAPTION, color=theme.text_dim()),
                        ft.Text(f"Stock {product.qty:g}",
                                size=theme.Type.CAPTION, color=theme.text_secondary()),
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

    def _service_card(self, service: Service) -> ft.Container:
        status_color = theme.SUCCESS if service.active else theme.TEXT_DIM
        status_text = "Active" if service.active else "Archived"

        actions = []
        if self._can_edit:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED, icon_color=theme.ACCENT, tooltip="Edit",
                    on_click=lambda e, sid=service.id: self._start_edit_service(sid),
                    width=36, height=36,
                )
            )
            if service.active:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.ARCHIVE_OUTLINED, icon_color=theme.TEXT_DIM, tooltip="Archive",
                        on_click=lambda e, sid=service.id: self._toggle_service_active(sid, False),
                        width=36, height=36,
                    )
                )
            else:
                actions.append(
                    ft.IconButton(
                        icon=ft.Icons.UNARCHIVE_OUTLINED, icon_color=theme.SUCCESS, tooltip="Activate",
                        on_click=lambda e, sid=service.id: self._toggle_service_active(sid, True),
                        width=36, height=36,
                    )
                )

        return glass_card(
            ft.Row([
                ft.Column([
                    ft.Text(service.name, size=theme.Type.BODY,
                            weight=ft.FontWeight.W_700, color=theme.text_primary()),
                    ft.Row([
                        ft.Text(f"Sell KES {service.selling_price:,.0f}",
                                size=theme.Type.SECTION, weight=ft.FontWeight.W_800, color=theme.GOLD),
                        ft.Text(f"Cost KES {service.cost:,.0f}",
                                size=theme.Type.CAPTION, color=theme.text_dim()),
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
            padding=theme.SPACING_MD, accent=theme.ACCENT if service.active else None,
        )

    def _water_config_card(self) -> ft.Container:
        self._load_water_config()
        config = self.services.water_config.get()
        sizes = ", ".join(f"{int(s)}L" if s == int(s) else f"{s}L" for s in config.refill_sizes)
        save_btn = None
        if self._can_edit:
            save_btn = primary_button(
                "Save Configuration", ft.Icons.SAVE_OUTLINED,
                self._save_water_config, bgcolor=theme.GOLD, width=float("inf"),
            )
        edit_section = []
        if self._can_edit:
            edit_section.append(
                ft.Column([
                    ft.Row([self.water_cost_field, self.water_sell_field], spacing=10),
                    self.water_custom_switch,
                    save_btn,
                ], spacing=theme.SPACING_SM)
            )
        return glass_card(
            ft.Column([
                section_title("Water Configuration", ft.Icons.WATER_DROP),
                ft.Text("The station's core commodity — configured per litre, not a product.",
                        size=theme.Type.CAPTION, color=theme.text_dim()),
                ft.Divider(height=1, color=theme.SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Cost / Litre", size=theme.Type.CAPTION, color=theme.text_secondary()),
                        ft.Text(f"KES {config.cost_per_litre:,.2f}", size=theme.Type.BODY,
                                weight=ft.FontWeight.W_700, color=theme.text_primary()),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Selling / Litre", size=theme.Type.CAPTION, color=theme.text_secondary()),
                        ft.Text(f"KES {config.selling_price_per_litre:,.2f}", size=theme.Type.BODY,
                                weight=ft.FontWeight.W_700, color=theme.GOLD),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Refill Sizes", size=theme.Type.CAPTION, color=theme.text_secondary()),
                        ft.Text(sizes, size=theme.Type.CAPTION, weight=ft.FontWeight.W_600,
                                color=theme.ACCENT),
                    ], spacing=2, expand=True),
                ], spacing=theme.SPACING_SM),
                *edit_section,
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
        services = self.services.services_catalog.list_services()
        active_services = [s for s in services if s.active]
        archived_services = [s for s in services if not s.active]

        controls = [self._hero(), self._add_dialog(), self._water_config_card()]

        # Physical Products section
        controls.append(section_title("Physical Products", ft.Icons.INVENTORY_2_OUTLINED))
        if active_products:
            controls.extend(self._product_card(p) for p in active_products)
        else:
            controls.append(
                ft.Text("No physical products yet.", size=theme.Type.CAPTION, color=theme.text_dim())
            )
        if archived_products:
            controls.append(
                ft.Text("Archived", size=theme.Type.SECTION,
                        weight=ft.FontWeight.W_700, color=theme.text_dim())
            )
            controls.extend(self._product_card(p) for p in archived_products)

        # Services section
        controls.append(section_title("Services", ft.Icons.HANDYMAN_OUTLINED))
        if active_services:
            controls.extend(self._service_card(s) for s in active_services)
        else:
            controls.append(
                ft.Text("No services yet.", size=theme.Type.CAPTION, color=theme.text_dim())
            )
        if archived_services:
            controls.append(
                ft.Text("Archived", size=theme.Type.SECTION,
                        weight=ft.FontWeight.W_700, color=theme.text_dim())
            )
            controls.extend(self._service_card(s) for s in archived_services)

        return controls