import flet as ft
import theme
from widgets import glass_card, primary_button, show_snack
from services import Services, BusinessDayError


def build_business_day_gate(page: ft.Page, services: Services, user, on_opened) -> ft.Container:
    """Workers land here instead of Home whenever no Business Day is open.
    Nothing else in the worker app is reachable until they open one --
    the nav/shell itself isn't even built yet at this point (see app.py)."""
    note_field = ft.TextField(
        label="Opening note (optional)", hint_text="e.g. starting float KES 2,000",
        multiline=True, min_lines=2, border_radius=theme.RADIUS_INPUT,
    )

    def _open(e):
        try:
            services.business_day.open_day(user.email, note_field.value or "")
        except BusinessDayError as err:
            show_snack(page, str(err), theme.DANGER)
            return
        on_opened()

    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=30),
        width=64, height=64, border_radius=18, alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                    colors=[theme.ACCENT, ft.Colors.BLUE_400]),
        shadow=ft.BoxShadow(blur_radius=20, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 6)),
    )

    card = glass_card(
        ft.Column(
            [
                logo_badge,
                ft.Text("No Business Day is open", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(
                    "Sales, deliveries, and expenses can't be recorded until the day is opened.",
                    size=12, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                note_field,
                primary_button("Open Business Day", ft.Icons.LOCK_OPEN, _open, width=float("inf")),
            ],
            spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24, accent=theme.ACCENT,
    )

    return ft.Container(content=card, alignment=ft.Alignment.CENTER, padding=20, expand=True)
