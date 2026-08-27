"""How much material had to move, which no emission figure can tell you.

Every impact this app reports is an output: something leaving a system into air
or src.environment.water. Nothing measures the input - the rock, ore, sand, biomass and soil
that has to be moved to put a product in someone's hand.

That gap matters because carbon and material use decouple more often than people
expect, and where they decouple the app currently gives advice that is right on
one axis and wrong on the other. A smartphone's manufacturing carbon is modest.
Built up from its bill of materials, the abiotic material moved to make one is
around two hundred and forty times the phone's own mass - and roughly three
quarters of that is attributable to about four percent of the phone, the
fractions of a gram of gold and palladium on its boards. Reported in carbon
alone, a phone looks like a small purchase.

The ratio is the number that communicates
------------------------------------------
Not the tonnage. Direct material input, product mass, and the unused extraction
sitting behind both are reported separately, and the ratio between what you hold
and what was moved to make it is the single most legible figure this module
produces.

Categories are not summed
--------------------------
Abiotic extraction, biotic harvest, soil moved by erosion, water and air are
kept apart. Adding moved topsoil to extracted ore produces a large number with
no meaning, and the convention that does so - Total Material Requirement - is
exactly the kind of aggregate that stops a metric being usable.

Grade is geology, not technology
---------------------------------
The rucksack of a metal is essentially a function of ore grade, and grades are
falling. Copper mined at 0.6% moves roughly three hundred and fifty kilograms of
rock per kilogram of metal; at 0.3% it moves twice that. Grade is a parameter
here so a user can see how much of a metal's footprint is geology they cannot
improve and how much is process they might.

Depletion and criticality are different questions
--------------------------------------------------
Abiotic depletion asks how much of a finite stock a use consumes. Criticality
asks whether the supply can be interrupted - concentration of production,
substitutability, how much secondary material exists. A material can be abundant
and critical at once, and collapsing the two into a single "resource score"
makes both unusable. They stay separate.

Reserves are economic, not geological
--------------------------------------
"Years of reserves remaining" moves with price and exploration. Presenting it as
a fixed countdown would be misleading, so the reserve base is stated as an
assumption wherever the depletion figures use it.

Where this connects to code already merged
-------------------------------------------
*   ``src.utils.circular_economy_engine.py`` argues for repair and reuse without a metric
    that shows the size of the prize. This is that metric.
*   ``src.utils.device_lifecycle.py`` models replacement intervals; extending a laptop
    from three years to six avoids a material footprint far more striking than
    the carbon saving.
*   ``src.carbon.emission_factors.py`` covers the output side. This is the input side.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class MaterialError(ValueError):
    """Raised when a material footprint calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Flow categories
#
# Kept apart on purpose. A single "total material requirement" adds moved soil
# to extracted ore and produces a number that cannot be acted on.
# ---------------------------------------------------------------------------
CATEGORIES = ("abiotic", "biotic", "soil", "water", "air")

CATEGORY_LABELS = {
    "abiotic": "Abiotic (rock, ore, minerals)",
    "biotic": "Biotic (harvested biomass)",
    "soil": "Soil moved by erosion",
    "water": "Water",
    "air": "Air",
}


