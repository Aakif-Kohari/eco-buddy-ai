import os

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"
eb_dir = os.path.join(base_dir, "environmental_benchmarking")
os.makedirs(eb_dir, exist_ok=True)

models_code = '''\
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
            assessment_id=row.get('id', 0),
            user_id=row.get('user_id', 1),
            date=date_val,
            transport=row.get('transport', 'car'),
            distance=float(row.get('distance', 0.0) or 0.0),
            electricity=float(row.get('electricity', 0.0) or 0.0),
            diet=row.get('diet', 'average'),
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
'''

profiles_code = '''\
"""
Pre-defined reference profiles for benchmarking.
"""
from .models import ReferenceProfile, CategoryStat

def get_default_profiles() -> dict:
    """Returns a dictionary of default reference profiles."""
    profiles = {}
    
    # 1. Global Average Profile
    profiles['global'] = ReferenceProfile(
        id='global',
        name='Global Average',
        description='Average environmental footprint worldwide.',
        region_code='GLO',
        transport_stat=CategoryStat(mean=1200, median=900, std_dev=800, min_val=0, max_val=10000, p10=100, p25=300, p75=1500, p90=2500),
        electricity_stat=CategoryStat(mean=3000, median=2500, std_dev=2000, min_val=0, max_val=20000, p10=500, p25=1200, p75=4000, p90=6000),
        diet_stat=CategoryStat(mean=1500, median=1400, std_dev=500, min_val=500, max_val=4000, p10=800, p25=1100, p75=1800, p90=2200),
        flights_stat=CategoryStat(mean=1, median=0, std_dev=2, min_val=0, max_val=50, p10=0, p25=0, p75=1, p90=3),
        footprint_stat=CategoryStat(mean=4500, median=4000, std_dev=2500, min_val=500, max_val=30000, p10=1500, p25=2500, p75=6000, p90=8500),
        eco_score_stat=CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=20, p25=35, p75=65, p90=80)
    )
    
    # 2. US Average (High Consumption)
    profiles['us'] = ReferenceProfile(
        id='us',
        name='United States Average',
        description='Average environmental footprint in the US.',
        region_code='US',
        transport_stat=CategoryStat(mean=4500, median=4000, std_dev=2000, min_val=0, max_val=20000, p10=1000, p25=2500, p75=6000, p90=8000),
        electricity_stat=CategoryStat(mean=10000, median=9000, std_dev=4000, min_val=0, max_val=30000, p10=3000, p25=6000, p75=12000, p90=16000),
        diet_stat=CategoryStat(mean=2500, median=2400, std_dev=800, min_val=800, max_val=6000, p10=1200, p25=1800, p75=3000, p90=3800),
        flights_stat=CategoryStat(mean=3, median=2, std_dev=4, min_val=0, max_val=100, p10=0, p25=0, p75=4, p90=8),
        footprint_stat=CategoryStat(mean=15000, median=14000, std_dev=6000, min_val=2000, max_val=60000, p10=6000, p25=10000, p75=19000, p90=24000),
        eco_score_stat=CategoryStat(mean=35, median=35, std_dev=15, min_val=0, max_val=100, p10=15, p25=25, p75=45, p90=60)
    )
    
    # 3. EU Average
    profiles['eu'] = ReferenceProfile(
        id='eu',
        name='European Union Average',
        description='Average environmental footprint in the EU.',
        region_code='EU',
        transport_stat=CategoryStat(mean=2000, median=1800, std_dev=1200, min_val=0, max_val=12000, p10=400, p25=1000, p75=2800, p90=3800),
        electricity_stat=CategoryStat(mean=4000, median=3500, std_dev=1800, min_val=0, max_val=15000, p10=1500, p25=2500, p75=5000, p90=6500),
        diet_stat=CategoryStat(mean=1800, median=1700, std_dev=600, min_val=600, max_val=4500, p10=1000, p25=1400, p75=2200, p90=2800),
        flights_stat=CategoryStat(mean=2, median=1, std_dev=3, min_val=0, max_val=50, p10=0, p25=0, p75=3, p90=6),
        footprint_stat=CategoryStat(mean=7000, median=6500, std_dev=3000, min_val=1500, max_val=25000, p10=3000, p25=4500, p75=9000, p90=12000),
        eco_score_stat=CategoryStat(mean=55, median=55, std_dev=18, min_val=0, max_val=100, p10=30, p25=42, p75=68, p90=82)
    )

    # 4. India Average (Developing Nation Example)
    profiles['in'] = ReferenceProfile(
        id='in',
        name='India Average',
        description='Average environmental footprint in India.',
        region_code='IN',
        transport_stat=CategoryStat(mean=600, median=400, std_dev=500, min_val=0, max_val=5000, p10=50, p25=150, p75=800, p90=1200),
        electricity_stat=CategoryStat(mean=900, median=700, std_dev=600, min_val=0, max_val=8000, p10=100, p25=300, p75=1200, p90=1800),
        diet_stat=CategoryStat(mean=900, median=800, std_dev=300, min_val=300, max_val=2500, p10=400, p25=600, p75=1100, p90=1400),
        flights_stat=CategoryStat(mean=0.2, median=0, std_dev=0.8, min_val=0, max_val=20, p10=0, p25=0, p75=0, p90=1),
        footprint_stat=CategoryStat(mean=1800, median=1500, std_dev=1000, min_val=200, max_val=15000, p10=500, p25=900, p75=2200, p90=3000),
        eco_score_stat=CategoryStat(mean=65, median=65, std_dev=15, min_val=0, max_val=100, p10=45, p25=55, p75=75, p90=85)
    )

    # 5. Sustainable Target (Paris Agreement)
    profiles['target'] = ReferenceProfile(
        id='target',
        name='Sustainable Target (Paris Agreement)',
        description='Target footprint to meet global climate goals (1.5C pathway).',
        region_code='TGT',
        transport_stat=CategoryStat(mean=500, median=400, std_dev=300, min_val=0, max_val=3000, p10=100, p25=200, p75=700, p90=1000),
        electricity_stat=CategoryStat(mean=1000, median=800, std_dev=500, min_val=0, max_val=5000, p10=200, p25=400, p75=1200, p90=1800),
        diet_stat=CategoryStat(mean=800, median=750, std_dev=300, min_val=400, max_val=2000, p10=500, p25=600, p75=1000, p90=1300),
        flights_stat=CategoryStat(mean=0, median=0, std_dev=0.5, min_val=0, max_val=2, p10=0, p25=0, p75=0, p90=1),
        footprint_stat=CategoryStat(mean=2000, median=1800, std_dev=800, min_val=500, max_val=6000, p10=800, p25=1200, p75=2500, p90=3200),
        eco_score_stat=CategoryStat(mean=85, median=85, std_dev=10, min_val=0, max_val=100, p10=70, p25=80, p75=92, p90=98)
    )

    # 6. High Income Eco-Conscious (Aspirational Profile)
    profiles['eco_conscious'] = ReferenceProfile(
        id='eco_conscious',
        name='Eco-Conscious (High Income)',
        description='Average for individuals actively reducing footprints in developed nations.',
        region_code='ECO',
        transport_stat=CategoryStat(mean=1200, median=1000, std_dev=800, min_val=0, max_val=6000, p10=200, p25=500, p75=1500, p90=2200),
        electricity_stat=CategoryStat(mean=2500, median=2000, std_dev=1500, min_val=0, max_val=10000, p10=500, p25=1000, p75=3000, p90=4500),
        diet_stat=CategoryStat(mean=1200, median=1100, std_dev=400, min_val=500, max_val=3000, p10=600, p25=900, p75=1400, p90=1800),
        flights_stat=CategoryStat(mean=1, median=0, std_dev=1, min_val=0, max_val=10, p10=0, p25=0, p75=1, p90=2),
        footprint_stat=CategoryStat(mean=4500, median=4000, std_dev=2000, min_val=1000, max_val=15000, p10=2000, p25=3000, p75=5500, p90=7000),
        eco_score_stat=CategoryStat(mean=75, median=75, std_dev=12, min_val=0, max_val=100, p10=60, p25=68, p75=82, p90=90)
    )
    
    # 7. China Average (High industry, growing consumer)
    profiles['cn'] = ReferenceProfile(
        id='cn',
        name='China Average',
        description='Average environmental footprint in China.',
        region_code='CN',
        transport_stat=CategoryStat(mean=1500, median=1200, std_dev=1000, min_val=0, max_val=8000, p10=200, p25=500, p75=2000, p90=3000),
        electricity_stat=CategoryStat(mean=4500, median=4000, std_dev=2500, min_val=0, max_val=15000, p10=1000, p25=2000, p75=6000, p90=8000),
        diet_stat=CategoryStat(mean=1600, median=1500, std_dev=500, min_val=500, max_val=4000, p10=800, p25=1200, p75=2000, p90=2400),
        flights_stat=CategoryStat(mean=0.5, median=0, std_dev=1.5, min_val=0, max_val=20, p10=0, p25=0, p75=0, p90=2),
        footprint_stat=CategoryStat(mean=8000, median=7500, std_dev=4000, min_val=1000, max_val=25000, p10=2500, p25=4500, p75=10500, p90=13500),
        eco_score_stat=CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=25, p25=35, p75=65, p90=75)
    )

    for p in profiles.values():
        p.validate_all()
            
    return profiles
'''

