"""Anomaly Detection for Imported Eco Data.

This module provides statistical methods (Z-score, IQR, and MAD) 
to detect outliers and anomalies in imported sustainability datasets.
These anomalies might indicate typos (e.g., 10000 kWh instead of 100) 
or unusually high-impact activities that need user review.
"""

import math
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Statistical anomaly detector for eco records."""
    
    def __init__(self, sensitivity: float = 3.0):
        """
        Args:
            sensitivity: Z-score or IQR multiplier threshold.
        """
        self.sensitivity = sensitivity
        
    def detect_anomalies(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Run multiple detection algorithms and flag anomalous records."""
        stats = {"anomalies_detected": 0}
        
        if len(records) < 5:
            # Not enough data for statistical significance
            return records, stats
            
        # Group records by category to establish baselines
        category_values = {}
        for r in records:
            cat = r.get("category", "Other")
            val = r.get("normalized_value") or r.get("value")
            if val is not None:
                if cat not in category_values:
                    category_values[cat] = []
                category_values[cat].append(val)
                
        # Calculate thresholds per category
        thresholds = {}
        for cat, values in category_values.items():
            if len(values) >= 5:
                # We can calculate IQR
                sorted_vals = sorted(values)
                q1_idx = int(len(sorted_vals) * 0.25)
                q3_idx = int(len(sorted_vals) * 0.75)
                q1 = sorted_vals[q1_idx]
                q3 = sorted_vals[q3_idx]
                iqr = q3 - q1
                
                # Mean and std dev
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std_dev = math.sqrt(variance)
                
                thresholds[cat] = {
                    "iqr_upper": q3 + (self.sensitivity * iqr),
                    "z_score_upper": mean + (self.sensitivity * std_dev) if std_dev > 0 else float('inf'),
                    "mean": mean,
                    "std_dev": std_dev
                }
                
        # Flag anomalies
        anomalies_found = 0
        for r in records:
            cat = r.get("category", "Other")
            val = r.get("normalized_value") or r.get("value")
            
            if cat in thresholds and val is not None:
                thresh = thresholds[cat]
                is_anomaly = False
                reason = ""
                
                if val > thresh["iqr_upper"] and val > thresh["z_score_upper"]:
                    is_anomaly = True
                    reason = f"Value {val} is statistically anomalous (exceeds {self.sensitivity}x standard deviation from category mean of {thresh['mean']:.1f})."
                    
                if is_anomaly:
                    if "_warnings" not in r:
                        r["_warnings"] = []
                    r["_warnings"].append(f"[ANOMALY] {reason}")
                    r["_is_anomaly"] = True
                    anomalies_found += 1
                    
        stats["anomalies_detected"] = anomalies_found
        return records, stats
        
    def find_temporal_anomalies(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify records where the timestamp deviates heavily from the import batch."""
        if not records:
            return records
            
        import datetime
        
        # Extract all valid dates
        valid_dates = []
        for r in records:
            ds = r.get("activity_date")
            if ds:
                try:
                    dt = datetime.datetime.strptime(ds, "%Y-%m-%d").date()
                    valid_dates.append((r, dt))
                except ValueError:
                    continue
                    
        if len(valid_dates) < 2:
            return records
            
        # Find median date
        sorted_dates = sorted(valid_dates, key=lambda x: x[1])
        median_date = sorted_dates[len(sorted_dates) // 2][1]
        
        # Flag anything more than 5 years away from median as likely typo
        for r, dt in valid_dates:
            days_diff = abs((dt - median_date).days)
            if days_diff > 365 * 5:
                if "_warnings" not in r:
                    r["_warnings"] = []
                r["_warnings"].append(f"[TEMPORAL ANOMALY] Date {dt} is more than 5 years away from the batch median ({median_date}).")
                r["_is_anomaly"] = True
                
        return records
