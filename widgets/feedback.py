import flet as ft
import theme


def show_snack(page: ft.Page, message: str, color=None):
    color = color or theme.SUCCESS
    page.show_dialog(
        ft.SnackBar(
            content=ft.Row([
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_OUTLINE if color == theme.SUCCESS else
                    ft.Icons.ERROR_OUTLINE if color == theme.DANGER else ft.Icons.INFO_OUTLINE,
                    color=ft.Colors.WHITE, size=18,
                ),
                ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, size=13),
            ], spacing=8),
            bgcolor=color,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=ft.Margin(16, 0, 16, 80),
            shape=ft.RoundedRectangleBorder(radius=16),
            duration=2500,
        )
    )
