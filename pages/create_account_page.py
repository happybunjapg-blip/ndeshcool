"""Create Account page — redesigned as a choice screen.

Two options:
1. Start a New Business → full registration form (Business Name, etc.)
2. Join an Existing Business → navigates to QR scanner

No more invitation text field.
No more guessing between worker/owner invitation.
"""
import traceback
import flet as ft
import theme
from widgets import primary_button
from services import Services
from services.auth_service import AuthError


def build_create_account(page: ft.Page, services: Services,
                          on_account_created, on_back_to_login,
                          on_join_business=None) -> ft.Container:
    """Build the create account page as a choice screen.
    
    Args:
        on_account_created: Called with User when owner signs up.
        on_back_to_login: Called when user taps back.
        on_join_business: Called when user selects "Join Existing Business".
                          Passed from app.py to navigate to QR scanner.
    """
    # --- Choice screen state ---
    showing_choice = True  # True = choice screen, False = owner creation form
    showing_form = False
    
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)
    
    # Owner creation fields
    business_name_field = ft.TextField(
        label="Business Name",
        hint_text="e.g. Maji Safi Water Station",
        prefix_icon=ft.Icons.BUSINESS_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
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
    
    def _show_owner_form(e):
        nonlocal showing_choice, showing_form
        showing_choice = False
        showing_form = True
        choice_container.visible = False
        form_container.visible = True
        page.update()
    
    def _show_choice():
        nonlocal showing_choice, showing_form
        showing_choice = True
        showing_form = False
        choice_container.visible = True
        form_container.visible = False
        error_text.visible = False
        page.update()
    
    def _do_owner_signup(e):
        try:
            error_text.visible = False
            loading.visible = True
            page.update()
            
            business_name = (business_name_field.value or "").strip()
            first_name = (first_name_field.value or "").strip()
            last_name = (last_name_field.value or "").strip()
            email = (email_field.value or "").strip()
            password = (password_field.value or "").strip()
            confirm = (confirm_password_field.value or "").strip()
            
            if not business_name:
                error_text.value = "Business name is required."
                error_text.visible = True
                loading.visible = False
                page.update()
                return
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
            
            user = services.auth.sign_up_owner(
                business_name=business_name, first_name=first_name,
                last_name=last_name, email=email, password=password,
            )
            loading.visible = False
            page.update()
            on_account_created(user)
            
        except AuthError as err:
            error_text.value = str(err)
            error_text.color = theme.DANGER
            error_text.visible = True
        except Exception:
            error_text.value = "Something went wrong. Please check your connection."
            error_text.color = theme.DANGER
            error_text.visible = True
            traceback.print_exc()
        
        loading.visible = False
        page.update()
    
    def _handle_join_business(e):
        if on_join_business:
            on_join_business()
    
    # =====================================================================
    # Logo
    # =====================================================================
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=24),
        width=48, height=48, border_radius=14, alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=16, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 4)),
    )
    
    # =====================================================================
    # CHOICE SCREEN (Option A vs Option B)
    # =====================================================================
    choice_card = ft.Container(
        content=ft.Column([
            logo_badge,
            ft.Text("Get Started", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("Choose how you'd like to begin", size=12, color=theme.TEXT_DIM),
            ft.Container(height=16),
            
            # Option A: Start a New Business
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.ADD_BUSINESS, color=ft.Colors.BLACK, size=22),
                            width=44, height=44, border_radius=12,
                            bgcolor=theme.ACCENT, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=theme.TEXT_MID, size=20),
                    ]),
                    ft.Container(height=8),
                    ft.Text("Start a New Business", size=17, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Text("Create a brand new water station", size=12, color=theme.TEXT_DIM),
                ], spacing=4),
                padding=ft.Padding(16, 14, 16, 14),
                border_radius=theme.RADIUS_CARD,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                border=ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=_show_owner_form,
                ink=True,
            ),
            
            ft.Container(height=8),
            
            # Option B: Join an Existing Business
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.QR_CODE_SCANNER, color=ft.Colors.BLACK, size=22),
                            width=44, height=44, border_radius=12,
                            bgcolor=theme.GOLD, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=theme.TEXT_MID, size=20),
                    ]),
                    ft.Container(height=8),
                    ft.Text("Join an Existing Business", size=17, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Text("Join a business that has invited you", size=12, color=theme.TEXT_DIM),
                ], spacing=4),
                padding=ft.Padding(16, 14, 16, 14),
                border_radius=theme.RADIUS_CARD,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                border=ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=_handle_join_business,
                ink=True,
            ),
            
            ft.Container(height=20),
            
            # Sign in link
            ft.Row([
                ft.Text("Already have an account?", size=12, color=theme.TEXT_DIM),
                ft.TextButton("Sign In", on_click=lambda e: on_back_to_login(),
                              style=ft.ButtonStyle(color=theme.ACCENT)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=24, border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE), ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )
    
    # =====================================================================
    # OWNER REGISTRATION FORM
    # =====================================================================
    form_card = ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.TextButton("← Back", on_click=lambda e: _show_choice(),
                                  style=ft.ButtonStyle(color=theme.TEXT_MID)),
                ]),
                logo_badge,
                ft.Text("New Business", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Create your water station account", size=12, color=theme.TEXT_DIM),
                ft.Container(height=8),
                business_name_field,
                first_name_field,
                last_name_field,
                email_field,
                password_field,
                confirm_password_field,
                error_text,
                primary_button("Create Business", ft.Icons.ADD_BUSINESS, _do_owner_signup, width=float("inf")),
                ft.Container(content=loading, alignment=ft.Alignment.CENTER),
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
        visible=False,
    )
    
    # =====================================================================
    # MAIN CONTAINER: shows choice or form
    # =====================================================================
    choice_container = ft.Container(content=choice_card, alignment=ft.Alignment.CENTER, padding=20, expand=True)
    form_container = ft.Container(content=form_card, alignment=ft.Alignment.CENTER, padding=20, expand=True)
    
    return ft.Stack([
        choice_container,
        form_container,
    ], expand=True)