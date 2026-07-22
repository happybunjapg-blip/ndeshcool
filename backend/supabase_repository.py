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
        super().__init__()
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

    def _apply_business_filter(self, query):
        """Append business_id filter to a query if set."""
        if self._business_id:
            return query.eq("business_id", self._business_id)
        return query

    def _safe_select(self, table: str):
        """Create a select query scoped to the current business."""
        query = self.client.table(table).select("*")
        return self._apply_business_filter(query)

    def _safe_execute(self, table_name: str, operation: str):
        try:
            return self._safe_select(table_name).execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def _safe_execute_single(self, table_name: str, name: str, field: str):
        try:
            query = self.client.table(table_name).select("*").eq(field, name)
            return self._apply_business_filter(query).execute().data
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
            query = self._safe_select("products")
            products = query.execute().data
            batch_query = self.client.table("product_batches").select("*").order("id")
            if self._business_id:
                batch_query = batch_query.eq("business_id", self._business_id)
            batches = batch_query.execute().data
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
            query = self.client.table("products").select("*").eq("name", name)
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
            if not rows:
                return None
            batch_query = self.client.table("product_batches").select("*").eq(
                "product_name", name).order("id")
            if self._business_id:
                batch_query = batch_query.eq("business_id", self._business_id)
            batches = batch_query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_product(rows[0], batches)

    def save_product(self, product: Product) -> None:
        update_data = {
            "qty": product.qty, "threshold": product.threshold,
            "selling_price": product.selling_price,
            "buying_price": product.buying_price, "updated_at": datetime.now().isoformat(),
        }
        query = self.client.table("products").update(update_data).eq("name", product.name)
        if self._business_id:
            query = query.eq("business_id", self._business_id)
        self._safe_execute_operation(query)

        # Batches are the source of truth for FIFO -- rewrite them wholesale.
        delete_query = self.client.table("product_batches").delete().eq("product_name", product.name)
        if self._business_id:
            delete_query = delete_query.eq("business_id", self._business_id)
        self._safe_execute_operation(delete_query)
        if product.batches:
            self._safe_execute_operation(self.client.table("product_batches").insert([
                {
                    "product_name": product.name, "business_id": self._business_id or "",
                    "qty": b.qty,
                    "purchase_price": b.purchase_price, "purchase_date": b.date,
                }
                for b in product.batches
            ]))

    # ---- Customers (credit customers only) ------------------------------
    def list_customers(self) -> List[Customer]:
        try:
            query = self._safe_select("customers")
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._row_to_customer(r) for r in rows]

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        try:
            query = self.client.table("customers").select("*").eq("id", customer_id)
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_customer(rows[0]) if rows else None

    def save_customer(self, customer: Customer) -> None:
        query = self.client.table("customers").update({
            "balance": customer.balance, "is_credit": customer.is_credit,
            "notes": customer.notes, "last_purchase": customer.last_purchase,
        }).eq("id", customer.id)
        if self._business_id:
            query = query.eq("business_id", self._business_id)
        self._safe_execute_operation(query)

    def add_customer(self, customer: Customer) -> None:
        self._safe_execute_operation(self.client.table("customers").insert({
            "id": customer.id, "name": customer.name, "phone": customer.phone,
            "is_credit": customer.is_credit, "balance": customer.balance,
            "notes": customer.notes, "business_id": self._business_id or "",
        }))

    # ---- Transactions ----------------------------------------------------
    def list_transactions(self) -> List[Transaction]:
        try:
            query = self._safe_select("transactions")
            rows = query.execute().data
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
            "business_id": self._business_id or "",
        }))

    def next_transaction_id(self) -> str:
        count = self.client.table("transactions").select("id", count="exact").execute().count or 0
        return f"T{count + 1:05d}"

    # ---- Expenses -----------------------------------------------------
    def list_daily_expenses(self) -> List[Dict[str, Any]]:
        try:
            query = self.client.table("expenses").select("*").eq("is_capital", False)
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return rows

    def add_daily_expense(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("expenses").insert({
            **record, "is_capital": False, "business_id": self._business_id or "",
        }))

    def list_capital_expenses(self) -> List[Dict[str, Any]]:
        try:
            query = self.client.table("expenses").select("*").eq("is_capital", True)
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return rows

    def add_capital_expense(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("expenses").insert({
            **record, "is_capital": True, "business_id": self._business_id or "",
        }))

    # ---- Timeline -----------------------------------------------------
    def list_timeline(self) -> List[Dict[str, Any]]:
        try:
            query = self._safe_select("timeline_events")
            return query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def add_timeline_event(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("timeline_events").insert({
            **record, "business_id": self._business_id or "",
        }))

    # ---- Water readings -------------------------------------------------
    def list_water_readings(self) -> List[Dict[str, Any]]:
        try:
            query = self._safe_select("water_readings")
            return query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise

    def add_water_reading(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("water_readings").upsert({
            **record, "business_id": self._business_id or "",
        }))

    def upsert_today_water_reading(self, record: Dict[str, Any]) -> None:
        self._safe_execute_operation(self.client.table("water_readings").upsert({
            **record, "business_id": self._business_id or "",
        }))

    # ---- Business Day ----------------------------------------------------
    def get_open_business_day(self) -> Optional[BusinessDay]:
        try:
            query = self.client.table("business_days").select("*").eq("status", "OPEN")
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return None
            raise
        return self._row_to_business_day(rows[0]) if rows else None

    def list_business_days(self) -> List[BusinessDay]:
        try:
            query = self.client.table("business_days").select("*").order("opened_at", desc=True)
            if self._business_id:
                query = query.eq("business_id", self._business_id)
            rows = query.execute().data
        except APIError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._row_to_business_day(r) for r in rows]

    def open_business_day(self, business_day: BusinessDay) -> None:
        self._safe_execute_operation(self.client.table("business_days").insert({
            "id": business_day.id, "opened_at": business_day.opened_at,
            "opened_by": business_day.opened_by, "status": business_day.status,
            "opening_note": business_day.opening_note,
            "business_id": self._business_id or "",
        }))

    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None:
        query = self.client.table("business_days").update({
            "status": "CLOSED", "closed_at": closed_at,
            "closed_by": closed_by, "closing_note": closing_note,
        }).eq("id", business_day_id)
        if self._business_id:
            query = query.eq("business_id", self._business_id)
        self._safe_execute_operation(query)

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
                async_client = create_client(self._url, self._key, is_async=True)
                channels = []

                def make_handler(table_name: str):
                    def _on_change(payload):
                        self._last_realtime_ts = time.monotonic()
                        self._realtime_pending.set()
                    return _on_change

                for table in REALTIME_TABLES:
                    channel = async_client.channel(f"table-{table}")
                    channel.on_postgres_changes(
                        "*",
                        schema="public",
                        table=table,
                        callback=make_handler(table),
                    )
                    await channel.subscribe()
                    channels.append(channel)

                delay = RECONNECT_BASE_DELAY

                while not self._stop_event.is_set():
                    await asyncio.sleep(1)

                for ch in channels:
                    try:
                        await ch.unsubscribe()
                    except Exception:
                        pass
                break

            except Exception:
                if self._stop_event.is_set():
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_DELAY)