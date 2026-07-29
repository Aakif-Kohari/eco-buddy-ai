import os
import uuid
import pytest
import database as db
from admin_analytics import calculate_platform_stats, get_admin_platform_stats


@pytest.fixture(autouse=True)
def setup_teardown_db():
    """Setup clean isolated test database for admin analytics tests."""
    original_db_name = db.DB_NAME
    test_db_name = f"test_admin_{uuid.uuid4().hex[:8]}.db"
    db.DB_NAME = test_db_name

    db.init_db()

    yield

    db.DB_NAME = original_db_name
    if os.path.exists(test_db_name):
        try:
            os.remove(test_db_name)
        except OSError:
            pass


def test_calculate_platform_stats_empty():
    """Test platform statistics calculation on empty dataset."""
    stats = calculate_platform_stats([])
    assert stats["total_assessments"] == 0
    assert stats["average_eco_score"] == 0.0
    assert stats["active_users"] == 0
    assert stats["popular_recommendations"] == []


def test_calculate_platform_stats_single_user():
    """Test platform statistics calculation with multiple assessments for a single user."""
    mock_assessments = [
        # (id, user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
        (1, 101, "2026-07-28 10:00:00", "Car", 20.0, 350.0, "Non-Vegetarian", 2, 6000.0, 40),
        (2, 101, "2026-07-28 11:00:00", "Bike", 10.0, 150.0, "Vegetarian", 0, 1500.0, 80),
    ]

    stats = calculate_platform_stats(mock_assessments)
    assert stats["total_assessments"] == 2
    assert stats["average_eco_score"] == 60.0  # (40 + 80) / 2
    assert stats["active_users"] == 1
    assert len(stats["popular_recommendations"]) > 0


def test_calculate_platform_stats_multiple_users():
    """Test platform statistics calculation across distinct users."""
    mock_assessments = [
        (1, 101, "2026-07-28 10:00:00", "Car", 25.0, 400.0, "Non-Vegetarian", 3, 7500.0, 30),
        (2, 102, "2026-07-28 11:00:00", "Walking", 5.0, 100.0, "Vegan", 0, 800.0, 95),
        (3, 103, "2026-07-28 12:00:00", "Public Transport", 15.0, 200.0, "Vegetarian", 1, 3200.0, 70),
        (4, 101, "2026-07-28 13:00:00", "Bike", 8.0, 150.0, "Vegetarian", 0, 1200.0, 85),
    ]

    stats = calculate_platform_stats(mock_assessments)
    assert stats["total_assessments"] == 4
    assert stats["average_eco_score"] == round((30 + 95 + 70 + 85) / 4, 1)  # 70.0
    assert stats["active_users"] == 3  # 101, 102, 103


def test_popular_recommendations_ranking():
    """Test that generated recommendations are correctly aggregated and sorted by frequency descending."""
    mock_assessments = [
        (1, 1, "2026-07-28", "Car", 20.0, 400.0, "Non-Vegetarian", 6, 8000.0, 20),
        (2, 2, "2026-07-28", "Car", 30.0, 450.0, "Non-Vegetarian", 6, 9000.0, 15),
    ]

    stats = calculate_platform_stats(mock_assessments)
    recs = stats["popular_recommendations"]
    
    assert len(recs) > 0
    counts = [item[1] for item in recs]
    assert counts == sorted(counts, reverse=True)
    assert all(c >= 1 for c in counts)


def test_anonymization_no_pii():
    """Verify that statistics dictionaries contain zero user personal information (no usernames or emails)."""
    mock_assessments = [
        (1, 1, "2026-07-28", "Car", 20.0, 250.0, "Vegetarian", 0, 3000.0, 65)
    ]
    stats = calculate_platform_stats(mock_assessments)
    
    allowed_keys = {"total_assessments", "average_eco_score", "active_users", "popular_recommendations"}
    assert set(stats.keys()) == allowed_keys
    
    for rec_text, count in stats["popular_recommendations"]:
        assert isinstance(rec_text, str)
        assert isinstance(count, int)
        assert "@" not in rec_text


def test_get_admin_platform_stats_with_db():
    """Integration test checking get_admin_platform_stats with saved database records."""
    db.save_assessment(1, "Car", 20.0, 300.0, "Non-Vegetarian", 2, 6000.0, 40)
    db.save_assessment(2, "Bike", 10.0, 120.0, "Vegetarian", 0, 1800.0, 80)

    stats = get_admin_platform_stats()
    assert stats["total_assessments"] == 2
    assert stats["average_eco_score"] == 60.0
    assert stats["active_users"] == 2
