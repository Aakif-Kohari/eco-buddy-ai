import pandas as pd
from typing import List, Dict

class SmartBuildingAlerts:
    """
    Evaluates telemetry data stream and detects anomalies or rule violations.
    Used for predictive maintenance and real-time efficiency notifications.
    """

    # Thresholds
    HVAC_MAX_POWER_WATTS = 2500
    OFF_HOURS_MAX_WATTS = 1000
    CO2_WARNING_PPM = 1000
    CO2_CRITICAL_PPM = 1500

    def __init__(self, alerts_history: List[Dict] = None):
        if alerts_history is None:
            self.alerts = []
        else:
            self.alerts = alerts_history

    def analyze_batch(self, telemetry_df: pd.DataFrame) -> List[Dict]:
        """Analyzes a batch of telemetry records and stores generated alerts."""
        if telemetry_df.empty:
            return self.alerts

        new_alerts = []
        
        for _, row in telemetry_df.iterrows():
            timestamp = row['timestamp']
            hour = timestamp.hour
            is_off_hours = hour < 6 or hour > 20
            
            # Rule 1: Equipment Anomalous Draw
            if row['type'] == 'HVAC_Unit' and row['power_usage_watts'] > self.HVAC_MAX_POWER_WATTS:
                new_alerts.append({
                    "timestamp": timestamp.isoformat(),
                    "device_id": row['device_id'],
                    "level": "CRITICAL",
                    "reason": f"HVAC power draw ({row['power_usage_watts']:.0f} W) exceeded maximum threshold."
                })

            # Rule 2: Zombie Power Draw
            if is_off_hours and row['power_usage_watts'] > self.OFF_HOURS_MAX_WATTS:
                new_alerts.append({
                    "timestamp": timestamp.isoformat(),
                    "device_id": row['device_id'],
                    "level": "WARNING",
                    "reason": f"High off-hours power draw detected ({row['power_usage_watts']:.0f} W) at hour {hour}."
                })

            # Rule 3: Air Quality 
            if pd.notna(row['co2_ppm']):
                if row['co2_ppm'] > self.CO2_CRITICAL_PPM:
                    new_alerts.append({
                        "timestamp": timestamp.isoformat(),
                        "device_id": row['device_id'],
                        "level": "CRITICAL",
                        "reason": f"CO2 levels critically high ({row['co2_ppm']:.0f} ppm)."
                    })
                elif row['co2_ppm'] > self.CO2_WARNING_PPM:
                    new_alerts.append({
                        "timestamp": timestamp.isoformat(),
                        "device_id": row['device_id'],
                        "level": "WARNING",
                        "reason": f"CO2 levels elevated ({row['co2_ppm']:.0f} ppm)."
                    })

        self.alerts.extend(new_alerts)
        return new_alerts

    def get_all_alerts(self) -> pd.DataFrame:
        """Returns all historical alerts as a DataFrame."""
        if not self.alerts:
            return pd.DataFrame(columns=["timestamp", "device_id", "level", "reason"])
            
        df = pd.DataFrame(self.alerts)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values(by="timestamp", ascending=False)