# ---------------------------------------------------------------------------
# Materials
#
# ``abiotic`` is kilograms of abiotic raw material moved per kilogram of the
# material delivered - the ecological rucksack. For metals it is dominated by
# overburden and tailings, and it is essentially a function of ore grade.
#
# ``adp`` is abiotic depletion potential in kg antimony equivalent per kg, on
# the CML convention where antimony is 1 by definition. ``hhi`` is a
# Herfindahl-Hirschman index of production concentration by country on the
# conventional 0-10,000 scale. ``substitutability`` runs 0 (easily replaced) to
# 1 (no known substitute at comparable performance). ``recycling_input_rate`` is
# the share of current supply met by end-of-life secondary material.
# ---------------------------------------------------------------------------
MATERIALS = {
    "gold": {
        "label": "Gold",
        "family": "precious_metal",
        "abiotic": 540000.0, "biotic": 0.0, "soil": 0.0,
        "water": 260000.0, "air": 1200.0,
        "ore_grade": 0.0000015, "reference_grade": 0.0000015,
        "adp": 52.0, "hhi": 1100, "substitutability": 0.30,
        "recycling_input_rate": 0.30,
        "note": "Half a million kilograms of rock per kilogram of metal at "
                "current grades. A single wedding ring moves about a tonne. "
                "Nothing else in consumer products comes close per gram.",
    },
    "palladium": {
        "label": "Palladium",
        "family": "precious_metal",
        "abiotic": 1000000.0, "biotic": 0.0, "soil": 0.0,
        "water": 400000.0, "air": 2100.0,
        "ore_grade": 0.0000020, "reference_grade": 0.0000020,
        "adp": 32.0, "hhi": 3200, "substitutability": 0.75,
        "recycling_input_rate": 0.55,
        "note": "The largest rucksack in this table and a supply concentrated "
                "in two countries. Used in milligram quantities, which is the "
                "only reason it is affordable at all.",
    },
    "platinum": {
        "label": "Platinum",
        "family": "precious_metal",
        "abiotic": 320000.0, "biotic": 0.0, "soil": 0.0,
        "water": 180000.0, "air": 900.0,
        "ore_grade": 0.0000040, "reference_grade": 0.0000040,
        "adp": 12.5, "hhi": 5100, "substitutability": 0.70,
        "recycling_input_rate": 0.60,
        "note": "Highly concentrated supply and a functioning recovery route "
                "from autocatalysts, which is why its recycling input rate is "
                "among the best of any metal.",
    },
    "silver": {
        "label": "Silver",
        "family": "precious_metal",
        "abiotic": 7500.0, "biotic": 0.0, "soil": 0.0,
        "water": 1600.0, "air": 55.0,
        "ore_grade": 0.00012, "reference_grade": 0.00012,
        "adp": 1.18, "hhi": 900, "substitutability": 0.45,
        "recycling_input_rate": 0.20,
        "note": "Mostly a by-product of copper, lead and zinc mining, so its "
                "supply follows the demand for other metals rather than its "
                "own - which makes it harder to expand than the reserve figure "
                "suggests.",
    },
    "copper": {
        "label": "Copper",
        "family": "base_metal",
        "abiotic": 348.0, "biotic": 0.0, "soil": 0.0,
        "water": 260.0, "air": 1.6,
        "ore_grade": 0.0060, "reference_grade": 0.0060,
        "adp": 0.00137, "hhi": 1600, "substitutability": 0.55,
        "recycling_input_rate": 0.55,
        "note": "The metal that most clearly demonstrates falling grades. "
                "Average grade has roughly halved over a century, so the same "
                "kilogram of copper moves twice the rock it used to.",
    },
    "aluminium": {
        "label": "Aluminium (primary)",
        "family": "base_metal",
        "abiotic": 37.0, "biotic": 0.0, "soil": 0.0,
        "water": 1200.0, "air": 12.0,
        "ore_grade": 0.230, "reference_grade": 0.230,
        "adp": 1.09e-9, "hhi": 2600, "substitutability": 0.35,
        "recycling_input_rate": 0.42,
        "note": "A modest rucksack for a metal, because bauxite is rich. Its "
                "problem is energy rather than material, which is exactly the "
                "kind of divergence a carbon-only view cannot show.",
    },
    "steel": {
        "label": "Steel (primary)",
        "family": "base_metal",
        "abiotic": 7.0, "biotic": 0.0, "soil": 0.0,
        "water": 55.0, "air": 2.4,
        "ore_grade": 0.560, "reference_grade": 0.560,
        "adp": 8.43e-8, "hhi": 1900, "substitutability": 0.25,
        "recycling_input_rate": 0.85,
        "note": "The lowest rucksack per kilogram of any metal here, and by "
                "far the largest in absolute terms because of how much of it "
                "is used. Both facts matter.",
    },
    "nickel": {
        "label": "Nickel",
        "family": "base_metal",
        "abiotic": 141.0, "biotic": 0.0, "soil": 0.0,
        "water": 380.0, "air": 3.2,
        "ore_grade": 0.0130, "reference_grade": 0.0130,
        "adp": 1.08e-4, "hhi": 1500, "substitutability": 0.50,
        "recycling_input_rate": 0.34,
        "note": "Battery demand is shifting production towards lateritic ores "
                "that need far more energy and move far more material than the "
                "sulphides they replace.",
    },
    "cobalt": {
        "label": "Cobalt",
        "family": "battery_metal",
        "abiotic": 750.0, "biotic": 0.0, "soil": 0.0,
        "water": 1100.0, "air": 8.0,
        "ore_grade": 0.0025, "reference_grade": 0.0025,
        "adp": 2.6e-5, "hhi": 6700, "substitutability": 0.65,
        "recycling_input_rate": 0.22,
        "note": "Mostly a by-product of copper and nickel, with the most "
                "concentrated supply of any battery material. Abundant in the "
                "crust and critical in practice - the clearest case for keeping "
                "depletion and criticality apart.",
    },
    "lithium": {
        "label": "Lithium",
        "family": "battery_metal",
        "abiotic": 120.0, "biotic": 0.0, "soil": 0.0,
        "water": 2100.0, "air": 4.5,
        "ore_grade": 0.0110, "reference_grade": 0.0110,
        "adp": 6.3e-4, "hhi": 2400, "substitutability": 0.80,
        "recycling_input_rate": 0.05,
        "note": "A small rucksack and an enormous water figure for brine "
                "extraction, which is why the category split matters here more "
                "than anywhere else in the table.",
    },
    "neodymium": {
        "label": "Neodymium (rare earth)",
        "family": "rare_earth",
        "abiotic": 1300.0, "biotic": 0.0, "soil": 0.0,
        "water": 890.0, "air": 15.0,
        "ore_grade": 0.0009, "reference_grade": 0.0009,
        "adp": 6.0e-5, "hhi": 7800, "substitutability": 0.85,
        "recycling_input_rate": 0.01,
        "note": "Not geologically rare. Critical because separation is "
                "concentrated in one country and because almost none is "
                "recovered from end-of-life magnets.",
    },
    "tantalum": {
        "label": "Tantalum",
        "family": "technology_metal",
        "abiotic": 2500.0, "biotic": 0.0, "soil": 0.0,
        "water": 1400.0, "air": 18.0,
        "ore_grade": 0.00035, "reference_grade": 0.00035,
        "adp": 4.06e-2, "hhi": 4400, "substitutability": 0.80,
        "recycling_input_rate": 0.04,
        "note": "Used in capacitors in milligram quantities and effectively "
                "never recovered from them, because nobody can economically "
                "separate a milligram from a circuit board.",
    },
    "indium": {
        "label": "Indium",
        "family": "technology_metal",
        "abiotic": 8600.0, "biotic": 0.0, "soil": 0.0,
        "water": 2300.0, "air": 26.0,
        "ore_grade": 0.00010, "reference_grade": 0.00010,
        "adp": 3.9, "hhi": 3900, "substitutability": 0.85,
        "recycling_input_rate": 0.01,
        "note": "Entirely a by-product of zinc refining, so its supply cannot "
                "respond to its own price. Every flat screen contains a little "
                "and essentially none comes back.",
    },
    "tin": {
        "label": "Tin",
        "family": "technology_metal",
        "abiotic": 300.0, "biotic": 0.0, "soil": 0.0,
        "water": 240.0, "air": 2.8,
        "ore_grade": 0.0070, "reference_grade": 0.0070,
        "adp": 1.65e-2, "hhi": 2100, "substitutability": 0.45,
        "recycling_input_rate": 0.32,
        "note": "Solder. Present in everything electronic and recovered "
                "reasonably well where boards are processed properly.",
    },
    "silicon_solar": {
        "label": "Silicon (solar grade)",
        "family": "semiconductor",
        "abiotic": 20.0, "biotic": 0.0, "soil": 0.0,
        "water": 380.0, "air": 6.0,
        "ore_grade": 0.460, "reference_grade": 0.460,
        "adp": 2.99e-11, "hhi": 5600, "substitutability": 0.60,
        "recycling_input_rate": 0.02,
        "note": "Quartz is abundant and purification is the hard part. A low "
                "rucksack, a high energy cost, and the reason solar is "
                "material-cheap and energy-expensive to make.",
    },
    "plastic_generic": {
        "label": "Plastic (generic polymer)",
        "family": "polymer",
        "abiotic": 5.4, "biotic": 0.0, "soil": 0.0,
        "water": 180.0, "air": 3.1,
        "ore_grade": None, "reference_grade": None,
        "adp": 8.0e-6, "hhi": 1200, "substitutability": 0.30,
        "recycling_input_rate": 0.09,
        "note": "Small on material and large on everything else. Included so "
                "the comparison against metals is available rather than "
                "assumed.",
    },
    "glass": {
        "label": "Glass",
        "family": "mineral",
        "abiotic": 3.0, "biotic": 0.0, "soil": 0.0,
        "water": 18.0, "air": 1.4,
        "ore_grade": None, "reference_grade": None,
        "adp": 1.4e-8, "hhi": 800, "substitutability": 0.20,
        "recycling_input_rate": 0.55,
        "note": "Sand, soda ash and limestone, all abundant. One of the few "
                "genuinely low-concern materials in this table.",
    },
    "concrete": {
        "label": "Concrete",
        "family": "mineral",
        "abiotic": 1.3, "biotic": 0.0, "soil": 0.0,
        "water": 3.6, "air": 0.9,
        "ore_grade": None, "reference_grade": None,
        "adp": 3.0e-9, "hhi": 400, "substitutability": 0.15,
        "recycling_input_rate": 0.35,
        "note": "The lowest rucksack ratio here and the largest material flow "
                "on Earth by mass. Ratio and total tell opposite stories, "
                "which is why both are reported.",
    },
    "timber": {
        "label": "Timber",
        "family": "biotic",
        "abiotic": 0.4, "biotic": 1.6, "soil": 2.9,
        "water": 480.0, "air": 0.3,
        "ore_grade": None, "reference_grade": None,
        "adp": 0.0, "hhi": 600, "substitutability": 0.30,
        "recycling_input_rate": 0.20,
        "note": "The one material here where the biotic and soil columns carry "
                "the weight. Summing them into the abiotic figure would make "
                "timber look worse than steel, which would be nonsense.",
    },
    "cotton": {
        "label": "Cotton fibre",
        "family": "biotic",
        "abiotic": 1.5, "biotic": 3.2, "soil": 15.0,
        "water": 10000.0, "air": 0.6,
        "ore_grade": None, "reference_grade": None,
        "adp": 0.0, "hhi": 900, "substitutability": 0.25,
        "recycling_input_rate": 0.01,
        "note": "Fifteen kilograms of soil moved per kilogram of fibre, and "
                "ten tonnes of src.environment.water. Neither number appears anywhere in a "
                "carbon footprint.",
    },
}


