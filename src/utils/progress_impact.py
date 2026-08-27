#!/usr/bin/env python3
"""
Sustainability Progress & Impact Analytics - Module 2: Advanced Analytics & Visualization
Comprehensive analytics, ML, and visualization engine for sustainability impact assessment.

Version: 1.0.0
Author: Sustainability Analytics Team
License: MIT
"""

import json
import math
import random
import statistics
import datetime
import uuid
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
from functools import lru_cache
import numpy as np
from scipy import stats
from scipy.optimize import minimize
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

# ============================================================================
# Configuration and Constants
# ============================================================================

VERSION = "1.0.0"
LOG_FILE = "spia_advanced_log.txt"

# ============================================================================
# Enums and Data Models
# ============================================================================

class ModelType(Enum):
    """Types of ML models."""
    LINEAR_REGRESSION = auto()
    RIDGE = auto()
    LASSO = auto()
    RANDOM_FOREST = auto()
    NEURAL_NETWORK = auto()
    ARIMA = auto()

class ScenarioType(Enum):
    """Scenario analysis types."""
    BEST_CASE = auto()
    WORST_CASE = auto()
    LIKELY = auto()
    OPTIMISTIC = auto()
    PESSIMISTIC = auto()
    CUSTOM = auto()

@dataclass
class MLModel:
    """Machine learning model for sustainability analytics."""
    id: str
    name: str
    model_type: ModelType
    features: List[str]
    target: str
    model: Any = None
    scaler: StandardScaler = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    trained_date: datetime.datetime = field(default_factory=datetime.datetime.now)
    training_data_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScenarioAnalysis:
    """Scenario analysis results."""
    id: str
    name: str
    scenario_type: ScenarioType
    assumptions: Dict[str, float]
    results: Dict[str, float]
    confidence_interval: Tuple[float, float]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualizationData:
    """Data for visualization and charts."""
    chart_type: str
    title: str
    x_axis_label: str
    y_axis_label: str
    data: List[Dict[str, Any]]
    colors: Optional[List[str]] = None
    annotations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# Advanced Analytics Engine
# ============================================================================

