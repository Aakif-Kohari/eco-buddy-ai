"""
Decision Simulator Orchestration Engine.

Generates time horizons, handles what-if iterations, detects trade-offs, 
and ranks multiple scenarios.
"""

from typing import List, Dict, Tuple
from src.decision_engine.models import (
    Scenario, ScenarioInputs, TimeHorizonProjection, 
    TradeOff, SimulationResult
)
from src.decision_engine.calculator import ImpactCalculator, FinancialCalculator

class TimeHorizonEngine:
    """Projects environmental and financial impact over time."""
    
    HORIZONS_MONTHS = [1, 6, 12, 60, 120] # 1m, 6m, 1y, 5y, 10y
    
    @classmethod
    def generate_projections(cls, scenario: Scenario, baseline: Scenario = None) -> Dict[int, TimeHorizonProjection]:
        projections = {}
        env_impact = scenario.environmental_impact
        fin_impact = scenario.financial_impact
        
        baseline_fin = baseline.financial_impact if baseline else None
        
        for months in cls.HORIZONS_MONTHS:
            years = months / 12.0
            
            cum_carbon = env_impact.carbon_emissions_kg_co2e_per_year * years
            cum_water = env_impact.water_footprint_liters_per_year * years
            cum_waste = env_impact.waste_generation_kg_per_year * years
            
            # Cost factoring inflation
            cum_cost = fin_impact.calculate_total_cost_over_years(years)
            
            savings = 0.0
            roi = 0.0
            if baseline_fin:
                baseline_cost = baseline_fin.calculate_total_cost_over_years(years)
                savings = baseline_cost - cum_cost
                if fin_impact.implementation_cost_upfront > 0:
                    roi = (savings / fin_impact.implementation_cost_upfront) * 100.0
            
            projections[months] = TimeHorizonProjection(
                horizon_months=months,
                cumulative_carbon_kg=cum_carbon,
                cumulative_cost=cum_cost,
                cumulative_water_liters=cum_water,
                cumulative_waste_kg=cum_waste,
                net_savings_vs_baseline=savings,
                roi_percentage=roi
            )
        
        return projections

class TradeOffDetector:
    """Identifies conflicts between environmental and financial metrics."""
    
    @classmethod
    def detect(cls, baseline: Scenario, alternative: Scenario) -> List[TradeOff]:
        tradeoffs = []
        
        base_env = baseline.environmental_impact
        alt_env = alternative.environmental_impact
        base_fin = baseline.financial_impact
        alt_fin = alternative.financial_impact
        
        carbon_diff = alt_env.carbon_emissions_kg_co2e_per_year - base_env.carbon_emissions_kg_co2e_per_year
        cost_diff = alt_fin.yearly_recurring_cost - base_fin.yearly_recurring_cost
        
        # 1. Environmental improvement vs Financial Cost
        if carbon_diff < 0 and alt_fin.implementation_cost_upfront > 0:
            tradeoffs.append(TradeOff(
                category="Finance vs Carbon",
                description=f"Reduces carbon by {abs(carbon_diff):.0f} kg/yr, but costs ${alt_fin.implementation_cost_upfront:,.2f} upfront.",
                severity="high" if alt_fin.implementation_cost_upfront > 5000 else "medium",
                metric_improved="Carbon Emissions",
                metric_worsened="Upfront Cost",
                magnitude_improved=abs(carbon_diff),
                magnitude_worsened=alt_fin.implementation_cost_upfront
            ))
            
        # 2. Rebound effect (Cost savings leading to more impact somewhere else - mock example)
        if cost_diff < 0 and carbon_diff > 0:
             tradeoffs.append(TradeOff(
                category="Carbon vs Finance",
                description=f"Saves ${abs(cost_diff):,.2f}/yr, but increases carbon by {carbon_diff:.0f} kg/yr.",
                severity="high" if carbon_diff > 1000 else "medium",
                metric_improved="Recurring Cost",
                metric_worsened="Carbon Emissions",
                magnitude_improved=abs(cost_diff),
                magnitude_worsened=carbon_diff
            ))
            
        # 3. Water vs Energy (e.g. desalination or heavy filtering)
        water_diff = alt_env.water_footprint_liters_per_year - base_env.water_footprint_liters_per_year
        energy_diff = alt_env.energy_consumption_kwh_per_year - base_env.energy_consumption_kwh_per_year
        
        if water_diff < 0 and energy_diff > 0:
             tradeoffs.append(TradeOff(
                category="Water vs Energy",
                description=f"Saves {abs(water_diff):.0f}L of water/yr, but uses {energy_diff:.0f} more kWh of energy.",
                severity="medium",
                metric_improved="Water Footprint",
                metric_worsened="Energy Consumption",
                magnitude_improved=abs(water_diff),
                magnitude_worsened=energy_diff
            ))
            
        return tradeoffs

