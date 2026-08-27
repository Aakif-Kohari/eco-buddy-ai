"""
Spatiotemporal Environmental Risk Intelligence Framework
==========================================================
An advanced framework for integrating spatial and temporal environmental data
to assess, predict, and provide early warnings for environmental risks.

Author: EcoBuddy Team
Version: 4.0.0
"""

import json
import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path
import hashlib
import re
from collections import defaultdict, Counter, deque
import heapq
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class RiskType(Enum):
    """Types of environmental risks."""
    FLOOD = "flood"
    DROUGHT = "drought"
    WILDFIRE = "wildfire"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    HEATWAVE = "heatwave"
    COLDWAVE = "coldwave"
    AIR_POLLUTION = "air_pollution"
    WATER_POLLUTION = "water_pollution"
    SOIL_CONTAMINATION = "soil_contamination"
    DEFORESTATION = "deforestation"
    DESERTIFICATION = "desertification"
    GLACIAL_MELT = "glacial_melt"
    SEA_LEVEL_RISE = "sea_level_rise"
    BIODIVERSITY_LOSS = "biodiversity_loss"
    WASTE_ACCUMULATION = "waste_accumulation"
    NOISE_POLLUTION = "noise_pollution"
    LIGHT_POLLUTION = "light_pollution"


class RiskSeverity(Enum):
    """Severity levels for risks."""
    INSIGNIFICANT = 0
    MINOR = 1
    MODERATE = 2
    MAJOR = 3
    SEVERE = 4
    CATASTROPHIC = 5


class RiskStatus(Enum):
    """Current status of a risk."""
    INACTIVE = "inactive"
    MONITORING = "monitoring"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"
    ONGOING = "ongoing"
    RESOLVED = "resolved"


class SpatialScale(Enum):
    """Spatial scales for analysis."""
    GLOBAL = "global"
    CONTINENTAL = "continental"
    REGIONAL = "regional"
    NATIONAL = "national"
    SUB_NATIONAL = "sub_national"
    LOCAL = "local"
    NEIGHBORHOOD = "neighborhood"
    INDIVIDUAL = "individual"


class TemporalScale(Enum):
    """Temporal scales for analysis."""
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    ANNUAL = "annual"
    DECADAL = "decadal"
    CENTURY = "century"


class DataSourceType(Enum):
    """Types of data sources."""
    SATELLITE = "satellite"
    GROUND_STATION = "ground_station"
    WEATHER_STATION = "weather_station"
    BUOY = "buoy"
    RADAR = "radar"
    LIDAR = "lidar"
    DRONE = "drone"
    AIRCRAFT = "aircraft"
    SHIP = "ship"
    SENSOR_NETWORK = "sensor_network"
    CITIZEN_SCIENCE = "citizen_science"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    HISTORICAL_RECORDS = "historical_records"
    MODEL_OUTPUT = "model_output"
    EXPERT_KNOWLEDGE = "expert_knowledge"


# ============================================================================
# DATA CLASSES FOR SPATIOTEMPORAL DATA
# ============================================================================

@dataclass
class GeoPoint:
    """Geographic point with coordinates."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: float = 0.0
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")
    
    def distance_to(self, other: 'GeoPoint') -> float:
        """Calculate Euclidean distance in km."""
        import math
        lat1, lon1 = self.latitude, self.longitude
        lat2, lon2 = other.latitude, other.longitude
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c


@dataclass
class BoundingBox:
    """Geographic bounding box."""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    
    def __post_init__(self):
        if not -90 <= self.min_lat <= 90 or not -90 <= self.max_lat <= 90:
            raise ValueError("Invalid latitude range")
        if not -180 <= self.min_lon <= 180 or not -180 <= self.max_lon <= 180:
            raise ValueError("Invalid longitude range")
        if self.min_lat > self.max_lat:
            self.min_lat, self.max_lat = self.max_lat, self.min_lat
        if self.min_lon > self.max_lon:
            self.min_lon, self.max_lon = self.max_lon, self.min_lon
    
    def contains_point(self, point: GeoPoint) -> bool:
        """Check if point is within bounding box."""
        return (self.min_lat <= point.latitude <= self.max_lat and
                self.min_lon <= point.longitude <= self.max_lon)
    
    def area_sqkm(self) -> float:
        """Calculate approximate area in square kilometers."""
        import math
        lat_avg = (self.min_lat + self.max_lat) / 2
        lat_diff = abs(self.max_lat - self.min_lat)
        lon_diff = abs(self.max_lon - self.min_lon)
        R = 6371
        lat_rad = math.radians(lat_avg)
        area = R**2 * math.cos(lat_rad) * math.radians(lat_diff) * math.radians(lon_diff)
        return abs(area)


@dataclass
class TimeWindow:
    """Time window for temporal analysis."""
    start_time: datetime
    end_time: datetime
    
    def __post_init__(self):
        if self.start_time > self.end_time:
            self.start_time, self.end_time = self.end_time, self.start_time
    
    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp is within window."""
        return self.start_time <= timestamp <= self.end_time
    
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600


@dataclass
class SpatiotemporalPoint:
    """Point with both spatial and temporal data."""
    point: GeoPoint
    timestamp: datetime
    values: Dict[str, float]
    quality_indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskIndicator:
    """An environmental risk indicator."""
    indicator_id: str
    name: str
    description: str
    risk_type: RiskType
    value: float
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_alert: Optional[float] = None
    unit: str = ""
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    spatial_scale: SpatialScale = SpatialScale.LOCAL
    temporal_scale: TemporalScale = TemporalScale.HOURLY
    source: DataSourceType = DataSourceType.GROUND_STATION
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_severity(self) -> RiskSeverity:
        """Determine risk severity based on thresholds."""
        if self.threshold_alert is not None and self.value >= self.threshold_alert:
            return RiskSeverity.CATASTROPHIC if self.value >= self.threshold_alert * 1.5 else RiskSeverity.SEVERE
        if self.threshold_warning is not None and self.value >= self.threshold_warning:
            return RiskSeverity.MAJOR if self.value >= self.threshold_warning * 1.3 else RiskSeverity.MODERATE
        if self.threshold_max is not None and self.value >= self.threshold_max:
            return RiskSeverity.MODERATE
        if self.threshold_min is not None and self.value <= self.threshold_min:
            return RiskSeverity.MINOR
        return RiskSeverity.INSIGNIFICANT
    
    def is_anomalous(self) -> bool:
        """Check if indicator value is anomalous."""
        if self.threshold_max is not None and self.value > self.threshold_max:
            return True
        if self.threshold_min is not None and self.value < self.threshold_min:
            return True
        if self.threshold_warning is not None and self.value > self.threshold_warning:
            return True
        return False


@dataclass
class EnvironmentalEvent:
    """An environmental event with spatiotemporal characteristics."""
    event_id: str
    event_type: RiskType
    description: str
    location: GeoPoint
    bounding_box: Optional[BoundingBox] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    severity: RiskSeverity = RiskSeverity.MODERATE
    status: RiskStatus = RiskStatus.MONITORING
    magnitude: float = 0.0
    affected_area_sqkm: float = 0.0
    affected_population: int = 0
    economic_impact_usd: float = 0.0
    indicators: List[RiskIndicator] = field(default_factory=list)
    confidence: float = 0.5
    source: DataSourceType = DataSourceType.MODEL_OUTPUT
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_indicator(self, indicator: RiskIndicator):
        """Add a risk indicator to the event."""
        self.indicators.append(indicator)
        self._update_event_properties()
    
    def _update_event_properties(self):
        """Update event properties based on indicators."""
        if self.indicators:
            # Update severity based on highest severity indicator
            severities = [ind.get_severity().value for ind in self.indicators]
            self.severity = RiskSeverity(max(severities))
            
            # Update confidence
            self.confidence = statistics.mean([ind.confidence for ind in self.indicators])
            
            # Update magnitude
            self.magnitude = statistics.mean([ind.value for ind in self.indicators if ind.value])


