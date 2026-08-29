"""Simulated Eco Data Generator for Testing the Import Pipeline.

Generates realistic CSV and JSON datasets spanning multiple years,
including deliberately injected malformations, duplicates, and outliers
so users can test the resilience of the Import Hub.
"""

import csv
import json
import random
from datetime import datetime, timedelta
import io

class EcoDataSimulator:
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        
        self.categories = ["Energy", "Transport", "Waste", "Water", "Food", "Shopping"]
        self.activities = {
            "Energy": ["Home Electricity", "Natural Gas", "Propane Heating", "Solar Generation"],
            "Transport": ["Commute (Car)", "Flight (Economy)", "Train Travel", "Uber Ride"],
            "Waste": ["Municipal Solid Waste", "Recycling", "Compostable Organics", "E-Waste"],
            "Water": ["Indoor Water Use", "Lawn Irrigation", "Pool Maintenance"],
            "Food": ["Beef Meal", "Vegetarian Diet", "Vegan Groceries", "Restaurant Dining"],
            "Shopping": ["Clothing Purchase", "Electronics", "Furniture", "Amazon Delivery"]
        }
        self.units = {
            "Energy": ["kWh", "therms", "joules"],
            "Transport": ["miles", "km"],
            "Waste": ["lbs", "kg", "tons"],
            "Water": ["gallons", "liters"],
            "Food": ["meals", "kg"],
            "Shopping": ["items", "$"]
        }
        
    def generate_records(self, count: int, malformation_rate: float = 0.05) -> list[dict]:
        """Generate a specified number of synthetic records."""
        records = []
        
        start_date = datetime(2023, 1, 1)
        
        for i in range(count):
            cat = random.choice(self.categories)
            act = random.choice(self.activities[cat])
            unit = random.choice(self.units[cat])
            
            # Base value
            value = round(random.uniform(1.0, 500.0), 2)
            
            # Timestamp progression
            current_date = start_date + timedelta(days=random.randint(0, 1000))
            date_str = current_date.strftime("%Y-%m-%d")
            
            record = {
                "activity_date": date_str,
                "category": cat,
                "activity": act,
                "value": value,
                "unit": unit
            }
            
            # Inject Emulated Malformations based on rate
            if random.random() < malformation_rate:
                malform_type = random.choice(["bad_date", "string_value", "missing_unit", "missing_cat", "outlier"])
                
                if malform_type == "bad_date":
                    record["activity_date"] = "Not a date"
                elif malform_type == "string_value":
                    record["value"] = "One Hundred"
                elif malform_type == "missing_unit":
                    del record["unit"]
                elif malform_type == "missing_cat":
                    del record["category"]
                elif malform_type == "outlier":
                    record["value"] = value * 10000.0 # Anomalous multiplier
                    
            records.append(record)
            
            # Inject Exact Duplicates
            if random.random() < (malformation_rate * 0.5):
                records.append(record.copy())
                
        # Shuffle everything
        random.shuffle(records)
        return records
        
    def generate_csv_bytes(self, records: list[dict]) -> bytes:
        """Convert records to CSV bytes payload."""
        if not records:
            return b""
            
        output = io.StringIO()
        # Some records might have missing keys due to malformations, so get all possible keys
        all_keys = set()
        for r in records:
            all_keys.update(r.keys())
            
        writer = csv.DictWriter(output, fieldnames=list(all_keys))
        writer.writeheader()
        
        for r in records:
            writer.writerow(r)
            
        return output.getvalue().encode('utf-8')
        
    def generate_json_bytes(self, records: list[dict]) -> bytes:
        """Convert records to JSON bytes payload."""
        return json.dumps(records, indent=2).encode('utf-8')

def generate_large_test_dataset(format_type: str = "csv", count: int = 1000) -> bytes:
    """Convenience wrapper for Streamlit UI generation."""
    sim = EcoDataSimulator()
    records = sim.generate_records(count)
    if format_type.lower() == "csv":
        return sim.generate_csv_bytes(records)
    return sim.generate_json_bytes(records)
