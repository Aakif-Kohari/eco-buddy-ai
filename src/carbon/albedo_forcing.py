"""What a roof's colour does to the planet, not just to the room beneath it.

``src/lib/src.lib.uhi_planner.py`` already knows that a dark roof reflects 12% of the
sunlight that lands on it and a cool white roof reflects 70%. It uses that
difference to estimate how much hotter the surface gets. It stops there, and so
does the rest of the app: albedo is treated as a comfort variable.

It is also a climate variable, and the two do not always point the same way.

The sunlight a surface reflects back to space is energy that never enters the
climate system. Reflect more of it and you have done something with the same
sign as not emitting - measurable, immediate, and denominated in watts rather
than tonnes. This module does the conversion, so a roof colour can be compared
against a heat pump.

Why the equivalence needs a horizon attached
---------------------------------------------
An albedo change is a *sustained* forcing: the roof reflects the same extra
sunlight every year it stays white. A CO2 emission is a *pulse* whose forcing
decays as the carbon is taken up. Comparing them means integrating both to some
year and dividing, and the answer depends on which year you pick - not slightly,
but by a factor that grows with the horizon. A single kg-CO2e-per-square-metre
figure has already made that choice on the reader's behalf and hidden it. Here
the horizon is a required argument and appears in every result.

Why one coefficient will not do
--------------------------------
Forcing scales with the sunlight actually arriving, which varies by more than a
factor of two between Reykjavik and Riyadh, and with how much of the reflected
beam gets back out through the atmosphere, which depends on cloud. The same
white roof is worth roughly three times as much in the tropics as at sixty
degrees north. Published single-number coefficients are quoting a mid-latitude
clear-sky case without saying so.

The canopy result may be negative, and that is the point
---------------------------------------------------------
``src.environment.neighborhood_canopy_engine.py`` recommends planting on cooling and
sequestration grounds. Both are real. But a conifer stand over seasonal snow
replaces a surface reflecting 75% of incoming light with one reflecting about
20%, for however many months the snow lies. That darkening is a warming forcing,
and above some latitude it exceeds what the trees sequester. This module will
return that answer where the numbers give it, because a tool that can only ever
recommend planting is not measuring anything.

Local cooling and global forcing are never summed
--------------------------------------------------
A white roof cools the city and cools the planet. Irrigated turf cools the city
by evaporating water and does essentially nothing globally, while spending water
that ``src.environment.water_scarcity.py`` says is scarce. Reported as one "cooling benefit"
those two become indistinguishable, so they are reported as two results with
different units and no arithmetic between them.

Soiling is not a detail
------------------------
A cool roof loses a quarter of its initial albedo advantage in the first two or
three years to dust, biological growth and weathering. An offset claim built on
day-one reflectance overstates the lifetime effect by roughly that much. The
effective albedo here is a time-average over the horizon, with the recoating
interval as a parameter, so the claim degrades the way the roof does.

On the size of the numbers
---------------------------
A hundred square metres of roof taken from 0.12 to 0.70 at mid-latitude comes
out near twelve tonnes of CO2 on a hundred-year horizon. That is a large number
for a tin of paint and it deserves scepticism, so the derivation is kept in
separate, individually testable steps - surface forcing, top-of-atmosphere
forcing, globalisation by area, then CO2-equivalence - rather than collapsed
into one constant. It is also somewhat more conservative than the figures in the
cool-roof literature, which tend to assume clearer skies than the default here.

Where this connects to code already merged
-------------------------------------------
*   ``src/lib/src.lib.uhi_planner.py`` holds the local half of this and the same surface
    table. Nothing there is modified; this module carries its own values so the
    two can be compared rather than coupled.
*   ``src.environment.neighborhood_canopy_engine.py`` gains a check it currently lacks.
*   ``src.carbon.abatement_curve.py`` can price these interventions once they are in
    tonnes, which is the main reason for doing the conversion at all.
*   ``src.environment.climate_metrics.py`` handles well-mixed gases. A surface property is not a
    gas and its equivalence problem is a different one.

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


class AlbedoError(ValueError):
    """Raised when an albedo forcing calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Physical constants
#
# Each of these is a real measured quantity rather than a fitted coefficient,
# which is the only reason the derivation can be checked step by step.
# ---------------------------------------------------------------------------

# Surface area of the Earth, m^2. Forcing over a roof becomes a global forcing
# by dividing by this, which is where the very small numbers come from.
EARTH_SURFACE_AREA_M2 = 5.10e14

# Absolute global warming potential of CO2: the time-integrated radiative
# forcing, in W m^-2 yr, produced by emitting one kilogram of CO2 today. These
# already contain the carbon cycle response, which is why they are not linear
# in the horizon - and that non-linearity is exactly what makes the horizon
# choice matter for a sustained forcing.
AGWP_CO2_W_M2_YR_PER_KG = {
    20: 2.49e-14,
    50: 5.71e-14,
    100: 9.17e-14,
    500: 3.20e-13,
}

DEFAULT_HORIZON_YEARS = 100

# Fraction of shortwave radiation reflected at the surface that makes it back
# out through a cloud-free atmosphere. The rest is absorbed on the way up, and
# a surface reflection that is then absorbed by the air above it has not cooled
# anything.
CLEAR_SKY_UPWARD_TRANSMITTANCE = 0.76

# Cloud is the largest single reason a published cool-roof coefficient does not
# reproduce. A reflected beam under thick cloud is largely returned downward.
CLOUD_TRANSMITTANCE = 0.15