# ---------------------------------------------------------------------------
# Products
#
# Bills of materials in kilograms. Assembled rather than looked up so the
# footprint is derived from something inspectable, and so a user can see which
# few grams are doing the work.
# ---------------------------------------------------------------------------
PRODUCTS = {
    "smartphone": {
        "label": "Smartphone",
        "typical_life_years": 3.0,
        "bom": {
            "gold": 0.000025, "palladium": 0.000010, "silver": 0.00025,
            "copper": 0.012, "aluminium": 0.030, "steel": 0.022,
            "cobalt": 0.006, "lithium": 0.0015, "neodymium": 0.0003,
            "tantalum": 0.00004, "indium": 0.000006, "tin": 0.001,
            "plastic_generic": 0.048, "glass": 0.030,
        },
        "note": "Around thirty grams of metal doing almost all of the damage, "
                "and a few hundredths of a gram of gold and palladium doing "
                "most of that.",
    },
    "laptop": {
        "label": "Laptop",
        "typical_life_years": 5.0,
        "bom": {
            "gold": 0.00008, "palladium": 0.000025, "silver": 0.0008,
            "copper": 0.180, "aluminium": 0.450, "steel": 0.250,
            "cobalt": 0.030, "lithium": 0.008, "neodymium": 0.0015,
            "tantalum": 0.0002, "indium": 0.00002, "tin": 0.006,
            "plastic_generic": 0.400, "glass": 0.150,
        },
        "note": "More of everything than a phone, and a longer life, so the "
                "footprint per year of service is lower despite the larger "
                "total.",
    },
    "ev_battery_60kwh": {
        "label": "EV battery pack (60 kWh)",
        "typical_life_years": 12.0,
        "bom": {
            "lithium": 7.5, "cobalt": 12.0, "nickel": 40.0,
            "copper": 45.0, "aluminium": 90.0, "steel": 60.0,
            "plastic_generic": 25.0,
        },
        "note": "The clearest carbon-versus-materials trade in the table. It "
                "removes tailpipe emissions and it moves a great deal of rock, "
                "and both are true at once.",
    },
    "solar_panel_400w": {
        "label": "Solar panel (400 W)",
        "typical_life_years": 25.0,
        "bom": {
            "silicon_solar": 2.2, "silver": 0.012, "copper": 0.55,
            "aluminium": 2.8, "glass": 13.0, "plastic_generic": 1.6,
            "tin": 0.05,
        },
        "note": "Material-cheap and energy-expensive, and the silver is the "
                "constraint nobody discusses. Twelve grams a panel adds up "
                "quickly at terawatt scale.",
    },
    "washing_machine": {
        "label": "Washing machine",
        "typical_life_years": 11.0,
        "bom": {
            "steel": 42.0, "copper": 3.2, "aluminium": 2.4,
            "plastic_generic": 14.0, "concrete": 20.0, "glass": 1.5,
            "neodymium": 0.05,
        },
        "note": "Mostly steel and a counterweight, so the rucksack ratio is "
                "low. Life extension still wins because the absolute mass is "
                "large.",
    },
    "car_ice": {
        "label": "Car (internal combustion)",
        "typical_life_years": 14.0,
        "bom": {
            "steel": 900.0, "aluminium": 150.0, "copper": 25.0,
            "plastic_generic": 200.0, "glass": 45.0, "platinum": 0.005,
            "palladium": 0.004, "tin": 0.5,
        },
        "note": "The catalytic converter's few grams of platinum group metal "
                "carry a rucksack comparable to the rest of the car.",
    },
    "cotton_tshirt": {
        "label": "Cotton t-shirt",
        "typical_life_years": 3.0,
        "bom": {"cotton": 0.200},
        "note": "Included as a contrast: almost no abiotic flow, a great deal "
                "of soil and src.environment.water. A single-category metric would rank it "
                "either far too well or far too badly.",
    },
}


