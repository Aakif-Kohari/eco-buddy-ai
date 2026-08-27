"""The impact category where mass tells you nothing, and the app has no number for it.

This app measures climate in some depth, water in ``water_scarcity.py``,
nutrients in ``nutrient_footprint.py``, land and biodiversity in
``biodiversity_footprint.py``, and material input in ``material_footprint.py``.
The one mainstream impact category with no representation at all is toxicity.
The word appears in three modules, every time as an unquantified adjective
inside a recommendation string.

That gap is not neutral. It is the category where the app's advice is most
likely to be confidently wrong, because it is the category where carbon and
impact diverge hardest. ``ethical_shopping.py``, ``circular_economy_engine.py``
and ``home_guide.py`` all propose substitutions. Several classic green
substitutions are better on carbon and worse on human toxicity, and nothing in
the codebase can currently notice.

Mass is not the variable
-------------------------
Every other module here is mass-weighted, and for toxicity mass is close to
irrelevant. A few grams of something persistent and bioaccumulative outweighs
tonnes of something inert. This is why the gap is structural rather than an
oversight: there was no place in the existing data model for a quantity that
does not scale with tonnage.

Three steps, kept visible
--------------------------
A characterisation factor is the product of fate, exposure and effect - how long
the substance persists, how much of it reaches people or organisms, and what it
does when it gets there. They are separable, they are reported separately here,
and that is the difference between a result a reader can interrogate and an
oracle. Collapsing them into one number per kilogram is not a simplification of
this model; it is a different and wrong quantity.

The compartment is required, not defaulted
-------------------------------------------
The same substance emitted to urban air, to rural air, to freshwater or to
agricultural soil produces impacts differing by orders of magnitude. A caller
who does not know the compartment does not have enough information to be given
an answer, and is told so rather than handed a default that quietly assumes one.

Cancer and non-cancer are not added
------------------------------------
They rest on different effect factors and different bodies of evidence. Summing
them into a single CTUh figure is common and discards the distinction that
actually drives regulation, so they stay apart the whole way through.

Interim factors stay flagged
-----------------------------
Metals and several organics carry factors the consensus model itself marks as
interim, because their uncertainty spans orders of magnitude. Presenting an
interim metal factor with the same visual weight as a recommended organic one is
the main way this metric gets misused, so the flag survives into every result
and into the comparison output.

There is deliberately no single environmental score
----------------------------------------------------
Toxicity results span more orders of magnitude than any other category in this
app. Normalised and weighted into a composite they would either dominate the sum
or be scaled into irrelevance, and either way both the toxicity and everything
else become unreadable. ``compare_options`` will report that carbon and toxicity
disagree; it will not resolve the disagreement by inventing a weighting.

Where this connects to code already merged
-------------------------------------------
*   ``material_footprint.py`` prices mining in tonnes of rock moved. The
    tailings are the toxicity story, and this supplies it.
*   ``plastic_leakage.py`` tracks where plastic ends up but not the additives
    that make where it ends up matter.
*   ``refrigerant_gases.py`` tracks GWP but not the degradation products.
*   ``circular_economy_engine.py`` and ``ethical_shopping.py`` make substitution
    claims they currently have no basis for.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import math
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

LN2 = math.log(2.0)


class ToxicityError(ValueError):
    """Raised when a toxicity calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Compartments
#
# Required on every call. The intake rate is the fraction of the mass resident
# in a compartment that reaches a human population per day, and the water
# transfer is the fraction that finds its way into freshwater, which is what
# drives the ecotoxicity result.
#
# The spread between urban air and natural soil is nearly three orders of
# magnitude. Defaulting this would be the single largest error the module could
# make, so it does not have a default.
# ---------------------------------------------------------------------------
COMPARTMENTS = {
    "urban_air": {
        "label": "Urban air",
        "intake_rate_per_day": 3.0e-6,
        "water_transfer": 0.15,
        "note": "Emitted where the people are. The intake fraction here is "
                "one to two orders of magnitude above rural air for the same "
                "substance and the same mass, which is why a stack height or "
                "a ring road's position changes the answer more than the "
                "chemistry does.",
    },
    "rural_air": {
        "label": "Rural air",
        "intake_rate_per_day": 2.0e-7,
        "water_transfer": 0.25,
        "note": "Disperses before it reaches a population. More of it "
                "deposits to soil and water, so the human number falls and "
                "the ecotoxicity number does not.",
    },
    "freshwater": {
        "label": "Freshwater",
        "intake_rate_per_day": 1.2e-6,
        "water_transfer": 1.0,
        "note": "Drinking water and freshwater fish. The dominant compartment "
                "for ecotoxicity by construction, since nothing has to be "
                "transported anywhere first.",
    },
    "seawater": {
        "label": "Seawater",
        "intake_rate_per_day": 4.0e-8,
        "water_transfer": 0.0,
        "note": "Enormous dilution and a long path back to people. Freshwater "
                "ecotoxicity is not assessed for marine emissions here, which "
                "is a limitation of the indicator rather than an absence of "
                "harm.",
    },
    "agricultural_soil": {
        "label": "Agricultural soil",
        "intake_rate_per_day": 8.0e-7,
        "water_transfer": 0.35,
        "note": "Crops are a direct route into people, which is why a "
                "pesticide applied to farmland scores far above the same "
                "pesticide reaching natural ground.",
    },
    "natural_soil": {
        "label": "Natural soil",
        "intake_rate_per_day": 5.0e-9,
        "water_transfer": 0.20,
        "note": "Almost no human intake pathway. A substance can be very "
                "harmful and score near zero here, which is a statement about "
                "exposure rather than about the substance.",
    },
}


