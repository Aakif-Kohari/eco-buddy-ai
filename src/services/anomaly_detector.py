"""
Anomaly Detector.
Processes historical assessment data using statistical methods to flag unusual carbon footprint spikes.
"""

from typing import List, Dict, Any, Optional
import math


class AnomalyDetector:
    """Detects anomalies in time-series carbon footprint data using Z-score analysis."""

    def __init__(self, z_score_threshold: float = 2.0):
        """
        Initializes the detector.

        Args:
            z_score_threshold: The number of standard deviations from the mean
                               to consider a data point anomalous. Default is 2.0.
        """
        self.z_score_threshold = z_score_threshold

    def calculate_statistics(self, data_points: List[float]) -> Dict[str, float]:
        """
        Calculates the mean and standard deviation of a list of data points.

        Args:
            data_points: List of numerical values (e.g., carbon footprint in kg).

        Returns:
            Dictionary containing 'mean' and 'std_dev'.
        """
        if not data_points:
            return {"mean": 0.0, "std_dev": 0.0}

        n = len(data_points)
        mean = sum(data_points) / n

        if n < 2:
            return {"mean": mean, "std_dev": 0.0}

        variance = sum((x - mean) ** 2 for x in data_points) / (n - 1)
        std_dev = math.sqrt(variance)

        return {"mean": round(mean, 2), "std_dev": round(std_dev, 2)}

    def detect_anomalies(
        self, historical_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identifies anomalous entries in historical footprint data.

        Args:
            historical_data: List of dictionaries containing 'date' and 'carbon_kg' keys.

        Returns:
            List of dictionaries representing anomalous data points with added 'z_score'
            and 'is_anomaly' flags.
        """
        if len(historical_data) < 3:
            # Not enough data for meaningful statistical deviation
            return [
                {**entry, "is_anomaly": False, "z_score": 0.0}
                for entry in historical_data
            ]

        carbon_values = [entry["carbon_kg"] for entry in historical_data]
        stats = self.calculate_statistics(carbon_values)
        mean = stats["mean"]
        std_dev = stats["std_dev"]

        results = []
        for entry in historical_data:
            carbon = entry["carbon_kg"]
            if std_dev == 0:
                z_score = 0.0
            else:
                z_score = (carbon - mean) / std_dev

            is_anomaly = abs(z_score) > self.z_score_threshold

            results.append(
                {
                    **entry,
                    "z_score": round(z_score, 2),
                    "is_anomaly": is_anomaly,
                    "mean_baseline": mean,
                    "std_dev_baseline": std_dev,
                }
            )

        return results
