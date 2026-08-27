"""External API Connectors for Data Import Hub.

Provides modular connectors to simulate fetching sustainability data
from external 3rd-party services (e.g., Smart Meters, EV APIs, 
Aviation trackers) and standardizing them into the internal EcoBuddy
schema for downstream cleaning and analytics.
"""

import time
import random
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BaseConnector:
    """Base class for all external API connectors."""
    
    def __init__(self, api_key: str, name: str):
        self.api_key = api_key
        self.name = name
        self.is_connected = False
        
    def authenticate(self) -> bool:
        """Authenticate with the 3rd party service."""
        # Simulated auth
        time.sleep(0.5)
        if len(self.api_key) > 5:
            self.is_connected = True
            return True
        return False
        
    def fetch_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch raw data from the provider. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement fetch_data")
        
    def map_to_standard_schema(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map raw provider schema to EcoBuddy Standard Schema."""
        raise NotImplementedError("Subclasses must implement map_to_standard_schema")
        
    def sync(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Full pipeline: fetch and map."""
        if not self.is_connected:
            if not self.authenticate():
                logger.error(f"Failed to authenticate connector {self.name}")
                return []
                
        raw = self.fetch_data(start_date, end_date)
        return self.map_to_standard_schema(raw)


class TeslaAPIConnector(BaseConnector):
    """Simulated connector for Tesla EV telemetry data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "Tesla API")
        
    def fetch_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Simulate fetching charging and driving history."""
        # Generating dummy telemetry
        raw = []
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            delta = end_dt - start_dt
            
            for i in range(delta.days + 1):
                current = start_dt + timedelta(days=i)
                # 60% chance of driving that day
                if random.random() > 0.4:
                    raw.append({
                        "timestamp": current.isoformat() + "Z",
                        "event_type": "drive",
                        "distance_mi": round(random.uniform(5.0, 60.0), 1),
                        "energy_used_kwh": round(random.uniform(2.0, 15.0), 1)
                    })
                # 30% chance of charging
                if random.random() > 0.7:
                    raw.append({
                        "timestamp": current.isoformat() + "Z",
                        "event_type": "charge",
                        "energy_added_kwh": round(random.uniform(10.0, 50.0), 1),
                        "cost_usd": round(random.uniform(2.0, 10.0), 2)
                    })
            return raw
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD")
            return []

    def map_to_standard_schema(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped = []
        for r in raw_data:
            dt_str = r["timestamp"][:10] # extract YYYY-MM-DD
            
            if r["event_type"] == "drive":
                mapped.append({
                    "activity_date": dt_str,
                    "category": "Transport",
                    "activity": "Tesla Drive",
                    "value": r["distance_mi"],
                    "unit": "miles",
                    "emissions_kg": 0.0 # EV driving is 0 tailpipe
                })
            elif r["event_type"] == "charge":
                mapped.append({
                    "activity_date": dt_str,
                    "category": "Energy",
                    "activity": "Tesla Supercharging",
                    "value": r["energy_added_kwh"],
                    "unit": "kWh"
                })
        return mapped


class OpowerConnector(BaseConnector):
    """Simulated connector for Smart Meter Utility data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "Opower Smart Meter")
        
    def fetch_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        raw = []
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            delta = end_dt - start_dt
            
            for i in range(delta.days + 1):
                current = start_dt + timedelta(days=i)
                # Daily usage data
                raw.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "meter_id": "MTR-99382",
                    "consumption_wh": random.randint(15000, 35000),
                    "peak_demand_w": random.randint(3000, 7000)
                })
            return raw
        except Exception:
            return []
            
    def map_to_standard_schema(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped = []
        for r in raw_data:
            mapped.append({
                "activity_date": r["date"],
                "category": "Energy",
                "activity": f"Home Electricity Usage ({r['meter_id']})",
                "value": r["consumption_wh"] / 1000.0, # wh to kwh
                "unit": "kWh"
            })
        return mapped


class FlightAwareConnector(BaseConnector):
    """Simulated connector for historical flight data."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "FlightAware")
        
    def fetch_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        raw = []
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            delta = end_dt - start_dt
            
            # Flights are sparse, maybe 2 per month
            for i in range(delta.days + 1):
                current = start_dt + timedelta(days=i)
                if random.random() > 0.95:
                    raw.append({
                        "flight_date": current.strftime("%Y-%m-%d"),
                        "origin": "JFK",
                        "destination": "LAX",
                        "distance_km": 3983.0,
                        "class": "Economy"
                    })
            return raw
        except Exception:
            return []
            
    def map_to_standard_schema(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped = []
        for r in raw_data:
            mapped.append({
                "activity_date": r["flight_date"],
                "category": "Transport",
                "activity": f"Flight {r['origin']} to {r['destination']}",
                "value": r["distance_km"],
                "unit": "km",
                # Rough approximation: 0.15 kg CO2 per km for economy flight
                "emissions_kg": r["distance_km"] * 0.15
            })
        return mapped

class ConnectorManager:
    """Manages multi-source data ingestion."""
    
    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        
    def register_connector(self, connector_id: str, connector: BaseConnector):
        self.connectors[connector_id] = connector
        
    def sync_all(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Pull data from all registered external services."""
        combined = []
        for cid, conn in self.connectors.items():
            logger.info(f"Syncing connector: {cid}")
            try:
                data = conn.sync(start_date, end_date)
                # Tag the source
                for d in data:
                    d["_source_api"] = cid
                combined.extend(data)
            except Exception as e:
                logger.error(f"Error syncing {cid}: {e}")
                
        return combined
