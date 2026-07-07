from typing import Optional, List
from models import BusinessDay
from backend.state import AppState


class BusinessDayError(Exception):
    pass


class BusinessDayService:
    def __init__(self, state: AppState):
        self.state = state

    def is_open(self) -> bool:
        return self.state.is_business_day_open()

    def current(self) -> Optional[BusinessDay]:
        return self.state.get_open_business_day()

    def history(self) -> List[BusinessDay]:
        return sorted(self.state.business_days, key=lambda d: d.opened_at, reverse=True)

    def open_day(self, opened_by: str, opening_note: str = "") -> BusinessDay:
        if self.is_open():
            raise BusinessDayError("A Business Day is already open.")
        return self.state.open_business_day(opened_by, opening_note)

    def close_day(self, closed_by: str, closing_note: str = "") -> BusinessDay:
        if not self.is_open():
            raise BusinessDayError("No Business Day is currently open.")
        return self.state.close_business_day(closed_by, closing_note)
