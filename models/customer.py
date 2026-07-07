from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Customer:
    id: str
    name: str
    phone: str = ""
    is_credit: bool = False
    balance: float = 0.0          # outstanding amount owed to the business
    notes: str = ""
    last_purchase: Optional[str] = None
    history: List[str] = field(default_factory=list)  # transaction ids

    def record_history(self, transaction_id: str, note: str, when: str):
        self.history.append(transaction_id)
        self.last_purchase = when
