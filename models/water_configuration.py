from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class WaterConfiguration:
    """The station's core commodity configuration.

    Water is NOT a product. It is the primary business of the application
    and deserves its own configuration. This model stores the per-litre
    economics and the default refill sizes offered to customers.

    Future expansion (treatment cost, electricity allocation, tank info,
    water production) is designed for by the `future` dict — new fields can
    be added there without a schema/model change.
    """
    business_id: str = ""
    cost_per_litre: float = 1.0
    selling_price_per_litre: float = 10.0
    refill_sizes: List[float] = field(default_factory=lambda: [5.0, 10.0, 20.0])
    custom_allowed: bool = True
    created_at: str = ""
    updated_at: str = ""

    # Future-proofing: treatment cost, electricity allocation, tank info,
    # water production, etc. can be stored here without a model change.
    future: Dict[str, Any] = field(default_factory=dict)

    def price_for(self, liters: float) -> float:
        """Selling price for a given number of litres."""
        return liters * self.selling_price_per_litre

    def cost_for(self, liters: float) -> float:
        """Cost of goods for a given number of litres."""
        return liters * self.cost_per_litre

    def profit_for(self, liters: float) -> float:
        """Profit for a given number of litres."""
        return self.price_for(liters) - self.cost_for(liters)