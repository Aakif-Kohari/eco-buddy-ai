import os
import textwrap

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"
eb_dir = os.path.join(base_dir, "environmental_benchmarking")
os.makedirs(eb_dir, exist_ok=True)

def generate_engine():
    content = '''\
"""
Environmental Benchmarking Engine.

This module provides comprehensive functionality for calculating, comparing,
and analyzing user environmental sustainability footprints against various
reference profiles (e.g., regional, global averages).
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

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
        if self.min_val > self.max_val:
            raise ValueError("min_val cannot be greater than max_val")
        if not (self.p10 <= self.p25 <= self.median <= self.p75 <= self.p90):
            raise ValueError("Percentiles must be monotonically increasing")

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
        mapping = {
            "transport": self.transport_stat,
            "electricity": self.electricity_stat,
            "diet": self.diet_stat,
            "flights": self.flights_stat,
            "footprint": self.footprint_stat,
            "eco_score": self.eco_score_stat,
        }
        return mapping.get(category)

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
        return cls(
            assessment_id=row.get('id', 0),
            user_id=row.get('user_id', 1),
            date=row.get('date', datetime.now()),
            transport=row.get('transport', 'car'),
            distance=float(row.get('distance', 0.0)),
            electricity=float(row.get('electricity', 0.0)),
            diet=row.get('diet', 'average'),
            flights=int(row.get('flights', 0)),
            footprint=float(row.get('footprint', 0.0)),
            eco_score=int(row.get('eco_score', 0))
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

class BenchmarkEngine:
    """Core engine for all benchmarking and comparison logic."""
    
    def __init__(self):
        self.profiles = self._load_default_profiles()
        
    def _load_default_profiles(self) -> Dict[str, ReferenceProfile]:
        """Loads default regional profiles with detailed statistics."""
        profiles = {}
        
        # Profile 1: Global Average
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
        
        # Profile 2: US Average (Higher consumption)
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
        
        # Profile 3: EU Average
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
        
        # Profile 4: Sustainable Goal (Target profile)
        profiles['target'] = ReferenceProfile(
            id='target',
            name='Sustainable Target (Paris Agreement)',
            description='Target footprint to meet global climate goals.',
            region_code='TGT',
            transport_stat=CategoryStat(mean=500, median=400, std_dev=300, min_val=0, max_val=3000, p10=100, p25=200, p75=700, p90=1000),
            electricity_stat=CategoryStat(mean=1000, median=800, std_dev=500, min_val=0, max_val=5000, p10=200, p25=400, p75=1200, p90=1800),
            diet_stat=CategoryStat(mean=800, median=750, std_dev=300, min_val=400, max_val=2000, p10=500, p25=600, p75=1000, p90=1300),
            flights_stat=CategoryStat(mean=0, median=0, std_dev=0.5, min_val=0, max_val=2, p10=0, p25=0, p75=0, p90=1),
            footprint_stat=CategoryStat(mean=2000, median=1800, std_dev=800, min_val=500, max_val=6000, p10=800, p25=1200, p75=2500, p90=3200),
            eco_score_stat=CategoryStat(mean=85, median=85, std_dev=10, min_val=0, max_val=100, p10=70, p25=80, p75=92, p90=98)
        )
        
        for p in profiles.values():
            for cat in ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]:
                p.get_stat(cat).validate()
                
        return profiles

    def get_profile(self, profile_id: str) -> ReferenceProfile:
        """Retrieve a profile by ID."""
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found.")
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
            
        # For carbon emissions, lower is better. We want the percentile to represent "how good you are".
        # So if you have 0 footprint, you are in the 99th percentile (better than 99% of people).
        
        # Let's map the value to raw CDF first.
        # Raw CDF = what percentage of people have a value LESS than this.
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
        
        # If higher is better (like eco_score), your score is just the CDF.
        # If lower is better (like footprint), your score is 100 - CDF.
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
            
        # Overall percentile based on footprint
        overall_percentile = comparisons["footprint"].percentile
        
        # Analyze strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for cat, comp in comparisons.items():
            if cat in ["footprint", "eco_score"]:
                continue
                
            if comp.percentile >= 75:
                strengths.append(cat)
            elif comp.percentile <= 35:
                weaknesses.append(cat)
                
        # Generate Insights
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
        
        # Overall insight
        fp_comp = comparisons.get("footprint")
        if fp_comp:
            if fp_comp.percentile >= 90:
                insights.append(f"Outstanding! Your overall footprint is better than 90% of the {profile_name}.")
            elif fp_comp.percentile >= 50:
                insights.append(f"Good job! Your footprint is below the {profile_name} average.")
            else:
                insights.append(f"Your footprint is higher than the {profile_name} average. There's room for improvement!")
                
        # Category specific insights
        trans_comp = comparisons.get("transport")
        if trans_comp and trans_comp.percentile <= 30:
            insights.append("Transportation is a major contributor to your footprint. Consider carpooling, public transit, or cycling.")
            
        elec_comp = comparisons.get("electricity")
        if elec_comp and elec_comp.percentile <= 30:
            insights.append("Your home energy use is high. Simple changes like LED bulbs or smart thermostats can make a big difference.")
            
        diet_comp = comparisons.get("diet")
        if diet_comp and diet_comp.percentile <= 30:
            insights.append("Your diet has a high carbon intensity. Try incorporating more plant-based meals each week.")
            
        flights_comp = comparisons.get("flights")
        if flights_comp and flights_comp.percentile <= 30:
            insights.append("Air travel is heavily impacting your score. Consider local vacations or train travel when possible.")
            
        if not insights:
            insights.append("Keep maintaining your current sustainable habits!")
            
        return insights


'''
    with open(eb_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
def generate_tests():
    # Will add >500 lines of rigorous tests
    pass

def generate_streamlit():
    # Will add >800 lines of UI
    pass

if __name__ == "__main__":
    generate_engine()
    print("Generated engine.py")
