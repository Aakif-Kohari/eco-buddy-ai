"""
Decision Simulator Calculator.

Provides comprehensive environmental and financial calculations for scenarios.
"""

from src.decision_engine.models import (
    ScenarioInputs, EnvironmentalImpact, FinancialImpact,
    TransportMode, EnergySource, DietType
)

class ImpactCalculator:
    """Calculates environmental impact from raw scenario inputs."""
    
    # Constants for CO2e per unit
    CO2_PER_LITER_GASOLINE = 2.31  # kg CO2e
    LITERS_PER_GALLON = 3.785
    KWH_PER_GALLON_GASOLINE_EQUIV = 33.7
    
    CO2_PER_KWH_GRID = 0.4  # average global kg CO2e per kWh
    CO2_PER_KWH_RENEWABLE = 0.05
    CO2_PER_KWH_SOLAR = 0.04
    CO2_PER_THERM_GAS = 5.3
    
    # Diet (kg CO2e per year)
    DIET_IMPACT = {
        DietType.MEAT_HEAVY: 3300.0,
        DietType.OMNIVORE: 2500.0,
        DietType.PESCATARIAN: 1900.0,
        DietType.FLEXITARIAN: 1500.0,
        DietType.VEGETARIAN: 1200.0,
        DietType.VEGAN: 900.0,
        DietType.LOCAL_SOURCED: 1800.0,
    }
    
    # Waste (kg CO2e per kg of waste)
    CO2_PER_KG_WASTE_LANDFILL = 1.2
    CO2_PER_KG_WASTE_RECYCLED = 0.1
    KG_PER_TRASH_BAG = 5.0
    
    @classmethod
    def calculate(cls, inputs: ScenarioInputs) -> EnvironmentalImpact:
        impact = EnvironmentalImpact()
        
        # 1. Transport Impact
        annual_commute_km = inputs.transport.weekly_commute_km * 52 * (1 - (inputs.transport.telecommute_days_per_week / 5.0))
        annual_weekend_km = inputs.transport.weekend_travel_km * 52
        total_annual_km = annual_commute_km + annual_weekend_km
        
        mode = inputs.transport.primary_mode
        if mode == TransportMode.ICE_CAR or mode == TransportMode.HYBRID_CAR:
            gallons_used = (total_annual_km * 0.621371) / inputs.transport.car_efficiency_mpg
            impact.transport_co2e = gallons_used * cls.CO2_PER_LITER_GASOLINE * cls.LITERS_PER_GALLON
        elif mode == TransportMode.EV_CAR:
            kwh_used = (total_annual_km / 100) * inputs.transport.ev_efficiency_kwh_per_100km
            # Assuming EV uses default grid for simplicity, could be enhanced
            impact.transport_co2e = kwh_used * cls.CO2_PER_KWH_GRID
        elif mode == TransportMode.PUBLIC_TRANSIT:
            impact.transport_co2e = total_annual_km * 0.05 # Bus/Train average
        elif mode in [TransportMode.WALKING, TransportMode.CYCLING]:
            impact.transport_co2e = 0.0
        elif mode == TransportMode.CARPOOL:
            gallons_used = (total_annual_km * 0.621371) / inputs.transport.car_efficiency_mpg
            impact.transport_co2e = (gallons_used * cls.CO2_PER_LITER_GASOLINE * cls.LITERS_PER_GALLON) / max(1, inputs.transport.carpool_passengers)
        
        # Flights (assume 1000kg CO2e per flight avg)
        impact.transport_co2e += inputs.transport.flights_per_year * 1000.0
        
        # 2. Energy Impact
        annual_kwh = inputs.energy.monthly_electricity_kwh * 12
        if inputs.energy.has_smart_thermostat:
            annual_kwh *= 0.85 # 15% savings
            
        source = inputs.energy.primary_source
        if source == EnergySource.GRID_DEFAULT:
            impact.energy_co2e = annual_kwh * cls.CO2_PER_KWH_GRID
        elif source == EnergySource.GRID_RENEWABLE:
            impact.energy_co2e = annual_kwh * cls.CO2_PER_KWH_RENEWABLE
        elif source == EnergySource.SOLAR_ROOF:
            impact.energy_co2e = annual_kwh * cls.CO2_PER_KWH_SOLAR
        else:
            impact.energy_co2e = annual_kwh * 0.1 # Wind/Geothermal estimate
            
        annual_gas = inputs.energy.monthly_gas_therms * 12
        impact.energy_co2e += annual_gas * cls.CO2_PER_THERM_GAS
        
        # 3. Food Impact
        base_food_co2 = cls.DIET_IMPACT.get(inputs.food.diet_type, 2500.0)
        # Waste modifier
        if inputs.food.food_waste_percentage > 20:
            base_food_co2 *= 1.2
        elif inputs.food.food_waste_percentage < 10:
            base_food_co2 *= 0.9
            
        if inputs.food.composting_enabled:
            base_food_co2 -= 100.0
            
        impact.food_co2e = max(0.0, base_food_co2)
        
        # 4. Waste Impact
        annual_trash_kg = inputs.waste.weekly_trash_bags * 52 * cls.KG_PER_TRASH_BAG
        recycled_kg = annual_trash_kg * (inputs.waste.recycling_rate_percentage / 100.0)
        landfill_kg = annual_trash_kg - recycled_kg
        
        impact.waste_generation_kg_per_year = annual_trash_kg
        impact.waste_co2e = (landfill_kg * cls.CO2_PER_KG_WASTE_LANDFILL) + (recycled_kg * cls.CO2_PER_KG_WASTE_RECYCLED)
        
        # 5. Water Impact (Liters)
        daily_shower = inputs.water.shower_duration_minutes * (9.0 if inputs.water.low_flow_fixtures_installed else 15.0)
        weekly_laundry = inputs.water.weekly_laundry_loads * 50.0
        weekly_dishes = inputs.water.dishwasher_usage_per_week * 20.0
        weekly_lawn = inputs.water.lawn_watering_hours_per_week * 600.0
        
        annual_water = (daily_shower * 365) + ((weekly_laundry + weekly_dishes + weekly_lawn) * 52)
        annual_water -= (inputs.water.rainwater_harvesting_liters * 52)
        impact.water_footprint_liters_per_year = max(0.0, annual_water)
        
        # Totals
        impact.carbon_emissions_kg_co2e_per_year = (
            impact.transport_co2e + 
            impact.energy_co2e + 
            impact.food_co2e + 
            impact.waste_co2e
        )
        impact.energy_consumption_kwh_per_year = annual_kwh
        
        # Simple Sustainability Score (0-100), lower CO2 is better. 
        # Benchmark ~ 10,000 kg is average.
        score = 100 - (impact.carbon_emissions_kg_co2e_per_year / 15000.0 * 100)
        impact.sustainability_score = max(0.0, min(100.0, score))
        
        return impact

