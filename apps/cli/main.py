"""
EcoBuddy AI Command-Line Interface (CLI)

Provides terminal commands for quick assessment calculations, eco score evaluation,
water footprint audits, food impact insights, and exporting reports.
"""

import argparse
import sys
import json
from typing import Optional, List, Dict, Any

from src.carbon.emissions import calculate_footprint, calculate_eco_score
from src.ai.recommendations import generate_recommendations
from src.environment.water import (
    calculate_water_footprint,
    calculate_water_efficiency_score,
    calculate_potential_water_savings
)
from src.lifestyle.meal_planner import build_meal, INGREDIENTS
from src.utils.units import convert, format_quantity




def create_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="eco-cli",
        description="🌱 EcoBuddy AI - Command-Line Sustainability & Environmental Impact Suite"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- Carbon Assessment Command ---
    carbon_parser = subparsers.add_parser("carbon", help="Calculate annual carbon footprint")
    carbon_parser.add_argument("--transport", default="Car", choices=["Car", "Bike", "Public Transport", "Walking"], help="Primary transport mode")
    carbon_parser.add_argument("--distance", type=float, default=20.0, help="Daily travel distance (km)")
    carbon_parser.add_argument("--electricity", type=float, default=250.0, help="Monthly electricity consumption (kWh)")
    carbon_parser.add_argument("--diet", default="Non-Vegetarian", choices=["Vegetarian", "Non-Vegetarian", "Vegan", "Omnivore", "Heavy Meat"], help="Dietary pattern")
    carbon_parser.add_argument("--flights", type=int, default=1, help="Annual flight count")
    carbon_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # --- Water Audit Command ---
    water_parser = subparsers.add_parser("water", help="Calculate daily and annual water footprint")
    water_parser.add_argument("--shower", type=float, default=8.0, help="Shower duration in minutes")
    water_parser.add_argument("--laundry", type=float, default=3.0, help="Laundry loads per week")
    water_parser.add_argument("--diet", default="Omnivore", choices=["Vegan", "Vegetarian", "Omnivore", "Heavy Meat"], help="Diet type for virtual water")
    water_parser.add_argument("--dishwasher", type=float, default=4.0, help="Dishwasher runs per week")
    water_parser.add_argument("--garden", type=float, default=15.0, help="Garden watering minutes per week")
    water_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # --- Food Meal Impact Command ---
    food_parser = subparsers.add_parser("meal", help="Calculate carbon and water impact of a recipe/meal")
    food_parser.add_argument("--name", default="Custom Meal", help="Name of the meal")
    food_parser.add_argument("--item", action="append", nargs=2, metavar=("INGREDIENT", "GRAMS"), help="Ingredient name and quantity in grams (e.g. --item Beef 200 --item Rice 150)")
    food_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # --- Units Converter Command ---
    units_parser = subparsers.add_parser("convert", help="Convert physical quantities across metric/imperial units")
    units_parser.add_argument("value", type=float, help="Numeric value to convert")
    units_parser.add_argument("from_unit", help="Source unit symbol or key (e.g., km, mi, kg, lb, L, gal)")
    units_parser.add_argument("to_unit", help="Target unit symbol or key")

    return parser


