"""AppState is a local cache in front of whichever Repository is configured.

Data is NOT loaded on construction. Instead refresh() is called explicitly
after authentication succeeds. This avoids crashing on the splash/login
screen when no user is authenticated yet.
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
        # Data is NOT loaded here. Call refresh() after authentication.
        self.products: List[Product] = []
        self.customers: List[Customer] = []
        self.transactions: List[Transaction] = []
        self.daily_expenses: List[dict] = []
        self.capital_expenses: List[dict] = []
        self.timeline: List[dict] = []
        self.water_readings: List[dict] = []
        self.business_days: List[BusinessDay] = []

        # Subscribe to realtime — this doesn't query, just listens
        self.repo.subscribe(self._handle_remote_change)

    # ---------------------------------------------------------------
    # Cache refresh — call AFTER authentication succeeds
    # ---------------------------------------------------------------
    def refresh(self):
        """Load all data from the repository. Must only be called after
        authentication is complete and business_id is set on the repo."""
        self.products = self.repo.list_products()
        self.customers = self.repo.list_customers()
        self.transactions = self.repo.list_transactions()
        self.daily_expenses = self.repo.list_daily_expenses()
        self.capital_expenses = self.repo.list_capital_expenses()
        self.timeline = self.repo.list_timeline()
        self.water_readings = self.repo.list_water_readings()
        self.business_days = self.repo.list_business_days()

    def on_change(self, callback):
        self._on_change = callback

    def notify_change(self):
        if self._on_change:
            self._on_change()

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
        self.notify_change()
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
        self.notify_change()
        return day

    # ---------------------------------------------------------------
    # Period metrics
    # ---------------------------------------------------------------
    @staticmethod
    def period_length_days(period: str) -> int:
        return PERIOD_LENGTHS.get(period, 1)

    def period_dates(self, period: str, end: Optional[date] = None) -> Tuple[date, date]:
        end = end or date.today()
        start = end - timedelta(days=self.period_length_days(period) - 1)
        return start, end

    @staticmethod
    def day_bounds(ref: Optional[date] = None) -> Tuple[date, date]:
        ref = ref or date.today()
        return ref, ref

    @staticmethod
    def week_bounds(ref: Optional[date] = None) -> Tuple[date, date]:
        ref = ref or date.today()
        start = ref - timedelta(days=ref.weekday())
        end = start + timedelta(days=6)
        return start, end

    @staticmethod
    def month_bounds(ref: Optional[date] = None) -> Tuple[date, date]:
        ref = ref or date.today()
        start = ref.replace(day=1)
        if start.month == 12:
            next_month_start = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month_start = start.replace(month=start.month + 1, day=1)
        end = next_month_start - timedelta(days=1)
        return start, end

    def calendar_period_dates(self, period: str, ref: Optional[date] = None) -> Tuple[date, date]:
        if period == "weekly":
            return self.week_bounds(ref)
        if period == "monthly":
            return self.month_bounds(ref)
        return self.day_bounds(ref)

    def detail_in_range(self, start: date, end: date) -> Dict:
        tx_in_range = [
            t for t in self.transactions
            if start <= datetime.strptime(t.date, "%Y-%m-%d").date() <= end
        ]
        daily_exp_in_range = [
            e for e in self.daily_expenses
            if start <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end
        ]
        capital_exp_in_range = [
            e for e in self.capital_expenses
            if start <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end
        ]
        tx_in_range.sort(key=lambda t: (t.date, t.time), reverse=True)
        return {
            "transactions": tx_in_range,
            "daily_expenses": daily_exp_in_range,
            "capital_expenses": capital_exp_in_range,
        }

    def calculate_period_metrics(self, start: date, end: date) -> Dict:
        period_tx = [
            t for t in self.transactions
            if start <= datetime.strptime(t.date, "%Y-%m-%d").date() <= end
        ]
        revenue = sum(t.amount for t in period_tx if t.type.value in
                      ("water_refill", "product_sale", "bottle_water_sale", "bulk_delivery"))
        profit = sum(t.profit for t in period_tx)
        daily_in_range = [
            e for e in self.daily_expenses
            if start <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end
        ]
        capital_in_range = [
            e for e in self.capital_expenses
            if start <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end
        ]
        daily_expenses_total = sum(e["amount"] for e in daily_in_range)
        capital_expenses_total = sum(e["amount"] for e in capital_in_range)
        losses = daily_expenses_total + capital_expenses_total
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
            "daily_expenses_total": daily_expenses_total,
            "capital_expenses_total": capital_expenses_total,
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