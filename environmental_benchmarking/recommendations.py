"""
Detailed rule engine for actionable sustainability recommendations based on benchmarks.
"""
from typing import List
from .models import CategoryComparison

class RecommendationEngine:
    """Generates highly specific recommendations from benchmark data."""
    
    def generate_recommendations(self, comparisons: dict) -> List[str]:
        """Process all category comparisons and return a list of actionable advice."""
        recs = []
        
        if "transport" in comparisons:
            recs.extend(self._transport_recs(comparisons["transport"]))
        if "electricity" in comparisons:
            recs.extend(self._electricity_recs(comparisons["electricity"]))
        if "diet" in comparisons:
            recs.extend(self._diet_recs(comparisons["diet"]))
        if "flights" in comparisons:
            recs.extend(self._flight_recs(comparisons["flights"]))
            
        return recs
        
    def _transport_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Your transport emissions are in the bottom 20%. Switch to EV, carpooling, or public transit immediately to see massive reductions.")
        elif comp.percentile <= 40:
            recs.append("Your transport emissions are below average. Try replacing 2 car trips a week with cycling or walking.")
        elif comp.percentile >= 80:
            recs.append("EXCELLENT: Your transport emissions are very low! Consider sharing your commuting habits with the community.")
        return recs

    def _electricity_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Your home energy usage is extremely high. Schedule a home energy audit, check insulation, and upgrade to a smart thermostat.")
            recs.append("Consider switching to a green energy provider or installing solar panels if feasible.")
        elif comp.percentile <= 40:
            recs.append("Your electricity footprint is above average. Ensure all bulbs are LED and unplug phantom loads.")
        return recs

    def _diet_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Dietary footprint is very high. Reducing red meat consumption by just 50% can dramatically improve this score.")
        elif comp.percentile <= 40:
            recs.append("Consider adopting a 'Meatless Monday' routine to lower your dietary carbon impact.")
        elif comp.percentile >= 90:
            recs.append("EXCELLENT: Your diet is highly sustainable! Your food choices are actively fighting climate change.")
        return recs

    def _flight_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.user_value > 2000: # high absolute flights
            recs.append("Air travel is dominating your footprint. For every necessary flight, consider high-quality carbon offsets.")
            recs.append("Can any of your recent flights be replaced with high-speed rail or virtual meetings?")
        return recs