# ---------------------------------------------------------------------------
# Substances
#
# Curated to what this app already models rather than attempted comprehensively:
# the metals behind material_footprint.py, the pesticides behind the food
# modules, the additives behind plastic_leakage.py, and the degradation products
# behind refrigerant_gases.py.
#
# ``half_life_days`` per compartment gives the fate step. ``bioavailability``
# modulates the exposure step. The effect factors are cases per kilogram taken
# in, kept separate for cancer and non-cancer throughout.
#
# ``interim`` marks factors the consensus model does not consider settled. Every
# metal here is interim, and that is not a defect in this table.
# ---------------------------------------------------------------------------
SUBSTANCES = {
    "lead": {
        "label": "Lead",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 10.0, "rural_air": 10.0, "freshwater": 3600.0,
            "seawater": 3600.0, "agricultural_soil": 25000.0,
            "natural_soil": 25000.0,
        },
        "bioavailability": 0.55,
        "effect_cancer_per_kg_intake": 0.09,
        "effect_noncancer_per_kg_intake": 2.60,
        "eco_effect_paf_m3_per_kg": 9.5e3,
        "interim": True,
        "note": "Does not degrade, so its fate factor in soil is effectively a "
                "residence time of decades. Neurotoxic at exposures with no "
                "established threshold, which is why the non-cancer effect "
                "factor dominates the cancer one by an order of magnitude.",
    },
    "cadmium": {
        "label": "Cadmium",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 8.0, "rural_air": 8.0, "freshwater": 2800.0,
            "seawater": 2800.0, "agricultural_soil": 11000.0,
            "natural_soil": 11000.0,
        },
        "bioavailability": 0.70,
        "effect_cancer_per_kg_intake": 1.40,
        "effect_noncancer_per_kg_intake": 3.90,
        "eco_effect_paf_m3_per_kg": 2.6e4,
        "interim": True,
        "note": "Taken up readily by crops from agricultural soil, which makes "
                "the compartment choice matter more for cadmium than for any "
                "other metal here. A phosphate fertiliser impurity as much as "
                "an industrial emission.",
    },
    "mercury": {
        "label": "Mercury",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 180.0, "rural_air": 180.0, "freshwater": 1400.0,
            "seawater": 1400.0, "agricultural_soil": 9000.0,
            "natural_soil": 9000.0,
        },
        "bioavailability": 0.85,
        "effect_cancer_per_kg_intake": 0.05,
        "effect_noncancer_per_kg_intake": 6.20,
        "eco_effect_paf_m3_per_kg": 3.1e4,
        "interim": True,
        "note": "Long atmospheric residence, so an emission in one hemisphere "
                "becomes an exposure in the other. Methylates in sediment and "
                "biomagnifies, which no single-compartment factor captures "
                "well - this figure understates it.",
    },
    "arsenic": {
        "label": "Arsenic",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 9.0, "rural_air": 9.0, "freshwater": 2200.0,
            "seawater": 2200.0, "agricultural_soil": 18000.0,
            "natural_soil": 18000.0,
        },
        "bioavailability": 0.60,
        "effect_cancer_per_kg_intake": 4.80,
        "effect_noncancer_per_kg_intake": 1.10,
        "eco_effect_paf_m3_per_kg": 7.2e3,
        "interim": True,
        "note": "The clearest case in the table for keeping cancer and "
                "non-cancer apart: its carcinogenic effect factor is several "
                "times its non-cancer one, the reverse of every other metal "
                "here.",
    },
    "chromium_vi": {
        "label": "Chromium (VI)",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 5.0, "rural_air": 5.0, "freshwater": 400.0,
            "seawater": 400.0, "agricultural_soil": 1800.0,
            "natural_soil": 1800.0,
        },
        "bioavailability": 0.75,
        "effect_cancer_per_kg_intake": 12.0,
        "effect_noncancer_per_kg_intake": 0.85,
        "eco_effect_paf_m3_per_kg": 1.4e4,
        "interim": True,
        "note": "Speciation is everything. Chromium III is a nutrient and "
                "chromium VI is a potent carcinogen, and a table keyed on the "
                "element rather than the species would average them into "
                "something meaningless.",
    },
    "copper_ion": {
        "label": "Copper (ionic)",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 7.0, "rural_air": 7.0, "freshwater": 1900.0,
            "seawater": 1900.0, "agricultural_soil": 8000.0,
            "natural_soil": 8000.0,
        },
        "bioavailability": 0.40,
        "effect_cancer_per_kg_intake": 0.0,
        "effect_noncancer_per_kg_intake": 0.22,
        "eco_effect_paf_m3_per_kg": 6.8e4,
        "interim": True,
        "note": "Barely a human toxicity concern and among the worst aquatic "
                "toxicants in the table. Included specifically because it "
                "shows that the human and ecosystem indicators cannot be "
                "collapsed into one another.",
    },
    "zinc_ion": {
        "label": "Zinc (ionic)",
        "family": "heavy_metal",
        "half_life_days": {
            "urban_air": 7.0, "rural_air": 7.0, "freshwater": 1600.0,
            "seawater": 1600.0, "agricultural_soil": 7000.0,
            "natural_soil": 7000.0,
        },
        "bioavailability": 0.35,
        "effect_cancer_per_kg_intake": 0.0,
        "effect_noncancer_per_kg_intake": 0.06,
        "eco_effect_paf_m3_per_kg": 2.2e4,
        "interim": True,
        "note": "An essential nutrient and an aquatic toxicant above a "
                "threshold. Tyre and brake wear put a great deal of it into "
                "roadside runoff.",
    },
    "glyphosate": {
        "label": "Glyphosate",
        "family": "pesticide",
        "half_life_days": {
            "urban_air": 2.0, "rural_air": 2.0, "freshwater": 40.0,
            "seawater": 40.0, "agricultural_soil": 32.0,
            "natural_soil": 45.0,
        },
        "bioavailability": 0.25,
        "effect_cancer_per_kg_intake": 0.008,
        "effect_noncancer_per_kg_intake": 0.030,
        "eco_effect_paf_m3_per_kg": 62.0,
        "interim": False,
        "note": "Degrades in weeks and is applied in enormous quantity. Its "
                "per-kilogram factor is low and its total burden is not, which "
                "is the argument for always reporting mass alongside impact.",
    },
    "chlorpyrifos": {
        "label": "Chlorpyrifos",
        "family": "pesticide",
        "half_life_days": {
            "urban_air": 3.0, "rural_air": 3.0, "freshwater": 60.0,
            "seawater": 60.0, "agricultural_soil": 90.0,
            "natural_soil": 120.0,
        },
        "bioavailability": 0.80,
        "effect_cancer_per_kg_intake": 0.020,
        "effect_noncancer_per_kg_intake": 1.90,
        "eco_effect_paf_m3_per_kg": 4.9e5,
        "interim": False,
        "note": "An organophosphate with extreme aquatic toxicity - the "
                "highest ecotoxicity effect factor in this table by a wide "
                "margin. Restricted in many jurisdictions and still widely "
                "used in others.",
    },
    "imidacloprid": {
        "label": "Imidacloprid",
        "family": "pesticide",
        "half_life_days": {
            "urban_air": 1.5, "rural_air": 1.5, "freshwater": 120.0,
            "seawater": 120.0, "agricultural_soil": 190.0,
            "natural_soil": 220.0,
        },
        "bioavailability": 0.45,
        "effect_cancer_per_kg_intake": 0.004,
        "effect_noncancer_per_kg_intake": 0.14,
        "eco_effect_paf_m3_per_kg": 8.8e4,
        "interim": False,
        "note": "Persistent in soil and highly toxic to invertebrates. The "
                "freshwater ecotoxicity indicator captures part of that and "
                "misses the pollinator effect entirely, which is a boundary of "
                "the indicator worth stating rather than working around.",
    },
    "atrazine": {
        "label": "Atrazine",
        "family": "pesticide",
        "half_life_days": {
            "urban_air": 4.0, "rural_air": 4.0, "freshwater": 200.0,
            "seawater": 200.0, "agricultural_soil": 110.0,
            "natural_soil": 140.0,
        },
        "bioavailability": 0.50,
        "effect_cancer_per_kg_intake": 0.045,
        "effect_noncancer_per_kg_intake": 0.21,
        "eco_effect_paf_m3_per_kg": 3.4e3,
        "interim": False,
        "note": "Mobile enough to reach groundwater, which is why it shows up "
                "in drinking water sources long after application and far "
                "from where it was applied.",
    },
    "benzene": {
        "label": "Benzene",
        "family": "solvent",
        "half_life_days": {
            "urban_air": 6.0, "rural_air": 6.0, "freshwater": 25.0,
            "seawater": 25.0, "agricultural_soil": 30.0,
            "natural_soil": 30.0,
        },
        "bioavailability": 0.90,
        "effect_cancer_per_kg_intake": 0.85,
        "effect_noncancer_per_kg_intake": 0.12,
        "eco_effect_paf_m3_per_kg": 88.0,
        "interim": False,
        "note": "A known human carcinogen with a short environmental life. "
                "Almost entirely a human health concern and barely an "
                "ecotoxicity one, the mirror image of copper.",
    },
    "toluene": {
        "label": "Toluene",
        "family": "solvent",
        "half_life_days": {
            "urban_air": 2.5, "rural_air": 2.5, "freshwater": 20.0,
            "seawater": 20.0, "agricultural_soil": 25.0,
            "natural_soil": 25.0,
        },
        "bioavailability": 0.85,
        "effect_cancer_per_kg_intake": 0.0,
        "effect_noncancer_per_kg_intake": 0.055,
        "eco_effect_paf_m3_per_kg": 130.0,
        "interim": False,
        "note": "The common substitute where benzene is being designed out. "
                "Substantially less harmful and not harmless, which is what a "
                "substitution comparison is for.",
    },
    "formaldehyde": {
        "label": "Formaldehyde",
        "family": "solvent",
        "half_life_days": {
            "urban_air": 1.2, "rural_air": 1.2, "freshwater": 8.0,
            "seawater": 8.0, "agricultural_soil": 6.0,
            "natural_soil": 6.0,
        },
        "bioavailability": 0.95,
        "effect_cancer_per_kg_intake": 0.32,
        "effect_noncancer_per_kg_intake": 0.28,
        "eco_effect_paf_m3_per_kg": 210.0,
        "interim": False,
        "note": "Breaks down within days, so its fate factor is tiny and its "
                "indoor exposure is not. This module measures outdoor emission "
                "compartments and therefore understates the exposure that "
                "actually matters for it.",
    },
    "dehp": {
        "label": "DEHP (phthalate plasticiser)",
        "family": "plastic_additive",
        "half_life_days": {
            "urban_air": 1.0, "rural_air": 1.0, "freshwater": 55.0,
            "seawater": 55.0, "agricultural_soil": 300.0,
            "natural_soil": 340.0,
        },
        "bioavailability": 0.65,
        "effect_cancer_per_kg_intake": 0.014,
        "effect_noncancer_per_kg_intake": 0.62,
        "eco_effect_paf_m3_per_kg": 1.9e3,
        "interim": False,
        "note": "Not bound into the polymer, so it leaches over the material's "
                "life. The additive that makes where plastic ends up matter, "
                "which plastic_leakage.py can locate and could not previously "
                "characterise.",
    },
    "bisphenol_a": {
        "label": "Bisphenol A",
        "family": "plastic_additive",
        "half_life_days": {
            "urban_air": 1.0, "rural_air": 1.0, "freshwater": 30.0,
            "seawater": 30.0, "agricultural_soil": 75.0,
            "natural_soil": 90.0,
        },
        "bioavailability": 0.70,
        "effect_cancer_per_kg_intake": 0.006,
        "effect_noncancer_per_kg_intake": 0.48,
        "eco_effect_paf_m3_per_kg": 2.7e3,
        "interim": True,
        "note": "Interim because the dose-response for endocrine effects is "
                "not monotonic, and the linear effect factor this model uses "
                "is the wrong shape for it. Reported with that flag rather "
                "than omitted.",
    },
    "decabde": {
        "label": "DecaBDE (flame retardant)",
        "family": "flame_retardant",
        "half_life_days": {
            "urban_air": 60.0, "rural_air": 60.0, "freshwater": 700.0,
            "seawater": 700.0, "agricultural_soil": 2200.0,
            "natural_soil": 2600.0,
        },
        "bioavailability": 0.30,
        "effect_cancer_per_kg_intake": 0.011,
        "effect_noncancer_per_kg_intake": 0.19,
        "eco_effect_paf_m3_per_kg": 5.6e3,
        "interim": True,
        "note": "Persistent and bioaccumulative, and present in electronics in "
                "quantities small enough that a mass-weighted view drops it "
                "entirely. Exactly the substance a mass-based app cannot see.",
    },
    "tfa": {
        "label": "Trifluoroacetic acid (HFO degradation product)",
        "family": "refrigerant_degradation",
        "half_life_days": {
            "urban_air": 15.0, "rural_air": 15.0, "freshwater": 100000.0,
            "seawater": 100000.0, "agricultural_soil": 40000.0,
            "natural_soil": 40000.0,
        },
        "bioavailability": 0.20,
        "effect_cancer_per_kg_intake": 0.0,
        "effect_noncancer_per_kg_intake": 0.009,
        "eco_effect_paf_m3_per_kg": 41.0,
        "interim": True,
        "note": "Low toxicity per kilogram and effectively infinite "
                "persistence in water, so the fate step rather than the effect "
                "step carries the result. The impact refrigerant_gases.py "
                "cannot see, because it stops at global warming potential.",
    },
}