class AdvancedAnalyticsEngine:
    """Advanced analytics engine with ML and statistical capabilities."""
    
    def __init__(self, tracker):
        self.tracker = tracker
        self.models: List[MLModel] = []
        self.scenarios: List[ScenarioAnalysis] = []
        self.feature_cache = {}
        
    def prepare_features(self, metric_names: List[str], lookback_days: int = 30) -> np.ndarray:
        """Prepare feature matrix for ML models."""
        features = []
        for metric_name in metric_names:
            metrics = [m for m in self.tracker.metrics if m.name == metric_name]
            if metrics:
                sorted_metrics = sorted(metrics, key=lambda x: x.timestamp)[-lookback_days:]
                values = [m.value for m in sorted_metrics]
                features.append(values)
                
        if not features:
            return np.array([])
            
        # Pad sequences to same length
        max_len = max(len(f) for f in features)
        padded = []
        for f in features:
            if len(f) < max_len:
                f = f + [f[-1]] * (max_len - len(f))
            padded.append(f)
            
        return np.array(padded).T
        
    def train_model(self, features: List[str], target: str, model_type: ModelType = ModelType.LINEAR_REGRESSION) -> MLModel:
        """Train a machine learning model."""
        # Prepare data
        X = self.prepare_features(features, lookback_days=90)
        if X.shape[0] < 10:
            raise ValueError("Insufficient data for training")
            
        target_metrics = [m for m in self.tracker.metrics if m.name == target]
        if not target_metrics:
            raise ValueError(f"Target metric '{target}' not found")
            
        y = np.array([m.value for m in sorted(target_metrics, key=lambda x: x.timestamp)[-X.shape[0]:]])
        
        if len(y) != X.shape[0]:
            y = y[:X.shape[0]]
            
        # Split data
        split_idx = int(0.8 * len(X))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Scale data
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Select and train model
        model = None
        if model_type == ModelType.LINEAR_REGRESSION:
            model = LinearRegression()
        elif model_type == ModelType.RIDGE:
            model = Ridge(alpha=1.0)
        elif model_type == ModelType.LASSO:
            model = Lasso(alpha=0.1)
        elif model_type == ModelType.RANDOM_FOREST:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
            
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Store model
        ml_model = MLModel(
            id=str(uuid.uuid4()),
            name=f"{target}_model",
            model_type=model_type,
            features=features,
            target=target,
            model=model,
            scaler=scaler,
            performance_metrics={
                "mse": mse,
                "rmse": np.sqrt(mse),
                "r2": r2,
                "training_size": len(X_train),
                "test_size": len(X_test)
            }
        )
        
        self.models.append(ml_model)
        return ml_model
        
    def predict_with_model(self, model_id: str, new_data: np.ndarray) -> Dict[str, Any]:
        """Make predictions using trained model."""
        model = next((m for m in self.models if m.id == model_id), None)
        if not model:
            raise ValueError(f"Model {model_id} not found")
            
        if model.scaler:
            X_scaled = model.scaler.transform(new_data)
            predictions = model.model.predict(X_scaled)
        else:
            predictions = model.model.predict(new_data)
            
        return {
            "predictions": predictions.tolist(),
            "model_id": model_id,
            "target": model.target,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    def perform_scenario_analysis(self, scenario_type: ScenarioType, 
                                  base_metrics: Dict[str, float],
                                  adjustments: Dict[str, float]) -> ScenarioAnalysis:
        """Perform scenario analysis with custom adjustments."""
        results = {}
        confidence_interval = (0, 0)
        
        # Apply adjustments to base metrics
        adjusted_metrics = base_metrics.copy()
        for metric, adjustment in adjustments.items():
            if metric in adjusted_metrics:
                if scenario_type == ScenarioType.OPTIMISTIC:
                    adjusted_metrics[metric] *= (1 + adjustment)
                elif scenario_type == ScenarioType.PESSIMISTIC:
                    adjusted_metrics[metric] *= (1 - adjustment)
                else:
                    adjusted_metrics[metric] += adjustment * np.random.normal(0, 0.1)
                    
        # Calculate impact scores
        for category in IMPACT_CATEGORIES:
            if category in adjusted_metrics:
                impact = adjusted_metrics[category] * IMPACT_WEIGHTS.get(category, 0.1)
                results[category] = impact
                
        # Monte Carlo simulation for confidence intervals
        simulations = 1000
        sim_results = []
        for _ in range(simulations):
            sim_metrics = base_metrics.copy()
            for metric, value in sim_metrics.items():
                noise = np.random.normal(0, 0.05 * value)
                sim_metrics[metric] = max(0, value + noise)
            sim_results.append(sum(sim_metrics.values()))
            
        confidence_interval = (
            np.percentile(sim_results, 5),
            np.percentile(sim_results, 95)
        )
        
        scenario = ScenarioAnalysis(
            id=str(uuid.uuid4()),
            name=f"{scenario_type.name}_scenario_{datetime.datetime.now().strftime('%Y%m%d')}",
            scenario_type=scenario_type,
            assumptions=adjustments,
            results=results,
            confidence_interval=confidence_interval,
            metadata={
                "base_metrics": base_metrics,
                "simulations": simulations
            }
        )
        
        self.scenarios.append(scenario)
        return scenario
        
    def perform_sensitivity_analysis(self, base_metrics: Dict[str, float],
                                     parameters: List[str],
                                     ranges: Dict[str, List[float]]) -> Dict[str, Any]:
        """Perform sensitivity analysis on key parameters."""
        sensitivity_results = {}
        
        for param in parameters:
            if param not in ranges:
                continue
                
            param_sensitivity = []
            for value in ranges[param]:
                test_metrics = base_metrics.copy()
                test_metrics[param] = value
                
                # Calculate impact
                impact = sum(test_metrics.get(c, 0) * IMPACT_WEIGHTS.get(c, 0.1) 
                           for c in IMPACT_CATEGORIES)
                param_sensitivity.append({
                    "parameter_value": value,
                    "impact_score": impact
                })
                
            sensitivity_results[param] = param_sensitivity
            
        return sensitivity_results
        
    def detect_anomalies_advanced(self, metric_name: str, 
                                  method: str = "isolation_forest",
                                  contamination: float = 0.1) -> Dict[str, Any]:
        """Advanced anomaly detection using multiple methods."""
        metrics = [m for m in self.tracker.metrics if m.name == metric_name]
        if not metrics:
            return {"error": "Metric not found"}
            
        sorted_metrics = sorted(metrics, key=lambda x: x.timestamp)
        values = np.array([m.value for m in sorted_metrics]).reshape(-1, 1)
        
        anomalies = []
        anomaly_scores = []
        
        if method == "z_score":
            mean_val = np.mean(values)
            std_val = np.std(values)
            if std_val > 0:
                z_scores = np.abs((values - mean_val) / std_val)
                threshold = 2.5
                anomaly_scores = z_scores.flatten().tolist()
                anomalies = [i for i, z in enumerate(z_scores) if z > threshold]
                
        elif method == "iqr":
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            anomalies = [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]
            
        elif method == "dbscan":
            if len(values) > 2:
                scaler = StandardScaler()
                values_scaled = scaler.fit_transform(values)
                clustering = DBSCAN(eps=0.5, min_samples=2).fit(values_scaled)
                anomalies = [i for i, label in enumerate(clustering.labels_) if label == -1]
                
        else:  # isolation_forest
            from sklearn.ensemble import IsolationForest
            scaler = StandardScaler()
            values_scaled = scaler.fit_transform(values)
            iso_forest = IsolationForest(contamination=contamination, random_state=42)
            predictions = iso_forest.fit_predict(values_scaled)
            anomalies = [i for i, pred in enumerate(predictions) if pred == -1]
            
        return {
            "metric_name": metric_name,
            "anomaly_indices": anomalies,
            "anomaly_count": len(anomalies),
            "total_points": len(values),
            "anomaly_percentage": (len(anomalies) / len(values) * 100) if len(values) > 0 else 0,
            "anomaly_values": [float(values[i][0]) for i in anomalies if i < len(values)],
            "anomaly_dates": [sorted_metrics[i].timestamp.isoformat() for i in anomalies if i < len(sorted_metrics)],
            "anomaly_scores": anomaly_scores if anomaly_scores else []
        }
        
    def perform_clustering_analysis(self, features: List[str], 
                                    n_clusters: int = 3) -> Dict[str, Any]:
        """Perform clustering analysis on sustainability data."""
        # Prepare data
        X = self.prepare_features(features, lookback_days=30)
        if X.shape[0] < n_clusters:
            return {"error": "Insufficient data for clustering"}
            
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Analyze clusters
        cluster_summary = {}
        for i in range(n_clusters):
            cluster_mask = clusters == i
            cluster_data = X[cluster_mask]
            if len(cluster_data) > 0:
                cluster_summary[i] = {
                    "size": int(np.sum(cluster_mask)),
                    "mean_values": np.mean(cluster_data, axis=0).tolist(),
                    "std_values": np.std(cluster_data, axis=0).tolist(),
                    "center": kmeans.cluster_centers_[i].tolist()
                }
                
        return {
            "n_clusters": n_clusters,
            "labels": clusters.tolist(),
            "centers": kmeans.cluster_centers_.tolist(),
            "inertia": kmeans.inertia_,
            "cluster_summary": cluster_summary,
            "features": features
        }

# ============================================================================
# Visualization Engine
# ============================================================================

class VisualizationEngine:
    """Advanced visualization and dashboard engine."""
    
    def __init__(self, tracker):
        self.tracker = tracker
        self.analytics = AdvancedAnalyticsEngine(tracker)
        self.chart_cache = {}
        
    def create_progress_dashboard(self) -> Dict[str, List[VisualizationData]]:
        """Create comprehensive progress dashboard."""
        dashboard = {}
        
        # 1. Overall progress gauge
        overall_progress = self._calculate_overall_progress()
        dashboard["progress_gauge"] = [VisualizationData(
            chart_type="gauge",
            title="Overall Sustainability Progress",
            x_axis_label="Progress",
            y_axis_label="Percentage",
            data=[{"value": overall_progress}],
            metadata={"target": 100, "unit": "%"}
        )]
        
        # 2. Category performance chart
        category_data = self._get_category_performance()
        dashboard["category_performance"] = [VisualizationData(
            chart_type="bar",
            title="Category Performance",
            x_axis_label="Category",
            y_axis_label="Score",
            data=[{"category": k, "score": v} for k, v in category_data.items()],
            colors=["#2ecc71", "#3498db", "#e74c3c", "#f39c12", "#9b59b6"],
            metadata={"max_score": 100}
        )]
        
        # 3. Progress trend chart
        trend_data = self._get_progress_trend()
        dashboard["progress_trend"] = [VisualizationData(
            chart_type="line",
            title="Progress Trends Over Time",
            x_axis_label="Date",
            y_axis_label="Progress (%)",
            data=trend_data,
            colors=["#3498db"],
            metadata={"fill": True}
        )]
        
        # 4. Project status distribution
        status_data = self._get_project_status()
        dashboard["project_status"] = [VisualizationData(
            chart_type="pie",
            title="Project Status Distribution",
            x_axis_label="Status",
            y_axis_label="Count",
            data=[{"status": k, "count": v} for k, v in status_data.items()],
            colors=["#2ecc71", "#f39c12", "#e74c3c", "#95a5a6", "#3498db"],
            metadata={"show_percentage": True}
        )]
        
        # 5. Impact heatmap
        heatmap_data = self._get_impact_heatmap()
        dashboard["impact_heatmap"] = [VisualizationData(
            chart_type="heatmap",
            title="Impact Heatmap by Category",
            x_axis_label="Metric",
            y_axis_label="Category",
            data=heatmap_data,
            metadata={"colormap": "YlOrRd"}
        )]
        
        # 6. Velocity chart
        velocity_data = self._get_velocity_metrics()
        dashboard["velocity_metrics"] = [VisualizationData(
            chart_type="bar",
            title="Progress Velocity by Project",
            x_axis_label="Project",
            y_axis_label="Velocity (%/day)",
            data=velocity_data,
            colors=["#9b59b6"],
            metadata={"threshold": 1.0}
        )]
        
        return dashboard
        
    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress percentage."""
        if not self.tracker.indicators:
            return 0.0
        return statistics.mean([i.progress_percent for i in self.tracker.indicators])
        
    def _get_category_performance(self) -> Dict[str, float]:
        """Get performance by category."""
        performance = {}
        for category in IMPACT_CATEGORIES:
            indicators = [i for i in self.tracker.indicators if i.category == category]
            if indicators:
                performance[category] = statistics.mean([i.progress_percent for i in indicators])
            else:
                performance[category] = 0.0
        return performance
        
    def _get_progress_trend(self) -> List[Dict[str, Any]]:
        """Get progress trends over time."""
        trend_data = []
        # Aggregate progress over time from indicator updates
        all_updates = []
        for indicator in self.tracker.indicators:
            for update in indicator.updates:
                all_updates.append({
                    "date": update["timestamp"][:10],
                    "progress": update.get("progress_percent", 0)
                })
                
        # Average by date
        date_groups = defaultdict(list)
        for update in all_updates:
            date_groups[update["date"]].append(update["progress"])
            
        for date in sorted(date_groups.keys()):
            if date_groups[date]:
                trend_data.append({
                    "date": date,
                    "value": statistics.mean(date_groups[date])
                })
                
        return trend_data
        
    def _get_project_status(self) -> Dict[str, int]:
        """Get project status distribution."""
        status_counts = defaultdict(int)
        for project in self.tracker.projects:
            status_counts[project.status.name] += 1
        return dict(status_counts)
        
    def _get_impact_heatmap(self) -> List[Dict[str, Any]]:
        """Generate impact heatmap data."""
        heatmap_data = []
        
        # Get metrics by category
        for category in IMPACT_CATEGORIES:
            category_metrics = [m for m in self.tracker.metrics if m.category == category]
            if category_metrics:
                values = [m.value for m in category_metrics[:5]]  # Top 5 metrics
                for i, metric in enumerate(category_metrics[:5]):
                    heatmap_data.append({
                        "category": category,
                        "metric": metric.name[:20],
                        "value": metric.value,
                        "normalized": min(100, (metric.value / (metric.target or 100)) * 100)
                    })
                    
        return heatmap_data
        
    def _get_velocity_metrics(self) -> List[Dict[str, Any]]:
        """Get velocity metrics by project."""
        velocity_data = []
        for project in self.tracker.projects:
            if project.indicators:
                avg_velocity = statistics.mean([i.velocity for i in project.indicators if i.velocity > 0])
                velocity_data.append({
                    "project": project.name[:20],
                    "velocity": avg_velocity
                })
        return velocity_data
        
    def create_impact_dashboard(self) -> Dict[str, List[VisualizationData]]:
        """Create impact-focused dashboard."""
        dashboard = {}
        
        # 1. Impact score overview
        impact_scores = self._calculate_impact_scores()
        dashboard["impact_scores"] = [VisualizationData(
            chart_type="radar",
            title="Impact Score Overview",
            x_axis_label="Category",
            y_axis_label="Score",
            data=[{"category": k, "score": v} for k, v in impact_scores.items()],
            metadata={"max_score": 100, "min_score": 0}
        )]
        
        # 2. Impact distribution
        distribution_data = self._get_impact_distribution()
        dashboard["impact_distribution"] = [VisualizationData(
            chart_type="pie",
            title="Impact Distribution by Category",
            x_axis_label="Category",
            y_axis_label="Impact",
            data=distribution_data,
            colors=["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"],
            metadata={"show_percentage": True}
        )]
        
        # 3. ROI analysis
        roi_data = self._get_roi_analysis()
        dashboard["roi_analysis"] = [VisualizationData(
            chart_type="bar",
            title="Impact ROI by Project",
            x_axis_label="Project",
            y_axis_label="ROI (%)",
            data=roi_data,
            colors=["#27ae60"],
            metadata={"threshold": 0}
        )]
        
        return dashboard
        
    def _calculate_impact_scores(self) -> Dict[str, float]:
        """Calculate impact scores by category."""
        scores = {}
        for category in IMPACT_CATEGORIES:
            metrics = [m for m in self.tracker.metrics if m.category == category]
            if metrics:
                score = statistics.mean([m.value for m in metrics])
                scores[category] = min(100, score)
            else:
                scores[category] = 0
        return scores
        
    def _get_impact_distribution(self) -> List[Dict[str, Any]]:
        """Get impact distribution by category."""
        distribution = []
        total_impact = sum(m.value for m in self.tracker.metrics if m.value > 0)
        if total_impact > 0:
            for category in IMPACT_CATEGORIES:
                category_impact = sum(m.value for m in self.tracker.metrics 
                                    if m.category == category and m.value > 0)
                if category_impact > 0:
                    distribution.append({
                        "category": category,
                        "impact": category_impact,
                        "percentage": (category_impact / total_impact) * 100
                    })
        return distribution
        
    def _get_roi_analysis(self) -> List[Dict[str, Any]]:
        """Calculate ROI for projects."""
        roi_data = []
        for project in self.tracker.projects:
            if project.budget > 0:
                # Calculate impact value (simplified)
                impact_value = sum(m.value for m in project.impacts) * 10  # $10 per impact unit
                roi = ((impact_value - project.actual_cost) / project.budget) * 100
                roi_data.append({
                    "project": project.name[:20],
                    "roi": roi
                })
        return roi_data
        
    def create_forecast_dashboard(self, forecast_periods: int = 12) -> Dict[str, List[VisualizationData]]:
        """Create forecast and prediction dashboard."""
        dashboard = {}
        
        # Forecast data
        forecast_data = []
        for indicator in self.tracker.indicators[:5]:  # Top 5 indicators
            historical = [u.get("value", 0) for u in indicator.updates[-30:]]
            if len(historical) > 1:
                # Simple linear extrapolation
                x = np.arange(len(historical))
                y = np.array(historical)
                slope, intercept = np.polyfit(x, y, 1)
                forecast = [intercept + slope * (len(historical) + i) for i in range(forecast_periods)]
                
                forecast_data.append({
                    "indicator": indicator.name[:20],
                    "historical": historical,
                    "forecast": forecast,
                    "confidence": 0.8,
                    "dates": [(datetime.datetime.now() + datetime.timedelta(days=i*30)).strftime("%Y-%m") 
                             for i in range(forecast_periods)]
                })
                
        dashboard["forecasts"] = [VisualizationData(
            chart_type="line",
            title="Sustainability Forecast",
            x_axis_label="Time",
            y_axis_label="Value",
            data=forecast_data,
            metadata={"show_confidence": True}
        )]
        
        # Confidence bands
        dashboard["confidence_bands"] = [VisualizationData(
            chart_type="area",
            title="Forecast Confidence Bands",
            x_axis_label="Time",
            y_axis_label="Range",
            data=forecast_data,
            metadata={"show_bands": True}
        )]
        
        return dashboard

# ============================================================================
# API Interface
# ============================================================================

class SustainabilityAnalyticsAPI:
    """API interface for sustainability analytics."""
    
    def __init__(self, tracker):
        self.tracker = tracker
        self.analytics = AdvancedAnalyticsEngine(tracker)
        self.visualization = VisualizationEngine(tracker)
        
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        return {
            "version": VERSION,
            "total_metrics": len(self.tracker.metrics),
            "total_projects": len(self.tracker.projects),
            "total_indicators": len(self.tracker.indicators),
            "total_assessments": len(self.tracker.assessments),
            "models_trained": len(self.analytics.models),
            "scenarios_analyzed": len(self.analytics.scenarios),
            "last_updated": datetime.datetime.now().isoformat()
        }
        
    def train_prediction_model(self, features: List[str], target: str) -> Dict[str, Any]:
        """Train a prediction model."""
        try:
            model = self.analytics.train_model(features, target, ModelType.RANDOM_FOREST)
            return {
                "model_id": model.id,
                "features": model.features,
                "target": model.target,
                "performance": model.performance_metrics,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
            
    def run_scenario_analysis(self, scenario_type: str, adjustments: Dict[str, float]) -> Dict[str, Any]:
        """Run scenario analysis."""
        try:
            # Get current metrics
            current_metrics = {}
            for category in IMPACT_CATEGORIES:
                metrics = [m for m in self.tracker.metrics if m.category == category]
                if metrics:
                    current_metrics[category] = statistics.mean([m.value for m in metrics])
                    
            scenario = self.analytics.perform_scenario_analysis(
                ScenarioType[scenario_type.upper()],
                current_metrics,
                adjustments
            )
            
            return {
                "scenario_id": scenario.id,
                "scenario_type": scenario.scenario_type.name,
                "results": scenario.results,
                "confidence_interval": scenario.confidence_interval,
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
            
    def detect_anomalies(self, metric_name: str, method: str = "z_score") -> Dict[str, Any]:
        """Detect anomalies in metrics."""
        return self.analytics.detect_anomalies_advanced(metric_name, method)
        
    def get_visualization_dashboard(self, dashboard_type: str = "progress") -> Dict[str, Any]:
        """Get visualization dashboard."""
        if dashboard_type == "progress":
            dashboard = self.visualization.create_progress_dashboard()
        elif dashboard_type == "impact":
            dashboard = self.visualization.create_impact_dashboard()
        elif dashboard_type == "forecast":
            dashboard = self.visualization.create_forecast_dashboard()
        else:
            return {"error": f"Unknown dashboard type: {dashboard_type}"}
            
        # Convert to serializable format
        serializable_dashboard = {}
        for key, value in dashboard.items():
            serializable_dashboard[key] = []
            for viz_data in value:
                serializable_dashboard[key].append({
                    "chart_type": viz_data.chart_type,
                    "title": viz_data.title,
                    "x_axis_label": viz_data.x_axis_label,
                    "y_axis_label": viz_data.y_axis_label,
                    "data": viz_data.data,
                    "colors": viz_data.colors,
                    "metadata": viz_data.metadata
                })
                
        return serializable_dashboard
        
    def run_clustering_analysis(self, features: List[str], n_clusters: int = 3) -> Dict[str, Any]:
        """Run clustering analysis."""
        return self.analytics.perform_clustering_analysis(features, n_clusters)
        
    def run_sensitivity_analysis(self, parameters: List[str]) -> Dict[str, Any]:
        """Run sensitivity analysis on parameters."""
        # Get current metrics
        current_metrics = {}
        for category in IMPACT_CATEGORIES:
            metrics = [m for m in self.tracker.metrics if m.category == category]
            if metrics:
                current_metrics[category] = statistics.mean([m.value for m in metrics])
                
        # Define ranges for each parameter
        ranges = {}
        for param in parameters:
            if param in current_metrics:
                base_value = current_metrics[param]
                ranges[param] = [base_value * (0.5 + i * 0.1) for i in range(6)]  # 50% to 100%
                
        return self.analytics.perform_sensitivity_analysis(current_metrics, parameters, ranges)
        
    def generate_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        report = {
            "generated_at": datetime.datetime.now().isoformat(),
            "analytics_summary": self.get_analytics_summary(),
            "progress_dashboard": self.get_visualization_dashboard("progress"),
            "impact_dashboard": self.get_visualization_dashboard("impact"),
            "forecast_dashboard": self.get_visualization_dashboard("forecast"),
            "models": [{
                "id": m.id,
                "name": m.name,
                "type": m.model_type.name,
                "features": m.features,
                "target": m.target,
                "performance": m.performance_metrics
            } for m in self.analytics.models],
            "scenarios": [{
                "id": s.id,
                "name": s.name,
                "type": s.scenario_type.name,
                "assumptions": s.assumptions,
                "results": s.results,
                "confidence_interval": s.confidence_interval
            } for s in self.analytics.scenarios]
        }
        
        return report

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for testing."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Initialize tracker and API
    from sustainability_progress_tracker import ProgressTracker  # Import from module 1
    tracker = ProgressTracker()
    api = SustainabilityAnalyticsAPI(tracker)
    
    # Get analytics summary
    print("=== Analytics Summary ===")
    summary = api.get_analytics_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
        
    # Get progress dashboard
    print("\n=== Progress Dashboard ===")
    dashboard = api.get_visualization_dashboard("progress")
    for key, value in dashboard.items():
        print(f"{key}: {len(value)} charts")
        
    # Run clustering analysis
    print("\n=== Clustering Analysis ===")
    features = [m.name for m in tracker.metrics[:5]]
    if features:
        clusters = api.run_clustering_analysis(features, n_clusters=3)
        print(f"Clusters: {clusters.get('n_clusters', 0)}")
        print(f"Inertia: {clusters.get('inertia', 0):.2f}")
        
    # Run anomaly detection
    print("\n=== Anomaly Detection ===")
    if tracker.metrics:
        anomalies = api.detect_anomalies(tracker.metrics[0].name)
        print(f"Anomalies detected: {anomalies.get('anomaly_count', 0)}")
        
    print("\nAnalytics completed successfully!")

if __name__ == "__main__":
    main()

# ============================================================================
# End of File
# ============================================================================
