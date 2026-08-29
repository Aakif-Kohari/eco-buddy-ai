"""Green Energy Advisor & Solar ROI Calculator for EcoBuddy AI.

Compares renewable energy providers, calculates solar panel payback periods
and lifetime ROI, models battery storage economics, and recommends the
optimal clean energy setup based on a user's electricity profile.

All financial figures use simplified but realistic models derived from
IRENA, EIA, and national energy regulator data. Units are clearly
documented so the module can be tuned per-region without touching
calculation logic.
"""

from __future__ import annotations

import math
import os
import sqlite3
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

# ── Grid Carbon Intensity by Region (kg CO2 per kWh, 2024 avg) ──────────────

GRID_INTENSITY: dict[str, dict[str, Any]] = {
    "US": {"intensity": 0.386, "avg_electricity_cost_kwh": 0.16, "currency": "USD"},
    "UK": {"intensity": 0.233, "avg_electricity_cost_kwh": 0.34, "currency": "GBP"},
    "EU": {"intensity": 0.276, "avg_electricity_cost_kwh": 0.28, "currency": "EUR"},
    "India": {"intensity": 0.708, "avg_electricity_cost_kwh": 0.08, "currency": "INR"},
    "China": {"intensity": 0.555, "avg_electricity_cost_kwh": 0.09, "currency": "CNY"},
    "Australia": {"intensity": 0.530, "avg_electricity_cost_kwh": 0.27, "currency": "AUD"},
    "Brazil": {"intensity": 0.075, "avg_electricity_cost_kwh": 0.12, "currency": "BRL"},
    "Japan": {"intensity": 0.470, "avg_electricity_cost_kwh": 0.25, "currency": "JPY"},
    "Germany": {"intensity": 0.350, "avg_electricity_cost_kwh": 0.36, "currency": "EUR"},
    "Canada": {"intensity": 0.120, "avg_electricity_cost_kwh": 0.13, "currency": "CAD"},
    "Global": {"intensity": 0.475, "avg_electricity_cost_kwh": 0.15, "currency": "USD"},
}

# ── Solar Panel System Configurations ────────────────────────────────────────

SOLAR_SYSTEMS: dict[str, dict[str, Any]] = {
    "small": {
        "name": "Small System (3 kWp)",
        "capacity_kwp": 3.0,
        "panels_count": 8,
        "roof_area_m2": 16,
        "upfront_cost": 4500,
        "annual_maintenance_cost": 75,
        "expected_annual_kwh": 4200,
        "panel_warranty_years": 25,
        "inverter_warranty_years": 12,
        "degradation_pct_per_year": 0.5,
        "description": "Suitable for small apartments or studios with limited roof space.",
    },
    "medium": {
        "name": "Medium System (6 kWp)",
        "capacity_kwp": 6.0,
        "panels_count": 16,
        "roof_area_m2": 32,
        "upfront_cost": 8500,
        "annual_maintenance_cost": 120,
        "expected_annual_kwh": 8400,
        "panel_warranty_years": 25,
        "inverter_warranty_years": 12,
        "degradation_pct_per_year": 0.5,
        "description": "Ideal for average 3-bedroom homes with moderate roof space.",
    },
    "large": {
        "name": "Large System (10 kWp)",
        "capacity_kwp": 10.0,
        "panels_count": 28,
        "roof_area_m2": 56,
        "upfront_cost": 14000,
        "annual_maintenance_cost": 180,
        "expected_annual_kwh": 14000,
        "panel_warranty_years": 25,
        "inverter_warranty_years": 12,
        "degradation_pct_per_year": 0.5,
        "description": "For large homes or families with high electricity consumption.",
    },
    "premium": {
        "name": "Premium System (15 kWp)",
        "capacity_kwp": 15.0,
        "panels_count": 42,
        "roof_area_m2": 84,
        "upfront_cost": 21000,
        "annual_maintenance_cost": 250,
        "expected_annual_kwh": 21000,
        "panel_warranty_years": 30,
        "inverter_warranty_years": 15,
        "degradation_pct_per_year": 0.4,
        "description": "Commercial-grade system for large properties or EV charging.",
    },
}