# Human toxicity results are reported in comparative toxic units, cases per
# kilogram emitted. Ecotoxicity is in PAF m3 day per kilogram. They are not
# added to each other, and neither is added to carbon.
HUMAN_UNIT = "CTUh"
ECO_UNIT = "CTUe"


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def list_substances(family=None):
    """Substance keys, optionally filtered to one family."""
    if family is None:
        return sorted(SUBSTANCES)
    return sorted(k for k, v in SUBSTANCES.items() if v["family"] == family)


def list_families():
    """The distinct substance families present in the table."""
    return sorted({spec["family"] for spec in SUBSTANCES.values()})


def get_substance(key):
    """One substance specification."""
    try:
        return SUBSTANCES[key]
    except KeyError:
        raise ToxicityError(
            f"Unknown substance '{key}'. Known substances: "
            f"{', '.join(list_substances())}."
        )


def list_compartments():
    """Emission compartments, most exposed first."""
    return sorted(
        COMPARTMENTS,
        key=lambda k: -COMPARTMENTS[k]["intake_rate_per_day"],
    )


def get_compartment(key):
    """One compartment specification."""
    if key is None:
        raise ToxicityError(
            "An emission compartment is required. The same substance emitted "
            "to urban air and to natural soil differs by orders of magnitude, "
            "so there is no defensible default - a caller who does not know "
            "the compartment does not have enough information for an answer."
        )
    try:
        return COMPARTMENTS[key]
    except KeyError:
        raise ToxicityError(
            f"Unknown compartment '{key}'. Known compartments: "
            f"{', '.join(list_compartments())}."
        )