# ---------------------------------------------------------------------------
# Surfaces
#
# Albedo, how it ages, and what the surface does locally. The local column is
# carried so the module can show the local and global effects side by side and
# refuse to add them.
# ---------------------------------------------------------------------------
SURFACES = {
    "asphalt_new": {
        "label": "Asphalt, new",
        "albedo": 0.05,
        "aged_albedo": 0.12,
        "soiling_years": 3.0,
        "family": "paving",
        "evaporative": False,
        "local_temp_delta_c": 16.0,
        "note": "The darkest common outdoor surface, and unusual in that it "
                "gets lighter with age rather than darker as the binder "
                "weathers off.",
    },
    "asphalt_aged": {
        "label": "Asphalt, weathered",
        "albedo": 0.12,
        "aged_albedo": 0.12,
        "soiling_years": None,
        "family": "paving",
        "evaporative": False,
        "local_temp_delta_c": 14.5,
        "note": "Already at its long-run value, so nothing further is lost to "
                "soiling. Most road surface in a city is in this state.",
    },
    "concrete_paving": {
        "label": "Concrete paving",
        "albedo": 0.35,
        "aged_albedo": 0.25,
        "soiling_years": 4.0,
        "family": "paving",
        "evaporative": False,
        "local_temp_delta_c": 8.0,
        "note": "Bright when laid and noticeably duller within a few years. "
                "The gap between the two figures is the reason this module "
                "time-averages rather than using nameplate reflectance.",
    },
    "cool_paving": {
        "label": "Reflective (cool) paving",
        "albedo": 0.45,
        "aged_albedo": 0.33,
        "soiling_years": 3.0,
        "family": "paving",
        "evaporative": False,
        "local_temp_delta_c": 5.0,
        "note": "Effective on surface temperature and awkward at street level, "
                "because reflected shortwave arriving at a pedestrian is not a "
                "comfort improvement even where the air is cooler.",
    },
    "dark_roof": {
        "label": "Dark roof membrane",
        "albedo": 0.12,
        "aged_albedo": 0.10,
        "soiling_years": 5.0,
        "family": "roof",
        "evaporative": False,
        "local_temp_delta_c": 16.0,
        "note": "The default roof over most of the world's building stock and "
                "the baseline against which every cool-roof claim is made.",
    },
    "grey_roof": {
        "label": "Grey roof membrane",
        "albedo": 0.30,
        "aged_albedo": 0.24,
        "soiling_years": 4.0,
        "family": "roof",
        "evaporative": False,
        "local_temp_delta_c": 9.5,
        "note": "A middle case worth having, because much of the practical "
                "choice is between grey and white rather than black and white.",
    },
    "cool_white_roof": {
        "label": "Cool white roof",
        "albedo": 0.70,
        "aged_albedo": 0.55,
        "soiling_years": 2.5,
        "family": "roof",
        "evaporative": False,
        "local_temp_delta_c": 2.5,
        "note": "Loses roughly a fifth of its initial reflectance in the first "
                "two to three years. Recoating restores it, which is why the "
                "maintenance interval is a parameter here.",
    },
    "green_roof": {
        "label": "Green (vegetated) roof",
        "albedo": 0.22,
        "aged_albedo": 0.22,
        "soiling_years": None,
        "family": "roof",
        "evaporative": True,
        "local_temp_delta_c": 3.0,
        "note": "Cools locally by transpiring, not by reflecting. Its global "
                "albedo effect against a grey roof is slightly negative, which "
                "is not an argument against it but is worth stating.",
    },
    "solar_pv": {
        "label": "Solar PV array",
        "albedo": 0.08,
        "aged_albedo": 0.08,
        "soiling_years": None,
        "family": "roof",
        "evaporative": False,
        "local_temp_delta_c": 12.0,
        "note": "Dark by design, because a panel that reflected light would "
                "not work. The albedo cost is real, small against the "
                "generation benefit, and routinely left out of the sum.",
    },
    "bare_soil": {
        "label": "Bare soil",
        "albedo": 0.17,
        "aged_albedo": 0.17,
        "soiling_years": None,
        "family": "land",
        "evaporative": False,
        "local_temp_delta_c": 6.0,
        "note": "Varies widely with moisture and mineralogy; a dry sandy soil "
                "can reach 0.35. Treated as a single value here because the "
                "module's purpose is the comparison, not the soil survey.",
    },
    "grassland": {
        "label": "Grassland",
        "albedo": 0.23,
        "aged_albedo": 0.23,
        "soiling_years": None,
        "family": "land",
        "evaporative": True,
        "local_temp_delta_c": -1.5,
        "note": "Cools mostly by evaporating, which requires src.environment.water. Where that "
                "water is irrigated the local cooling has a cost that belongs "
                "in a different module.",
    },
    "cropland": {
        "label": "Cropland",
        "albedo": 0.20,
        "aged_albedo": 0.20,
        "soiling_years": None,
        "family": "land",
        "evaporative": True,
        "local_temp_delta_c": -1.0,
        "note": "Seasonally variable between bare soil and full canopy. The "
                "annual mean is used, and the seasonality matters most where "
                "the bare period coincides with snow.",
    },
    "deciduous_forest": {
        "label": "Deciduous forest",
        "albedo": 0.16,
        "aged_albedo": 0.16,
        "soiling_years": None,
        "family": "forest",
        "evaporative": True,
        "local_temp_delta_c": -4.0,
        "note": "Bare in winter, so it masks lying snow less completely than "
                "conifer does. Where snow is seasonal this is the difference "
                "between a small penalty and a large one.",
    },
    "conifer_forest": {
        "label": "Conifer forest",
        "albedo": 0.09,
        "aged_albedo": 0.09,
        "soiling_years": None,
        "family": "forest",
        "evaporative": True,
        "local_temp_delta_c": -4.5,
        "note": "The darkest vegetated surface and evergreen, so it hides snow "
                "all winter. This single fact is why high-latitude afforestation "
                "can be net warming.",
    },
    "fresh_snow": {
        "label": "Fresh snow",
        "albedo": 0.80,
        "aged_albedo": 0.80,
        "soiling_years": None,
        "family": "cryosphere",
        "evaporative": False,
        "local_temp_delta_c": -8.0,
        "note": "The brightest natural surface on Earth. Present as the "
                "reference for what canopy replaces, not as something anyone "
                "chooses to install.",
    },
    "water": {
        "label": "Open water",
        "albedo": 0.06,
        "aged_albedo": 0.06,
        "soiling_years": None,
        "family": "water",
        "evaporative": True,
        "local_temp_delta_c": -3.0,
        "note": "Very dark at high sun and much brighter at low angles. The "
                "single value here is a high-sun approximation and should not "
                "be used near the poles.",
    },
}


