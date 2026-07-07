"""AppState is a local cache in front of whichever Repository is configured
(MemoryRepository for dev, SupabaseRepository for production). Every method
and attribute that existed before (products, customers, transactions,
daily_expenses, capital_expenses, timeline, water_readings, get_product,
get_customer, next_transaction_id, log_timeline, calculate_period_metrics,
period_dates, trend_str) is preserved exactly -- no service or page had to
change when this file was rewired to a real backend. That's the point of
having a Repository seam: only this file needed to know persistence changed.

New in this revision: Business Day tracking, and a `refresh()` + `subscribe`
hook so Supabase realtime pushes can update every connected device's cache.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from models import Product, Customer, Transaction, BusinessDay, BusinessDayStatus
from constants import PERIOD_LENGTHS
from .repository import Repository


class AppState:
    def __init__(self, repository: Repository):
        self.repo = repository
        self._on_change = None
        self.refresh()
        self.repo.subscribe(self._handle_remote_change)

    # ---------------------------------------------------------------
    # Cache refresh -- called on startup and whenever a realtime push
    # arrives, so every device converges on the same data.
    # ---------------------------------------------------------------
    def refresh(self):
        self.products: List[Product] = self.repo.list_products()
        self.customers: List[Customer] = self.repo.list_customers()
        self.transactions: List[Transaction] = self.repo.list_transactions()
        self.daily_expenses: List[dict] = self.repo.list_daily_expenses()
        self.capital_expenses: List[dict] = self.repo.list_capital_expenses()
        self.timeline: List[dict] = self.repo.list_timeline()
        self.water_readings: List[dict] = self.repo.list_water_readings()
        self.business_days: List[BusinessDay] = self.repo.list_business_days()

    def on_change(self, callback):
        """app.py registers a callback here (e.g. re-render the current
        page) so remote writes from other devices show up automatically."""
        self._on_change = callback

    def _handle_remote_change(self):
        self.refresh()
        if self._on_change:
            self._on_change()

    # ---------------------------------------------------------------
    # Lookups
    # ---------------------------------------------------------------
    def get_product(self, name: str) -> Optional[Product]:
        return next((p for p in self.products if p.name == name), None)

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return next((c for c in self.customers if c.id == customer_id), None)

    def next_transaction_id(self) -> str:
        return self.repo.next_transaction_id()

    def log_timeline(self, event: str, event_type: str, change: str, stock_after=0):
        now = datetime.now()
        record = {
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M"),
            "event": event,
            "type": event_type,
            "change": change,
            "stock_after": stock_after,
        }
        self.repo.add_timeline_event(record)
        self.timeline.append(record)

    # ---------------------------------------------------------------
    # Business Day
    # ---------------------------------------------------------------
    def get_open_business_day(self) -> Optional[BusinessDay]:
        return next((b for b in self.business_days if b.status == BusinessDayStatus.OPEN), None)

    def is_business_day_open(self) -> bool:
        return self.get_open_business_day() is not None

    def open_business_day(self, opened_by: str, opening_note: str = "") -> BusinessDay:
        if self.is_business_day_open():
            raise ValueError("A Business Day is already open.")
        now = datetime.now()
        day = BusinessDay(
            id=f"BD-{now.strftime('%Y%m%d-%H%M%S')}",
            opened_at=now.isoformat(),
            opened_by=opened_by,
            status=BusinessDayStatus.OPEN,
            opening_note=opening_note,
        )
        self.repo.open_business_day(day)
        self.business_days.append(day)
        self.log_timeline(f"Business Day opened by {opened_by}", "business_day", "", 0)
        return day

    def close_business_day(self, closed_by: str, closing_note: str = ""):
        day = self.get_open_business_day()
        if not day:
            raise ValueError("No Business Day is currently open.")
        now = datetime.now().isoformat()
        self.repo.close_business_day(day.id, now, closed_by, closing_note)
        day.status = BusinessDayStatus.CLOSED
        day.closed_at = now
        day.closed_by = closed_by
        day.closing_note = closing_note
        self.log_timeline(f"Business Day closed by {closed_by}", "business_day", "", 0)
        return day

    # ---------------------------------------------------------------
    # Period metrics (used by dashboard/reports)
    # ---------------------------------------------------------------
    @staticmethod
    def period_length_days(period: str) -> int:
        return PERIOD_LENGTHS.get(period, 1)

    def period_dates(self, period: str, end: Optional[date] = None) -> Tuple[date, date]:
        end = end or date.today()
        start = end - timedelta(days=self.period_length_days(period) - 1)
        return start, end

    def calculate_period_metrics(self, start: date, end: date) -> Dict:
        period_tx = [
            t for t in self.transactions
            if start <= datetime.strptime(t.date, "%Y-%m-%d").date() <= end
        ]
        revenue = sum(t.amount for t in period_tx if t.type.value in
                      ("water_refill", "product_sale", "bottle_water_sale", "bulk_delivery"))
        profit = sum(t.profit for t in period_tx)
        expenses_in_range = [
            e for e in self.daily_expenses
            if start <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end
        ]
        losses = sum(e["amount"] for e in expenses_in_range)
        water = [
            r for r in self.water_readings
            if start <= datetime.strptime(r["date"], "%Y-%m-%d").date() <= end
        ]
        water_total = sum(r["final"] - r["initial"] for r in water)
        water_cleaning = sum(r.get("cleaning", 0) for r in water)
        water_sold = sum(r.get("sold_water", 0) for r in water)
        return {
            "revenue": revenue,
            "profit": profit,
            "losses": losses,
            "water_total": water_total,
            "water_cleaning": water_cleaning,
            "water_sold": water_sold,
        }

    @staticmethod
    def trend_str(current: float, previous: float, invert: bool = False) -> Optional[str]:
        if previous == 0 and current == 0:
            return None
        pct = 100.0 if previous == 0 else (current - previous) / abs(previous) * 100
        if invert:
            pct = -pct
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.0f}%"
