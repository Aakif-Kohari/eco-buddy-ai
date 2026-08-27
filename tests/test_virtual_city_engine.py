import pytest
from src.utils.virtual_city_engine import VirtualCityEngine

def test_unlocked_assets_thresholds():
    engine = VirtualCityEngine(user_id=1)
    
    # 0 kg
    assets = engine.calculate_unlocked_assets(0)
    assert len(assets) == 1
    assert assets[0]["id"] == "grass"
    
    # 60 kg -> should unlock grass and small tree (threshold 50)
    assets = engine.calculate_unlocked_assets(60)
    assert len(assets) == 2
    ids = [a["id"] for a in assets]
    assert "grass" in ids
    assert "tree_small" in ids
    
    # 600 kg -> grass, small tree, large tree, solar panel, wind turbine
    assets = engine.calculate_unlocked_assets(600)
    assert len(assets) == 5
    ids = [a["id"] for a in assets]
    assert "wind_turbine" in ids
    
from unittest.mock import patch

def test_update_city_state():
    # Mock the database calls
    with patch("virtual_city_engine.get_virtual_city_state") as mock_get, \
         patch("virtual_city_engine.save_virtual_city_state") as mock_save:
        
        # Setup mock return
        mock_get.return_value = {
            "user_id": 1,
            "carbon_saved_kg": 0,
            "unlocked_assets": [],
            "layout_state": {}
        }
        
        engine = VirtualCityEngine(user_id=1)
        state = engine.update_city_state(200)
        
        # Check save was called with correct parameters
        mock_save.assert_called_once()
        
        args, kwargs = mock_save.call_args
        assert kwargs["user_id"] == 1
        assert kwargs["carbon_saved_kg"] == 200
        assert len(kwargs["unlocked_assets"]) == 3 # 0, 50, 150 thresholds met