# ---------------------------------------------------------------------------
# Latitude bands
#
# Annual mean downward shortwave at the surface, the fraction of the year with
# lying snow, and typical cloud cover. Together these are why the same roof is
# worth three times as much in one place as another.
# ---------------------------------------------------------------------------
LATITUDE_BANDS = {
    "equatorial": {
        "label": "Equatorial (0-15 deg)",
        "centre_latitude": 7.5,
        "insolation_w_m2": 235.0,
        "snow_fraction": 0.0,
        "cloud_fraction": 0.62,
        "note": "The most sunlight and the most cloud. The two partly cancel, "
                "which is why the cloud term cannot be dropped even here.",
    },
    "tropical": {
        "label": "Tropical (15-30 deg)",
        "centre_latitude": 22.5,
        "insolation_w_m2": 245.0,
        "snow_fraction": 0.0,
        "cloud_fraction": 0.44,
        "note": "The subtropical dry belt: high sun and thin cloud together, "
                "so this band, not the equator, is where a reflective surface "
                "does the most good.",
    },
    "subtropical": {
        "label": "Subtropical (30-40 deg)",
        "centre_latitude": 35.0,
        "insolation_w_m2": 210.0,
        "snow_fraction": 0.02,
        "cloud_fraction": 0.50,
        "note": "Where most of the cool-roof literature was measured, which is "
                "worth knowing before applying its coefficients elsewhere.",
    },
    "temperate": {
        "label": "Temperate (40-50 deg)",
        "centre_latitude": 45.0,
        "insolation_w_m2": 172.0,
        "snow_fraction": 0.12,
        "cloud_fraction": 0.62,
        "note": "Enough winter snow for the canopy question to arise and not "
                "enough to settle it. The crossover usually sits just poleward "
                "of here.",
    },
    "cool_temperate": {
        "label": "Cool temperate (50-60 deg)",
        "centre_latitude": 55.0,
        "insolation_w_m2": 132.0,
        "snow_fraction": 0.28,
        "cloud_fraction": 0.68,
        "note": "Weak sun, persistent cloud and real snow cover. A white roof "
                "here returns roughly a third of what the same roof returns in "
                "the subtropics.",
    },
    "boreal": {
        "label": "Boreal (60-70 deg)",
        "centre_latitude": 65.0,
        "insolation_w_m2": 97.0,
        "snow_fraction": 0.48,
        "cloud_fraction": 0.70,
        "note": "Half the year under snow. This is where planting a conifer "
                "stand can warm rather than cool, and where the module is most "
                "likely to contradict the rest of the app.",
    },
    "arctic": {
        "label": "Arctic (70+ deg)",
        "centre_latitude": 75.0,
        "insolation_w_m2": 68.0,
        "snow_fraction": 0.70,
        "cloud_fraction": 0.72,
        "note": "Very little sunlight and almost permanent snow. The albedo "
                "leverage per unit of sunlight is the highest anywhere and "
                "there is very little sunlight to lever.",
    },
}

# Albedo of a snow-covered surface once a canopy is standing over it. Snow on
# the ground under a conifer stand is largely invisible from above, and this
# single number carries most of the high-latitude afforestation penalty.
CANOPY_MASKED_SNOW_ALBEDO = {
    "conifer_forest": 0.21,
    "deciduous_forest": 0.42,
}

# What an open, treeless surface looks like when snow is lying on it.
OPEN_SNOW_ALBEDO = 0.72

# How much carbon a forest actually accumulates, by latitude, and how fast.
#
# Two things have to be right here or the canopy comparison is worthless.
#
# First, growth saturates. A stand does not keep taking up carbon at its
# twenty-year rate for a century; it approaches a stock and stops. Multiplying
# an early-growth rate by a hundred years - the obvious thing to do, and what a
# flat rate amounts to - overstates a boreal stand by a factor of four and
# buries the albedo penalty entirely.
#
# Second, the stock is strongly latitude-dependent, and in the direction that
# matters: the places where the albedo penalty is largest are the places where
# forests hold the least carbon and take longest to get there. Using one global
# rate would cancel exactly the effect this module exists to find.
#
# Asymptotic stock is above- and below-ground biomass expressed as tCO2 per
# hectare; the time constant is the e-folding time towards it.
FOREST_CARBON_STOCK = {
    "equatorial": {"asymptote_t_co2_ha": 900.0, "growth_tau_years": 40.0},
    "tropical": {"asymptote_t_co2_ha": 700.0, "growth_tau_years": 40.0},
    "subtropical": {"asymptote_t_co2_ha": 550.0, "growth_tau_years": 45.0},
    "temperate": {"asymptote_t_co2_ha": 480.0, "growth_tau_years": 50.0},
    "cool_temperate": {"asymptote_t_co2_ha": 380.0, "growth_tau_years": 60.0},
    "boreal": {"asymptote_t_co2_ha": 240.0, "growth_tau_years": 80.0},
    "arctic": {"asymptote_t_co2_ha": 90.0, "growth_tau_years": 100.0},
}

