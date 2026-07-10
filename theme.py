"""Visual theme. All colors and Flet-specific styling constants live here so
pages/widgets never hardcode a hex value or opacity themselves.

Dark mode is the default. When DARK_MODE is toggled to False, all
mode-aware widgets automatically use the LIGHT_* palette instead.
"""
import flet as ft

# =====================================================================
# GLOBAL MODE (set by app.py when the user toggles theme)
# =====================================================================
DARK_MODE = True

# =====================================================================
# DARK MODE COLORS (original, unchanged)
# =====================================================================
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

# =====================================================================
# LIGHT MODE COLORS (professional, high-contrast, daylight-readable)
# =====================================================================
LIGHT_BG_TOP = "#F0F4F8"
LIGHT_BG_BOTTOM = "#FFFFFF"

LIGHT_SURFACE = "#FFFFFF"
LIGHT_SURFACE_BORDER = "#E2E8F0"
LIGHT_CARD_SHADOW = ft.Colors.with_opacity(0.08, ft.Colors.BLACK)
LIGHT_CARD_SHADOW_ELEVATED = ft.Colors.with_opacity(0.12, ft.Colors.BLACK)

# Text — dark navy for maximum contrast on white
LIGHT_TEXT_PRIMARY = "#1A202C"
LIGHT_TEXT_SECONDARY = "#4A5568"
LIGHT_TEXT_DIM = "#8E99A4"

# Header — solid white with a soft bottom border
LIGHT_HEADER_BG = "#FFFFFF"

# =====================================================================
# MODE-AWARE HELPERS (used by widgets when DARK_MODE flag changes)
# =====================================================================

def text_primary() -> str:
    """Primary text color (headings, values)."""
    return LIGHT_TEXT_PRIMARY if not DARK_MODE else "#FFFFFF"


def text_secondary() -> str:
    """Secondary / body text color."""
    return LIGHT_TEXT_SECONDARY if not DARK_MODE else TEXT_MID


def text_dim() -> str:
    """Muted / auxiliary text color."""
    return LIGHT_TEXT_DIM if not DARK_MODE else TEXT_DIM


def card_border() -> str:
    """Card border color."""
    return LIGHT_SURFACE_BORDER if not DARK_MODE else SURFACE_BORDER


def card_bg() -> ft.LinearGradient | str:
    """Card background — gradient in dark mode, solid white in light mode."""
    if not DARK_MODE:
        return LIGHT_SURFACE
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=[
            ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
            ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
        ],
    )


def card_shadow() -> ft.BoxShadow:
    """Subtle drop shadow for cards."""
    if not DARK_MODE:
        return ft.BoxShadow(
            blur_radius=16,
            color=LIGHT_CARD_SHADOW,
            offset=ft.Offset(0, 2),
        )
    return ft.BoxShadow(
        blur_radius=20,
        color=ft.Colors.with_opacity(0.28, ft.Colors.BLACK),
        offset=ft.Offset(0, 6),
    )


def header_bg() -> str | None:
    """Header background color."""
    return LIGHT_HEADER_BG if not DARK_MODE else None


# =====================================================================
# RADII
# =====================================================================
RADIUS_CARD = 22
RADIUS_INPUT = 14
RADIUS_PILL = 24

# =====================================================================
# SPACING SCALE
# =====================================================================
SPACING_XXS = 4
SPACING_XS = 8
SPACING_SM = 12
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

# =====================================================================
# TIMELINE
# =====================================================================
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
        colors = [LIGHT_BG_TOP, LIGHT_BG_BOTTOM]
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=colors,
    )