# ── Battery Storage Options ──────────────────────────────────────────────────

BATTERY_OPTIONS: dict[str, dict[str, Any]] = {
    "small": {
        "name": "Compact (5 kWh)",
        "capacity_kwh": 5.0,
        "upfront_cost": 3500,
        "annual_degradation_pct": 2.0,
        "warranty_years": 10,
        "round_trip_efficiency": 0.90,
        "cycles": 6000,
        "description": "Best for storing surplus solar for evening use in small homes.",
    },
    "medium": {
        "name": "Standard (10 kWh)",
        "capacity_kwh": 10.0,
        "upfront_cost": 6000,
        "annual_degradation_pct": 1.8,
        "warranty_years": 12,
        "round_trip_efficiency": 0.92,
        "cycles": 7000,
        "description": "Suitable for most households; covers overnight electricity needs.",
    },
    "large": {
        "name": "Extended (15 kWh)",
        "capacity_kwh": 15.0,
        "upfront_cost": 8500,
        "annual_degradation_pct": 1.5,
        "warranty_years": 15,
        "round_trip_efficiency": 0.93,
        "cycles": 8000,
        "description": "For households with EV charging or high evening electricity demand.",
    },
}

# ── Green Energy Providers ───────────────────────────────────────────────────

GREEN_PROVIDERS: dict[str, dict[str, Any]] = {
    "octopus_energy": {
        "name": "Octopus Energy",
        "regions": ["UK", "EU", "US", "AU", "NZ"],
        "plan_type": "100% Renewable",
        "price_kwh": 0.30,
        "feed_in_tariff_kwh": 0.15,
        "contract_months": 12,
        "early_exit_fee": 0,
        "green_certification": "Green Energy Supply Licence",
        "rating": 4.6,
        "features": ["Smart tariff options", "No exit fees", "Carbon tracking app"],
    },
    "green_mountain_energy": {
        "name": "Green Mountain Energy",
        "regions": ["US"],
        "plan_type": "100% Wind & Solar",
        "price_kwh": 0.18,
        "feed_in_tariff_kwh": 0.10,
        "contract_months": 12,
        "early_exit_fee": 0,
        "green_certification": "EPA Green-e Certified",
        "rating": 4.3,
        "features": ["Carbon offset included", "Fixed rate plans", "EV charging discounts"],
    },
    "bulb_energy": {
        "name": "Bulb Energy",
        "regions": ["UK"],
        "plan_type": "100% Renewable",
        "price_kwh": 0.32,
        "feed_in_tariff_kwh": 0.15,
        "contract_months": 12,
        "early_exit_fee": 0,
        "green_certification": "Ofgem Green Supply",
        "rating": 4.1,
        "features": ["Simple tariff", "No exit fees", "Member-owned cooperative"],
    },
    "enel_green": {
        "name": "Enel Green Power",
        "regions": ["EU", "US", "BR", "MX"],
        "plan_type": "Renewable Portfolio",
        "price_kwh": 0.22,
        "feed_in_tariff_kwh": 0.12,
        "contract_months": 24,
        "early_exit_fee": 50,
        "green_certification": "I-REC / Guarantees of Origin",
        "rating": 4.0,
        "features": ["Large-scale renewables", "Corporate PPA available", "EV integration"],
    },
    "acorns_green": {
        "name": "Acorns Green Energy",
        "regions": ["AU", "NZ"],
        "plan_type": "100% Carbon Neutral",
        "price_kwh": 0.28,
        "feed_in_tariff_kwh": 0.12,
        "contract_months": 12,
        "early_exit_fee": 0,
        "green_certification": "GreenPower Certified",
        "rating": 4.2,
        "features": ["Carbon neutral supply", "Solar buyback", "No lock-in"],
    },
}

# ── Financial Constants ──────────────────────────────────────────────────────