def list_interim_substances():
    """Substances whose factors the model does not treat as settled."""
    return sorted(k for k, v in SUBSTANCES.items() if v["interim"])


# ---------------------------------------------------------------------------
# The three steps
# ---------------------------------------------------------------------------
def fate_factor(substance, compartment):
    """Residence time in days: how long the substance stays where it landed.

    Derived from the compartment half-life. This is the step that makes a
    persistent substance dangerous at small mass, and the step a hazard band
    has no way to represent.
    """
    spec = get_substance(substance)
    get_compartment(compartment)
    try:
        half_life = spec["half_life_days"][compartment]
    except KeyError:
        raise ToxicityError(
            f"No half-life for {substance} in {compartment}."
        )
    if half_life <= 0:
        raise ToxicityError("Half-life must be positive.")
    return half_life / LN2


def exposure_factor(substance, compartment):
    """Fraction of the resident mass taken in per day, per day.

    The compartment's intake rate scaled by how bioavailable the substance is.
    Multiplied by the fate factor this gives an intake fraction.
    """
    spec = get_substance(substance)
    comp = get_compartment(compartment)
    return comp["intake_rate_per_day"] * spec["bioavailability"]


def intake_fraction(substance, compartment):
    """Kilograms taken in per kilogram emitted: fate multiplied by exposure."""
    return (
        fate_factor(substance, compartment)
        * exposure_factor(substance, compartment)
    )


