"""Reusable layout helpers for consistent mobile-friendly spacing.

All page content should be wrapped with :func:`page_content` to ensure
proper padding, vertical rhythm, and safe-area awareness on mobile.
"""
import flet as ft
import theme


def page_content(controls: list, spacing: int | None = None) -> ft.Column:
    """Wrap a list of page controls with consistent mobile-friendly spacing.

    This is the **single** place where horizontal padding, vertical rhythm,
    and section spacing are defined.  Every page's ``build()`` method
    should return its controls wrapped in this helper.

    Parameters
    ----------
    controls : list
        The raw controls returned by a page's ``build()`` method.
    spacing : int, optional
        Override the default section-to-section spacing.  Defaults to
        ``theme.SECTION_SPACING`` (20 px).

    Returns
    -------
    ft.Column
        A scrollable column with proper padding and spacing.
    """
    return ft.Column(
        controls=controls,
        spacing=spacing or theme.SECTION_SPACING,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )