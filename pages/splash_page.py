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
    NAVY_DEEP = "#081B33"

    # ---- The mark: an abstract compass/navigation glyph built entirely from
    # primitives (no image assets) — a gradient ring, a rotated "needle"
    # diamond, and a pivot point. Reads as identity, not a literal icon. ----

    glow_ring = ft.Container(
        width=112, height=112, border_radius=56,
        bgcolor=ft.Colors.with_opacity(0.28, theme.ACCENT),
        opacity=0.0, scale=0.75,
        animate_opacity=ft.Animation(900, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(900, ft.AnimationCurve.EASE_OUT),
    )

    needle = ft.Container(
        width=40, height=40, border_radius=6,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
            colors=[ft.Colors.WHITE, theme.ACCENT],
        ),
        rotate=0.785398,  # 45 degrees, in radians
        left=28, top=28,
    )
    pivot_dot = ft.Container(
        width=10, height=10, border_radius=5, bgcolor=NAVY_BG,
        border=ft.Border.all(2, ft.Colors.with_opacity(0.6, ft.Colors.WHITE)),
        left=43, top=43,
    )

    mark_core = ft.Container(
        width=96, height=96, border_radius=48, bgcolor=NAVY_BG,
        content=ft.Stack([needle, pivot_dot], width=96, height=96),
    )

    mark_ring = ft.Container(
        width=112, height=112, border_radius=56,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, "#123A6B"],
        ),
        shadow=ft.BoxShadow(blur_radius=28, color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                             offset=ft.Offset(0, 10)),
        alignment=ft.Alignment.CENTER,
        content=mark_core,
    )

    logo_wrap = ft.Container(
        content=ft.Stack([glow_ring, mark_ring], width=112, height=112),
        opacity=0.0, scale=0.85,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
    )

    title_text = ft.Text("WaterPilot", size=30, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE)
    tagline_text = ft.Text("Navigate Your Water Business", size=13, color=theme.TEXT_DIM)

    wordmark_wrap = ft.Container(
        content=ft.Column([title_text, tagline_text], spacing=4,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        opacity=0.0,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
    )

    status_text = ft.Text("", size=12, color=theme.TEXT_DIM, visible=False,
                           text_align=ft.TextAlign.CENTER)
    loading_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=theme.ACCENT)
    loading_wrap = ft.Container(
        content=ft.Column([loading_ring, status_text], spacing=10,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        opacity=0.0,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
    )

    content_column = ft.Column(
        [
            logo_wrap,
            ft.Container(height=20),
            wordmark_wrap,
            ft.Container(height=32),
            loading_wrap,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
            colors=[NAVY_BG, NAVY_DEEP],
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        opacity=0,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
    )

    # Status messages shown while the real session check runs alongside them.
    # The check itself happens exactly once, during the first message.
    STATUS_MESSAGES = [
        "Checking secure session...",
        "Loading business workspace...",
        "Preparing dashboard...",
        "Almost ready...",
    ]

    async def _advance():
        # Stage 1: page fade-in, then the mark settles in with a soft
        # scale + a single glow ripple (no looping/bouncing motion).
        await asyncio.sleep(0.05)
        root.opacity = 1
        page.update()

        await asyncio.sleep(0.15)
        logo_wrap.opacity = 1
        logo_wrap.scale = 1.0
        page.update()

        await asyncio.sleep(0.3)
        glow_ring.opacity = 0.0
        glow_ring.scale = 1.55
        page.update()

        # Stage 2: wordmark, then the loading state fade in.
        await asyncio.sleep(0.25)
        wordmark_wrap.opacity = 1
        page.update()

        await asyncio.sleep(0.3)
        loading_wrap.opacity = 1
        page.update()

        # Stage 3: rotate through status messages. The real session check
        # runs once, during the first message — the authentication logic
        # itself is unchanged, only the surrounding presentation is new.
        user = None
        for i, message in enumerate(STATUS_MESSAGES):
            status_text.value = message
            status_text.visible = True
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
            await asyncio.sleep(0.4)
            on_authenticated(user)
            return

        on_unauthenticated()

    page.run_task(_advance)

    return root