def effect_factors(substance):
    """Cases per kilogram taken in, cancer and non-cancer kept apart."""
    spec = get_substance(substance)
    return {
        "cancer": spec["effect_cancer_per_kg_intake"],
        "noncancer": spec["effect_noncancer_per_kg_intake"],
    }


def characterisation_factor(substance, compartment):
    """CTUh per kilogram emitted, with the three steps returned alongside.

    The steps are in the result because the product on its own is an assertion
    and the decomposition is an argument.
    """
    spec = get_substance(substance)
    ff = fate_factor(substance, compartment)
    xf = exposure_factor(substance, compartment)
    ef = effect_factors(substance)
    intake = ff * xf

    return {
        "substance": substance,
        "label": spec["label"],
        "compartment": compartment,
        "compartment_label": get_compartment(compartment)["label"],
        "fate_factor_days": ff,
        "exposure_factor_per_day": xf,
        "intake_fraction": intake,
        "effect_cancer": ef["cancer"],
        "effect_noncancer": ef["noncancer"],
        "cf_cancer_ctuh_per_kg": intake * ef["cancer"],
        "cf_noncancer_ctuh_per_kg": intake * ef["noncancer"],
        "interim": spec["interim"],
        "unit": HUMAN_UNIT,
        "not_summed_note": (
            "Cancer and non-cancer rest on different effect factors and "
            "different evidence. They are reported separately and are never "
            "added to each other."
        ),
    }


