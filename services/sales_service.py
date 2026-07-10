"""This is the heart of the business-logic redesign: instead of one generic
'sale', each real-world transaction type has its own method that enforces
the correct inventory side-effects. UI code should never mutate stock or
water readings directly -- it should call one of these methods.

Business Day gate: every write in this file now requires an OPEN Business
Day. This mirrors how the station actually operates -- nothing gets logged
before the till is opened for the day, and everything stops the moment it's
closed out.

Boda accounting fix: previously the boda fee was subtracted a second time
from `profit` even though it's already excluded via the separate rider
expense. That double-counted the -20 impact. Now: revenue includes the
+20 the customer pays, profit is computed from revenue minus cost of goods
only (the boda fee is real profit until the rider is paid), and a matching
-50 expense is logged automatically for the rider. Net effect across
revenue + profit + expenses works out to exactly -30, matching the brief.
"""
from datetime import datetime
from typing import Optional

from constants import WATER_REFILL_PRICES, BODA_FEE, BODA_RIDER_FEE, BOTTLE_WATER_LITERS
from models import TransactionType, ProductCategory, Transaction
from backend.state import AppState
from .inventory_service import InventoryService

WATER_BUY_PRICE_PER_LITER = 1.0
WATER_SELL_PRICE_PER_LITER = 10.0


class SalesError(Exception):
    pass


