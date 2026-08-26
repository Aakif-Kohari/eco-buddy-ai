#!/usr/bin/env python3
"""
Personal Sustainability Roadmap Engine (PSRE)
A comprehensive, single-file Python application for tracking, analyzing,
and optimizing personal sustainability across environmental, social,
and economic dimensions.

Version: 2.0.0
Author: Sustainability Engine Team
License: MIT
"""

import json
import math
import random
import statistics
import hashlib
import datetime
import calendar
import itertools
import collections
import functools
import operator
import re
import os
import sys
import time
import uuid
import base64
import zlib
import csv
import io
import tempfile
import subprocess
import threading
import queue
import logging
import warnings
import enum
import dataclasses
import typing
from typing import Dict, List, Tuple, Optional, Any, Union, Set, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, Counter, deque
from contextlib import contextmanager, suppress
from functools import lru_cache, wraps

# ============================================================================
# Configuration and Constants
# ============================================================================

VERSION = "2.0.0"
CONFIG_FILE = "psre_config.json"
DATA_FILE = "psre_data.json"
LOG_FILE = "psre_log.txt"

SUSTAINABILITY_CATEGORIES = [
    "ENVIRONMENTAL",
    "SOCIAL",
    "ECONOMIC",
    "ENERGY",
    "TRANSPORTATION",
    "FOOD",
    "WASTE",
    "WATER",
    "COMMUNITY",
    "HEALTH",
    "EDUCATION",
    "CAREER"
]

CARBON_FACTORS = {
    "electricity": 0.92,  # kg CO2 per kWh
    "natural_gas": 2.32,  # kg CO2 per therm
    "gasoline": 8.89,     # kg CO2 per gallon
    "diesel": 10.16,      # kg CO2 per gallon
    "air_travel": 0.18,   # kg CO2 per passenger mile
    "car_travel": 0.41,   # kg CO2 per vehicle mile
    "bus_travel": 0.17,   # kg CO2 per passenger mile
    "train_travel": 0.14, # kg CO2 per passenger mile
}

WATER_FACTORS = {
    "shower": 2.5,        # gallons per minute
    "bath": 36,           # gallons per bath
    "toilet": 1.6,        # gallons per flush
    "washing_machine": 40, # gallons per load
    "dishwasher": 6,      # gallons per load
    "faucet": 2.2,        # gallons per minute
    "garden": 10,         # gallons per minute
}

WASTE_FACTORS = {
    "plastic": 0.85,      # kg per item average
    "paper": 0.005,       # kg per sheet
    "glass": 0.5,         # kg per bottle
    "metal": 0.015,       # kg per can
    "organic": 0.5,       # kg per meal waste
    "electronics": 2.5,   # kg per device
}

# ============================================================================
# Utility Functions and Decorators
# ============================================================================

def timer_decorator(func):
    """Decorator to measure execution time of functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logging.debug(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    return wrapper

def validate_input(func):
    """Decorator to validate input parameters."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (ValueError, TypeError) as e:
            logging.error(f"Input validation error in {func.__name__}: {e}")
            raise
    return wrapper

@contextmanager
def safe_file_operation(filepath, mode='r'):
    """Context manager for safe file operations."""
    try:
        with open(filepath, mode) as f:
            yield f
    except FileNotFoundError:
        logging.warning(f"File {filepath} not found")
        yield None
    except Exception as e:
        logging.error(f"Error in file operation {filepath}: {e}")
        raise

# ============================================================================
# Data Models and Enums
# ============================================================================

class SustainabilityDimension(Enum):
    """Main sustainability dimensions."""
    ENVIRONMENTAL = auto()
    SOCIAL = auto()
    ECONOMIC = auto()
    ENERGY = auto()
    TRANSPORTATION = auto()
    FOOD = auto()
    WASTE = auto()
    WATER = auto()
    COMMUNITY = auto()
    HEALTH = auto()
    EDUCATION = auto()
    CAREER = auto()

class ImpactLevel(Enum):
    """Impact severity levels."""
    NEGATIVE_HIGH = 1
    NEGATIVE_MEDIUM = 2
    NEGATIVE_LOW = 3
    NEUTRAL = 4
    POSITIVE_LOW = 5
    POSITIVE_MEDIUM = 6
    POSITIVE_HIGH = 7

