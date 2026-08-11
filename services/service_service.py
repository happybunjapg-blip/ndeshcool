from typing import List, Optional
from models import Service
from backend.state import AppState


class ServiceService:
    """Business logic for Services — catalog entries with cost + selling
    price that do NOT track stock."""

    def __init__(self, state: AppState):
        self.state = state

    def list_services(self) -> List[Service]:
        return self.state.services

    def list_active_services(self) -> List[Service]:
        return [s for s in self.state.services if s.active]

    def get(self, service_id: str) -> Optional[Service]:
        return self.state.get_service_by_id(service_id)

    def add_service(self, name: str, cost: float, selling_price: float) -> Service:
        service = Service(
            name=name,
            cost=cost,
            selling_price=selling_price,
            active=True,
        )
        return self.state.add_service(service)

    def update_service(self, service: Service) -> Service:
        return self.state.update_service(service)

    def set_active(self, service_id: str, active: bool) -> None:
        self.state.set_service_active(service_id, active)