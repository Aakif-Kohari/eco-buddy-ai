"""
Unit tests for Carbon Tax Simulator and Dividend Rebate Calculator.
"""

import pytest
from carbon_tax_simulator import CarbonTaxSimulator
from dividend_rebate_calculator import DividendRebateCalculator


def test_carbon_tax_simulator_base():
    sim = CarbonTaxSimulator(
        annual_household_footprint_tonnes=10.0, tax_rate_per_tonne_usd=50.0
    )
    result = sim.calculate_tax_liability()

    assert result["total_annual_liability_usd"] == 500.0
    assert result["breakdown"]["scope1_direct_usd"] == 150.0  # 30%
    assert result["breakdown"]["scope2_electricity_usd"] == 100.0  # 20%
    assert result["breakdown"]["scope3_consumption_usd"] == 250.0  # 50%


def test_dividend_rebate_calculator_base():
    calc = DividendRebateCalculator(
        num_adults=2, num_children=1, annual_household_income_usd=75000
    )
    result = calc.calculate_rebate()

    # Base: (2 * 600) + (1 * 300) = 1500
    # Income is below threshold, so no reduction
    assert result["base_rebate_usd"] == 1500.0
    assert result["income_reduction_usd"] == 0.0
    assert result["final_annual_rebate_usd"] == 1500.0


def test_dividend_rebate_calculator_phase_out():
    # High income household
    calc = DividendRebateCalculator(
        num_adults=2, num_children=0, annual_household_income_usd=250000
    )
    result = calc.calculate_rebate()

    # Base: 2 * 600 = 1200
    # Excess income: 250000 - 150000 = 100000
    # Reduction: 100000 * 0.002 = 200
    assert result["base_rebate_usd"] == 1200.0
    assert result["income_reduction_usd"] == 200.0
    assert result["final_annual_rebate_usd"] == 1000.0


def test_net_financial_impact_positive():
    tax_sim = CarbonTaxSimulator(
        annual_household_footprint_tonnes=5.0, tax_rate_per_tonne_usd=50.0
    )
    tax_result = tax_sim.calculate_tax_liability()  # 250.0

    rebate_calc = DividendRebateCalculator(
        num_adults=2, num_children=1, annual_household_income_usd=75000
    )
    net_result = rebate_calc.calculate_net_financial_impact(
        tax_result["total_annual_liability_usd"]
    )

    # Rebate is 1500, Tax is 250. Net = +1250
    assert net_result["net_annual_impact_usd"] == 1250.0
    assert net_result["is_net_positive"] is True
    assert "Net Gainer" in net_result["interpretation"]


def test_net_financial_impact_negative():
    tax_sim = CarbonTaxSimulator(
        annual_household_footprint_tonnes=20.0, tax_rate_per_tonne_usd=100.0
    )
    tax_result = tax_sim.calculate_tax_liability()  # 2000.0

    rebate_calc = DividendRebateCalculator(
        num_adults=1, num_children=0, annual_household_income_usd=200000
    )
    net_result = rebate_calc.calculate_net_financial_impact(
        tax_result["total_annual_liability_usd"]
    )

    # Base rebate: 600. Excess income: 50000. Reduction: 100. Final rebate: 500.
    # Tax: 2000. Net = 500 - 2000 = -1500
    assert net_result["net_annual_impact_usd"] == -1500.0
    assert net_result["is_net_positive"] is False
    assert "Net Payer" in net_result["interpretation"]