# Species adjustment on the stock above. Small, because at this resolution
# latitude dominates species by a wide margin.
FOREST_STOCK_SPECIES_FACTOR = {
    "conifer_forest": 1.00,
    "deciduous_forest": 0.95,
}

SQUARE_METRES_PER_HECTARE = 10000.0


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def list_surfaces(family=None):
    """Surface keys, optionally filtered to one family."""
    if family is None:
        return sorted(SURFACES)
    return sorted(k for k, v in SURFACES.items() if v["family"] == family)


def list_surface_families():
    """The distinct surface families present in the table."""
    return sorted({spec["family"] for spec in SURFACES.values()})


def get_surface(key):
    """One surface specification."""
    try:
        return SURFACES[key]
    except KeyError:
        raise AlbedoError(
            f"Unknown surface '{key}'. Known surfaces: "
            f"{', '.join(list_surfaces())}."
        )


def list_latitude_bands():
    """Latitude band keys, equator first."""
    return sorted(LATITUDE_BANDS, key=lambda k: LATITUDE_BANDS[k]["centre_latitude"])


def get_latitude_band(key):
    """One latitude band specification."""
    try:
        return LATITUDE_BANDS[key]
    except KeyError:
        raise AlbedoError(
            f"Unknown latitude band '{key}'. Known bands: "
            f"{', '.join(list_latitude_bands())}."
        )


def list_horizons():
    """Horizons for which a CO2 equivalence can be computed."""
    return sorted(AGWP_CO2_W_M2_YR_PER_KG)


# ---------------------------------------------------------------------------
# Step 1: forcing at the surface, and what escapes
# ---------------------------------------------------------------------------
def upward_transmittance(cloud_fraction):
    """Fraction of surface-reflected shortwave that reaches space.

    A linear mix between the clear-sky and overcast cases. Crude, and the
    honest alternative is a radiative transfer model that does not belong in
    this app; what matters is that the term exists and is visible, because
    leaving it out inflates every result by a factor of two.
    """
    if not 0.0 <= cloud_fraction <= 1.0:
        raise AlbedoError("Cloud fraction must be between 0 and 1.")
    return (
        (1.0 - cloud_fraction) * CLEAR_SKY_UPWARD_TRANSMITTANCE
        + cloud_fraction * CLOUD_TRANSMITTANCE
    )


def local_radiative_forcing(delta_albedo, latitude_band, cloud_fraction=None):
    """Top-of-atmosphere forcing per square metre of changed surface, W/m^2.

    Negative for a brightening, which is the cooling direction and matches the
    sign convention used for forcings everywhere else.
    """
    if not -1.0 <= delta_albedo <= 1.0:
        raise AlbedoError("An albedo change must lie between -1 and 1.")

    band = get_latitude_band(latitude_band)
    if cloud_fraction is None:
        cloud_fraction = band["cloud_fraction"]

    transmittance = upward_transmittance(cloud_fraction)
    return -band["insolation_w_m2"] * delta_albedo * transmittance


def globalise(local_forcing_w_m2, area_m2):
    """Spread a patch forcing over the whole planet, W/m^2.

    The division by the Earth's area is what makes these numbers look
    negligible. They are negligible per roof; the point of the CO2 conversion
    is that so is one person's annual src.carbon.emissions.
    """
    if area_m2 <= 0:
        raise AlbedoError("Area must be positive.")
    return local_forcing_w_m2 * area_m2 / EARTH_SURFACE_AREA_M2


# ---------------------------------------------------------------------------
# Step 2: CO2 equivalence, with the horizon in the open
# ---------------------------------------------------------------------------
def agwp_co2(horizon_years):
    """Absolute GWP of CO2 at a horizon, interpolated where necessary."""
    if horizon_years <= 0:
        raise AlbedoError("A time horizon must be positive.")

    known = list_horizons()
    if horizon_years in AGWP_CO2_W_M2_YR_PER_KG:
        return AGWP_CO2_W_M2_YR_PER_KG[horizon_years]
    if horizon_years < known[0] or horizon_years > known[-1]:
        raise AlbedoError(
            f"Horizon must be between {known[0]} and {known[-1]} years; the "
            f"carbon cycle response outside that range is not tabulated here."
        )

    lower = max(h for h in known if h < horizon_years)
    upper = min(h for h in known if h > horizon_years)
    span = upper - lower
    weight = (horizon_years - lower) / span
    return (
        AGWP_CO2_W_M2_YR_PER_KG[lower] * (1.0 - weight)
        + AGWP_CO2_W_M2_YR_PER_KG[upper] * weight
    )


def co2_equivalent(global_forcing_w_m2, horizon_years=DEFAULT_HORIZON_YEARS):
    """Kilograms of CO2 whose forcing over the horizon matches a sustained one.

    A sustained forcing integrates linearly with the horizon. A CO2 pulse does
    not, because the carbon is progressively taken up. So the equivalent mass
    grows with the horizon you choose, and any module reporting one number has
    quietly picked a side of that argument. Negative means an offset.
    """
    integrated = global_forcing_w_m2 * horizon_years
    return integrated / agwp_co2(horizon_years)


