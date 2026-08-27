"""What a household's consumption displaces, in species rather than in carbon.

``src.environment.local_biodiversity.py`` is a catalogue: it tells a user which birds and
pollinators live near them. Nothing a user does anywhere else in this app
changes a number in it. Meanwhile the driver that actually decides biodiversity
outcomes - land use, and specifically the land converted and occupied to produce
what a household consumes - is unmeasured.

``src.environment.land_opportunity_cost.py`` does measure land, but through its carbon
opportunity cost. That is a real improvement over ignoring land entirely, and it
implicitly says that land matters only as a carbon store. A hectare of
species-rich grassland and a hectare of fast-growing plantation can score
similarly on carbon and could not be further apart on species.

Occupation and transformation are different impacts
----------------------------------------------------
**Occupation** is holding land in production, so it cannot recover. Measured in
m2.yr, and the damage accrues for as long as the occupation lasts.
**Transformation** is converting it in the first place. Measured in m2, one-off,
and its damage is the recovery period the ecosystem now has to serve before it
is what it was - if it ever is.

They are kept apart everywhere in this module. Summing them produces a number
that cannot be interpreted, because one is a rate and the other is a stock.

Where the hectare is matters more than how many
------------------------------------------------
A hectare of oil palm in Borneo and a hectare of barley in Denmark are not
comparable. Regional species richness and endemism differ by more than an order
of magnitude, and a species lost from an ecoregion where it occurs nowhere else
is lost outright. A global-average biodiversity factor would be close to
meaningless, so the factors here are regional and the sourcing assumption is
labelled as an assumption wherever it is a default.

One index would hide the disagreement
--------------------------------------
Plants, mammals, birds, amphibians and reptiles do not agree about which land
use is worst. Amphibians collapse under drainage that barely registers for
birds; birds tolerate mosaic agriculture that plants do not. Aggregating first
hides that, so the taxa are reported separately as well as together.

Intensity, because "agriculture" is not one thing
--------------------------------------------------
Intensive arable, extensive pasture, agroforestry, plantation forestry and
managed forest leave very different residual species abundance on the same
hectare. A module without intensity classes would say all farming is equally
bad, which is false and, being false, is also demotivating.

Legibility without false precision
-----------------------------------
PDF.m2.yr is not a unit anyone reads. It is anchored here to an area of habitat
rendered unavailable, which is legible, and the scientific unit is always shown
alongside so the anchor never becomes the only number on screen.

What this does not cover
-------------------------
Land use is the largest driver of terrestrial biodiversity loss. It is not the
only one. Overexploitation, invasive species, pollution and climate change are
all outside this module, and a partial footprint that does not say so reads as a
complete one.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class BiodiversityError(ValueError):
    """Raised when a biodiversity calculation was asked for something meaningless."""


# ---------------------------------------------------------------------------
# Taxa
#
# Reported separately because they disagree, and the disagreement is the
# information. An aggregate that hides it is worse than no aggregate.
# ---------------------------------------------------------------------------
TAXA = ("plants", "mammals", "birds", "amphibians", "reptiles")


# ---------------------------------------------------------------------------
# Land use intensity classes
#
# ``pdf`` is the potentially disappeared fraction of the original species pool
# under this land use - the share of species that were there and are not. Per
# taxon, because they respond differently to the same conversion.
#
# These are local relative losses on a 0-1 scale, not global extinction
# probabilities. A local loss of 0.75 does not mean three quarters of the
# world's species are gone; it means three quarters of what was on that ground
# no longer is.
# ---------------------------------------------------------------------------
LAND_USE_CLASSES = {
    "intensive_arable": {
        "label": "Intensive arable",
        "pdf": {
            "plants": 0.82, "mammals": 0.68, "birds": 0.60,
            "amphibians": 0.78, "reptiles": 0.70,
        },
        "note": "Monoculture with tillage, herbicide and no field margin. "
                "Plants go first because the whole point of the system is that "
                "only one of them grows.",
    },
    "extensive_arable": {
        "label": "Extensive or low-input arable",
        "pdf": {
            "plants": 0.62, "mammals": 0.44, "birds": 0.34,
            "amphibians": 0.55, "reptiles": 0.48,
        },
        "note": "Rotation, margins, lower inputs. Birds recover fastest "
                "because the mosaic gives them something to use.",
    },
    "intensive_pasture": {
        "label": "Intensive pasture",
        "pdf": {
            "plants": 0.70, "mammals": 0.42, "birds": 0.40,
            "amphibians": 0.60, "reptiles": 0.52,
        },
        "note": "Reseeded, fertilised, heavily stocked. Structurally simple in "
                "a way that a species-rich sward is not.",
    },
    "extensive_pasture": {
        "label": "Extensive or rough grazing",
        "pdf": {
            "plants": 0.30, "mammals": 0.22, "birds": 0.18,
            "amphibians": 0.28, "reptiles": 0.24,
        },
        "note": "Low stocking on semi-natural grassland. Some such systems "
                "hold more species than the woodland that would replace them, "
                "which is why a blanket rewilding assumption is not safe.",
    },
    "agroforestry": {
        "label": "Agroforestry and shade-grown crops",
        "pdf": {
            "plants": 0.34, "mammals": 0.26, "birds": 0.16,
            "amphibians": 0.32, "reptiles": 0.28,
        },
        "note": "Structural complexity retained. The single largest available "
                "improvement for tropical commodity crops, and the reason "
                "shade-grown coffee and cocoa are not a marketing distinction.",
    },
    "plantation_forestry": {
        "label": "Plantation forestry",
        "pdf": {
            "plants": 0.58, "mammals": 0.44, "birds": 0.38,
            "amphibians": 0.52, "reptiles": 0.50,
        },
        "note": "Even-aged monoculture. Scores well on carbon and poorly on "
                "species, which is precisely the divergence this module exists "
                "to make visible.",
    },
    "managed_forest": {
        "label": "Selectively managed natural forest",
        "pdf": {
            "plants": 0.16, "mammals": 0.14, "birds": 0.10,
            "amphibians": 0.20, "reptiles": 0.18,
        },
        "note": "Continuous cover, native composition, extraction below "
                "increment. Close to the least damaging productive use of "
                "forested land.",
    },
    "urban": {
        "label": "Urban and built",
        "pdf": {
            "plants": 0.88, "mammals": 0.72, "birds": 0.54,
            "amphibians": 0.90, "reptiles": 0.84,
        },
        "note": "Sealed surface is the most complete local loss in the table. "
                "Birds do better than everything else because some of them are "
                "genuinely urban.",
    },
    "oil_palm": {
        "label": "Oil palm plantation",
        "pdf": {
            "plants": 0.80, "mammals": 0.78, "birds": 0.66,
            "amphibians": 0.86, "reptiles": 0.82,
        },
        "note": "Separated from plantation forestry because it almost always "
                "replaces lowland tropical forest, which is the most "
                "species-rich terrestrial habitat there is.",
    },
}


# ---------------------------------------------------------------------------
# Regions
#
# ``vulnerability`` scales the local loss by how much a species lost there
# matters globally: richness times endemism. A species lost from an ecoregion
# where it occurs nowhere else is lost outright, and that is what separates
# Borneo from Denmark by more than an order of magnitude.
#
# ``recovery_years`` is how long the habitat needs to be what it was, and it is
# what turns a one-off transformation into a quantity of damage.
# ---------------------------------------------------------------------------
REGIONS = {
    "tropical_forest_seasia": {
        "label": "Tropical forest, Southeast Asia",
        "vulnerability": 12.0, "recovery_years": 85,
        "note": "The highest endemism in the table. Much of what is lost from "
                "a Bornean lowland forest occurs nowhere else on Earth.",
    },
    "tropical_forest_samerica": {
        "label": "Tropical forest, South America",
        "vulnerability": 10.5, "recovery_years": 85,
        "note": "Amazon and Cerrado. Soy and pasture expansion is the "
                "conversion front that matters for a European or North "
                "American diet.",
    },
    "tropical_forest_africa": {
        "label": "Tropical forest, Central and West Africa",
        "vulnerability": 8.5, "recovery_years": 80,
        "note": "Cocoa is the commodity most directly attached to this front.",
    },
    "tropical_savanna": {
        "label": "Tropical savanna and dry woodland",
        "vulnerability": 4.2, "recovery_years": 35,
        "note": "Less rich than rainforest and converted faster, so the total "
                "loss is not proportionally smaller.",
    },
    "temperate_forest": {
        "label": "Temperate broadleaf and mixed forest",
        "vulnerability": 2.4, "recovery_years": 55,
        "note": "Most of Europe and eastern North America was this, and was "
                "converted centuries ago. The baseline problem: what is being "
                "compared against is already a fragment.",
    },
    "temperate_grassland": {
        "label": "Temperate grassland",
        "vulnerability": 2.0, "recovery_years": 22,
        "note": "Among the most completely converted biomes on Earth and among "
                "the least discussed, because the conversion finished before "
                "anyone was counting.",
    },
    "mediterranean": {
        "label": "Mediterranean scrub and woodland",
        "vulnerability": 5.4, "recovery_years": 45,
        "note": "Disproportionately rich and endemic for its area. Olive, "
                "almond and vine expansion is the relevant pressure.",
    },
    "boreal_forest": {
        "label": "Boreal forest",
        "vulnerability": 1.4, "recovery_years": 110,
        "note": "Species-poor and very slow to recover, so a low vulnerability "
                "and a long recovery period pull in opposite directions.",
    },
    "arid": {
        "label": "Desert and arid shrubland",
        "vulnerability": 1.8, "recovery_years": 60,
        "note": "Low productivity, high endemism among reptiles, and very slow "
                "recovery once soil crusts are broken.",
    },
    "wetland": {
        "label": "Wetland and floodplain",
        "vulnerability": 7.5, "recovery_years": 65,
        "note": "Amphibian richness concentrates here, which is why drainage "
                "shows up in the amphibian column far more than in the bird "
                "column.",
    },
}


# ---------------------------------------------------------------------------
# Products
#
# ``occupation`` is m2.yr of land per kilogram of product. ``transformation`` is
# the m2 per kilogram attributable to recent conversion on the conventional
# twenty-year attribution window - zero for commodities grown on land converted
# long ago, and the dominant term for those grown on a live deforestation front.
#
# ``default_region`` and ``default_use`` are defaults. They are the single
# largest source of variance in the answer, which is why the module reports
# them as assumptions rather than folding them silently into a number.
# ---------------------------------------------------------------------------
PRODUCTS = {
    "beef_pasture": {
        "label": "Beef, pasture raised",
        "category": "food",
        "occupation": 164.0, "transformation": 0.0,
        "default_region": "temperate_grassland", "default_use": "extensive_pasture",
        "note": "By far the most land-hungry food per kilogram. On extensive "
                "semi-natural grassland the per-hectare damage is low, which "
                "is why the total and the intensity pull in opposite "
                "directions and both need showing.",
    },
    "beef_deforestation": {
        "label": "Beef, recently converted pasture",
        "category": "food",
        "occupation": 185.0, "transformation": 4.60,
        "default_region": "tropical_forest_samerica",
        "default_use": "intensive_pasture",
        "note": "The same food as the row above with a transformation term "
                "attached. The difference between these two rows is larger "
                "than the difference between beef and anything else.",
    },
    "lamb": {
        "label": "Lamb and mutton",
        "category": "food",
        "occupation": 185.0, "transformation": 0.0,
        "default_region": "temperate_grassland", "default_use": "extensive_pasture",
        "note": "Comparable land demand to beef, usually on land that would "
                "support little else.",
    },
    "chicken": {
        "label": "Chicken",
        "category": "food",
        "occupation": 12.2, "transformation": 0.030,
        "default_region": "tropical_forest_samerica",
        "default_use": "intensive_arable",
        "note": "Land-efficient per kilogram, and the land is soy on an active "
                "conversion front, so the transformation term is not zero.",
    },
    "pork": {
        "label": "Pork",
        "category": "food",
        "occupation": 17.4, "transformation": 0.045,
        "default_region": "tropical_forest_samerica",
        "default_use": "intensive_arable",
        "note": "Same feed chain as chicken with a worse conversion ratio.",
    },
    "cheese": {
        "label": "Cheese",
        "category": "food",
        "occupation": 87.8, "transformation": 0.060,
        "default_region": "temperate_grassland", "default_use": "intensive_pasture",
        "note": "Roughly ten litres of milk per kilogram, and the land follows.",
    },
    "milk": {
        "label": "Milk",
        "category": "food",
        "occupation": 8.9, "transformation": 0.006,
        "default_region": "temperate_grassland", "default_use": "intensive_pasture",
        "note": "Mostly water, so low per kilogram.",
    },
    "eggs": {
        "label": "Eggs",
        "category": "food",
        "occupation": 6.3, "transformation": 0.018,
        "default_region": "tropical_forest_samerica",
        "default_use": "intensive_arable",
        "note": "Layer feed is cereal and soy.",
    },
    "soy_direct": {
        "label": "Soy for direct human consumption",
        "category": "food",
        "occupation": 2.2, "transformation": 0.015,
        "default_region": "tropical_forest_samerica",
        "default_use": "intensive_arable",
        "note": "The point almost always missed: the great majority of soy is "
                "animal feed, and soy eaten directly carries a fraction of the "
                "land of soy eaten through a pig.",
    },
    "wheat": {
        "label": "Wheat",
        "category": "food",
        "occupation": 3.9, "transformation": 0.0,
        "default_region": "temperate_grassland", "default_use": "intensive_arable",
        "note": "Grown almost entirely on land converted long ago, so there is "
                "no live transformation term.",
    },
    "rice": {
        "label": "Rice",
        "category": "food",
        "occupation": 2.8, "transformation": 0.004,
        "default_region": "wetland", "default_use": "intensive_arable",
        "note": "Paddy replaces wetland, which is where amphibian richness "
                "concentrates. The taxon breakdown is the point for rice.",
    },
    "palm_oil": {
        "label": "Palm oil",
        "category": "food",
        "occupation": 2.0, "transformation": 0.095,
        "default_region": "tropical_forest_seasia", "default_use": "oil_palm",
        "note": "The most land-efficient vegetable oil by a wide margin, grown "
                "in the most species-rich place available. Substituting it for "
                "a less efficient oil grown somewhere ordinary is not "
                "automatically an improvement, and this module can show which "
                "way that trade actually falls.",
    },
    "cocoa": {
        "label": "Cocoa",
        "category": "food",
        "occupation": 68.0, "transformation": 0.620,
        "default_region": "tropical_forest_africa", "default_use": "intensive_arable",
        "note": "Very land-hungry per kilogram and grown on a live conversion "
                "front. Shade-grown cocoa moves it to agroforestry, which is "
                "the largest single improvement available for this crop.",
    },
    "coffee": {
        "label": "Coffee",
        "category": "food",
        "occupation": 21.0, "transformation": 0.130,
        "default_region": "tropical_forest_samerica", "default_use": "intensive_arable",
        "note": "Sun-grown coffee is a monoculture; shade-grown is "
                "agroforestry. The difference is roughly a factor of two here.",
    },
    "cotton": {
        "label": "Cotton fibre",
        "category": "textile",
        "occupation": 7.8, "transformation": 0.020,
        "default_region": "arid", "default_use": "intensive_arable",
        "note": "The land figure is modest; the water figure, which is not in "
                "this module, is not.",
    },
    "wool": {
        "label": "Wool fibre",
        "category": "textile",
        "occupation": 305.0, "transformation": 0.0,
        "default_region": "temperate_grassland", "default_use": "extensive_pasture",
        "note": "Enormous per kilogram and allocation-sensitive: how much of a "
                "sheep's land belongs to the wool rather than the meat is a "
                "methodological choice, not a measurement.",
    },
    "softwood_timber": {
        "label": "Softwood timber",
        "category": "material",
        "occupation": 24.0, "transformation": 0.0,
        "default_region": "boreal_forest", "default_use": "plantation_forestry",
        "note": "Scores well on carbon and moderately on species. Switching "
                "the assumed use to managed natural forest roughly halves it.",
    },
    "paper": {
        "label": "Paper and board",
        "category": "material",
        "occupation": 11.0, "transformation": 0.0,
        "default_region": "boreal_forest", "default_use": "plantation_forestry",
        "note": "Recycled content displaces this almost proportionally, which "
                "is one of the few places where recycling does most of what it "
                "is claimed to do.",
    },
}


# ---------------------------------------------------------------------------
# Uncertainty
#
# Biodiversity characterisation factors carry uncertainty roughly an order of
# magnitude wider than carbon factors. Reporting a point estimate on its own
# would imply a precision that does not exist, so every headline number here
# comes with a range and the module has no function that returns a bare number.
# ---------------------------------------------------------------------------
UNCERTAINTY_LOWER = 0.32
UNCERTAINTY_UPPER = 3.10

# A reference for the anchoring: one hectare held entirely clear of its original
# species for one year.
HECTARE_M2 = 10000.0

# A downscaled per-capita share of the land-use component of the biosphere
# integrity boundary, expressed in the same PDF.m2.yr unit. The basis is
# contested and is stated wherever the number is used.
BOUNDARY_PDF_M2_YR_PER_CAPITA = 9500.0

# The attribution window a conversion is charged against. Twenty years is the
# conventional choice and the basis the product table is built on. The choice
# matters: over 20 years a conversion looks five times worse per kilogram than
# over 100, and the ranking of products changes with it.
DEFAULT_AMORTISATION_YEARS = 20
AMORTISATION_OPTIONS = (20, 50, 100)


def list_products(category: str | None = None) -> list:
    """Product keys, optionally filtered by category."""
    keys = sorted(PRODUCTS)
    if category is None:
        return keys
    return [k for k in keys if PRODUCTS[k]["category"] == category]


def list_categories() -> list:
    """Distinct product categories."""
    return sorted({v["category"] for v in PRODUCTS.values()})


def get_product(key: str) -> dict:
    """One product's land data, refusing an unknown key."""
    try:
        return dict(PRODUCTS[key])
    except KeyError:
        raise BiodiversityError(
            f"No land data for '{key}'. Land demand across this table spans "
            f"two orders of magnitude, so an average would be meaningless. "
            f"Known products: {', '.join(list_products())}"
        ) from None


