import os
import logging
import requests
import json
import datetime
import math

logger = logging.getLogger(__name__)from config import (
    ECO_SCORE_BASELINE, ECO_SCORE_SENSITIVITY, CATEGORY_WEIGHTS,
    VALID_TRANSPORT, VALID_DIET, VALID_REGIONS,
    MAX_DISTANCE, MAX_ELECTRICITY, MAX_FLIGHTS,
    TRANSPORT_EMISSION_FACTORS, DIET_EMISSION_FACTORS,
    normalize_diet,
)
from cache import cached
from cache_config import TTL_EXTERNAL_API, CACHE_CATEGORY_API


@cached(ttl=TTL_EXTERNAL_API, category=CACHE_CATEGORY_API)
def fetch_emission_factors(region: str) -> dict:
    """
    Fetches dynamic emission factors from a third-party Carbon API.
    Provides graceful fallback to static factors if the API fails.
    """
    # Static fallbacks
    factors = {
        "electricity": 0.82, # kg CO2 per kWh
        "flight": 250.0,     # kg CO2 per flight
        "is_dynamic": False
    }
    
    api_key = os.environ.get("CARBON_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return factors
        
    try:
        url = "https://api.climatiq.io/data/v1/estimate"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "emission_factor": {
                "activity_id": "electricity-energy_source_grid_mix",
                "region": region if region != "Global" else "earth"
            },
            "parameters": {"energy": 1, "energy_unit": "kWh"}
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            factors["electricity"] = data.get("co2e", factors["electricity"])
            factors["is_dynamic"] = True
            
        flight_payload = {
            "emission_factor": {
                "activity_id": "passenger_flight-route_type_domestic",
                "region": region if region != "Global" else "earth"
            },
            "parameters": {"passengers": 1}
        }
        f_response = requests.post(url, json=flight_payload, headers=headers, timeout=5)
        if f_response.status_code == 200:
            f_data = f_response.json()
            factors["flight"] = f_data.get("co2e", factors["flight"])
            factors["is_dynamic"] = True
            
except Exception:
        logger.exception("API Error, falling back to static factors")        
    return factors


def calculate_footprint(
    transport,
    distance,
    electricity,
    diet,
    flights,
    region="Global",
    return_audit=False
):
    # Normalize diet input early
    diet = normalize_diet(diet)

    # Validate categorical inputs to avoid KeyError and provide clear errors
    if transport not in TRANSPORT_EMISSION_FACTORS:
        raise ValueError(
            f"Invalid transport '{transport}'. Must be one of: {', '.join(sorted(TRANSPORT_EMISSION_FACTORS.keys()))}"
        )
    if diet not in DIET_EMISSION_FACTORS:
        raise ValueError(
            f"Invalid diet '{diet}'. Must be one of: {', '.join(sorted(DIET_EMISSION_FACTORS.keys()))}"
        )

    # Validate region; fall back to Global when unknown
    if region not in VALID_REGIONS:
        region = "Global"

    # Coerce and clamp numeric inputs to reasonable ranges
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        raise ValueError("distance must be a number")
    distance = max(0.0, min(distance, MAX_DISTANCE))

    try:
        electricity = float(electricity)
    except (TypeError, ValueError):
        raise ValueError("electricity must be a number")
    electricity = max(0.0, min(electricity, MAX_ELECTRICITY))

    try:
        flights = int(flights)
    except (TypeError, ValueError):
        raise ValueError("flights must be an integer")
    flights = max(0, min(flights, MAX_FLIGHTS))

    contributors = {}

    # Transport emissions (kg CO₂ per km)
    transport_factor = TRANSPORT_EMISSION_FACTORS[transport]
    transport_emission = transport_factor * distance * 365
    contributors["Transport"] = round(transport_emission, 2)

    # Fetch dynamic factors (with fallback and caching)
    dynamic_factors = fetch_emission_factors(region)
    elec_factor = dynamic_factors["electricity"]
    flight_factor = dynamic_factors["flight"]

    # Electricity
    electricity_emission = electricity * elec_factor * 12
    contributors["Electricity"] = round(electricity_emission, 2)

    # Diet (annual estimate)
    diet_factor = DIET_EMISSION_FACTORS[diet]
    diet_emission = diet_factor
    contributors["Diet"] = diet_emission

    # Flights
    flight_emission = flights * flight_factor
    contributors["Flights"] = flight_emission

    total = sum(contributors.values())
    total_rounded = round(total, 2)

    audit_log = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "region": region,
        "is_dynamic_api_used": dynamic_factors.get("is_dynamic", False),
        "inputs": {
            "transport": transport,
            "daily_distance_km": distance,
            "monthly_electricity_kwh": electricity,
            "diet": diet,
            "annual_flights": flights,
        },
        "emission_factors": {
            "transport_kg_co2_per_km": transport_factor,
            "electricity_kg_co2_per_kwh": elec_factor,
            "diet_kg_co2_per_year": diet_factor,
            "flight_kg_co2_per_flight": flight_factor,
        },
        "intermediate_calculations": {
            "Transport": {
                "formula": "daily_distance_km * transport_factor * 365 days",
                "expression": f"{distance} km * {transport_factor} kg/km * 365",
                "raw_result": transport_emission,
                "rounded_result_kg": contributors["Transport"]
            },
            "Electricity": {
                "formula": "monthly_kwh * electricity_factor * 12 months",
                "expression": f"{electricity} kWh * {elec_factor} kg/kWh * 12",
                "raw_result": electricity_emission,
                "rounded_result_kg": contributors["Electricity"]
            },
            "Diet": {
                "formula": "annual_diet_emission_factor",
                "expression": f"{diet_factor} kg/year ({diet})",
                "raw_result": diet_emission,
                "rounded_result_kg": contributors["Diet"]
            },
            "Flights": {
                "formula": "annual_flights * flight_factor",
                "expression": f"{flights} flights * {flight_factor} kg/flight",
                "raw_result": flight_emission,
                "rounded_result_kg": contributors["Flights"]
            }
        },
        "total_emissions_kg_co2": total_rounded
    }

    if return_audit:
        return total_rounded, contributors, audit_log
    return total_rounded, contributors