# ---------------------------------------------------------------------------
# Context
#
# A per-capita level often quoted for a resource-safe operating space. The basis
# is contested - it comes from downscaling a global material extraction target
# by population - and it is labelled as contested wherever it appears.
# ---------------------------------------------------------------------------
SUSTAINABLE_ABIOTIC_PER_CAPITA_TONNES = 8.0

# Where the criticality thresholds sit. Stated so a reader can disagree with
# them rather than having to reverse-engineer a colour on a chart.
HHI_CONCENTRATED = 2500
HHI_HIGHLY_CONCENTRATED = 5000
LOW_RECYCLING_INPUT = 0.10


def list_materials(family: str | None = None) -> list:
    """Material keys, optionally filtered by family."""
    keys = sorted(MATERIALS)
    if family is None:
        return keys
    return [k for k in keys if MATERIALS[k]["family"] == family]


def list_families() -> list:
    """Distinct material families."""
    return sorted({v["family"] for v in MATERIALS.values()})


def get_material(key: str) -> dict:
    """One material's data, refusing an unknown key.

    Rucksack ratios in this table span six orders of magnitude, from concrete at
    1.3 to palladium at a million. There is no average worth offering.
    """
    try:
        return dict(MATERIALS[key])
    except KeyError:
        raise MaterialError(
            f"No data for material '{key}'. Rucksack ratios here span six "
            f"orders of magnitude, so an average would be meaningless. Known "
            f"materials: {', '.join(list_materials())}"
        ) from None


