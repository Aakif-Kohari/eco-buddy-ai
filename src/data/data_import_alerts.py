"""Intelligent Alerting System for Imported Data.

Evaluates imported datasets to generate actionable alerts, warnings, and
celebratory milestones based on consumption patterns and anomalies.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ImportAlertSystem:
    
    def __init__(self):
        self.alerts = []
        
    def generate_alerts(self, records: List[Dict[str, Any]], stats: Dict[str, Any]) -> List[Dict[str, str]]:
        """Scan records and analytics to produce actionable alerts."""
        self.alerts = []
        
        self._check_data_quality(stats)
        self._check_anomalies(records)
        self._check_footprint_milestones(records)
        self._check_carbon_intensity(records)
        self._check_transport_behavior(records)
        self._check_missing_data_gaps(records)
        
        return self.alerts
        
    def _add_alert(self, level: str, title: str, message: str):
        self.alerts.append({"level": level, "title": title, "message": message})
        
    def _check_data_quality(self, stats: Dict[str, Any]):
        """Alert if data quality is dangerously low."""
        total = stats.get("total", 0)
        invalid = stats.get("invalid", 0)
        
        if total > 0:
            error_rate = invalid / total
            if error_rate > 0.5:
                self._add_alert("error", "Critical Data Quality", 
                                f"More than 50% of your imported records ({invalid}/{total}) failed validation. Check your column mappings and unit formats.")
            elif error_rate > 0.1:
                self._add_alert("warning", "Data Quality Warning", 
                                f"{error_rate*100:.1f}% of records failed validation. Please review the Invalid Records tab.")
                                
    def _check_anomalies(self, records: List[Dict[str, Any]]):
        """Highlight severe anomalies directly to the user."""
        anomalies = [r for r in records if r.get("_is_anomaly")]
        if anomalies:
            self._add_alert("warning", "Anomalous Activity Detected", 
                            f"We detected {len(anomalies)} activities that are statistically outside your normal footprint patterns. For example: {anomalies[0].get('activity')} on {anomalies[0].get('activity_date')}.")
                            
    def _check_footprint_milestones(self, records: List[Dict[str, Any]]):
        """Celebrate massive cumulative milestones."""
        total_co2 = sum([r.get("emissions_kg", 0.0) for r in records])
        
        # We don't want to "celebrate" high carbon, but we want to point out scope.
        if total_co2 > 10000:
            self._add_alert("info", "Major Milestone: 10+ Tons CO2e", 
                            f"The imported dataset covers over 10 tons of CO2e. This is equivalent to driving an average car over 25,000 miles.")
        elif total_co2 > 1000:
            self._add_alert("info", "Milestone: 1+ Ton CO2e", 
                            f"The imported dataset covers over 1 ton of CO2e. That's a significant amount of tracked sustainability data!")

    def _check_carbon_intensity(self, records: List[Dict[str, Any]]):
        """Identify high carbon intensity ratios."""
        energy_records = []
        for r in records:
            if r.get("category") == "Energy":
                try:
                    v = float(r.get("value", 0))
                    if v > 0:
                        energy_records.append(r)
                except (ValueError, TypeError):
                    pass
        
        if energy_records:
            total_kwh = 0.0
            for r in energy_records:
                if r.get("normalized_unit") == "kWh":
                    try:
                        total_kwh += float(r.get("normalized_value", 0))
                    except (ValueError, TypeError):
                        pass
                        
            total_energy_co2 = 0.0
            for r in energy_records:
                try:
                    total_energy_co2 += float(r.get("emissions_kg", 0) or 0.0)
                except (ValueError, TypeError):
                    pass
            
            if total_kwh > 0:
                intensity = total_energy_co2 / total_kwh
                # US average is ~0.38 kg/kWh. Above 0.6 is very coal heavy.
                if intensity > 0.6:
                    self._add_alert("warning", "High Grid Carbon Intensity", 
                                    f"Your average electricity footprint is {intensity:.2f} kg CO2/kWh. This indicates a very fossil-heavy energy grid. Consider solar or green energy purchasing programs.")
                elif intensity < 0.2:
                    self._add_alert("success", "Clean Energy Grid", 
                                    f"Your electricity footprint is highly efficient ({intensity:.2f} kg CO2/kWh), indicating a strong renewable energy mix in your region!")

    def _check_transport_behavior(self, records: List[Dict[str, Any]]):
        """Detect highly active transport profiles."""
        flights = [r for r in records if "flight" in str(r.get("activity")).lower()]
        if len(flights) > 10:
            flight_co2 = sum([f.get("emissions_kg", 0) for f in flights])
            self._add_alert("info", "Frequent Flyer", 
                            f"You have {len(flights)} flights recorded in this dataset, contributing {flight_co2:.1f} kg CO2e. Aviation is likely a primary driver of your footprint.")
                            
    def _check_missing_data_gaps(self, records: List[Dict[str, Any]]):
        """Detect temporal gaps in imported data."""
        from datetime import datetime
        
        dates = []
        for r in records:
            dt = r.get("activity_date")
            if dt:
                try:
                    dates.append(datetime.strptime(dt, "%Y-%m-%d"))
                except ValueError:
                    pass
                    
        if len(dates) > 10:
            dates.sort()
            max_gap = 0
            for i in range(1, len(dates)):
                gap = (dates[i] - dates[i-1]).days
                if gap > max_gap:
                    max_gap = gap
                    
            if max_gap > 90:
                self._add_alert("warning", "Large Data Gap Detected", 
                                f"There is a continuous gap of {max_gap} days in your imported data where no activities were recorded. Your analytics might be skewed.")
