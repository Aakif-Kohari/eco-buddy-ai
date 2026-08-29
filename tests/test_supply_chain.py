import pytest
import pandas as pd
from src.business.supply_chain_data import SupplyChainDataGenerator
from src.business.supply_chain_logic import SupplyChainLogic

class TestSupplyChainLogic:
    
    @pytest.fixture
    def mock_data(self):
        generator = SupplyChainDataGenerator(num_suppliers=5, seed=123)
        return generator.get_full_dataset()

    def test_data_generation(self, mock_data):
        assert "suppliers" in mock_data
        assert "shipments" in mock_data
        assert "facilities" in mock_data
        
        assert len(mock_data["suppliers"]) == 5
        assert len(mock_data["shipments"]) > 0
        assert len(mock_data["facilities"]) > 0

    def test_transport_emissions(self, mock_data):
        logic = SupplyChainLogic(mock_data)
        transport_df = logic.calculate_transport_emissions()
        
        assert "transport_emissions_mt" in transport_df.columns
        assert not transport_df["transport_emissions_mt"].isnull().any()
        assert (transport_df["transport_emissions_mt"] >= 0).all()

    def test_material_emissions(self, mock_data):
        logic = SupplyChainLogic(mock_data)
        material_df = logic.calculate_material_emissions()
        
        assert "material_emissions_mt" in material_df.columns
        assert not material_df["material_emissions_mt"].isnull().any()
        assert (material_df["material_emissions_mt"] >= 0).all()

    def test_facility_emissions(self, mock_data):
        logic = SupplyChainLogic(mock_data)
        facility_df = logic.calculate_facility_emissions()
        
        assert "facility_emissions_mt" in facility_df.columns
        assert not facility_df["facility_emissions_mt"].isnull().any()
        assert (facility_df["facility_emissions_mt"] >= 0).all()

    def test_supplier_scorecard(self, mock_data):
        logic = SupplyChainLogic(mock_data)
        scorecard = logic.generate_supplier_scorecard()
        
        assert len(scorecard) == 5
        assert "total_scope3_emissions_mt" in scorecard.columns
        assert "esg_score" in scorecard.columns
        assert "compliance_status" in scorecard.columns
        
        # Verify aggregation works
        row = scorecard.iloc[0]
        assert row["total_scope3_emissions_mt"] >= 0

    def test_summary_metrics(self, mock_data):
        logic = SupplyChainLogic(mock_data)
        metrics = logic.get_summary_metrics()
        
        assert metrics["total_suppliers"] == 5
        assert metrics["compliant_suppliers"] + metrics["at_risk_suppliers"] == 5
        assert 0 <= metrics["avg_esg_score"] <= 100
        assert metrics["total_scope3_emissions"] >= 0

    def test_empty_dataframe_handling(self):
        empty_data = {
            "suppliers": pd.DataFrame(),
            "shipments": pd.DataFrame(),
            "facilities": pd.DataFrame()
        }
        
        logic = SupplyChainLogic(empty_data)
        metrics = logic.get_summary_metrics()
        
        assert len(metrics) == 0
        assert logic.generate_supplier_scorecard().empty
        assert logic.calculate_transport_emissions().empty
