"""Production backend. Talks to Supabase (Postgres + Auth + Realtime) using
the official `supabase-py` client. Implements the exact same Repository
interface as MemoryRepository, so `backend/state.py`, every service, and
every page work completely unchanged whether BACKEND=memory or =supabase.

Setup:
    1. Create a Supabase project.
    2. Run backend/supabase_schema.sql in its SQL editor.
    3. Copy .env.example to .env and fill in SUPABASE_URL / SUPABASE_KEY.
    4. Set BACKEND=supabase in .env.
    5. pip install -r requirements.txt (adds `supabase`).
"""
import asyncio
import threading
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable

from postgrest.exceptions import APIError

from models import Product, Batch, Customer, Transaction, TransactionType, ProductCategory, BusinessDay
from .repository import Repository

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


RECONNECT_BASE_DELAY = 1.0   # seconds
RECONNECT_MAX_DELAY = 30.0   # seconds
REALTIME_TABLES = [
    "transactions", "expenses", "products", "product_batches",
    "customers", "water_readings", "business_days", "timeline_events",
]


class SupabaseRepository(Repository):
    def __init__(self, url: str, key: str):
        if create_client is None:
            raise RuntimeError(
                "The `supabase` package isn't installed. Run: pip install supabase"
            )
        self._url = url
        self._key = key
        self.client: Client = create_client(url, key)
        self._change_callback: Optional[Callable] = None

        # ---- Realtime thread-safety primitives --------------------------
        self._realtime_pending = threading.Event()
        self._last_realtime_ts = 0.0
        self._stop_event = threading.Event()
        self._realtime_thread: Optional[threading.Thread] = None

    # ---- Row <-> model mapping ------------------------------------------
    @staticmethod
    def _row_to_product(row: dict, batch_rows: List[dict]) -> Product:
        return Product(
            name=row["name"],
            category=ProductCategory(row["category"]),
            qty=row["qty"],
            threshold=row["threshold"],
            selling_price=row["selling_price"],
            buying_price=row["buying_price"],
            batches=[Batch(b["qty"], b["purchase_price"], str(b["purchase_date"])) for b in batch_rows],
        )

    @staticmethod
    def _row_to_customer(row: dict) -> Customer:
        return Customer(
            id=row["id"], name=row["name"], phone=row.get("phone", ""),
            is_credit=row.get("is_credit", True), balance=row.get("balance", 0),
            notes=row.get("notes", ""), last_purchase=row.get("last_purchase"),
        )

    @staticmethod
    def _row_to_transaction(row: dict) -> Transaction:
        return Transaction(
            id=row["id"], type=TransactionType(row["type"]), date=str(row["date"]),
            time=row["time"], amount=row["amount"], profit=row["profit"],
            customer_id=row.get("customer_id"), details=row.get("details", {}),
        )

    @staticmethod
    def _row_to_business_day(row: dict) -> BusinessDay:
        return BusinessDay(
            id=row["id"], opened_at=str(row["opened_at"]), opened_by=row["opened_by"],
            status=row["status"], opening_note=row.get("opening_note", ""),
            closed_at=row.get("closed_at"), closed_by=row.get("closed_by"),
            closing_note=row.get("closing_note", ""),
        )

    def _safe_execute(self, table_name: str, operation: str):
        try:
            return self.client.table(table_name).select("*").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def _safe_execute_single(self, table_name: str, name: str, field: str):
        try:
            return self.client.table(table_name).select("*").eq(field, name).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def _safe_execute_operation(self, operation):
        try:
            return operation.execute()
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise

    # ---- Products ----------------------------------------------------
    def list_products(self) -> List[Product]:
        try:
            products = self.client.table("products").select("*").execute().data
            batches = self.client.table("product_batches").select("*").order("id").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        result = []
        for p in products:
            own_batches = [b for b in batches if b["product_name"] == p["name"]]
            result.append(self._row_to_product(p, own_batches))
        return result

    def get_product(self, name: str) -> Optional[Product]:
        try:
            rows = self.client.table("products").select("*").eq("name", name).execute().data
            if not rows:
                return None
            batches = self.client.table("product_batches").select("*").eq(
                "product_name", name).order("id").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_product(rows[0], batches)

    def save_product(self, product: Product) -> None:
        self._safe_execute_operation(self.client.table("products").update({
            "qty": product.qty, "threshold": product.threshold,
            "selling_price": product.selling_price,
            "buying_price": product.buying_price, "updated_at": datetime.now().isoformat(),
        }).eq("name", product.name))
        # Batches are the source of truth for FIFO -- rewrite them wholesale.
        # (Fine at this data volume; switch to targeted upserts if batch
        # counts grow into the thousands per product.)
        self._safe_execute_operation(self.client.table("product_batches").delete().eq("product_name", product.name))
        for b in product.batches:
            self._safe_execute_operation(self.client.table("product_batches").insert({
                "product_name": product.name, "qty": b.qty,
                "purchase_price": b.purchase_price, "purchase_date": b.date,
            }))

    # ---- Customers (credit customers only) ------------------------------
    def list_customers(self) -> List[Customer]:
        try:
            rows = self.client.table("customers").select("*").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._row_to_customer(r) for r in rows]

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        try:
            rows = self.client.table("customers").select("*").eq("id", customer_id).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_customer(rows[0]) if rows else None

    def save_customer(self, customer: Customer) -> None:
        self._safe_execute_operation(self.client.table("customers").update({
            "balance": customer.balance, "is_credit": customer.is_credit,
            "notes": customer.notes, "last_purchase": customer.last_purchase,
        }).eq("id", customer.id))

    def add_customer(self, customer: Customer) -> None:
        self._safe_execute_operation(self.client.table("customers").insert({
            "id": customer.id, "name": customer.name, "phone": customer.phone,
            "is_credit": customer.is_credit, "balance": customer.balance, "notes": customer.notes,
        }))

    # ---- Transactions ----------------------------------------------------
    def list_transactions(self) -> List[Transaction]:
        try:
            rows = self.client.table("transactions").select("*").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._row_to_transaction(r) for r in rows]

    def add_transaction(self, transaction: Transaction) -> None:
        self._safe_execute_operation(self.client.table("transactions").insert({
            "id": transaction.id, "type": transaction.type.value, "date": transaction.date,
            "time": transaction.time, "amount": transaction.amount, "profit": transaction.profit,
            "customer_id": transaction.customer_id, "details": transaction.details,
            "created_by": transaction.customer_id or "system",
        }))

    def next_transaction_id(self) -> str:
        # Postgres identity columns would be cleaner; kept as a readable id
        # scheme (T00001, T00002...) to match the in-memory backend's format.
        count = self.client.table("transactions").select("id", count="exact").execute().count or 0
        return f"T{count + 1:05d}"

    # ---- Expenses -----------------------------------------------------
    def list_daily_expenses(self) -> List[Dict[str, Any]]:
        try:
            rows = self.client.table("expenses").select("*").eq("is_capital", False).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return rows

    def add_daily_expense(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("expenses").insert({**record, "is_capital": False}))

    def list_capital_expenses(self) -> List[Dict[str, Any]]:
        try:
            rows = self.client.table("expenses").select("*").eq("is_capital", True).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return rows

    def add_capital_expense(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("expenses").insert({**record, "is_capital": True}))

    # ---- Timeline -----------------------------------------------------
    def list_timeline(self) -> List[Dict[str, Any]]:
        try:
            return self.client.table("timeline_events").select("*").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def add_timeline_event(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("timeline_events").insert(record))

    # ---- Water readings -------------------------------------------------
    def list_water_readings(self) -> List[Dict[str, Any]]:
        try:
            return self.client.table("water_readings").select("*").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def add_water_reading(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("water_readings").upsert(record))

    def upsert_today_water_reading(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("water_readings").upsert(record))

    # ---- Business Day ----------------------------------------------------
    def get_open_business_day(self) -> Optional[BusinessDay]:
        try:
            rows = self.client.table("business_days").select("*").eq("status", "OPEN").execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_business_day(rows[0]) if rows else None

    def list_business_days(self) -> List[BusinessDay]:
        try:
            rows = self.client.table("business_days").select("*").order("opened_at", desc=True).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._row_to_business_day(r) for r in rows]

    def open_business_day(self, business_day: BusinessDay) -> None:
        # The partial unique index in supabase_schema.sql (one row with
        # status='OPEN') makes this safe even if two workers tap "Open" at
        # the same instant on different devices -- the second insert fails.
        self._safe_execute_operation(self.client.table("business_days").insert({
            "id": business_day.id, "opened_at": business_day.opened_at,
            "opened_by": business_day.opened_by, "status": business_day.status,
            "opening_note": business_day.opening_note,
        }))

    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None:
        self._safe_execute_operation(self.client.table("business_days").update({
            "status": "CLOSED", "closed_at": closed_at,
            "closed_by": closed_by, "closing_note": closing_note,
        }).eq("id", business_day_id))

    # =====================================================================
    # REALTIME — cross-device sync via Supabase Realtime
    # =====================================================================
    def subscribe(self, on_change) -> None:
        """Subscribe to Postgres Changes on every table this app uses.

        Runs the async realtime listener in a background daemon thread.
        When a change is detected, sets a thread-safe pending flag instead
        of calling the callback directly — the app's main-thread timer picks
        it up and re-renders safely.

        The subscription auto-reconnects with exponential backoff.
        """
        self._change_callback = on_change

        if self._realtime_thread and self._realtime_thread.is_alive():
            return  # Already subscribed

        self._stop_event.clear()
        self._realtime_thread = threading.Thread(
            target=self._run_realtime_loop,
            name="supabase-realtime",
            daemon=True,
        )
        self._realtime_thread.start()

    def cancel_subscriptions(self):
        """Clean shutdown — call when the app logs out or exits."""
        self._stop_event.set()
        if self._realtime_thread:
            self._realtime_thread.join(timeout=5)

    # -- Thread-safe query methods for the main-thread checker ----------
    def check_realtime_pending(self) -> bool:
        """Returns True if a realtime event arrived since last check."""
        return self._realtime_pending.is_set()

    def clear_realtime_pending(self):
        """Call after processing a realtime event to reset the flag."""
        self._realtime_pending.clear()

    def last_realtime_time(self) -> float:
        """Timestamp (time.monotonic) of the most recent realtime event."""
        return self._last_realtime_ts

    # -- Internal: async listener loop running in a background thread ---
    def _run_realtime_loop(self):
        """Entry point for the background thread. Creates a fresh asyncio
        event loop and runs the realtime listener with reconnection."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._realtime_listener())
        finally:
            loop.close()

    async def _realtime_listener(self):
        """Subscribe to all relevant Postgres tables and forward changes
        to the pending flag. Reconnects with exponential backoff on error."""
        from supabase import create_client

        delay = RECONNECT_BASE_DELAY

        while not self._stop_event.is_set():
            try:
                # Create a *separate* async client for the realtime channel
                # (the sync client in self.client can't subscribe).
                async_client = create_client(self._url, self._key, is_async=True)
                channels = []

                def make_handler(table_name: str):
                    """Closure to capture the table name per channel."""
                    def _on_change(payload):
                        # Called from the realtime library's internal thread.
                        # We only signal the flag — no UI work here.
                        self._last_realtime_ts = time.monotonic()
                        self._realtime_pending.set()
                    return _on_change

                for table in REALTIME_TABLES:
                    channel = async_client.channel(f"table-{table}")
                    channel.on_postgres_changes(
                        "*",                     # listen to INSERT, UPDATE, DELETE
                        schema="public",
                        table=table,
                        callback=make_handler(table),
                    )
                    await channel.subscribe()
                    channels.append(channel)

                # Connected successfully — reset backoff
                delay = RECONNECT_BASE_DELAY

                # Keep alive until we're asked to stop
                while not self._stop_event.is_set():
                    await asyncio.sleep(1)

                # Clean unsubscribe
                for ch in channels:
                    try:
                        await ch.unsubscribe()
                    except Exception:
                        pass
                break  # Normal exit

            except Exception:
                # Connection or subscription failed — wait and retry
                if self._stop_event.is_set():
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_DELAY)