def list_products() -> list:
    """Product keys, in a stable order."""
    return sorted(PRODUCTS)


def get_product(key: str) -> dict:
    """One product's bill of materials."""
    try:
        entry = dict(PRODUCTS[key])
        entry["bom"] = dict(entry["bom"])
        return entry
    except KeyError:
        raise MaterialError(
            f"No bill of materials for '{key}'. Known products: "
            f"{', '.join(list_products())}"
        ) from None


def rucksack(material: str, kg: float, ore_grade: float | None = None) -> dict:
    """Material moved to deliver a mass of one material, by category.

    ``ore_grade`` overrides the reference grade. The rucksack of a metal is
    essentially inversely proportional to grade, so halving the grade doubles
    the rock moved - which is geology rather than inefficiency, and worth
    separating from the parts of a footprint that can be engineered away.
    """
    spec = get_material(material)
    if kg < 0:
        raise MaterialError("Mass cannot be negative.")

    scale = 1.0
    reference = spec.get("reference_grade")
    if ore_grade is not None:
        if reference is None:
            raise MaterialError(
                f"'{material}' is not extracted from an ore, so it has no "
                f"grade to vary. Grade sensitivity applies to mined metals."
            )
        if not 0.0 < ore_grade <= 1.0:
            raise MaterialError("Ore grade must lie between 0 and 1.")
        scale = reference / ore_grade

    flows = {
        category: spec[category] * kg * (scale if category == "abiotic" else 1.0)
        for category in CATEGORIES
    }

    return {
        "material": material,
        "label": spec["label"],
        "family": spec["family"],
        "kg": kg,
        "flows": flows,
        "abiotic_kg": flows["abiotic"],
        "ore_grade": ore_grade if ore_grade is not None else reference,
        "reference_grade": reference,
        "grade_scale": scale,
        "ratio": flows["abiotic"] / kg if kg > 0 else 0.0,
        "note": spec["note"],
    }


def grade_sensitivity(material: str, grades: list | None = None) -> list:
    """The same kilogram of metal at a range of ore grades.

    Answers how much of a metal's footprint is geology. For copper the answer is
    almost all of it, and no amount of process improvement changes that.
    """
    spec = get_material(material)
    reference = spec.get("reference_grade")
    if reference is None:
        raise MaterialError(
            f"'{material}' is not mined from an ore, so grade sensitivity does "
            f"not apply."
        )

    grades = grades or [
        reference * multiplier for multiplier in (2.0, 1.5, 1.0, 0.7, 0.5, 0.35)
    ]
    rows = []
    for grade in sorted(grades, reverse=True):
        result = rucksack(material, 1.0, ore_grade=grade)
        rows.append({
            "ore_grade": grade,
            "grade_percent": grade * 100.0,
            "abiotic_kg_per_kg": result["abiotic_kg"],
            "relative_to_reference": result["grade_scale"],
            "is_reference": abs(grade - reference) < reference * 1e-9,
        })
    return rows