# ---------------------------------------------------------------------------
# Soiling
# ---------------------------------------------------------------------------
def effective_albedo(surface, horizon_years=DEFAULT_HORIZON_YEARS,
                     recoat_interval_years=None):
    """Time-averaged albedo over a period, allowing for soiling and recoating.

    Reflectance decays exponentially towards an aged value with a characteristic
    time of a few years. Recoating resets it. Using day-one reflectance instead
    overstates a white roof by roughly a fifth over its life, which is the
    difference between an honest claim and a marketing one.
    """
    spec = get_surface(surface)
    initial = spec["albedo"]
    aged = spec["aged_albedo"]
    tau = spec["soiling_years"]

    if horizon_years <= 0:
        raise AlbedoError("A time horizon must be positive.")
    if tau is None or abs(initial - aged) < 1e-12:
        return {
            "surface": surface,
            "initial_albedo": initial,
            "aged_albedo": aged,
            "effective_albedo": initial,
            "soils": False,
            "recoat_interval_years": None,
            "note": "This surface has no meaningful soiling decay, so its "
                    "nameplate reflectance is also its long-run one.",
        }

    period = recoat_interval_years if recoat_interval_years else horizon_years
    period = min(period, horizon_years)
    if period <= 0:
        raise AlbedoError("A recoating interval must be positive.")

    # Mean of aged + (initial - aged) * exp(-t / tau) over one cycle.
    decay = (initial - aged) * (tau / period) * (1.0 - math.exp(-period / tau))
    mean = aged + decay

    return {
        "surface": surface,
        "initial_albedo": initial,
        "aged_albedo": aged,
        "effective_albedo": mean,
        "soils": True,
        "recoat_interval_years": recoat_interval_years,
        "fraction_of_nameplate": mean / initial if initial else 0.0,
        "note": (
            f"Reflectance decays towards {aged:.2f} with a time constant of "
            f"{tau:.1f} years. Averaged over "
            f"{'a ' + str(recoat_interval_years) + '-year recoating cycle' if recoat_interval_years else str(int(horizon_years)) + ' years with no recoating'}"
            f", the effective value is {mean:.3f} rather than the {initial:.2f} "
            f"on the datasheet."
        ),
    }


# ---------------------------------------------------------------------------
# The main calculation
# ---------------------------------------------------------------------------
def surface_change(from_surface, to_surface, area_m2, latitude_band,
                   horizon_years=DEFAULT_HORIZON_YEARS,
                   cloud_fraction=None, recoat_interval_years=None,
                   apply_soiling=True):
    """Full forcing and CO2-equivalence result for changing one surface to another.

    Every intermediate step is returned, because the headline number is large
    enough that a reader is entitled to check where it came from.
    """
    if area_m2 <= 0:
        raise AlbedoError("Area must be positive.")

    from_spec = get_surface(from_surface)
    to_spec = get_surface(to_surface)
    band = get_latitude_band(latitude_band)

    if apply_soiling:
        from_effective = effective_albedo(
            from_surface, horizon_years, recoat_interval_years
        )
        to_effective = effective_albedo(
            to_surface, horizon_years, recoat_interval_years
        )
        alpha_from = from_effective["effective_albedo"]
        alpha_to = to_effective["effective_albedo"]
    else:
        from_effective = None
        to_effective = None
        alpha_from = from_spec["albedo"]
        alpha_to = to_spec["albedo"]

    delta = alpha_to - alpha_from

    if cloud_fraction is None:
        cloud_fraction = band["cloud_fraction"]

    local = local_radiative_forcing(delta, latitude_band, cloud_fraction)
    global_forcing = globalise(local, area_m2)
    co2_kg = co2_equivalent(global_forcing, horizon_years)

    return {
        "from_surface": from_surface,
        "from_label": from_spec["label"],
        "to_surface": to_surface,
        "to_label": to_spec["label"],
        "area_m2": area_m2,
        "latitude_band": latitude_band,
        "latitude_label": band["label"],
        "horizon_years": horizon_years,
        "cloud_fraction": cloud_fraction,
        "insolation_w_m2": band["insolation_w_m2"],
        "upward_transmittance": upward_transmittance(cloud_fraction),
        "albedo_from": alpha_from,
        "albedo_to": alpha_to,
        "delta_albedo": delta,
        "soiling_applied": apply_soiling,
        "soiling_from": from_effective,
        "soiling_to": to_effective,
        "local_forcing_w_m2": local,
        "global_forcing_w_m2": global_forcing,
        "co2_equivalent_kg": co2_kg,
        "co2_equivalent_kg_per_m2": co2_kg / area_m2,
        "is_offset": co2_kg < 0,
        "local_temp_delta_c": to_spec["local_temp_delta_c"]
                              - from_spec["local_temp_delta_c"],
        "local_is_evaporative": to_spec["evaporative"],
        "separation_note": (
            "The surface temperature change and the CO2 equivalence are two "
            "different quantities in two different units and are never added. "
            "One is about the street; the other is about the planet."
        ),
    }


def horizon_sensitivity(from_surface, to_surface, area_m2, latitude_band,
                        horizons=None, **kwargs):
    """The same change evaluated at several horizons.

    Presented as a table rather than a single row because the spread between
    the twenty-year and hundred-year answers is the most important thing a
    reader can know about this metric.
    """
    horizons = horizons or list_horizons()
    rows = []
    for horizon in horizons:
        result = surface_change(
            from_surface, to_surface, area_m2, latitude_band,
            horizon_years=horizon, **kwargs
        )
        rows.append({
            "horizon_years": horizon,
            "co2_equivalent_kg": result["co2_equivalent_kg"],
            "co2_equivalent_kg_per_m2": result["co2_equivalent_kg_per_m2"],
        })
    return rows