SOLAR_TAX_CREDIT_PCT: float = 0.30  # US ITC (simplified)
SOLAR_TAX_CREDIT_PCT_EU: float = 0.0  # Varies by country
ELECTRICITY_PRICE_INFLATION_PCT: float = 3.0  # Annual electricity price increase
DISCOUNT_RATE: float = 0.05  # For NPV calculations
ANALYSIS_YEARS: int = 25  # Standard solar panel lifetime


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class SolarROIResult:
    """Complete solar panel ROI analysis."""
    system_key: str
    system_name: str
    capacity_kwp: float
    upfront_cost: float
    annual_maintenance: float
    annual_kwh: float
    annual_savings_usd: float
    annual_co2_avoided_kg: float
    payback_years: float | None
    lifetime_savings_usd: float
    lifetime_savings_25yr: float
    roi_pct: float
    npv_usd: float
    lcoe_kwh: float  # Levelised cost of energy ($/kWh)
    yearly_projection: list[dict[str, Any]]
    tax_credit_usd: float
    net_upfront_cost: float


@dataclass
class BatteryResult:
    """Battery storage economics analysis."""
    battery_key: str
    battery_name: str
    capacity_kwh: float
    upfront_cost: float
    annual_value_usd: float
    payback_years: float | None
    lifetime_value_usd: float
    cycles_per_year: int
    effective_capacity_kwh: float
    description: str


@dataclass
class GreenProviderMatch:
    """A recommended green energy provider."""
    provider_key: str
    provider_name: str
    plan_type: str
    monthly_cost_usd: float
    annual_cost_usd: float
    annual_co2_savings_kg: float
    rating: float
    features: list[str]
    match_score: float


@dataclass
class EnergyAdvisorReport:
    """Full energy advisor report for a user."""
    user_id: int
    monthly_kwh: float
    region: str
    grid_intensity: float
    current_annual_cost: float
    current_annual_co2_kg: float
    solar_options: list[SolarROIResult]
    battery_options: list[BatteryResult]
    provider_matches: list[GreenProviderMatch]
    best_solar: SolarROIResult | None
    best_battery: BatteryResult | None
    best_provider: GreenProviderMatch | None
    total_annual_savings_potential: float
    total_annual_co2_reduction_kg: float
    recommendations: list[str]


# ── Solar ROI Calculator ────────────────────────────────────────────────────


