import flet as ft
import theme
from widgets import glass_card, section_title, show_snack
from services import Services


class PartnerSettingsPage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate

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

    def build(self) -> list:
        products = self.services.inventory.all_products()

        header = ft.Row([
            ft.Text("Product", width=100, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600),
            ft.Text("Price", width=80, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text("Bottle", width=80, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text("Cost", width=80, size=11, color=theme.TEXT_DIM, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        rows = [header]
        for item in products:
            rows.append(
                ft.Row([
                    ft.Text(item.name, width=100, weight=ft.FontWeight.W_600, size=12, color=theme.text_primary()),
                    ft.TextField(value=str(item.selling_price), width=80, border_radius=10,
                                 content_padding=ft.Padding(8, 8, 8, 8), text_align=ft.TextAlign.CENTER,
                                 on_change=lambda e, n=item.name: self._update_price(n, "selling_price", e.control.value)),
                    ft.TextField(value=str(item.bottle_price), width=80, border_radius=10,
                                 content_padding=ft.Padding(8, 8, 8, 8), text_align=ft.TextAlign.CENTER,
                                 on_change=lambda e, n=item.name: self._update_price(n, "bottle_price", e.control.value)),
                    ft.TextField(value=str(item.cost), width=80, border_radius=10,
                                 content_padding=ft.Padding(8, 8, 8, 8), text_align=ft.TextAlign.CENTER,
                                 on_change=lambda e, n=item.name: self._update_price(n, "cost", e.control.value)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        batch_rows = []
        for item in products:
            if item.batches:
                latest = item.batches[-1]
                batch_rows.append(
                    ft.Row([
                        ft.Text(item.name, width=100, size=12, color=theme.text_primary()),
                        ft.Text(f"{len(item.batches)} batches", size=12, color=theme.TEXT_DIM),
                        ft.Text(f"Latest: {latest.qty:g} @ KES {latest.purchase_price}", size=12, color=theme.GOLD),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

        return [
            section_title("Price Settings", ft.Icons.SETTINGS_OUTLINED),
            glass_card(
                ft.Column([
                    ft.Text("Adjust prices, bottle fees, and costs.", size=13, color=theme.TEXT_DIM),
                    ft.Divider(height=1, color=theme.SURFACE_BORDER),
                    ft.Column(rows, spacing=10),
                ], spacing=10),
                padding=16, accent=theme.ACCENT,
            ),
            section_title("FIFO Batches", ft.Icons.LAYERS_OUTLINED),
            glass_card(
                ft.Column(batch_rows, spacing=8) if batch_rows else ft.Column([ft.Text("No batches", color=theme.TEXT_DIM)]),
                padding=16, accent=theme.GOLD,
            ),
        ]