class GoalStatus(Enum):
    """Status of sustainability goals."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    ABANDONED = auto()
    ON_HOLD = auto()
    ARCHIVED = auto()

class DataSource(Enum):
    """Data source types."""
    USER_INPUT = auto()
    SENSOR = auto()
    API = auto()
    ESTIMATE = auto()
    CALCULATED = auto()
    IMPORTED = auto()

@dataclass
class SustainabilityMetric:
    """Base metric for sustainability tracking."""
    id: str
    name: str
    dimension: SustainabilityDimension
    value: float
    unit: str
    timestamp: datetime.datetime
    source: DataSource = DataSource.USER_INPUT
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CarbonFootprint:
    """Carbon footprint data structure."""
    total: float  # kg CO2e
    breakdown: Dict[str, float]  # Category -> kg CO2e
    offset: float = 0.0
    date: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class WaterFootprint:
    """Water footprint data structure."""
    total: float  # liters
    breakdown: Dict[str, float]  # Category -> liters
    date: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class WasteFootprint:
    """Waste footprint data structure."""
    total: float  # kg
    recycled: float = 0.0
    composted: float = 0.0
    landfill: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)
    date: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class SustainabilityGoal:
    """Sustainability goal definition."""
    id: str
    title: str
    description: str
    dimension: SustainabilityDimension
    target_value: float
    current_value: float
    unit: str
    deadline: datetime.datetime
    status: GoalStatus = GoalStatus.NOT_STARTED
    created: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated: datetime.datetime = field(default_factory=datetime.datetime.now)
    progress_history: List[Tuple[datetime.datetime, float]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10

@dataclass
class SustainabilityAction:
    """Individual sustainability action."""
    id: str
    name: str
    description: str
    dimension: SustainabilityDimension
    impact: ImpactLevel
    effort: ImpactLevel  # Effort required
    cost: float = 0.0
    co2_reduction: float = 0.0
    water_savings: float = 0.0
    waste_reduction: float = 0.0
    frequency: str = "daily"  # daily, weekly, monthly, yearly
    completed: int = 0
    target: int = 1
    tags: List[str] = field(default_factory=list)

@dataclass
class ProgressReport:
    """Progress report for sustainability metrics."""
    period_start: datetime.datetime
    period_end: datetime.datetime
    metrics: Dict[str, float]
    changes: Dict[str, float]
    goals: List[SustainabilityGoal]
    actions: List[SustainabilityAction]
    recommendations: List[str] = field(default_factory=list)
    score: float = 0.0

# ============================================================================
# Core Engine Classes
# ============================================================================

class SustainabilityDataManager:
    """Manages all sustainability data for the engine."""
    
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.metrics: List[SustainabilityMetric] = []
        self.goals: List[SustainabilityGoal] = []
        self.actions: List[SustainabilityAction] = []
        self.carbon_history: List[CarbonFootprint] = []
        self.water_history: List[WaterFootprint] = []
        self.waste_history: List[WasteFootprint] = []
        self.cache = {}
        self._loaded = False
        self._load_data()
        
    @timer_decorator
    def _load_data(self):
        """Load data from persistent storage."""
        try:
            with safe_file_operation(self.data_file, 'r') as f:
                if f:
                    data = json.load(f)
                    self._deserialize_data(data)
                    self._loaded = True
                    logging.info(f"Loaded sustainability data from {self.data_file}")
        except Exception as e:
            logging.warning(f"Could not load data: {e}. Initializing fresh.")
            self._initialize_default_data()
            
    @timer_decorator
    def _save_data(self):
        """Save data to persistent storage."""
        try:
            data = self._serialize_data()
            with safe_file_operation(self.data_file, 'w') as f:
                if f:
                    json.dump(data, f, indent=2, default=str)
                    logging.info(f"Saved sustainability data to {self.data_file}")
        except Exception as e:
            logging.error(f"Could not save data: {e}")
            
    def _initialize_default_data(self):
        """Initialize with default sustainability data."""
        # Add default metrics
        now = datetime.datetime.now()
        default_metrics = [
            SustainabilityMetric(
                id=str(uuid.uuid4()),
                name="Monthly Electricity Usage",
                dimension=SustainabilityDimension.ENERGY,
                value=500.0,
                unit="kWh",
                timestamp=now,
                source=DataSource.ESTIMATE
            ),
            SustainabilityMetric(
                id=str(uuid.uuid4()),
                name="Monthly Water Usage",
                dimension=SustainabilityDimension.WATER,
                value=3000.0,
                unit="gallons",
                timestamp=now,
                source=DataSource.ESTIMATE
            ),
            SustainabilityMetric(
                id=str(uuid.uuid4()),
                name="Monthly Waste Generated",
                dimension=SustainabilityDimension.WASTE,
                value=100.0,
                unit="kg",
                timestamp=now,
                source=DataSource.ESTIMATE
            )
        ]
        self.metrics.extend(default_metrics)
        
        # Add default goals
        default_goals = [
            SustainabilityGoal(
                id=str(uuid.uuid4()),
                title="Reduce Electricity Usage",
                description="Reduce monthly electricity usage by 20%",
                dimension=SustainabilityDimension.ENERGY,
                target_value=400.0,
                current_value=500.0,
                unit="kWh",
                deadline=now + datetime.timedelta(days=180)
            ),
            SustainabilityGoal(
                id=str(uuid.uuid4()),
                title="Reduce Water Consumption",
                description="Reduce monthly water usage by 15%",
                dimension=SustainabilityDimension.WATER,
                target_value=2550.0,
                current_value=3000.0,
                unit="gallons",
                deadline=now + datetime.timedelta(days=120)
            ),
            SustainabilityGoal(
                id=str(uuid.uuid4()),
                title="Zero Waste Initiative",
                description="Achieve 80% waste diversion from landfill",
                dimension=SustainabilityDimension.WASTE,
                target_value=20.0,
                current_value=100.0,
                unit="kg",
                deadline=now + datetime.timedelta(days=365)
            )
        ]
        self.goals.extend(default_goals)
        
        # Add default actions
        default_actions = [
            SustainabilityAction(
                id=str(uuid.uuid4()),
                name="Turn off lights when leaving",
                description="Turn off lights in unused rooms",
                dimension=SustainabilityDimension.ENERGY,
                impact=ImpactLevel.POSITIVE_LOW,
                effort=ImpactLevel.NEGATIVE_LOW,
                co2_reduction=2.5,
                frequency="daily"
            ),
            SustainabilityAction(
                id=str(uuid.uuid4()),
                name="Use reusable water bottle",
                description="Avoid single-use plastic bottles",
                dimension=SustainabilityDimension.WASTE,
                impact=ImpactLevel.POSITIVE_MEDIUM,
                effort=ImpactLevel.NEGATIVE_LOW,
                waste_reduction=0.5,
                frequency="daily"
            ),
            SustainabilityAction(
                id=str(uuid.uuid4()),
                name="Take shorter showers",
                description="Reduce shower time to under 5 minutes",
                dimension=SustainabilityDimension.WATER,
                impact=ImpactLevel.POSITIVE_MEDIUM,
                effort=ImpactLevel.NEGATIVE_MEDIUM,
                water_savings=15.0,
                frequency="daily"
            )
        ]
        self.actions.extend(default_actions)
        
        self._save_data()
        
    def _serialize_data(self) -> Dict[str, Any]:
        """Serialize data to JSON-compatible dictionary."""
        return {
            "metrics": [self._serialize_metric(m) for m in self.metrics],
            "goals": [self._serialize_goal(g) for g in self.goals],
            "actions": [self._serialize_action(a) for a in self.actions],
            "carbon_history": [self._serialize_carbon(c) for c in self.carbon_history],
            "water_history": [self._serialize_water(w) for w in self.water_history],
            "waste_history": [self._serialize_waste(w) for w in self.waste_history],
            "version": VERSION,
            "last_updated": datetime.datetime.now().isoformat()
        }
        
    def _deserialize_data(self, data: Dict[str, Any]):
        """Deserialize data from dictionary."""
        self.metrics = [self._deserialize_metric(m) for m in data.get("metrics", [])]
        self.goals = [self._deserialize_goal(g) for g in data.get("goals", [])]
        self.actions = [self._deserialize_action(a) for a in data.get("actions", [])]
        self.carbon_history = [self._deserialize_carbon(c) for c in data.get("carbon_history", [])]
        self.water_history = [self._deserialize_water(w) for w in data.get("water_history", [])]
        self.waste_history = [self._deserialize_waste(w) for w in data.get("waste_history", [])]
        
    def _serialize_metric(self, metric: SustainabilityMetric) -> Dict:
        return {
            "id": metric.id,
            "name": metric.name,
            "dimension": metric.dimension.name,
            "value": metric.value,
            "unit": metric.unit,
            "timestamp": metric.timestamp.isoformat(),
            "source": metric.source.name,
            "confidence": metric.confidence,
            "metadata": metric.metadata
        }
        
    def _deserialize_metric(self, data: Dict) -> SustainabilityMetric:
        return SustainabilityMetric(
            id=data["id"],
            name=data["name"],
            dimension=SustainabilityDimension[data["dimension"]],
            value=data["value"],
            unit=data["unit"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            source=DataSource[data["source"]],
            confidence=data.get("confidence", 0.8),
            metadata=data.get("metadata", {})
        )
        
    def _serialize_goal(self, goal: SustainabilityGoal) -> Dict:
        return {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "dimension": goal.dimension.name,
            "target_value": goal.target_value,
            "current_value": goal.current_value,
            "unit": goal.unit,
            "deadline": goal.deadline.isoformat(),
            "status": goal.status.name,
            "created": goal.created.isoformat(),
            "updated": goal.updated.isoformat(),
            "progress_history": [(t.isoformat(), v) for t, v in goal.progress_history],
            "tags": goal.tags,
            "priority": goal.priority
        }
        
    def _deserialize_goal(self, data: Dict) -> SustainabilityGoal:
        return SustainabilityGoal(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            dimension=SustainabilityDimension[data["dimension"]],
            target_value=data["target_value"],
            current_value=data["current_value"],
            unit=data["unit"],
            deadline=datetime.datetime.fromisoformat(data["deadline"]),
            status=GoalStatus[data["status"]],
            created=datetime.datetime.fromisoformat(data["created"]),
            updated=datetime.datetime.fromisoformat(data["updated"]),
            progress_history=[(datetime.datetime.fromisoformat(t), v) for t, v in data.get("progress_history", [])],
            tags=data.get("tags", []),
            priority=data.get("priority", 5)
        )
        
    def _serialize_action(self, action: SustainabilityAction) -> Dict:
        return {
            "id": action.id,
            "name": action.name,
            "description": action.description,
            "dimension": action.dimension.name,
            "impact": action.impact.name,
            "effort": action.effort.name,
            "cost": action.cost,
            "co2_reduction": action.co2_reduction,
            "water_savings": action.water_savings,
            "waste_reduction": action.waste_reduction,
            "frequency": action.frequency,
            "completed": action.completed,
            "target": action.target,
            "tags": action.tags
        }
        
    def _deserialize_action(self, data: Dict) -> SustainabilityAction:
        return SustainabilityAction(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            dimension=SustainabilityDimension[data["dimension"]],
            impact=ImpactLevel[data["impact"]],
            effort=ImpactLevel[data["effort"]],
            cost=data.get("cost", 0.0),
            co2_reduction=data.get("co2_reduction", 0.0),
            water_savings=data.get("water_savings", 0.0),
            waste_reduction=data.get("waste_reduction", 0.0),
            frequency=data.get("frequency", "daily"),
            completed=data.get("completed", 0),
            target=data.get("target", 1),
            tags=data.get("tags", [])
        )
        
    def _serialize_carbon(self, carbon: CarbonFootprint) -> Dict:
        return {
            "total": carbon.total,
            "breakdown": carbon.breakdown,
            "offset": carbon.offset,
            "date": carbon.date.isoformat()
        }
        
    def _deserialize_carbon(self, data: Dict) -> CarbonFootprint:
        return CarbonFootprint(
            total=data["total"],
            breakdown=data["breakdown"],
            offset=data.get("offset", 0.0),
            date=datetime.datetime.fromisoformat(data["date"])
        )
        
    def _serialize_water(self, water: WaterFootprint) -> Dict:
        return {
            "total": water.total,
            "breakdown": water.breakdown,
            "date": water.date.isoformat()
        }
        
    def _deserialize_water(self, data: Dict) -> WaterFootprint:
        return WaterFootprint(
            total=data["total"],
            breakdown=data["breakdown"],
            date=datetime.datetime.fromisoformat(data["date"])
        )
        
    def _serialize_waste(self, waste: WasteFootprint) -> Dict:
        return {
            "total": waste.total,
            "recycled": waste.recycled,
            "composted": waste.composted,
            "landfill": waste.landfill,
            "breakdown": waste.breakdown,
            "date": waste.date.isoformat()
        }
        
    def _deserialize_waste(self, data: Dict) -> WasteFootprint:
        return WasteFootprint(
            total=data["total"],
            recycled=data.get("recycled", 0.0),
            composted=data.get("composted", 0.0),
            landfill=data.get("landfill", 0.0),
            breakdown=data.get("breakdown", {}),
            date=datetime.datetime.fromisoformat(data["date"])
        )
        
    def add_metric(self, metric: SustainabilityMetric) -> bool:
        """Add a new sustainability metric."""
        try:
            self.metrics.append(metric)
            self._save_data()
            return True
        except Exception as e:
            logging.error(f"Error adding metric: {e}")
            return False
            
    def add_goal(self, goal: SustainabilityGoal) -> bool:
        """Add a new sustainability goal."""
        try:
            self.goals.append(goal)
            self._save_data()
            return True
        except Exception as e:
            logging.error(f"Error adding goal: {e}")
            return False
            
    def add_action(self, action: SustainabilityAction) -> bool:
        """Add a new sustainability action."""
        try:
            self.actions.append(action)
            self._save_data()
            return True
        except Exception as e:
            logging.error(f"Error adding action: {e}")
            return False
            
    def update_goal_progress(self, goal_id: str, new_value: float) -> bool:
        """Update progress for a specific goal."""
        try:
            for goal in self.goals:
                if goal.id == goal_id:
                    goal.current_value = new_value
                    goal.updated = datetime.datetime.now()
                    goal.progress_history.append((goal.updated, new_value))
                    
                    # Update status based on progress
                    if new_value <= goal.target_value:
                        goal.status = GoalStatus.COMPLETED
                    elif new_value < goal.target_value * 1.2:
                        goal.status = GoalStatus.IN_PROGRESS
                    else:
                        goal.status = GoalStatus.NOT_STARTED
                        
                    self._save_data()
                    return True
            return False
        except Exception as e:
            logging.error(f"Error updating goal progress: {e}")
            return False
            
    def get_goals_by_dimension(self, dimension: SustainabilityDimension) -> List[SustainabilityGoal]:
        """Retrieve goals by dimension."""
        return [g for g in self.goals if g.dimension == dimension]
        
    def get_metrics_by_dimension(self, dimension: SustainabilityDimension) -> List[SustainabilityMetric]:
        """Retrieve metrics by dimension."""
        return [m for m in self.metrics if m.dimension == dimension]
        
    def get_actions_by_dimension(self, dimension: SustainabilityDimension) -> List[SustainabilityAction]:
        """Retrieve actions by dimension."""
        return [a for a in self.actions if a.dimension == dimension]
        
    def get_carbon_summary(self, period_days: int = 30) -> Dict[str, float]:
        """Get carbon summary for a period."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        recent = [c for c in self.carbon_history if c.date >= cutoff]
        
        if not recent:
            return {"total": 0.0, "average": 0.0, "count": 0}
            
        totals = [c.total for c in recent]
        return {
            "total": sum(totals),
            "average": statistics.mean(totals) if totals else 0.0,
            "count": len(totals),
            "max": max(totals) if totals else 0.0,
            "min": min(totals) if totals else 0.0
        }

