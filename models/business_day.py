from dataclasses import dataclass
from typing import Optional
from .enums import DeliveryStatus  # re-export not needed, kept for import symmetry


class BusinessDayStatus:
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class BusinessDay:
    """Only one BusinessDay may be OPEN system-wide at any time. Workers
    cannot record sales/expenses/payments unless one is open. This models
    a real water station's operating rhythm: open the till in the morning,
    close it out at night with a summary.
    """
    id: str
    opened_at: str            # ISO datetime
    opened_by: str            # user email
    status: str = BusinessDayStatus.OPEN
    opening_note: str = ""
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    closing_note: str = ""