def product_footprint(
    product: str, quantity: float = 1.0, grades: dict | None = None
) -> dict:
    """Material footprint of a product, built from its bill of materials.

    The direct-to-hidden ratio is the communicative number: what you hold
    against what was moved to make it. For a smartphone it runs to roughly
    a hundred and eighty to one.
    """
    spec = get_product(product)
    if quantity <= 0:
        raise MaterialError("Quantity must be positive.")

    grades = grades or {}
    rows = []
    flows = {category: 0.0 for category in CATEGORIES}
    direct_mass = 0.0

    for material, kg in spec["bom"].items():
        mass = kg * quantity
        result = rucksack(material, mass, ore_grade=grades.get(material))
        rows.append(result)
        direct_mass += mass
        for category in CATEGORIES:
            flows[category] += result["flows"][category]

    rows.sort(key=lambda row: -row["abiotic_kg"])
    hidden = flows["abiotic"] - direct_mass

    return {
        "product": product,
        "label": spec["label"],
        "quantity": quantity,
        "materials": rows,
        "flows": flows,
        "direct_mass_kg": direct_mass,
        "abiotic_kg": flows["abiotic"],
        "hidden_flow_kg": max(0.0, hidden),
        "ratio": flows["abiotic"] / direct_mass if direct_mass > 0 else 0.0,
        "typical_life_years": spec["typical_life_years"],
        "abiotic_per_year": (
            flows["abiotic"] / spec["typical_life_years"]
            if spec["typical_life_years"] > 0 else 0.0
        ),
        "note": spec["note"],
        "categories_not_summed": (
            "Abiotic, biotic, soil, water and air are reported separately. "
            "Adding moved topsoil to extracted ore would produce a large "
            "number with no meaning."
        ),
    }


def concentration(product_result: dict, top_n: int = 3) -> dict:
    """How much of a product's footprint sits in how little of its mass.

    This is the finding that changes how people think about small electronics:
    a few hundredths of a gram carrying most of the material moved.
    """
    rows = product_result["materials"]
    if not rows:
        raise MaterialError("Nothing to analyse.")

    top = rows[:top_n]
    top_abiotic = sum(row["abiotic_kg"] for row in top)
    top_mass = sum(row["kg"] for row in top)
    total_abiotic = product_result["abiotic_kg"]
    total_mass = product_result["direct_mass_kg"]

    return {
        "top": [
            {
                "material": row["material"],
                "label": row["label"],
                "kg": row["kg"],
                "abiotic_kg": row["abiotic_kg"],
                "share_of_abiotic": (
                    row["abiotic_kg"] / total_abiotic if total_abiotic else 0.0
                ),
                "share_of_mass": row["kg"] / total_mass if total_mass else 0.0,
            }
            for row in top
        ],
        "top_share_of_abiotic": (
            top_abiotic / total_abiotic if total_abiotic else 0.0
        ),
        "top_share_of_mass": top_mass / total_mass if total_mass else 0.0,
    }


def abiotic_depletion(material: str, kg: float) -> dict:
    """Depletion potential in antimony equivalents, with the basis stated.

    Separate from criticality, which is a different question with a different
    answer for several of these materials.
    """
    spec = get_material(material)
    if kg < 0:
        raise MaterialError("Mass cannot be negative.")

    return {
        "material": material,
        "label": spec["label"],
        "kg": kg,
        "adp_sb_eq": spec["adp"] * kg,
        "adp_per_kg": spec["adp"],
        "basis": (
            "CML abiotic depletion potential, antimony equivalent, computed "
            "against an economically recoverable reserve base. Reserves move "
            "with price and exploration, so this is a comparison between "
            "materials rather than a countdown."
        ),
    }


def criticality(material: str) -> dict:
    """Supply concentration, substitutability and secondary supply.

    Deliberately three numbers rather than one. A material can be abundant and
    critical at once - cobalt is the clearest case - and a combined score would
    make both dimensions unreadable.
    """
    spec = get_material(material)
    hhi = spec["hhi"]

    if hhi >= HHI_HIGHLY_CONCENTRATED:
        concentration_verdict = (
            "Highly concentrated. A single country's policy can move global "
            "supply."
        )
    elif hhi >= HHI_CONCENTRATED:
        concentration_verdict = (
            "Concentrated. Fewer suppliers than a resilient market would want."
        )
    else:
        concentration_verdict = "Diversified supply."

    return {
        "material": material,
        "label": spec["label"],
        "hhi": hhi,
        "concentration_verdict": concentration_verdict,
        "substitutability": spec["substitutability"],
        "recycling_input_rate": spec["recycling_input_rate"],
        "secondary_supply_constrained": (
            spec["recycling_input_rate"] < LOW_RECYCLING_INPUT
        ),
        "adp_per_kg": spec["adp"],
        "abundant_but_critical": (
            spec["adp"] < 1e-3 and hhi >= HHI_HIGHLY_CONCENTRATED
        ),
        "dimensions_kept_separate": (
            "Depletion asks how much of a finite stock a use consumes. "
            "Criticality asks whether the supply can be interrupted. They are "
            "different questions with different answers, and a combined "
            "'resource score' would obscure both."
        ),
    }


