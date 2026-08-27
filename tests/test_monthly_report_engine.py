import pytest
import tempfile
import os
from unittest.mock import patch
from src.reporting.monthly_report_engine import (
    aggregate_monthly_data,
    compute_monthly_trends,
    generate_actionable_insights,
    generate_monthly_pdf
)

def test_aggregate_monthly_data_empty():
    with patch('monthly_report_engine._fetch_assessments_for_month', return_value=[]):
        result = aggregate_monthly_data(1, 2026, 8)
        assert result["user_id"] == 1
        assert result["assessments_count"] == 0
        assert result["total_footprint_kg"] == 0.0

def test_aggregate_monthly_data_with_data():
    mock_data = [
        {'id': 1, 'transport': 'car', 'distance': 100, 'electricity': 50, 'diet': 'average', 'flights': 0, 'footprint': 30, 'eco_score': 80, 'created_at': '2026-08-15 10:00:00'},
        {'id': 2, 'transport': 'bus', 'distance': 50, 'electricity': 30, 'diet': 'vegan', 'flights': 1, 'footprint': 150, 'eco_score': 60, 'created_at': '2026-08-20 10:00:00'}
    ]
    with patch('monthly_report_engine._fetch_assessments_for_month', return_value=mock_data):
        result = aggregate_monthly_data(1, 2026, 8)
        assert result["assessments_count"] == 2
        assert result["total_footprint_kg"] == 180.0
        assert result["avg_eco_score"] == 70.0
        assert result["total_transport_km"] == 150.0
        assert result["total_electricity_kwh"] == 80.0
        assert result["total_flights"] == 1
        assert "transport" in result["category_breakdown"]

def test_compute_monthly_trends():
    prev_data = {"total_footprint_kg": 100, "avg_eco_score": 50, "assessments_count": 5}
    curr_data = {"total_footprint_kg": 120, "avg_eco_score": 60, "assessments_count": 10}
    
    trends = compute_monthly_trends(curr_data, prev_data)
    assert trends["footprint_trend"]["change_pct"] == 20.0
    assert trends["footprint_trend"]["direction"] == "up"
    assert trends["footprint_trend"]["absolute_diff"] == 20.0
    
    assert trends["eco_score_trend"]["change_pct"] == 20.0
    assert trends["eco_score_trend"]["direction"] == "up"
    
    assert trends["assessments_trend"]["change_pct"] == 100.0

    # Test prev = 0
    trends_zero = compute_monthly_trends({"total_footprint_kg": 10}, {"total_footprint_kg": 0})
    assert trends_zero["footprint_trend"]["change_pct"] == 0
    assert trends_zero["footprint_trend"]["direction"] == "up"

def test_generate_actionable_insights():
    # Empty
    assert generate_actionable_insights({}) == ["Log more assessments this month to get personalized insights."]
    
    # Missing categories
    assert generate_actionable_insights({"assessments_count": 5}) == ["Keep logging data to see category insights."]
    
    # Valid categories
    data = {
        "assessments_count": 5,
        "category_breakdown": {
            "transport": 100.0,
            "electricity": 50.0,
            "diet": 10.0,
            "flights": 200.0
        }
    }
    insights = generate_actionable_insights(data)
    assert len(insights) == 2
    assert any("Air travel" in i for i in insights) # flights is highest
    assert any("transport" in i for i in insights) # transport is 2nd highest

def test_generate_monthly_pdf():
    data = {
        "user_id": 1,
        "year": 2026,
        "month": 8,
        "total_footprint_kg": 150.0,
        "avg_eco_score": 75.0,
        "assessments_count": 5,
        "category_breakdown": {
            "transport": 50.0,
            "electricity": 100.0
        },
        "insights": ["Test insight"]
    }
    
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    
    try:
        out_path = generate_monthly_pdf(data, path)
        assert out_path == path
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)
