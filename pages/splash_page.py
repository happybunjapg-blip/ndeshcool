import asyncio
import flet as ft
import theme


def build_splash(page: ft.Page, on_finish, delay_seconds: float = 1.4) -> ft.Container:
    """A simple branded splash screen. Auto-advances to the login screen
    after `delay_seconds`. Kept dumb on purpose -- no auth logic here."""
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=44),
        width=96, height=96,
        border_radius=28,
        alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=30, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 8)),
    )

    content = ft.Column(
        [
            logo_badge,
            ft.Text("AquaFlow", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("Water Station Ops", size=13, color=theme.TEXT_DIM),
            ft.Container(height=24),
            ft.ProgressRing(width=22, height=22, stroke_width=2.5, color=theme.ACCENT),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )

    async def _advance():
        await asyncio.sleep(delay_seconds)
        on_finish()

    page.run_task(_advance)

    return ft.Container(
        content=content,
        alignment=ft.Alignment.CENTER,
        expand=True,
    )
