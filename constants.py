"""Business-rule constants. Deliberately free of Flet imports so this file
can be reused by a future backend/API layer untouched.
"""
from datetime import date, timedelta

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)

BODA_FEE = 20               # what the customer pays for boda delivery
BODA_RIDER_FEE = 50          # what the business pays the rider (a delivery expense)
INITIAL_CAPITAL = 150_000

CAPITAL_EXPENSE_CATEGORIES = ["Rent", "Utilities", "Repairs", "Stock Replenish", "Other"]
PAYMENT_METHODS = ["Cash", "M-Pesa"]
DELIVERY_METHODS = ["Walk-in", "Boda"]
PERIOD_LENGTHS = {"daily": 1, "weekly": 7, "monthly": 30}

# Water Refill pricing: customer brings their own container, only water leaves
# inventory (tracked via the meter, not the product stock table).
# New rule: 1L is bought at 1 sh and sold at 10 sh.
WATER_REFILL_PRICES = {5: 50, 10: 100, 20: 200}   # liters -> price (KES)

# Bulk delivery presets
BULK_DELIVERY_SIZES = [500, 1000]               # liters
TRANSPORT_FEE_DEFAULT = 300

# Rough liters-per-bottle used only to keep the water-meter "sold" tally
# consistent when a Bottle + Water sale happens (not a separate stock item).
BOTTLE_WATER_LITERS = {
    "5L Bottles": 5,
    "10L Bottles": 10,
    "20L Bottles": 20,
    "1L Sachets": 1,
}
