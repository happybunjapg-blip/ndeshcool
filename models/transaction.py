from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .enums import TransactionType


@dataclass
class Transaction:
    """A single business event: a sale, a payment, a delivery, or an expense.

    `amount` is always the cash figure relevant to the event (revenue for a
    sale, amount paid for a customer payment, cost for an expense).
    `profit` is 0 for anything that isn't a sale.
    `details` carries type-specific fields (product name, liters, driver, etc.)
    so this single model can represent every transaction type from the brief
    without a combinatorial explosion of dataclasses.
    """
    id: str
    type: TransactionType
    date: str
    time: str
    amount: float
    profit: float = 0.0
    customer_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
