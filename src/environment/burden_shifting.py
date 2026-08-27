"""Whether reducing carbon made something else worse, which nothing here asks.

This repository now computes a genuinely broad set of environmental impacts.
Climate in ``src.environment.climate_metrics.py``, water scarcity in
``water_scarcity.py``, biodiversity in ``biodiversity_footprint.py``, human and
ecosystem toxicity in ``src.carbon.toxicity_characterisation.py``,
eutrophication in ``nutrient_footprint.py``, resource depletion in
``material_footprint.py``, marine litter in ``plastic_leakage.py``. Each is
careful, each is well tested, and each reports in its own unit on its own page.

Nothing puts them in the same frame, so the app cannot answer the question a
multi-impact inventory exists to answer.

Burden shifting is the central hazard of single-issue advice
--------------------------------------------------------------
Biofuels for land and biodiversity. Battery electrification for mining and
toxicity. Almond milk for water scarcity. Every one is a defensible carbon
recommendation and a potentially poor environmental one, and
``src.ai.recommendation_engine.py`` optimises on carbon alone.

Presenting seven numbers on seven pages is not neutrality
-----------------------------------------------------------
400 kg CO2e against 12 m3 water-equivalent against 3e-7 DALY is not a
comparison a person can make unaided. Leaving the integration to the reader is
an unstated invitation to weight by whichever number looks biggest, which is
the worst available weighting.

The app already weights, it just does not say so
--------------------------------------------------
By devoting most of its surface to carbon it has made a choice. The honest
response is an explicit, switchable, labelled weighting set - including a
carbon-only set that reproduces the current behaviour so a user can see what
it has been doing.

Aggregation done badly is worse than not aggregating
------------------------------------------------------
A single eco-score summing raw magnitudes across units is meaningless, and
confidently presented meaninglessness is the worst outcome available here.
Normalisation comes before weighting, weighting is always named, and the
disaggregated profile stays the primary output. This module does not return a
headline score by default and there is a test that it does not.

Some categories have no safe level, and inventing one would be worse
---------------------------------------------------------------------
Novel entities and toxicity have no agreed per-capita boundary. Normalising
them against a fabricated one would produce a confident number resting on
nothing. They are reported as un-normalisable against a boundary, and the
coverage report names them, because absence of evidence is the most likely way
a cross-impact view misleads.

Where this connects to code already merged
--------------------------------------------
Read-only with respect to every impact module. It consumes their outputs and
modifies nothing, so a change here cannot alter a single existing result.

*   ``src.carbon.abatement_curve.py`` ranks by cost per tonne of CO2e. An
    option that is cheap per tonne and disastrous for freshwater ranks first
    and stays first.
*   ``src.environment.material_footprint.py``, ``nutrient_footprint.py`` and
    ``biodiversity_footprint.py`` each mention a planetary boundary in
    isolation. Nothing reported which one a user is furthest beyond.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class BurdenShiftError(ValueError):
    """Raised when a cross-impact comparison cannot be made as asked."""


# A category worsening by more than this share of its own boundary budget is
# flagged, whatever happens to the weighted total. A net-positive change that
# triples freshwater impact is still something a user is entitled to know.
DEFAULT_SHIFT_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# Impact categories
#
# Two references per category, because they answer different questions and
# give different pictures:
#
#   global_average   current impact per person per year. Normalising against
#                    it says how a user compares to everyone else.
#   boundary         a per-person share of a safe operating space. Normalising
#                    against it says how a user compares to what the system can
#                    take. The two disagree sharply wherever the world is
#                    already beyond the boundary, which is most of them.
#
# ``confidence`` is stated because these are not equally solid. Downscaling a
# planetary boundary to a person involves an allocation choice that is itself
# contested, and for two categories there is no agreed boundary at all.
# ---------------------------------------------------------------------------
IMPACT_CATEGORIES = {
    "climate_change": {
        "label": "Climate change",
        "unit": "kg CO2e",
        "global_average": 8100.0,
        "boundary": 985.0,
        "confidence": "well established",
        "module": "src.environment.climate_metrics",
        "note": "The boundary is a per-person share of a remaining budget "
                "consistent with 1.5 C. The global average is roughly eight "
                "times it, which is why normalising against the average and "
                "against the boundary tell such different stories.",
    },
    "water_scarcity": {
        "label": "Water scarcity",
        "unit": "m3 world-eq",
        "global_average": 11500.0,
        "boundary": 3800.0,
        "confidence": "moderately established",
        "module": "src.environment.water_scarcity",
        "note": "AWARE-weighted consumptive use. The boundary is a downscaled "
                "freshwater use limit and is sensitive to how much "
                "environmental flow is reserved, which is a policy choice "
                "rather than a measurement.",
    },
    "land_use": {
        "label": "Land use",
        "unit": "m2a crop-eq",
        "global_average": 6600.0,
        "boundary": 2600.0,
        "confidence": "moderately established",
        "module": "src.environment.land_opportunity_cost",
        "note": "Land occupation weighted towards cropland equivalence. The "
                "boundary derives from the land-system-change limit, which is "
                "stated regionally rather than globally and loses meaning in "
                "the downscaling.",
    },
    "biodiversity_loss": {
        "label": "Biodiversity loss",
        "unit": "PDF m2 yr",
        "global_average": 210000.0,
        "boundary": 80000.0,
        "confidence": "contested",
        "module": "src.environment.biodiversity_footprint",
        "note": "Potentially disappeared fraction of species from land use. "
                "The characterisation factors vary by an order of magnitude "
                "between methods, so this category carries the widest "
                "uncertainty of anything in the table and should not be the "
                "deciding factor on its own.",
    },
    "eutrophication_freshwater": {
        "label": "Eutrophication, freshwater",
        "unit": "kg P-eq",
        "global_average": 0.61,
        "boundary": 0.10,
        "confidence": "well established",
        "module": "src.environment.nutrient_footprint",
        "note": "Phosphorus to freshwater. The boundary is one of the more "
                "solid ones, being grounded in a measurable global flow rather "
                "than in a modelled damage pathway.",
    },
    "eutrophication_marine": {
        "label": "Eutrophication, marine",
        "unit": "kg N-eq",
        "global_average": 19.5,
        "boundary": 4.4,
        "confidence": "well established",
        "module": "src.environment.nutrient_footprint",
        "note": "Reactive nitrogen to coastal waters. Same footing as the "
                "freshwater phosphorus boundary and transgressed by a similar "
                "margin.",
    },
    "resource_depletion": {
        "label": "Mineral resource depletion",
        "unit": "kg Sb-eq",
        "global_average": 0.064,
        "boundary": 0.021,
        "confidence": "contested",
        "module": "src.environment.material_footprint",
        "note": "Antimony-equivalent scarcity weighting. There is no "
                "planetary boundary for mineral depletion; the figure here is "
                "a reserve-based sustainability proxy and is the weakest "
                "reference in the table.",
    },
    "human_toxicity": {
        "label": "Human toxicity",
        "unit": "CTUh",
        "global_average": 0.00053,
        "boundary": None,
        "confidence": "no boundary defined",
        "module": "src.carbon.toxicity_characterisation",
        "note": "USEtox comparative toxic units. There is no agreed safe "
                "per-person level, and inventing one would produce a "
                "confident number resting on nothing. Normalisation against "
                "the current average still works and is what should be used.",
    },
    "ecotoxicity": {
        "label": "Freshwater ecotoxicity",
        "unit": "CTUe",
        "global_average": 57000.0,
        "boundary": None,
        "confidence": "no boundary defined",
        "module": "src.carbon.toxicity_characterisation",
        "note": "Same footing as human toxicity: a real and measurable impact "
                "with no defensible per-person threshold.",
    },
    "plastic_leakage": {
        "label": "Plastic to the environment",
        "unit": "kg",
        "global_average": 3.1,
        "boundary": None,
        "confidence": "no boundary defined",
        "module": "src.environment.plastic_leakage",
        "note": "The novel entities boundary is assessed as transgressed with "
                "no safe operating space quantified. Reporting a per-person "
                "share of a boundary nobody has defined would be a fabrication.",
    },
}


REFERENCES = {
    "boundary": {
        "label": "Planetary boundary share",
        "field": "boundary",
        "note": "How this compares to what the system can take. The more "
                "demanding reference, and unavailable for the three "
                "categories where no safe level has been agreed.",
    },
    "global_average": {
        "label": "Current global average",
        "field": "global_average",
        "note": "How this compares to what everyone else does. Available for "
                "every category, and quietly forgiving: matching the average "
                "on a transgressed boundary is not sustainability.",
    },
}


# ---------------------------------------------------------------------------
# Weighting sets
#
# All of these are value judgements. None is the default in disguise: the
# carbon-only set is included precisely so a user can see what the rest of the
# app has been doing without saying so.
# ---------------------------------------------------------------------------
WEIGHTING_SETS = {
    "equal": {
        "label": "Equal weight",
        "note": "Every category counts the same. Defensible as a starting "
                "point and indefensible as a conclusion, since it treats a "
                "boundary transgressed eightfold and one barely approached as "
                "equally urgent.",
        "weights": {key: 1.0 for key in IMPACT_CATEGORIES},
    },
    "distance_to_boundary": {
        "label": "Distance to boundary",
        "note": "Weighted by how far the world already is beyond each "
                "boundary, so categories in worse shape count for more. "
                "Undefined where no boundary exists, and those categories "
                "fall back to the equal weight rather than to zero.",
        "weights": None,  # computed below
    },
    "damage_oriented": {
        "label": "Damage oriented",
        "note": "Weighted towards categories with the clearest pathway to "
                "human and ecosystem harm. Closer to an endpoint method in "
                "spirit, and it deliberately downweights resource depletion, "
                "which is a scarcity concern rather than a damage one.",
        "weights": {
            "climate_change": 1.0,
            "human_toxicity": 0.9,
            "biodiversity_loss": 0.8,
            "water_scarcity": 0.7,
            "ecotoxicity": 0.6,
            "eutrophication_marine": 0.5,
            "eutrophication_freshwater": 0.5,
            "land_use": 0.4,
            "plastic_leakage": 0.3,
            "resource_depletion": 0.2,
        },
    },
    "carbon_only": {
        "label": "Carbon only (what this app does now)",
        "note": "Climate change at full weight, everything else at zero. Not "
                "offered as a recommendation - it is here so the app's "
                "existing implicit weighting is visible as a choice, and so a "
                "user can watch a ranking change when it is switched away "
                "from.",
        "weights": {
            key: (1.0 if key == "climate_change" else 0.0)
            for key in IMPACT_CATEGORIES
        },
    },
}


def _distance_to_boundary_weights():
    """Weights proportional to how far the global average exceeds a boundary."""
    weights = {}
    for key, meta in IMPACT_CATEGORIES.items():
        boundary = meta["boundary"]
        if boundary in (None, 0):
            weights[key] = 1.0
        else:
            weights[key] = max(1.0, meta["global_average"] / boundary)
    largest = max(weights.values())
    return {key: value / largest for key, value in weights.items()}


WEIGHTING_SETS["distance_to_boundary"]["weights"] = \
    _distance_to_boundary_weights()


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def normalise(profile, reference="boundary"):
    """Express each impact as a share of a per-person reference.

    Returns dimensionless shares that are comparable across categories, plus an
    explicit account of what could not be normalised. The second part is not
    housekeeping: a favourable profile across four categories says nothing
    about the three that were not measured, and this is where that gets said.
    """
    if reference not in REFERENCES:
        raise BurdenShiftError(
            f"{reference!r} is not a known reference. Known references: "
            f"{', '.join(REFERENCES)}."
        )
    if not profile:
        raise BurdenShiftError("There is no impact profile to normalise.")

    field = REFERENCES[reference]["field"]

    rows = []
    unnormalisable = []
    missing = []
    for key, meta in IMPACT_CATEGORIES.items():
        if key not in profile:
            missing.append(key)
            continue
        try:
            amount = float(profile[key])
        except (TypeError, ValueError):
            raise BurdenShiftError(
                f"{profile[key]!r} is not a number for {key!r}."
            )
        if amount < 0:
            raise BurdenShiftError(
                f"{key!r} cannot be negative. A negative impact is an avoided "
                f"burden and belongs in a comparison rather than in a profile."
            )

        divisor = meta[field]
        if divisor in (None, 0):
            unnormalisable.append(key)
            rows.append({
                "category": key,
                "label": meta["label"],
                "unit": meta["unit"],
                "amount": round(amount, 8),
                "share": None,
                "reference": None,
                "confidence": meta["confidence"],
            })
            continue

        rows.append({
            "category": key,
            "label": meta["label"],
            "unit": meta["unit"],
            "amount": round(amount, 8),
            "share": round(amount / divisor, 6),
            "reference": divisor,
            "confidence": meta["confidence"],
        })

    unknown = [key for key in profile if key not in IMPACT_CATEGORIES]
    if unknown:
        raise BurdenShiftError(
            f"{', '.join(sorted(unknown))} are not known impact categories. "
            f"Known categories: {', '.join(IMPACT_CATEGORIES)}."
        )

    scored = [row for row in rows if row["share"] is not None]
    scored.sort(key=lambda row: row["share"], reverse=True)

    return {
        "reference": reference,
        "reference_label": REFERENCES[reference]["label"],
        "categories": rows,
        "ranked": scored,
        "worst_category": scored[0]["category"] if scored else None,
        "worst_share": scored[0]["share"] if scored else None,
        "over_reference": [
            row["category"] for row in scored if row["share"] > 1.0
        ],
        "unnormalisable": unnormalisable,
        "missing": missing,
        "coverage": round(
            len(rows) / len(IMPACT_CATEGORIES), 4
        ),
        "scored_coverage": round(
            len(scored) / len(IMPACT_CATEGORIES), 4
        ),
    }


def coverage_report(normalised):
    """What this profile does and does not say, stated plainly."""
    missing = normalised["missing"]
    unnormalisable = normalised["unnormalisable"]

    warnings = []
    if missing:
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"] for key in missing
        )
        warnings.append(
            f"No data for {names}. A favourable profile across the categories "
            f"that were measured says nothing about the ones that were not, "
            f"and this is the most likely way a cross-impact view misleads."
        )
    if unnormalisable and normalised["reference"] == "boundary":
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"] for key in unnormalisable
        )
        warnings.append(
            f"{names} have no agreed safe per-person level, so they are shown "
            f"in their own units and excluded from any weighted total. "
            f"Inventing a boundary for them would produce a confident number "
            f"resting on nothing."
        )
    contested = [
        row["category"] for row in normalised["ranked"]
        if row["confidence"] in ("contested", "moderately established")
    ]
    if contested:
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"] for key in contested
        )
        warnings.append(
            f"{names} rest on references that are contested or only "
            f"moderately established. They are included because excluding them "
            f"would be worse, but a conclusion resting on one of them alone is "
            f"weaker than it looks."
        )

    return {
        "measured": len(normalised["categories"]),
        "total_categories": len(IMPACT_CATEGORIES),
        "coverage": normalised["coverage"],
        "scored_coverage": normalised["scored_coverage"],
        "warnings": warnings,
        "complete": not missing,
    }


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------
def weighted_score(normalised, weighting):
    """A single number, always labelled with the value judgement behind it.

    Deliberately not produced by ``normalise``. The disaggregated profile is
    the primary output and a weighted total is a derived view that requires the
    caller to name a weighting set, because there is no neutral one.
    """
    if weighting not in WEIGHTING_SETS:
        raise BurdenShiftError(
            f"{weighting!r} is not a known weighting set. Known sets: "
            f"{', '.join(WEIGHTING_SETS)}. There is no unweighted option, "
            f"because summing normalised impacts is itself equal weighting."
        )

    weights = WEIGHTING_SETS[weighting]["weights"]
    contributions = []
    total = 0.0
    for row in normalised["ranked"]:
        weight = weights.get(row["category"], 0.0)
        value = row["share"] * weight
        total += value
        contributions.append({
            "category": row["category"],
            "label": row["label"],
            "share": row["share"],
            "weight": round(weight, 4),
            "contribution": round(value, 6),
        })

    contributions.sort(key=lambda row: row["contribution"], reverse=True)
    for row in contributions:
        row["contribution_share"] = (
            round(row["contribution"] / total, 4) if total else 0.0
        )

    return {
        "weighting": weighting,
        "weighting_label": WEIGHTING_SETS[weighting]["label"],
        "weighting_note": WEIGHTING_SETS[weighting]["note"],
        "reference": normalised["reference"],
        "score": round(total, 6),
        "contributions": contributions,
        "excluded": normalised["unnormalisable"] + normalised["missing"],
    }


# ---------------------------------------------------------------------------
# Burden shifting
# ---------------------------------------------------------------------------
def detect_burden_shift(before, after, reference="boundary",
                        threshold=DEFAULT_SHIFT_THRESHOLD):
    """Flag categories that worsen while others improve.

    The flag fires on the disaggregated movement and not on a weighted total,
    on purpose. A change that improves the weighted score and triples
    freshwater impact is still burden shifting, and a detector that only looked
    at the total would miss exactly the cases it exists for.
    """
    first = normalise(before, reference)
    second = normalise(after, reference)

    rows = []
    improved = []
    worsened = []
    for row in second["categories"]:
        key = row["category"]
        previous = next(
            (item for item in first["categories"]
             if item["category"] == key), None
        )
        if previous is None:
            continue

        amount_change = row["amount"] - previous["amount"]
        share_change = (
            row["share"] - previous["share"]
            if row["share"] is not None and previous["share"] is not None
            else None
        )
        entry = {
            "category": key,
            "label": row["label"],
            "unit": row["unit"],
            "before": previous["amount"],
            "after": row["amount"],
            "amount_change": round(amount_change, 8),
            "relative_change": (
                round(amount_change / previous["amount"], 4)
                if previous["amount"] else None
            ),
            "share_change": (
                round(share_change, 6) if share_change is not None else None
            ),
            "normalisable": row["share"] is not None,
        }
        rows.append(entry)
        if share_change is not None:
            if share_change < -1e-12:
                improved.append(entry)
            elif share_change > 1e-12:
                worsened.append(entry)

    material = [
        entry for entry in worsened
        if entry["share_change"] is not None
        and entry["share_change"] > threshold
    ]
    shifted = bool(improved) and bool(material)

    unnormalised_worsened = [
        entry for entry in rows
        if not entry["normalisable"] and entry["amount_change"] > 0
    ]

    rows.sort(
        key=lambda entry: abs(entry["share_change"] or 0.0), reverse=True
    )

    return {
        "reference": reference,
        "threshold": threshold,
        "categories": rows,
        "improved": [entry["category"] for entry in improved],
        "worsened": [entry["category"] for entry in worsened],
        "material_worsening": [entry["category"] for entry in material],
        "burden_shifted": shifted,
        "net_share_change": round(
            sum(entry["share_change"] for entry in rows
                if entry["share_change"] is not None), 6
        ),
        "unnormalisable_worsening": [
            entry["category"] for entry in unnormalised_worsened
        ],
        "note": (
            "This change improves some categories and materially worsens "
            "others. That is burden shifting, and it is reported whatever "
            "happens to any weighted total."
            if shifted else
            "No material burden shifting detected at this threshold across "
            "the categories with data."
        ),
    }


def trade_off_ratios(shift):
    """Exchange rates between what improved and what got worse.

    Expressed in boundary shares rather than raw units, because a ratio of
    kilograms to cubic metres is arithmetic rather than information.
    """
    improved = [
        entry for entry in shift["categories"]
        if entry["share_change"] is not None and entry["share_change"] < 0
    ]
    worsened = [
        entry for entry in shift["categories"]
        if entry["share_change"] is not None and entry["share_change"] > 0
    ]
    if not improved or not worsened:
        return []

    ratios = []
    for gain in improved:
        for loss in worsened:
            ratios.append({
                "improved": gain["category"],
                "improved_label": gain["label"],
                "worsened": loss["category"],
                "worsened_label": loss["label"],
                "share_gained": round(abs(gain["share_change"]), 6),
                "share_lost": round(loss["share_change"], 6),
                "ratio": round(
                    loss["share_change"] / abs(gain["share_change"]), 4
                ) if gain["share_change"] else None,
                "unit_ratio": (
                    round(loss["amount_change"] / abs(gain["amount_change"]), 6)
                    if gain["amount_change"] else None
                ),
            })

    ratios.sort(key=lambda row: row["ratio"] or 0.0, reverse=True)
    return ratios


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
def dominates(first, second, reference="boundary"):
    """Whether ``first`` is at least as good everywhere and better somewhere."""
    a = normalise(first, reference)
    b = normalise(second, reference)

    shared = [
        row["category"] for row in a["ranked"]
        if any(other["category"] == row["category"] for other in b["ranked"])
    ]
    if not shared:
        raise BurdenShiftError(
            "The two options share no normalisable category, so neither can "
            "dominate the other."
        )

    strictly_better = False
    for key in shared:
        first_share = next(
            row["share"] for row in a["ranked"] if row["category"] == key
        )
        second_share = next(
            row["share"] for row in b["ranked"] if row["category"] == key
        )
        if first_share > second_share + 1e-12:
            return False
        if first_share < second_share - 1e-12:
            strictly_better = True
    return strictly_better


def pareto_front(options, reference="boundary"):
    """Options improved in at least one category and worsened in none.

    These need no value judgement at all and should be surfaced before any
    weighting is applied. Only the remainder requires a user to choose a
    weighting set, and separating the two is the honest way to present a
    multi-criteria comparison.
    """
    if not options or len(options) < 2:
        raise BurdenShiftError(
            "A Pareto comparison needs at least two options."
        )

    named = []
    for index, option in enumerate(options):
        if not isinstance(option, dict) or "profile" not in option:
            raise BurdenShiftError(
                "Each option must be a mapping with a 'profile'."
            )
        named.append({
            "name": str(option.get("name") or f"Option {index + 1}"),
            "profile": option["profile"],
        })

    front = []
    dominated = []
    for candidate in named:
        beaten_by = [
            other["name"] for other in named
            if other is not candidate
            and dominates(other["profile"], candidate["profile"], reference)
        ]
        if beaten_by:
            dominated.append({
                "name": candidate["name"], "dominated_by": beaten_by
            })
        else:
            front.append(candidate["name"])

    return {
        "reference": reference,
        "front": front,
        "dominated": dominated,
        "needs_value_judgement": len(front) > 1,
        "note": (
            f"{len(front)} of {len(named)} options are non-dominated. "
            f"Choosing between them requires a weighting set, because none is "
            f"better than the others in every category."
            if len(front) > 1 else
            f"One option is better than every alternative in every category "
            f"with data. No weighting is required and none should be applied."
        ),
    }


def weighting_robustness(options, reference="boundary"):
    """Whether the best option survives every available weighting set.

    A conclusion that holds under all of them is strong. One that flips is a
    value judgement wearing a number, and should be labelled as such rather
    than presented as a result.
    """
    if not options or len(options) < 2:
        raise BurdenShiftError(
            "A robustness check needs at least two options."
        )

    winners = {}
    table = []
    for weighting in WEIGHTING_SETS:
        scores = []
        for index, option in enumerate(options):
            name = str(option.get("name") or f"Option {index + 1}")
            score = weighted_score(
                normalise(option["profile"], reference), weighting
            )["score"]
            scores.append((name, score))
        scores.sort(key=lambda item: item[1])
        winners[weighting] = scores[0][0]
        table.append({
            "weighting": weighting,
            "label": WEIGHTING_SETS[weighting]["label"],
            "winner": scores[0][0],
            "scores": {name: round(score, 6) for name, score in scores},
        })

    distinct = set(winners.values())
    return {
        "reference": reference,
        "by_weighting": table,
        "winners": winners,
        "robust": len(distinct) == 1,
        "distinct_winners": sorted(distinct),
        "note": (
            f"{next(iter(distinct))} wins under every weighting set here. "
            f"That conclusion does not depend on the value judgement."
            if len(distinct) == 1 else
            f"The winner changes with the weighting set "
            f"({', '.join(sorted(distinct))}). This is a value judgement "
            f"wearing a number, and presenting any one of them as the answer "
            f"would be presenting a choice as a finding."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_burden_insights(normalised, shift=None, robustness=None):
    """Plain-language findings, ordered by how much they should change a view."""
    insights = []

    if normalised["worst_category"]:
        worst = IMPACT_CATEGORIES[normalised["worst_category"]]
        insights.append(
            f"The furthest beyond its reference is {worst['label'].lower()} at "
            f"{normalised['worst_share']:.2f}× the "
            f"{normalised['reference_label'].lower()}. That is the category to "
            f"act on first, and it is not visible from any single-impact page."
        )

    if normalised["over_reference"]:
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"].lower()
            for key in normalised["over_reference"]
        )
        insights.append(
            f"Over the reference on {len(normalised['over_reference'])} "
            f"categor{'ies' if len(normalised['over_reference']) > 1 else 'y'}: "
            f"{names}."
        )

    for warning in coverage_report(normalised)["warnings"]:
        insights.append(warning)

    if shift:
        if shift["burden_shifted"]:
            worsened = ", ".join(
                IMPACT_CATEGORIES[key]["label"].lower()
                for key in shift["material_worsening"]
            )
            improved = ", ".join(
                IMPACT_CATEGORIES[key]["label"].lower()
                for key in shift["improved"][:3]
            )
            insights.append(
                f"This change improves {improved} and materially worsens "
                f"{worsened}. That is burden shifting, and it is reported here "
                f"whatever the weighted total does."
            )
            ratios = trade_off_ratios(shift)
            if ratios:
                top = ratios[0]
                insights.append(
                    f"The steepest exchange is {top['worsened_label'].lower()} "
                    f"for {top['improved_label'].lower()}: every unit of "
                    f"boundary share saved on the second costs "
                    f"{top['ratio']:.2f} on the first."
                )
        else:
            insights.append(
                "No material burden shifting across the categories with data. "
                "That is a weaker statement than it sounds if coverage is "
                "incomplete."
            )

        if shift["unnormalisable_worsening"]:
            names = ", ".join(
                IMPACT_CATEGORIES[key]["label"].lower()
                for key in shift["unnormalisable_worsening"]
            )
            insights.append(
                f"{names} got worse and cannot be normalised against a "
                f"boundary, so no weighted total will ever reflect it. Worth "
                f"reading in its own units before deciding."
            )

    if robustness:
        insights.append(robustness["note"])

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS burden_shift_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            reference TEXT NOT NULL,
            burden_shifted INTEGER NOT NULL,
            worst_category TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_burden_shift_assessments_user
        ON burden_shift_assessments (user_id)
        """
    )


