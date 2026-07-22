"""Forgot Password page.

Sends a password reset email via Supabase Auth.
"""
import flet as ft
import theme
from widgets import primary_button
from services import Services
from services.auth_service import AuthError


def build_forgot_password(page: ft.Page, services: Services,
                           on_back_to_login, on_reset_sent) -> ft.Container:
    """Build the forgot password page.
    
    Args:
        on_back_to_login: Called when user taps "Back to Sign In".
        on_reset_sent: Called after reset email is sent.
    """
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    success_text = ft.Text("", size=12, color=theme.SUCCESS, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)

    email_field = ft.TextField(
        label="Email",
        hint_text="Enter your registered email",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
        keyboard_type=ft.KeyboardType.EMAIL,
        autofocus=True,
    )

    def _send_reset(e):
        email = (email_field.value or "").strip()
        error_text.visible = False
        success_text.visible = False

        if not email:
            error_text.value = "Please enter your email address."
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        page.update()

        try:
            sent = services.auth.forgot_password(email)
            loading.visible = False
            if sent:
                success_text.value = (
                    "Password reset link sent!\n\n"
                    "Check your email inbox and follow the instructions to reset your password."
                )
                success_text.visible = True
                email_field.value = ""
                page.update()
            else:
                error_text.value = "Could not send reset email. Please try again."
                error_text.visible = True
                page.update()
        except AuthError as err:
            loading.visible = False
            error_text.value = str(err)
            error_text.visible = True
            page.update()

    # Logo
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=24),
        width=48, height=48,
        border_radius=14,
        alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=16, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 4)),
    )

    form_card = ft.Container(
        content=ft.Column(
            [
                logo_badge,
                ft.Text("Reset Password", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(
                    "Enter your email and we'll send you a password reset link.",
                    size=12, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=12),
                email_field,
                error_text,
                success_text,
                ft.Stack(
                    [
                        primary_button("Send Reset Link", ft.Icons.SEND, _send_reset, width=float("inf")),
                        ft.Container(
                            content=loading,
                            alignment=ft.Alignment.CENTER,
                            expand=True,
                        ),
                    ],
                    height=48,
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_BACK, size=14, color=theme.ACCENT),
                        ft.TextButton(
                            "Back to Sign In",
                            on_click=lambda e: on_back_to_login(),
                            style=ft.ButtonStyle(color=theme.ACCENT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24,
        border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE), ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )

    return ft.Container(
        content=form_card,
        alignment=ft.Alignment.CENTER,
        padding=20,
        expand=True,
    )