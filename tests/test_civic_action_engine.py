import pytest
from civic_action_engine import CivicActionEngine

@pytest.fixture
def engine():
    return CivicActionEngine()

def test_get_active_bills(engine):
    bills = engine.get_active_bills()
    assert len(bills) == 3
    assert bills[0]["bill_id"] == "hr-4040"

def test_evaluate_user_impact_hr4040(engine):
    bill = next(b for b in engine.get_active_bills() if b["bill_id"] == "hr-4040")
    
    # User without EV
    impact1 = engine.evaluate_user_impact(1, {"owns_ev": False}, bill)
    assert impact1["financial_savings_usd"] == 7500.0
    assert impact1["carbon_savings_kg"] == 4600.0
    
    # User with EV (no additional savings)
    impact2 = engine.evaluate_user_impact(1, {"owns_ev": True}, bill)
    assert impact2["financial_savings_usd"] == 0.0
    assert impact2["carbon_savings_kg"] == 0.0

def test_evaluate_user_impact_sb110(engine):
    bill = next(b for b in engine.get_active_bills() if b["bill_id"] == "sb-110")
    
    user_footprint = {
        "monthly_gas_spend_usd": 100.0,
        "total_emissions_kg": 10000.0
    }
    
    impact = engine.evaluate_user_impact(1, user_footprint, bill)
    
    # 400 - (100 * 12 * 0.15) = 400 - 180 = 220
    assert impact["financial_savings_usd"] == 220.0
    # 10000 * 0.10 = 1000
    assert impact["carbon_savings_kg"] == 1000.0

def test_generate_advocacy_prompt(engine):
    prompt = engine.generate_advocacy_prompt("Jane Doe", "Clean Air Act", 500.0, 1000.0)
    assert "Jane Doe" in prompt
    assert "Clean Air Act" in prompt
    assert "$500.00" in prompt
    assert "1,000 kg" in prompt
