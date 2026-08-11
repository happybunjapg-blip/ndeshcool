from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Service:
    """A sellable service offered by the station.

    Services (Delivery, Installation, Cleaning) have a cost and a selling
    price but do NOT track stock — they are not physical inventory.
    """
    name: str
    selling_price: float
    cost: float = 0.0
    id: str = field(default_factory=lambda: f"S-{uuid4().hex[:8]}")
    business_id: str = ""
    active: bool = True
    created_at: str = ""
    updated_at: str = ""

    @property
    def profit(self) -> float:
        return self.selling_price - self.cost