import uuid
from typing import Any, Dict
from datetime import datetime

class BaseFactory:
    """Abstract base factory for generating isolated, deterministic test data."""
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"{self._counter:04d}"

class UserFactory(BaseFactory):
    def build(self, **kwargs) -> Dict[str, Any]:
        uid = self._next_id()
        defaults = {
            "id": str(uuid.UUID(f"00000000-0000-0000-0000-{uid}00000000")),
            "username": f"ecouser_{uid}",
            "email": f"user_{uid}@ecobuddy.local",
            "carbon_footprint_goal": 2500.0,
            "created_at": datetime(2026, 1, 1, 12, 0, 0).isoformat(),
            "is_active": True
        }
        defaults.update(kwargs)
        return defaults

class CarbonLogFactory(BaseFactory):
    def build(self, **kwargs) -> Dict[str, Any]:
        uid = self._next_id()
        defaults = {
            "id": str(uuid.UUID(f"10000000-0000-0000-0000-{uid}00000000")),
            "user_id": str(uuid.UUID(f"00000000-0000-0000-0000-000100000000")),
            "category": "transportation",
            "co2_emissions_kg": 15.4,
            "logged_at": datetime(2026, 8, 22, 12, 0, 0).isoformat()
        }
        defaults.update(kwargs)
        return defaults
