"""Create Account page.

Three flows:
1. New business owner — First Name, Last Name, Business Name, Email, Password
2. Worker with invitation code — First Name, Last Name, Email, Password, Code
3. Second owner with owner invitation code — First Name, Last Name, Email, Password, Code
"""
import traceback
import flet as ft
import theme
from widgets import primary_button
from services import Services
from services.auth_service import AuthError


def build_create_account(page: ft.Page, services: Services,
                          on_account_created, on_back_to_login) -> ft.Container:
    """Build the create account page."""
    # State
    has_invitation = False
    invitation_valid = False
    invitation_is_owner = False
    invitation_business_id = None

    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)

    # Fields
    invitation_field = ft.TextField(
        label="Invitation Code",
        hint_text="Enter 6-digit code from your employer",
        prefix_icon=ft.Icons.VPN_KEY_OUTLINED,
        border_radius=theme.RADIUS_INPUT,
        visible=False,
        text_align=ft.TextAlign.CENTER,
        text_style=ft.TextStyle(letter_spacing=6, weight=ft.FontWeight.W_700),
        max_length=6,
    )
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

    # Toggle between owner and invitation-based registration
    def _toggle_registration_type(e):
        nonlocal has_invitation, invitation_valid, invitation_is_owner, invitation_business_id
        has_invitation = not has_invitation
        invitation_valid = False
        invitation_is_owner = False
        invitation_business_id = None
        invitation_field.visible = has_invitation
        business_name_field.visible = not has_invitation
        error_text.visible = False
        invitation_field.value = ""
        if has_invitation:
            toggle_text.value = "Starting a new business? Register as owner"
        else:
            toggle_text.value = "Joining an existing business? Enter invitation code"
        page.update()

    def _validate_invitation(e):
        nonlocal invitation_valid, invitation_is_owner, invitation_business_id
        code = (invitation_field.value or "").strip()
        if len(code) != 6 or not code.isdigit():
            error_text.value = "Enter a valid 6-digit invitation code."
            error_text.color = theme.DANGER
            error_text.visible = True
            page.update()
            return
        try:
            invitation = services.auth.validate_invitation(code)
            invitation_valid = True
            invitation_is_owner = getattr(invitation, 'owner_invite', False)
            invitation_business_id = invitation.business_id
            if invitation_is_owner:
                error_text.value = "✓ Owner invitation code is valid!"
            else:
                error_text.value = "✓ Worker invitation code is valid!"
            error_text.color = theme.SUCCESS
            error_text.visible = True
        except AuthError as err:
            invitation_valid = False
            invitation_is_owner = False
            invitation_business_id = None
            error_text.value = str(err)
            error_text.color = theme.DANGER
            error_text.visible = True
        page.update()

    def _do_signup(e):
        nonlocal has_invitation, invitation_valid, invitation_is_owner, invitation_business_id
        
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

            try:
                if has_invitation:
                    if not invitation_valid:
                        error_text.value = "Please validate your invitation code first."
                        error_text.visible = True
                        loading.visible = False
                        page.update()
                        return
                    code = (invitation_field.value or "").strip()
                    if invitation_is_owner:
                        user = services.auth.sign_up_second_owner(
                            invitation_code=code, first_name=first_name,
                            last_name=last_name, email=email, password=password,
                        )
                    else:
                        user = services.auth.sign_up_worker(
                            invitation_code=code, first_name=first_name,
                            last_name=last_name, email=email, password=password,
                        )
                else:
                    business_name = (business_name_field.value or "").strip()
                    if not business_name:
                        error_text.value = "Business name is required."
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
                return
            except AuthError as err:
                error_text.value = str(err)
                error_text.color = theme.DANGER
                error_text.visible = True
        except Exception as err:
            error_text.value = f"Something went wrong. Please check your connection and try again."
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

    toggle_text = ft.Text(
        "Joining an existing business? Enter invitation code",
        size=12, color=theme.ACCENT,
    )
    toggle_button = ft.TextButton(
        content=toggle_text, on_click=_toggle_registration_type,
        style=ft.ButtonStyle(color=theme.ACCENT),
    )

    validate_button = ft.TextButton(
        "Validate Code", on_click=_validate_invitation,
        style=ft.ButtonStyle(color=theme.ACCENT), visible=False,
    )

    def _on_invitation_focus(e):
        validate_button.visible = True
        page.update()
    invitation_field.on_focus = _on_invitation_focus

    form_card = ft.Container(
        content=ft.Column(
            [
                logo_badge,
                ft.Text("Create Account", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Set up your water station account", size=12, color=theme.TEXT_DIM),
                ft.Container(height=8),
                invitation_field,
                validate_button,
                business_name_field,
                first_name_field,
                last_name_field,
                email_field,
                password_field,
                confirm_password_field,
                error_text,
                primary_button("Create Account", ft.Icons.PERSON_ADD, _do_signup, width=float("inf")),
                ft.Container(content=loading, alignment=ft.Alignment.CENTER),
                ft.Container(height=4),
                toggle_button,
                ft.Row([
                    ft.Text("Already have an account?", size=12, color=theme.TEXT_DIM),
                    ft.TextButton("Sign In", on_click=lambda e: on_back_to_login(),
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