# ============================================================================
# Analysis Engine
# ============================================================================

class SustainabilityAnalyzer:
    """Advanced sustainability analysis engine."""
    
    def __init__(self, data_manager: SustainabilityDataManager):
        self.data_manager = data_manager
        self.cache = {}
        
    @lru_cache(maxsize=128)
    def calculate_carbon_footprint(self, period_days: int = 30) -> CarbonFootprint:
        """Calculate carbon footprint for a period."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        # Collect relevant metrics
        energy_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.ENERGY
        )
        transport_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.TRANSPORTATION
        )
        
        # Calculate carbon from energy usage
        electricity_usage = 0.0
        natural_gas_usage = 0.0
        
        for metric in energy_metrics:
            if metric.timestamp >= cutoff:
                if metric.unit == "kWh":
                    electricity_usage += metric.value
                elif metric.unit == "therm":
                    natural_gas_usage += metric.value
                    
        # Calculate carbon from transportation
        car_miles = 0.0
        air_miles = 0.0
        bus_miles = 0.0
        train_miles = 0.0
        
        for metric in transport_metrics:
            if metric.timestamp >= cutoff:
                if "car" in metric.name.lower():
                    car_miles += metric.value
                elif "air" in metric.name.lower():
                    air_miles += metric.value
                elif "bus" in metric.name.lower():
                    bus_miles += metric.value
                elif "train" in metric.name.lower():
                    train_miles += metric.value
                    
        # Apply carbon factors
        total_carbon = (
            electricity_usage * CARBON_FACTORS["electricity"] +
            natural_gas_usage * CARBON_FACTORS["natural_gas"] +
            car_miles * CARBON_FACTORS["car_travel"] +
            air_miles * CARBON_FACTORS["air_travel"] +
            bus_miles * CARBON_FACTORS["bus_travel"] +
            train_miles * CARBON_FACTORS["train_travel"]
        )
        
        breakdown = {
            "electricity": electricity_usage * CARBON_FACTORS["electricity"],
            "natural_gas": natural_gas_usage * CARBON_FACTORS["natural_gas"],
            "car_travel": car_miles * CARBON_FACTORS["car_travel"],
            "air_travel": air_miles * CARBON_FACTORS["air_travel"],
            "bus_travel": bus_miles * CARBON_FACTORS["bus_travel"],
            "train_travel": train_miles * CARBON_FACTORS["train_travel"]
        }
        
        carbon = CarbonFootprint(
            total=total_carbon,
            breakdown=breakdown,
            date=datetime.datetime.now()
        )
        
        # Store in history
        self.data_manager.carbon_history.append(carbon)
        self.data_manager._save_data()
        
        return carbon
        
    @lru_cache(maxsize=128)
    def calculate_water_footprint(self, period_days: int = 30) -> WaterFootprint:
        """Calculate water footprint for a period."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        # Collect water metrics
        water_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.WATER
        )
        
        total_water = 0.0
        breakdown = defaultdict(float)
        
        for metric in water_metrics:
            if metric.timestamp >= cutoff:
                total_water += metric.value
                breakdown[metric.name] = breakdown.get(metric.name, 0) + metric.value
                
        water = WaterFootprint(
            total=total_water,
            breakdown=dict(breakdown),
            date=datetime.datetime.now()
        )
        
        self.data_manager.water_history.append(water)
        self.data_manager._save_data()
        
        return water
        
    @lru_cache(maxsize=128)
    def calculate_waste_footprint(self, period_days: int = 30) -> WasteFootprint:
        """Calculate waste footprint for a period."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        # Collect waste metrics
        waste_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.WASTE
        )
        
        total_waste = 0.0
        recycled = 0.0
        composted = 0.0
        landfill = 0.0
        breakdown = defaultdict(float)
        
        for metric in waste_metrics:
            if metric.timestamp >= cutoff:
                total_waste += metric.value
                if metric.unit == "recycled":
                    recycled += metric.value
                elif metric.unit == "composted":
                    composted += metric.value
                elif metric.unit == "landfill":
                    landfill += metric.value
                breakdown[metric.name] = breakdown.get(metric.name, 0) + metric.value
                
        # If no waste breakdown provided, estimate based on total
        if not recycled and not composted and not landfill and total_waste > 0:
            # Default assumption: 30% recycled, 20% composted, 50% landfill
            recycled = total_waste * 0.3
            composted = total_waste * 0.2
            landfill = total_waste * 0.5
            
        waste = WasteFootprint(
            total=total_waste,
            recycled=recycled,
            composted=composted,
            landfill=landfill,
            breakdown=dict(breakdown),
            date=datetime.datetime.now()
        )
        
        self.data_manager.waste_history.append(waste)
        self.data_manager._save_data()
        
        return waste
        
    def calculate_sustainability_score(self) -> float:
        """Calculate overall sustainability score (0-100)."""
        scores = []
        
        # Carbon score (lower is better)
        carbon = self.calculate_carbon_footprint()
        carbon_score = max(0, 100 - (carbon.total / 50))  # Assuming 50 kg CO2e is baseline
        scores.append(carbon_score)
        
        # Water score (lower is better)
        water = self.calculate_water_footprint()
        water_score = max(0, 100 - (water.total / 100))  # Assuming 100 gallons is baseline
        scores.append(water_score)
        
        # Waste score (lower is better)
        waste = self.calculate_waste_footprint()
        waste_score = max(0, 100 - (waste.total / 10))  # Assuming 10 kg waste is baseline
        scores.append(waste_score)
        
        # Goal progress score
        if self.data_manager.goals:
            goal_progress = []
            for goal in self.data_manager.goals:
                if goal.target_value > 0:
                    progress = min(100, (goal.current_value / goal.target_value) * 100)
                    if goal.status == GoalStatus.COMPLETED:
                        progress = 100
                    goal_progress.append(progress)
            if goal_progress:
                scores.append(statistics.mean(goal_progress))
                
        # Action completion score
        if self.data_manager.actions:
            action_completion = []
            for action in self.data_manager.actions:
                if action.target > 0:
                    completion = min(100, (action.completed / action.target) * 100)
                    action_completion.append(completion)
            if action_completion:
                scores.append(statistics.mean(action_completion))
                
        # Overall score
        if scores:
            overall_score = statistics.mean(scores)
            return round(min(100, overall_score), 2)
        return 0.0
        
    def generate_recommendations(self) -> List[str]:
        """Generate personalized sustainability recommendations."""
        recommendations = []
        
        # Carbon recommendations
        carbon = self.calculate_carbon_footprint()
        if carbon.total > 100:
            recommendations.append(
                "High carbon footprint detected. Consider reducing energy usage "
                "and using more sustainable transportation options."
            )
            
        # Water recommendations
        water = self.calculate_water_footprint()
        if water.total > 500:
            recommendations.append(
                "High water usage detected. Consider installing water-efficient "
                "fixtures and reducing shower time."
            )
            
        # Waste recommendations
        waste = self.calculate_waste_footprint()
        if waste.total > 20:
            recommendations.append(
                "High waste generation. Consider increasing recycling efforts "
                "and reducing single-use items."
            )
            
        # Goal-based recommendations
        for goal in self.data_manager.goals:
            if goal.status != GoalStatus.COMPLETED:
                if goal.dimension == SustainabilityDimension.ENERGY:
                    recommendations.append(
                        f"Work towards {goal.title}. Consider using energy-efficient "
                        f"appliances and LED lighting."
                    )
                elif goal.dimension == SustainabilityDimension.WATER:
                    recommendations.append(
                        f"Work towards {goal.title}. Consider fixing leaks and "
                        f"using water-efficient fixtures."
                    )
                elif goal.dimension == SustainabilityDimension.WASTE:
                    recommendations.append(
                        f"Work towards {goal.title}. Consider composting and "
                        f"buying products with minimal packaging."
                    )
                    
        # Action-based recommendations
        for action in self.data_manager.actions:
            if action.completed < action.target:
                recommendations.append(
                    f"Complete {action.name}. {action.description}"
                )
                
        # Return top 10 recommendations
        return recommendations[:10]
        
    def calculate_trends(self, dimension: SustainabilityDimension, period_days: int = 90) -> Dict[str, Any]:
        """Calculate trends for a specific dimension."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        metrics = self.data_manager.get_metrics_by_dimension(dimension)
        recent_metrics = [m for m in metrics if m.timestamp >= cutoff]
        
        if not recent_metrics:
            return {"trend": "insufficient_data", "change": 0.0}
            
        # Group by month
        monthly_data = defaultdict(list)
        for metric in recent_metrics:
            month_key = metric.timestamp.strftime("%Y-%m")
            monthly_data[month_key].append(metric.value)
            
        monthly_averages = {
            month: statistics.mean(values) for month, values in monthly_data.items()
        }
        
        sorted_months = sorted(monthly_averages.items())
        if len(sorted_months) < 2:
            return {"trend": "insufficient_data", "change": 0.0}
            
        # Calculate trend
        first_value = sorted_months[0][1]
        last_value = sorted_months[-1][1]
        
        if first_value == 0:
            change_percent = 0.0
        else:
            change_percent = ((last_value - first_value) / first_value) * 100
            
        # Determine trend direction
        if change_percent > 10:
            trend = "increasing"
        elif change_percent < -10:
            trend = "decreasing"
        else:
            trend = "stable"
            
        return {
            "trend": trend,
            "change": round(change_percent, 2),
            "current": last_value,
            "historical": monthly_averages
        }