def run_carbon_command(args: argparse.Namespace) -> int:
    """Execute carbon footprint computation."""
    footprint, breakdown = calculate_footprint(
        transport=args.transport,
        distance=args.distance,
        electricity=args.electricity,
        diet=args.diet,
        flights=args.flights
    )
    score = calculate_eco_score(footprint, breakdown)
    insight, recs = generate_recommendations(
        args.transport, args.electricity, args.diet, args.flights, breakdown
    )

    data = {
        "annual_footprint_kg_co2": round(footprint, 2),
        "eco_score": round(score, 1),
        "breakdown": breakdown,
        "insight": insight,
        "recommendations": recs
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("🌱 ECOBUDDY AI - CARBON FOOTPRINT ASSESSMENT")
        print("=" * 60)
        print(f"Annual Footprint : {data['annual_footprint_kg_co2']:.1f} kg CO2e/year")
        print(f"Eco Score        : {data['eco_score']:.0f} / 100")
        print("\nCategory Breakdown:")
        for cat, val in breakdown.items():
            print(f"  • {cat:<15}: {val:.1f} kg CO2e")
        print(f"\nInsight:\n  {insight}")
        print("\nActionable Recommendations:")
        for r in recs:
            print(f"  ✓ {r}")
        print("=" * 60)

    return 0


def run_water_command(args: argparse.Namespace) -> int:
    """Execute water audit calculation."""
    daily_liters, breakdown = calculate_water_footprint(
        shower_mins_per_day=args.shower,
        laundry_loads_per_week=int(args.laundry),
        dishwasher_runs_per_week=int(args.dishwasher),
        garden_mins_per_week=args.garden,
        diet=args.diet
    )
    score_info = calculate_water_efficiency_score(daily_liters)
    savings = calculate_potential_water_savings({
        "shower_mins": args.shower,
        "laundry_loads": args.laundry,
        "diet": args.diet
    })

    data = {
        "daily_liters": round(daily_liters, 1),
        "annual_liters": round(daily_liters * 365.0, 1),
        "efficiency_grade": score_info["grade"],
        "efficiency_score": score_info["score"],
        "status": score_info["status"],
        "breakdown": breakdown,
        "savings_actions": savings
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("💧 ECOBUDDY AI - WATER AUDIT ASSESSMENT")
        print("=" * 60)
        print(f"Daily Water Footprint  : {data['daily_liters']:.1f} Liters/day")
        print(f"Annual Water Footprint : {data['annual_liters']:.0f} Liters/year")
        print(f"Efficiency Grade       : {data['efficiency_grade']} ({data['efficiency_score']}/100 - {data['status']})")
        print("\nUsage Breakdown:")
        for cat, val in breakdown.items():
            print(f"  • {cat:<15}: {val:.1f} L/day")
        print("\nActionable Water Savings:")
        for s in savings:
            print(f"  ✓ {s['action']} (Save ~{s['annual_liters_saved']:.0f} L/year): {s['tip']}")
        print("=" * 60)

    return 0



def run_meal_command(args: argparse.Namespace) -> int:
    """Execute meal impact computation."""
    items = []
    if args.item:
        for ingr, grams_str in args.item:
            try:
                items.append((ingr.strip(), float(grams_str)))
            except ValueError:
                pass

    if not items:
        # Default sample ingredients if none provided
        items = [("Chicken", 150.0), ("Rice", 200.0), ("Peas", 80.0)]

    meal = build_meal(args.name, items)

    if args.json:
        print(json.dumps(meal, indent=2))
    else:
        print("=" * 60)
        print(f"🍽️  MEAL IMPACT ANALYSIS: {meal['name']}")
        print("=" * 60)
        print(f"Total Carbon Footprint : {meal['co2_kg']:.3f} kg CO2e")
        print(f"Virtual Water Footprint: {meal['water_l']:.1f} Litres")
        print(f"Total Portion Weight   : {meal['grams']:.1f} g")
        print(f"Impact Tier            : {meal['tier'].upper()}")
        print("\nIngredient Contributions:")
        for c in meal["contributions"]:
            print(f"  • {c['ingredient']:<14} ({c['grams']}g): {c['co2_kg']} kg CO2e ({c['co2_share_pct']}%), {c['water_l']} L water")
        print("=" * 60)

    return 0


def run_convert_command(args: argparse.Namespace) -> int:
    """Execute physical units conversion."""
    try:
        converted = convert(args.value, args.from_unit, args.to_unit)
        formatted = format_quantity(converted, args.to_unit, convert_to_preference=False)
        print(f"{args.value} {args.from_unit} = {formatted}")
        return 0
    except Exception as exc:
        print(f"Conversion Error: {exc}", file=sys.stderr)
        return 1



def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "carbon":
        return run_carbon_command(args)
    elif args.command == "water":
        return run_water_command(args)
    elif args.command == "meal":
        return run_meal_command(args)
    elif args.command == "convert":
        return run_convert_command(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