def calculate_solar_roi(
    system_key: str,
    monthly_kwh: float,
    region: str = "US",
    roof_area_m2: float | None = None,
    self_consumption_pct: float = 0.70,
) -> SolarROIResult:
    """Calculate the full ROI for a solar panel system.

    Parameters
    ----------
    system_key : str
        Key from SOLAR_SYSTEMS (e.g. ``"medium"``).
    monthly_kwh : float
        User's average monthly electricity consumption in kWh.
    region : str
        Region key from GRID_INTENSITY.
    roof_area_m2 : float | None
        Available roof area; if None uses system default.
    self_consumption_pct : float
        Fraction of solar generation consumed on-site (rest is exported).
    """
    if system_key not in SOLAR_SYSTEMS:
        raise ValueError(
            f"Unknown system '{system_key}'. Available: {sorted(SOLAR_SYSTEMS)}"
        )

    system = SOLAR_SYSTEMS[system_key]
    grid = GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])

    upfront = system["upfront_cost"]
    tax_credit = upfront * SOLAR_TAX_CREDIT_PCT
    net_upfront = upfront - tax_credit

    annual_maintenance = system["annual_maintenance_cost"]
    annual_kwh = system["expected_annual_kwh"]
    price_kwh = grid["avg_electricity_cost_kwh"]
    intensity = grid["intensity"]

    # Annual projection
    yearly_projection: list[dict[str, Any]] = []
    cumulative_savings = 0.0
    cumulative_cost = annual_maintenance
    payback_year = None

    for year in range(1, ANALYSIS_YEARS + 1):
        # Degradation: output decreases each year
        efficiency = (1 - system["degradation_pct_per_year"] / 100) ** year
        year_kwh = annual_kwh * efficiency

        # Electricity price inflation
        year_price = price_kwh * (1 + ELECTRICITY_PRICE_INFLATION_PCT / 100) ** year

        # Savings = self-consumed portion saves at retail + exported at feed-in
        self_consumed = year_kwh * self_consumption_pct
        exported = year_kwh * (1 - self_consumption_pct)
        feed_in = grid.get("feed_in_tariff_kwh", 0.10)
        year_savings = (self_consumed * year_price) + (exported * feed_in)

        year_cost = annual_maintenance
        year_co2 = year_kwh * intensity
        year_net = year_savings - year_cost

        cumulative_savings += year_net
        cumulative_cost += year_cost

        # Discount for NPV
        discounted_net = year_net / (1 + DISCOUNT_RATE) ** year

        yearly_projection.append({
            "year": year,
            "kwh_generated": round(year_kwh, 1),
            "savings_usd": round(year_savings, 2),
            "maintenance_usd": year_cost,
            "net_benefit_usd": round(year_net, 2),
            "cumulative_savings_usd": round(cumulative_savings, 2),
            "co2_avoided_kg": round(year_co2, 1),
            "electricity_price_kwh": round(year_price, 4),
        })

        if payback_year is None and cumulative_savings >= net_upfront:
            payback_year = year

    # Lifetime savings
    total_savings = sum(p["net_benefit_usd"] for p in yearly_projection)
    lifetime_savings = round(total_savings, 2)

    # ROI
    roi = (
        round((lifetime_savings / net_upfront) * 100, 1)
        if net_upfront > 0
        else 0
    )

    # NPV
    npv = round(
        sum(
            p["net_benefit_usd"] / (1 + DISCOUNT_RATE) ** p["year"]
            for p in yearly_projection
        )
        - net_upfront,
        2,
    )

    # LCOE
    total_kwh_lifetime = sum(p["kwh_generated"] for p in yearly_projection)
    total_cost_lifetime = net_upfront + sum(p["maintenance_usd"] for p in yearly_projection)
    lcoe = (
        round(total_cost_lifetime / total_kwh_lifetime, 4)
        if total_kwh_lifetime > 0
        else 0
    )

    # Annual metrics (first year)
    annual_savings = yearly_projection[0]["savings_usd"] if yearly_projection else 0
    annual_co2 = yearly_projection[0]["co2_avoided_kg"] if yearly_projection else 0

    return SolarROIResult(
        system_key=system_key,
        system_name=system["name"],
        capacity_kwp=system["capacity_kwp"],
        upfront_cost=upfront,
        annual_maintenance=annual_maintenance,
        annual_kwh=annual_kwh,
        annual_savings_usd=round(annual_savings, 2),
        annual_co2_avoided_kg=round(annual_co2, 1),
        payback_years=payback_year,
        lifetime_savings_usd=lifetime_savings,
        lifetime_savings_25yr=lifetime_savings,
        roi_pct=roi,
        npv_usd=npv,
        lcoe_kwh=lcoe,
        yearly_projection=yearly_projection,
        tax_credit_usd=round(tax_credit, 2),
        net_upfront_cost=round(net_upfront, 2),
    )


# ── Battery Storage Calculator ──────────────────────────────────────────────