@dataclass
class SpatiotemporalRiskForecast:
    """A forecast for environmental risks."""
    forecast_id: str
    risk_type: RiskType
    location: GeoPoint
    forecast_time: datetime
    time_window: TimeWindow
    predicted_probability: float  # 0-1
    predicted_severity: RiskSeverity
    confidence: float
    lead_time_hours: float
    indicators: Dict[str, float] = field(default_factory=dict)
    scenarios: Dict[str, Dict[str, float]] = field(default_factory=dict)
    uncertainty_range: Tuple[float, float] = (0.0, 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SPATIOTEMPORAL DATA FUSION ENGINE
# ============================================================================

class SpatiotemporalDataFusionEngine:
    """Engine for fusing data from multiple spatiotemporal sources."""
    
    def __init__(self):
        """Initialize the fusion engine."""
        self.logger = logging.getLogger(f"{__name__}.SpatiotemporalDataFusionEngine")
        self.data_cache = {}
        self.source_weights = self._initialize_source_weights()
        self.fusion_methods = self._initialize_fusion_methods()
    
    def _initialize_source_weights(self) -> Dict[DataSourceType, float]:
        """Initialize weights for different data sources."""
        return {
            DataSourceType.SATELLITE: 0.9,
            DataSourceType.GROUND_STATION: 1.0,
            DataSourceType.WEATHER_STATION: 0.95,
            DataSourceType.BUOY: 0.85,
            DataSourceType.RADAR: 0.8,
            DataSourceType.LIDAR: 0.8,
            DataSourceType.DRONE: 0.75,
            DataSourceType.AIRCRAFT: 0.7,
            DataSourceType.SHIP: 0.7,
            DataSourceType.SENSOR_NETWORK: 0.8,
            DataSourceType.CITIZEN_SCIENCE: 0.4,
            DataSourceType.SOCIAL_MEDIA: 0.3,
            DataSourceType.NEWS: 0.4,
            DataSourceType.HISTORICAL_RECORDS: 0.6,
            DataSourceType.MODEL_OUTPUT: 0.85,
            DataSourceType.EXPERT_KNOWLEDGE: 0.75
        }
    
    def _initialize_fusion_methods(self) -> Dict[str, Callable]:
        """Initialize different data fusion methods."""
        return {
            "weighted_average": self._weighted_average_fusion,
            "bayesian": self._bayesian_fusion,
            "kalman": self._kalman_fusion,
            "dempster_shafer": self._dempster_shafer_fusion,
            "ensemble": self._ensemble_fusion
        }
    
    def _weighted_average_fusion(self, data_points: List[SpatiotemporalPoint],
                                 weights: Optional[List[float]] = None) -> Dict[str, float]:
        """Fuse data using weighted average."""
        if not data_points:
            return {}
        
        if weights is None:
            weights = [1.0] * len(data_points)
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            total = 0.0
            total_weight = 0.0
            for point, weight in zip(data_points, weights):
                if key in point.values:
                    total += point.values[key] * weight
                    total_weight += weight
            
            if total_weight > 0:
                result[key] = total / total_weight
        
        return result
    
    def _bayesian_fusion(self, data_points: List[SpatiotemporalPoint],
                        prior_distribution: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fuse data using Bayesian approach."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            # Collect observations and uncertainties
            observations = []
            uncertainties = []
            for point in data_points:
                if key in point.values:
                    observations.append(point.values[key])
                    uncertainties.append(point.quality_indicators.get('uncertainty', 0.1))
            
            if not observations:
                continue
            
            # Weighted average with uncertainty weighting
            total_weight = sum(1.0 / (u + 0.001) for u in uncertainties)
            weighted_sum = sum(v / (u + 0.001) for v, u in zip(observations, uncertainties))
            
            result[f"{key}_mean"] = weighted_sum / total_weight
            result[f"{key}_variance"] = 1.0 / total_weight
        
        return result
    
    def _kalman_fusion(self, data_points: List[SpatiotemporalPoint],
                       state: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Fuse data using Kalman filter approach."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            # Extract time series
            time_series = []
            for point in data_points:
                if key in point.values:
                    time_series.append((point.timestamp, point.values[key]))
            
            if len(time_series) < 2:
                continue
            
            # Simple Kalman filter
            x_prev = time_series[0][1]
            p_prev = 1.0
            
            for t, z in time_series[1:]:
                # Prediction
                x_pred = x_prev
                p_pred = p_prev + 0.1
                
                # Update
                k = p_pred / (p_pred + 0.5)
                x_est = x_pred + k * (z - x_pred)
                p_est = (1 - k) * p_pred
                
                x_prev = x_est
                p_prev = p_est
            
            result[f"{key}_filtered"] = x_prev
            result[f"{key}_uncertainty"] = math.sqrt(p_prev)
        
        return result
    
    def _dempster_shafer_fusion(self, data_points: List[SpatiotemporalPoint]) -> Dict[str, float]:
        """Fuse data using Dempster-Shafer theory."""
        if not data_points:
            return {}
        
        result = {}
        value_keys = data_points[0].values.keys()
        
        for key in value_keys:
            beliefs = []
            for point in data_points:
                if key in point.values:
                    belief = point.values[key]
                    confidence = point.quality_indicators.get('confidence', 0.5)
                    beliefs.append((belief, confidence))
            
            if not beliefs:
                continue
            
            # Combine beliefs
            total_belief = 0.0
            total_weight = 0.0
            for b, c in beliefs:
                weight = c / (1 - c + 0.001)
                total_belief += b * weight
                total_weight += weight
            
            if total_weight > 0:
                result[f"{key}_belief"] = total_belief / total_weight
        
        return result
    
    def _ensemble_fusion(self, data_points: List[SpatiotemporalPoint],
                        methods: List[str] = None) -> Dict[str, float]:
        """Fuse data using ensemble of methods."""
        if not data_points:
            return {}
        
        if methods is None:
            methods = ["weighted_average", "bayesian", "kalman"]
        
        results = []
        for method in methods:
            if method == "weighted_average":
                result = self._weighted_average_fusion(data_points)
            elif method == "bayesian":
                result = self._bayesian_fusion(data_points)
            elif method == "kalman":
                result = self._kalman_fusion(data_points)
            elif method == "dempster_shafer":
                result = self._dempster_shafer_fusion(data_points)
            else:
                continue
            results.append(result)
        
        # Ensemble average
        if not results:
            return {}
        
        ensemble_result = {}
        for key in results[0].keys():
            values = [r.get(key, 0) for r in results if key in r]
            if values:
                ensemble_result[key] = statistics.mean(values)
                ensemble_result[f"{key}_std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        return ensemble_result
    
    def fuse_data(self, data_points: List[SpatiotemporalPoint],
                 method: str = "ensemble",
                 **kwargs) -> Dict[str, float]:
        """
        Fuse spatiotemporal data using specified method.
        """
        self.logger.info(f"Fusing {len(data_points)} data points using {method}")
        
        if not data_points:
            self.logger.warning("No data points to fuse")
            return {}
        
        if method in self.fusion_methods:
            return self.fusion_methods[method](data_points, **kwargs)
        else:
            self.logger.warning(f"Unknown fusion method: {method}, using weighted_average")
            return self._weighted_average_fusion(data_points, **kwargs)
    
    def interpolate_spatiotemporal(self, data_points: List[SpatiotemporalPoint],
                                   target_point: GeoPoint,
                                   target_time: datetime,
                                   method: str = "inverse_distance") -> Dict[str, float]:
        """
        Interpolate data to a target spatiotemporal point.
        """
        self.logger.info(f"Interpolating to {target_point}, {target_time}")
        
        if not data_points:
            return {}
        
        # Calculate spatiotemporal distances
        weighted_points = []
        for point in data_points:
            spatial_dist = target_point.distance_to(point.point)
            temporal_dist = abs((target_time - point.timestamp).total_seconds()) / 3600
            
            # Weighted distance
            distance = math.sqrt(spatial_dist**2 + (temporal_dist * 10)**2)
            weight = 1.0 / (distance + 0.001)
            weighted_points.append((weight, point))
        
        # Interpolate using inverse distance weighting
        result = {}
        if not weighted_points:
            return result
        
        value_keys = weighted_points[0][1].values.keys()
        for key in value_keys:
            total = 0.0
            total_weight = 0.0
            for weight, point in weighted_points:
                if key in point.values:
                    total += point.values[key] * weight
                    total_weight += weight
            
            if total_weight > 0:
                result[key] = total / total_weight
        
        return result


# ============================================================================
# RISK PATTERN DETECTION ENGINE
# ============================================================================

class RiskPatternDetectionEngine:
    """Engine for detecting patterns and anomalies in spatiotemporal data."""
    
    def __init__(self):
        """Initialize the pattern detection engine."""
        self.logger = logging.getLogger(f"{__name__}.RiskPatternDetectionEngine")
        self.patterns = []
        self.anomaly_detectors = self._initialize_anomaly_detectors()
    
    def _initialize_anomaly_detectors(self) -> Dict[str, Callable]:
        """Initialize anomaly detection methods."""
        return {
            "statistical": self._statistical_anomaly,
            "z_score": self._z_score_anomaly,
            "isolation_forest": self._isolation_forest_anomaly,
            "time_series": self._time_series_anomaly,
            "spatial_clustering": self._spatial_clustering_anomaly
        }
    
    def _statistical_anomaly(self, data: List[float],
                            threshold: float = 3.0) -> List[int]:
        """Detect anomalies using statistical methods."""
        if len(data) < 3:
            return []
        
        mean = statistics.mean(data)
        std = statistics.stdev(data) if len(data) > 1 else 0
        
        if std == 0:
            return []
        
        anomalies = []
        for i, value in enumerate(data):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(i)
        
        return anomalies
    
    def _z_score_anomaly(self, data: List[float],
                        threshold: float = 2.5) -> List[int]:
        """Detect anomalies using Z-score method."""
        return self._statistical_anomaly(data, threshold)
    
    def _isolation_forest_anomaly(self, data: List[float],
                                 contamination: float = 0.1) -> List[int]:
        """Detect anomalies using Isolation Forest approach."""
        # Simplified isolation forest
        if len(data) < 10:
            return []
        
        # Random forest isolation
        anomalies = set()
        n_samples = len(data)
        n_trees = 10
        
        for _ in range(n_trees):
            # Randomly select data
            indices = random.sample(range(n_samples), min(50, n_samples))
            values = [data[i] for i in indices]
            
            # Simple isolation
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0
            
            for i, value in enumerate(data):
                if std_val > 0 and abs(value - mean_val) / std_val > 3.0:
                    anomalies.add(i)
        
        return list(anomalies)
    
    def _time_series_anomaly(self, data: List[float],
                            window_size: int = 5,
                            threshold: float = 2.0) -> List[int]:
        """Detect anomalies in time series data."""
        if len(data) < window_size * 2:
            return []
        
        anomalies = []
        
        for i in range(window_size, len(data) - window_size):
            window = data[i-window_size:i+window_size]
            mean = statistics.mean(window)
            std = statistics.stdev(window) if len(window) > 1 else 0
            
            if std > 0:
                z_score = abs((data[i] - mean) / std)
                if z_score > threshold:
                    anomalies.append(i)
        
        return anomalies
    
    def _spatial_clustering_anomaly(self, data: List[Tuple[float, float, float]],
                                   eps: float = 0.5,
                                   min_samples: int = 3) -> List[int]:
        """Detect spatial anomalies using clustering."""
        # Simplified DBSCAN-like approach
        if len(data) < min_samples:
            return []
        
        anomalies = []
        clusters = []
        visited = set()
        
        for i, point in enumerate(data):
            if i in visited:
                continue
            
            # Find neighbors
            neighbors = []
            for j, other in enumerate(data):
                if j == i:
                    continue
                distance = math.sqrt((point[0] - other[0])**2 + 
                                   (point[1] - other[1])**2)
                if distance < eps:
                    neighbors.append(j)
            
            if len(neighbors) >= min_samples:
                cluster = [i] + neighbors
                clusters.append(cluster)
                visited.update(cluster)
            else:
                visited.add(i)
        
        # Points not in clusters are anomalies
        all_clustered = set()
        for cluster in clusters:
            all_clustered.update(cluster)
        
        for i in range(len(data)):
            if i not in all_clustered:
                anomalies.append(i)
        
        return anomalies
    
    def detect_anomalies(self, data: List[float],
                        method: str = "statistical",
                        **kwargs) -> List[int]:
        """
        Detect anomalies in data using specified method.
        """
        if not data:
            return []
        
        if method in self.anomaly_detectors:
            return self.anomaly_detectors[method](data, **kwargs)
        else:
            self.logger.warning(f"Unknown anomaly method: {method}, using statistical")
            return self._statistical_anomaly(data, **kwargs)
    
    def detect_patterns(self, spatiotemporal_data: List[SpatiotemporalPoint],
                       pattern_type: str = "trend") -> Dict[str, Any]:
        """
        Detect patterns in spatiotemporal data.
        """
        self.logger.info(f"Detecting patterns of type: {pattern_type}")
        
        if not spatiotemporal_data:
            return {}
        
        patterns = {}
        
        if pattern_type == "trend":
            patterns = self._detect_trends(spatiotemporal_data)
        elif pattern_type == "seasonal":
            patterns = self._detect_seasonal_patterns(spatiotemporal_data)
        elif pattern_type == "spatial_cluster":
            patterns = self._detect_spatial_clusters(spatiotemporal_data)
        elif pattern_type == "temporal_correlation":
            patterns = self._detect_temporal_correlations(spatiotemporal_data)
        elif pattern_type == "spatiotemporal_evolution":
            patterns = self._detect_spatiotemporal_evolution(spatiotemporal_data)
        
        return patterns
    
    def _detect_trends(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect temporal trends in data."""
        patterns = {}
        
        # Extract value keys
        if not data:
            return patterns
        
        value_keys = data[0].values.keys()
        
        for key in value_keys:
            # Extract time series
            time_series = [(p.timestamp, p.values.get(key, 0)) for p in data if key in p.values]
            
            if len(time_series) < 3:
                continue
            
            # Sort by time
            time_series.sort(key=lambda x: x[0])
            values = [v for _, v in time_series]
            
            # Simple linear trend
            n = len(values)
            x = list(range(n))
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(values)
            
            slope = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
            slope /= sum((x[i] - mean_x)**2 for i in range(n))
            
            # Trend significance
            patterns[f"{key}_trend"] = slope
            patterns[f"{key}_trend_direction"] = "increasing" if slope > 0 else "decreasing"
            patterns[f"{key}_trend_magnitude"] = abs(slope) / mean_y if mean_y != 0 else 0
        
        return patterns
    
    def _detect_seasonal_patterns(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect seasonal patterns in data."""
        patterns = {}
        
        # Group by month
        monthly_data = defaultdict(list)
        for point in data:
            month = point.timestamp.month
            for key, value in point.values.items():
                monthly_data[(month, key)].append(value)
        
        for (month, key), values in monthly_data.items():
            if values:
                patterns[f"{key}_month_{month}_mean"] = statistics.mean(values)
                patterns[f"{key}_month_{month}_std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        return patterns
    
    def _detect_spatial_clusters(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect spatial clusters in data."""
        patterns = {}
        
        if len(data) < 3:
            return patterns
        
        # Extract coordinates and values
        points = []
        for point in data:
            value_sum = sum(point.values.values())
            points.append((point.point.latitude, point.point.longitude, value_sum))
        
        # Use simplified clustering
        clusters = []
        visited = set()
        eps = 0.1  # Approximately 11km
        
        for i, point in enumerate(points):
            if i in visited:
                continue
            
            # Find neighbors
            neighbors = []
            for j, other in enumerate(points):
                if j == i:
                    continue
                distance = math.sqrt((point[0] - other[0])**2 + (point[1] - other[1])**2)
                if distance < eps:
                    neighbors.append(j)
            
            if len(neighbors) >= 2:
                cluster = [i] + neighbors
                clusters.append(cluster)
                visited.update(cluster)
            else:
                visited.add(i)
        
        patterns["num_clusters"] = len(clusters)
        for i, cluster in enumerate(clusters):
            cluster_values = [points[j][2] for j in cluster]
            cluster_lats = [points[j][0] for j in cluster]
            cluster_lons = [points[j][1] for j in cluster]
            
            patterns[f"cluster_{i}_size"] = len(cluster)
            patterns[f"cluster_{i}_mean_value"] = statistics.mean(cluster_values) if cluster_values else 0
            patterns[f"cluster_{i}_center_lat"] = statistics.mean(cluster_lats) if cluster_lats else 0
            patterns[f"cluster_{i}_center_lon"] = statistics.mean(cluster_lons) if cluster_lons else 0
        
        return patterns
    
    def _detect_temporal_correlations(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect temporal correlations between variables."""
        patterns = {}
        
        if len(data) < 5:
            return patterns
        
        # Extract time series for each variable
        variables = {}
        for point in data:
            timestamp = point.timestamp
            for key, value in point.values.items():
                if key not in variables:
                    variables[key] = []
                variables[key].append((timestamp, value))
        
        # Sort each variable by time
        for key in variables:
            variables[key].sort(key=lambda x: x[0])
        
        # Calculate correlations
        keys = list(variables.keys())
        for i, key1 in enumerate(keys):
            for key2 in keys[i+1:]:
                # Align time series
                values1 = [v for _, v in variables[key1]]
                values2 = [v for _, v in variables[key2]]
                
                if len(values1) == len(values2) and len(values1) > 2:
                    # Calculate correlation
                    corr = self._pearson_correlation(values1, values2)
                    patterns[f"correlation_{key1}_{key2}"] = corr
                    
                    # Calculate lag correlation
                    for lag in [1, 2, 3]:
                        if len(values1) > lag:
                            shifted2 = values2[lag:]
                            truncated1 = values1[:len(shifted2)]
                            if len(truncated1) > 2:
                                lag_corr = self._pearson_correlation(truncated1, shifted2)
                                patterns[f"correlation_lag_{lag}_{key1}_{key2}"] = lag_corr
        
        return patterns
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 3:
            return 0.0
        
        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = math.sqrt(sum((x[i] - mean_x)**2 for i in range(n)))
        std_y = math.sqrt(sum((y[i] - mean_y)**2 for i in range(n)))
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        return covariance / (std_x * std_y)
    
    def _detect_spatiotemporal_evolution(self, data: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """Detect spatiotemporal evolution patterns."""
        patterns = {}
        
        if len(data) < 3:
            return patterns
        
        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Track movement of "centers" over time
        centers = []
        for time_slice in self._split_by_time(sorted_data, 3):
            if time_slice:
                center_lat = statistics.mean([p.point.latitude for p in time_slice])
                center_lon = statistics.mean([p.point.longitude for p in time_slice])
                mean_value = statistics.mean([sum(p.values.values()) for p in time_slice])
                centers.append({
                    'time': time_slice[0].timestamp,
                    'lat': center_lat,
                    'lon': center_lon,
                    'value': mean_value
                })
        
        if len(centers) > 1:
            # Calculate movement
            for i in range(len(centers) - 1):
                time_diff = (centers[i+1]['time'] - centers[i]['time']).total_seconds() / 3600
                if time_diff > 0:
                    lat_change = centers[i+1]['lat'] - centers[i]['lat']
                    lon_change = centers[i+1]['lon'] - centers[i]['lon']
                    speed = math.sqrt(lat_change**2 + lon_change**2) / time_diff
                    
                    patterns[f"movement_speed_{i}"] = speed
                    patterns[f"lat_change_{i}"] = lat_change
                    patterns[f"lon_change_{i}"] = lon_change
        
        return patterns
    
    def _split_by_time(self, data: List[SpatiotemporalPoint], 
                      num_splits: int) -> List[List[SpatiotemporalPoint]]:
        """Split data into temporal slices."""
        if not data:
            return []
        
        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Determine split points
        n = len(sorted_data)
        split_size = max(1, n // num_splits)
        
        splits = []
        for i in range(0, n, split_size):
            splits.append(sorted_data[i:min(i+split_size, n)])
        
        return splits


# ============================================================================
# EARLY WARNING SYSTEM
# ============================================================================

class EarlyWarningSystem:
    """Early warning system for environmental risks."""
    
    def __init__(self):
        """Initialize the early warning system."""
        self.logger = logging.getLogger(f"{__name__}.EarlyWarningSystem")
        self.warnings = []
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.communication_channels = []
    
    def _initialize_alert_thresholds(self) -> Dict[RiskType, Dict[str, float]]:
        """Initialize alert thresholds for different risk types."""
        return {
            RiskType.FLOOD: {
                "water_level": 2.5,  # meters above normal
                "rainfall_intensity": 50.0,  # mm/hour
                "river_discharge": 1000.0  # m3/s
            },
            RiskType.DROUGHT: {
                "precipitation_deficit": -30.0,  # percent
                "soil_moisture": 0.2,  # fraction
                "vegetation_health": 0.3  # fraction
            },
            RiskType.WILDFIRE: {
                "temperature": 40.0,  # °C
                "humidity": 20.0,  # percent
                "wind_speed": 40.0,  # km/h
                "fuel_moisture": 10.0  # percent
            },
            RiskType.HEATWAVE: {
                "temperature": 40.0,  # °C
                "temperature_anomaly": 5.0,  # °C above normal
                "humidity": 50.0  # percent
            },
            RiskType.AIR_POLLUTION: {
                "pm2.5": 50.0,  # µg/m³
                "pm10": 100.0,  # µg/m³
                "no2": 100.0,  # µg/m³
                "o3": 120.0  # µg/m³
            },
            RiskType.WATER_POLLUTION: {
                "dissolved_oxygen": 4.0,  # mg/L
                "turbidity": 50.0,  # NTU
                "ph": 6.5,  # pH units
                "nitrate": 10.0  # mg/L
            }
        }
    
    def _initialize_communication_channels(self):
        """Initialize communication channels for alerts."""
        self.communication_channels = [
            "email",
            "sms",
            "push_notification",
            "dashboard",
            "webhook",
            "telegram",
            "slack"
        ]
    
    def check_alerts(self, indicators: List[RiskIndicator]) -> List[Dict[str, Any]]:
        """
        Check if any indicators trigger alerts.
        """
        alerts = []
        
        for indicator in indicators:
            thresholds = self.alert_thresholds.get(indicator.risk_type, {})
            
            if indicator.name in thresholds:
                threshold = thresholds[indicator.name]
                
                if indicator.value >= threshold:
                    severity = self._determine_alert_severity(indicator.value, threshold)
                    alert = {
                        "indicator": indicator,
                        "threshold": threshold,
                        "value": indicator.value,
                        "severity": severity,
                        "timestamp": indicator.timestamp,
                        "message": self._generate_alert_message(indicator, severity),
                        "actions": self._generate_recommended_actions(indicator, severity)
                    }
                    alerts.append(alert)
        
        return alerts
    
    def _determine_alert_severity(self, value: float, threshold: float) -> RiskSeverity:
        """Determine alert severity based on value relative to threshold."""
        ratio = value / threshold
        
        if ratio >= 2.0:
            return RiskSeverity.CATASTROPHIC
        elif ratio >= 1.5:
            return RiskSeverity.SEVERE
        elif ratio >= 1.2:
            return RiskSeverity.MAJOR
        elif ratio >= 1.0:
            return RiskSeverity.MODERATE
        else:
            return RiskSeverity.MINOR
    
    def _generate_alert_message(self, indicator: RiskIndicator, 
                               severity: RiskSeverity) -> str:
        """Generate an alert message."""
        messages = {
            RiskSeverity.INSIGNIFICANT: f"{indicator.risk_type.value.replace('_', ' ').title()} monitoring - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MINOR: f"Minor {indicator.risk_type.value} detected - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MODERATE: f"Moderate {indicator.risk_type.value} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.MAJOR: f"MAJOR {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.SEVERE: f"SEVERE {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}",
            RiskSeverity.CATASTROPHIC: f"CATASTROPHIC {indicator.risk_type.value.upper()} - {indicator.name}: {indicator.value:.2f} {indicator.unit}"
        }
        
        return messages.get(severity, f"Alert for {indicator.name}: {indicator.value:.2f} {indicator.unit}")
    
    def _generate_recommended_actions(self, indicator: RiskIndicator,
                                    severity: RiskSeverity) -> List[str]:
        """Generate recommended actions based on alert."""
        actions = []
        
        if indicator.risk_type == RiskType.FLOOD:
            actions = [
                "Monitor water levels",
                "Prepare sandbags",
                "Move valuables to higher ground",
                "Monitor evacuation routes",
                "Stay tuned to local alerts"
            ]
        elif indicator.risk_type == RiskType.DROUGHT:
            actions = [
                "Conserve water",
                "Reduce outdoor watering",
                "Implement water restrictions",
                "Monitor crop conditions",
                "Prepare for water rationing"
            ]
        elif indicator.risk_type == RiskType.WILDFIRE:
            actions = [
                "Clear vegetation around property",
                "Create firebreaks",
                "Prepare evacuation plan",
                "Monitor fire weather conditions",
                "Report any fires immediately"
            ]
        elif indicator.risk_type == RiskType.HEATWAVE:
            actions = [
                "Stay hydrated",
                "Avoid outdoor activities",
                "Use air conditioning",
                "Check on vulnerable people",
                "Never leave children in vehicles"
            ]
        elif indicator.risk_type == RiskType.AIR_POLLUTION:
            actions = [
                "Stay indoors",
                "Use air purifiers",
                "Wear N95 masks if outside",
                "Close windows",
                "Avoid outdoor exercise"
            ]
        elif indicator.risk_type == RiskType.WATER_POLLUTION:
            actions = [
                "Use bottled water",
                "Report pollution to authorities",
                "Avoid swimming in affected waters",
                "Monitor water quality alerts",
                "Protect wildlife"
            ]
        else:
            actions = [
                f"Monitor {indicator.risk_type.value} conditions",
                "Stay informed through official channels",
                "Follow safety guidelines",
                "Prepare emergency supplies",
                "Check on neighbors and community"
            ]
        
        # Adjust actions based on severity
        if severity in [RiskSeverity.SEVERE, RiskSeverity.CATASTROPHIC]:
            actions.append("IMMEDIATE ACTION REQUIRED - Follow emergency protocols")
        
        return actions
    
    def send_alert(self, alert: Dict[str, Any],
                   channels: List[str] = None) -> Dict[str, bool]:
        """
        Send alert through specified channels.
        """
        if channels is None:
            channels = self.communication_channels
        
        results = {}
        
        for channel in channels:
            if channel in self.communication_channels:
                success = self._send_through_channel(channel, alert)
                results[channel] = success
        
        self.warnings.append({
            "alert": alert,
            "channels": results,
            "timestamp": datetime.now()
        })
        
        return results
    
    def _send_through_channel(self, channel: str, alert: Dict[str, Any]) -> bool:
        """Send alert through a specific channel."""
        # In production, implement actual communication
        self.logger.info(f"Sending alert through {channel}: {alert['message'][:50]}...")
        
        # Simulate success
        return True
    
    def get_active_alerts(self, risk_type: Optional[RiskType] = None) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        active_alerts = []
        for warning in self.warnings:
            alert = warning['alert']
            if risk_type is None or alert['indicator'].risk_type == risk_type:
                if alert['severity'].value >= RiskSeverity.MODERATE.value:
                    active_alerts.append(alert)
        
        return active_alerts


# ============================================================================
# RISK FORECASTING ENGINE
# ============================================================================

class RiskForecastingEngine:
    """Engine for forecasting environmental risks."""
    
    def __init__(self):
        """Initialize the forecasting engine."""
        self.logger = logging.getLogger(f"{__name__}.RiskForecastingEngine")
        self.forecast_models = self._initialize_forecast_models()
        self.model_weights = {}
    
    def _initialize_forecast_models(self) -> Dict[str, Callable]:
        """Initialize forecasting src.notifications.models."""
        return {
            "time_series": self._forecast_time_series,
            "arima": self._forecast_arima,
            "ensemble": self._forecast_ensemble,
            "spatiotemporal": self._forecast_spatiotemporal,
            "machine_learning": self._forecast_machine_learning
        }
    
    def _forecast_time_series(self, data: List[SpatiotemporalPoint],
                             horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using time series methods."""
        if len(data) < 5:
            return {"error": "Insufficient data for forecasting"}
        
        # Extract time series
        time_series = defaultdict(list)
        for point in data:
            for key, value in point.values.items():
                time_series[key].append((point.timestamp, value))
        
        forecasts = {}
        
        for key, series in time_series.items():
            # Sort by time
            series.sort(key=lambda x: x[0])
            values = [v for _, v in series]
            
            if len(values) < 3:
                continue
            
            # Simple linear extrapolation
            n = len(values)
            x = list(range(n))
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(values)
            
            slope = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
            slope /= sum((x[i] - mean_x)**2 for i in range(n))
            intercept = mean_y - slope * mean_x
            
            # Forecast
            forecast_value = intercept + slope * (n + horizon_hours)
            
            # Uncertainty
            residuals = [values[i] - (intercept + slope * x[i]) for i in range(n)]
            mse = statistics.mean([r**2 for r in residuals]) if residuals else 0
            uncertainty = math.sqrt(mse)
            
            forecasts[key] = {
                "forecast": forecast_value,
                "uncertainty": uncertainty,
                "method": "time_series",
                "confidence": 0.7 - 0.1 * (horizon_hours / 100)
            }
        
        return forecasts
    
    def _forecast_arima(self, data: List[SpatiotemporalPoint],
                       horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using ARIMA-like approach."""
        # Simplified ARIMA
        if len(data) < 10:
            return {"error": "Insufficient data for ARIMA forecasting"}
        
        forecasts = {}
        time_series = defaultdict(list)
        
        for point in data:
            for key, value in point.values.items():
                time_series[key].append((point.timestamp, value))
        
        for key, series in time_series.items():
            series.sort(key=lambda x: x[0])
            values = [v for _, v in series]
            
            if len(values) < 5:
                continue
            
            # Simple AR(2) model
            if len(values) >= 3:
                ar1 = values[-1] / (values[-2] + 0.001)
                ar2 = values[-2] / (values[-3] + 0.001)
                
                forecast_value = values[-1] * ar1 * 0.7 + values[-2] * ar2 * 0.3
                
                # Extrapolate for longer horizon
                for _ in range(horizon_hours - 1):
                    forecast_value = forecast_value * 0.95 + random.gauss(0, 0.05)
            else:
                forecast_value = values[-1]
            
            forecasts[key] = {
                "forecast": forecast_value,
                "uncertainty": 0.1 * horizon_hours,
                "method": "arima",
                "confidence": 0.6
            }
        
        return forecasts
    
    def _forecast_ensemble(self, data: List[SpatiotemporalPoint],
                          horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using ensemble of methods."""
        forecasts = []
        methods = ["time_series", "arima"]
        
        for method in methods:
            if method in self.forecast_models:
                result = self.forecast_models[method](data, horizon_hours)
                if "error" not in result:
                    forecasts.append(result)
        
        if not forecasts:
            return {"error": "No forecasts available for ensemble"}
        
        # Ensemble average
        ensemble_forecast = {}
        for key in forecasts[0].keys():
            values = []
            for f in forecasts:
                if key in f and "forecast" in f[key]:
                    values.append(f[key]["forecast"])
            
            if values:
                ensemble_forecast[key] = {
                    "forecast": statistics.mean(values),
                    "uncertainty": statistics.stdev(values) if len(values) > 1 else 0,
                    "method": "ensemble",
                    "confidence": 0.75 - 0.1 * (horizon_hours / 100)
                }
        
        return ensemble_forecast
    
    def _forecast_spatiotemporal(self, data: List[SpatiotemporalPoint],
                                horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using spatiotemporal methods."""
        if len(data) < 5:
            return {"error": "Insufficient data for spatiotemporal forecasting"}
        
        # Track movement and trends
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Calculate movement
        if len(sorted_data) > 1:
            first = sorted_data[0]
            last = sorted_data[-1]
            time_diff = (last.timestamp - first.timestamp).total_seconds() / 3600
            
            if time_diff > 0:
                lat_change = (last.point.latitude - first.point.latitude) / time_diff
                lon_change = (last.point.longitude - first.point.longitude) / time_diff
            else:
                lat_change = 0
                lon_change = 0
        else:
            lat_change = 0
            lon_change = 0
        
        # Forecast new location
        forecast_lat = data[-1].point.latitude + lat_change * horizon_hours
        forecast_lon = data[-1].point.longitude + lon_change * horizon_hours
        
        # Forecast values
        forecasts = {}
        value_keys = data[0].values.keys()
        
        for key in value_keys:
            values = [p.values.get(key, 0) for p in data]
            trend = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
            forecast_value = values[-1] + trend * horizon_hours
            
            forecasts[key] = {
                "forecast": forecast_value,
                "forecast_location": (forecast_lat, forecast_lon),
                "uncertainty": 0.15 * horizon_hours,
                "method": "spatiotemporal",
                "confidence": 0.7
            }
        
        return forecasts
    
    def _forecast_machine_learning(self, data: List[SpatiotemporalPoint],
                                  horizon_hours: int = 24) -> Dict[str, Any]:
        """Forecast using machine learning approach."""
        # Placeholder for ML-based forecasting
        if len(data) < 20:
            return {"error": "Insufficient data for ML forecasting"}
        
        return {"warning": "ML forecasting not fully implemented, using time_series"}
    
    def forecast_risk(self, data: List[SpatiotemporalPoint],
                     risk_type: RiskType,
                     horizon_hours: int = 24,
                     method: str = "ensemble") -> SpatiotemporalRiskForecast:
        """
        Generate a risk forecast.
        """
        self.logger.info(f"Forecasting {risk_type.value} for {horizon_hours} hours")
        
        if method in self.forecast_models:
            forecast_data = self.forecast_models[method](data, horizon_hours)
        else:
            self.logger.warning(f"Unknown forecast method: {method}, using time_series")
            forecast_data = self._forecast_time_series(data, horizon_hours)
        
        if "error" in forecast_data:
            self.logger.error(f"Forecast error: {forecast_data['error']}")
            return None
        
        # Calculate probability based on forecast values
        probability = 0.5
        if "forecast" in forecast_data:
            values = [v["forecast"] for v in forecast_data.values() if isinstance(v, dict) and "forecast" in v]
            if values:
                max_value = max(values)
                probability = min(1.0, max_value / 100.0)  # Normalize
        
        # Determine severity
        severity = RiskSeverity.MODERATE
        if probability > 0.8:
            severity = RiskSeverity.SEVERE
        elif probability > 0.6:
            severity = RiskSeverity.MAJOR
        elif probability > 0.4:
            severity = RiskSeverity.MODERATE
        elif probability > 0.2:
            severity = RiskSeverity.MINOR
        
        # Calculate confidence
        confidence = 0.7 - 0.1 * (horizon_hours / 100)
        confidence = max(0.3, min(0.9, confidence))
        
        forecast = SpatiotemporalRiskForecast(
            forecast_id=f"forecast_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            risk_type=risk_type,
            location=data[-1].point if data else GeoPoint(0, 0),
            forecast_time=datetime.now() + timedelta(hours=horizon_hours),
            time_window=TimeWindow(
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=horizon_hours)
            ),
            predicted_probability=probability,
            predicted_severity=severity,
            confidence=confidence,
            lead_time_hours=horizon_hours,
            indicators={k: v.get("forecast", 0) for k, v in forecast_data.items() if isinstance(v, dict)},
            scenarios={
                "best_case": {"probability": max(0, probability - 0.2)},
                "worst_case": {"probability": min(1.0, probability + 0.2)},
                "most_likely": {"probability": probability}
            },
            uncertainty_range=(max(0, probability - 0.15), min(1.0, probability + 0.15))
        )
        
        return forecast


# ============================================================================
# SPATIOTEMPORAL RISK INTELLIGENCE FRAMEWORK
# ============================================================================

class SpatiotemporalRiskIntelligenceFramework:
    """Main framework for spatiotemporal environmental risk intelligence."""
    
    def __init__(self):
        """Initialize the framework."""
        self.logger = logging.getLogger(f"{__name__}.SpatiotemporalRiskIntelligenceFramework")
        self.fusion_engine = SpatiotemporalDataFusionEngine()
        self.pattern_engine = RiskPatternDetectionEngine()
        self.early_warning = EarlyWarningSystem()
        self.forecast_engine = RiskForecastingEngine()
        self.events = []
        self.risk_history = []
        self.analytics_cache = {}
    
    def process_observations(self, observations: List[SpatiotemporalPoint]) -> Dict[str, Any]:
        """
        Process a batch of observations.
        """
        self.logger.info(f"Processing {len(observations)} observations")
        
        result = {
            "timestamp": datetime.now(),
            "observations_processed": len(observations),
            "fused_data": {},
            "patterns": {},
            "alerts": [],
            "forecasts": [],
            "events": []
        }
        
        # Fuse data
        if observations:
            fused_data = self.fusion_engine.fuse_data(observations)
            result["fused_data"] = fused_data
        
        # Detect patterns
        if len(observations) >= 3:
            patterns = self.pattern_engine.detect_patterns(observations)
            result["patterns"] = patterns
        
        # Check for alerts
        indicators = self._extract_indicators(observations)
        alerts = self.early_warning.check_alerts(indicators)
        result["alerts"] = alerts
        
        # Send alerts for critical issues
        for alert in alerts:
            if alert['severity'].value >= RiskSeverity.MAJOR.value:
                self.early_warning.send_alert(alert, ["dashboard", "email"])
        
        # Generate forecasts
        if len(observations) >= 5:
            for risk_type in RiskType:
                forecast = self.forecast_engine.forecast_risk(
                    observations, risk_type, horizon_hours=24
                )
                if forecast:
                    result["forecasts"].append(forecast)
        
        # Detect events
        events = self._detect_events(observations, alerts)
        result["events"] = events
        
        # Update history
        self.risk_history.extend(observations)
        self.events.extend(events)
        
        return result
    
    def _extract_indicators(self, observations: List[SpatiotemporalPoint]) -> List[RiskIndicator]:
        """Extract risk indicators from observations."""
        indicators = []
        
        for obs in observations:
            for key, value in obs.values.items():
                # Determine risk type from key
                risk_type = self._determine_risk_type_from_key(key)
                
                indicator = RiskIndicator(
                    indicator_id=f"ind_{datetime.now().strftime('%Y%m%d%H%M%S')}_{key}",
                    name=key,
                    description=f"{key} measurement",
                    risk_type=risk_type,
                    value=value,
                    timestamp=obs.timestamp,
                    source=DataSourceType.SENSOR_NETWORK,
                    confidence=obs.quality_indicators.get('confidence', 0.5)
                )
                indicators.append(indicator)
        
        return indicators
    
    def _determine_risk_type_from_key(self, key: str) -> RiskType:
        """Determine risk type from indicator key."""
        risk_mapping = {
            "water_level": RiskType.FLOOD,
            "rainfall": RiskType.FLOOD,
            "river_discharge": RiskType.FLOOD,
            "precipitation": RiskType.DROUGHT,
            "soil_moisture": RiskType.DROUGHT,
            "temperature": RiskType.HEATWAVE,
            "humidity": RiskType.WILDFIRE,
            "wind_speed": RiskType.WILDFIRE,
            "pm2.5": RiskType.AIR_POLLUTION,
            "pm10": RiskType.AIR_POLLUTION,
            "no2": RiskType.AIR_POLLUTION,
            "o3": RiskType.AIR_POLLUTION,
            "dissolved_oxygen": RiskType.WATER_POLLUTION,
            "turbidity": RiskType.WATER_POLLUTION,
            "ph": RiskType.WATER_POLLUTION,
            "nitrate": RiskType.WATER_POLLUTION
        }
        
        return risk_mapping.get(key, RiskType.AIR_POLLUTION)
    
    def _detect_events(self, observations: List[SpatiotemporalPoint],
                      alerts: List[Dict[str, Any]]) -> List[EnvironmentalEvent]:
        """Detect environmental events from observations and alerts."""
        events = []
        
        for alert in alerts:
            if alert['severity'].value >= RiskSeverity.MODERATE.value:
                indicator = alert['indicator']
                event = EnvironmentalEvent(
                    event_id=f"event_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    event_type=indicator.risk_type,
                    description=alert['message'],
                    location=observations[0].point if observations else GeoPoint(0, 0),
                    start_time=indicator.timestamp,
                    severity=alert['severity'],
                    status=RiskStatus.WARNING,
                    indicators=[indicator],
                    confidence=indicator.confidence
                )
                events.append(event)
        
        return events
    
    def get_risk_assessment(self, region: BoundingBox,
                           time_window: TimeWindow) -> Dict[str, Any]:
        """
        Get comprehensive risk assessment for a region.
        """
        self.logger.info(f"Assessing risk for region: {region}")
        
        assessment = {
            "region": region,
            "time_window": time_window,
            "risk_summary": {},
            "critical_indicators": [],
            "trends": {},
            "forecasts": [],
            "recommendations": []
        }
        
        # Filter observations in region
        filtered_obs = []
        for obs in self.risk_history:
            if region.contains_point(obs.point) and time_window.contains(obs.timestamp):
                filtered_obs.append(obs)
        
        if not filtered_obs:
            assessment["risk_summary"] = {"status": "No data available for region"}
            return assessment
        
        # Analyze filtered observations
        for obs in filtered_obs:
            for key, value in obs.values.items():
                if key not in assessment["risk_summary"]:
                    assessment["risk_summary"][key] = {
                        "values": [],
                        "mean": 0,
                        "max": 0,
                        "min": 0
                    }
                assessment["risk_summary"][key]["values"].append(value)
        
        # Calculate statistics
        for key, data in assessment["risk_summary"].items():
            values = data["values"]
            if values:
                data["mean"] = statistics.mean(values)
                data["max"] = max(values)
                data["min"] = min(values)
                data["std"] = statistics.stdev(values) if len(values) > 1 else 0
        
        # Identify critical indicators
        for key, data in assessment["risk_summary"].items():
            if data["mean"] > 0.8:  # Assuming values are normalized
                assessment["critical_indicators"].append(key)
        
        # Detect trends
        patterns = self.pattern_engine.detect_patterns(filtered_obs, "trend")
        assessment["trends"] = patterns
        
        # Generate forecasts
        for risk_type in RiskType:
            forecast = self.forecast_engine.forecast_risk(
                filtered_obs, risk_type, horizon_hours=48
            )
            if forecast:
                assessment["forecasts"].append(forecast)
        
        # Generate recommendations
        assessment["recommendations"] = self._generate_risk_recommendations(assessment)
        
        return assessment
    
    def _generate_risk_recommendations(self, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk-based src.ai.recommendations."""
        recommendations = []
        
        critical_indicators = assessment.get("critical_indicators", [])
        if critical_indicators:
            src.ai.recommendations.append({
                "priority": "high",
                "action": f"Immediate attention needed for: {', '.join(critical_indicators)}",
                "details": "Critical indicators exceed safety thresholds",
                "timeframe": "Immediate"
            })
        
        # Forecast-based recommendations
        for forecast in assessment.get("forecasts", []):
            if forecast.predicted_probability > 0.6:
                src.ai.recommendations.append({
                    "priority": "high" if forecast.predicted_probability > 0.8 else "medium",
                    "action": f"Prepare for {forecast.risk_type.value} within {forecast.lead_time_hours} hours",
                    "details": f"Probability: {forecast.predicted_probability:.1%}",
                    "timeframe": f"{int(forecast.lead_time_hours)} hours"
                })
        
        # Trend-based recommendations
        trends = assessment.get("trends", {})
        for key, value in trends.items():
            if "increasing" in str(value) and "_trend" in key:
                src.ai.recommendations.append({
                    "priority": "medium",
                    "action": f"Monitor {key} - increasing trend detected",
                    "details": f"Trend magnitude: {abs(float(value) if isinstance(value, (int, float)) else 0):.2f}",
                    "timeframe": "Ongoing"
                })
        
        # General recommendations
        if len(recommendations) < 2:
            src.ai.recommendations.append({
                "priority": "low",
                "action": "Continue monitoring environmental indicators",
                "details": "No immediate risks detected",
                "timeframe": "Ongoing"
            })
        
        return recommendations
    
    def get_historical_risk_analysis(self, region: BoundingBox,
                                    start_time: datetime,
                                    end_time: datetime) -> Dict[str, Any]:
        """
        Get historical risk analysis for a region.
        """
        self.logger.info(f"Analyzing historical risks for region from {start_time} to {end_time}")
        
        analysis = {
            "region": region,
            "start_time": start_time,
            "end_time": end_time,
            "events": [],
            "patterns": {},
            "statistics": {},
            "trends": {}
        }
        
        # Filter events
        for event in self.events:
            if (region.contains_point(event.location) and
                start_time <= event.start_time <= end_time):
                analysis["events"].append(event)
        
        # Analyze events
        if analysis["events"]:
            # Event frequency by type
            event_counts = defaultdict(int)
            for event in analysis["events"]:
                event_counts[event.event_type.value] += 1
            analysis["statistics"]["event_frequency"] = dict(event_counts)
            
            # Average severity
            avg_severity = statistics.mean([e.severity.value for e in analysis["events"]])
            analysis["statistics"]["average_severity"] = avg_severity
            
            # Event duration
            durations = []
            for event in analysis["events"]:
                if event.end_time:
                    duration = (event.end_time - event.start_time).total_seconds() / 3600
                    durations.append(duration)
            if durations:
                analysis["statistics"]["average_duration_hours"] = statistics.mean(durations)
        else:
            analysis["statistics"] = {"status": "No events found in this period"}
        
        return analysis


# ============================================================================
# VISUALIZATION AND REPORTING
# ============================================================================

class SpatiotemporalVisualizationGenerator:
    """Generate visualizations for spatiotemporal risk data."""
    
    @staticmethod
    def generate_risk_heatmap(observations: List[SpatiotemporalPoint],
                             risk_type: RiskType,
                             grid_size: int = 10) -> Dict[str, Any]:
        """Generate risk heatmap data."""
        if not observations:
            return {"error": "No observations available"}
        
        # Create grid
        lats = [obs.point.latitude for obs in observations]
        lons = [obs.point.longitude for obs in observations]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        lat_step = (max_lat - min_lat) / grid_size
        lon_step = (max_lon - min_lon) / grid_size
        
        # Initialize grid
        grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        weights = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Populate grid
        for obs in observations:
            lat_idx = min(grid_size - 1, int((obs.point.latitude - min_lat) / lat_step))
            lon_idx = min(grid_size - 1, int((obs.point.longitude - min_lon) / lon_step))
            
            # Determine risk value
            risk_value = 0
            for key, value in obs.values.items():
                if risk_type.value in key.lower():
                    risk_value = max(risk_value, value)
            
            grid[lat_idx][lon_idx] += risk_value
            weights[lat_idx][lon_idx] += 1
        
        # Normalize grid
        for i in range(grid_size):
            for j in range(grid_size):
                if weights[i][j] > 0:
                    grid[i][j] /= weights[i][j]
        
        return {
            "grid": grid,
            "grid_size": grid_size,
            "bounds": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon
            },
            "risk_type": risk_type.value
        }
    
    @staticmethod
    def generate_time_series(observations: List[SpatiotemporalPoint],
                           indicator_key: str) -> Dict[str, Any]:
        """Generate time series data for an indicator."""
        if not observations:
            return {"error": "No observations available"}
        
        # Sort by time
        sorted_obs = sorted(observations, key=lambda x: x.timestamp)
        
        times = []
        values = []
        uncertainties = []
        
        for obs in sorted_obs:
            if indicator_key in obs.values:
                times.append(obs.timestamp.isoformat())
                values.append(obs.values[indicator_key])
                uncertainties.append(obs.quality_indicators.get('uncertainty', 0))
        
        return {
            "times": times,
            "values": values,
            "uncertainties": uncertainties,
            "indicator": indicator_key
        }
    
    @staticmethod
    def generate_risk_dashboard(risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive risk dashboard."""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "risk_summary": {},
            "critical_indicators": [],
            "trends": {},
            "forecasts": [],
            "recommendations": [],
            "heatmap": None
        }
        
        # Add risk summary
        if "risk_summary" in risk_assessment:
            dashboard["risk_summary"] = risk_assessment["risk_summary"]
        
        # Add critical indicators
        if "critical_indicators" in risk_assessment:
            dashboard["critical_indicators"] = risk_assessment["critical_indicators"]
        
        # Add trends
        if "trends" in risk_assessment:
            dashboard["trends"] = risk_assessment["trends"]
        
        # Add forecasts
        if "forecasts" in risk_assessment:
            dashboard["forecasts"] = [
                {
                    "risk_type": f.risk_type.value,
                    "probability": f.predicted_probability,
                    "severity": f.predicted_severity.value,
                    "lead_time": f.lead_time_hours
                }
                for f in risk_assessment.get("forecasts", [])[:5]
            ]
        
        # Add recommendations
        if "recommendations" in risk_assessment:
            dashboard["recommendations"] = risk_assessment["recommendations"][:5]
        
        return dashboard


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def generate_test_observations(n: int = 100) -> List[SpatiotemporalPoint]:
    """Generate test observations for demonstration."""
    observations = []
    
    base_lat = 37.7749  # San Francisco
    base_lon = -122.4194
    
    for i in range(n):
        # Generate random offsets
        lat_offset = random.gauss(0, 0.1)  # ~11 km spread
        lon_offset = random.gauss(0, 0.1)
        
        point = GeoPoint(
            latitude=base_lat + lat_offset,
            longitude=base_lon + lon_offset,
            altitude=random.uniform(0, 100)
        )
        
        # Generate values
        values = {
            "temperature": 20 + random.gauss(5, 3) + math.sin(i/10) * 2,
            "humidity": 60 + random.gauss(10, 5) + math.cos(i/15) * 10,
            "pm2.5": 20 + random.gauss(10, 5) + random.random() * 30,
            "pm10": 40 + random.gauss(15, 8) + random.random() * 40,
            "no2": 30 + random.gauss(8, 4) + random.random() * 20,
            "o3": 40 + random.gauss(10, 6) + math.sin(i/8) * 15,
            "water_level": 2 + random.gauss(1, 0.5) + random.random() * 2,
            "rainfall": 5 + random.gauss(3, 2) + random.random() * 10,
            "wind_speed": 15 + random.gauss(5, 3) + random.random() * 10,
            "soil_moisture": 0.5 + random.gauss(0.2, 0.1) + random.random() * 0.2,
            "dissolved_oxygen": 8 + random.gauss(1, 0.5) + random.random() * 1,
            "turbidity": 10 + random.gauss(5, 3) + random.random() * 10
        }
        
        # Add seasonal pattern
        season = math.sin(i / 30) * 5
        values["temperature"] += season
        
        quality_indicators = {
            "confidence": random.uniform(0.7, 0.95),
            "uncertainty": random.uniform(0.05, 0.15),
            "precision": random.uniform(0.8, 0.98)
        }
        
        obs = SpatiotemporalPoint(
            point=point,
            timestamp=datetime.now() - timedelta(hours=n-i),
            values=values,
            quality_indicators=quality_indicators
        )
        observations.append(obs)
    
    return observations


def run_demonstration():
    """Run a comprehensive demonstration."""
    print("\n" + "=" * 80)
    print("SPATIOTEMPORAL ENVIRONMENTAL RISK INTELLIGENCE FRAMEWORK")
    print("=" * 80 + "\n")
    
    # Initialize framework
    framework = SpatiotemporalRiskIntelligenceFramework()
    
    print("🚀 Generating test observations...")
    observations = generate_test_observations(200)
    print(f"✓ Generated {len(observations)} test observations\n")
    
    print("📊 Processing observations...")
    result = framework.process_observations(observations)
    print(f"✓ Processed {result['observations_processed']} observations")
    print(f"✓ Generated {len(result['alerts'])} alerts")
    print(f"✓ Generated {len(result['forecasts'])} forecasts")
    print(f"✓ Detected {len(result['events'])} events\n")
    
    # Show alerts
    if result['alerts']:
        print("🚨 Critical Alerts:")
        for alert in result['alerts'][:3]:
            print(f"  • {alert['message']}")
            print(f"    Severity: {alert['severity'].name}")
            if 'actions' in alert:
                print(f"    Actions: {alert['actions'][0]}")
        print()
    
    # Get risk assessment
    region = BoundingBox(37.6, 37.9, -122.6, -122.2)  # San Francisco area
    time_window = TimeWindow(
        start_time=datetime.now() - timedelta(days=7),
        end_time=datetime.now()
    )
    
    print("🔍 Assessing risk for region...")
    assessment = framework.get_risk_assessment(region, time_window)
    
    print(f"✓ Critical indicators: {assessment.get('critical_indicators', [])}")
    print(f"✓ Generated {len(assessment.get('recommendations', []))} recommendations")
    
    if assessment.get('recommendations'):
        print("\n📋 Recommendations:")
        for rec in assessment['recommendations'][:3]:
            print(f"  • [{rec['priority'].upper()}] {rec['action']}")
    print()
    
    # Generate dashboard
    print("📊 Generating dashboard...")
    dashboard = SpatiotemporalVisualizationGenerator.generate_risk_dashboard(assessment)
    
    print("Dashboard Summary:")
    print(f"  • Critical Indicators: {len(dashboard.get('critical_indicators', []))}")
    print(f"  • Forecasts: {len(dashboard.get('forecasts', []))}")
    print(f"  • Recommendations: {len(dashboard.get('recommendations', []))}")
    
    # Generate heatmap
    print("\n🗺️ Generating risk heatmap...")
    heatmap = SpatiotemporalVisualizationGenerator.generate_risk_heatmap(
        observations, RiskType.AIR_POLLUTION
    )
    
    if 'grid' in heatmap:
        print(f"✓ Generated {heatmap['grid_size']}x{heatmap['grid_size']} heatmap grid")
    
    # Historical analysis
    print("\n📈 Analyzing historical risks...")
    history = framework.get_historical_risk_analysis(
        region,
        datetime.now() - timedelta(days=30),
        datetime.now()
    )
    
    print(f"✓ Found {len(history.get('events', []))} historical events")
    if 'statistics' in history and 'event_frequency' in history['statistics']:
        print(f"  Event frequency: {history['statistics']['event_frequency']}")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


def run_tests():
    """Run comprehensive tests."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60 + "\n")
    
    # Test 1: GeoPoint
    print("Test 1: GeoPoint")
    p1 = GeoPoint(37.7749, -122.4194)
    p2 = GeoPoint(37.7833, -122.4167)
    distance = p1.distance_to(p2)
    assert distance > 0, "Distance should be positive"
    print(f"✓ Distance between points: {distance:.2f} km")
    
    # Test 2: BoundingBox
    print("\nTest 2: BoundingBox")
    bbox = BoundingBox(37.0, 38.0, -123.0, -122.0)
    assert bbox.contains_point(p1), "Should contain point"
    print("✓ Bounding box contains point")
    print(f"  Area: {bbox.area_sqkm():.2f} km²")
    
    # Test 3: Data Fusion
    print("\nTest 3: Data Fusion")
    obs = generate_test_observations(10)
    engine = SpatiotemporalDataFusionEngine()
    fused = engine.fuse_data(obs)
    assert len(fused) > 0, "Should have fused data"
    print(f"✓ Fused {len(fused)} values")
    
    # Test 4: Pattern Detection
    print("\nTest 4: Pattern Detection")
    pattern_engine = RiskPatternDetectionEngine()
    anomalies = pattern_engine.detect_anomalies([1, 2, 3, 4, 5, 100, 6, 7, 8])
    assert len(anomalies) > 0, "Should detect anomalies"
    print(f"✓ Detected {len(anomalies)} anomalies")
    
    # Test 5: Early Warning
    print("\nTest 5: Early Warning System")
    early_warning = EarlyWarningSystem()
    indicator = RiskIndicator(
        indicator_id="test1",
        name="temperature",
        description="Test temperature",
        risk_type=RiskType.HEATWAVE,
        value=42.0,
        threshold_warning=35.0,
        threshold_alert=40.0
    )
    alerts = early_warning.check_alerts([indicator])
    assert len(alerts) > 0, "Should generate alerts"
    print(f"✓ Generated {len(alerts)} alerts")
    print(f"  Severity: {alerts[0]['severity'].name}")
    
    # Test 6: Forecasting
    print("\nTest 6: Forecasting")
    forecast_engine = RiskForecastingEngine()
    forecast = forecast_engine.forecast_risk(
        obs, RiskType.HEATWAVE, horizon_hours=12
    )
    assert forecast is not None, "Should generate forecast"
    print(f"✓ Generated forecast for {forecast.risk_type.value}")
    print(f"  Probability: {forecast.predicted_probability:.2%}")
    
    # Test 7: Framework Integration
    print("\nTest 7: Framework Integration")
    framework = SpatiotemporalRiskIntelligenceFramework()
    result = framework.process_observations(obs)
    assert result is not None, "Should process observations"
    print(f"✓ Processed {result['observations_processed']} observations")
    
    # Test 8: Risk Assessment
    print("\nTest 8: Risk Assessment")
    assessment = framework.get_risk_assessment(
        BoundingBox(37.5, 38.0, -122.5, -122.0),
        TimeWindow(
            datetime.now() - timedelta(days=1),
            datetime.now()
        )
    )
    assert assessment is not None, "Should generate assessment"
    print(f"✓ Generated risk assessment")
    print(f"  Recommendations: {len(assessment.get('recommendations', []))}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("SPATIOTEMPORAL ENVIRONMENTAL RISK INTELLIGENCE FRAMEWORK")
    print("Version 4.0.0")
    print("=" * 80 + "\n")
    
    print("Select an option:")
    print("1. Run demonstration")
    print("2. Run tests")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        run_demonstration()
    elif choice == '2':
        run_tests()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()

"""
Environmental Anomaly Detection and Early Warning Framework
============================================================

A comprehensive framework for detecting environmental anomalies and providing
early warnings using statistical methods, machine learning, and time series analysis.

Author: AI Assistant
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
import json
import logging
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import zscore, median_abs_deviation
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.decomposition import PCA
from sklearn.covariance import EllipticEnvelope
import joblib
import os
from collections import deque
import threading
import time
import pickle
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """Anomaly severity levels."""
    NORMAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AnomalyType(Enum):
    """Types of environmental anomalies."""
    TEMPERATURE_SPIKE = "temperature_spike"
    TEMPERATURE_DROP = "temperature_drop"
    PRESSURE_ANOMALY = "pressure_anomaly"
    HUMIDITY_ANOMALY = "humidity_anomaly"
    AIR_QUALITY_DEGRADATION = "air_quality_degradation"
    WIND_SPEED_ANOMALY = "wind_speed_anomaly"
    PRECIPITATION_ANOMALY = "precipitation_anomaly"
    MULTIVARIATE_ANOMALY = "multivariate_anomaly"
    SEASONAL_ANOMALY = "seasonal_anomaly"
    TREND_SHIFT = "trend_shift"


@dataclass
class AnomalyReport:
    """Data structure for anomaly reports."""
    timestamp: datetime
    parameter: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    value: float
    expected_value: float
    threshold: float
    confidence_score: float
    description: str
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EarlyWarning:
    """Data structure for early warnings."""
    timestamp: datetime
    parameter: str
    predicted_anomaly_type: AnomalyType
    predicted_severity: AnomalySeverity
    prediction_time_horizon: int  # hours ahead
    current_trend: str
    risk_score: float
    confidence: float
    mitigation_strategies: List[str]
    affected_areas: List[str]


class DataPreprocessor:
    """
    Data preprocessing class for environmental data.
    Handles missing values, outliers, normalization, and feature engineering.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.scalers = {}
        self.rolling_windows = self.config.get('rolling_windows', [1, 3, 6, 12, 24])
        self.outlier_method = self.config.get('outlier_method', 'iqr')
        self.normalization_method = self.config.get('normalization_method', 'standard')
        
    def handle_missing_values(self, df: pd.DataFrame, method: str = 'interpolate') -> pd.DataFrame:
        """
        Handle missing values in the dataset.
        
        Args:
            df: Input dataframe
            method: Method to handle missing values ('interpolate', 'ffill', 'bfill', 'drop')
            
        Returns:
            DataFrame with handled missing values
        """
        df_clean = df.copy()
        
        if method == 'interpolate':
            df_clean = df_clean.interpolate(method='time', limit_area='inside')
            df_clean = df_clean.bfill().ffill()
        elif method == 'ffill':
            df_clean = df_clean.ffill()
        elif method == 'bfill':
            df_clean = df_clean.bfill()
        elif method == 'drop':
            df_clean = df_clean.dropna()
        else:
            raise ValueError(f"Unknown method: {method}")
            
        logger.info(f"Handled missing values using {method} method")
        return df_clean
    
    def remove_outliers(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Remove outliers from the dataset.
        
        Args:
            df: Input dataframe
            method: Outlier removal method ('iqr', 'zscore', 'mad')
            
        Returns:
            DataFrame with outliers removed
        """
        method = method or self.outlier_method
        df_clean = df.copy()
        
        for column in df_clean.select_dtypes(include=[np.number]).columns:
            if method == 'iqr':
                Q1 = df_clean[column].quantile(0.25)
                Q3 = df_clean[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df_clean[column] = df_clean[column].clip(lower_bound, upper_bound)
                
            elif method == 'zscore':
                z_scores = np.abs(zscore(df_clean[column].values))
                threshold = self.config.get('zscore_threshold', 3)
                df_clean[column] = df_clean[column].mask(z_scores > threshold, df_clean[column].mean())
                
            elif method == 'mad':
                median = df_clean[column].median()
                mad = median_abs_deviation(df_clean[column].values)
                threshold = self.config.get('mad_threshold', 3)
                df_clean[column] = df_clean[column].mask(
                    np.abs(df_clean[column] - median) > threshold * mad,
                    median
                )
                
        logger.info(f"Removed outliers using {method} method")
        return df_clean
    
    def normalize_data(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Normalize the data.
        
        Args:
            df: Input dataframe
            method: Normalization method ('standard', 'minmax', 'robust')
            
        Returns:
            Normalized dataframe
        """
        method = method or self.normalization_method
        df_norm = df.copy()
        numeric_cols = df_norm.select_dtypes(include=[np.number]).columns
        
        if method == 'standard':
            for col in numeric_cols:
                scaler = StandardScaler()
                df_norm[col] = scaler.fit_transform(df_norm[[col]].values)
                self.scalers[f'{col}_scaler'] = scaler
                
        elif method == 'minmax':
            for col in numeric_cols:
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
                
        elif method == 'robust':
            for col in numeric_cols:
                median = df_norm[col].median()
                q1 = df_norm[col].quantile(0.25)
                q3 = df_norm[col].quantile(0.75)
                iqr = q3 - q1
                df_norm[col] = (df_norm[col] - median) / iqr if iqr != 0 else df_norm[col]
                
        logger.info(f"Normalized data using {method} method")
        return df_norm
    
    def create_features(self, df: pd.DataFrame, target_col: str = None) -> pd.DataFrame:
        """
        Create additional features from the data.
        
        Args:
            df: Input dataframe
            target_col: Target column for lag features
            
        Returns:
            DataFrame with additional features
        """
        df_features = df.copy()
        
        # Add rolling statistics
        for window in self.rolling_windows:
            for col in df_features.select_dtypes(include=[np.number]).columns:
                df_features[f'{col}_rolling_mean_{window}'] = df_features[col].rolling(window=window).mean()
                df_features[f'{col}_rolling_std_{window}'] = df_features[col].rolling(window=window).std()
                df_features[f'{col}_rolling_min_{window}'] = df_features[col].rolling(window=window).min()
                df_features[f'{col}_rolling_max_{window}'] = df_features[col].rolling(window=window).max()
        
        # Add lag features
        if target_col:
            for lag in [1, 3, 6, 12, 24]:
                df_features[f'{target_col}_lag_{lag}'] = df_features[target_col].shift(lag)
        
        # Add rate of change features
        for col in df_features.select_dtypes(include=[np.number]).columns:
            df_features[f'{col}_diff_1'] = df_features[col].diff()
            df_features[f'{col}_diff_3'] = df_features[col].diff(3)
            df_features[f'{col}_pct_change'] = df_features[col].pct_change()
        
        # Add time-based features
        if 'timestamp' in df_features.columns:
            df_features['hour'] = df_features['timestamp'].dt.hour
            df_features['day_of_week'] = df_features['timestamp'].dt.dayofweek
            df_features['month'] = df_features['timestamp'].dt.month
            df_features['quarter'] = df_features['timestamp'].dt.quarter
            df_features['is_weekend'] = df_features['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
            df_features['day_of_year'] = df_features['timestamp'].dt.dayofyear
            df_features['week_of_year'] = df_features['timestamp'].dt.isocalendar().week
        
        logger.info("Created additional features")
        return df_features


class AnomalyDetector(ABC):
    """
    Abstract base class for anomaly detection algorithms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.threshold = src.core.config.get('threshold', 0.95)
        
    @abstractmethod
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the anomaly detection model."""
        pass
    
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies in the data."""
        pass
    
    @abstractmethod
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        pass


class StatisticalAnomalyDetector(AnomalyDetector):
    """
    Statistical methods for anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'zscore')
        self.window_size = self.config.get('window_size', 30)
        self.upper_threshold = self.config.get('upper_threshold', 3.0)
        self.lower_threshold = self.config.get('lower_threshold', 3.0)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit statistical model parameters."""
        self.data_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            self.data_stats[col] = {
                'mean': data[col].mean(),
                'std': data[col].std(),
                'median': data[col].median(),
                'mad': median_abs_deviation(data[col].values),
                'q1': data[col].quantile(0.25),
                'q3': data[col].quantile(0.75),
                'min': data[col].min(),
                'max': data[col].max(),
                'seasonal_pattern': self._compute_seasonal_pattern(data, col)
            }
            
        logger.info("Statistical model fitted successfully")
    
    def _compute_seasonal_pattern(self, data: pd.DataFrame, col: str) -> np.ndarray:
        """Compute seasonal pattern for a column."""
        if len(data) < self.seasonal_period * 2:
            return np.array([])
            
        # Compute average pattern for each period
        n_periods = len(data) // self.seasonal_period
        if n_periods < 1:
            return np.array([])
            
        pattern = np.zeros(self.seasonal_period)
        for i in range(self.seasonal_period):
            values = data[col].iloc[i::self.seasonal_period]
            if len(values) > 0:
                pattern[i] = values.mean()
                
        return pattern
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using statistical methods."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            for idx, value in enumerate(values):
                if idx < len(data):
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    if self.method == 'zscore':
                        zscore_value = (value - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
                        if abs(zscore_value) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, zscore_value, 
                                'zscore_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'mad':
                        mad_score = (value - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
                        if abs(mad_score) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, mad_score,
                                'mad_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'iqr':
                        q1 = stats_info.get('q1', 0)
                        q3 = stats_info.get('q3', 0)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        if value < lower_bound or value > upper_bound:
                            severity = AnomalySeverity.HIGH if abs(value - stats_info.get('median', 0)) > 3 * iqr else AnomalySeverity.MEDIUM
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, (value - stats_info.get('median', 0)) / (iqr + 1e-10),
                                'iqr_anomaly', severity
                            ))
                            
        return reports
    
    def _create_anomaly_report(self, timestamp, col, value, score, anomaly_type, severity):
        """Create an anomaly src.reporting.report."""
        return AnomalyReport(
            timestamp=timestamp or datetime.now(),
            parameter=col,
            anomaly_type=AnomalyType.TEMPERATURE_SPIKE,  # Placeholder
            severity=severity,
            value=float(value),
            expected_value=float(self.data_stats.get(col, {}).get('mean', value)),
            threshold=float(self.upper_threshold),
            confidence_score=min(1.0, abs(score) / self.upper_threshold),
            description=f"Statistical anomaly detected in {col} with score {score:.2f}",
            recommendations=["Investigate data source", "Check sensor calibration"],
            metadata={'score': score, 'method': self.method}
        )
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            if self.method == 'zscore':
                col_scores = (values - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
            elif self.method == 'mad':
                col_scores = (values - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
            else:
                col_scores = np.zeros_like(values)
                
            scores.append(np.abs(col_scores))
            
        return np.column_stack(scores) if scores else np.array([])


class MachineLearningAnomalyDetector(AnomalyDetector):
    """
    Machine learning-based anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.algorithm = self.config.get('algorithm', 'isolation_forest')
        self.contamination = self.config.get('contamination', 0.1)
        self.n_estimators = self.config.get('n_estimators', 100)
        self.feature_columns = self.config.get('feature_columns', [])
        self.scaler = StandardScaler()
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the machine learning model."""
        features = self._prepare_features(data)
        
        if self.algorithm == 'isolation_forest':
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42
            )
        elif self.algorithm == 'one_class_svm':
            self.model = OneClassSVM(
                nu=self.contamination,
                kernel='rbf',
                gamma='auto'
            )
        elif self.algorithm == 'local_outlier_factor':
            self.model = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=True
            )
        elif self.algorithm == 'elliptic_envelope':
            self.model = EllipticEnvelope(
                contamination=self.contamination,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
            
        self.model.fit(features)
        logger.info(f"ML model {self.algorithm} fitted successfully")
    
    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare features for the model."""
        if self.feature_columns:
            features = data[self.feature_columns].values
        else:
            features = data.select_dtypes(include=[np.number]).values
            
        # Handle missing values
        features = np.nan_to_num(features, nan=0.0)
        
        # Scale features
        features = self.scaler.fit_transform(features)
        
        return features
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ML model."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        predictions = self.model.predict(features)
        scores = self.model.score_samples(features) if hasattr(self.model, 'score_samples') else None
        
        reports = []
        for idx, pred in enumerate(predictions):
            if pred == -1:  # Anomaly
                timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                severity = self._determine_severity(scores[idx] if scores is not None else 0)
                
                reports.append(AnomalyReport(
                    timestamp=timestamp or datetime.now(),
                    parameter="multivariate",
                    anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                    severity=severity,
                    value=float(scores[idx] if scores is not None else 0),
                    expected_value=0.0,
                    threshold=0.0,
                    confidence_score=1.0 if scores is None else min(1.0, abs(scores[idx])),
                    description=f"ML-based anomaly detected by {self.algorithm}",
                    recommendations=["Check all environmental parameters", "Validate sensor data"],
                    metadata={'algorithm': self.algorithm, 'prediction': int(pred)}
                ))
                
        return reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on anomaly score."""
        if abs(score) > 0.8:
            return AnomalySeverity.CRITICAL
        elif abs(score) > 0.6:
            return AnomalySeverity.HIGH
        elif abs(score) > 0.4:
            return AnomalySeverity.MEDIUM
        elif abs(score) > 0.2:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        
        if hasattr(self.model, 'score_samples'):
            return -self.model.score_samples(features)
        else:
            predictions = self.model.predict(features)
            return np.where(predictions == -1, 1.0, 0.0)


class TimeSeriesAnomalyDetector(AnomalyDetector):
    """
    Time series-based anomaly detection using decomposition and forecasting.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'stl_decomposition')
        self.forecast_horizon = self.config.get('forecast_horizon', 24)
        self.confidence_interval = self.config.get('confidence_interval', 0.95)
        self.trend_window = self.config.get('trend_window', 30)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit time series src.notifications.models."""
        self.time_series_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            n = len(values)
            
            # Store basic statistics
            self.time_series_stats[col] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'trend': self._compute_trend(values),
                'seasonal': self._compute_seasonal(values),
                'residual': self._compute_residual(values),
                'acf': self._compute_acf(values),
                'pacf': self._compute_pacf(values)
            }
            
        logger.info("Time series model fitted successfully")
    
    def _compute_trend(self, values: np.ndarray) -> np.ndarray:
        """Compute trend component using smoothing."""
        if len(values) < self.trend_window:
            return np.zeros_like(values)
        return savgol_filter(values, window_length=min(self.trend_window, len(values)-1), polyorder=3)
    
    def _compute_seasonal(self, values: np.ndarray) -> np.ndarray:
        """Compute seasonal component."""
        if len(values) < self.seasonal_period * 2:
            return np.zeros_like(values)
            
        n = len(values)
        seasonal = np.zeros(n)
        for i in range(self.seasonal_period):
            indices = range(i, n, self.seasonal_period)
            if len(indices) > 0:
                seasonal[indices] = np.mean(values[indices]) - np.mean(values)
                
        return seasonal
    
    def _compute_residual(self, values: np.ndarray) -> np.ndarray:
        """Compute residual component."""
        trend = self._compute_trend(values)
        seasonal = self._compute_seasonal(values)
        return values - trend - seasonal
    
    def _compute_acf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute autocorrelation function."""
        n = len(values)
        mean = np.mean(values)
        var = np.var(values)
        if var == 0:
            return np.zeros(nlags + 1)
            
        acf = np.zeros(nlags + 1)
        for lag in range(nlags + 1):
            if lag < n:
                acf[lag] = np.corrcoef(values[:-lag] if lag > 0 else values, 
                                      values[lag:] if lag > 0 else values)[0, 1]
        return acf
    
    def _compute_pacf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute partial autocorrelation function."""
        n = len(values)
        pacf = np.zeros(nlags + 1)
        pacf[0] = 1.0
        
        if n > 1:
            for lag in range(1, min(nlags + 1, n)):
                # Simple approximation using OLS
                y = values[lag:]
                X = np.column_stack([values[i:-(lag-i)] for i in range(lag+1)])
                if X.shape[0] > 0:
                    try:
                        coeff = np.linalg.lstsq(X, y, rcond=None)[0]
                        pacf[lag] = coeff[-1]
                    except:
                        pacf[lag] = 0
                        
        return pacf
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using time series analysis."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats = self.time_series_stats.get(col, {})
            
            if len(values) < 2:
                continue
                
            # Decompose time series
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            # Calculate anomaly scores
            residual_std = np.std(residual)
            z_scores = np.abs(residual / (residual_std + 1e-10))
            
            # Detect anomalies
            threshold = stats.norm.ppf(self.confidence_interval)
            
            for idx, z_score in enumerate(z_scores):
                if z_score > threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    severity = self._determine_severity(z_score)
                    
                    reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter=col,
                        anomaly_type=AnomalyType.SEASONAL_ANOMALY if abs(seasonal[idx]) > 0.5 * abs(values[idx]) else AnomalyType.TREND_SHIFT,
                        severity=severity,
                        value=float(values[idx]),
                        expected_value=float(trend[idx] + seasonal[idx]),
                        threshold=float(threshold * residual_std),
                        confidence_score=min(1.0, z_score / (threshold * 2)),
                        description=f"Time series anomaly detected in {col} with z-score {z_score:.2f}",
                        recommendations=["Check for sudden environmental changes", "Validate with other sensors"],
                        metadata={
                            'z_score': float(z_score),
                            'trend': float(trend[idx]),
                            'seasonal': float(seasonal[idx]),
                            'residual': float(residual[idx])
                        }
                    ))
                    
        return reports
    
    def _determine_severity(self, z_score: float) -> AnomalySeverity:
        """Determine severity based on z-score."""
        if z_score > 6.0:
            return AnomalySeverity.CRITICAL
        elif z_score > 4.0:
            return AnomalySeverity.HIGH
        elif z_score > 3.0:
            return AnomalySeverity.MEDIUM
        elif z_score > 2.0:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores based on residuals."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            residual_std = np.std(residual) + 1e-10
            col_scores = np.abs(residual / residual_std)
            scores.append(col_scores)
            
        return np.column_stack(scores) if scores else np.array([])


class EnsembleAnomalyDetector(AnomalyDetector):
    """
    Ensemble approach combining multiple anomaly detection methods.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.detectors = []
        self.weights = self.config.get('weights', [])
        self.voting_method = self.config.get('voting_method', 'weighted')
        self._initialize_detectors()
        
    def _initialize_detectors(self) -> None:
        """Initialize individual detectors."""
        detector_configs = self.config.get('detectors', [
            {'type': 'statistical', 'method': 'zscore'},
            {'type': 'statistical', 'method': 'mad'},
            {'type': 'machine_learning', 'algorithm': 'isolation_forest'},
            {'type': 'time_series', 'method': 'stl_decomposition'}
        ])
        
        for config in detector_configs:
            detector_type = src.core.config.get('type')
            if detector_type == 'statistical':
                detector = StatisticalAnomalyDetector(config)
            elif detector_type == 'machine_learning':
                detector = MachineLearningAnomalyDetector(config)
            elif detector_type == 'time_series':
                detector = TimeSeriesAnomalyDetector(config)
            else:
                continue
                
            self.detectors.append(detector)
            
        if not self.weights:
            self.weights = [1.0 / len(self.detectors)] * len(self.detectors)
            
    def fit(self, data: pd.DataFrame) -> None:
        """Fit all detectors."""
        for detector in self.detectors:
            detector.fit(data)
        logger.info("All ensemble detectors fitted successfully")
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ensemble approach."""
        all_reports = []
        detector_scores = []
        
        for detector in self.detectors:
            reports = detector.detect(data)
            all_reports.extend(reports)
            
            # Get scores for voting
            scores = detector.predict_score(data)
            if scores.size > 0:
                detector_scores.append(scores.mean(axis=1))
                
        # Apply ensemble voting
        if detector_scores and self.voting_method == 'weighted':
            ensemble_scores = np.average(detector_scores, weights=self.weights, axis=0)
            
            # Create ensemble reports
            for idx, score in enumerate(ensemble_scores):
                if score > self.threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    all_reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter="ensemble",
                        anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                        severity=self._determine_severity(score),
                        value=float(score),
                        expected_value=0.0,
                        threshold=float(self.threshold),
                        confidence_score=min(1.0, score / self.threshold),
                        description=f"Ensemble anomaly detected with score {score:.2f}",
                        recommendations=["Verify with multiple data sources", "Cross-check all parameters"],
                        metadata={'ensemble_score': float(score), 'n_detectors': len(self.detectors)}
                    ))
                    
        return all_reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on ensemble score."""
        if score > 0.8 * self.threshold:
            return AnomalySeverity.CRITICAL
        elif score > 0.6 * self.threshold:
            return AnomalySeverity.HIGH
        elif score > 0.4 * self.threshold:
            return AnomalySeverity.MEDIUM
        elif score > 0.2 * self.threshold:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores using ensemble."""
        scores = []
        
        for detector in self.detectors:
            detector_scores = detector.predict_score(data)
            if detector_scores.size > 0:
                scores.append(detector_scores)
                
        if scores:
            weighted_scores = np.average(scores, weights=self.weights, axis=0)
            return weighted_scores
        else:
            return np.array([])


class EarlyWarningSystem:
    """
    Early warning system for environmental anomalies.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.historical_data = deque(maxlen=self.config.get('history_length', 1000))
        self.warning_thresholds = self.config.get('warning_thresholds', {})
        self.trend_analysis_window = self.config.get('trend_window', 24)
        self.forecast_horizons = self.config.get('forecast_horizons', [1, 3, 6, 12, 24])
        self.detector = None
        self.monitoring_active = False
        self.monitoring_thread = None
        self.warning_history = deque(maxlen=100)
        self.alert_callbacks = []
        
    def initialize_detector(self, detector_type: str = 'ensemble', **kwargs) -> None:
        """Initialize the anomaly detector."""
        config = self.config.copy()
        src.core.config.update(kwargs)
        
        if detector_type == 'statistical':
            self.detector = StatisticalAnomalyDetector(config)
        elif detector_type == 'machine_learning':
            self.detector = MachineLearningAnomalyDetector(config)
        elif detector_type == 'time_series':
            self.detector = TimeSeriesAnomalyDetector(config)
        elif detector_type == 'ensemble':
            self.detector = EnsembleAnomalyDetector(config)
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
            
        logger.info(f"Initialized {detector_type} detector for early warning system")
    
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the detector with historical data."""
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        self.detector.fit(data)
        self.historical_data.extend(data.values.tolist())
        logger.info("Early warning system fitted with historical data")
    
    def detect_anomalies(self, data: pd.DataFrame) -> Tuple[List[AnomalyReport], List[EarlyWarning]]:
        """
        Detect anomalies and generate early warnings.
        
        Returns:
            Tuple of (anomaly_reports, early_warnings)
        """
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        # Detect anomalies
        anomaly_reports = self.detector.detect(data)
        
        # Generate early warnings
        early_warnings = self._generate_early_warnings(data, anomaly_reports)
        
        # Update historical data
        self.historical_data.extend(data.values.tolist())
        self.warning_history.extend(early_warnings)
        
        # Trigger alerts
        self._trigger_alerts(anomaly_reports, early_warnings)
        
        return anomaly_reports, early_warnings
    
    def _generate_early_warnings(self, data: pd.DataFrame, anomalies: List[AnomalyReport]) -> List[EarlyWarning]:
        """Generate early warnings based