# ============================================================================
# Optimization Engine
# ============================================================================

class SustainabilityOptimizer:
    """Optimizes sustainability strategies and actions."""
    
    def __init__(self, data_manager: SustainabilityDataManager):
        self.data_manager = data_manager
        self.analyzer = SustainabilityAnalyzer(data_manager)
        
    def optimize_energy_usage(self) -> Dict[str, Any]:
        """Optimize energy usage patterns."""
        recommendations = []
        potential_savings = 0.0
        
        energy_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.ENERGY
        )
        
        if not energy_metrics:
            return {
                "recommendations": ["No energy data available for optimization"],
                "potential_savings": 0.0
            }
            
        # Analyze energy usage patterns
        total_energy = sum(m.value for m in energy_metrics)
        average_usage = total_energy / len(energy_metrics) if energy_metrics else 0
        
        if average_usage > 400:
            recommendations.append(
                f"Reduce electricity usage from {average_usage:.1f} to under 400 kWh/month. "
                f"Potential savings: 20%"
            )
            potential_savings += average_usage * 0.2 * CARBON_FACTORS["electricity"]
            
        if average_usage > 100:
            recommendations.append(
                f"Reduce natural gas usage from {average_usage:.1f} to under 100 therms/month."
            )
            
        # Suggest specific actions
        for action in self.data_manager.actions:
            if action.dimension == SustainabilityDimension.ENERGY:
                if action.completed < action.target:
                    recommendations.append(
                        f"Implement {action.name}. CO2 reduction: {action.co2_reduction:.1f} kg/year"
                    )
                    
        return {
            "recommendations": recommendations[:5],
            "potential_savings": round(potential_savings, 2)
        }
        
    def optimize_water_usage(self) -> Dict[str, Any]:
        """Optimize water usage patterns."""
        recommendations = []
        potential_savings = 0.0
        
        water_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.WATER
        )
        
        if not water_metrics:
            return {
                "recommendations": ["No water data available for optimization"],
                "potential_savings": 0.0
            }
            
        total_water = sum(m.value for m in water_metrics)
        average_usage = total_water / len(water_metrics) if water_metrics else 0
        
        if average_usage > 200:
            recommendations.append(
                f"Reduce water usage from {average_usage:.1f} to under 200 gallons/month. "
                f"Potential savings: 15%"
            )
            potential_savings += average_usage * 0.15
            
        # Suggest specific actions
        for action in self.data_manager.actions:
            if action.dimension == SustainabilityDimension.WATER:
                if action.completed < action.target:
                    recommendations.append(
                        f"Implement {action.name}. Water savings: {action.water_savings:.1f} gallons/use"
                    )
                    
        return {
            "recommendations": recommendations[:5],
            "potential_savings": round(potential_savings, 2)
        }
        
    def optimize_waste_management(self) -> Dict[str, Any]:
        """Optimize waste management practices."""
        recommendations = []
        potential_savings = 0.0
        
        waste_metrics = self.data_manager.get_metrics_by_dimension(
            SustainabilityDimension.WASTE
        )
        
        if not waste_metrics:
            return {
                "recommendations": ["No waste data available for optimization"],
                "potential_savings": 0.0
            }
            
        total_waste = sum(m.value for m in waste_metrics)
        average_usage = total_waste / len(waste_metrics) if waste_metrics else 0
        
        if average_usage > 50:
            recommendations.append(
                f"Reduce waste generation from {average_usage:.1f} to under 50 kg/month. "
                f"Potential savings: 30% reduction in landfill waste"
            )
            potential_savings += average_usage * 0.3
            
        # Suggest specific actions
        for action in self.data_manager.actions:
            if action.dimension == SustainabilityDimension.WASTE:
                if action.completed < action.target:
                    recommendations.append(
                        f"Implement {action.name}. Waste reduction: {action.waste_reduction:.1f} kg/use"
                    )
                    
        return {
            "recommendations": recommendations[:5],
            "potential_savings": round(potential_savings, 2)
        }
        
    def optimize_goal_priority(self) -> List[Tuple[str, float]]:
        """Optimize goal priority based on impact and effort."""
        goals_with_score = []
        
        for goal in self.data_manager.goals:
            if goal.status == GoalStatus.COMPLETED:
                continue
                
            # Calculate priority score
            impact_score = 0.0
            if goal.dimension == SustainabilityDimension.ENERGY:
                impact_score = (goal.current_value - goal.target_value) / goal.current_value * 10
            elif goal.dimension == SustainabilityDimension.WATER:
                impact_score = (goal.current_value - goal.target_value) / goal.current_value * 8
            elif goal.dimension == SustainabilityDimension.WASTE:
                impact_score = (goal.current_value - goal.target_value) / goal.current_value * 9
            else:
                impact_score = 5.0
                
            # Time urgency (closer deadline = higher priority)
            days_remaining = (goal.deadline - datetime.datetime.now()).days
            urgency_score = max(0, 10 - max(0, days_remaining) / 30)
            
            # Overall priority
            overall_score = (impact_score * 0.6 + urgency_score * 0.4) * (goal.priority / 10)
            
            goals_with_score.append((goal.title, overall_score))
            
        return sorted(goals_with_score, key=lambda x: x[1], reverse=True)