engine_code = '''\
"""
Core engine for Environmental Benchmarking calculations and analysis.
"""
import math
from typing import Dict, List, Optional
from .models import ReferenceProfile, CategoryStat, UserAssessment, CategoryComparison, BenchmarkResult
from .profiles import get_default_profiles

class BenchmarkEngine:
    """Core engine for all benchmarking and comparison logic."""
    
    def __init__(self):
        self.profiles = get_default_profiles()
        
    def get_profile(self, profile_id: str) -> ReferenceProfile:
        """Retrieve a profile by ID."""
        if profile_id not in self.profiles:
            raise ValueError(f"Profile '{profile_id}' not found.")
        return self.profiles[profile_id]
        
    def get_all_profiles(self) -> List[ReferenceProfile]:
        """Get list of all available profiles."""
        return list(self.profiles.values())

    def _calculate_percentile_from_stat(self, value: float, stat: CategoryStat, is_higher_better: bool = False) -> float:
        """
        Calculate an approximate percentile for a value given statistical distribution points.
        Uses linear interpolation between deciles.
        If is_higher_better is True, a high value gets a high percentile.
        If is_higher_better is False (e.g., carbon footprint), a low value gets a high percentile (better ranking).
        """
        if math.isnan(value):
            return 50.0
            
        if value <= stat.p10:
            cdf = 0.0 + (value - stat.min_val) / max(0.1, (stat.p10 - stat.min_val)) * 10.0
        elif value <= stat.p25:
            cdf = 10.0 + (value - stat.p10) / max(0.1, (stat.p25 - stat.p10)) * 15.0
        elif value <= stat.median:
            cdf = 25.0 + (value - stat.p25) / max(0.1, (stat.median - stat.p25)) * 25.0
        elif value <= stat.p75:
            cdf = 50.0 + (value - stat.median) / max(0.1, (stat.p75 - stat.median)) * 25.0
        elif value <= stat.p90:
            cdf = 75.0 + (value - stat.p75) / max(0.1, (stat.p90 - stat.p75)) * 15.0
        else:
            cdf = 90.0 + (value - stat.p90) / max(0.1, (stat.max_val - stat.p90)) * 10.0
            
        cdf = max(0.0, min(100.0, cdf))
        return cdf if is_higher_better else 100.0 - cdf

    def _calculate_normalized_score(self, value: float, stat: CategoryStat, is_higher_better: bool = False) -> float:
        """Calculate a 0-100 normalized score for visualization purposes."""
        if math.isnan(value):
            return 50.0
            
        value_clipped = max(stat.min_val, min(stat.max_val, value))
        range_val = stat.max_val - stat.min_val
        if range_val == 0:
            return 50.0
            
        score = ((value_clipped - stat.min_val) / range_val) * 100.0
        return score if is_higher_better else 100.0 - score

    def compare_category(self, category: str, user_val: float, profile: ReferenceProfile) -> CategoryComparison:
        """Compare a single category value against a reference profile."""
        stat = profile.get_stat(category)
        if not stat:
            raise ValueError(f"Category {category} not found in profile.")
            
        is_higher_better = (category == "eco_score")
        
        percentile = self._calculate_percentile_from_stat(user_val, stat, is_higher_better)
        normalized_score = self._calculate_normalized_score(user_val, stat, is_higher_better)
        
        diff = user_val - stat.mean
        if stat.mean != 0:
            pct_diff = (diff / stat.mean) * 100.0
        else:
            pct_diff = 0.0 if diff == 0 else (100.0 if diff > 0 else -100.0)
            
        if is_higher_better:
            is_better = user_val >= stat.mean
        else:
            is_better = user_val <= stat.mean
            
        return CategoryComparison(
            category_name=category,
            user_value=user_val,
            reference_mean=stat.mean,
            reference_median=stat.median,
            percentile=percentile,
            is_better_than_average=is_better,
            difference_from_mean=diff,
            percentage_difference=pct_diff,
            normalized_score=normalized_score
        )

    def extract_carbon_value(self, category: str, assessment: UserAssessment) -> float:
        """Extract or approximate the carbon equivalent value for a category."""
        if category == "transport":
            return assessment.distance * 0.2  # Approx kg CO2 per km for average car
        elif category == "electricity":
            return assessment.electricity * 0.4 # Approx kg CO2 per kWh
        elif category == "diet":
            diet_map = {"vegan": 1.5, "vegetarian": 2.0, "average": 4.0, "meat_heavy": 6.0}
            return diet_map.get(assessment.diet.lower(), 4.0) * 365 # Annualized approx
        elif category == "flights":
            return assessment.flights * 500.0 # Approx 500kg per flight
        elif category == "footprint":
            return assessment.footprint
        elif category == "eco_score":
            return float(assessment.eco_score)
        else:
            return 0.0

    def compare_assessment(self, assessment: UserAssessment, profile_id: str) -> BenchmarkResult:
        """Compare a full user assessment against a reference profile."""
        profile = self.get_profile(profile_id)
        
        categories = ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]
        comparisons = {}
        
        for cat in categories:
            user_val = self.extract_carbon_value(cat, assessment)
            comp = self.compare_category(cat, user_val, profile)
            comparisons[cat] = comp
            
        overall_percentile = comparisons["footprint"].percentile
        
        # Analyze strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for cat, comp in comparisons.items():
            if cat in ["footprint", "eco_score"]:
                continue
            if comp.percentile >= 70:
                strengths.append(cat)
            elif comp.percentile <= 40:
                weaknesses.append(cat)
                
        insights = self._generate_insights(comparisons, profile.name)
        
        return BenchmarkResult(
            user_id=assessment.user_id,
            assessment_id=assessment.assessment_id,
            profile_name=profile.name,
            overall_percentile=overall_percentile,
            categories=comparisons,
            strengths=strengths,
            weaknesses=weaknesses,
            insights=insights
        )
        
    def _generate_insights(self, comparisons: Dict[str, CategoryComparison], profile_name: str) -> List[str]:
        """Generate personalized insights based on comparison results."""
        insights = []
        
        fp_comp = comparisons.get("footprint")
        if fp_comp:
            if fp_comp.percentile >= 90:
                insights.append(f"Outstanding! Your overall footprint is better than 90% of the {profile_name}.")
            elif fp_comp.percentile >= 50:
                insights.append(f"Good job! Your footprint is below the {profile_name} average.")
            else:
                insights.append(f"Your footprint is higher than the {profile_name} average. Focusing on your weakest categories will help.")
                
        trans_comp = comparisons.get("transport")
        if trans_comp and trans_comp.percentile <= 35:
            insights.append("Transportation is a major contributor to your footprint. Consider carpooling, public transit, or cycling.")
        elif trans_comp and trans_comp.percentile >= 80:
            insights.append("Your transport emissions are excellently low. Keep up the green commuting!")
            
        elec_comp = comparisons.get("electricity")
        if elec_comp and elec_comp.percentile <= 35:
            insights.append("Your home energy use is high. Simple changes like LED bulbs, smart thermostats, or unplugging idle devices can make a big difference.")
            
        diet_comp = comparisons.get("diet")
        if diet_comp and diet_comp.percentile <= 35:
            insights.append("Your diet has a high carbon intensity. Try incorporating more plant-based meals each week.")
            
        flights_comp = comparisons.get("flights")
        if flights_comp and flights_comp.percentile <= 35:
            insights.append("Air travel is heavily impacting your score. Consider local vacations or train travel when possible.")
            
        if len(insights) <= 1:
            insights.append("You're maintaining highly sustainable habits across the board!")
            
        return insights
'''