def latitude_sensitivity(from_surface, to_surface, area_m2,
                         horizon_years=DEFAULT_HORIZON_YEARS, **kwargs):
    """The same change evaluated in every latitude band."""
    rows = []
    for band_key in list_latitude_bands():
        result = surface_change(
            from_surface, to_surface, area_m2, band_key,
            horizon_years=horizon_years, **kwargs
        )
        band = get_latitude_band(band_key)
        rows.append({
            "latitude_band": band_key,
            "label": band["label"],
            "centre_latitude": band["centre_latitude"],
            "insolation_w_m2": band["insolation_w_m2"],
            "co2_equivalent_kg": result["co2_equivalent_kg"],
        })
    return rows


# ---------------------------------------------------------------------------
# The canopy question
# ---------------------------------------------------------------------------
def sequestration_stock(latitude_band, years, forest_type,
                        asymptote_t_co2_ha=None, growth_tau_years=None):
    """Carbon a stand has accumulated after some years, tCO2 per hectare.

    Saturating rather than linear. The distinction is not academic: at a flat
    early-growth rate a boreal stand appears to bank four times what it can
    physically hold, which is enough on its own to hide the albedo penalty.
    """
    if years < 0:
        raise AlbedoError("Growth period cannot be negative.")
    if latitude_band not in FOREST_CARBON_STOCK:
        raise AlbedoError(f"No forest carbon stock modelled for '{latitude_band}'.")

    stock = FOREST_CARBON_STOCK[latitude_band]
    asymptote = (
        asymptote_t_co2_ha if asymptote_t_co2_ha is not None
        else stock["asymptote_t_co2_ha"]
        * FOREST_STOCK_SPECIES_FACTOR.get(forest_type, 1.0)
    )
    tau = growth_tau_years or stock["growth_tau_years"]
    if tau <= 0:
        raise AlbedoError("Growth time constant must be positive.")

    accumulated = asymptote * (1.0 - math.exp(-years / tau))
    return {
        "asymptote_t_co2_ha": asymptote,
        "growth_tau_years": tau,
        "years": years,
        "accumulated_t_co2_ha": accumulated,
        "share_of_asymptote": accumulated / asymptote if asymptote else 0.0,
        "mean_rate_t_co2_ha_yr": accumulated / years if years > 0 else 0.0,
    }


def canopy_albedo_penalty(forest_type, area_m2, latitude_band,
                          horizon_years=DEFAULT_HORIZON_YEARS,
                          open_surface="grassland", cloud_fraction=None,
                          asymptote_t_co2_ha=None, growth_tau_years=None,
                          growth_years=None):
    """Net effect of planting: sequestration against the darkening it causes.

    The snow term does the work. An open field under snow reflects around 0.72;
    the same ground under a conifer stand reflects around 0.21, because the snow
    is no longer visible from above. Where snow lies for a substantial part of
    the year that darkening is a large sustained forcing, and it can be larger
    than what the trees take up.

    A negative ``net_co2_kg`` means planting is a net benefit. A positive one
    means it is not, and the module says so.
    """
    if forest_type not in CANOPY_MASKED_SNOW_ALBEDO:
        raise AlbedoError(
            f"Canopy albedo is only modelled for "
            f"{', '.join(sorted(CANOPY_MASKED_SNOW_ALBEDO))}."
        )
    if area_m2 <= 0:
        raise AlbedoError("Area must be positive.")

    band = get_latitude_band(latitude_band)
    snow_fraction = band["snow_fraction"]
    if cloud_fraction is None:
        cloud_fraction = band["cloud_fraction"]

    open_spec = get_surface(open_surface)
    forest_spec = get_surface(forest_type)

    # Annual mean albedo of each state, weighted by how much of the year the
    # ground is under snow.
    open_albedo = (
        snow_fraction * OPEN_SNOW_ALBEDO
        + (1.0 - snow_fraction) * open_spec["albedo"]
    )
    forest_albedo = (
        snow_fraction * CANOPY_MASKED_SNOW_ALBEDO[forest_type]
        + (1.0 - snow_fraction) * forest_spec["albedo"]
    )
    delta = forest_albedo - open_albedo

    local = local_radiative_forcing(delta, latitude_band, cloud_fraction)
    global_forcing = globalise(local, area_m2)
    albedo_co2_kg = co2_equivalent(global_forcing, horizon_years)

    years = growth_years if growth_years is not None else horizon_years
    growth = sequestration_stock(
        latitude_band, years, forest_type,
        asymptote_t_co2_ha=asymptote_t_co2_ha,
        growth_tau_years=growth_tau_years,
    )

    hectares = area_m2 / SQUARE_METRES_PER_HECTARE
    sequestered_kg = -growth["accumulated_t_co2_ha"] * 1000.0 * hectares

    net = albedo_co2_kg + sequestered_kg

    return {
        "forest_type": forest_type,
        "forest_label": forest_spec["label"],
        "open_surface": open_surface,
        "open_label": open_spec["label"],
        "area_m2": area_m2,
        "hectares": hectares,
        "latitude_band": latitude_band,
        "latitude_label": band["label"],
        "snow_fraction": snow_fraction,
        "horizon_years": horizon_years,
        "growth_years": years,
        "open_annual_albedo": open_albedo,
        "forest_annual_albedo": forest_albedo,
        "delta_albedo": delta,
        "albedo_co2_kg": albedo_co2_kg,
        "sequestration_co2_kg": sequestered_kg,
        "growth": growth,
        "sequestration_rate_t_ha_yr": growth["mean_rate_t_co2_ha_yr"],
        "net_co2_kg": net,
        "planting_is_net_beneficial": net < 0,
        "albedo_offsets_share": (
            min(1.0, albedo_co2_kg / abs(sequestered_kg))
            if sequestered_kg < 0 and albedo_co2_kg > 0 else 0.0
        ),
        "note": (
            "Snow lies here for {:.0%} of the year. Under it the open ground "
            "reflects {:.2f} and the same ground beneath canopy reflects {:.2f}, "
            "so the planting darkens the surface for that part of the year."
        ).format(
            snow_fraction, OPEN_SNOW_ALBEDO,
            CANOPY_MASKED_SNOW_ALBEDO[forest_type],
        ) if snow_fraction > 0.01 else (
            "No meaningful snow cover here, so the albedo penalty is only the "
            "difference between canopy and open vegetation and is small."
        ),
    }