def circularity_saving(
    product: str,
    life_before_years: float,
    life_after_years: float,
    horizon_years: float = 20.0,
    secondary_share: float = 0.0,
) -> dict:
    """Material footprint avoided by making a product last longer.

    ``secondary_share`` is how much of the replacement's material comes from
    end-of-life recycling. It is capped at what the recycling input rates in the
    material table can actually deliver, and it is applied to both scenarios so
    that life extension is not credited with a recycling saving that has nothing
    to do with it. The two effects are reported separately, so this cannot be
    read as saying recycling solves the problem.
    """
    if life_before_years <= 0 or life_after_years <= 0:
        raise MaterialError("Service lives must be positive.")
    if horizon_years <= 0:
        raise MaterialError("Horizon must be positive.")
    if not 0.0 <= secondary_share <= 1.0:
        raise MaterialError("Secondary share must lie between 0 and 1.")
    if life_after_years < life_before_years:
        raise MaterialError(
            "This models life extension. A shorter life is not an "
            "improvement and the function will not pretend otherwise."
        )

    base = product_footprint(product)
    units_before = horizon_years / life_before_years
    units_after = horizon_years / life_after_years

    achievable = _achievable_secondary_share(base)
    applied_share = min(secondary_share, achievable)

    # The secondary share applies to both scenarios. Applying it only to the
    # longer-life case would credit life extension with a recycling saving that
    # has nothing to do with it, and the two effects are worth telling apart.
    primary_before = base["abiotic_kg"] * units_before * (1.0 - applied_share)
    primary_after = base["abiotic_kg"] * units_after * (1.0 - applied_share)
    secondary_avoided = base["abiotic_kg"] * units_after * applied_share

    return {
        "product": product,
        "label": base["label"],
        "horizon_years": horizon_years,
        "life_before_years": life_before_years,
        "life_after_years": life_after_years,
        "units_before": units_before,
        "units_after": units_after,
        "abiotic_before_kg": primary_before,
        "abiotic_after_kg": primary_after,
        "avoided_kg": primary_before - primary_after,
        "avoided_share": (
            (primary_before - primary_after) / primary_before
            if primary_before > 0 else 0.0
        ),
        "secondary_avoided_kg": secondary_avoided,
        "secondary_share_requested": secondary_share,
        "secondary_share_applied": applied_share,
        "secondary_capped": applied_share < secondary_share,
        "achievable_secondary_share": achievable,
        "recycling_caveat": (
            "Secondary supply is capped at what the end-of-life recycling "
            "input rates in this product's own bill of materials can deliver. "
            "For anything containing rare earths, tantalum or indium, that is "
            "close to nothing, so recycling cannot substitute for using the "
            "thing longer."
        ),
    }


def _achievable_secondary_share(product_result: dict) -> float:
    """Mass-weighted recycling input rate across a product's materials.

    A ceiling on what secondary supply can realistically contribute. Weighted by
    abiotic flow rather than by mass, because the materials carrying the
    footprint are precisely the ones with no recovery route.
    """
    total = product_result["abiotic_kg"]
    if total <= 0:
        return 0.0
    return sum(
        row["abiotic_kg"] * MATERIALS[row["material"]]["recycling_input_rate"]
        for row in product_result["materials"]
    ) / total


def per_capita_context(abiotic_kg: float) -> dict:
    """Compare against a per-capita resource-safe level, basis stated."""
    if abiotic_kg < 0:
        raise MaterialError("Material footprint cannot be negative.")

    budget_kg = SUSTAINABLE_ABIOTIC_PER_CAPITA_TONNES * 1000.0
    return {
        "abiotic_kg": abiotic_kg,
        "budget_kg": budget_kg,
        "share": abiotic_kg / budget_kg,
        "basis": (
            "Eight tonnes per person per year is a figure commonly used for a "
            "resource-safe level of abiotic material consumption. It comes "
            "from downscaling a global extraction target by population, both "
            "halves of which are contested, and it is offered as a scale "
            "rather than as a limit anyone has agreed."
        ),
    }


def compare_products(products: list | None = None) -> list:
    """Products ranked by abiotic footprint per year of service.

    Per year rather than per unit, because a laptop that lasts five years and a
    phone that lasts three are not comparable on a per-unit basis.
    """
    products = products or list_products()
    rows = []
    for key in products:
        result = product_footprint(key)
        rows.append({
            "product": key,
            "label": result["label"],
            "abiotic_kg": result["abiotic_kg"],
            "abiotic_per_year": result["abiotic_per_year"],
            "direct_mass_kg": result["direct_mass_kg"],
            "ratio": result["ratio"],
            "life_years": result["typical_life_years"],
        })
    rows.sort(key=lambda row: -row["abiotic_per_year"])
    return rows


