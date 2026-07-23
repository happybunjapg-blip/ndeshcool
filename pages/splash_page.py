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
                 delay_seconds: float = 1.5) -> ft.Container:
    """A branded splash screen that checks for an existing session.
    
    Args:
        services: Application services (for session check).
        on_authenticated: Callback with User if session is valid.
        on_unauthenticated: Callback if no session exists.
    """
    NAVY_BG = "#0B2545"

    status_text = ft.Text("", size=11, color=theme.TEXT_DIM, visible=False)

    logo_badge = ft.Container(
        content=ft.Text("WP", size=36, weight=ft.FontWeight.BOLD, color=NAVY_BG),
        width=112, height=112,
        border_radius=56,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK), offset=ft.Offset(0, 8)),
    )

    content_column = ft.Column(
        [
            logo_badge,
            ft.Container(height=8),
            ft.Text("WaterPilot", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("Navigate Your Water Business", size=13, color=theme.TEXT_DIM),
            ft.Container(height=24),
            ft.ProgressRing(width=20, height=20, stroke_width=2.5, color=theme.ACCENT),
            status_text,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )

    footer_text = ft.Text("Powered by ArcNova", size=11, color=theme.TEXT_DIM)

    root = ft.Container(
        content=ft.Stack(
            [
                ft.Container(content=content_column, alignment=ft.Alignment.CENTER, expand=True),
                ft.Container(content=footer_text, alignment=ft.Alignment.CENTER, bottom=24, left=0, right=0),
            ],
            expand=True,
        ),
        bgcolor=NAVY_BG,
        alignment=ft.Alignment.CENTER,
        expand=True,
        opacity=0,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
    )

    async def _advance():
        # Trigger fade-in shortly after mount.
        await asyncio.sleep(0.05)
        root.opacity = 1
        page.update()

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

    return root