import flet as ft
import theme


def pill_style(bgcolor, fgcolor=ft.Colors.BLACK) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        bgcolor=bgcolor,
        color=fgcolor,
        shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_INPUT),
        padding=ft.Padding(18, 14, 18, 14),
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