# ============================================================================
# Reporting Engine
# ============================================================================

class SustainabilityReporter:
    """Generates sustainability reports and visualizations."""
    
    def __init__(self, data_manager: SustainabilityDataManager):
        self.data_manager = data_manager
        self.analyzer = SustainabilityAnalyzer(data_manager)
        
    def generate_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive sustainability report."""
        start_date = datetime.datetime.now() - datetime.timedelta(days=period_days)
        end_date = datetime.datetime.now()
        
        # Calculate key metrics
        carbon = self.analyzer.calculate_carbon_footprint(period_days)
        water = self.analyzer.calculate_water_footprint(period_days)
        waste = self.analyzer.calculate_waste_footprint(period_days)
        score = self.analyzer.calculate_sustainability_score()
        recommendations = self.analyzer.generate_recommendations()
        
        # Goal progress
        goal_progress = []
        for goal in self.data_manager.goals:
            progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0
            goal_progress.append({
                "title": goal.title,
                "progress": min(100, progress),
                "status": goal.status.name,
                "deadline": goal.deadline.isoformat()
            })
            
        # Action completion
        action_status = []
        for action in self.data_manager.actions:
            completion = (action.completed / action.target * 100) if action.target > 0 else 0
            action_status.append({
                "name": action.name,
                "completion": min(100, completion),
                "impact": action.impact.name,
                "frequency": action.frequency
            })
            
        # Generate report
        report = {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "sustainability_score": score,
            "carbon_footprint": carbon.total,
            "carbon_breakdown": carbon.breakdown,
            "water_footprint": water.total,
            "water_breakdown": water.breakdown,
            "waste_footprint": waste.total,
            "waste_breakdown": waste.breakdown,
            "waste_recycled": waste.recycled,
            "waste_composted": waste.composted,
            "waste_landfill": waste.landfill,
            "goal_progress": goal_progress,
            "action_status": action_status,
            "recommendations": recommendations,
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        return report
        
    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of sustainability status."""
        return {
            "overall_score": self.analyzer.calculate_sustainability_score(),
            "goal_count": len(self.data_manager.goals),
            "completed_goals": sum(1 for g in self.data_manager.goals if g.status == GoalStatus.COMPLETED),
            "action_count": len(self.data_manager.actions),
            "completed_actions": sum(1 for a in self.data_manager.actions if a.completed >= a.target),
            "total_carbon_saved": sum(a.co2_reduction for a in self.data_manager.actions if a.completed >= a.target),
            "total_water_saved": sum(a.water_savings for a in self.data_manager.actions if a.completed >= a.target),
            "total_waste_reduced": sum(a.waste_reduction for a in self.data_manager.actions if a.completed >= a.target)
        }
        
    def generate_progress_report(self, period_days: int = 30) -> ProgressReport:
        """Generate a detailed progress report."""
        start_date = datetime.datetime.now() - datetime.timedelta(days=period_days)
        end_date = datetime.datetime.now()
        
        # Calculate metrics changes
        carbon_start = self.analyzer.calculate_carbon_footprint(period_days * 2)
        carbon_end = self.analyzer.calculate_carbon_footprint(period_days)
        
        metrics = {
            "carbon_footprint": carbon_end.total,
            "water_footprint": self.analyzer.calculate_water_footprint(period_days).total,
            "waste_footprint": self.analyzer.calculate_waste_footprint(period_days).total,
            "sustainability_score": self.analyzer.calculate_sustainability_score()
        }
        
        changes = {
            "carbon_change": carbon_end.total - carbon_start.total,
            "carbon_change_percent": ((carbon_end.total - carbon_start.total) / carbon_start.total * 100) if carbon_start.total > 0 else 0
        }
        
        return ProgressReport(
            period_start=start_date,
            period_end=end_date,
            metrics=metrics,
            changes=changes,
            goals=self.data_manager.goals[:10],
            actions=self.data_manager.actions[:10],
            recommendations=self.analyzer.generate_recommendations(),
            score=metrics["sustainability_score"]
        )
        
    def export_report_csv(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Export report data to CSV format."""
        if not filename:
            filename = f"sustainability_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Metric', 'Value', 'Unit'])
            
            # Write key metrics
            writer.writerow(['Sustainability Score', report.get('sustainability_score', 0), 'score'])
            writer.writerow(['Carbon Footprint', report.get('carbon_footprint', 0), 'kg CO2e'])
            writer.writerow(['Water Footprint', report.get('water_footprint', 0), 'gallons'])
            writer.writerow(['Waste Footprint', report.get('waste_footprint', 0), 'kg'])
            
            # Write carbon breakdown
            writer.writerow(['Carbon Breakdown - Electricity', report.get('carbon_breakdown', {}).get('electricity', 0), 'kg CO2e'])
            writer.writerow(['Carbon Breakdown - Natural Gas', report.get('carbon_breakdown', {}).get('natural_gas', 0), 'kg CO2e'])
            writer.writerow(['Carbon Breakdown - Car Travel', report.get('carbon_breakdown', {}).get('car_travel', 0), 'kg CO2e'])
            writer.writerow(['Carbon Breakdown - Air Travel', report.get('carbon_breakdown', {}).get('air_travel', 0), 'kg CO2e'])
            
            # Write goals
            for goal in report.get('goal_progress', []):
                writer.writerow(['Goal', goal.get('title', ''), goal.get('progress', 0), '%'])
                
            # Write actions
            for action in report.get('action_status', []):
                writer.writerow(['Action', action.get('name', ''), action.get('completion', 0), '%'])
                
        return filename

# ============================================================================
# Visualization Engine
# ============================================================================

class SustainabilityVisualizer:
    """Visualization and chart generation engine."""
    
    def __init__(self, data_manager: SustainabilityDataManager):
        self.data_manager = data_manager
        self.analyzer = SustainabilityAnalyzer(data_manager)
        
    def generate_carbon_chart_data(self, period_days: int = 90) -> Dict[str, List]:
        """Generate data for carbon footprint chart."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        # Get carbon history
        carbon_history = [c for c in self.data_manager.carbon_history if c.date >= cutoff]
        
        if not carbon_history:
            return {"dates": [], "values": []}
            
        dates = [c.date.strftime("%Y-%m-%d") for c in carbon_history]
        values = [c.total for c in carbon_history]
        
        return {"dates": dates, "values": values}
        
    def generate_water_chart_data(self, period_days: int = 90) -> Dict[str, List]:
        """Generate data for water footprint chart."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        water_history = [w for w in self.data_manager.water_history if w.date >= cutoff]
        
        if not water_history:
            return {"dates": [], "values": []}
            
        dates = [w.date.strftime("%Y-%m-%d") for w in water_history]
        values = [w.total for w in water_history]
        
        return {"dates": dates, "values": values}
        
    def generate_waste_chart_data(self, period_days: int = 90) -> Dict[str, List]:
        """Generate data for waste footprint chart."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=period_days)
        
        waste_history = [w for w in self.data_manager.waste_history if w.date >= cutoff]
        
        if not waste_history:
            return {"dates": [], "values": []}
            
        dates = [w.date.strftime("%Y-%m-%d") for w in waste_history]
        values = [w.total for w in waste_history]
        
        return {"dates": dates, "values": values}
        
    def generate_goal_progress_chart(self) -> Dict[str, List]:
        """Generate data for goal progress chart."""
        goals = self.data_manager.goals[:10]  # Top 10 goals
        
        if not goals:
            return {"labels": [], "values": []}
            
        labels = [g.title[:20] + "..." if len(g.title) > 20 else g.title for g in goals]
        values = []
        
        for goal in goals:
            if goal.target_value > 0:
                progress = (goal.current_value / goal.target_value) * 100
                values.append(min(100, progress))
            else:
                values.append(0)
                
        return {"labels": labels, "values": values}
        
    def generate_action_completion_chart(self) -> Dict[str, List]:
        """Generate data for action completion chart."""
        actions = self.data_manager.actions[:10]  # Top 10 actions
        
        if not actions:
            return {"labels": [], "values": []}
            
        labels = [a.name[:20] + "..." if len(a.name) > 20 else a.name for a in actions]
        values = []
        
        for action in actions:
            if action.target > 0:
                completion = (action.completed / action.target) * 100
                values.append(min(100, completion))
            else:
                values.append(0)
                
        return {"labels": labels, "values": values}
        
    def generate_dimension_breakdown_chart(self) -> Dict[str, float]:
        """Generate dimension breakdown for sustainability score."""
        breakdown = {}
        
        for dimension in SustainabilityDimension:
            metrics = self.data_manager.get_metrics_by_dimension(dimension)
            if metrics:
                breakdown[dimension.name] = statistics.mean([m.value for m in metrics])
            else:
                breakdown[dimension.name] = 0.0
                
        return breakdown

# ============================================================================
# API and Interface Layer
# ============================================================================

class SustainabilityAPI:
    """API interface for the sustainability engine."""
    
    def __init__(self):
        self.data_manager = SustainabilityDataManager()
        self.analyzer = SustainabilityAnalyzer(self.data_manager)
        self.optimizer = SustainabilityOptimizer(self.data_manager)
        self.reporter = SustainabilityReporter(self.data_manager)
        self.visualizer = SustainabilityVisualizer(self.data_manager)
        
    def get_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "version": VERSION,
            "data_file": DATA_FILE,
            "metrics_count": len(self.data_manager.metrics),
            "goals_count": len(self.data_manager.goals),
            "actions_count": len(self.data_manager.actions),
            "carbon_history_count": len(self.data_manager.carbon_history),
            "water_history_count": len(self.data_manager.water_history),
            "waste_history_count": len(self.data_manager.waste_history)
        }
        
    def add_metric(self, metric: SustainabilityMetric) -> bool:
        """Add a new sustainability metric."""
        return self.data_manager.add_metric(metric)
        
    def add_goal(self, goal: SustainabilityGoal) -> bool:
        """Add a new sustainability goal."""
        return self.data_manager.add_goal(goal)
        
    def add_action(self, action: SustainabilityAction) -> bool:
        """Add a new sustainability action."""
        return self.data_manager.add_action(action)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get sustainability summary."""
        return self.reporter.generate_summary()
        
    def get_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive sustainability report."""
        return self.reporter.generate_report(period_days)
        
    def get_progress_report(self, period_days: int = 30) -> ProgressReport:
        """Get detailed progress report."""
        return self.reporter.generate_progress_report(period_days)
        
    def get_recommendations(self) -> List[str]:
        """Get sustainability recommendations."""
        return self.analyzer.generate_recommendations()
        
    def get_carbon_footprint(self, period_days: int = 30) -> CarbonFootprint:
        """Calculate carbon footprint."""
        return self.analyzer.calculate_carbon_footprint(period_days)
        
    def get_water_footprint(self, period_days: int = 30) -> WaterFootprint:
        """Calculate water footprint."""
        return self.analyzer.calculate_water_footprint(period_days)
        
    def get_waste_footprint(self, period_days: int = 30) -> WasteFootprint:
        """Calculate waste footprint."""
        return self.analyzer.calculate_waste_footprint(period_days)
        
    def get_sustainability_score(self) -> float:
        """Get overall sustainability score."""
        return self.analyzer.calculate_sustainability_score()
        
    def get_trends(self, dimension: SustainabilityDimension, period_days: int = 90) -> Dict[str, Any]:
        """Get trend analysis for a dimension."""
        return self.analyzer.calculate_trends(dimension, period_days)
        
    def optimize_energy(self) -> Dict[str, Any]:
        """Get energy optimization recommendations."""
        return self.optimizer.optimize_energy_usage()
        
    def optimize_water(self) -> Dict[str, Any]:
        """Get water optimization recommendations."""
        return self.optimizer.optimize_water_usage()
        
    def optimize_waste(self) -> Dict[str, Any]:
        """Get waste optimization recommendations."""
        return self.optimizer.optimize_waste_management()
        
    def prioritize_goals(self) -> List[Tuple[str, float]]:
        """Get prioritized goals."""
        return self.optimizer.optimize_goal_priority()
        
    def get_chart_data(self, chart_type: str, period_days: int = 90) -> Dict[str, Any]:
        """Get chart data for visualization."""
        if chart_type == "carbon":
            return self.visualizer.generate_carbon_chart_data(period_days)
        elif chart_type == "water":
            return self.visualizer.generate_water_chart_data(period_days)
        elif chart_type == "waste":
            return self.visualizer.generate_waste_chart_data(period_days)
        elif chart_type == "goals":
            return self.visualizer.generate_goal_progress_chart()
        elif chart_type == "actions":
            return self.visualizer.generate_action_completion_chart()
        elif chart_type == "dimensions":
            return self.visualizer.generate_dimension_breakdown_chart()
        else:
            return {}
            
    def export_report_csv(self, period_days: int = 30, filename: Optional[str] = None) -> str:
        """Export report to CSV."""
        report = self.get_report(period_days)
        return self.reporter.export_report_csv(report, filename)
        
    def reset_data(self) -> bool:
        """Reset all data (use with caution)."""
        try:
            self.data_manager = SustainabilityDataManager()
            self.analyzer = SustainabilityAnalyzer(self.data_manager)
            self.optimizer = SustainabilityOptimizer(self.data_manager)
            self.reporter = SustainabilityReporter(self.data_manager)
            self.visualizer = SustainabilityVisualizer(self.data_manager)
            return True
        except Exception as e:
            logging.error(f"Error resetting data: {e}")
            return False