def canopy_crossover(forest_type, area_m2=SQUARE_METRES_PER_HECTARE,
                     horizon_years=DEFAULT_HORIZON_YEARS, **kwargs):
    """Where planting stops paying, band by band.

    Returns every band with its net result, and identifies the first band going
    poleward at which the sign flips. That band, not a global average, is the
    useful output.
    """
    rows = []
    crossover_band = None
    for band_key in list_latitude_bands():
        result = canopy_albedo_penalty(
            forest_type, area_m2, band_key,
            horizon_years=horizon_years, **kwargs
        )
        rows.append({
            "latitude_band": band_key,
            "label": result["latitude_label"],
            "centre_latitude": get_latitude_band(band_key)["centre_latitude"],
            "snow_fraction": result["snow_fraction"],
            "albedo_co2_kg": result["albedo_co2_kg"],
            "sequestration_co2_kg": result["sequestration_co2_kg"],
            "net_co2_kg": result["net_co2_kg"],
            "beneficial": result["planting_is_net_beneficial"],
        })
        if crossover_band is None and not result["planting_is_net_beneficial"]:
            crossover_band = band_key

    return {
        "forest_type": forest_type,
        "horizon_years": horizon_years,
        "bands": rows,
        "crossover_band": crossover_band,
        "crossover_latitude": (
            get_latitude_band(crossover_band)["centre_latitude"]
            if crossover_band else None
        ),
        "note": (
            "Planting remains net beneficial in every band modelled here."
            if crossover_band is None else
            "Poleward of roughly {:.0f} degrees the albedo penalty exceeds the "
            "sequestration on this horizon, so planting this species there is "
            "net warming.".format(
                get_latitude_band(crossover_band)["centre_latitude"]
            )
        ),
    }


# ---------------------------------------------------------------------------
# Solar panels
# ---------------------------------------------------------------------------
def solar_panel_net(area_m2, latitude_band, annual_yield_kwh_per_m2,
                    grid_intensity_kg_per_kwh, lifetime_years=25.0,
                    replaced_surface="grey_roof",
                    horizon_years=DEFAULT_HORIZON_YEARS, cloud_fraction=None):
    """Generation benefit of a PV array net of the darkening it causes.

    The albedo term is small next to the generation, which is the expected
    result and worth computing anyway - a module that only ever nets off the
    terms that help is not doing lifecycle accounting.
    """
    if annual_yield_kwh_per_m2 < 0 or grid_intensity_kg_per_kwh < 0:
        raise AlbedoError("Yield and grid intensity cannot be negative.")
    if lifetime_years <= 0:
        raise AlbedoError("Panel lifetime must be positive.")

    albedo_result = surface_change(
        replaced_surface, "solar_pv", area_m2, latitude_band,
        horizon_years=horizon_years, cloud_fraction=cloud_fraction,
    )

    displaced_kg = -(
        annual_yield_kwh_per_m2 * area_m2
        * grid_intensity_kg_per_kwh * lifetime_years
    )
    albedo_kg = albedo_result["co2_equivalent_kg"]
    net = displaced_kg + albedo_kg

    return {
        "area_m2": area_m2,
        "latitude_band": latitude_band,
        "replaced_surface": replaced_surface,
        "lifetime_years": lifetime_years,
        "horizon_years": horizon_years,
        "delta_albedo": albedo_result["delta_albedo"],
        "albedo_co2_kg": albedo_kg,
        "displaced_co2_kg": displaced_kg,
        "net_co2_kg": net,
        "albedo_penalty_share": (
            albedo_kg / abs(displaced_kg) if displaced_kg < 0 else 0.0
        ),
        "note": (
            "The panel is darker than what it covers, so it carries a warming "
            "term. It is {:.1%} of the generation benefit here - small, real, "
            "and normally left out entirely."
        ).format(albedo_kg / abs(displaced_kg) if displaced_kg < 0 else 0.0),
    }


# ---------------------------------------------------------------------------
# Local versus global, kept apart
# ---------------------------------------------------------------------------
def local_versus_global(result):
    """The two effects side by side, with an explicit refusal to add them."""
    return {
        "global_co2_equivalent_kg": result["co2_equivalent_kg"],
        "local_surface_temp_delta_c": result["local_temp_delta_c"],
        "local_mechanism": (
            "evaporative" if result["local_is_evaporative"] else "reflective"
        ),
        "comparable": False,
        "explanation": (
            "A reflective surface cools the street and the planet by the same "
            "mechanism. An evaporative one cools the street by moving water "
            "into the air and does almost nothing globally, while spending "
            "src.environment.water. Both are worth having and they are not the same benefit, "
            "so there is no combined figure here."
        ) if result["local_is_evaporative"] else (
            "Both effects here come from reflection, so they move together - "
            "but they are still different quantities in different units and "
            "the module will not sum them."
        ),
    }