def get_region(key: str) -> dict:
    """One region's vulnerability and recovery period."""
    try:
        return dict(REGIONS[key])
    except KeyError:
        raise BiodiversityError(
            f"Unknown region '{key}'. Where the hectare is matters more than "
            f"how many there are, so this cannot be defaulted silently. Known "
            f"regions: {', '.join(sorted(REGIONS))}"
        ) from None


def get_land_use(key: str) -> dict:
    """One land use class and its per-taxon potentially disappeared fraction."""
    try:
        entry = dict(LAND_USE_CLASSES[key])
        entry["pdf"] = dict(entry["pdf"])
        return entry
    except KeyError:
        raise BiodiversityError(
            f"Unknown land use class '{key}'. 'Agriculture' is not one thing "
            f"and the intensity classes differ by a factor of three. Known "
            f"classes: {', '.join(sorted(LAND_USE_CLASSES))}"
        ) from None


def list_land_uses() -> list:
    """Land use classes, least damaging first, averaged across taxa."""
    return sorted(
        LAND_USE_CLASSES,
        key=lambda k: sum(LAND_USE_CLASSES[k]["pdf"].values()) / len(TAXA),
    )


def list_regions() -> list:
    """Region keys, most vulnerable first."""
    return sorted(REGIONS, key=lambda k: -REGIONS[k]["vulnerability"])