def calculate_eco_score(total_footprint, contributors=None, return_audit=False):
    """
    Higher score = better sustainability
    Calculates a continuous score based on a sigmoid function.
    Supports per-category weighting if contributors are provided.
    Optionally returns audit log for score calculation.
    """
    audit = {
        "baseline": ECO_SCORE_BASELINE,
        "sensitivity": ECO_SCORE_SENSITIVITY,
        "category_weights": CATEGORY_WEIGHTS,
        "category_scores": {}
    }

    if contributors:
        weighted_score = 0.0
        for category, cat_total in contributors.items():
            weight = CATEGORY_WEIGHTS.get(category, 0.0)
            if weight > 0:
                cat_baseline = ECO_SCORE_BASELINE * weight
                cat_sensitivity = ECO_SCORE_SENSITIVITY * weight
                cat_score = 100 / (1 + math.exp((cat_total - cat_baseline) / cat_sensitivity))
                weighted_score += weight * cat_score
                audit["category_scores"][category] = {
                    "cat_total_kg": cat_total,
                    "weight": weight,
                    "cat_baseline": cat_baseline,
                    "cat_sensitivity": cat_sensitivity,
                    "raw_cat_score": cat_score,
                    "weighted_component": weight * cat_score
                }
        final_score = int(round(weighted_score))
        audit["final_weighted_score"] = weighted_score
        audit["final_score"] = final_score
    else:
        score = 100 / (1 + math.exp((total_footprint - ECO_SCORE_BASELINE) / ECO_SCORE_SENSITIVITY))
        final_score = int(round(score))
        audit["unweighted_raw_score"] = score
        audit["final_score"] = final_score

    if return_audit:
        return final_score, audit
    return final_score


def generate_full_audit_log(transport, distance, electricity, diet, flights, region="Global") -> dict:
    """
    Generates a comprehensive audit log dictionary including both carbon footprint
    and eco score intermediate calculation steps.
    """
    total, contributors, footprint_audit = calculate_footprint(
        transport, distance, electricity, diet, flights, region, return_audit=True
    )
    eco_score, eco_score_audit = calculate_eco_score(total, contributors, return_audit=True)
    
    return {
        "footprint_audit": footprint_audit,
        "eco_score_audit": eco_score_audit,
        "summary": {
            "total_footprint_kg_co2": total,
            "eco_score": eco_score,
            "contributors": contributors
        }
    }


def export_audit_log_json(audit_log: dict, indent: int = 2) -> str:
    """Exports an audit log dictionary into a formatted JSON string."""
    return json.dumps(audit_log, indent=indent)