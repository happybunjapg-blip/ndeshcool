from datetime import datetime
import flet as ft
import theme
from widgets import glass_card, section_title, primary_button
from services import Services


class PartnerPerformancePage:
    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.date_field = ft.TextField(label="Filter by date (YYYY-MM-DD)", value="",
                                        expand=True, read_only=True, border_radius=theme.RADIUS_INPUT)
        self.date_picker = ft.DatePicker(on_change=self._on_date_picked)
        self.timeline_list = ft.Column(spacing=10)

    def _on_date_picked(self, e):
        picked = self.date_picker.value
        if picked:
            picked_date = picked.date() if isinstance(picked, datetime) else picked
            self.date_field.value = picked_date.isoformat()
            self.on_navigate("performance")

    def _clear(self, e):
        self.date_field.value = ""
        self.on_navigate("performance")

    def _rows(self):
        filter_date = self.date_field.value
        rows = [t for t in self.services.state.timeline if not filter_date or t["date"] == filter_date]
        rows = sorted(rows, key=lambda r: (r["date"], r["time"]), reverse=True)
        controls = []
        for t in rows:
            icon, color = theme.TIMELINE_STYLE.get(t["type"], theme.DEFAULT_TIMELINE_STYLE)
            controls.append(
                glass_card(
                    ft.Row([
                        ft.Icon(icon, color=color),
                        ft.Column([
                            ft.Text(t["event"], size=13, weight=ft.FontWeight.W_600, color=theme.text_primary()),
                            ft.Text(f"{t['date']}  •  {t['time']}", size=11, color=theme.TEXT_DIM),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(t["change"], size=13, weight=ft.FontWeight.W_700, color=color),
                            ft.Text(f"stock: {t['stock_after']}", size=10, color=theme.TEXT_DIM),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=12,
                )
            )
        return controls or [ft.Text("No events for this date.", color=theme.TEXT_DIM)]

    def build(self) -> list:
        self.timeline_list.controls = self._rows()
        return [
            section_title("Performance History", ft.Icons.TIMELINE_OUTLINED),
            glass_card(
                ft.Column([
                    ft.Row([
                        self.date_field,
                        ft.IconButton(ft.Icons.CALENDAR_MONTH_OUTLINED, icon_color=theme.ACCENT,
                                      on_click=lambda e: self.page.show_dialog(self.date_picker)),
                    ], spacing=8),
                    ft.Row([
                        primary_button("Refresh", ft.Icons.REFRESH, lambda e: self.on_navigate("performance")),
                        ft.TextButton("Clear", style=ft.ButtonStyle(color=theme.TEXT_MID), on_click=self._clear),
                    ], spacing=8),
                ], spacing=12),
                padding=16, accent=theme.ACCENT,
            ),
            self.timeline_list,
        ]
