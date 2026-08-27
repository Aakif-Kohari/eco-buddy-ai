import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from src.community import streak_calendar

def test_get_activity_intensity():
    assert streak_calendar.get_activity_intensity(0) == 0
    assert streak_calendar.get_activity_intensity(1) == 1
    assert streak_calendar.get_activity_intensity(2) == 2
    assert streak_calendar.get_activity_intensity(3) == 3
    assert streak_calendar.get_activity_intensity(4) == 3
    assert streak_calendar.get_activity_intensity(5) == 4
    assert streak_calendar.get_activity_intensity(-1) == 0

def test_compute_streak_stats_empty():
    current, longest, active = streak_calendar.compute_streak_stats({})
    assert current == 0
    assert longest == 0
    assert active == 0

def test_compute_streak_stats_current_active():
    today = date(2023, 10, 5)
    data = {
        today: {"total_actions": 1},
        today - timedelta(days=1): {"total_actions": 2},
        today - timedelta(days=2): {"total_actions": 1},
        today - timedelta(days=4): {"total_actions": 5},
    }
    current, longest, active = streak_calendar.compute_streak_stats(data, current_date=today)
    assert current == 3
    assert longest == 3
    assert active == 4

def test_compute_streak_stats_yesterday_active_today_not():
    today = date(2023, 10, 5)
    data = {
        today - timedelta(days=1): {"total_actions": 2},
        today - timedelta(days=2): {"total_actions": 1},
        today - timedelta(days=4): {"total_actions": 5},
        today - timedelta(days=5): {"total_actions": 1},
    }
    current, longest, active = streak_calendar.compute_streak_stats(data, current_date=today)
    # Today is not active, but yesterday was, so streak is still 2
    assert current == 2
    assert longest == 2
    assert active == 4

def test_compute_streak_stats_broken_streak():
    today = date(2023, 10, 5)
    data = {
        today - timedelta(days=2): {"total_actions": 2},
        today - timedelta(days=3): {"total_actions": 1},
        today - timedelta(days=4): {"total_actions": 5},
    }
    current, longest, active = streak_calendar.compute_streak_stats(data, current_date=today)
    # Neither today nor yesterday active => current streak 0
    assert current == 0
    assert longest == 3
    assert active == 3

def test_compute_streak_stats_ignore_zero_actions():
    today = date(2023, 10, 5)
    data = {
        today: {"total_actions": 1},
        today - timedelta(days=1): {"total_actions": 0},
        today - timedelta(days=2): {"total_actions": 1},
    }
    current, longest, active = streak_calendar.compute_streak_stats(data, current_date=today)
    assert current == 1
    assert longest == 1
    assert active == 2

@patch("streak_calendar.get_connection")
def test_get_daily_activity_counts(mock_get_connection):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock row data
    mock_cursor.fetchall.return_value = [
        {"activity_date": "2023-05-10", "assessment_count": 1, "challenge_count": 0, "xp_earned": 50, "habit_count": 0},
        {"activity_date": "2023-05-11", "assessment_count": 0, "challenge_count": 1, "xp_earned": 0, "habit_count": 1}
    ]

    result = streak_calendar.get_daily_activity_counts(user_id=1, year=2023)
    
    date1 = date(2023, 5, 10)
    date2 = date(2023, 5, 11)
    
    assert len(result) == 2
    assert date1 in result
    assert result[date1]["total_actions"] == 2 # 1 assessment + 1 (xp>0)
    assert result[date1]["intensity_level"] == 2
    
    assert date2 in result
    assert result[date2]["total_actions"] == 2 # 1 challenge + 1 habit + 0 xp
    assert result[date2]["intensity_level"] == 2
    
    from unittest.mock import ANY
    mock_cursor.execute.assert_called_once_with(
        ANY,
        (1, '2023-01-01', '2023-12-31')
    )
