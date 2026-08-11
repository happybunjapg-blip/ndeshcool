from dataclasses import dataclass, field
from typing import List
from uuid import uuid4
from .enums import ProductCategory


@dataclass
class Batch:
    """A single purchase batch, used for FIFO cost-of-goods calculations."""
    qty: float
    purchase_price: float
    date: str


@dataclass
class Product:
    """A sellable product owned by a business.

    V1 Product Setup fields (managed by the Product Management page):
        id              – unique product identifier
        business_id     – owning business (all queries are scoped to this)
        name            – display name
        selling_price   – price in KES
        track_inventory – whether this product participates in the existing
                          inventory/FIFO system
        active          – archived (False) products are hidden from sales
        created_at      – row creation time
        updated_at      – last modification time

    Inventory-architecture fields below are PRESERVED unchanged (category,
    qty, threshold, buying_price, batches) so the existing FIFO/inventory
    system keeps working exactly as before. They are not exposed by the
    Product Management UI.
    """
    name: str
    selling_price: float
    id: str = field(default_factory=lambda: f"P-{uuid4().hex[:8]}")
    business_id: str = ""
    track_inventory: bool = True
    active: bool = True
    created_at: str = ""
    updated_at: str = ""

    # Existing inventory architecture (unchanged, not in Product Setup UI)
    category: ProductCategory = ProductCategory.ACCESSORY
    qty: float = 0.0
    threshold: float = 0.0
    buying_price: float = 0.0
    batches: List[Batch] = field(default_factory=list)

    # Catalog architecture: opening stock (the stock level when the product
    # was first configured). Backfilled to current qty during migration.
    opening_stock: float = 0.0

    # ---- Semantic aliases (Catalog naming) ---------------------------
    # These map the Catalog vocabulary onto the existing inventory fields
    # so the rest of the app (FIFO, stock cards, analytics) keeps working
    # unchanged while the UI reads/writes the more descriptive names.
    @property
    def current_stock(self) -> float:
        return self.qty

    @current_stock.setter
    def current_stock(self, value: float) -> None:
        self.qty = value

    @property
    def low_stock_level(self) -> float:
        return self.threshold

    @low_stock_level.setter
    def low_stock_level(self, value: float) -> None:
        self.threshold = value

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