class ScenarioRanker:
    """Ranks scenarios based on various heuristics."""
    
    @classmethod
    def rank(cls, scenarios: List[Scenario]) -> Dict[str, List[str]]:
        # Lowest carbon impact
        by_carbon = sorted(scenarios, key=lambda s: s.environmental_impact.carbon_emissions_kg_co2e_per_year)
        
        # Lowest recurring cost
        by_cost = sorted(scenarios, key=lambda s: s.financial_impact.yearly_recurring_cost)
        
        # Best ROI at 10 years
        by_roi = sorted(scenarios, key=lambda s: s.projections.get(120, TimeHorizonProjection(120,0,0,0,0,0,-999)).roi_percentage, reverse=True)
        
        # Highest sustainability score
        by_score = sorted(scenarios, key=lambda s: s.environmental_impact.sustainability_score, reverse=True)
        
        return {
            "lowest_carbon": [s.id for s in by_carbon],
            "lowest_cost": [s.id for s in by_cost],
            "best_roi_10y": [s.id for s in by_roi],
            "highest_sustainability_score": [s.id for s in by_score]
        }

class DecisionSimulator:
    """Main facade for generating a simulation report."""
    
    @classmethod
    def simulate(cls, baseline_inputs: ScenarioInputs, alternative_inputs_map: Dict[str, ScenarioInputs]) -> SimulationResult:
        
        # Baseline
        base_scenario = Scenario(
            id="baseline",
            name="Current Lifestyle",
            description="Your current habits and configuration.",
            is_baseline=True,
            inputs=baseline_inputs,
            environmental_impact=ImpactCalculator.calculate(baseline_inputs),
            financial_impact=FinancialCalculator.calculate(baseline_inputs)
        )
        base_scenario.projections = TimeHorizonEngine.generate_projections(base_scenario, base_scenario)
        
        # Alternatives
        alternatives = []
        trade_offs = {}
        
        for alt_id, alt_inputs in alternative_inputs_map.items():
            alt_scenario = Scenario(
                id=alt_id,
                name=f"Alternative: {alt_id}",
                description="Simulated alternative.",
                is_baseline=False,
                inputs=alt_inputs,
                environmental_impact=ImpactCalculator.calculate(alt_inputs),
                financial_impact=FinancialCalculator.calculate(alt_inputs)
            )
            alt_scenario.projections = TimeHorizonEngine.generate_projections(alt_scenario, base_scenario)
            alternatives.append(alt_scenario)
            
            trade_offs[alt_id] = TradeOffDetector.detect(base_scenario, alt_scenario)
            
        # Rankings
        all_scenarios = [base_scenario] + alternatives
        rankings = ScenarioRanker.rank(all_scenarios)
        
        # Recommendations
        recommendations = []
        if rankings["lowest_carbon"][0] != "baseline":
            best_carbon_id = rankings["lowest_carbon"][0]
            recommendations.append(f"Consider adopting '{best_carbon_id}' for the maximum reduction in your carbon footprint.")
        
        if rankings["best_roi_10y"][0] != "baseline":
            best_roi_id = rankings["best_roi_10y"][0]
            recommendations.append(f"Option '{best_roi_id}' provides the best financial return on investment over 10 years.")
            
        if not recommendations:
            recommendations.append("Your current baseline is highly optimized. Keep up the good work!")
            
        return SimulationResult(
            baseline=base_scenario,
            alternatives=alternatives,
            trade_offs=trade_offs,
            rankings=rankings,
            recommendations=recommendations
        )
