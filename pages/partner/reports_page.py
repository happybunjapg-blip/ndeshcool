from datetime import datetime, timedelta
import flet as ft
import theme
from constants import TODAY
from widgets import glass_card, section_title, primary_button, show_snack, page_content
from services import Services


class PartnerReportsPage:
    """Professional business dashboard for AquaFlow owners.

    Displays a date-range report with four themed card groups:
        1. Income  – Revenue, Gross Profit
        2. Expenses – Operational, Capital, Total
        3. Business Result – Net Profit, Profit Margin %
        4. Water Operations – Processed, Sold, Cleaning, Efficiency %
    """

    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.from_field = ft.TextField(
            label="From",
            value=(TODAY - timedelta(days=30)).isoformat(),
            expand=True,
            border_radius=theme.RADIUS_INPUT,
        )
        self.to_field = ft.TextField(
            label="To",
            value=TODAY.isoformat(),
            expand=True,
            border_radius=theme.RADIUS_INPUT,
        )
        self.summary = self._compute_summary()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _compute_summary(self):
        try:
            start = datetime.strptime(self.from_field.value, "%Y-%m-%d").date()
            end = datetime.strptime(self.to_field.value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start, end = TODAY - timedelta(days=30), TODAY
        return self.services.state.calculate_period_metrics(start, end)

    def _generate(self, e):
        if not self.from_field.value or not self.to_field.value:
            show_snack(self.page, "Please select both dates.", theme.DANGER)
            return
        self.summary = self._compute_summary()
        show_snack(
            self.page,
            f"Report generated for {self.from_field.value} to {self.to_field.value}",
        )
        self.on_navigate("reports")

    # ------------------------------------------------------------------
    # Card builders
    # ------------------------------------------------------------------
    def _income_card(self, s: dict) -> ft.Container:
        return glass_card(
            ft.Column([
                section_title("Income", ft.Icons.TRENDING_UP),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Total Revenue", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {s['revenue']:,.0f}", size=22,
                                weight=ft.FontWeight.W_800, color=theme.SUCCESS),
                    ], spacing=2, expand=True),
                ]),
                ft.Row([
                    ft.Column([
                        ft.Text("Gross Profit", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {s['profit']:,.0f}", size=22,
                                weight=ft.FontWeight.W_800, color=theme.ACCENT),
                    ], spacing=2, expand=True),
                ]),
            ], spacing=10),
            padding=16, accent=theme.SUCCESS,
        )

    def _expenses_card(self, s: dict) -> ft.Container:
        return glass_card(
            ft.Column([
                section_title("Expenses", ft.Icons.RECEIPT_LONG_OUTLINED),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Operational Expenses", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {s['daily_expenses_total']:,.0f}", size=18,
                                weight=ft.FontWeight.W_700, color=theme.WARNING),
                    ], spacing=2, expand=True),
                ]),
                ft.Row([
                    ft.Column([
                        ft.Text("Capital Expenses", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {s['capital_expenses_total']:,.0f}", size=18,
                                weight=ft.FontWeight.W_700, color=theme.WARNING),
                    ], spacing=2, expand=True),
                ]),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Total Expenses", size=13, weight=ft.FontWeight.W_600,
                                color=theme.text_primary()),
                        ft.Text(f"KES {s['losses']:,.0f}", size=20,
                                weight=ft.FontWeight.W_800, color=theme.DANGER),
                    ], spacing=2, expand=True),
                ]),
            ], spacing=10),
            padding=16, accent=theme.WARNING,
        )

    def _result_card(self, s: dict) -> ft.Container:
        net_profit = s["profit"] - s["losses"]
        margin = (net_profit / s["revenue"] * 100) if s["revenue"] > 0 else 0.0
        profit_color = theme.SUCCESS if net_profit >= 0 else theme.DANGER
        return glass_card(
            ft.Column([
                section_title("Business Result", ft.Icons.ANALYTICS_OUTLINED),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Net Profit", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {net_profit:,.0f}", size=24,
                                weight=ft.FontWeight.W_800, color=profit_color),
                    ], spacing=2, expand=True),
                ]),
                ft.Row([
                    ft.Column([
                        ft.Text("Profit Margin", size=12, color=theme.text_secondary()),
                        ft.Text(f"{margin:.1f}%", size=24,
                                weight=ft.FontWeight.W_800, color=profit_color),
                    ], spacing=2, expand=True),
                ]),
            ], spacing=10),
            padding=16, accent=profit_color,
        )

    def _water_card(self, s: dict) -> ft.Container:
        efficiency = (s["water_sold"] / s["water_total"] * 100) if s["water_total"] > 0 else 0.0
        return glass_card(
            ft.Column([
                section_title("Water Operations", ft.Icons.WATER_DROP),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Total Processed", size=12, color=theme.text_secondary()),
                        ft.Text(f"{s['water_total']:,.0f} L", size=18,
                                weight=ft.FontWeight.W_700, color=theme.ACCENT),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Water Sold", size=12, color=theme.text_secondary()),
                        ft.Text(f"{s['water_sold']:,.0f} L", size=18,
                                weight=ft.FontWeight.W_700, color=theme.SUCCESS),
                    ], spacing=2, expand=True),
                ]),
                ft.Row([
                    ft.Column([
                        ft.Text("Cleaning Usage", size=12, color=theme.text_secondary()),
                        ft.Text(f"{s['water_cleaning']:,.0f} L", size=18,
                                weight=ft.FontWeight.W_700, color=theme.WARNING),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Efficiency", size=12, color=theme.text_secondary()),
                        ft.Text(f"{efficiency:.1f}%", size=18,
                                weight=ft.FontWeight.W_700, color=theme.GOLD),
                    ], spacing=2, expand=True),
                ]),
                ft.ProgressBar(
                    value=s["water_sold"] / max(s["water_total"], 1),
                    color=theme.ACCENT,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                    bar_height=8,
                    border_radius=4,
                ),
                ft.Text(
                    f"{efficiency:.0f}% of processed water was sold",
                    size=11, color=theme.text_dim(),
                ),
            ], spacing=10),
            padding=16, accent=theme.ACCENT,
        )

    def _general_totals_card(self) -> ft.Container:
        """Lifetime / all-time financial summary stored so all money
        is always accounted for — every KES in revenue, expenses, and
        profit appears here regardless of the date-range filter."""
        # Use a very wide date range (year 2000 → 2100) to capture all data
        all_start = datetime(2000, 1, 1).date()
        all_end = datetime(2100, 1, 1).date()
        g = self.services.state.calculate_period_metrics(all_start, all_end)
        net = g["profit"] - g["losses"]
        margin = (net / g["revenue"] * 100) if g["revenue"] > 0 else 0.0
        color = theme.SUCCESS if net >= 0 else theme.DANGER
        return glass_card(
            ft.Column([
                section_title("General Totals (All Time)", ft.Icons.ACCOUNT_BALANCE_OUTLINED),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("Total Revenue", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {g['revenue']:,.0f}", size=20,
                                weight=ft.FontWeight.W_800, color=theme.SUCCESS),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Total Expenses", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {g['losses']:,.0f}", size=20,
                                weight=ft.FontWeight.W_800, color=theme.DANGER),
                    ], spacing=2, expand=True),
                ]),
                ft.Row([
                    ft.Column([
                        ft.Text("Net Profit", size=12, color=theme.text_secondary()),
                        ft.Text(f"KES {net:,.0f}", size=20,
                                weight=ft.FontWeight.W_800, color=color),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text("Profit Margin", size=12, color=theme.text_secondary()),
                        ft.Text(f"{margin:.1f}%", size=20,
                                weight=ft.FontWeight.W_800, color=color),
                    ], spacing=2, expand=True),
                ]),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Text(
                    "Every KES earned and spent appears here — no money is lost.",
                    size=12, color=theme.text_dim(),
                ),
            ], spacing=10),
            padding=16, accent=theme.ACCENT,
        )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self) -> list:
        s = self.summary
        return [
            # ── Page title ───────────────────────────────────────
            section_title("Partner Reports", ft.Icons.BAR_CHART_OUTLINED),

            # ── Date range picker ────────────────────────────────
            glass_card(
                ft.Column([
                    ft.Row([self.from_field, self.to_field], spacing=10),
                    primary_button(
                        "Generate Report", ft.Icons.REFRESH,
                        self._generate, width=float("inf"),
                    ),
                ], spacing=12),
                padding=16, accent=theme.ACCENT,
            ),

            # ── Income ───────────────────────────────────────────
            self._income_card(s),

            # ── Expenses ─────────────────────────────────────────
            self._expenses_card(s),

            # ── Business Result ──────────────────────────────────
            self._result_card(s),

            # ── Water Operations ─────────────────────────────────
            self._water_card(s),

            # ── General Totals (all time) ────────────────────────
            self._general_totals_card(),
        ]
