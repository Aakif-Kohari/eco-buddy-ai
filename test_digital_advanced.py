import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from plugins.digital_screen_time_parser import ScreenTimeParser
from plugins.digital_ml_forecaster import DigitalMLForecaster
from plugins.device_lifecycle_engine import DeviceLifecycleEngine
from plugins.digital_api_clients import CloudCarbonAPIClient
from plugins.digital_gamification import DigitalGamificationEngine

# --- 1. Test Screen Time Parser ---
def test_apple_screen_time_parsing():
    mock_json = ScreenTimeParser.generate_mock_apple_data(days=3)
    parser = ScreenTimeParser(mock_json, "apple_json")
    df = parser.parse()
    
    assert not df.empty
    assert "emission_category" in df.columns
    
    averages = parser.get_daily_averages_for_plugin()
    assert "streaming_hours_daily" in averages
    assert "web_browsing_hours_daily" in averages

def test_google_csv_parsing():
    csv_data = "Date,App,Duration_Milliseconds\n2023-10-01,YouTube,3600000\n2023-10-01,Chrome,1800000"
    parser = ScreenTimeParser(csv_data, "google_csv")
    df = parser.parse()
    
    assert len(df) == 2
    assert df["hours"].iloc[0] == 1.0
    assert df["hours"].iloc[1] == 0.5
    
    averages = parser.get_daily_averages_for_plugin()
    assert averages["streaming_hours_daily"] == 1.0
    assert averages["web_browsing_hours_daily"] == 0.5

# --- 2. Test ML Forecaster ---
def test_ml_forecaster_training_and_prediction():
    # Create fake historical upward trend
    data = [
        {"date": "2023-10-01", "daily_kg_co2": 1.0},
        {"date": "2023-10-02", "daily_kg_co2": 1.1},
        {"date": "2023-10-03", "daily_kg_co2": 1.2},
        {"date": "2023-10-04", "daily_kg_co2": 1.5},
        {"date": "2023-10-05", "daily_kg_co2": 1.8},
        {"date": "2023-10-06", "daily_kg_co2": 2.2},
        {"date": "2023-10-07", "daily_kg_co2": 2.5},
    ]
    df = pd.DataFrame(data)
    
    forecaster = DigitalMLForecaster(df)
    result = forecaster.predict_future_emissions(days_ahead=7)
    
    assert result["success"] is True
    assert result["trajectory"] in ["Escalating Rapidly", "Creeping Upward"]
    assert len(result["forecast_series"]) == 7
    assert result["trend_percent"] > 0

def test_ml_forecaster_anomalies():
    data = [
        {"date": "2023-10-01", "daily_kg_co2": 1.0},
        {"date": "2023-10-02", "daily_kg_co2": 1.1},
        {"date": "2023-10-03", "daily_kg_co2": 1.0},
        {"date": "2023-10-04", "daily_kg_co2": 1.1},
        {"date": "2023-10-05", "daily_kg_co2": 10.0}, # Spike!
        {"date": "2023-10-06", "daily_kg_co2": 1.2},
        {"date": "2023-10-07", "daily_kg_co2": 1.0},
    ]
    df = pd.DataFrame(data)
    forecaster = DigitalMLForecaster(df)
    anomalies = forecaster.detect_anomalies(threshold_z_score=2.0)
    
    assert len(anomalies) == 1
    assert anomalies[0]["date"] == "2023-10-05"
    assert anomalies[0]["severity"] == "Medium"

# --- 3. Test Device Lifecycle Engine ---
def test_device_lifecycle_math():
    engine = DeviceLifecycleEngine("Smartphone", current_age_years=2.0, daily_charge_cycles=1.0)
    health = engine.calculate_battery_health()
    
    # 2 years * 365 cycles * 0.00018 = 0.1314 cycle degradation
    # 2 years * 0.015 = 0.03 calendar degradation
    # Total degradation = 0.1614
    # Health = 1.0 - 0.1614 = 0.8386
    assert round(health, 2) == 0.84
    
    report = engine.generate_lifecycle_report()
    assert report["amortized_carbon_per_year"] == 30.0 # 60kg / 2 years
    assert report["upgrade_analysis"]["carbon_saved_by_not_upgrading"] > 0

def test_device_lifecycle_replace_battery_logic():
    # 5 year old phone heavily used
    engine = DeviceLifecycleEngine("Smartphone", current_age_years=5.0, daily_charge_cycles=2.0)
    health = engine.calculate_battery_health()
    assert health < 0.80 # Degraded
    
    report = engine.generate_lifecycle_report()
    analysis = report["upgrade_analysis"]
    
    assert "REPLACE THE BATTERY" in analysis["recommendation"]
    assert analysis["carbon_saved_by_not_upgrading"] == 52.0 # 60kg new - 8kg battery

# --- 4. Test API Clients ---
def test_aws_api_client_signing():
    client = CloudCarbonAPIClient("AWS", "mock_key", "mock_secret")
    headers = client._ensure_authenticated()
    
    assert "Authorization" in headers
    assert "AWS4-HMAC-SHA256" in headers["Authorization"]
    assert "x-amz-date" in headers

def test_gcp_api_client_oauth():
    client = CloudCarbonAPIClient("GCP", "mock_key", "mock_secret")
    headers = client._ensure_authenticated()
    
    assert "Authorization" in headers
    assert "Bearer mock_secure_token_abc123" in headers["Authorization"]

def test_api_client_data_fetching():
    client = CloudCarbonAPIClient("AWS", "mock_key", "mock_secret")
    df = client.fetch_historical_emissions(days_back=5)
    
    assert len(df) == 5
    assert "total_kg_co2" in df.columns
    
    scopes = client.get_scope_breakdown(df)
    assert "Scope 1 (Direct)" in scopes
    assert scopes["Scope 2 (Electricity)"] > 0

# --- 5. Test Gamification ---
def test_gamification_perfect_user():
    ui_meta = {
        "is_high_res": False,
        "cloud_heavy": False,
        "network": "WiFi",
        "ai_heavy": False,
        "grid_intensity": 0.2
    }
    life_meta = {"age_years": 5.0}
    
    engine = DigitalGamificationEngine(ui_meta, life_meta, total_kg=100.0)
    result = engine.evaluate()
    
    assert len(result["badges"]) == 6 # All badges unlocked
    assert result["score"] >= 80

def test_gamification_bad_user():
    ui_meta = {
        "is_high_res": True,
        "cloud_heavy": True,
        "network": "5G",
        "ai_heavy": True,
        "grid_intensity": 0.8
    }
    life_meta = {"age_years": 1.0}
    
    engine = DigitalGamificationEngine(ui_meta, life_meta, total_kg=2000.0)
    result = engine.evaluate()
    
    assert len(result["badges"]) == 0
    assert result["score"] < 50 # Penalized for >1000kg
