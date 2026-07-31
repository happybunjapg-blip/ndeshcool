"""Invitation Code Entry page — a permanent first-class method for joining a business.

Users enter the invitation code provided by the business owner.
The code is validated against the database via lookup_invitation().
The database determines business_id and role — NOT the client.

Both QR and manual-code flows converge on the same canonical methods:
  lookup_invitation(code) → join_business_with_invitation(code, ...)
"""
import traceback
import flet as ft
import theme
from widgets import primary_button
from services import Services
from services.auth_service import AuthError


def build_invitation_code_entry(page: ft.Page, services: Services,
                                 on_code_validated,
                                 on_back) -> ft.Container:
    """Build the manual invitation code entry page.
    
    Args:
        on_code_validated: Called with (code, invitation_info) on successful lookup.
        on_back: Called when user taps back.
    """
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False)
    loading = ft.ProgressRing(width=20, height=20, stroke_width=2, color=theme.ACCENT, visible=False)
    
    code_field = ft.TextField(
        label="Invitation Code",
        hint_text="e.g. 542180",
        prefix_icon=ft.Icons.LINK,
        border_radius=theme.RADIUS_INPUT,
        max_length=10,
        text_align=ft.TextAlign.CENTER,
        autofocus=True,
    )
    
    # Result display (shown after successful lookup)
    business_name_text = ft.Text("", size=16, color=theme.text_primary(),
                                  weight=ft.FontWeight.W_700)
    role_text = ft.Text("", size=14, color=theme.ACCENT, weight=ft.FontWeight.W_500)
    result_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.SUCCESS, size=20),
                ft.Text("Invitation Verified", size=14, color=theme.SUCCESS,
                        weight=ft.FontWeight.W_600),
            ], spacing=6),
            ft.Container(height=8),
            business_name_text,
            role_text,
            ft.Container(height=8),
            primary_button("Continue Registration", ft.Icons.ARROW_FORWARD,
                           lambda e: on_code_validated(code_field.value.strip(), None),
                           width=float("inf")),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(16, 12, 16, 12),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.08, theme.SUCCESS),
        visible=False,
    )
    
    def _validate_code(e):
        """Validate the invitation code against the database."""
        code = (code_field.value or "").strip()
        
        # Basic client-side validation
        if not code:
            error_text.value = "Please enter an invitation code."
            error_text.visible = True
            result_container.visible = False
            page.update()
            return
        
        if len(code) < 4:
            error_text.value = "Invitation code is too short."
            error_text.visible = True
            result_container.visible = False
            page.update()
            return
        
        if not code.isdigit():
            error_text.value = "Invitation code should contain only numbers."
            error_text.visible = True
            result_container.visible = False
            page.update()
            return
        
        # Show loading
        error_text.visible = False
        loading.visible = True
        page.update()
        
        # Look up invitation from database
        try:
            invitation_info = services.auth.lookup_invitation(code)
            
            # Display the result
            business_name = invitation_info.get("business_name", "the business")
            role = invitation_info.get("role", "worker")
            role_label = "Co-owner" if role == "co_owner" else "Worker"
            
            business_name_text.value = f"Business: {business_name}"
            role_text.value = f"Joining as: {role_label}"
            result_container.visible = True
            error_text.visible = False
            loading.visible = False
            page.update()
            
        except AuthError as err:
            error_text.value = str(err)
            error_text.visible = True
            result_container.visible = False
            loading.visible = False
            page.update()
        except Exception as err:
            error_text.value = "Could not verify invitation. Please check your connection."
            error_text.visible = True
            result_container.visible = False
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
                ft.Text("Enter Invitation Code", size=22, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Text("Ask the business owner for the invitation code",
                        size=12, color=theme.TEXT_DIM),
                ft.Container(height=12),
                code_field,
                error_text,
                ft.Container(content=loading, alignment=ft.Alignment.CENTER),
                primary_button("Verify Code", ft.Icons.CHECK_CIRCLE_OUTLINE,
                               _validate_code, width=float("inf")),
                ft.Container(height=8),
                result_container,
                ft.Container(height=4),
                ft.TextButton(
                    "← Back",
                    on_click=lambda e: on_back(),
                    style=ft.ButtonStyle(color=theme.TEXT_MID),
                ),
            ],
            spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=24, border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
                    ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )
    
    return ft.Container(content=form_card, alignment=ft.Alignment.CENTER,
                        padding=20, expand=True)