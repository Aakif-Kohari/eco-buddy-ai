"""
Comprehensive test suite for Environmental Benchmarking Engine.
"""
import unittest
from datetime import datetime, timedelta
import math
import sqlite3
import os

from src.environmental_benchmarking.models import (
    CategoryStat, 
    ReferenceProfile, 
    UserAssessment, 
    CategoryComparison, 
    BenchmarkResult,
    HistoricalTrendData
)
from src.environmental_benchmarking.engine import BenchmarkEngine
from src.environmental_benchmarking.history import HistoryAnalyzer
from src.environmental_benchmarking.profiles import get_default_profiles

class TestModels(unittest.TestCase):
    
    def test_category_stat_validation(self):
        """Test the CategoryStat validation logic."""
        # Valid stat
        stat = CategoryStat(mean=50, median=45, std_dev=10, min_val=0, max_val=100, p10=10, p25=25, p75=75, p90=90)
        stat.validate() # Should not raise
        
        # Invalid min > max
        with self.assertRaises(ValueError):
            stat2 = CategoryStat(mean=50, median=45, std_dev=10, min_val=100, max_val=0, p10=10, p25=25, p75=75, p90=90)
            stat2.validate()
            
        # Invalid monotonic percentiles
        with self.assertRaises(ValueError):
            stat3 = CategoryStat(mean=50, median=45, std_dev=10, min_val=0, max_val=100, p10=30, p25=25, p75=75, p90=90)
            stat3.validate()
            
        # Invalid mean outside bounds
        with self.assertRaises(ValueError):
            stat4 = CategoryStat(mean=150, median=45, std_dev=10, min_val=0, max_val=100, p10=10, p25=25, p75=75, p90=90)
            stat4.validate()

    def test_reference_profile(self):
        """Test ReferenceProfile fetching logic."""
        stat = CategoryStat(mean=50, median=45, std_dev=10, min_val=0, max_val=100, p10=10, p25=25, p75=75, p90=90)
        profile = ReferenceProfile(
            id="test", name="Test", description="Test", region_code="TS",
            transport_stat=stat, electricity_stat=stat, diet_stat=stat, 
            flights_stat=stat, footprint_stat=stat, eco_score_stat=stat
        )
        
        self.assertEqual(profile.get_stat("transport"), stat)
        self.assertIsNone(profile.get_stat("nonexistent"))
        profile.validate_all() # Should not raise
        
    def test_user_assessment_parsing(self):
        """Test parsing user assessment from DB row."""
        row = {
            'id': 5,
            'user_id': 2,
            'date': '2026-08-23T10:00:00',
            'transport': 'bus',
            'distance': 15.5,
            'electricity': 120.0,
            'diet': 'vegan',
            'flights': 0,
            'footprint': 345.6,
            'eco_score': 85
        }
        assessment = UserAssessment.from_db_row(row)
        self.assertEqual(assessment.assessment_id, 5)
        self.assertEqual(assessment.user_id, 2)
        self.assertEqual(assessment.diet, 'vegan')
        self.assertEqual(assessment.footprint, 345.6)
        
        # Test missing / null fields
        row2 = {'id': 6}
        a2 = UserAssessment.from_db_row(row2)
        self.assertEqual(a2.transport, 'car')
        self.assertEqual(a2.distance, 0.0)

class TestBenchmarkEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = BenchmarkEngine()
        
    def test_profiles_loaded(self):
        self.assertIn('global', self.engine.profiles)
        self.assertIn('us', self.engine.profiles)
        self.assertIn('target', self.engine.profiles)
        
    def test_percentile_calculation_lower_is_better(self):
        """Test footprint percentile calculation where lower values should yield higher percentiles."""
        stat = CategoryStat(mean=4500, median=4000, std_dev=2500, min_val=500, max_val=30000, p10=1500, p25=2500, p75=6000, p90=8500)
        
        # Perfect footprint (<= min) -> near 100th percentile
        p_perfect = self.engine._calculate_percentile_from_stat(500, stat, is_higher_better=False)
        self.assertEqual(p_perfect, 100.0)
        
        # Median footprint -> 50th percentile
        p_med = self.engine._calculate_percentile_from_stat(4000, stat, is_higher_better=False)
        self.assertEqual(p_med, 50.0) # Wait, median in CDF is 50%, so 100-50 = 50.
        
        # At p90 (very high footprint) -> meaning they are in the bottom 10% of sustainability
        p_bad = self.engine._calculate_percentile_from_stat(8500, stat, is_higher_better=False)
        self.assertEqual(p_bad, 10.0) # 100 - 90 = 10
        
        # Extremely high -> 0
        p_worst = self.engine._calculate_percentile_from_stat(30000, stat, is_higher_better=False)
        self.assertEqual(p_worst, 0.0)

    def test_percentile_calculation_higher_is_better(self):
        """Test eco_score percentile where higher values yield higher percentiles."""
        stat = CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=20, p25=35, p75=65, p90=80)
        
        p_perfect = self.engine._calculate_percentile_from_stat(100, stat, is_higher_better=True)
        self.assertEqual(p_perfect, 100.0)
        
        p_med = self.engine._calculate_percentile_from_stat(50, stat, is_higher_better=True)
        self.assertEqual(p_med, 50.0)
        
        p_bad = self.engine._calculate_percentile_from_stat(20, stat, is_higher_better=True)
        self.assertEqual(p_bad, 10.0)

    def test_nan_values(self):
        """Test that NaN values are handled gracefully."""
        stat = CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=20, p25=35, p75=65, p90=80)
        p = self.engine._calculate_percentile_from_stat(math.nan, stat)
        self.assertEqual(p, 50.0)
        
        n = self.engine._calculate_normalized_score(math.nan, stat)
        self.assertEqual(n, 50.0)

    def test_normalized_score(self):
        stat = CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=20, p25=35, p75=65, p90=80)
        
        # Lower is better (carbon)
        self.assertEqual(self.engine._calculate_normalized_score(0, stat, False), 100.0)
        self.assertEqual(self.engine._calculate_normalized_score(50, stat, False), 50.0)
        self.assertEqual(self.engine._calculate_normalized_score(100, stat, False), 0.0)
        
        # Higher is better (eco score)
        self.assertEqual(self.engine._calculate_normalized_score(0, stat, True), 0.0)
        self.assertEqual(self.engine._calculate_normalized_score(50, stat, True), 50.0)
        self.assertEqual(self.engine._calculate_normalized_score(100, stat, True), 100.0)

    def test_extract_carbon_value(self):
        ass = UserAssessment(1, 1, datetime.now(), 'car', 100.0, 50.0, 'vegan', 2, 1000.0, 85)
        self.assertAlmostEqual(self.engine.extract_carbon_value('transport', ass), 20.0)
        self.assertAlmostEqual(self.engine.extract_carbon_value('electricity', ass), 20.0)
        self.assertAlmostEqual(self.engine.extract_carbon_value('diet', ass), 1.5 * 365)
        self.assertAlmostEqual(self.engine.extract_carbon_value('flights', ass), 1000.0)
        self.assertAlmostEqual(self.engine.extract_carbon_value('footprint', ass), 1000.0)
        self.assertAlmostEqual(self.engine.extract_carbon_value('eco_score', ass), 85.0)

    def test_compare_category(self):
        profile = self.engine.get_profile('global')
        comp = self.engine.compare_category('footprint', 2000, profile)
        
        self.assertEqual(comp.category_name, 'footprint')
        self.assertEqual(comp.user_value, 2000)
        self.assertGreater(comp.percentile, 50.0) # Lower than median (4000), so better percentile
        self.assertTrue(comp.is_better_than_average)
        self.assertLess(comp.difference_from_mean, 0) # 2000 - 4500 = -2500
        
        comp_bad = self.engine.compare_category('footprint', 15000, profile)
        self.assertLess(comp_bad.percentile, 50.0)
        self.assertFalse(comp_bad.is_better_than_average)

    def test_compare_assessment(self):
        ass = UserAssessment(1, 1, datetime.now(), 'bus', 20.0, 10.0, 'vegan', 0, 1500.0, 95)
        res = self.engine.compare_assessment(ass, 'global')
        
        self.assertEqual(res.profile_name, 'Global Average')
        self.assertGreater(res.overall_percentile, 70.0)
        self.assertIn('transport', res.categories)
        self.assertTrue(len(res.strengths) > 0)
        self.assertTrue(len(res.insights) > 0)
        
    def test_edge_cases_empty_missing(self):
        # Everything zero
        ass = UserAssessment(1, 1, datetime.now(), 'car', 0.0, 0.0, 'average', 0, 0.0, 0)
        res = self.engine.compare_assessment(ass, 'us')
        # Expect extremely high percentiles for footprint/emissions, extremely low for eco_score
        self.assertEqual(res.categories['footprint'].percentile, 100.0)
        self.assertEqual(res.categories['eco_score'].percentile, 0.0)

class TestHistoryAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.db_path = "test_history_eb.db"
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transport TEXT,
            distance REAL,
            electricity REAL,
            diet TEXT,
            flights INTEGER,
            footprint REAL,
            eco_score INTEGER
        )
        """)
        # Insert test data
        cursor.execute("INSERT INTO assessments (user_id, footprint) VALUES (1, 5000)")
        cursor.execute("INSERT INTO assessments (user_id, footprint) VALUES (1, 4500)")
        cursor.execute("INSERT INTO assessments (user_id, footprint) VALUES (1, 4000)")
        cursor.execute("INSERT INTO assessments (user_id, footprint) VALUES (2, 8000)")
        self.conn.commit()
        
        self.history = HistoryAnalyzer(db_path=self.db_path)
        
    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_get_user_history(self):
        hist = self.history.get_user_history(1)
        self.assertEqual(len(hist), 3)
        self.assertEqual(hist[0].footprint, 5000)
        self.assertEqual(hist[-1].footprint, 4000)
        
        hist2 = self.history.get_user_history(2)
        self.assertEqual(len(hist2), 1)
        
        hist3 = self.history.get_user_history(999)
        self.assertEqual(len(hist3), 0)

    def test_calculate_trends(self):
        trends = self.history.calculate_trends(1, 'global')
        self.assertIsNotNone(trends)
        self.assertEqual(len(trends.footprints), 3)
        self.assertEqual(trends.footprints, [5000.0, 4500.0, 4000.0])
        
        # As footprint decreases, percentile should increase
        self.assertTrue(trends.percentiles[2] > trends.percentiles[0])
        
        trends_none = self.history.calculate_trends(999)
        self.assertIsNone(trends_none)

if __name__ == '__main__':
    unittest.main()
