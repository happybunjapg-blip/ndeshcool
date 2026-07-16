from datetime import datetime, timedelta, date
import flet as ft
import theme
from constants import TODAY
from widgets import glass_card, section_title, primary_button, show_snack, page_content
from services import Services

# Human-readable labels for each transaction type, used in the daily
# activity list so a partner can see exactly what happened -- not just
# a total.
_TX_LABELS = {
    "water_refill": "Water Refill",
    "product_sale": "Product Sale",
    "bottle_water_sale": "Bottle + Water Sale",
    "bulk_delivery": "Bulk Delivery",
    "customer_payment": "Customer Payment",
    "expense": "Expense",
}


class PartnerReportsPage:
    """Professional business dashboard for AquaFlow owners.

    Three calendar-accurate views -- Daily / Weekly / Monthly -- each
    showing that period's own numbers (no overlap/repetition with the
    others) plus a line-item activity list:
        1. Income  – Revenue, Gross Profit
        2. Expenses – Operational, Capital, Total
        3. Business Result – Net Profit, Profit Margin %
        4. Water Operations – Processed, Sold, Cleaning, Efficiency %
        5. Activity – every sale/payment/expense that happened in the period

    "Monthly" means the *actual* calendar month (1st -> the real last day,
    28/29/30/31 whatever that month has) -- not a rolling 30-day window.
    "Weekly" means the real Monday -> Sunday week. Use the arrows to step
    to a previous/next day, week, or month.
    """

    PERIODS = ["daily", "weekly", "monthly"]
    PERIOD_LABELS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}

    def __init__(self, page: ft.Page, services: Services, on_navigate):
        self.page = page
        self.services = services
        self.on_navigate = on_navigate
        self.period = "daily"
        self.ref_date = TODAY
        self.summary = None
        self.detail = None
        self.range_label = ""
        self._compute()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _compute(self):
        start, end = self.services.state.calendar_period_dates(self.period, self.ref_date)
        self.summary = self.services.state.calculate_period_metrics(start, end)
        self.detail = self.services.state.detail_in_range(start, end)
        if self.period == "daily":
            self.range_label = start.strftime("%A, %d %b %Y")
        elif self.period == "weekly":
            self.range_label = f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
        else:
            self.range_label = start.strftime("%B %Y")

    def _set_period(self, e):
        self.period = e.control.data
        self.ref_date = TODAY  # jump back to "now" whenever switching tabs
        self._compute()
        self.on_navigate("reports")

    def _step(self, delta: int):
        def handler(e):
            if self.period == "daily":
                self.ref_date = self.ref_date + timedelta(days=delta)
            elif self.period == "weekly":
                self.ref_date = self.ref_date + timedelta(weeks=delta)
            else:
                # Step by calendar month, not by a fixed day count, so
                # stepping from e.g. Jan 31 lands in Feb, not skips it.
                month = self.ref_date.month - 1 + delta
                year = self.ref_date.year + month // 12
                month = month % 12 + 1
                day = min(self.ref_date.day, 28)
                self.ref_date = date(year, month, day)
            self._compute()
            self.on_navigate("reports")
        return handler

    # ------------------------------------------------------------------
    # Period tabs + navigation
    # ------------------------------------------------------------------
    def _period_tabs(self) -> ft.Container:
        buttons = []
        for p in self.PERIODS:
            active = p == self.period
            buttons.append(
                ft.Container(
                    content=ft.Text(self.PERIOD_LABELS[p], size=13,
                                     weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
                                     color=theme.BG if active else theme.text_secondary()),
                    padding=ft.Padding(14, 8, 14, 8),
                    border_radius=10,
                    bgcolor=theme.ACCENT if active else None,
                    data=p,
                    on_click=self._set_period,
                    ink=True,
                )
            )
        return ft.Container(
            content=ft.Row(buttons, spacing=6),
            padding=4,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
        )

    def _range_nav(self) -> ft.Row:
        return ft.Row([
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=self._step(-1)),
            ft.Text(self.range_label, size=14, weight=ft.FontWeight.W_700,
                    color=theme.text_primary(), expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=self._step(1)),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

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

    def _activity_card(self) -> ft.Container:
        """Line-item list of everything that happened in this period --
        every sale, payment, and expense -- so nothing is just a total
        with no way to see what actually made it up."""
        rows = []
        for t in self.detail["transactions"]:
            label = _TX_LABELS.get(t.type.value, t.type.value)
            extra = ""
            d = t.details or {}
            if "product" in d:
                extra = f" — {d.get('qty', ''):g} × {d['product']}" if isinstance(d.get("qty"), (int, float)) else f" — {d['product']}"
            elif "liters" in d:
                extra = f" — {d['liters']:g}L"
            amount_color = theme.SUCCESS if t.amount >= 0 else theme.DANGER
            rows.append(
                ft.Row([
                    ft.Column([
                        ft.Text(f"{label}{extra}", size=13, weight=ft.FontWeight.W_600,
                                color=theme.text_primary()),
                        ft.Text(f"{t.date} {t.time}", size=11, color=theme.text_dim()),
                    ], spacing=1, expand=True),
                    ft.Text(f"KES {t.amount:,.0f}", size=13, weight=ft.FontWeight.W_700,
                            color=amount_color),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
        for exp in self.detail["daily_expenses"] + self.detail["capital_expenses"]:
            rows.append(
                ft.Row([
                    ft.Column([
                        ft.Text(f"Expense — {exp['description']}", size=13,
                                weight=ft.FontWeight.W_600, color=theme.text_primary()),
                        ft.Text(f"{exp['date']} {exp.get('time', '')} · {exp.get('category', 'Other')}",
                                size=11, color=theme.text_dim()),
                    ], spacing=1, expand=True),
                    ft.Text(f"-KES {exp['amount']:,.0f}", size=13, weight=ft.FontWeight.W_700,
                            color=theme.DANGER),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
        if not rows:
            rows = [ft.Text("Nothing recorded for this period.", color=theme.TEXT_DIM)]
        return glass_card(
            ft.Column([
                section_title("Activity", ft.Icons.LIST_ALT_OUTLINED),
                ft.Divider(height=1, color=theme.SURFACE_BORDER if theme.DARK_MODE
                           else theme.LIGHT_SURFACE_BORDER),
                ft.Column(rows, spacing=10),
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

            # ── Daily / Weekly / Monthly selector + period nav ───
            glass_card(
                ft.Column([
                    self._period_tabs(),
                    self._range_nav(),
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

            # ── Activity (this period only) ──────────────────────
            self._activity_card(),

            # ── General Totals (all time) ────────────────────────
            self._general_totals_card(),
        ]
