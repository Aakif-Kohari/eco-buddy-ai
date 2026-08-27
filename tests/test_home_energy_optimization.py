import pytest
import pandas as pd
from pages.Home_Energy_Optimization import calculate_projected_energy, generate_efficiency_score, get_recommendations

def test_generate_efficiency_score():
    score, rating = generate_efficiency_score(0)
    assert score == 100
    assert "Outstanding" in rating or "Excellent" in rating
    
    score, rating = generate_efficiency_score(14.0) # 50% of benchmark 28.0
    assert score == 100
    assert "Outstanding" in rating
    
    score, rating = generate_efficiency_score(28.0) # 100% of benchmark
    assert score == 75
    assert "Good" in rating
    
    score, rating = generate_efficiency_score(56.0) # 200% of benchmark
    assert score == 40
    assert "Needs Improvement" in rating

def test_get_recommendations():
    # Empty case
    df_empty = pd.DataFrame()
    recs = get_recommendations(df_empty)
    assert len(recs) == 1
    assert "registry" in recs[0]
    
    # Test high impact and high standby
    df_data = pd.DataFrame([
        {"Name": "Old Fridge", "Category": "Refrigerator", "Power (W)": 800, "Hours/Day": 24, "Standby (W)": 0, "Monthly kWh": 576, "Quantity": 1},
        {"Name": "TV", "Category": "Electronics", "Power (W)": 150, "Hours/Day": 4, "Standby (W)": 20, "Monthly kWh": 18 + 14.4, "Quantity": 1},
        {"Name": "AC", "Category": "AC", "Power (W)": 2000, "Hours/Day": 10, "Standby (W)": 0, "Monthly kWh": 600, "Quantity": 1},
        {"Name": "Living Room Lights", "Category": "Lighting", "Power (W)": 60, "Hours/Day": 5, "Standby (W)": 0, "Monthly kWh": 9, "Quantity": 6} # 360W total lighting
    ])
    
    recs = get_recommendations(df_data)
    assert any("Highest Impact" in rec for rec in recs)
    assert any("Phantom Load" in rec for rec in recs)
    assert any("Climate Control" in rec for rec in recs)
    assert any("Lighting" in rec for rec in recs)

def test_calculate_projected_energy():
    df_input = pd.DataFrame([
        {"Name": "TV", "Power (W)": 100, "Hours/Day": 10, "Standby (W)": 0, "Quantity": 1, "Days/Month": 30}
    ])
    
    projected_df = calculate_projected_energy(df_input)
    # Active daily kWh = (100 * 10 * 1) / 1000 = 1.0 kWh
    # Monthly = 30 kWh
    assert projected_df["Projected Daily kWh"].iloc[0] == 1.0
    assert projected_df["Projected Monthly kWh"].iloc[0] == 30.0
