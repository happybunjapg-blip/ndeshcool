from typing import List
from models import Product
from backend.state import AppState


class InventoryService:
    def __init__(self, state: AppState):
        self.state = state

    def all_products(self) -> List[Product]:
        return self.state.products

    def low_stock(self) -> List[Product]:
        return [p for p in self.state.products if p.is_low() or p.is_out()]

    def fifo_deduct(self, product_name: str, qty: float) -> float:
        """Deduct qty from oldest batches first. Returns total cost of goods sold."""
        product = self.state.get_product(product_name)
        if not product:
            return 0.0
        remaining = qty
        total_cost = 0.0
        while remaining > 0 and product.batches:
            batch = product.batches[0]
            take = min(remaining, batch.qty)
            total_cost += take * batch.purchase_price
            batch.qty -= take
            remaining -= take
            if batch.qty <= 0:
                product.batches.pop(0)
        product.qty -= qty
        self.state.repo.save_product(product)
        return total_cost

    def restock(self, product_name: str, qty: float, purchase_price: float):
        from models import Batch
        from constants import TODAY
        product = self.state.get_product(product_name)
        if not product:
            return
        product.batches.append(Batch(qty, purchase_price, TODAY.isoformat()))
        product.qty += qty
        self.state.repo.save_product(product)
        self.state.log_timeline(f"Restock — {product_name}", "restock", f"+{qty:g}", product.qty)
