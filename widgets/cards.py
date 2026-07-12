from typing import Optional, Tuple
import flet as ft
import theme


def glass_card(content, padding=16, margin=0, accent=None) -> ft.Container:
    """Mode-aware card — solid white in light mode, glass gradient in dark mode.

    By default each card gets a bottom margin (``CARD_MARGIN_BOTTOM``) to
    create comfortable vertical breathing room on mobile.  Pass an explicit
    ``margin`` value to override.
    """
    if margin == 0:
        margin = ft.Margin(0, 0, 0, theme.CARD_MARGIN_BOTTOM)
    return ft.Container(
        content=content,
        padding=padding,
        margin=margin,
        border_radius=14,
        bgcolor=None if theme.DARK_MODE else theme.LIGHT_SURFACE,
        gradient=theme.card_bg() if theme.DARK_MODE else None,
        border=ft.Border.all(
            1,
            ft.Colors.with_opacity(0.14, accent) if accent
            else (theme.LIGHT_SURFACE_BORDER if not theme.DARK_MODE else theme.SURFACE_BORDER),
        ),
        shadow=theme.card_shadow(),
    )


def section_title(text: str, icon=None) -> ft.Row:
    controls = [ft.Container(width=4, height=18, border_radius=2, bgcolor=theme.ACCENT)]
    if icon:
        controls.append(ft.Icon(icon, size=18, color=theme.ACCENT))
    controls.append(
        ft.Text(
            text, size=16, weight=ft.FontWeight.W_700,
            color=theme.text_primary(),
        )
    )
    return ft.Row(controls, spacing=8)


def kpi_card(title, value, icon, color, trend: Optional[str] = None, live=False) -> ft.Container:
    icon_badge = ft.Container(
        content=ft.Icon(icon, color=color, size=18),
        width=34, height=34,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.14, color),
        alignment=ft.Alignment.CENTER,
    )
    content = ft.Column([
        ft.Row([
            icon_badge,
            ft.Row([
                ft.Container(width=7, height=7, border_radius=4, bgcolor=theme.SUCCESS),
                ft.Text("live", size=9, color=theme.text_dim()),
            ], spacing=4) if live else ft.Container(),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Text(value, size=24, weight=ft.FontWeight.W_800, color=theme.text_primary()),
        ft.Text(title, size=12, color=theme.text_secondary()),
    ], spacing=6)
    if trend:
        trend_color = theme.SUCCESS if trend.startswith("+") else theme.DANGER
        content.controls.append(
            ft.Row([
                ft.Icon(ft.Icons.ARROW_UPWARD if trend.startswith("+") else ft.Icons.ARROW_DOWNWARD,
                        size=13, color=trend_color),
                ft.Text(trend, size=12, weight=ft.FontWeight.W_600, color=trend_color),
                ft.Text("vs prior period", size=10, color=theme.text_dim()),
            ], spacing=3)
        )
    return glass_card(content, padding=12, accent=color)


def _stock_status_color(item) -> Tuple[str, str]:
    label = item.status_label()
    color = {"Out": theme.DANGER, "Low": theme.WARNING, "In": theme.SUCCESS}[label]
    return label, color


def stock_card(item, compact: bool = False) -> ft.Container:
    status_label, status_color = _stock_status_color(item)
    is_cap = "cap" in item.name.lower()
    accent = theme.GOLD if is_cap else status_color
    fill_ratio = max(0.0, min(1.0, item.qty / max(item.threshold * 4, 1)))
    children = [
        ft.Row([
            ft.Text(item.name, size=13, weight=ft.FontWeight.W_600, color=theme.text_primary()),
            ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, size=8, color=theme.GOLD) if is_cap else ft.Container(),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Text(f"{item.qty:g}", size=26, weight=ft.FontWeight.W_800, color=accent),
        ft.ProgressBar(
            value=fill_ratio, color=accent,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            bar_height=5, border_radius=3,
        ),
    ]
    if not compact:
        children.append(
            ft.Container(
                content=ft.Text(status_label, size=10, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK),
                bgcolor=status_color,
                padding=ft.Padding(8, 3, 8, 3),
                border_radius=10,
            )
        )
    else:
        children.append(ft.Text("units", size=10, color=theme.text_dim()))
    return glass_card(ft.Column(children, spacing=6), padding=12, accent=accent)


def customer_card(customer, on_click=None) -> ft.Container:
    balance_color = theme.DANGER if customer.balance > 0 else theme.SUCCESS
    card_content = ft.Row([
        ft.Container(
            content=ft.Text(customer.name[:1].upper(), size=16, weight=ft.FontWeight.W_700, color=ft.Colors.BLACK),
            width=40, height=40, border_radius=20, alignment=ft.Alignment.CENTER,
            bgcolor=theme.ACCENT,
        ),
        ft.Column([
            ft.Text(customer.name, size=14, weight=ft.FontWeight.W_600, color=theme.text_primary()),
            ft.Text(customer.phone or "No phone on file", size=11, color=theme.text_dim()),
        ], spacing=2, expand=True),
        ft.Column([
            ft.Text(f"KES {customer.balance:,.0f}", size=13, weight=ft.FontWeight.W_700, color=balance_color),
            ft.Text("Credit" if customer.is_credit else "Cash", size=10, color=theme.text_secondary()),
        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    card = glass_card(card_content, padding=12, accent=balance_color if customer.balance > 0 else None)
    return card if on_click is None else ft.GestureDetector(on_tap=on_click, content=card)