def ecotoxicity_factor(substance, compartment):
    """CTUe per kilogram emitted, for freshwater ecosystems.

    Only the fraction of an emission that reaches freshwater is characterised,
    which is why a marine emission returns zero here. That zero is a boundary
    of the indicator, not a statement that nothing was harmed.
    """
    spec = get_substance(substance)
    comp = get_compartment(compartment)

    water_residence = spec["half_life_days"]["freshwater"] / LN2
    transfer = comp["water_transfer"]
    ctue = water_residence * transfer * spec["eco_effect_paf_m3_per_kg"] / 365.0

    return {
        "substance": substance,
        "label": spec["label"],
        "compartment": compartment,
        "water_transfer_fraction": transfer,
        "freshwater_residence_days": water_residence,
        "eco_effect_paf_m3_per_kg": spec["eco_effect_paf_m3_per_kg"],
        "cf_ctue_per_kg": ctue,
        "interim": spec["interim"],
        "unit": ECO_UNIT,
        "boundary_note": (
            "Freshwater only. A marine emission characterises to zero here "
            "because the indicator does not cover seawater, which is a limit "
            "of the indicator rather than an absence of harm."
        ) if transfer == 0 else (
            "Only the fraction reaching freshwater is characterised. Marine, "
            "terrestrial and sediment ecotoxicity are outside this indicator."
        ),
    }


# ---------------------------------------------------------------------------
# Assessing an emission
# ---------------------------------------------------------------------------
def assess_emission(substance, mass_kg, compartment):
    """Full toxicity result for a mass of one substance to one compartment."""
    if mass_kg < 0:
        raise ToxicityError("Emitted mass cannot be negative.")

    human = characterisation_factor(substance, compartment)
    eco = ecotoxicity_factor(substance, compartment)

    return {
        "substance": substance,
        "label": human["label"],
        "family": get_substance(substance)["family"],
        "mass_kg": mass_kg,
        "compartment": compartment,
        "compartment_label": human["compartment_label"],
        "fate_factor_days": human["fate_factor_days"],
        "exposure_factor_per_day": human["exposure_factor_per_day"],
        "intake_fraction": human["intake_fraction"],
        "cancer_ctuh": human["cf_cancer_ctuh_per_kg"] * mass_kg,
        "noncancer_ctuh": human["cf_noncancer_ctuh_per_kg"] * mass_kg,
        "ecotoxicity_ctue": eco["cf_ctue_per_kg"] * mass_kg,
        "interim": human["interim"],
        "human_unit": HUMAN_UNIT,
        "eco_unit": ECO_UNIT,
        "aggregation_note": (
            "Cancer, non-cancer and freshwater ecotoxicity are three "
            "quantities in two units. They are not summed with each other and "
            "not summed with carbon."
        ),
        "interim_note": (
            "This factor is interim: its uncertainty spans orders of "
            "magnitude and it should be used to rank rather than to quantify."
            if human["interim"] else
            "This factor is in the recommended set, so its uncertainty is "
            "within the usual range for the method."
        ),
        "boundary_note": eco["boundary_note"],
    }


def assess_inventory(emissions, compartment):
    """Several substances into one compartment, totalled by indicator.

    Totals are per indicator only. There is no grand total, because the three
    indicators are in two units and adding them would produce a number with no
    referent.
    """
    if not emissions:
        raise ToxicityError("Nothing to assess.")

    rows = [
        assess_emission(substance, mass, compartment)
        for substance, mass in emissions.items()
    ]

    totals = {
        "cancer_ctuh": sum(r["cancer_ctuh"] for r in rows),
        "noncancer_ctuh": sum(r["noncancer_ctuh"] for r in rows),
        "ecotoxicity_ctue": sum(r["ecotoxicity_ctue"] for r in rows),
        "mass_kg": sum(r["mass_kg"] for r in rows),
    }

    interim_share = {}
    for indicator in ("cancer_ctuh", "noncancer_ctuh", "ecotoxicity_ctue"):
        total = totals[indicator]
        from_interim = sum(r[indicator] for r in rows if r["interim"])
        interim_share[indicator] = from_interim / total if total else 0.0

    return {
        "compartment": compartment,
        "compartment_label": get_compartment(compartment)["label"],
        "substances": sorted(rows, key=lambda r: -r["noncancer_ctuh"]),
        "totals": totals,
        "interim_share": interim_share,
        "no_grand_total_note": (
            "There is no combined figure. Cancer cases, non-cancer cases and "
            "potentially affected fractions of freshwater species are not "
            "commensurable, and a weighted composite would make all three "
            "unreadable rather than making one readable."
        ),
    }


