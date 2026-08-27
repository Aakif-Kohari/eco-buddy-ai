import pytest
from datetime import datetime, timedelta
import json
import sqlite3
import os

from pages.Lifestyle_Habit_Tracker import LifestyleTracker
from habit_tracker import DB_NAME, init_habit_db

@pytest.fixture
def temp_tracker():
    # Use a dummy user_id
    user_id = 99999
    
    # Initialize DB table just in case it doesn't exist
    init_habit_db()
    
    # Create the tracker
    tracker = LifestyleTracker(user_id)
    
    # Clear existing state just for the test
    tracker.data = {
        'habits': [],
        'history': {},
        'streaks': {},
        'best_streaks': {},
        'last_active_date': datetime.now().date().isoformat()
    }
    
    yield tracker
    
    # Cleanup dummy user after
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_habits WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def test_add_and_remove_custom_habit(temp_tracker):
    # Add
    temp_tracker.add_custom_habit("Compost Daily", "Waste", "daily")
    assert len(temp_tracker.data['habits']) == 1
    h_id = temp_tracker.data['habits'][0]['id']
    assert h_id in temp_tracker.data['history']
    assert temp_tracker.data['habits'][0]['name'] == "Compost Daily"
    
    # Remove
    temp_tracker.remove_habit(h_id)
    assert len(temp_tracker.data['habits']) == 0
    assert h_id not in temp_tracker.data['history']

def test_update_status_and_streaks(temp_tracker):
    temp_tracker.add_custom_habit("Bike to Work", "Transportation", "daily")
    h_id = temp_tracker.data['habits'][0]['id']
    
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    
    # Complete yesterday
    temp_tracker.update_status(h_id, "completed", yesterday)
    assert temp_tracker.data['streaks'][h_id] == 1
    assert temp_tracker.data['best_streaks'][h_id] == 1
    
    # Complete today
    temp_tracker.update_status(h_id, "completed", today)
    assert temp_tracker.data['streaks'][h_id] == 2
    assert temp_tracker.data['best_streaks'][h_id] == 2
    
    # Change today to missed
    temp_tracker.update_status(h_id, "missed", today)
    assert temp_tracker.data['streaks'][h_id] == 0  # Streak broken
    assert temp_tracker.data['best_streaks'][h_id] == 2  # Best remains

def test_get_stats(temp_tracker):
    temp_tracker.add_custom_habit("Vegan Meal", "Food", "daily")
    temp_tracker.add_custom_habit("No Plastics", "Waste", "daily")
    
    h1 = temp_tracker.data['habits'][0]['id']
    h2 = temp_tracker.data['habits'][1]['id']
    
    today = datetime.now().date().isoformat()
    
    temp_tracker.update_status(h1, "completed", today)
    temp_tracker.update_status(h2, "skipped", today)
    
    stats = temp_tracker.get_stats()
    assert stats['total'] == 2
    assert stats['completed'] == 1
    assert stats['skipped'] == 1
    assert stats['completion_rate'] == 50.0
    
    assert stats['category_stats']['Food']['completed'] == 1
    assert stats['category_stats']['Waste']['completed'] == 0

def test_recommendations(temp_tracker):
    # Setup some stats
    temp_tracker.add_custom_habit("Walk", "Transportation", "daily")
    temp_tracker.add_custom_habit("Lights off", "Energy", "daily")
    
    h1 = temp_tracker.data['habits'][0]['id']
    
    today = datetime.now().date()
    # Miss the last 3 days for h1
    for i in range(1, 4):
        d_str = (today - timedelta(days=i)).isoformat()
        temp_tracker.update_status(h1, "missed", d_str)
        
    recs = temp_tracker.generate_recommendations()
    assert any("Habit Alert" in r and "Walk" in r for r in recs)
