import random
import math
import datetime
import pandas as pd
from typing import List, Dict, Any

class SmartBuildingIoTSimulator:
    """
    Simulates real-time telemetry from IoT sensors within a smart building ecosystem.
    Data includes HVAC energy consumption, lighting power draw, and plug load metrics.
    """

    FLOORS = ["Floor 1", "Floor 2", "Floor 3", "Floor 4", "Floor 5"]
    ZONES = ["North Wing", "South Wing", "East Wing", "West Wing", "Core"]
    DEVICE_TYPES = ["HVAC_Unit", "LED_Controller", "Smart_Plug", "Air_Quality_Monitor"]

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(self.seed)

    def generate_devices(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generates a list of registered IoT devices in the building."""
        devices = []
        for i in range(count):
            device_type = random.choice(self.DEVICE_TYPES)
            baseline = 0
            if device_type == "HVAC_Unit":
                baseline = random.uniform(500, 2000) # Watts
            elif device_type == "LED_Controller":
                baseline = random.uniform(100, 500)
            elif device_type == "Smart_Plug":
                baseline = random.uniform(50, 250)
            else:
                baseline = random.uniform(5, 15)

            device = {
                "device_id": f"DEV-{random.randint(10000, 99999)}",
                "type": device_type,
                "floor": random.choice(self.FLOORS),
                "zone": random.choice(self.ZONES),
                "baseline_power_watts": baseline,
                "install_date": (datetime.date.today() - datetime.timedelta(days=random.randint(10, 1000))).isoformat(),
                "status": "ONLINE" if random.random() > 0.05 else "OFFLINE"
            }
            devices.append(device)
        return devices

    def generate_telemetry(self, devices: List[Dict[str, Any]], hours: int = 24, start_time: datetime.datetime = None) -> pd.DataFrame:
        """
        Generates telemetry metrics for the specified hours.
        Applies diurnal sinusoidal patterns to simulate work hours vs non-work hours.
        """
        if start_time is None:
            start_time = datetime.datetime.now().replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=hours)

        records = []
        for hour_offset in range(hours):
            current_time = start_time + datetime.timedelta(hours=hour_offset)
            hour_of_day = current_time.hour
            
            # Sinusoidal diurnal wave (peak around 2 PM / 14:00)
            # Normalize hour to a -pi to pi range roughly centered on peak
            time_shift = hour_of_day - 14
            occupancy_multiplier = math.cos(time_shift * (math.pi / 24)) * 0.8 + 0.2
            
            if 1 <= hour_of_day <= 5: 
                # Deep night, minimal occupancy
                occupancy_multiplier = 0.1
            
            for dev in devices:
                if dev["status"] == "OFFLINE":
                    continue

                # Add noise
                noise = random.uniform(-0.1, 0.1)
                
                # HVAC spikes more randomly
                if dev["type"] == "HVAC_Unit":
                    active_power = dev["baseline_power_watts"] * (occupancy_multiplier + noise + random.uniform(0, 0.5))
                    temp = random.uniform(20.0, 24.0) if occupancy_multiplier > 0.5 else random.uniform(18.0, 26.0)
                elif dev["type"] == "LED_Controller":
                    active_power = dev["baseline_power_watts"] * (1.0 if occupancy_multiplier > 0.3 else 0.05) + (noise * 10)
                    temp = None
                else:
                    active_power = dev["baseline_power_watts"] * (occupancy_multiplier + noise)
                    temp = None
                
                record = {
                    "timestamp": current_time.isoformat(),
                    "device_id": dev["device_id"],
                    "type": dev["type"],
                    "floor": dev["floor"],
                    "zone": dev["zone"],
                    "power_usage_watts": max(0, active_power),
                    "temperature_c": temp
                }
                
                if dev["type"] == "Air_Quality_Monitor":
                    record["co2_ppm"] = 400 + (occupancy_multiplier * random.uniform(200, 600))
                    record["tvoc_ppb"] = random.uniform(10, 500) * occupancy_multiplier
                else:
                    record["co2_ppm"] = None
                    record["tvoc_ppb"] = None
                    
                records.append(record)

        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

if __name__ == "__main__":
    sim = SmartBuildingIoTSimulator(seed=101)
    devs = sim.generate_devices(20)
    data = sim.generate_telemetry(devs, hours=4)
    print("Devices:", len(devs))
    print("Telemetry Records:", len(data))
    print(data.head())
