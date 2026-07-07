"""Visual theme. All colors and Flet-specific styling constants live here so
pages/widgets never hardcode a hex value or opacity themselves.
"""
import flet as ft

BG_TOP = "#0A1120"
BG_BOTTOM = "#0F1E33"

SURFACE = ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
SURFACE_BORDER = ft.Colors.with_opacity(0.09, ft.Colors.WHITE)

ACCENT = ft.Colors.CYAN_400
ACCENT_SOFT = ft.Colors.with_opacity(0.14, ft.Colors.CYAN_400)
GOLD = ft.Colors.AMBER_400
GOLD_SOFT = ft.Colors.with_opacity(0.16, ft.Colors.AMBER_400)
SUCCESS = ft.Colors.GREEN_400
DANGER = ft.Colors.RED_400
WARNING = ft.Colors.ORANGE_400

TEXT_DIM = ft.Colors.with_opacity(0.55, ft.Colors.WHITE)
TEXT_MID = ft.Colors.with_opacity(0.75, ft.Colors.WHITE)

RADIUS_CARD = 22
RADIUS_INPUT = 14
RADIUS_PILL = 24

TIMELINE_STYLE = {
    "restock": (ft.Icons.ADD_BOX_OUTLINED, SUCCESS),
    "sale": (ft.Icons.SHOPPING_CART_CHECKOUT, ACCENT),
    "payment": (ft.Icons.PAYMENTS_OUTLINED, SUCCESS),
    "delivery": (ft.Icons.LOCAL_SHIPPING_OUTLINED, ACCENT),
    "expense": (ft.Icons.RECEIPT_LONG_OUTLINED, WARNING),
    "warning": (ft.Icons.WARNING_AMBER_ROUNDED, WARNING),
}
DEFAULT_TIMELINE_STYLE = (ft.Icons.CIRCLE_OUTLINED, ft.Colors.GREY)


def background_gradient(dark_mode: bool) -> ft.LinearGradient:
    if dark_mode:
        colors = [BG_TOP, BG_BOTTOM]
    else:
        colors = [ft.Colors.GREY_100, ft.Colors.WHITE]
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=colors,
    )