def save_assessment(user_id, name, normalised, shift=None):
    """Persist a cross-impact assessment and return its row id."""
    if not user_id:
        raise BurdenShiftError("An assessment needs a user to belong to.")
    if not name or not str(name).strip():
        raise BurdenShiftError("An assessment needs a name.")

    payload = json.dumps({
        "reference": normalised["reference"],
        "categories": normalised["categories"],
        "over_reference": normalised["over_reference"],
        "unnormalisable": normalised["unnormalisable"],
        "missing": normalised["missing"],
        "shift": {
            "burden_shifted": shift["burden_shifted"],
            "improved": shift["improved"],
            "material_worsening": shift["material_worsening"],
        } if shift else None,
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO burden_shift_assessments
                (user_id, name, payload, reference, burden_shifted,
                 worst_category)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), str(name).strip(), payload,
                normalised["reference"],
                1 if (shift and shift["burden_shifted"]) else 0,
                normalised["worst_category"],
            ),
        )
        return int(cursor.lastrowid)


def get_assessments(user_id, limit=25):
    """Saved assessments for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, reference, burden_shifted,
                       worst_category, created_at
                FROM burden_shift_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved burden shift assessments")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "reference": row[3],
            "burden_shifted": bool(row[4]),
            "worst_category": row[5],
            "created_at": row[6],
        })
    return saved


def delete_assessment(user_id, assessment_id):
    """Delete one saved assessment. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM burden_shift_assessments "
                "WHERE id = ? AND user_id = ?",
                (assessment_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete assessment %s", assessment_id)
        return False


# ---------------------------------------------------------------------------
# Small accessors used by the page
# ---------------------------------------------------------------------------
def list_impacts():
    return list(IMPACT_CATEGORIES)


def get_impact(key):
    if key not in IMPACT_CATEGORIES:
        raise BurdenShiftError(f"{key!r} is not a known impact category.")
    return dict(IMPACT_CATEGORIES[key])


def list_weightings():
    return list(WEIGHTING_SETS)


def get_weighting(key):
    if key not in WEIGHTING_SETS:
        raise BurdenShiftError(f"{key!r} is not a known weighting set.")
    return dict(WEIGHTING_SETS[key])


def list_references():
    return list(REFERENCES)


def get_reference(key):
    if key not in REFERENCES:
        raise BurdenShiftError(f"{key!r} is not a known reference.")
    return dict(REFERENCES[key])
