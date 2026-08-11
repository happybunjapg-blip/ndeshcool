import flet as ft
import theme


def waterpilot_mark(size: int = 96, color: str | None = None) -> ft.Container:
    """A geometric WaterPilot monogram mark built for brand recognition."""
    color = color or theme.PRIMARY
    white = theme.LIGHT_SURFACE
    stroke_width = max(10, size // 10)
    inner_offset = size * 0.18
    return ft.Container(
        width=size,
        height=size,
        border_radius=int(size * 0.22),
        bgcolor=color,
        content=ft.Stack(
            [
                ft.Container(
                    width=stroke_width,
                    height=int(size * 0.55),
                    border_radius=stroke_width // 2,
                    bgcolor=white,
                    left=int(inner_offset),
                    top=int(size * 0.22),
                ),
                ft.Container(
                    width=int(size * 0.25),
                    height=int(size * 0.42),
                    border_radius=int(size * 0.15),
                    bgcolor=white,
                    left=int(size * 0.60),
                    top=int(size * 0.22),
                ),
                ft.Container(
                    width=int(size * 0.30),
                    height=int(size * 0.10),
                    border_radius=stroke_width // 2,
                    bgcolor=white,
                    left=int(inner_offset + 2),
                    top=int(size * 0.50),
                    rotate=-0.36,
                ),
                ft.Container(
                    width=int(size * 0.30),
                    height=int(size * 0.10),
                    border_radius=stroke_width // 2,
                    bgcolor=white,
                    left=int(inner_offset + size * 0.20),
                    top=int(size * 0.50),
                    rotate=0.36,
                ),
            ],
            width=size,
            height=size,
        ),
    )


def waterpilot_wordmark(size: int = 32) -> ft.Text:
    return ft.Text(
        "WaterPilot",
        style=ft.TextStyle(
            size=size,
            weight=ft.FontWeight.W_700,
            letter_spacing=0.36,
            height=1.0,
        ),
        color=theme.TEXT_PRIMARY,
        text_align=ft.TextAlign.CENTER,
    )


def waterpilot_tagline(text: str = "Smart Water Business Management") -> ft.Text:
    return ft.Text(
        text,
        style=ft.TextStyle(
            size=15,
            weight=ft.FontWeight.W_400,
            letter_spacing=0.18,
            height=1.6,
        ),
        color=theme.text_secondary(),
        text_align=ft.TextAlign.CENTER,
    )


def waterpilot_loader(dot_count: int = 3, dot_size: int = 10, spacing: int = 10) -> tuple[ft.Row, list[ft.Container]]:
    dots: list[ft.Container] = []
    for _ in range(dot_count):
        dot = ft.Container(
            width=dot_size,
            height=dot_size,
            border_radius=dot_size // 2,
            bgcolor=theme.ACCENT,
            opacity=0.32,
            animate_opacity=ft.Animation(theme.ANIM_DURATION_FAST, theme.ANIMATION_CURVE),
        )
        dots.append(dot)

    loader = ft.Row(
        controls=dots,
        spacing=spacing,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return loader, dots


def waterpilot_footer(text: str = "Powered by ArcNova") -> ft.Text:
    return ft.Text(
        text,
        style=ft.TextStyle(
            size=10,
            weight=ft.FontWeight.W_400,
            letter_spacing=0.12,
            height=1.4,
        ),
        color=theme.text_dim(),
        text_align=ft.TextAlign.CENTER,
        opacity=0.55,
    )
