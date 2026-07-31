"""Join Business page — a permanent choice screen with two supported methods.

1. Scan QR Code
2. Enter Invitation Code

Both methods converge on the same canonical flow:
  lookup_invitation(code) → display business/role → join_business_with_invitation(code, ...)
"""
import flet as ft
import theme


def build_join_business(page: ft.Page,
                         on_scan_qr: callable,
                         on_enter_code: callable,
                         on_back: callable) -> ft.Container:
    """Build the Join Business choice screen.
    
    Args:
        on_scan_qr: Called when user chooses QR scan.
        on_enter_code: Called when user chooses manual code entry.
        on_back: Called when user taps back.
    """
    logo_badge = ft.Container(
        content=ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLACK, size=24),
        width=48, height=48, border_radius=14, alignment=ft.Alignment.CENTER,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.ACCENT, ft.Colors.BLUE_400],
        ),
        shadow=ft.BoxShadow(blur_radius=16, color=theme.ACCENT_SOFT, offset=ft.Offset(0, 4)),
    )

    choice_card = ft.Container(
        content=ft.Column([
            logo_badge,
            ft.Text("Join a Business", size=24, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE),
            ft.Text("Choose how to join", size=12, color=theme.TEXT_DIM),
            ft.Container(height=16),

            # Option A: Scan QR Code
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.QR_CODE_SCANNER,
                                            color=ft.Colors.BLACK, size=22),
                            width=44, height=44, border_radius=12,
                            bgcolor=theme.ACCENT, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=theme.TEXT_MID, size=20),
                    ]),
                    ft.Container(height=8),
                    ft.Text("Scan QR Code", size=17, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Text("Use your phone's camera to scan an invitation QR",
                            size=12, color=theme.TEXT_DIM),
                ], spacing=4),
                padding=ft.Padding(16, 14, 16, 14),
                border_radius=theme.RADIUS_CARD,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                border=ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=lambda e: on_scan_qr(),
                ink=True,
            ),

            ft.Container(
                content=ft.Row([
                    ft.Container(height=1, expand=True,
                                 bgcolor=theme.SURFACE_BORDER),
                    ft.Text("  or  ", size=12, color=theme.TEXT_DIM),
                    ft.Container(height=1, expand=True,
                                 bgcolor=theme.SURFACE_BORDER),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=0),
                padding=ft.Padding(0, 8, 0, 8),
            ),

            # Option B: Enter Invitation Code
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.KEYBOARD,
                                            color=ft.Colors.BLACK, size=22),
                            width=44, height=44, border_radius=12,
                            bgcolor=theme.GOLD, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=theme.TEXT_MID, size=20),
                    ]),
                    ft.Container(height=8),
                    ft.Text("Enter Invitation Code", size=17, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Text("Type the invitation code shared by the business owner",
                            size=12, color=theme.TEXT_DIM),
                ], spacing=4),
                padding=ft.Padding(16, 14, 16, 14),
                border_radius=theme.RADIUS_CARD,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                border=ft.Border.all(1, theme.SURFACE_BORDER),
                on_click=lambda e: on_enter_code(),
                ink=True,
            ),

            ft.Container(height=20),

            # Back button
            ft.TextButton(
                "← Back",
                on_click=lambda e: on_back(),
                style=ft.ButtonStyle(color=theme.TEXT_MID),
            ),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=24, border_radius=theme.RADIUS_CARD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
                    ft.Colors.with_opacity(0.02, ft.Colors.WHITE)],
        ),
        border=ft.Border.all(1, theme.SURFACE_BORDER),
        expand=True,
    )

    return ft.Container(content=choice_card, alignment=ft.Alignment.CENTER,
                        padding=20, expand=True)