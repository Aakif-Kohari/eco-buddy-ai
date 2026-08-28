"""
Data models for the Environmental Benchmarking feature.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import math

@dataclass
class CategoryStat:
    """Statistical distribution details for a specific category."""
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    p10: float
    p25: float
    p75: float
    p90: float
    weight: float = 1.0

    def validate(self):
        """Ensure statistical validity of the defined distribution."""
        if self.min_val > self.max_val:
            raise ValueError(f"min_val ({self.min_val}) cannot be greater than max_val ({self.max_val})")
        
        percentiles = [self.min_val, self.p10, self.p25, self.median, self.p75, self.p90, self.max_val]
        if not all(percentiles[i] <= percentiles[i+1] for i in range(len(percentiles)-1)):
            raise ValueError(f"Percentiles must be monotonically increasing: {percentiles}")

        if self.mean < self.min_val or self.mean > self.max_val:
            raise ValueError("Mean must be between min and max")

@dataclass
class ReferenceProfile:
    """A reference profile for comparison (e.g., US Average, Global)."""
    id: str
    name: str
    description: str
    region_code: str
    transport_stat: CategoryStat
    electricity_stat: CategoryStat
    diet_stat: CategoryStat
    flights_stat: CategoryStat
    footprint_stat: CategoryStat
    eco_score_stat: CategoryStat

    def get_stat(self, category: str) -> Optional[CategoryStat]:
        """Fetch the statistic for a specific category."""
        mapping = {
            "transport": self.transport_stat,
            "electricity": self.electricity_stat,
            "diet": self.diet_stat,
            "flights": self.flights_stat,
            "footprint": self.footprint_stat,
            "eco_score": self.eco_score_stat,
        }
        return mapping.get(category)
        
    def validate_all(self):
        """Validate all internal category statistics."""
        for cat in ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]:
            stat = self.get_stat(cat)
            if stat:
                try:
                    stat.validate()
                except ValueError as e:
                    raise ValueError(f"Validation failed for {self.id} category {cat}: {e}")

@dataclass
class UserAssessment:
    """Represents a user's single environmental assessment."""
    assessment_id: int
    user_id: int
    date: datetime
    transport: str
    distance: float
    electricity: float
    diet: str
    flights: int
    footprint: float
    eco_score: int
    
    @classmethod
    def from_db_row(cls, row: dict) -> 'UserAssessment':
        """Parse a row from the assessments table into a UserAssessment object."""
        date_val = row.get('date', datetime.now())
        if isinstance(date_val, str):
            try:
                date_val = datetime.fromisoformat(date_val)
            except ValueError:
                date_val = datetime.now()
                
        return cls(
            assessment_id=row.get('id', 0) or 0,
            user_id=row.get('user_id', 1) or 1,
            date=date_val,
            transport=row.get('transport', 'car') or 'car',
            distance=float(row.get('distance', 0.0) or 0.0),
            electricity=float(row.get('electricity', 0.0) or 0.0),
            diet=row.get('diet', 'average') or 'average',
            flights=int(row.get('flights', 0) or 0),
            footprint=float(row.get('footprint', 0.0) or 0.0),
            eco_score=int(row.get('eco_score', 0) or 0)
        )

@dataclass
class CategoryComparison:
    """Result of comparing a user's category against a reference stat."""
    category_name: str
    user_value: float
    reference_mean: float
    reference_median: float
    percentile: float
    is_better_than_average: bool
    difference_from_mean: float
    percentage_difference: float
    normalized_score: float # 0 to 100, where 100 is best

@dataclass
class BenchmarkResult:
    """Full benchmark comparison result."""
    user_id: int
    assessment_id: int
    profile_name: str
    overall_percentile: float
    categories: Dict[str, CategoryComparison]
    strengths: List[str]
    weaknesses: List[str]
    insights: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class HistoricalTrendData:
    """Data structure for passing historical trends to the UI."""
    dates: List[datetime]
    footprints: List[float]
    eco_scores: List[float]
    transport_vals: List[float]
    electricity_vals: List[float]
    diet_vals: List[float]
    flights_vals: List[float]
    percentiles: List[float] # Tracking percentile vs a specific profile over time
