import random
import uuid
import datetime
import pandas as pd
from typing import List, Dict, Any

class SupplyChainDataGenerator:
    """
    Generates mock supply chain data for testing and demonstration purposes.
    Simulates a complex global supply chain with various tiers of suppliers,
    transportation modes, material types, and facility energy usage.
    """

    REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East", "Africa"]
    MATERIAL_TYPES = {
        "Raw": ["Steel", "Aluminum", "Plastic", "Copper", "Lithium"],
        "Component": ["Microchips", "Batteries", "Casings", "Screens", "Motors"],
        "Packaging": ["Cardboard", "Recycled Paper", "Bio-Plastic", "Styrofoam", "Wood"],
    }
    TRANSPORT_MODES = ["Air", "Sea", "Rail", "Road"]
    FACILITY_TYPES = ["Manufacturing", "Assembly", "Warehouse", "Distribution Center", "R&D"]

    def __init__(self, num_suppliers: int = 50, seed: int = 42):
        self.num_suppliers = num_suppliers
        self.seed = seed
        random.seed(self.seed)

    def generate_suppliers(self) -> List[Dict[str, Any]]:
        """Generates a list of supplier dictionaries with varied ESG metrics."""
        suppliers = []
        for i in range(self.num_suppliers):
            region = random.choice(self.REGIONS)
            tier = random.choices([1, 2, 3], weights=[0.2, 0.5, 0.3])[0]
            
            # ESG Score out of 100
            esg_score = random.randint(40, 95)
            compliance_status = "Compliant" if esg_score > 60 else "At Risk"
            
            supplier = {
                "supplier_id": f"SUP-{uuid.uuid4().hex[:6].upper()}",
                "name": f"Global {random.choice(['Tech', 'Materials', 'Logistics', 'Dynamics', 'Solutions'])} {i+1}",
                "region": region,
                "tier": tier,
                "esg_score": esg_score,
                "compliance_status": compliance_status,
                "renewable_energy_pct": round(random.uniform(5.0, 100.0), 2),
                "annual_capacity_tons": random.randint(1000, 50000),
                "is_active": random.choice([True, True, True, False])
            }
            suppliers.append(supplier)
        return suppliers

    def generate_shipments(self, suppliers: List[Dict[str, Any]], num_shipments: int = 500) -> List[Dict[str, Any]]:
        """Generates historical shipment data for the provided suppliers."""
        shipments = []
        start_date = datetime.date(2025, 1, 1)
        
        for _ in range(num_shipments):
            supplier = random.choice(suppliers)
            mat_category = random.choice(list(self.MATERIAL_TYPES.keys()))
            material = random.choice(self.MATERIAL_TYPES[mat_category])
            
            mode = random.choices(self.TRANSPORT_MODES, weights=[0.1, 0.5, 0.1, 0.3])[0]
            distance_km = random.randint(100, 15000)
            weight_tons = round(random.uniform(1.0, 500.0), 2)
            
            days_offset = random.randint(0, 365)
            ship_date = start_date + datetime.timedelta(days=days_offset)
            
            shipment = {
                "shipment_id": f"SHP-{uuid.uuid4().hex[:8].upper()}",
                "supplier_id": supplier["supplier_id"],
                "material_category": mat_category,
                "material_name": material,
                "transport_mode": mode,
                "distance_km": distance_km,
                "weight_tons": weight_tons,
                "date": ship_date.isoformat(),
                "cost_usd": round(weight_tons * random.uniform(50, 500), 2)
            }
            shipments.append(shipment)
        return shipments

    def generate_facilities(self, suppliers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates facility data associated with the suppliers."""
        facilities = []
        for supplier in suppliers:
            num_facilities_for_supplier = random.randint(1, 3)
            for _ in range(num_facilities_for_supplier):
                facility = {
                    "facility_id": f"FAC-{uuid.uuid4().hex[:6].upper()}",
                    "supplier_id": supplier["supplier_id"],
                    "facility_type": random.choice(self.FACILITY_TYPES),
                    "square_footage": random.randint(10000, 500000),
                    "annual_energy_mwh": round(random.uniform(500, 10000), 2),
                    "water_usage_k_liters": round(random.uniform(100, 5000), 2),
                    "waste_generated_tons": round(random.uniform(50, 2000), 2),
                    "waste_recycled_pct": round(random.uniform(10.0, 90.0), 2)
                }
                facilities.append(facility)
        return facilities

    def get_full_dataset(self) -> Dict[str, pd.DataFrame]:
        """Returns all mocked data as a dictionary of pandas DataFrames."""
        suppliers = self.generate_suppliers()
        shipments = self.generate_shipments(suppliers)
        facilities = self.generate_facilities(suppliers)
        
        return {
            "suppliers": pd.DataFrame(suppliers),
            "shipments": pd.DataFrame(shipments),
            "facilities": pd.DataFrame(facilities)
        }

if __name__ == "__main__":
    # Quick test array when running standalone
    generator = SupplyChainDataGenerator(num_suppliers=10)
    data = generator.get_full_dataset()
    print("Mock Dataset Generated:")
    print(f"Suppliers: {len(data['suppliers'])}")
    print(f"Shipments: {len(data['shipments'])}")
    print(f"Facilities: {len(data['facilities'])}")
    print(data['suppliers'].head())
