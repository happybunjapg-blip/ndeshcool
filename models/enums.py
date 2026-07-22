"""Domain-wide enumerations.

Kept dependency-free (no Flet imports) so the model layer can be reused
by a future backend/API without dragging in UI code.
"""
from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    WORKER = "worker"


class ProductCategory(str, Enum):
    """How a stock item behaves in inventory rules.

    BOTTLE_WATER -> a bottle sold already filled with water (e.g. "20L Bottles").
                      Selling one reduces bottle stock AND counts as water sold.
    ACCESSORY    -> a pure product with no water component (caps, taps, pumps).
                      Selling one only reduces its own stock.
    """
    BOTTLE_WATER = "bottle_water"
    ACCESSORY = "accessory"


class TransactionType(str, Enum):
    WATER_REFILL = "water_refill"          # customer's own container, water only
    PRODUCT_SALE = "product_sale"          # accessory, no water
    BOTTLE_WATER_SALE = "bottle_water_sale"  # new bottle + water together
    BULK_DELIVERY = "bulk_delivery"        # large volume delivered to a customer
    CUSTOMER_PAYMENT = "customer_payment"  # settling an existing debt, not a sale
    EXPENSE = "expense"                    # operational or capital cost


class DeliveryStatus(str, Enum):
    PENDING = "Pending"
    IN_TRANSIT = "In Transit"
    DELIVERED = "Delivered"


class PaymentMethod(str, Enum):
    CASH = "Cash"
    MPESA = "M-Pesa"
    CREDIT = "Credit"