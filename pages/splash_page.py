"""Splash screen with session check.

On app launch:
1. Show branded splash
2. Check for existing authenticated session
3. If authenticated → go to home
4. If not → go to login
"""
import asyncio
import flet as ft
import theme
from services import Services


def build_splash(page: ft.Page, services: Services, on_authenticated, on_unauthenticated,
                 delay_seconds: float = 1.4) -> ft.Container:
    """A branded splash screen that checks for an existing session.
    
    Args:
        services: Application services (for session check).
        on_authenticated: Callback with User if session is valid.
        on_unauthenticated: Callback if no session exists.
    """
    status_text = ft.Text("", size=11, color=theme.TEXT_DIM, visible=False)

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

    content_column = ft.Column(
        [
            logo_badge,
            ft.Text("AquaFlow", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("Water Station Ops", size=13, color=theme.TEXT_DIM),
            ft.Container(height=24),
            ft.ProgressRing(width=22, height=22, stroke_width=2.5, color=theme.ACCENT),
            status_text,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )

    async def _advance():
        await asyncio.sleep(delay_seconds)

        # Check for existing session
        try:
            user = services.auth.get_saved_session()
            if user:
                status_text.value = f"Welcome back, {user.first_name}"
                status_text.visible = True
                page.update()
                await asyncio.sleep(0.3)
                on_authenticated(user)
                return
        except Exception:
            pass

        on_unauthenticated()

    page.run_task(_advance)

    return ft.Container(
        content=content_column,
        alignment=ft.Alignment.CENTER,
        expand=True,
    )