"""Registration form displayed after a successful QR scan.

The QR code contains ONLY the invitation code.
The database invitation record determines:
- business_id (which business to join)
- role (worker or co_owner)

The client NEVER determines role or business_id from QR parameters.
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
        qr_data: Decoded QR payload — ONLY 'code' is used.
        on_account_created: Called with User on success.
        on_back_to_scanner: Called when user wants to re-scan.
    """
    code = (qr_data.get("code") or "").strip()
    
    # State for invitation lookup
    invitation_info = {}
    lookup_done = False
    lookup_error = ""
    
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)
    
    # Invitation info display (shown after successful DB lookup)
    business_name_text = ft.Text("", size=14, color=theme.text_primary(), weight=ft.FontWeight.W_600)
    role_text = ft.Text("", size=13, color=theme.ACCENT, weight=ft.FontWeight.W_500)
    invitation_status = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=theme.SUCCESS, size=18),
                ft.Text("Invitation code detected", size=13, color=theme.SUCCESS),
            ], spacing=6),
            ft.Container(height=4),
            business_name_text,
            role_text,
        ], spacing=2),
        padding=ft.Padding(12, 8, 12, 8),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.1, theme.SUCCESS),
        visible=False,
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
    
    def _do_lookup():
        """Look up the invitation from the database."""
        nonlocal lookup_done, lookup_error, invitation_info
        if lookup_done or not code:
            return
        
        try:
            result = services.auth.lookup_invitation(code)
            invitation_info = result
            lookup_done = True
            lookup_error = ""
            
            # Update UI with invitation details from database
            business_name = result.get("business_name", "the business")
            role = result.get("role", "worker")
            role_label = "Co-owner" if role == "co_owner" else "Worker"
            
            business_name_text.value = f"Business: {business_name}"
            role_text.value = f"Joining as: {role_label}"
            invitation_status.visible = True
            page.update()
            
        except AuthError as err:
            lookup_error = str(err)
            lookup_done = True
            error_text.value = str(err)
            error_text.visible = True
            page.update()
        except Exception as err:
            lookup_error = "Could not verify invitation. Please check your connection."
            lookup_done = True
            error_text.value = lookup_error
            error_text.visible = True
            page.update()
    
    def _do_signup(e):
        nonlocal invitation_info
        print(f"[JOIN_DEBUG] _do_signup called")
        try:
            error_text.visible = False
            loading.visible = True
            page.update()
            
            first_name = (first_name_field.value or "").strip()
            last_name = (last_name_field.value or "").strip()
            email = (email_field.value or "").strip()
            password = (password_field.value or "").strip()
            confirm = (confirm_password_field.value or "").strip()
            
            print(f"[JOIN_DEBUG] fields: first_name={first_name!r}, last_name={last_name!r}, email={email!r}")
            
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
            
            # Use the canonical join method
            # The database determines role and business_id — NOT the client
            print(f"[JOIN_DEBUG] calling join_business_with_invitation with code={code!r}")
            user = services.auth.join_business_with_invitation(
                code=code,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )
            loading.visible = False
            page.update()
            on_account_created(user)
            
        except AuthError as err:
            print(f"[JOIN_DEBUG] AuthError caught: {err}")
            error_text.value = str(err)
            error_text.color = theme.DANGER
            error_text.visible = True
        except Exception as err:
            print(f"[JOIN_DEBUG] Exception caught: {err}")
            error_text.value = "Something went wrong. Please check your connection."
            error_text.color = theme.DANGER
            error_text.visible = True
            traceback.print_exc()
        
        loading.visible = False
        page.update()
    
    # Perform the invitation lookup immediately
    _do_lookup()
    
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
                invitation_status,
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