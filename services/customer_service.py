from typing import List, Optional
from models import Customer
from backend.state import AppState


class CustomerService:
    def __init__(self, state: AppState):
        self.state = state

    def list_customers(self) -> List[Customer]:
        return self.state.customers

    def get(self, customer_id: str) -> Optional[Customer]:
        return self.state.get_customer(customer_id)

    def add_customer(self, name: str, phone: str = "", notes: str = "") -> Customer:
        """Creates a CREDIT customer. Cash customers are never stored --
        there's nothing to track for them (no balance, no history worth
        keeping), matching the business rule that the customers table only
        ever holds people who buy on credit."""
        new_id = f"C{len(self.state.customers) + 1:03d}"
        customer = Customer(id=new_id, name=name, phone=phone, is_credit=True, notes=notes)
        self.state.repo.add_customer(customer)
        self.state.customers.append(customer)
        return customer

    def customers_with_balance(self) -> List[Customer]:
        return [c for c in self.state.customers if c.balance > 0]

    def total_outstanding(self) -> float:
        return sum(c.balance for c in self.state.customers)
