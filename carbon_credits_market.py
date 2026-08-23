import uuid
import datetime
import random
from typing import List, Dict, Any, Optional

class CarbonCreditsMarketplace:
    """
    Manages the registry of verified carbon offset projects and allows users
    to purchase credits to neutralize their footprint.
    """
    
    def __init__(self):
        self.listed_projects = self._initialize_market()
        self.transactions_ledger = []
        
    def _initialize_market(self) -> List[Dict[str, Any]]:
        """Mock data for verified offset projects."""
        return [
            {
                "id": "PRJ-AMZ-001",
                "name": "Amazon Reforestation Project",
                "type": "Reforestation",
                "verifier": "Verra",
                "price_per_ton_usd": 15.50,
                "available_tons": 50000,
                "rating": 4.8
            },
            {
                "id": "PRJ-DAC-002",
                "name": "Direct Air Capture - Iceland",
                "type": "Technology",
                "verifier": "Gold Standard",
                "price_per_ton_usd": 120.00,
                "available_tons": 1000,
                "rating": 4.9
            },
            {
                "id": "PRJ-WND-003",
                "name": "Texas Wind Farm Expansion",
                "type": "Renewable Energy",
                "verifier": "Climate Action Reserve",
                "price_per_ton_usd": 8.00,
                "available_tons": 150000,
                "rating": 4.2
            },
            {
                "id": "PRJ-MTH-004",
                "name": "Methane Capture AgTech",
                "type": "Agriculture",
                "verifier": "Verra",
                "price_per_ton_usd": 22.00,
                "available_tons": 8000,
                "rating": 4.5
            }
        ]

    def get_available_projects(self) -> List[Dict]:
        """Returns all projects with available credits."""
        return [p for p in self.listed_projects if p["available_tons"] > 0]

    def purchase_credits(self, user_id: str, project_id: str, tons: float) -> Dict[str, Any]:
        """
        Executes a transaction to buy carbon credits.
        """
        project = next((p for p in self.listed_projects if p["id"] == project_id), None)
        
        if not project:
            return {"status": "error", "message": "Project not found"}
            
        if project["available_tons"] < tons:
            return {"status": "error", "message": "Not enough tons available"}
            
        total_cost = tons * project["price_per_ton_usd"]
        
        # Deduct availability
        project["available_tons"] -= tons
        
        # Log Transaction
        receipt = {
            "tx_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "user_id": user_id,
            "project_id": project_id,
            "tons_offset": tons,
            "total_paid_usd": total_cost,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.transactions_ledger.append(receipt)
        
        return {"status": "success", "receipt": receipt}

    def get_user_impact(self, user_id: str) -> Dict[str, float]:
        """Returns the total tons offset by the user."""
        user_txns = [t for t in self.transactions_ledger if t["user_id"] == user_id]
        total = sum(t["tons_offset"] for t in user_txns)
        spent = sum(t["total_paid_usd"] for t in user_txns)
        return {"total_offset_tons": total, "total_spent_usd": spent}