def occupation_impact(
    area_m2_yr: float, region: str, land_use: str
) -> dict:
    """Damage from holding land in production, per taxon and aggregated.

    The unit is PDF.m2.yr - a species-weighted habitat-year. It is the local
    fraction of the species pool absent, times the area, times the time, times
    a regional weight for how much a loss there matters globally.
    """
    if area_m2_yr < 0:
        raise BiodiversityError("Occupied area cannot be negative.")

    region_data = get_region(region)
    use_data = get_land_use(land_use)
    weight = region_data["vulnerability"]

    by_taxon = {
        taxon: use_data["pdf"][taxon] * area_m2_yr * weight
        for taxon in TAXA
    }
    total = sum(by_taxon.values()) / len(TAXA)

    return {
        "kind": "occupation",
        "area_m2_yr": area_m2_yr,
        "region": region,
        "region_label": region_data["label"],
        "land_use": land_use,
        "land_use_label": use_data["label"],
        "vulnerability": weight,
        "by_taxon": by_taxon,
        "pdf_m2_yr": total,
        "range": _range(total),
        "note": use_data["note"],
    }


def transformation_impact(
    area_m2: float,
    region: str,
    land_use: str,
    amortisation_years: int = DEFAULT_AMORTISATION_YEARS,
) -> dict:
    """Damage from converting land, over the recovery period it now owes.

    Two different periods are at work here and conflating them is the usual way
    this calculation goes wrong.

    *   **Recovery** is a property of the ecosystem: how long the habitat needs
        before it is what it was. It multiplies the damage and is not a choice.
    *   **Attribution** is a convention: how many years of production a single
        conversion event is charged against. The product table is built on the
        conventional twenty-year window, so a longer window spreads the same
        conversion over more years of output and reduces the area attributed to
        any one kilogram.

    The window is a parameter because it changes the ranking of products, and
    the result carries whichever one was used.
    """
    if area_m2 < 0:
        raise BiodiversityError("Transformed area cannot be negative.")
    if amortisation_years <= 0:
        raise BiodiversityError("Attribution period must be positive.")

    region_data = get_region(region)
    use_data = get_land_use(land_use)
    weight = region_data["vulnerability"]
    recovery = region_data["recovery_years"]

    # The product table is expressed on the conventional twenty-year attribution
    # window; a different window rescales the area charged to this output.
    attributed_area = area_m2 * DEFAULT_AMORTISATION_YEARS / amortisation_years

    by_taxon = {
        taxon: use_data["pdf"][taxon] * attributed_area * weight * recovery
        for taxon in TAXA
    }
    total = sum(by_taxon.values()) / len(TAXA)

    return {
        "kind": "transformation",
        "area_m2": area_m2,
        "attributed_area_m2": attributed_area,
        "region": region,
        "region_label": region_data["label"],
        "land_use": land_use,
        "land_use_label": use_data["label"],
        "vulnerability": weight,
        "recovery_years": recovery,
        "amortisation_years": amortisation_years,
        "by_taxon": by_taxon,
        "pdf_m2_yr": total,
        "range": _range(total),
        "note": region_data["note"],
    }