def get_material_insights(result: dict) -> list:
    """Plain-language findings, emitted only where the result supports them."""
    insights = []

    ratio = result["ratio"]
    if ratio > 1:
        insights.append(
            f"{ratio:,.0f} kilograms of material moved per kilogram you hold. "
            f"That ratio, rather than the tonnage, is the number worth "
            f"remembering."
        )

    focus = concentration(result, top_n=3)
    if focus["top_share_of_abiotic"] > 0.6:
        mass_share = focus["top_share_of_mass"] * 100.0
        insights.append(
            f"{focus['top_share_of_abiotic'] * 100:.0f}% of the material moved "
            f"is attributable to three materials making up {mass_share:.1f}% of "
            f"the product's own mass."
        )

    flows = result["flows"]
    if flows["water"] > flows["abiotic"] * 3:
        insights.append(
            f"The water flow ({flows['water']:,.0f} kg) is several times the "
            f"abiotic flow. Summing the categories would have buried that; "
            f"they are kept apart for exactly this reason."
        )
    if flows["soil"] > flows["abiotic"]:
        insights.append(
            f"More soil is moved ({flows['soil']:,.0f} kg) than rock. This is a "
            f"biotic product and reading its abiotic column alone would say "
            f"almost nothing about it."
        )

    critical = [
        row["material"] for row in result["materials"]
        if criticality(row["material"])["abundant_but_critical"]
    ]
    if critical:
        labels = ", ".join(
            MATERIALS[material]["label"] for material in critical[:3]
        )
        insights.append(
            f"{labels} score low on depletion and high on supply "
            f"concentration. Abundant and critical at once, which is why the "
            f"two are never combined into one score here."
        )

    low_recovery = [
        row for row in result["materials"][:5]
        if MATERIALS[row["material"]]["recycling_input_rate"] < LOW_RECYCLING_INPUT
        and row["abiotic_kg"] > 0
    ]
    if low_recovery:
        labels = ", ".join(row["label"] for row in low_recovery[:3])
        verb = "has" if len(low_recovery) == 1 else "have"
        subject = "it is" if len(low_recovery) == 1 else "they are"
        insights.append(
            f"{labels} {verb} essentially no end-of-life recovery route, and "
            f"{subject} among the largest contributors here. Recycling cannot "
            f"substitute for using the thing longer."
        )

    context = per_capita_context(result["abiotic_per_year"])
    if context["share"] > 0.05:
        insights.append(
            f"Spread over its service life this is "
            f"{context['share'] * 100:.0f}% of a per-capita resource-safe "
            f"level for a year - from one object."
        )

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS material_footprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            abiotic_kg REAL NOT NULL,
            direct_mass_kg REAL NOT NULL,
            ratio REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_material_footprints_user
        ON material_footprints (user_id)
        """
    )


def save_footprint(user_id: str, name: str, result: dict) -> int:
    """Persist a product footprint and return its row id."""
    if not user_id:
        raise MaterialError("A footprint needs a user to belong to.")
    if not name or not name.strip():
        raise MaterialError("A footprint needs a name.")

    payload = json.dumps({
        "product": result["product"],
        "quantity": result["quantity"],
        "flows": result["flows"],
        "typical_life_years": result["typical_life_years"],
        "abiotic_per_year": result["abiotic_per_year"],
        "materials": [
            {
                "material": row["material"],
                "kg": row["kg"],
                "abiotic_kg": row["abiotic_kg"],
                "ore_grade": row["ore_grade"],
            }
            for row in result["materials"]
        ],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO material_footprints
                (user_id, name, payload, abiotic_kg, direct_mass_kg, ratio)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(result["abiotic_kg"]),
                float(result["direct_mass_kg"]),
                float(result["ratio"]),
            ),
        )
        return int(cursor.lastrowid)


def get_footprints(user_id: str) -> list:
    """Saved footprints for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, abiotic_kg, direct_mass_kg, ratio,
                       created_at
                FROM material_footprints
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved material footprints")
        return []

    footprints = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        footprints.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "abiotic_kg": row[3],
            "direct_mass_kg": row[4],
            "ratio": row[5],
            "created_at": row[6],
        })
    return footprints


def delete_footprint(user_id: str, footprint_id: int) -> bool:
    """Delete one saved footprint. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM material_footprints WHERE id = ? AND user_id = ?",
                (footprint_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete material footprint %s", footprint_id)
        return False
