"""QR Scanner page for WaterPilot — Android Deep Link version.

The in-app camera scanner has been removed.

Architecture (Android):
1. Owner generates a QR containing a deep link URL:
     waterpilot://join?code=XXX&type=worker&business_id=UUID
2. Worker opens the phone's native Camera app
3. Android recognizes the QR and launches WaterPilot via the deep link
4. Flet receives the URL via page.url
5. The app parses the deep link and navigates to the Join Registration page

This page shows instructions for the worker to use their phone camera.
"""
import flet as ft
import theme
from widgets import primary_button


def build_qr_scanner(page: ft.Page,
                     on_scan_success,
                     on_back: callable,
                     services=None) -> ft.Container:
    """Build the QR scanner instruction page.
    
    This is NOT a real camera scanner. It shows instructions for the worker
    to use their phone's native Camera app to scan the QR code.
    
    Args:
        on_scan_success: Called with decoded QR dict when a deep link is received.
        on_back: Called when user taps back button.
        services: App services (unused in this version).
    """
    return _build_instruction_page(page, on_back)


def _build_instruction_page(page: ft.Page, on_back: callable) -> ft.Container:
    """Build a page instructing the user to scan with their phone camera."""
    
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.QR_CODE_SCANNER, color=ft.Colors.BLACK, size=28),
        width=56, height=56, border_radius=16, alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=18, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 4)),
    )
    
    step_icon_style = {
        "width": 36, "height": 36, "border_radius": 10,
        "alignment": ft.Alignment.CENTER,
        "bgcolor": ft.Colors.with_opacity(0.1, theme.ACCENT),
    }
    
    instruction_card = ft.Container(
        content=ft.Column([
            logo_badge,
            ft.Container(height=8),
            ft.Text("Scan with Phone Camera", size=22, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
            ft.Text("Use your phone's camera to scan the QR code",
                    size=13, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER),
            ft.Container(height=16),
            
            # Step 1
            ft.Row([
                ft.Container(
                    content=ft.Text("1", size=14, weight=ft.FontWeight.W_700,
                                    color=theme.ACCENT),
                    **step_icon_style,
                ),
                ft.Column([
                    ft.Text("Open Camera", size=15, weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE),
                    ft.Text("Open your phone's camera app", size=12, color=theme.TEXT_DIM),
                ], spacing=2, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Container(height=8),
            
            # Step 2
            ft.Row([
                ft.Container(
                    content=ft.Text("2", size=14, weight=ft.FontWeight.W_700,
                                    color=theme.ACCENT),
                    **step_icon_style,
                ),
                ft.Column([
                    ft.Text("Point at QR Code", size=15, weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE),
                    ft.Text("Point your camera at the QR code shown by the business owner",
                            size=12, color=theme.TEXT_DIM),
                ], spacing=2, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Container(height=8),
            
            # Step 3
            ft.Row([
                ft.Container(
                    content=ft.Text("3", size=14, weight=ft.FontWeight.W_700,
                                    color=theme.ACCENT),
                    **step_icon_style,
                ),
                ft.Column([
                    ft.Text("Tap the Link", size=15, weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE),
                    ft.Text("When a notification appears, tap it to open WaterPilot",
                            size=12, color=theme.TEXT_DIM),
                ], spacing=2, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Container(height=8),
            
            # Step 4
            ft.Row([
                ft.Container(
                    content=ft.Text("4", size=14, weight=ft.FontWeight.W_700,
                                    color=theme.ACCENT),
                    **step_icon_style,
                ),
                ft.Column([
                    ft.Text("Complete Registration", size=15, weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE),
                    ft.Text("Fill in your details to join the business",
                            size=12, color=theme.TEXT_DIM),
                ], spacing=2, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Container(height=20),
            
            # Manual code entry fallback
            ft.Container(
                content=ft.Column([
                    ft.Text("Can't scan?", size=13, color=theme.TEXT_DIM,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Ask the business owner for the invitation code "
                            "and enter it manually.",
                            size=12, color=theme.TEXT_DIM,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(16, 12, 16, 12),
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            ),
            
            ft.Container(height=12),
            
            # Back button
            ft.TextButton(
                "← Back",
                on_click=lambda e: on_back(),
                style=ft.ButtonStyle(color=theme.TEXT_MID),
            ),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           scroll=ft.ScrollMode.AUTO),
        padding=24, border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
                    ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )
    
    return ft.Container(
        content=instruction_card,
        alignment=ft.Alignment.CENTER,
        padding=20,
        expand=True,
    )