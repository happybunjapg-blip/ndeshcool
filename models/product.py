from dataclasses import dataclass, field
from typing import List
from .enums import ProductCategory


@dataclass
class Batch:
    """A single purchase batch, used for FIFO cost-of-goods calculations."""
    qty: float
    purchase_price: float
    date: str


@dataclass
class Product:
    name: str
    category: ProductCategory
    qty: float
    threshold: float
    selling_price: float
    bottle_price: float = 0.0
    cost: float = 0.0
    batches: List[Batch] = field(default_factory=list)

    def is_out(self) -> bool:
        return self.qty <= 0

    def is_low(self) -> bool:
        return not self.is_out() and self.qty <= self.threshold

    def status_label(self) -> str:
        if self.is_out():
            return "Out"
        if self.is_low():
            return "Low"
        return "In"
