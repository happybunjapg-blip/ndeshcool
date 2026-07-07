import flet as ft
import theme
from widgets import primary_button
from services import Services


def build_login(page: ft.Page, services: Services, on_login_success) -> ft.Container:
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)

    email_field = ft.TextField(
        label="Email",
        hint_text="partner@example.com or worker@example.com",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
        keyboard_type=ft.KeyboardType.EMAIL,
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
        error_text.visible = False
        user = services.auth.authenticate(email_field.value, password_field.value)
        if not user:
            error_text.value = "Invalid email or password. Try partner@example.com / worker@example.com."
            error_text.visible = True
            page.update()
            return
        on_login_success(user)

    def _forgot_password(e):
        error_text.value = "Password reset isn't available yet in this preview build."
        error_text.color = theme.WARNING
        error_text.visible = True
        page.update()

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
                            on_click=_forgot_password,
                            style=ft.ButtonStyle(color=theme.ACCENT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                error_text,
                primary_button("Sign In", ft.Icons.LOGIN, _do_login, width=float("inf")),
                ft.Container(height=4),
                ft.Text(
                    "Demo accounts: partner@example.com / worker@example.com (any password)",
                    size=11, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
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
        width=360,
    )

    return ft.Container(
        content=form_card,
        alignment=ft.Alignment.CENTER,
        padding=20,
        expand=True,
    )
