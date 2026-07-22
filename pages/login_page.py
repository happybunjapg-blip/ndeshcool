"""Professional login page with Supabase Auth.

No demo accounts. Only email + password + remember me + forgot password.
"""
import flet as ft
import theme
from widgets import primary_button, show_snack
from services import Services
from services.auth_service import AuthError


def build_login(page: ft.Page, services: Services, on_login_success,
                on_create_account, on_forgot_password) -> ft.Container:
    """Build the sign-in page.
    
    Args:
        on_login_success: Called with the authenticated User on success.
        on_create_account: Called when user taps "Create Account".
        on_forgot_password: Called when user taps "Forgot Password".
    """
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)

    email_field = ft.TextField(
        label="Email",
        hint_text="Enter your email address",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
        keyboard_type=ft.KeyboardType.EMAIL,
        autofocus=True,
    )
    password_field = ft.TextField(
        label="Password",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True,
        can_reveal_password=True,
        border_radius=theme.RADIUS_INPUT,
    )
    remember_me = ft.Checkbox(label="Remember me", value=True, active_color=theme.ACCENT)

    def _do_login(e):
        email = (email_field.value or "").strip()
        password = (password_field.value or "").strip()

        if not email or not password:
            error_text.value = "Please enter your email and password."
            error_text.visible = True
            loading.visible = False
            page.update()
            return

        error_text.visible = False
        loading.visible = True
        page.update()

        try:
            user = services.auth.authenticate(email, password, remember_me=remember_me.value)
            loading.visible = False
            page.update()
            if user:
                on_login_success(user)
                return
        except AuthError as err:
            error_text.value = str(err)
            error_text.visible = True
        except Exception:
            error_text.value = "Something went wrong. Please check your connection."
            error_text.visible = True
        
        loading.visible = False
        page.update()

    def _handle_forgot_password(e):
        on_forgot_password()

    def _handle_create_account(e):
        on_create_account()

    # Logo
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=30),
        width=64, height=64,
        border_radius=18,
        alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=20, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 6)),
    )

    form_card = ft.Container(
        content=ft.Column(
            [
                logo_badge,
                ft.Text("AquaFlow", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Sign in to manage your water station", size=12, color=theme.TEXT_DIM),
                ft.Container(height=12),
                email_field,
                password_field,
                ft.Row(
                    [
                        remember_me,
                        ft.TextButton(
                            "Forgot password?",
                            on_click=_handle_forgot_password,
                            style=ft.ButtonStyle(color=theme.ACCENT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                error_text,
                primary_button("Sign In", ft.Icons.LOGIN, _do_login, width=float("inf")),
                ft.Container(content=loading, alignment=ft.Alignment.CENTER),
                ft.Container(height=8),
                ft.Row(
                    [
                        ft.Text("Don't have an account?", size=12, color=theme.TEXT_DIM),
                        ft.TextButton(
                            "Create one",
                            on_click=_handle_create_account,
                            style=ft.ButtonStyle(color=theme.ACCENT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
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