history_code = '''\
"""
History tracking and trend analysis for Environmental Benchmarking.
"""
from typing import List, Optional
import sqlite3
import pandas as pd
from .models import UserAssessment, HistoricalTrendData
from .engine import BenchmarkEngine

class HistoryAnalyzer:
    """Handles historical DB fetching and trend calculation."""
    
    def __init__(self, db_path: str = "eco_buddy.db"):
        self.db_path = db_path
        self.engine = BenchmarkEngine()
        
    def get_user_history(self, user_id: int, limit: int = 50) -> List[UserAssessment]:
        """Fetch the assessment history for a specific user."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM assessments WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to models, reversing to get chronological order
            return [UserAssessment.from_db_row(dict(row)) for row in reversed(rows)]
        except Exception as e:
            # Fallback or empty if table doesn't exist
            print(f"Error fetching history: {e}")
            return []

    def calculate_trends(self, user_id: int, profile_id: str = "global") -> Optional[HistoricalTrendData]:
        """Calculate historical trends against a specific profile."""
        assessments = self.get_user_history(user_id)
        if not assessments:
            return None
            
        dates = []
        footprints = []
        eco_scores = []
        transports = []
        electricities = []
        diets = []
        flights = []
        percentiles = []
        
        for a in assessments:
            dates.append(a.date)
            footprints.append(a.footprint)
            eco_scores.append(a.eco_score)
            
            transports.append(self.engine.extract_carbon_value("transport", a))
            electricities.append(self.engine.extract_carbon_value("electricity", a))
            diets.append(self.engine.extract_carbon_value("diet", a))
            flights.append(self.engine.extract_carbon_value("flights", a))
            
            # Get overall percentile vs chosen profile for this specific assessment
            res = self.engine.compare_assessment(a, profile_id)
            percentiles.append(res.overall_percentile)
            
        return HistoricalTrendData(
            dates=dates,
            footprints=footprints,
            eco_scores=eco_scores,
            transport_vals=transports,
            electricity_vals=electricities,
            diet_vals=diets,
            flights_vals=flights,
            percentiles=percentiles
        )
'''

with open(os.path.join(eb_dir, "__init__.py"), "w") as f:
    f.write("")
with open(os.path.join(eb_dir, "models.py"), "w") as f:
    f.write(models_code)
with open(os.path.join(eb_dir, "profiles.py"), "w") as f:
    f.write(profiles_code)
with open(os.path.join(eb_dir, "engine.py"), "w") as f:
    f.write(engine_code)
with open(os.path.join(eb_dir, "history.py"), "w") as f:
    f.write(history_code)
