"""Weibull reliability and circular economy decision engine for household appliances.
"""

import math
from src.lifestyle.appliance_circularity_types import (
    ApplianceAssessmentInputs,
    CircularityEvaluationResult,
    ApplianceCategory,
    FailureSeverity,
)


class ApplianceCircularityEngine:
    """Evaluates repair vs replacement decisions using Weibull hazard distributions and embodied LCA."""

    # Weibull parameters (eta = characteristic life in years, beta = shape parameter)
    WEIBULL_SPECS = {
        ApplianceCategory.WASHING_MACHINE: {"eta": 11.0, "beta": 2.6, "embodied_kg_co2": 260.0},
        ApplianceCategory.REFRIGERATOR: {"eta": 14.0, "beta": 2.8, "embodied_kg_co2": 380.0},
        ApplianceCategory.DISHWASHER: {"eta": 10.0, "beta": 2.4, "embodied_kg_co2": 210.0},
        ApplianceCategory.HEAT_PUMP_AC: {"eta": 15.0, "beta": 3.0, "embodied_kg_co2": 520.0},
        ApplianceCategory.LAPTOP_ELECTRONICS: {"eta": 5.5, "beta": 2.1, "embodied_kg_co2": 180.0},
    }

    @classmethod
    def evaluate_appliance_decision(cls, inputs: ApplianceAssessmentInputs) -> CircularityEvaluationResult:
        specs = cls.WEIBULL_SPECS.get(inputs.category, cls.WEIBULL_SPECS[ApplianceCategory.WASHING_MACHINE])
        eta = specs["eta"]
        beta = specs["beta"]
        embodied_co2 = specs["embodied_kg_co2"]

        # Weibull Cumulative Failure Probability F(t) = 1 - exp(- (t / eta)^beta)
        # Conditional probability of failure in next 2 years given survival up to t:
        # P(t <= T <= t+2 | T > t) = 1 - exp(- ((t+2)/eta)^beta + (t/eta)^beta)
        t = max(0.1, inputs.age_years)
        exponent_diff = - (math.pow((t + 2.0) / eta, beta)) + math.pow(t / eta, beta)
        prob_fail_2yr = (1.0 - math.exp(exponent_diff)) * 100.0

        # Straight-line / exponential depreciation for residual economic value
        depreciation_rate = 1.0 / eta
        residual_value = inputs.original_purchase_cost_usd * max(0.05, math.exp(-depreciation_rate * t))

        # Carbon saved if repaired (avoiding new manufacturing embodied carbon)
        # Avoided manufacturing minus repair parts embodied carbon (~12% of total)
        embodied_carbon_saved = embodied_co2 * 0.88

        # 50% Rule of Thumb & Payback Period:
        # If repair cost is < 50% of new replacement and age is < 70% of characteristic life
        cost_ratio = inputs.estimated_repair_cost_usd / max(1.0, inputs.new_replacement_cost_usd)
        age_ratio = t / eta

        # Economic payback (Years of life extension gained per repair dollar vs buying new)
        additional_expected_years = max(1.0, eta - t)
        annual_capital_cost_new = inputs.new_replacement_cost_usd / eta
        annual_capital_cost_repair = inputs.estimated_repair_cost_usd / additional_expected_years
        payback_years = inputs.estimated_repair_cost_usd / max(1.0, annual_capital_cost_new)

        # Lifecycle Circularity Score (0-100)
        circularity_score = (
            (inputs.repairability_index_score * 4.0) +
            (max(0.0, 1.0 - cost_ratio) * 35.0) +
            (max(0.0, 1.0 - age_ratio) * 25.0)
        )
        circularity_score = min(100.0, max(0.0, circularity_score))

        if cost_ratio <= 0.45 and age_ratio < 0.75:
            decision = "Repair & Extend Life"
            advice = (
                f"Economically and ecologically advantageous to repair. You will avoid {embodied_carbon_saved:.0f} kg CO₂e "
                f"of new manufacturing emissions while extending device lifespan by ~{additional_expected_years:.1f} years."
            )
        else:
            decision = "Eco-Recycle & Replace"
            advice = (
                f"Appliance has exceeded optimal circularity threshold ({age_ratio*100:.0f}% of lifespan). "
                "Recommend responsible WEEE/E-waste recycling and upgrading to an ultra-efficient ENERGY STAR / A+++ unit."
            )

        return CircularityEvaluationResult(
            appliance_name=inputs.appliance_name,
            recommended_decision=decision,
            failure_probability_next_2yrs_pct=round(prob_fail_2yr, 1),
            residual_economic_value_usd=round(residual_value, 2),
            embodied_carbon_saved_by_repair_kg=round(embodied_carbon_saved, 1),
            repair_economic_payback_years=round(payback_years, 2),
            lifecycle_circularity_score=round(circularity_score, 1),
            actionable_advice=advice,
        )