def _range(value: float) -> dict:
    """A range around a point estimate, because a point estimate alone lies.

    Biodiversity characterisation factors carry uncertainty roughly an order of
    magnitude wider than carbon factors, and nothing in this module returns a
    bare number without one of these attached.
    """
    return {
        "low": value * UNCERTAINTY_LOWER,
        "central": value,
        "high": value * UNCERTAINTY_UPPER,
        "basis": (
            "Characterisation factors for species loss are uncertain by "
            "roughly an order of magnitude, considerably wider than carbon "
            "factors. The central figure sits at the geometric centre of the "
            "range and is not more trustworthy than its ends."
        ),
    }


def product_footprint(
    key: str,
    kg: float,
    region: str | None = None,
    land_use: str | None = None,
    amortisation_years: int = DEFAULT_AMORTISATION_YEARS,
) -> dict:
    """Biodiversity footprint of a quantity of one product.

    Where ``region`` or ``land_use`` are not supplied the product's defaults are
    used and flagged as defaults, because sourcing is where almost all of the
    variance in the answer lives and pretending otherwise would be the main way
    this module could mislead.
    """
    if kg < 0:
        raise BiodiversityError("Quantity cannot be negative.")

    product = get_product(key)
    used_default_region = region is None
    used_default_use = land_use is None
    region = region or product["default_region"]
    land_use = land_use or product["default_use"]

    occupation = occupation_impact(
        product["occupation"] * kg, region, land_use
    )
    transformation = transformation_impact(
        product["transformation"] * kg, region, land_use, amortisation_years
    )

    by_taxon = {
        taxon: occupation["by_taxon"][taxon] + transformation["by_taxon"][taxon]
        for taxon in TAXA
    }
    total = occupation["pdf_m2_yr"] + transformation["pdf_m2_yr"]

    return {
        "product": key,
        "label": product["label"],
        "category": product["category"],
        "kg": kg,
        "occupation": occupation,
        "transformation": transformation,
        "by_taxon": by_taxon,
        "pdf_m2_yr": total,
        "range": _range(total),
        "transformation_share": (
            transformation["pdf_m2_yr"] / total if total > 0 else 0.0
        ),
        "region": region,
        "land_use": land_use,
        "used_default_region": used_default_region,
        "used_default_land_use": used_default_use,
        "sourcing_warning": (
            "Region and land use are assumed defaults for this product. "
            "Sourcing dominates this answer - the same commodity from a live "
            "conversion front and from long-converted land differ by more than "
            "the difference between commodities."
            if used_default_region or used_default_use else None
        ),
        "note": product["note"],
    }


def basket_footprint(
    items: dict,
    amortisation_years: int = DEFAULT_AMORTISATION_YEARS,
    overrides: dict | None = None,
) -> dict:
    """Footprint of a basket, with per-item sourcing overrides.

    ``overrides`` maps a product key to ``{"region": ..., "land_use": ...}`` for
    the cases where a user actually knows where something came from.
    """
    if not items:
        raise BiodiversityError("An empty basket has no footprint to src.reporting.report.")

    overrides = overrides or {}
    rows = []
    by_taxon = {taxon: 0.0 for taxon in TAXA}
    occupation_total = 0.0
    transformation_total = 0.0

    for key, kg in items.items():
        override = overrides.get(key, {})
        row = product_footprint(
            key,
            kg,
            region=override.get("region"),
            land_use=override.get("land_use"),
            amortisation_years=amortisation_years,
        )
        rows.append(row)
        occupation_total += row["occupation"]["pdf_m2_yr"]
        transformation_total += row["transformation"]["pdf_m2_yr"]
        for taxon in TAXA:
            by_taxon[taxon] += row["by_taxon"][taxon]

    rows.sort(key=lambda row: -row["pdf_m2_yr"])
    total = occupation_total + transformation_total

    return {
        "items": rows,
        "by_taxon": by_taxon,
        "occupation_pdf_m2_yr": occupation_total,
        "transformation_pdf_m2_yr": transformation_total,
        "pdf_m2_yr": total,
        "range": _range(total),
        "amortisation_years": amortisation_years,
        "anchor": anchor(total),
        "boundary": boundary_share(total),
        "taxon_disagreement": taxon_disagreement(by_taxon),
        "scope_limitation": (
            "Land use is the largest driver of terrestrial biodiversity loss "
            "and it is not the only one. Overexploitation, invasive species, "
            "pollution and climate change are outside this module. This is a "
            "partial footprint and reading it as a complete one would overstate "
            "how much of the problem a diet change addresses."
        ),
    }