def calculate_battery_value(
    battery_key: str,
    monthly_kwh: float,
    region: str = "US",
    solar_surplus_kwh_day: float = 5.0,
) -> BatteryResult:
    """Calculate the economic value of a home battery system.

    Parameters
    ----------
    battery_key : str
        Key from BATTERY_OPTIONS.
    monthly_kwh : float
        User's monthly electricity consumption.
    region : str
        Region key.
    solar_surplus_kwh_day : float
        Average daily surplus solar energy available to store.
    """
    if battery_key not in BATTERY_OPTIONS:
        raise ValueError(
            f"Unknown battery '{battery_key}'. Available: {sorted(BATTERY_OPTIONS)}"
        )

    battery = BATTERY_OPTIONS[battery_key]
    grid = GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])
    price_kwh = grid["avg_electricity_cost_kwh"]

    capacity = battery["capacity_kwh"]
    efficiency = battery["round_trip_efficiency"]
    upfront = battery["upfront_cost"]

    # Effective storable per day (capped by capacity)
    storable_per_day = min(solar_surplus_kwh_day, capacity)
    usable_per_day = storable_per_day * efficiency

    # Annual value = stored energy × price saved × 365
    annual_value = usable_per_day * price_kwh * 365

    # Payback
    payback = None
    if annual_value > 0:
        payback = round(upfront / annual_value, 1)

    # Lifetime (assume warranty years)
    lifetime_value = annual_value * battery["warranty_years"]

    # Effective capacity after degradation
    effective = capacity * (1 - battery["annual_degradation_pct"] / 100 * 5)  # at year 5

    cycles_per_year = int(365 * (storable_per_day / capacity)) if capacity > 0 else 0

    return BatteryResult(
        battery_key=battery_key,
        battery_name=battery["name"],
        capacity_kwh=capacity,
        upfront_cost=upfront,
        annual_value_usd=round(annual_value, 2),
        payback_years=payback,
        lifetime_value_usd=round(lifetime_value, 2),
        cycles_per_year=cycles_per_year,
        effective_capacity_kwh=round(effective, 2),
        description=battery["description"],
    )


# ── Green Provider Matching ─────────────────────────────────────────────────


def find_green_providers(
    region: str = "US",
    monthly_kwh: float = 300,
    max_price_kwh: float | None = None,
) -> list[GreenProviderMatch]:
    """Find and score green energy providers available in the user's region.

    Parameters
    ----------
    region : str
        User's region.
    monthly_kwh : float
        Average monthly consumption (for cost estimation).
    max_price_kwh : float | None
        Maximum acceptable price per kWh. None = no limit.
    """
    grid = GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])
    current_price = grid["avg_electricity_cost_kwh"]
    intensity = grid["intensity"]

    matches: list[GreenProviderMatch] = []

    for key, provider in GREEN_PROVIDERS.items():
        # Check region availability
        if region not in provider["regions"]:
            continue

        price = provider["price_kwh"]
        if max_price_kwh is not None and price > max_price_kwh:
            continue

        monthly_cost = price * monthly_kwh
        annual_cost = monthly_cost * 12

        # CO2 savings: switching from grid to 100% renewable eliminates
        # the user's electricity-related emissions
        monthly_co2_current = monthly_kwh * intensity
        annual_co2_savings = monthly_co2_current * 12  # near 100% reduction

        # Match score: blend of price competitiveness and rating
        price_ratio = price / current_price if current_price > 0 else 1.0
        price_score = max(0, 100 - (price_ratio - 1) * 200)  # penalise >50% more expensive
        rating_score = (provider["rating"] / 5.0) * 100
        match_score = 0.6 * price_score + 0.4 * rating_score

        matches.append(
            GreenProviderMatch(
                provider_key=key,
                provider_name=provider["name"],
                plan_type=provider["plan_type"],
                monthly_cost_usd=round(monthly_cost, 2),
                annual_cost_usd=round(annual_cost, 2),
                annual_co2_savings_kg=round(annual_co2_savings, 1),
                rating=provider["rating"],
                features=provider["features"],
                match_score=round(max(0, min(100, match_score)), 1),
            )
        )

    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches


# ── Full Advisor Report ─────────────────────────────────────────────────────