class FinancialCalculator:
    """Calculates financial costs and ROIs."""
    
    @classmethod
    def calculate(cls, inputs: ScenarioInputs) -> FinancialImpact:
        impact = FinancialImpact()
        
        upfront = 0.0
        monthly = 0.0
        
        # Transport
        monthly += inputs.transport.annual_maintenance_cost / 12.0
        mode = inputs.transport.primary_mode
        if mode == TransportMode.EV_CAR:
            upfront += 35000.0 # avg EV cost if adopting (assuming simplified adoption model)
            
        # Fuel costs
        annual_commute_km = inputs.transport.weekly_commute_km * 52 * (1 - (inputs.transport.telecommute_days_per_week / 5.0))
        annual_weekend_km = inputs.transport.weekend_travel_km * 52
        total_annual_km = annual_commute_km + annual_weekend_km
        
        if mode in [TransportMode.ICE_CAR, TransportMode.HYBRID_CAR]:
            gallons = (total_annual_km * 0.621371) / inputs.transport.car_efficiency_mpg
            monthly += (gallons * 3.50) / 12.0 # $3.50 per gallon
        elif mode == TransportMode.EV_CAR:
            kwh = (total_annual_km / 100) * inputs.transport.ev_efficiency_kwh_per_100km
            monthly += (kwh * 0.15) / 12.0 # $0.15 per kWh
            
        # Energy
        monthly += inputs.energy.monthly_electricity_kwh * 0.15
        monthly += inputs.energy.monthly_gas_therms * 1.20
        
        if inputs.energy.has_smart_thermostat:
            upfront += 200.0
            monthly -= (inputs.energy.monthly_electricity_kwh * 0.15 * 0.10) # 10% savings
            
        if inputs.energy.primary_source == EnergySource.SOLAR_ROOF:
            upfront += 12000.0
            monthly -= (inputs.energy.monthly_electricity_kwh * 0.15 * 0.80) # 80% bill reduction
            
        # Food
        monthly += inputs.food.grocery_budget_monthly
        monthly += inputs.food.dining_out_frequency_per_week * 4 * 25.0 # $25 per meal
        
        # Water
        water_cost_per_liter = 0.002
        water_inputs = inputs.water
        daily_shower = water_inputs.shower_duration_minutes * (9.0 if water_inputs.low_flow_fixtures_installed else 15.0)
        annual_water = (daily_shower * 365) + ((water_inputs.weekly_laundry_loads * 50.0 + water_inputs.dishwasher_usage_per_week * 20.0 + water_inputs.lawn_watering_hours_per_week * 600.0) * 52)
        monthly += (annual_water * water_cost_per_liter) / 12.0
        
        if water_inputs.low_flow_fixtures_installed:
            upfront += 150.0
            
        impact.implementation_cost_upfront = upfront
        impact.monthly_recurring_cost = max(0.0, monthly)
        impact.yearly_recurring_cost = impact.monthly_recurring_cost * 12.0
        
        return impact