def abatement_cost(result, cost_per_m2, maintenance_cost_per_m2_yr=0.0,
                   recoat_interval_years=None):
    """Cost per tonne of CO2e, so this can sit in the existing abatement curve.

    Returns ``None`` for the cost figure where the intervention is net warming,
    because a cost per tonne abated is meaningless when nothing is abated.
    """
    if cost_per_m2 < 0:
        raise AlbedoError("Cost cannot be negative.")

    horizon = result["horizon_years"]
    recoats = 0
    if recoat_interval_years:
        recoats = max(0, int(horizon // recoat_interval_years) - 1)

    capital = cost_per_m2 * result["area_m2"] * (1 + recoats)
    maintenance = maintenance_cost_per_m2_yr * result["area_m2"] * horizon
    total = capital + maintenance

    tonnes_abated = -result["co2_equivalent_kg"] / 1000.0

    return {
        "capital_cost": capital,
        "maintenance_cost": maintenance,
        "total_cost": total,
        "recoats": recoats,
        "tonnes_abated": tonnes_abated,
        "cost_per_tonne": (
            total / tonnes_abated if tonnes_abated > 0 else None
        ),
        "is_abatement": tonnes_abated > 0,
        "note": (
            "Net warming, so there is no cost per tonne abated to src.reporting.report."
            if tonnes_abated <= 0 else
            "Comparable directly against the measures in src.carbon.abatement_curve.py."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_albedo_insights(result):
    """Plain sentences about a surface change result."""
    insights = []
    co2 = result["co2_equivalent_kg"]

    if result["is_offset"]:
        insights.append(
            f"Brightening {result['area_m2']:,.0f} m² from "
            f"{result['albedo_from']:.2f} to {result['albedo_to']:.2f} is "
            f"equivalent to avoiding about {abs(co2) / 1000:,.1f} tonnes of "
            f"CO2 on a {result['horizon_years']:.0f}-year horizon."
        )
    else:
        insights.append(
            f"This change darkens the surface, so it is equivalent to emitting "
            f"about {co2 / 1000:,.1f} tonnes of CO2 on a "
            f"{result['horizon_years']:.0f}-year horizon."
        )

    insights.append(
        f"That figure is horizon-dependent by construction. The albedo change "
        f"forces continuously; a CO2 pulse decays. Halve the horizon and the "
        f"equivalent mass falls, not because the roof does less but because "
        f"the comparison changed."
    )

    if result["soiling_applied"] and result["soiling_to"] \
            and result["soiling_to"]["soils"]:
        soiling = result["soiling_to"]
        insights.append(
            f"The new surface is rated at {soiling['initial_albedo']:.2f} and "
            f"averages {soiling['effective_albedo']:.3f} once soiling is "
            f"allowed for - {soiling['fraction_of_nameplate']:.0%} of the "
            f"nameplate figure. Claims built on day-one reflectance are that "
            f"much too high."
        )

    transmittance = result["upward_transmittance"]
    insights.append(
        f"Only {transmittance:.0%} of what this surface reflects reaches space "
        f"at {result['cloud_fraction']:.0%} cloud cover. The rest is reabsorbed "
        f"on the way up and does no cooling at all."
    )

    band = get_latitude_band(result["latitude_band"])
    brightest = max(
        LATITUDE_BANDS.values(), key=lambda b: b["insolation_w_m2"]
    )
    if band["insolation_w_m2"] < brightest["insolation_w_m2"] * 0.8:
        insights.append(
            f"At {band['label'].lower()} there is "
            f"{band['insolation_w_m2'] / brightest['insolation_w_m2']:.0%} of "
            f"the sunlight available in the {brightest['label'].lower()} band, "
            f"so the same intervention returns proportionally less here."
        )

    if result["local_is_evaporative"]:
        insights.append(
            "The new surface cools locally mostly by evaporating water rather "
            "than by reflecting light. That is a real benefit to the street "
            "and a very small one to the climate, and it has a water cost."
        )

    insights.append(
        f"Locally the surface runs about "
        f"{abs(result['local_temp_delta_c']):.1f}°C "
        f"{'cooler' if result['local_temp_delta_c'] < 0 else 'warmer'}. "
        f"That number and the tonnage above are different quantities and are "
        f"not added together anywhere in this module."
    )

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS albedo_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            co2_equivalent_kg REAL NOT NULL,
            area_m2 REAL NOT NULL,
            horizon_years REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_albedo_assessments_user
        ON albedo_assessments (user_id)
        """
    )


def save_assessment(user_id, name, result):
    """Persist a surface change result and return its row id."""
    if not user_id:
        raise AlbedoError("An assessment needs a user to belong to.")
    if not name or not name.strip():
        raise AlbedoError("An assessment needs a name.")

    payload = json.dumps({
        "from_surface": result["from_surface"],
        "to_surface": result["to_surface"],
        "latitude_band": result["latitude_band"],
        "delta_albedo": result["delta_albedo"],
        "cloud_fraction": result["cloud_fraction"],
        "local_forcing_w_m2": result["local_forcing_w_m2"],
        "global_forcing_w_m2": result["global_forcing_w_m2"],
        "soiling_applied": result["soiling_applied"],
        "local_temp_delta_c": result["local_temp_delta_c"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO albedo_assessments
                (user_id, name, payload, co2_equivalent_kg, area_m2,
                 horizon_years)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(result["co2_equivalent_kg"]),
                float(result["area_m2"]),
                float(result["horizon_years"]),
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
                SELECT id, name, payload, co2_equivalent_kg, area_m2,
                       horizon_years, created_at
                FROM albedo_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved albedo assessments")
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
            "co2_equivalent_kg": row[3],
            "area_m2": row[4],
            "horizon_years": row[5],
            "created_at": row[6],
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
                "DELETE FROM albedo_assessments WHERE id = ? AND user_id = ?",
                (assessment_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete albedo assessment %s", assessment_id)
        return False
