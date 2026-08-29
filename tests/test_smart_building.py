import pytest
import pandas as pd
from src.energy.smart_building_iot_sim import SmartBuildingIoTSimulator
from src.energy.smart_building_logic import SmartBuildingLogic
from src.energy.smart_building_alerts import SmartBuildingAlerts

class TestSmartBuildingTracker:

    @pytest.fixture
    def mock_telemetry(self):
        sim = SmartBuildingIoTSimulator(seed=12)
        devs = sim.generate_devices(30)
        return sim.generate_telemetry(devs, hours=10)

    def test_simulation_data_format(self, mock_telemetry):
        assert not mock_telemetry.empty
        cols = mock_telemetry.columns
        assert "timestamp" in cols
        assert "power_usage_watts" in cols
        assert "device_id" in cols
        assert "floor" in cols

    def test_logic_computation(self, mock_telemetry):
        logic = SmartBuildingLogic(mock_telemetry)
        metrics = logic.calculate_energy_metrics()
        
        assert "energy_kwh" in metrics.columns
        assert "carbon_emissions_kg" in metrics.columns
        assert (metrics["carbon_emissions_kg"] >= 0).all()

        score = logic.calculate_building_score()
        assert 0 <= score["score"] <= 100
        assert score["total_co2_kg"] > 0

    def test_anomalies_engine(self, mock_telemetry):
        # Inject an anomaly artificially
        df = mock_telemetry.copy()
        
        # Artificial huge spike for HVAC
        df.loc[0, "type"] = "HVAC_Unit"
        df.loc[0, "power_usage_watts"] = 5000 
        
        alerts = SmartBuildingAlerts()
        batch_alerts = alerts.analyze_batch(df)
        
        assert len(batch_alerts) > 0
        assert any(a["level"] == "CRITICAL" for a in batch_alerts)
        
        df_alerts = alerts.get_all_alerts()
        assert not df_alerts.empty
        assert "CRITICAL" in df_alerts["level"].values

    def test_empty_dataframe(self):
        logic = SmartBuildingLogic(pd.DataFrame())
        score = logic.calculate_building_score()
        assert score["score"] == 0
        assert score["total_kwh"] == 0
        
        alerts = SmartBuildingAlerts()
        df = alerts.get_all_alerts()
        assert df.empty