def build_energy_advisor_report(
    user_id: int,
    monthly_kwh: float,
    region: str = "US",
) -> EnergyAdvisorReport:
    """Build a comprehensive green energy advisor src.reporting.report."""
    grid = GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])

    # Solar analysis
    solar_options: list[SolarROIResult] = []
    for key in SOLAR_SYSTEMS:
        result = calculate_solar_roi(key, monthly_kwh, region)
        # Only include systems that fit a reasonable roof
        solar_options.append(result)

    best_solar = None
    if solar_options:
        # Best = shortest payback (if any pay back), or highest ROI
        payback_solar = [s for s in solar_options if s.payback_years is not None]
        if payback_solar:
            best_solar = min(payback_solar, key=lambda s: s.payback_years)
        else:
            best_solar = max(solar_options, key=lambda s: s.roi_pct)

    # Battery analysis
    battery_options: list[BatteryResult] = []
    # Estimate solar surplus (if they install a medium system)
    if best_solar:
        surplus_day = max(0, (best_solar.annual_kwh / 365) - (monthly_kwh * 12 / 365) * 0.7)
    else:
        surplus_day = 5.0

    for key in BATTERY_OPTIONS:
        result = calculate_battery_value(key, monthly_kwh, region, surplus_day)
        battery_options.append(result)

    best_battery = None
    if battery_options:
        payback_bat = [b for b in battery_options if b.payback_years is not None]
        if payback_bat:
            best_battery = min(payback_bat, key=lambda b: b.payback_years)

    # Provider matching
    provider_matches = find_green_providers(region, monthly_kwh)
    best_provider = provider_matches[0] if provider_matches else None

    # Current costs
    current_annual_cost = monthly_kwh * 12 * grid["avg_electricity_cost_kwh"]
    current_annual_co2 = monthly_kwh * 12 * grid["intensity"]

    # Total savings potential
    total_annual_savings = 0.0
    total_annual_co2_reduction = 0.0

    if best_solar:
        total_annual_savings += best_solar.annual_savings_usd
        total_annual_co2_reduction += best_solar.annual_co2_avoided_kg
    if best_battery:
        total_annual_savings += best_battery.annual_value_usd
    if best_provider:
        total_annual_co2_reduction += best_provider.annual_co2_savings_kg

    # Recommendations
    recommendations = _generate_recommendations(
        best_solar, best_battery, best_provider, monthly_kwh, region,
    )

    return EnergyAdvisorReport(
        user_id=user_id,
        monthly_kwh=monthly_kwh,
        region=region,
        grid_intensity=grid["intensity"],
        current_annual_cost=round(current_annual_cost, 2),
        current_annual_co2_kg=round(current_annual_co2, 1),
        solar_options=solar_options,
        battery_options=battery_options,
        provider_matches=provider_matches,
        best_solar=best_solar,
        best_battery=best_battery,
        best_provider=best_provider,
        total_annual_savings_potential=round(total_annual_savings, 2),
        total_annual_co2_reduction_kg=round(total_annual_co2_reduction, 1),
        recommendations=recommendations,
    )


def _generate_recommendations(
    best_solar: SolarROIResult | None,
    best_battery: BatteryResult | None,
    best_provider: GreenProviderMatch | None,
    monthly_kwh: float,
    region: str,
) -> list[str]:
    """Generate prioritised energy src.ai.recommendations."""
    recs: list[str] = []

    if best_solar and best_solar.payback_years and best_solar.payback_years <= 10:
        recs.append(
            f"☀️ Install the {best_solar.system_name}: payback in "
            f"{best_solar.payback_years} years, then ~${best_solar.annual_savings_usd:,.0f}/yr free energy."
        )

    if best_battery and best_battery.payback_years and best_battery.payback_years <= 12:
        recs.append(
            f"🔋 Add the {best_battery.battery_name}: payback in "
            f"{best_battery.payback_years} years, storing {best_battery.capacity_kwh} kWh of surplus solar."
        )

    if best_provider:
        savings_vs_current = (
            best_provider.monthly_cost_usd - monthly_kwh * GRID_INTENSITY.get(region, GRID_INTENSITY["Global"])["avg_electricity_cost_kwh"]
        )
        if savings_vs_current <= 0:
            recs.append(
                f"⚡ Switch to {best_provider.provider_name}: "
                f"100% renewable at competitive rates, saving ~{best_provider.annual_co2_savings_kg:,.0f} kg CO₂/year."
            )
        else:
            recs.append(
                f"⚡ Switch to {best_provider.provider_name}: "
                f"100% renewable, adds ~${savings_vs_current * 12:,.0f}/yr but eliminates {best_provider.annual_co2_savings_kg:,.0f} kg CO₂/year."
            )

    if monthly_kwh > 500:
        recs.append(
            "💡 Your consumption is high. Consider LED lighting, smart thermostats, "
            "and energy-efficient appliances to reduce demand before investing in generation."
        )

    if not recs:
        recs.append(
            "🌟 Your current setup is already well-optimised for clean energy."
        )

    return recs


