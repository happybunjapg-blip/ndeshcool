from typing import List
from models import WaterConfiguration
from backend.state import AppState


class WaterConfigService:
    """Business logic for the station's Water Configuration — the core
    commodity economics (cost/selling per litre, refill sizes)."""

    def __init__(self, state: AppState):
        self.state = state

    def get(self) -> WaterConfiguration:
        return self.state.get_water_config_or_default()

    def save(self, config: WaterConfiguration) -> WaterConfiguration:
        return self.state.save_water_config(config)

    def refill_sizes(self) -> List[float]:
        return self.state.get_water_config_or_default().refill_sizes

    @property
    def cost_per_litre(self) -> float:
        return self.state.get_water_config_or_default().cost_per_litre

    @property
    def selling_price_per_litre(self) -> float:
        return self.state.get_water_config_or_default().selling_price_per_litre