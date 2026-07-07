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
from datetime import datetime
from typing import List, Optional, Dict, Any

from models import Product, Batch, Customer, Transaction, TransactionType, ProductCategory, BusinessDay
from .repository import Repository

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


class SupabaseRepository(Repository):
    def __init__(self, url: str, key: str):
        if create_client is None:
            raise RuntimeError(
                "The `supabase` package isn't installed. Run: pip install supabase"
            )
        self.client: Client = create_client(url, key)
        self._change_callback = None

    # ---- Row <-> model mapping ------------------------------------------
    @staticmethod
    def _row_to_product(row: dict, batch_rows: List[dict]) -> Product:
        return Product(
            name=row["name"],
            category=ProductCategory(row["category"]),
            qty=row["qty"],
            threshold=row["threshold"],
            selling_price=row["selling_price"],
            bottle_price=row["bottle_price"],
            cost=row["cost"],
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

    # ---- Products ----------------------------------------------------
    def list_products(self) -> List[Product]:
        products = self.client.table("products").select("*").execute().data
        batches = self.client.table("product_batches").select("*").order("id").execute().data
        result = []
        for p in products:
            own_batches = [b for b in batches if b["product_name"] == p["name"]]
            result.append(self._row_to_product(p, own_batches))
        return result

    def get_product(self, name: str) -> Optional[Product]:
        rows = self.client.table("products").select("*").eq("name", name).execute().data
        if not rows:
            return None
        batches = self.client.table("product_batches").select("*").eq(
            "product_name", name).order("id").execute().data
        return self._row_to_product(rows[0], batches)

    def save_product(self, product: Product) -> None:
        self.client.table("products").update({
            "qty": product.qty, "threshold": product.threshold,
            "selling_price": product.selling_price, "bottle_price": product.bottle_price,
            "cost": product.cost, "updated_at": datetime.now().isoformat(),
        }).eq("name", product.name).execute()
        # Batches are the source of truth for FIFO -- rewrite them wholesale.
        # (Fine at this data volume; switch to targeted upserts if batch
        # counts grow into the thousands per product.)
        self.client.table("product_batches").delete().eq("product_name", product.name).execute()
        for b in product.batches:
            self.client.table("product_batches").insert({
                "product_name": product.name, "qty": b.qty,
                "purchase_price": b.purchase_price, "purchase_date": b.date,
            }).execute()

    # ---- Customers (credit customers only) ------------------------------
    def list_customers(self) -> List[Customer]:
        rows = self.client.table("customers").select("*").execute().data
        return [self._row_to_customer(r) for r in rows]

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        rows = self.client.table("customers").select("*").eq("id", customer_id).execute().data
        return self._row_to_customer(rows[0]) if rows else None

    def save_customer(self, customer: Customer) -> None:
        self.client.table("customers").update({
            "balance": customer.balance, "is_credit": customer.is_credit,
            "notes": customer.notes, "last_purchase": customer.last_purchase,
        }).eq("id", customer.id).execute()

    def add_customer(self, customer: Customer) -> None:
        self.client.table("customers").insert({
            "id": customer.id, "name": customer.name, "phone": customer.phone,
            "is_credit": customer.is_credit, "balance": customer.balance, "notes": customer.notes,
        }).execute()

    # ---- Transactions ----------------------------------------------------
    def list_transactions(self) -> List[Transaction]:
        rows = self.client.table("transactions").select("*").execute().data
        return [self._row_to_transaction(r) for r in rows]

    def add_transaction(self, transaction: Transaction) -> None:
        self.client.table("transactions").insert({
            "id": transaction.id, "type": transaction.type.value, "date": transaction.date,
            "time": transaction.time, "amount": transaction.amount, "profit": transaction.profit,
            "customer_id": transaction.customer_id, "details": transaction.details,
        }).execute()

    def next_transaction_id(self) -> str:
        # Postgres identity columns would be cleaner; kept as a readable id
        # scheme (T00001, T00002...) to match the in-memory backend's format.
        count = self.client.table("transactions").select("id", count="exact").execute().count or 0
        return f"T{count + 1:05d}"

    # ---- Expenses -----------------------------------------------------
    def list_daily_expenses(self) -> List[Dict[str, Any]]:
        rows = self.client.table("expenses").select("*").eq("is_capital", False).execute().data
        return rows

    def add_daily_expense(self, record: Dict[str, Any]) -> None:
        self.client.table("expenses").insert({**record, "is_capital": False}).execute()

    def list_capital_expenses(self) -> List[Dict[str, Any]]:
        rows = self.client.table("expenses").select("*").eq("is_capital", True).execute().data
        return rows

    def add_capital_expense(self, record: Dict[str, Any]) -> None:
        self.client.table("expenses").insert({**record, "is_capital": True}).execute()

    # ---- Timeline -----------------------------------------------------
    def list_timeline(self) -> List[Dict[str, Any]]:
        return self.client.table("timeline_events").select("*").execute().data

    def add_timeline_event(self, record: Dict[str, Any]) -> None:
        self.client.table("timeline_events").insert(record).execute()

    # ---- Water readings -------------------------------------------------
    def list_water_readings(self) -> List[Dict[str, Any]]:
        return self.client.table("water_readings").select("*").execute().data

    def add_water_reading(self, record: Dict[str, Any]) -> None:
        self.client.table("water_readings").upsert(record).execute()

    def upsert_today_water_reading(self, record: Dict[str, Any]) -> None:
        self.client.table("water_readings").upsert(record).execute()

    # ---- Business Day ----------------------------------------------------
    def get_open_business_day(self) -> Optional[BusinessDay]:
        rows = self.client.table("business_days").select("*").eq("status", "OPEN").execute().data
        return self._row_to_business_day(rows[0]) if rows else None

    def list_business_days(self) -> List[BusinessDay]:
        rows = self.client.table("business_days").select("*").order("opened_at", desc=True).execute().data
        return [self._row_to_business_day(r) for r in rows]

    def open_business_day(self, business_day: BusinessDay) -> None:
        # The partial unique index in supabase_schema.sql (one row with
        # status='OPEN') makes this safe even if two workers tap "Open" at
        # the same instant on different devices -- the second insert fails.
        self.client.table("business_days").insert({
            "id": business_day.id, "opened_at": business_day.opened_at,
            "opened_by": business_day.opened_by, "status": business_day.status,
            "opening_note": business_day.opening_note,
        }).execute()

    def close_business_day(self, business_day_id: str, closed_at: str,
                            closed_by: str, closing_note: str) -> None:
        self.client.table("business_days").update({
            "status": "CLOSED", "closed_at": closed_at,
            "closed_by": closed_by, "closing_note": closing_note,
        }).eq("id", business_day_id).execute()

    # ---- Realtime -----------------------------------------------------
    def subscribe(self, on_change) -> None:
        """Push updates: every device (worker phone, partner phone/tablet/
        desktop) gets notified the instant any tracked table changes, so
        `app.py` can refresh the current page's data automatically."""
        self._change_callback = on_change
        tables = ["products", "product_batches", "customers", "business_days",
                  "transactions", "expenses", "timeline_events", "water_readings"]
        channel = self.client.channel("aquaflow-realtime")
        for table in tables:
            channel.on_postgres_changes(
                event="*", schema="public", table=table,
                callback=lambda payload: self._change_callback and self._change_callback(),
            )
        channel.subscribe()
