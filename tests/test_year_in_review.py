import pytest
from unittest.mock import patch, MagicMock
from src.reporting.year_in_review_engine import (
    aggregate_annual_data,
    compute_yoy_trends,
    extract_milestones,
    compute_community_percentiles
)

@pytest.fixture
def mock_assessments():
    return [
        {
            "id": 1, "transport": "car", "distance": 100.0, "electricity": 200.0,
            "diet": "meat_heavy", "flights": 0, "footprint": 50.0, "eco_score": 75.0,
            "created_at": "2024-01-15 10:00:00"
        },
        {
            "id": 2, "transport": "bike", "distance": 50.0, "electricity": 150.0,
            "diet": "vegan", "flights": 1, "footprint": 60.0, "eco_score": 85.0,
            "created_at": "2024-03-20 12:00:00"
        }
    ]

@patch("src.reporting.year_in_review_engine._fetch_assessments_for_year")
def test_aggregate_annual_data(mock_fetch, mock_assessments):
    mock_fetch.return_value = mock_assessments
    
    data = aggregate_annual_data(user_id=1, year=2024)
    
    assert data["total_footprint_kg"] == 110.0
    assert data["avg_eco_score"] == 80.0
    assert data["assessments_count"] == 2
    
    # Check monthly mapping
    # Jan = month 1
    jan_data = next(m for m in data["monthly_trends"] if m["month"] == 1)
    assert jan_data["count"] == 1
    assert jan_data["total_footprint"] == 50.0
    
    # March = month 3
    mar_data = next(m for m in data["monthly_trends"] if m["month"] == 3)
    assert mar_data["count"] == 1
    assert mar_data["total_footprint"] == 60.0

def test_compute_yoy_trends():
    prev_data = {"total_footprint_kg": 100.0, "avg_eco_score": 50.0, "assessments_count": 5}
    curr_data = {"total_footprint_kg": 80.0, "avg_eco_score": 75.0, "assessments_count": 10}
    
    trends = compute_yoy_trends(curr_data, prev_data)
    
    assert trends["footprint_trend"]["direction"] == "down"
    assert trends["footprint_trend"]["change_pct"] == -20.0
    
    assert trends["eco_score_trend"]["direction"] == "up"
    assert trends["eco_score_trend"]["change_pct"] == 50.0

@patch("src.reporting.year_in_review_engine._fetch_assessments_for_year")
def test_extract_milestones(mock_fetch, mock_assessments):
    mock_fetch.return_value = mock_assessments
    data = aggregate_annual_data(user_id=1, year=2024)
    
    milestones = extract_milestones(user_id=1, year=2024, annual_data=data)
    
    assert "Best Month" in milestones
    assert "Jan" in milestones["Best Month"] # 50 < 60
    assert "First Assessment" in milestones
    assert "2024-01-15" in milestones["First Assessment"]
    assert "Highest Eco Score" in milestones
    assert "85/100" in milestones["Highest Eco Score"]

@patch("src.reporting.year_in_review_engine.database_connection")
def test_compute_community_percentiles(mock_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # User 1: 50, User 2: 100, User 3: 150
    mock_cursor.fetchall.return_value = [
        (1, 50.0),
        (2, 100.0),
        (3, 150.0)
    ]
    
    # If user footprint is 100, they are rank 1 out of 3 -> percentile is 33.3%, so better than 66.7%
    res = compute_community_percentiles(user_id=2, year=2024, total_footprint=100.0)
    assert res["percentile"] == pytest.approx(66.66, 0.1)
