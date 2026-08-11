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
from widgets.branding import (
    waterpilot_mark,
    waterpilot_wordmark,
    waterpilot_tagline,
    waterpilot_loader,
    waterpilot_footer,
)


def build_splash(page: ft.Page, services: Services, on_authenticated, on_unauthenticated,
                 delay_seconds: float = 1.5,
                 check_deep_link=None, on_deep_link_found=None) -> ft.Container:
    """A branded splash screen that checks for an existing session.

    Args:
        services: Application services (for session check).
        on_authenticated: Callback with User if session is valid.
        on_unauthenticated: Callback if no session exists.
        check_deep_link: Optional callable that returns qr_data dict or None.
        on_deep_link_found: Optional callable(qr_data) if deep link detected.
    """

    logo = waterpilot_mark(size=168, color=theme.PRIMARY)
    logo.opacity = 0.0
    logo.animate_opacity = ft.Animation(theme.ANIM_DURATION_SLOW, theme.ANIMATION_CURVE)

    title_text = waterpilot_wordmark(size=38)
    title_text.opacity = 0.0
    title_text.animate_opacity = ft.Animation(theme.ANIM_DURATION_MEDIUM, theme.ANIMATION_CURVE)

    tagline_text = waterpilot_tagline("Smart water business software for modern operators")
    tagline_text.opacity = 0.0
    tagline_text.animate_opacity = ft.Animation(theme.ANIM_DURATION_MEDIUM, theme.ANIMATION_CURVE)

    loader_row, loader_dots = waterpilot_loader(dot_count=3, dot_size=10, spacing=12)
    loader_wrap = ft.Container(
        content=loader_row,
        opacity=0.0,
        animate_opacity=ft.Animation(theme.ANIM_DURATION_MEDIUM, theme.ANIMATION_CURVE),
    )

    status_text = ft.Text(
        "",
        style=ft.TextStyle(size=12, weight=ft.FontWeight.W_400, height=1.4),
        color=theme.text_dim(),
        visible=False,
        text_align=ft.TextAlign.CENTER,
    )
    status_wrap = ft.Container(
        content=status_text,
        padding=ft.Padding(0, 16, 0, 0),
    )

    footer = waterpilot_footer("Powered by ArcNova")

    content_column = ft.Column(
        [
            logo,
            ft.Container(height=28),
            title_text,
            ft.Container(height=16),
            tagline_text,
            ft.Container(height=42),
            loader_wrap,
            status_wrap,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=False,
    )

    root = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=140),
                content_column,
                ft.Container(expand=True),
                ft.Container(content=footer, alignment=ft.Alignment.CENTER, padding=ft.Padding(0, 18, 0, 0)),
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        bgcolor=theme.splash_background(),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    STATUS_MESSAGES = [
        "Checking secure session...",
        "Loading business workspace...",
        "Preparing your dashboard...",
        "Almost ready...",
    ]

    async def _pulse_loader_dots():
        while True:
            for dot in loader_dots:
                dot.opacity = 0.95
                page.update()
                await asyncio.sleep(0.14)
                dot.opacity = 0.32
                page.update()
                await asyncio.sleep(0.14)
            await asyncio.sleep(0.30)

    async def _advance():
        await asyncio.sleep(1.5)

        logo.opacity = 1.0
        page.update()
        await asyncio.sleep(0.8)

        await asyncio.sleep(0.6)
        title_text.opacity = 1.0
        page.update()
        await asyncio.sleep(0.5)

        tagline_text.opacity = 1.0
        page.update()
        await asyncio.sleep(0.5)

        loader_wrap.opacity = 1.0
        status_text.visible = True
        status_text.value = "Starting workspace..."
        page.update()
        page.run_task(_pulse_loader_dots)

        if check_deep_link is not None:
            for _ in range(5):
                qr_data = check_deep_link()
                if qr_data is not None:
                    status_text.value = "Invitation detected. Redirecting..."
                    page.update()
                    await asyncio.sleep(0.5)
                    if on_deep_link_found:
                        on_deep_link_found(qr_data)
                    return
                await asyncio.sleep(0.3)

        user = None
        for i, message in enumerate(STATUS_MESSAGES):
            status_text.value = message
            page.update()
            if i == 0:
                try:
                    user = services.auth.get_saved_session()
                except Exception:
                    user = None
            await asyncio.sleep(delay_seconds)

        if user:
            status_text.value = f"Welcome back, {user.first_name}"
            page.update()
            await asyncio.sleep(0.6)
            on_authenticated(user)
            return

        on_unauthenticated()

    page.run_task(_advance)
    return root