def anchor(pdf_m2_yr: float) -> dict:
    """Translate the scientific unit into something a person can picture.

    The anchor is an area of habitat rendered unavailable for a year. The
    underlying unit is always returned alongside it, so the anchor never becomes
    the only number on screen.
    """
    if pdf_m2_yr < 0:
        raise BiodiversityError("Impact cannot be negative.")

    hectare_years = pdf_m2_yr / HECTARE_M2
    return {
        "pdf_m2_yr": pdf_m2_yr,
        "hectare_years": hectare_years,
        "football_pitches": hectare_years / 0.71,
        "phrasing": (
            f"Equivalent to holding {hectare_years:.2f} hectares entirely clear "
            f"of their original species for a year, weighted for how much a "
            f"loss in those regions matters."
        ),
        "caveat": (
            "An anchor, not a measurement. No specific hectare is cleared; the "
            "figure is a species-weighted equivalent and the scientific unit is "
            "the one to quote."
        ),
    }


def boundary_share(pdf_m2_yr: float) -> dict:
    """Share of a downscaled per-capita safe operating space."""
    if pdf_m2_yr < 0:
        raise BiodiversityError("Impact cannot be negative.")

    return {
        "pdf_m2_yr": pdf_m2_yr,
        "per_capita_boundary": BOUNDARY_PDF_M2_YR_PER_CAPITA,
        "share": pdf_m2_yr / BOUNDARY_PDF_M2_YR_PER_CAPITA,
        "basis": (
            "The per-capita figure downscales the land-use component of the "
            "biosphere integrity boundary by population. Both the boundary and "
            "the downscaling are contested, and an equal per-capita split is "
            "an ethical choice rather than a scientific result."
        ),
    }


