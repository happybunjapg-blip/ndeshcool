"""Partner (Owner) Settings page.

Includes:
- Invite Workers (generate/revoke invitation codes)
- Invite Co-Owner (generate owner invitation)
- Price management
- Stock management
- FIFO batch view
"""
import flet as ft
import theme
from widgets import glass_card, section_title, primary_button, show_snack
from services import Services
from services.auth_service import AuthError


class PartnerSettingsPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate

        # Stock management form fields
        self.stock_product_dd = ft.Dropdown(
            label="Product", expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.stock_qty_field = ft.TextField(
            label="Quantity", value="10", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self.stock_price_field = ft.TextField(
            label="Purchase Price (KES)", value="100", keyboard_type=ft.KeyboardType.NUMBER,
            expand=True, border_radius=theme.RADIUS_INPUT,
        )
        self._refresh_product_dd()

        # Invitation management
        self.invitation_code_display = ft.Text("", size=20, weight=ft.FontWeight.W_700,
                                                color=theme.ACCENT, selectable=True)
        self.invitation_expiry_display = ft.Text("", size=11, color=theme.TEXT_DIM)
        self.invitations_list = ft.Column(spacing=8)

    def _refresh_product_dd(self):
        products = self.services.inventory.all_products()
        self.stock_product_dd.options = [
            ft.DropdownOption(key=p.name, text=f"{p.name}  ({p.qty:g} in stock)")
            for p in products
        ]
        if self.stock_product_dd.options:
            self.stock_product_dd.value = self.stock_product_dd.options[0].key

    def _handle_restock(self, e):
        name = self.stock_product_dd.value
        if not name:
            show_snack(self.page, "Select a product.", theme.DANGER)
            return
        try:
            qty = float(self.stock_qty_field.value or 0)
            price = float(self.stock_price_field.value or 0)
            if qty <= 0 or price < 0:
                raise ValueError
        except ValueError:
            show_snack(self.page, "Enter valid quantity and price.", theme.DANGER)
            return
        self.services.inventory.restock(name, qty, price)
        self._refresh_product_dd()
        self.on_navigate("settings")

    def _update_price(self, name: str, attr: str, value: str):
        try:
            new_val = float(value)
        except ValueError:
            show_snack(self.page, "Invalid number", theme.DANGER)
            return
        product = self.services.state.get_product(name)
        if product:
            setattr(product, attr, new_val)
            self.services.state.repo.save_product(product)
            self.page.update()
            show_snack(self.page, f"{name} {attr} updated to {new_val}")

    # ---- Invitation Management -----------------------------------------

    def _generate_worker_invitation(self, e):
        business_id = self.services.state.repo.get_business_id()
        if not business_id:
            show_snack(self.page, "Business not configured.", theme.DANGER)
            return
        try:
            invitation = self.services.auth.generate_invitation_code(
                business_id, owner_invite=False
            )
            self.invitation_code_display.value = invitation.code
            self.invitation_code_display.visible = True
            self.invitation_expiry_display.value = (
                f"Worker code — expires: {invitation.expires_at[:19].replace('T', ' ')}"
            )
            self.invitation_expiry_display.visible = True
            show_snack(self.page, f"Worker invitation: {invitation.code}")
            self._refresh_invitations()
            self.page.update()
        except AuthError as err:
            show_snack(self.page, str(err), theme.DANGER)

    def _generate_owner_invitation(self, e):
        business_id = self.services.state.repo.get_business_id()
        if not business_id:
            show_snack(self.page, "Business not configured.", theme.DANGER)
            return
        # Check max owners limit
        try:
            owner_count = self.services.auth.count_owners(business_id)
            if owner_count >= 2:
                show_snack(self.page, "Maximum of 2 owners already reached.", theme.WARNING)
                return
        except Exception:
            pass
        try:
            invitation = self.services.auth.generate_invitation_code(
                business_id, owner_invite=True
            )
            self.invitation_code_display.value = invitation.code
            self.invitation_code_display.visible = True
            self.invitation_expiry_display.value = (
                f"Co-owner code — expires: {invitation.expires_at[:19].replace('T', ' ')}"
            )
            self.invitation_expiry_display.visible = True
            show_snack(self.page, f"Co-owner invitation: {invitation.code}")
            self._refresh_invitations()
            self.page.update()
        except AuthError as err:
            show_snack(self.page, str(err), theme.DANGER)

    def _revoke_invitation(self, code: str):
        try:
            self.services.auth.revoke_invitation(code)
            show_snack(self.page, f"Invitation {code} revoked.")
            self._refresh_invitations()
            self.page.update()
        except Exception:
            show_snack(self.page, "Failed to revoke invitation.", theme.DANGER)

    def _refresh_invitations(self):
        business_id = self.services.state.repo.get_business_id()
        if not business_id:
            return
        try:
            invitations = self.services.auth.list_invitations(business_id)
        except Exception:
            invitations = []

        rows = []
        for inv in invitations:
            is_owner = inv.get("owner_invite", False)
            status_color = theme.SUCCESS
            status_text = "Active"
            if inv.get("is_invalidated"):
                status_color = theme.TEXT_DIM
                status_text = "Used / Revoked"
            else:
                expires = inv.get("expires_at", "")
                if expires:
                    from datetime import datetime, timezone
                    try:
                        exp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                        if exp < datetime.now(timezone.utc):
                            status_color = theme.DANGER
                            status_text = "Expired"
                    except ValueError:
                        pass

            role_label = "Co-owner" if is_owner else "Worker"
            role_color = theme.GOLD if is_owner else theme.ACCENT

            revoke_btn = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=theme.DANGER,
                tooltip="Revoke",
                on_click=lambda e, c=inv["code"]: self._revoke_invitation(c),
                width=32, height=32,
            )

            rows.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(inv["code"], size=16, weight=ft.FontWeight.W_700,
                                    color=theme.ACCENT, selectable=True),
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(role_label, size=9,
                                                    weight=ft.FontWeight.W_600, color=ft.Colors.BLACK),
                                    bgcolor=role_color, padding=ft.Padding(6, 2, 6, 2),
                                    border_radius=8,
                                ),
                                ft.Text(status_text, size=10, color=status_color),
                            ], spacing=6),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(inv.get("created_at", "")[:10], size=10, color=theme.TEXT_DIM),
                            revoke_btn if not inv.get("is_invalidated") else ft.Container(),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(12, 8, 4, 8),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                )
            )

        if not rows:
            rows = [ft.Text("No invitations generated yet.", size=12, color=theme.TEXT_DIM)]

        self.invitations_list.controls = rows

    # ---- Build ---------------------------------------------------------

    def build(self) -> list:
        products = self.services.inventory.all_products()
        self._refresh_product_dd()
        self._refresh_invitations()

        header = ft.Row([
            ft.Text("Product", width=100, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600),
            ft.Text("Sell Price", width=80, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text("Buy Price", width=80, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        rows = [header]
        for item in products:
            rows.append(
                ft.Row([
                    ft.Text(item.name, width=100, weight=ft.FontWeight.W_600, size=12, color=theme.text_primary()),
                    ft.TextField(value=str(item.selling_price), width=80, border_radius=10,
                                 content_padding=ft.Padding(8, 8, 8, 8), text_align=ft.TextAlign.CENTER,
                                 on_change=lambda e, n=item.name: self._update_price(n, "selling_price", e.control.value)),
                    ft.TextField(value=str(item.buying_price), width=80, border_radius=10,
                                 content_padding=ft.Padding(8, 8, 8, 8), text_align=ft.TextAlign.CENTER,
                                 on_change=lambda e, n=item.name: self._update_price(n, "buying_price", e.control.value)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        batch_rows = []
        for item in products:
            if item.batches:
                batch_rows.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item.name, size=13, weight=ft.FontWeight.W_700, color=theme.text_primary()),
                                ft.Text(f"Total: {sum(b.qty for b in item.batches):g} units",
                                        size=12, color=theme.TEXT_DIM),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            *[
                                ft.Container(
                                    content=ft.Row([
                                        ft.Text(f"Batch #{i+1}", size=11, color=theme.text_secondary(), width=60),
                                        ft.Text(f"{b.qty:g} remaining", size=12, weight=ft.FontWeight.W_600,
                                                color=theme.SUCCESS if b.qty > 0 else theme.TEXT_DIM, expand=True),
                                        ft.Text(f"@ KES {b.purchase_price:,.0f}", size=11, color=theme.GOLD, width=90),
                                        ft.Text(b.date, size=10, color=theme.TEXT_DIM, width=80),
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    padding=ft.Padding(8, 4, 8, 4), border_radius=8,
                                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                                )
                                for i, b in enumerate(item.batches)
                            ],
                        ], spacing=6),
                        padding=ft.Padding(0, 0, 0, 8),
                    )
                )

        return [
            # ── Invite Workers ──────────────────────────────────
            section_title("Manage Workers", ft.Icons.PEOPLE_OUTLINE),
            glass_card(
                ft.Column([
                    ft.Text("Generate a 6-digit invitation code for a new worker.",
                            size=13, color=theme.TEXT_DIM),
                    ft.Container(height=4),
                    primary_button("Generate Worker Code", ft.Icons.PERSON_ADD_OUTLINED,
                                   self._generate_worker_invitation, bgcolor=theme.ACCENT, width=float("inf")),
                    ft.Container(height=8),
                    ft.Text("Invite a co-owner (max 2 owners per business).",
                            size=13, color=theme.TEXT_DIM),
                    primary_button("Generate Co-Owner Code", ft.Icons.STAR_OUTLINE,
                                   self._generate_owner_invitation, bgcolor=theme.GOLD, width=float("inf")),
                    ft.Container(height=8),
                    self.invitation_code_display,
                    self.invitation_expiry_display,
                    ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE else theme.LIGHT_SURFACE_BORDER),
                    ft.Text("All Invitations", size=12, weight=ft.FontWeight.W_600, color=theme.text_secondary()),
                    self.invitations_list,
                ], spacing=8),
                padding=16, accent=theme.ACCENT,
            ),

            # ── Price Settings ──────────────────────────────────
            section_title("Price Settings", ft.Icons.SETTINGS_OUTLINED),
            glass_card(
                ft.Column([
                    ft.Text("Adjust prices, bottle fees, and costs.", size=13, color=theme.TEXT_DIM),
                    ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE else theme.LIGHT_SURFACE_BORDER),
                    ft.Column(rows, spacing=10),
                ], spacing=10),
                padding=16, accent=theme.ACCENT,
            ),

            # ── Stock Dashboard ────────────────────────────────
            section_title("Stock Dashboard", ft.Icons.INVENTORY_2_OUTLINED),
            glass_card(
                ft.Column([
                    ft.Text("Add stock to a product (creates a new FIFO batch).", size=13, color=theme.TEXT_DIM),
                    ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE else theme.LIGHT_SURFACE_BORDER),
                    self.stock_product_dd,
                    ft.Row([self.stock_qty_field, self.stock_price_field], spacing=10),
                    primary_button("Add Stock", ft.Icons.ADD_CIRCLE_OUTLINE, self._handle_restock,
                                   bgcolor=theme.GOLD, width=float("inf")),
                ], spacing=12),
                padding=16, accent=theme.ACCENT,
            ),

            # ── FIFO Batches ───────────────────────────────────
            section_title("FIFO Batches", ft.Icons.LAYERS_OUTLINED),
            glass_card(
                ft.Column(batch_rows, spacing=8) if batch_rows
                else ft.Column([ft.Text("No batches recorded yet.", color=theme.TEXT_DIM)]),
                padding=16, accent=theme.GOLD,
            ),
        ]