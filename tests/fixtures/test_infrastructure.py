import pytest

def test_valid_user_generation(user_factory, db_session):
    user_data = user_factory.build()
    db_session[user_data["id"]] = user_data
    assert user_data["username"] == "ecouser_0001"
    assert user_data["is_active"] is True

def test_invalid_and_edge_cases(user_factory, log_factory):
    # Edge case payload testing
    boundary_user = user_factory.build(carbon_footprint_goal=0.0)
    assert boundary_user["carbon_footprint_goal"] == 0.0
    
    # Malicious/Invalid data testing
    malicious_user = user_factory.build(username="' OR 1=1; --")
    assert malicious_user["username"] == "' OR 1=1; --"