def taxon_disagreement(by_taxon: dict) -> dict:
    """How much the taxa disagree, and which one is worst hit.

    Where the spread is wide, an aggregate index is hiding something and the
    module says so.
    """
    values = [by_taxon[taxon] for taxon in TAXA]
    if not any(values):
        return {"spread": 0.0, "worst": None, "best": None, "verdict": None}

    worst = max(TAXA, key=lambda t: by_taxon[t])
    best = min(TAXA, key=lambda t: by_taxon[t])
    spread = by_taxon[worst] / by_taxon[best] if by_taxon[best] > 0 else None

    if spread is None:
        verdict = (
            f"{best.title()} show no modelled loss at all here while "
            f"{worst} do. A single index would report the average of those two "
            f"and describe neither."
        )
    elif spread > 1.6:
        verdict = (
            f"{worst.title()} are hit {spread:.1f} times harder than {best}. "
            f"An aggregate index would report a number in between and describe "
            f"neither group."
        )
    else:
        verdict = (
            f"The taxa broadly agree here, within a factor of {spread:.1f}. "
            f"The aggregate is a fair summary in this particular case."
        )

    return {"spread": spread, "worst": worst, "best": best, "verdict": verdict}


def compare_land_uses(
    product: str,
    kg: float,
    region: str | None = None,
    amortisation_years: int = DEFAULT_AMORTISATION_YEARS,
) -> list:
    """The same product grown every way, ranked.

    This is where the module earns its keep: shade-grown cocoa against full-sun
    cocoa is a larger change than most substitutions between products.
    """
    rows = []
    for land_use in LAND_USE_CLASSES:
        result = product_footprint(
            product, kg, region=region, land_use=land_use,
            amortisation_years=amortisation_years,
        )
        rows.append({
            "land_use": land_use,
            "label": LAND_USE_CLASSES[land_use]["label"],
            "pdf_m2_yr": result["pdf_m2_yr"],
            "by_taxon": result["by_taxon"],
            "note": LAND_USE_CLASSES[land_use]["note"],
        })
    rows.sort(key=lambda row: row["pdf_m2_yr"])
    return rows


