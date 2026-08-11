from typing import Optional, List
from models import BusinessDay
from backend.state import AppState
from backend.repository import DuplicateBusinessDayError


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
        """Open (or, if the business already has one, simply return) the
        current Business Day.

        A Business Day belongs to the business, not to whoever is clicking
        the button -- an owner, co-owner, or another worker may have
        already opened one on a different device/session. So this always
        checks the authoritative server state first via
        state.sync_open_business_day() and reuses that day instead of
        attempting to INSERT a second OPEN row (which the
        one_open_business_day_per_business constraint would reject).

        A new day is only created when the authoritative check confirms
        none is currently open. The remaining edge case -- two clients
        both passing that check at nearly the same instant -- is a genuine
        database-level race, not something a client-side check alone can
        rule out. If it happens, DuplicateBusinessDayError is raised by the
        repository; we simply re-fetch the day that won the race and reuse
        it, since from the user's perspective the Business Day is open
        either way.
        """
        existing = self.state.sync_open_business_day()
        if existing:
            return existing

        try:
            return self.state.open_business_day(opened_by, opening_note)
        except DuplicateBusinessDayError:
            existing = self.state.sync_open_business_day()
            if existing:
                return existing
            # Unreachable in practice (the DB only raises this when a day
            # really is open), but fall back to the old error rather than
            # letting a None propagate.
            raise BusinessDayError("A Business Day is already open.")

    def close_day(self, closed_by: str, closing_note: str = "") -> BusinessDay:
        if not self.is_open():
            raise BusinessDayError("No Business Day is currently open.")
        return self.state.close_business_day(closed_by, closing_note)