class SalesService:
    def __init__(self, state: AppState, inventory: InventoryService):
        self.state = state
        self.inventory = inventory

    # ---------------------------------------------------------------
    def _require_open_business_day(self):
        if not self.state.is_business_day_open():
            raise SalesError("Open a Business Day before recording transactions.")

    def _today_water_reading(self) -> dict:
        """Get (or create) today's water-meter row so 'sold' tallies land
        somewhere even if the worker hasn't logged a meter reading yet."""
        today = datetime.now().date().isoformat()
        row = next((r for r in self.state.water_readings if r["date"] == today), None)
        if not row:
            row = {"date": today, "initial": 0, "final": 0, "cleaning": 0, "sold_water": 0}
            self.state.water_readings.append(row)
        return row

    def _persist_water_reading(self, reading: dict):
        self.state.repo.upsert_today_water_reading(reading)

    def _record(self, tx_type: TransactionType, amount: float, profit: float,
                details: dict, customer_id: Optional[str] = None) -> Transaction:
        now = datetime.now()
        transaction = Transaction(
            id=self.state.next_transaction_id(),
            type=tx_type,
            date=now.date().isoformat(),
            time=now.strftime("%H:%M"),
            amount=amount,
            profit=profit,
            customer_id=customer_id,
            details=details,
        )
        self.state.repo.add_transaction(transaction)
        self.state.transactions.append(transaction)
        if customer_id:
            customer = self.state.get_customer(customer_id)
            if customer:
                customer.record_history(transaction.id, tx_type.value, now.isoformat())
                self.state.repo.save_customer(customer)
        return transaction

    def _charge_rider_fee(self):
        """The business's side of a boda delivery: KES 50 out to the rider,
        logged as a delivery expense so it correctly reduces net profit."""
        self.record_expense("Boda rider payment", BODA_RIDER_FEE, is_capital=False, category="Delivery")

    # ---------------------------------------------------------------
    # 1. Water Refill -- customer's own container. Only the water resource
    #    (tracked via the meter) decreases. Bottle/product stock is untouched.
    # ---------------------------------------------------------------
    def record_water_refill(self, liters: float, payment: str, boda: bool = False,
                             customer_id: Optional[str] = None, on_credit: bool = False):
        self._require_open_business_day()
        if liters <= 0:
            raise SalesError("Refill amount must be positive.")
        if liters in WATER_REFILL_PRICES:
            price = WATER_REFILL_PRICES[liters]
        else:
            price = liters * WATER_SELL_PRICE_PER_LITER
        boda_fee = BODA_FEE if boda else 0
        revenue = price + boda_fee
        profit = revenue - (liters * WATER_BUY_PRICE_PER_LITER)
        reading = self._today_water_reading()
        reading["sold_water"] += liters
        self._persist_water_reading(reading)
        tx = self._record(
            TransactionType.WATER_REFILL, revenue, profit,
            {"liters": liters, "payment": payment, "boda": boda, "on_credit": on_credit},
            customer_id=customer_id,
        )
        if on_credit and customer_id:
            self._add_to_balance(customer_id, revenue)
        if boda:
            self._charge_rider_fee()
        self.state.log_timeline(f"Water Refill — {liters}L", "sale", f"-{liters}L", reading["sold_water"])
        return tx

    # ---------------------------------------------------------------
    # 2. Product Sale -- accessory only (caps, taps, pumps, stands...).
    #    Product stock decreases. Water is never touched.
    # ---------------------------------------------------------------
    def record_product_sale(self, product_name: str, qty: float, payment: str,
                             customer_id: Optional[str] = None, on_credit: bool = False):
        self._require_open_business_day()
        product = self.state.get_product(product_name)
        if not product:
            raise SalesError("Product not found.")
        if product.category != ProductCategory.ACCESSORY:
            raise SalesError(f"{product_name} is not an accessory product.")
        if qty > product.qty:
            raise SalesError(f"Only {product.qty:g} left.")
        cost = self.inventory.fifo_deduct(product_name, qty)
        revenue = qty * product.selling_price
        profit = revenue - cost
        tx = self._record(
            TransactionType.PRODUCT_SALE, revenue, profit,
            {"product": product_name, "qty": qty, "payment": payment, "on_credit": on_credit},
            customer_id=customer_id,
        )
        if on_credit and customer_id:
            self._add_to_balance(customer_id, revenue)
        self.state.log_timeline(f"Sale — {product_name}", "sale", f"-{qty:g}", product.qty)
        return tx

    # ---------------------------------------------------------------
    # 3. Bottle + Water Sale -- a brand-new bottle sold already filled.
    #    Bottle stock decreases AND the water tally decreases.
    # ---------------------------------------------------------------
    def record_bottle_water_sale(self, product_name: str, qty: float, payment: str,
                                  boda: bool = False, customer_id: Optional[str] = None,
                                  on_credit: bool = False):
        self._require_open_business_day()
        product = self.state.get_product(product_name)
        if not product:
            raise SalesError("Product not found.")
        if product.category != ProductCategory.BOTTLE_WATER:
            raise SalesError(f"{product_name} is not a bottle+water product.")
        if qty > product.qty:
            raise SalesError(f"Only {product.qty:g} left.")
        cost = self.inventory.fifo_deduct(product_name, qty)
        boda_fee = BODA_FEE if boda else 0
        revenue = qty * product.selling_price + boda_fee
        # Profit = Selling Price - FIFO Cost. The boda fee is real revenue
        # until the rider is paid -- that -20/-50 split is handled entirely
        # by _charge_rider_fee() below, not by subtracting it here too.
        profit = revenue - cost
        liters_each = BOTTLE_WATER_LITERS.get(product_name, 0)
        reading = self._today_water_reading()
        reading["sold_water"] += liters_each * qty
        self._persist_water_reading(reading)
        tx = self._record(
            TransactionType.BOTTLE_WATER_SALE, revenue, profit,
            {"product": product_name, "qty": qty, "payment": payment, "boda": boda, "on_credit": on_credit},
            customer_id=customer_id,
        )
        if on_credit and customer_id:
            self._add_to_balance(customer_id, revenue)
        if boda:
            self._charge_rider_fee()
        self.state.log_timeline(f"Sale — {product_name} (filled)", "sale", f"-{qty:g}", product.qty)
        return tx

    # ---------------------------------------------------------------
    # 4. Bulk Water Delivery -- large volume, may carry a transport fee,
    #    assigned to a driver/worker, tracked with a delivery status.
    # ---------------------------------------------------------------
    def record_bulk_delivery(self, liters: float, transport_fee: float, driver: str,
                              customer_id: Optional[str] = None, status: str = "Pending",
                              on_credit: bool = False):
        self._require_open_business_day()
        base_price_per_liter = 0.12  # simple flat bulk rate; tune per business
        revenue = liters * base_price_per_liter + transport_fee
        reading = self._today_water_reading()
        reading["sold_water"] += liters
        self._persist_water_reading(reading)
        tx = self._record(
            TransactionType.BULK_DELIVERY, revenue, revenue,
            {"liters": liters, "transport_fee": transport_fee, "driver": driver,
             "status": status, "on_credit": on_credit},
            customer_id=customer_id,
        )
        if on_credit and customer_id:
            self._add_to_balance(customer_id, revenue)
        self.state.log_timeline(f"Bulk Delivery — {liters:g}L to driver {driver}", "delivery",
                                 f"-{liters:g}L", reading["sold_water"])
        return tx

    # ---------------------------------------------------------------
    # 5. Meter Reading — initial + final from the worker, cleaning
    #    calculated automatically from what was actually sold.
    # ---------------------------------------------------------------
    def record_meter_reading(self, initial: float, final: float):
        """Record today's water meter reading.

        cleaning is NOT entered by the worker — it's derived:
            total_processed = final - initial
            cleaning = total_processed - sold_water

        ``sold_water`` comes from the individual refill / bottle /
        bulk-delivery transactions already recorded via SalesService
        (never duplicated here).
        """
        self._require_open_business_day()
        if final <= initial:
            raise SalesError("Final reading must be greater than initial.")
        reading = self._today_water_reading()
        total_processed = final - initial
        cleaning = total_processed - reading["sold_water"]
        reading["initial"] = initial
        reading["final"] = final
        reading["cleaning"] = max(0.0, cleaning)
        self._persist_water_reading(reading)
        self.state.log_timeline(
            f"Meter reading — {initial}L → {final}L (cleaning {reading['cleaning']:.1f}L, sold {reading['sold_water']:.1f}L)",
            "restock", f"{reading['sold_water']:.1f}L sold", final,
        )

    # ---------------------------------------------------------------
    # 6. Customer Payment -- NOT a sale. Reduces an existing debt.
    # ---------------------------------------------------------------
    def record_customer_payment(self, customer_id: str, amount: float):
        self._require_open_business_day()
        customer = self.state.get_customer(customer_id)
        if not customer:
            raise SalesError("Customer not found.")
        if amount <= 0:
            raise SalesError("Payment amount must be positive.")
        customer.balance = max(0.0, customer.balance - amount)
        self.state.repo.save_customer(customer)
        tx = self._record(
            TransactionType.CUSTOMER_PAYMENT, amount, 0.0,
            {"note": "Debt payment"}, customer_id=customer_id,
        )
        self.state.log_timeline(f"Payment received — {customer.name}", "payment", f"KES {amount:,.0f}", 0)
        return tx

    def _add_to_balance(self, customer_id: str, amount: float):
        customer = self.state.get_customer(customer_id)
        if customer:
            customer.balance += amount
            customer.is_credit = True
            self.state.repo.save_customer(customer)

    # ---------------------------------------------------------------
    # 7. Expenses -- affect profit, are never a sale.
    # ---------------------------------------------------------------
    def record_expense(self, description: str, amount: float, is_capital: bool = False,
                        category: str = "Other"):
        if not is_capital:
            # Daily/operational expenses (fuel, boda rider, small repairs)
            # are logged by workers during their shift -- gate them the same
            # way sales are gated. Capital expenses (rent, new equipment)
            # are a partner admin action and aren't tied to a shift.
            self._require_open_business_day()
        now = datetime.now()
        record = {
            "description": description,
            "amount": amount,
            "category": category,
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M"),
        }
        if is_capital:
            self.state.repo.add_capital_expense(record)
            self.state.capital_expenses.append(record)
        else:
            self.state.repo.add_daily_expense(record)
            self.state.daily_expenses.append(record)
        self.state.log_timeline(f"Expense — {description}", "expense", f"-KES {amount:,.0f}", 0)
        return record
