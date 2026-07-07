from dataclasses import dataclass
from .enums import Role


@dataclass
class User:
    email: str
    name: str
    role: Role