def compare_regions(
    product: str,
    kg: float,
    land_use: str | None = None,
    amortisation_years: int = DEFAULT_AMORTISATION_YEARS,
) -> list:
    """The same product sourced from every region, ranked.

    Counterfactual by design: several of these pairings do not exist in the
    world, since oil palm does not grow on temperate grassland. The comparison
    is there to show how much the regional weight alone moves the answer, which
    is the argument for caring about sourcing rather than about which product is
    bought. Read the rows that are physically possible.
    """
    rows = []
    for region in REGIONS:
        result = product_footprint(
            product, kg, region=region, land_use=land_use,
            amortisation_years=amortisation_years,
        )
        rows.append({
            "region": region,
            "label": REGIONS[region]["label"],
            "pdf_m2_yr": result["pdf_m2_yr"],
            "vulnerability": REGIONS[region]["vulnerability"],
            "note": REGIONS[region]["note"],
        })
    rows.sort(key=lambda row: row["pdf_m2_yr"])
    return rows


def get_biodiversity_insights(result: dict) -> list:
    """Plain-language findings, emitted only where the result supports them."""
    insights = []
    total = result["pdf_m2_yr"]

    if total <= 0:
        return ["This basket has no modelled land footprint."]

    transformation_share = result["transformation_pdf_m2_yr"] / total * 100.0
    if transformation_share > 25.0:
        insights.append(
            f"{transformation_share:.0f}% of this footprint is land "
            f"transformation rather than occupation - conversion happening now "
            f"rather than land farmed for generations. That share is the part "
            f"a sourcing change can remove outright."
        )
    elif transformation_share < 5.0:
        insights.append(
            "Almost all of this is occupation of land converted long ago. "
            "Eating less of it frees land; it does not prevent a conversion "
            "that has already happened."
        )

    items = result["items"]
    if items and len(items) > 1:
        top = items[0]
        share = top["pdf_m2_yr"] / total * 100.0
        if share > 40.0:
            insights.append(
                f"{top['label']} alone is {share:.0f}% of the basket. "
                f"Everything else is a rounding error next to it."
            )

    disagreement = result["taxon_disagreement"]
    if disagreement.get("verdict"):
        insights.append(disagreement["verdict"])

    defaults = [row for row in items if row["used_default_region"]]
    if defaults:
        insights.append(
            f"{len(defaults)} of {len(items)} items use an assumed sourcing "
            f"region. Sourcing moves this number by more than switching "
            f"product does, so those are the assumptions to challenge first."
        )

    share = result["boundary"]["share"]
    if share > 1.0:
        insights.append(
            f"This is {share:.1f} times a downscaled per-capita share of the "
            f"safe operating space. The downscaling is an ethical choice, not "
            f"a scientific result."
        )

    band = result["range"]
    insights.append(
        f"The plausible range runs from {band['low']:,.0f} to "
        f"{band['high']:,.0f} PDF.m2.yr. The central figure sits at the "
        f"geometric centre of that range and is not more trustworthy than its "
        f"ends."
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
        CREATE TABLE IF NOT EXISTS biodiversity_baskets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            pdf_m2_yr REAL NOT NULL,
            transformation_share REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_biodiversity_user
        ON biodiversity_baskets (user_id)
        """
    )


def save_basket(user_id: str, name: str, result: dict) -> int:
    """Persist a basket result and return its row id."""
    if not user_id:
        raise BiodiversityError("A basket needs a user to belong to.")
    if not name or not name.strip():
        raise BiodiversityError("A basket needs a name.")

    payload = json.dumps({
        "items": [
            {
                "product": row["product"],
                "kg": row["kg"],
                "region": row["region"],
                "land_use": row["land_use"],
                "pdf_m2_yr": row["pdf_m2_yr"],
            }
            for row in result["items"]
        ],
        "by_taxon": result["by_taxon"],
        "occupation_pdf_m2_yr": result["occupation_pdf_m2_yr"],
        "transformation_pdf_m2_yr": result["transformation_pdf_m2_yr"],
        "amortisation_years": result["amortisation_years"],
        "range": result["range"],
    })

    total = result["pdf_m2_yr"]
    share = result["transformation_pdf_m2_yr"] / total if total > 0 else 0.0

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO biodiversity_baskets
                (user_id, name, payload, pdf_m2_yr, transformation_share)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name.strip(), payload, float(total), float(share)),
        )
        return int(cursor.lastrowid)


def get_baskets(user_id: str) -> list:
    """Saved baskets for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, pdf_m2_yr, transformation_share,
                       created_at
                FROM biodiversity_baskets
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved biodiversity baskets")
        return []

    baskets = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        baskets.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "pdf_m2_yr": row[3],
            "transformation_share": row[4],
            "created_at": row[5],
        })
    return baskets


def delete_basket(user_id: str, basket_id: int) -> bool:
    """Delete one saved basket. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM biodiversity_baskets WHERE id = ? AND user_id = ?",
                (basket_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete biodiversity basket %s", basket_id)
        return False
