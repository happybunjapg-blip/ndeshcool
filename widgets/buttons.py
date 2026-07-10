import flet as ft
import theme


def pill_style(bgcolor, fgcolor=None) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        bgcolor=bgcolor,
        color=fgcolor or (ft.Colors.BLACK if theme.DARK_MODE else ft.Colors.WHITE),
        shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_INPUT),
        padding=ft.Padding(20, 16, 20, 16),
        elevation=0,
    )


def primary_button(text, icon, on_click, bgcolor=None, width=None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text,
        icon=icon,
        on_click=on_click,
        style=pill_style(bgcolor or theme.ACCENT),
        width=width,
    )