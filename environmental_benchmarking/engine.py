"""
Core engine for Environmental Benchmarking calculations and analysis.
"""
import math
from typing import Dict, List, Optional
from .models import ReferenceProfile, CategoryStat, UserAssessment, CategoryComparison, BenchmarkResult
from .profiles_extended import get_default_profiles_extended

class BenchmarkEngine:
    """Core engine for all benchmarking and comparison logic."""
    
    def __init__(self):
        self.profiles = get_default_profiles_extended()
        
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