def dominant_contributors(inventory, indicator="noncancer_ctuh", top_n=3):
    """Which substances carry an inventory, and how little of its mass they are.

    The mass share is the point. Toxicity concentrates in substances that a
    mass-weighted view discards as rounding error.
    """
    valid = ("cancer_ctuh", "noncancer_ctuh", "ecotoxicity_ctue")
    if indicator not in valid:
        raise ToxicityError(f"Indicator must be one of {valid}.")

    ordered = sorted(inventory["substances"], key=lambda r: -r[indicator])
    top = ordered[:top_n]

    total_impact = inventory["totals"][indicator]
    total_mass = inventory["totals"]["mass_kg"]

    return {
        "indicator": indicator,
        "top": [
            {
                "substance": r["substance"],
                "label": r["label"],
                "impact": r[indicator],
                "share_of_impact": (
                    r[indicator] / total_impact if total_impact else 0.0
                ),
                "mass_kg": r["mass_kg"],
                "share_of_mass": (
                    r["mass_kg"] / total_mass if total_mass else 0.0
                ),
                "interim": r["interim"],
            }
            for r in top
        ],
        "top_share_of_impact": (
            sum(r[indicator] for r in top) / total_impact
            if total_impact else 0.0
        ),
        "top_share_of_mass": (
            sum(r["mass_kg"] for r in top) / total_mass if total_mass else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Compartment sensitivity
# ---------------------------------------------------------------------------
def compartment_sensitivity(substance, mass_kg=1.0):
    """The same emission into every compartment.

    Produced so the required-compartment rule can be justified rather than
    merely asserted: the spread here is the argument for it.
    """
    rows = []
    for compartment in list_compartments():
        result = assess_emission(substance, mass_kg, compartment)
        rows.append({
            "compartment": compartment,
            "label": result["compartment_label"],
            "cancer_ctuh": result["cancer_ctuh"],
            "noncancer_ctuh": result["noncancer_ctuh"],
            "ecotoxicity_ctue": result["ecotoxicity_ctue"],
            "intake_fraction": result["intake_fraction"],
        })

    human = [r["noncancer_ctuh"] + r["cancer_ctuh"] for r in rows if
             (r["noncancer_ctuh"] + r["cancer_ctuh"]) > 0]
    spread = max(human) / min(human) if len(human) > 1 else 1.0

    return {
        "substance": substance,
        "label": get_substance(substance)["label"],
        "rows": rows,
        "human_spread_ratio": spread,
        "note": (
            f"The same kilogram of {get_substance(substance)['label']} differs "
            f"by a factor of {spread:,.0f} in human toxicity depending only on "
            f"where it was released. This is why the compartment is a required "
            f"argument and not a default."
        ),
    }


# ---------------------------------------------------------------------------
# Substitution, the primary use case
# ---------------------------------------------------------------------------
def compare_options(options):
    """Compare substitution options on toxicity and carbon, without resolving.

    Each option is a dict with ``name``, ``emissions`` (substance to kg),
    ``compartment`` and ``carbon_kg``. Where carbon and toxicity disagree the
    function says so; it does not produce a combined score, because inventing a
    weighting between cancer cases and kilograms of CO2 is not this module's
    job and is not anybody's job in a footprint app.
    """
    if len(options) < 2:
        raise ToxicityError("A comparison needs at least two options.")

    assessed = []
    for option in options:
        for field in ("name", "emissions", "compartment"):
            if field not in option:
                raise ToxicityError(f"Each option needs a '{field}'.")
        inventory = assess_inventory(option["emissions"], option["compartment"])
        assessed.append({
            "name": option["name"],
            "compartment": option["compartment"],
            "carbon_kg": option.get("carbon_kg"),
            "cancer_ctuh": inventory["totals"]["cancer_ctuh"],
            "noncancer_ctuh": inventory["totals"]["noncancer_ctuh"],
            "ecotoxicity_ctue": inventory["totals"]["ecotoxicity_ctue"],
            "human_ctuh": (
                inventory["totals"]["cancer_ctuh"]
                + inventory["totals"]["noncancer_ctuh"]
            ),
            "interim_share": inventory["interim_share"],
        })

    best_human = min(assessed, key=lambda o: o["human_ctuh"])
    best_eco = min(assessed, key=lambda o: o["ecotoxicity_ctue"])

    carbon_known = all(o["carbon_kg"] is not None for o in assessed)
    best_carbon = (
        min(assessed, key=lambda o: o["carbon_kg"]) if carbon_known else None
    )

    disagreement = None
    if best_carbon and best_carbon["name"] != best_human["name"]:
        disagreement = (
            f"'{best_carbon['name']}' is better on carbon and "
            f"'{best_human['name']}' is better on human toxicity. There is no "
            f"combined score here that would resolve that, and any module "
            f"offering one would be hiding the choice rather than making it."
        )
    elif best_human["name"] != best_eco["name"]:
        disagreement = (
            f"'{best_human['name']}' is better for people and "
            f"'{best_eco['name']}' is better for freshwater ecosystems. Copper "
            f"and benzene are the clearest illustration of why those two "
            f"indicators cannot stand in for one another."
        )

    # Where the winning margin is inside the uncertainty of interim factors,
    # the ranking is not a finding.
    human_values = sorted(o["human_ctuh"] for o in assessed)
    margin = (
        human_values[1] / human_values[0]
        if human_values[0] > 0 else float("inf")
    )
    interim_heavy = any(
        o["interim_share"]["noncancer_ctuh"] > 0.5 for o in assessed
    )
    too_close = interim_heavy and margin < 10

    return {
        "options": assessed,
        "best_human_toxicity": best_human["name"],
        "best_ecotoxicity": best_eco["name"],
        "best_carbon": best_carbon["name"] if best_carbon else None,
        "carbon_compared": carbon_known,
        "indicators_disagree": disagreement is not None,
        "disagreement": disagreement,
        "margin_ratio": margin,
        "too_close_to_call": too_close,
        "verdict": (
            "The difference between these options is smaller than the "
            "uncertainty on the interim factors driving it. The honest answer "
            "is that this comparison does not distinguish them."
            if too_close else
            disagreement or
            f"'{best_human['name']}' is better on every indicator assessed."
        ),
        "no_composite_note": (
            "No composite score is produced. Toxicity spans more orders of "
            "magnitude than any other category in this app; normalised into a "
            "weighted total it would either dominate the sum or vanish from "
            "it, and either way nothing in the total stays readable."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_toxicity_insights(result):
    """Plain sentences about a single-substance assessment."""
    insights = []
    spec = get_substance(result["substance"])

    insights.append(
        f"{result['mass_kg']:,.4g} kg of {result['label']} to "
        f"{result['compartment_label'].lower()} characterises to "
        f"{result['cancer_ctuh']:.3e} {HUMAN_UNIT} cancer and "
        f"{result['noncancer_ctuh']:.3e} {HUMAN_UNIT} non-cancer."
    )

    insights.append(
        f"Of that, the fate step contributes a residence time of "
        f"{result['fate_factor_days']:,.0f} days and the exposure step an "
        f"intake fraction of {result['intake_fraction']:.3e}. Multiplying "
        f"those by the effect factor is the whole calculation, which is why "
        f"all three are shown."
    )

    if result["fate_factor_days"] > 3650:
        insights.append(
            f"With a residence time of "
            f"{result['fate_factor_days'] / 365:,.0f} years in this "
            f"compartment, this substance does not go away. Its impact is "
            f"driven by persistence rather than by potency, and reducing the "
            f"mass emitted is the only lever."
        )

    effects = effect_factors(result["substance"])
    if effects["cancer"] > effects["noncancer"]:
        insights.append(
            "The carcinogenic effect factor exceeds the non-cancer one for "
            "this substance, which is unusual in this table and is the reason "
            "the two are never added together."
        )

    if result["ecotoxicity_ctue"] > 0 and result["noncancer_ctuh"] > 0:
        ratio = result["ecotoxicity_ctue"] / result["noncancer_ctuh"]
        if ratio > 1e6:
            insights.append(
                "This substance is far more of an aquatic problem than a human "
                "one. A single toxicity score would report it as mild."
            )

    if result["interim"]:
        insights.append(
            f"This is an interim factor. {spec['note']} Use it to rank options, "
            f"not to quantify a harm."
        )

    insights.append(result["aggregation_note"])

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS toxicity_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            compartment TEXT NOT NULL,
            cancer_ctuh REAL NOT NULL,
            noncancer_ctuh REAL NOT NULL,
            ecotoxicity_ctue REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_toxicity_assessments_user
        ON toxicity_assessments (user_id)
        """
    )


def save_assessment(user_id, name, inventory):
    """Persist an inventory assessment and return its row id."""
    if not user_id:
        raise ToxicityError("An assessment needs a user to belong to.")
    if not name or not name.strip():
        raise ToxicityError("An assessment needs a name.")

    payload = json.dumps({
        "compartment": inventory["compartment"],
        "interim_share": inventory["interim_share"],
        "substances": [
            {
                "substance": row["substance"],
                "mass_kg": row["mass_kg"],
                "cancer_ctuh": row["cancer_ctuh"],
                "noncancer_ctuh": row["noncancer_ctuh"],
                "ecotoxicity_ctue": row["ecotoxicity_ctue"],
                "interim": row["interim"],
            }
            for row in inventory["substances"]
        ],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO toxicity_assessments
                (user_id, name, payload, compartment, cancer_ctuh,
                 noncancer_ctuh, ecotoxicity_ctue)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload, inventory["compartment"],
                float(inventory["totals"]["cancer_ctuh"]),
                float(inventory["totals"]["noncancer_ctuh"]),
                float(inventory["totals"]["ecotoxicity_ctue"]),
            ),
        )
        return int(cursor.lastrowid)


def get_assessments(user_id):
    """Saved assessments for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, compartment, cancer_ctuh,
                       noncancer_ctuh, ecotoxicity_ctue, created_at
                FROM toxicity_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved toxicity assessments")
        return []

    assessments = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        assessments.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "compartment": row[3],
            "cancer_ctuh": row[4],
            "noncancer_ctuh": row[5],
            "ecotoxicity_ctue": row[6],
            "created_at": row[7],
        })
    return assessments


def delete_assessment(user_id, assessment_id):
    """Delete one saved assessment. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM toxicity_assessments WHERE id = ? AND user_id = ?",
                (assessment_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete toxicity assessment %s", assessment_id)
        return False