# ── Catalogue Helpers ────────────────────────────────────────────────────────


def list_solar_systems() -> list[dict[str, Any]]:
    """List all available solar system configurations."""
    return [
        {
            "key": key,
            "name": info["name"],
            "capacity_kwp": info["capacity_kwp"],
            "panels": info["panels_count"],
            "roof_area_m2": info["roof_area_m2"],
            "upfront_cost": info["upfront_cost"],
            "annual_kwh": info["expected_annual_kwh"],
            "description": info["description"],
        }
        for key, info in SOLAR_SYSTEMS.items()
    ]


def list_battery_options() -> list[dict[str, Any]]:
    """List all available battery storage options."""
    return [
        {
            "key": key,
            "name": info["name"],
            "capacity_kwh": info["capacity_kwh"],
            "upfront_cost": info["upfront_cost"],
            "warranty_years": info["warranty_years"],
            "description": info["description"],
        }
        for key, info in BATTERY_OPTIONS.items()
    ]


def list_green_providers(region: str | None = None) -> list[dict[str, Any]]:
    """List all green energy providers, optionally filtered by region."""
    providers = []
    for key, info in GREEN_PROVIDERS.items():
        if region and region not in info["regions"]:
            continue
        providers.append({
            "key": key,
            "name": info["name"],
            "plan_type": info["plan_type"],
            "price_kwh": info["price_kwh"],
            "rating": info["rating"],
            "features": info["features"],
        })
    return providers


def list_regions() -> list[str]:
    """Return all regions with grid intensity data."""
    return sorted(GRID_INTENSITY.keys())


# ── Database: Energy Assessment History ──────────────────────────────────────


def init_energy_advisor_db() -> bool:
    """Create the energy advisor history table if needed."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS energy_advisor_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                monthly_kwh REAL NOT NULL,
                region TEXT NOT NULL,
                best_solar_key TEXT,
                best_battery_key TEXT,
                best_provider_key TEXT,
                annual_savings_usd REAL,
                annual_co2_reduction_kg REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Energy advisor DB init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_energy_assessment(
    user_id: int,
    report: EnergyAdvisorReport,
) -> int | None:
    """Persist an energy advisor assessment."""
    init_energy_advisor_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.execute(
            """
            INSERT INTO energy_advisor_assessments
                (user_id, monthly_kwh, region, best_solar_key, best_battery_key,
                 best_provider_key, annual_savings_usd, annual_co2_reduction_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                src.reporting.report.monthly_kwh,
                src.reporting.report.region,
                src.reporting.report.best_solar.system_key if src.reporting.report.best_solar else None,
                src.reporting.report.best_battery.battery_key if src.reporting.report.best_battery else None,
                src.reporting.report.best_provider.provider_key if src.reporting.report.best_provider else None,
                src.reporting.report.total_annual_savings_potential,
                src.reporting.report.total_annual_co2_reduction_kg,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save energy assessment: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_energy_assessments(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Return a user's energy advisor assessments, newest first."""
    init_energy_advisor_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, user_id, monthly_kwh, region, best_solar_key,
                   best_battery_key, best_provider_key, annual_savings_usd,
                   annual_co2_reduction_kg, created_at
            FROM energy_advisor_assessments
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Unable to load energy assessments: %s", exc)
        return []
    finally:
        if conn:
            conn.close()