# ============================================================================
# Command Line Interface
# ============================================================================

class SustainabilityCLI:
    """Command Line Interface for the sustainability engine."""
    
    def __init__(self):
        self.api = SustainabilityAPI()
        self._setup_logging()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        
    def run(self, args: Optional[List[str]] = None):
        """Run the CLI interface."""
        if args is None:
            args = sys.argv[1:]
            
        if not args:
            self._print_help()
            return
            
        command = args[0].lower()
        command_args = args[1:]
        
        command_map = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "summary": self._cmd_summary,
            "report": self._cmd_report,
            "progress": self._cmd_progress,
            "recommendations": self._cmd_recommendations,
            "score": self._cmd_score,
            "carbon": self._cmd_carbon,
            "water": self._cmd_water,
            "waste": self._cmd_waste,
            "trends": self._cmd_trends,
            "optimize": self._cmd_optimize,
            "prioritize": self._cmd_prioritize,
            "export": self._cmd_export,
            "add": self._cmd_add,
            "list": self._cmd_list,
            "reset": self._cmd_reset,
            "version": self._cmd_version
        }
        
        if command in command_map:
            try:
                command_map[command](command_args)
            except Exception as e:
                logging.error(f"Error executing command '{command}': {e}")
                print(f"Error: {e}")
        else:
            print(f"Unknown command: {command}")
            self._print_help()
            
    def _print_help(self):
        """Print help information."""
        help_text = """
        Personal Sustainability Roadmap Engine (PSRE)
        
        Usage: psre <command> [options]
        
        Commands:
        help                  Show this help message
        status                Show system status
        summary               Show sustainability summary
        report [days]         Generate sustainability report
        progress [days]       Show progress report
        recommendations       Get sustainability recommendations
        score                 Show sustainability score
        carbon [days]         Show carbon footprint
        water [days]          Show water footprint
        waste [days]          Show waste footprint
        trends <dimension>    Show trends for a dimension
        optimize <type>       Optimize energy/water/waste
        prioritize           Show prioritized goals
        export [filename]    Export report to CSV
        add <metric|goal|action> Add new item
        list <metrics|goals|actions> List items
        reset                 Reset all data (caution)
        version              Show version
        
        Examples:
        psre report 30
        psre optimize energy
        psre add metric
        """
        print(help_text)
        
    def _cmd_help(self, args: List[str]):
        self._print_help()
        
    def _cmd_status(self, args: List[str]):
        status = self.api.get_status()
        print("=== System Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
            
    def _cmd_summary(self, args: List[str]):
        summary = self.api.get_summary()
        print("=== Sustainability Summary ===")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
                
    def _cmd_report(self, args: List[str]):
        days = int(args[0]) if args else 30
        report = self.api.get_report(days)
        print(f"=== Sustainability Report (Last {days} days) ===")
        print(f"Score: {report.get('sustainability_score', 0):.2f}")
        print(f"Carbon Footprint: {report.get('carbon_footprint', 0):.2f} kg CO2e")
        print(f"Water Footprint: {report.get('water_footprint', 0):.2f} gallons")
        print(f"Waste Footprint: {report.get('waste_footprint', 0):.2f} kg")
        print("\nGoals:")
        for goal in report.get('goal_progress', []):
            print(f"  - {goal['title']}: {goal['progress']:.1f}% ({goal['status']})")
        print("\nRecommendations:")
        for rec in report.get('recommendations', [])[:5]:
            print(f"  - {rec}")
            
    def _cmd_progress(self, args: List[str]):
        days = int(args[0]) if args else 30
        progress = self.api.get_progress_report(days)
        print(f"=== Progress Report ({days} days) ===")
        print(f"Score: {progress.score:.2f}")
        print(f"Period: {progress.period_start.strftime('%Y-%m-%d')} to {progress.period_end.strftime('%Y-%m-%d')}")
        print("\nMetrics:")
        for key, value in progress.metrics.items():
            print(f"  {key}: {value:.2f}")
        print("\nChanges:")
        for key, value in progress.changes.items():
            print(f"  {key}: {value:.2f}")
            
    def _cmd_recommendations(self, args: List[str]):
        recs = self.api.get_recommendations()
        print("=== Sustainability Recommendations ===")
        for i, rec in enumerate(recs, 1):
            print(f"{i}. {rec}")
            
    def _cmd_score(self, args: List[str]):
        score = self.api.get_sustainability_score()
        print(f"Sustainability Score: {score:.2f}/100")
        
    def _cmd_carbon(self, args: List[str]):
        days = int(args[0]) if args else 30
        carbon = self.api.get_carbon_footprint(days)
        print(f"=== Carbon Footprint (Last {days} days) ===")
        print(f"Total: {carbon.total:.2f} kg CO2e")
        print("\nBreakdown:")
        for category, value in carbon.breakdown.items():
            if value > 0:
                print(f"  {category}: {value:.2f} kg CO2e")
                
    def _cmd_water(self, args: List[str]):
        days = int(args[0]) if args else 30
        water = self.api.get_water_footprint(days)
        print(f"=== Water Footprint (Last {days} days) ===")
        print(f"Total: {water.total:.2f} gallons")
        print("\nBreakdown:")
        for category, value in water.breakdown.items():
            if value > 0:
                print(f"  {category}: {value:.2f} gallons")
                
    def _cmd_waste(self, args: List[str]):
        days = int(args[0]) if args else 30
        waste = self.api.get_waste_footprint(days)
        print(f"=== Waste Footprint (Last {days} days) ===")
        print(f"Total: {waste.total:.2f} kg")
        print(f"Recycled: {waste.recycled:.2f} kg")
        print(f"Composted: {waste.composted:.2f} kg")
        print(f"Landfill: {waste.landfill:.2f} kg")
        
    def _cmd_trends(self, args: List[str]):
        if not args:
            print("Please specify a dimension: ENERGY, WATER, WASTE, etc.")
            return
        dimension_name = args[0].upper()
        try:
            dimension = SustainabilityDimension[dimension_name]
            days = int(args[1]) if len(args) > 1 else 90
            trends = self.api.get_trends(dimension, days)
            print(f"=== Trends for {dimension_name} (Last {days} days) ===")
            print(f"Trend: {trends.get('trend', 'unknown')}")
            print(f"Change: {trends.get('change', 0):.2f}%")
            print(f"Current: {trends.get('current', 0):.2f}")
            print("\nHistorical Monthly Averages:")
            for month, value in trends.get('historical', {}).items():
                print(f"  {month}: {value:.2f}")
        except KeyError:
            print(f"Unknown dimension: {dimension_name}")
            print("Available dimensions: ENERGY, WATER, WASTE, TRANSPORTATION, etc.")
            
    def _cmd_optimize(self, args: List[str]):
        if not args:
            print("Please specify optimization type: energy, water, or waste")
            return
        opt_type = args[0].lower()
        
        if opt_type == "energy":
            result = self.api.optimize_energy()
            print("=== Energy Optimization ===")
            print(f"Potential Savings: {result.get('potential_savings', 0):.2f} kg CO2e")
            print("\nRecommendations:")
            for rec in result.get('recommendations', []):
                print(f"  - {rec}")
        elif opt_type == "water":
            result = self.api.optimize_water()
            print("=== Water Optimization ===")
            print(f"Potential Savings: {result.get('potential_savings', 0):.2f} gallons")
            print("\nRecommendations:")
            for rec in result.get('recommendations', []):
                print(f"  - {rec}")
        elif opt_type == "waste":
            result = self.api.optimize_waste()
            print("=== Waste Optimization ===")
            print(f"Potential Savings: {result.get('potential_savings', 0):.2f} kg")
            print("\nRecommendations:")
            for rec in result.get('recommendations', []):
                print(f"  - {rec}")
        else:
            print(f"Unknown optimization type: {opt_type}")
            
    def _cmd_prioritize(self, args: List[str]):
        priorities = self.api.prioritize_goals()
        print("=== Prioritized Goals ===")
        for title, score in priorities[:10]:
            print(f"{score:.2f}: {title}")
            
    def _cmd_export(self, args: List[str]):
        filename = args[0] if args else None
        days = int(args[1]) if len(args) > 1 else 30
        output = self.api.export_report_csv(days, filename)
        print(f"Report exported to: {output}")
        
    def _cmd_add(self, args: List[str]):
        if not args:
            print("Please specify what to add: metric, goal, or action")
            return
        item_type = args[0].lower()
        
        if item_type == "metric":
            self._add_metric_interactive()
        elif item_type == "goal":
            self._add_goal_interactive()
        elif item_type == "action":
            self._add_action_interactive()
        else:
            print(f"Unknown item type: {item_type}")
            
    def _add_metric_interactive(self):
        print("=== Add New Sustainability Metric ===")
        name = input("Metric name: ")
        dimension = input("Dimension (ENERGY, WATER, WASTE, etc.): ").upper()
        value = float(input("Value: "))
        unit = input("Unit: ")
        
        try:
            metric = SustainabilityMetric(
                id=str(uuid.uuid4()),
                name=name,
                dimension=SustainabilityDimension[dimension],
                value=value,
                unit=unit,
                timestamp=datetime.datetime.now()
            )
            if self.api.add_metric(metric):
                print("Metric added successfully!")
            else:
                print("Failed to add metric.")
        except KeyError:
            print(f"Invalid dimension: {dimension}")
        except ValueError:
            print("Invalid value.")
            
    def _add_goal_interactive(self):
        print("=== Add New Sustainability Goal ===")
        title = input("Goal title: ")
        description = input("Description: ")
        dimension = input("Dimension (ENERGY, WATER, WASTE, etc.): ").upper()
        target = float(input("Target value: "))
        current = float(input("Current value: "))
        unit = input("Unit: ")
        deadline_str = input("Deadline (YYYY-MM-DD): ")
        
        try:
            deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d")
            goal = SustainabilityGoal(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                dimension=SustainabilityDimension[dimension],
                target_value=target,
                current_value=current,
                unit=unit,
                deadline=deadline
            )
            if self.api.add_goal(goal):
                print("Goal added successfully!")
            else:
                print("Failed to add goal.")
        except ValueError as e:
            print(f"Invalid input: {e}")
            
    def _add_action_interactive(self):
        print("=== Add New Sustainability Action ===")
        name = input("Action name: ")
        description = input("Description: ")
        dimension = input("Dimension (ENERGY, WATER, WASTE, etc.): ").upper()
        
        try:
            action = SustainabilityAction(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                dimension=SustainabilityDimension[dimension],
                impact=ImpactLevel.POSITIVE_MEDIUM,
                effort=ImpactLevel.NEGATIVE_LOW
            )
            if self.api.add_action(action):
                print("Action added successfully!")
            else:
                print("Failed to add action.")
        except KeyError:
            print(f"Invalid dimension: {dimension}")
            
    def _cmd_list(self, args: List[str]):
        if not args:
            print("Please specify what to list: metrics, goals, or actions")
            return
        list_type = args[0].lower()
        
        if list_type == "metrics":
            print("=== Sustainability Metrics ===")
            for metric in self.api.data_manager.metrics:
                print(f"  - {metric.name}: {metric.value} {metric.unit} ({metric.dimension.name})")
        elif list_type == "goals":
            print("=== Sustainability Goals ===")
            for goal in self.api.data_manager.goals:
                progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0
                print(f"  - {goal.title}: {progress:.1f}% ({goal.status.name})")
        elif list_type == "actions":
            print("=== Sustainability Actions ===")
            for action in self.api.data_manager.actions:
                completion = (action.completed / action.target * 100) if action.target > 0 else 0
                print(f"  - {action.name}: {completion:.1f}% ({action.frequency})")
        else:
            print(f"Unknown list type: {list_type}")
            
    def _cmd_reset(self, args: List[str]):
        confirm = input("This will reset ALL data. Are you sure? (yes/no): ")
        if confirm.lower() == "yes":
            if self.api.reset_data():
                print("Data reset successfully.")
            else:
                print("Failed to reset data.")
        else:
            print("Reset cancelled.")
            
    def _cmd_version(self, args: List[str]):
        print(f"Personal Sustainability Roadmap Engine v{VERSION}")

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the application."""
    cli = SustainabilityCLI()
    cli.run()
    
if __name__ == "__main__":
    main()

# ============================================================================
# End of File
# ============================================================================
