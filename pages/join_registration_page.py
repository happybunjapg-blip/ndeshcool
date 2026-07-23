"""Registration form displayed after a successful QR scan.

This form does NOT ask for Business Name — the business already exists.
The role (worker/owner) is determined by the QR data, not user input.
"""
import traceback
import flet as ft
import theme
from widgets import primary_button
from services import Services
from services.auth_service import AuthError


def build_join_registration(page: ft.Page, services: Services,
                            qr_data: dict,
                            on_account_created,
                            on_back_to_scanner) -> ft.Container:
    """Build registration form for joining via QR invitation.
    
    Args:
        qr_data: Decoded QR payload with code, type, business_id.
        on_account_created: Called with User on success.
        on_back_to_scanner: Called when user wants to re-scan.
    """
    inv_type = qr_data.get("type", "worker")
    role_label = "Co-owner" if inv_type == "owner" else "Worker"
    
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)
    
    qr_info = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=theme.SUCCESS, size=18),
            ft.Text(f"✓ {role_label} invitation verified", size=13, color=theme.SUCCESS),
        ], spacing=6),
        padding=ft.Padding(12, 8, 12, 8),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.1, theme.SUCCESS),
    )
    
    first_name_field = ft.TextField(
        label="First Name",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=theme.RADIUS_INPUT,
    )
    last_name_field = ft.TextField(
        label="Last Name",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=theme.RADIUS_INPUT,
    )
    email_field = ft.TextField(
        label="Email",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
        keyboard_type=ft.KeyboardType.EMAIL,
    )
    password_field = ft.TextField(
        label="Password",
        hint_text="At least 6 characters",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True, can_reveal_password=True,
        border_radius=theme.RADIUS_INPUT,
    )
    confirm_password_field = ft.TextField(
        label="Confirm Password",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True, can_reveal_password=True,
        border_radius=theme.RADIUS_INPUT,
    )
    
    def _do_signup(e):
        try:
            error_text.visible = False
            loading.visible = True
            page.update()
            
            first_name = (first_name_field.value or "").strip()
            last_name = (last_name_field.value or "").strip()
            email = (email_field.value or "").strip()
            password = (password_field.value or "").strip()
            confirm = (confirm_password_field.value or "").strip()
            
            if not first_name or not last_name:
                error_text.value = "First and last name are required."
                error_text.visible = True
                loading.visible = False
                page.update()
                return
            if not email:
                error_text.value = "Email is required."
                error_text.visible = True
                loading.visible = False
                page.update()
                return
            if not password or len(password) < 6:
                error_text.value = "Password must be at least 6 characters."
                error_text.visible = True
                loading.visible = False
                page.update()
                return
            if password != confirm:
                error_text.value = "Passwords do not match."
                error_text.visible = True
                loading.visible = False
                page.update()
                return
            
            user = services.auth.sign_up_via_qr(
                qr_data=qr_data,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )
            loading.visible = False
            page.update()
            on_account_created(user)
            
        except AuthError as err:
            error_text.value = str(err)
            error_text.color = theme.DANGER
            error_text.visible = True
        except Exception as err:
            error_text.value = "Something went wrong. Please check your connection."
            error_text.color = theme.DANGER
            error_text.visible = True
            traceback.print_exc()
        
        loading.visible = False
        page.update()
    
    # Logo
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=24),
        width=48, height=48, border_radius=14, alignment=ft.Alignment.CENTER,
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
                ft.Text("Join Business", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Create your account to join", size=12, color=theme.TEXT_DIM),
                ft.Container(height=4),
                qr_info,
                ft.Container(height=8),
                first_name_field,
                last_name_field,
                email_field,
                password_field,
                confirm_password_field,
                error_text,
                primary_button("Create Account", ft.Icons.PERSON_ADD, _do_signup, width=float("inf")),
                ft.Container(content=loading, alignment=ft.Alignment.CENTER),
                ft.Container(height=4),
                ft.TextButton(
                    "← Scan a different code",
                    on_click=lambda e: on_back_to_scanner(),
                    style=ft.ButtonStyle(color=theme.TEXT_DIM),
                ),
                ft.Row([
                    ft.Text("Already have an account?", size=12, color=theme.TEXT_DIM),
                    ft.TextButton("Sign In", on_click=lambda e: on_back_to_scanner(),
                                  style=ft.ButtonStyle(color=theme.ACCENT)),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            ],
            spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=24, border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE), ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )
    
    return ft.Container(content=form_card, alignment=ft.Alignment.CENTER, padding=20, expand=True)