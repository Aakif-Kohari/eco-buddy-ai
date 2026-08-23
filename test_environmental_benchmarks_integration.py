"""
Comprehensive End-to-End Integration Tests for Environmental Benchmarking.
Tests the entire lifecycle from DB insertion, history fetching, forecasting, 
profile comparison, recommendation generation, and UI normalization formatting.
"""
import unittest
import sqlite3
import os
import math
from datetime import datetime, timedelta
import random

from environmental_benchmarking.history import HistoryAnalyzer
from environmental_benchmarking.engine import BenchmarkEngine
from environmental_benchmarking.recommendations import RecommendationEngine
from environmental_benchmarking.models import UserAssessment
from environmental_benchmarking.advanced_math import DataNormalizer, TrendForecaster
from environmental_benchmarking.profiles_extended import get_default_profiles_extended

class TestEnvironmentalBenchmarkingIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.db_path = "test_eb_integration.db"
        cls.conn = sqlite3.connect(cls.db_path)
        cursor = cls.conn.cursor()
        
        # Setup schema mirroring the real DB
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transport TEXT,
            distance REAL,
            electricity REAL,
            diet TEXT,
            flights INTEGER,
            footprint REAL,
            eco_score INTEGER,
            trip_id TEXT
        )
        """)
        
        # Populate with 2 years of synthetic history for User 1 (Consistent reduction)
        base_date = datetime.now() - timedelta(days=700)
        for i in range(24): # 24 months
            dt = base_date + timedelta(days=30 * i)
            # simulate footprint going down from 20000 to 5000 over 2 years
            fp = 20000.0 - (15000.0 * (i / 23.0))
            # eco score going up from 20 to 85
            es = 20 + int(65.0 * (i / 23.0))
            
            cursor.execute("""
                INSERT INTO assessments 
                (user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, dt.isoformat(), 'car', max(0, 100 - i*2), 500 - i*10, 'average', max(0, 5 - i//4), fp, es))
            
        # Populate for User 2 (Volatile/Random)
        for i in range(12):
            dt = base_date + timedelta(days=60 * i)
            cursor.execute("""
                INSERT INTO assessments 
                (user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (2, dt.isoformat(), 'flight', random.uniform(500, 2000), random.uniform(300, 800), 'meat_heavy', random.randint(0, 5), random.uniform(10000, 30000), random.randint(10, 60)))
            
        cls.conn.commit()

        cls.engine = BenchmarkEngine()
        cls.history_analyzer = HistoryAnalyzer(db_path=cls.db_path)
        cls.recommendation_engine = RecommendationEngine()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def test_full_user1_lifecycle(self):
        """Test the lifecycle for the consistently improving user."""
        history = self.history_analyzer.get_user_history(user_id=1)
        self.assertEqual(len(history), 24)
        
        # Oldest assessment
        first_assessment = history[0]
        self.assertAlmostEqual(first_assessment.footprint, 20000.0)
        
        # Newest assessment
        latest_assessment = history[-1]
        self.assertAlmostEqual(latest_assessment.footprint, 5000.0)
        
        # Compare latest assessment to global
        result = self.engine.compare_assessment(latest_assessment, 'global')
        self.assertEqual(result.profile_name, 'Global Average')
        self.assertEqual(result.user_id, 1)
        
        # Since global median is ~4000 and 5000 is slightly worse than median but better than p75 (6000)
        # the percentile should be reasonably good (e.g. between 25 and 50)
        fp_comp = result.categories['footprint']
        self.assertTrue(25.0 <= fp_comp.percentile <= 50.0)
        
        # Compare first assessment (20000.0) - should be terrible
        first_result = self.engine.compare_assessment(first_assessment, 'global')
        fp_comp_first = first_result.categories['footprint']
        self.assertTrue(fp_comp_first.percentile < 10.0) # Bottom 10%
        
        # Validate recommendations
        recs = self.recommendation_engine.generate_recommendations(result.categories)
        self.assertIsInstance(recs, list)
        
        # Test Trends
        trends = self.history_analyzer.calculate_trends(user_id=1, profile_id='global')
        self.assertEqual(len(trends.footprints), 24)
        # Percentiles should be increasing over time
        self.assertTrue(trends.percentiles[-1] > trends.percentiles[0])

    def test_full_user2_lifecycle(self):
        """Test the lifecycle for the highly volatile user."""
        history = self.history_analyzer.get_user_history(user_id=2)
        self.assertEqual(len(history), 12)
        
        trends = self.history_analyzer.calculate_trends(user_id=2, profile_id='us')
        self.assertEqual(len(trends.footprints), 12)
        
        forecast = self.history_analyzer.get_forecast(user_id=2, periods=3)
        self.assertEqual(len(forecast["predicted_footprints"]), 3)
        # Volatile users should have lower confidence
        self.assertTrue(0.0 <= forecast["confidence"] < 100.0)

    def test_cross_profile_comparisons(self):
        """Test the same assessment against multiple profiles to verify ranking changes."""
        latest = self.history_analyzer.get_user_history(user_id=1)[-1]
        
        # Against US (High emissions average)
        res_us = self.engine.compare_assessment(latest, 'us')
        # Against Target (Very low emissions average)
        res_tgt = self.engine.compare_assessment(latest, 'target')
        
        # 5000 footprint is great for US, terrible for Target
        pct_us = res_us.categories['footprint'].percentile
        pct_tgt = res_tgt.categories['footprint'].percentile
        
        self.assertTrue(pct_us > pct_tgt)

    def test_ui_data_preparation(self):
        """Test that data can be correctly formatted for the UI layer."""
        latest = self.history_analyzer.get_user_history(user_id=1)[-1]
        res = self.engine.compare_assessment(latest, 'eu')
        
        ui_metrics = []
        for cat, comp in res.categories.items():
            if cat in ["footprint", "eco_score"]: continue
            ui_metrics.append({
                "Category": cat.capitalize(),
                "Your Value": f"{comp.user_value:,.1f}",
                "Profile Avg": f"{comp.reference_mean:,.1f}",
                "% Difference": f"{comp.percentage_difference:+.1f}%",
                "Percentile": f"{comp.percentile:.1f}",
                "Status": "✅ Better" if comp.is_better_than_average else "❌ Worse"
            })
            
        self.assertEqual(len(ui_metrics), 4)
        self.assertTrue(all("Category" in m for m in ui_metrics))
        
    def test_advanced_math_projection_on_db_data(self):
        """Test forecasting against real DB data curves."""
        trends = self.history_analyzer.calculate_trends(user_id=1)
        # Historical footprint went from 20000 down to 5000 linearly
        # So the forecast for next period should be strictly < 5000
        forecast = TrendForecaster.forecast_next_periods(trends.footprints, periods=1)
        self.assertEqual(len(forecast), 1)
        
        # It's going down, so the next one should be lower than the last one
        self.assertTrue(forecast[0] < trends.footprints[-1])
        # It shouldn't predict negative
        self.assertTrue(forecast[0] >= 0.0)
        
        conf = TrendForecaster.calculate_projection_confidence(trends.footprints)
        # Perfect linear drop -> should be nearly 100% confidence
        self.assertAlmostEqual(conf, 100.0, delta=1.0)

    def test_edge_case_empty_db(self):
        """Test behavior when user has no DB history."""
        hist = self.history_analyzer.get_user_history(user_id=999)
        self.assertEqual(len(hist), 0)
        
        trends = self.history_analyzer.calculate_trends(user_id=999)
        self.assertIsNone(trends)
        
        forecast = self.history_analyzer.get_forecast(user_id=999)
        self.assertEqual(forecast["predicted_footprints"], [])
        self.assertEqual(forecast["confidence"], 0.0)

    def test_all_extended_profiles_exist(self):
        """Verify the extended profiles dataset is fully loaded by the engine."""
        profiles = self.engine.get_all_profiles()
        # Should include global, us, eu, in, target, plus all the dynamically loaded ones like ES, IT, NL, etc.
        self.assertTrue(len(profiles) > 15)
        self.assertTrue(any(p.id == 'es' for p in profiles))
        self.assertTrue(any(p.id == 'nl' for p in profiles))
        self.assertTrue(any(p.id == 'za' for p in profiles))

if __name__ == '__main__':
    unittest.main()

    def test_advanced_stats_and_recommendation_synergy(self):
        """
        Test that recommendations correctly map to normalized scores and Z-scores.
        This tests the synergy between the advanced mathematical models and the 
        final user-facing strings generated by the engine.
        """
        latest = self.history_analyzer.get_user_history(user_id=1)[-1]
        res = self.engine.compare_assessment(latest, 'target')
        
        # Test Z-score correlation
        z = DataNormalizer.z_score_normalize(
            latest.footprint, 
            res.categories['footprint'].reference_mean, 
            self.engine.profiles['target'].footprint_stat.std_dev
        )
        
        # The user's footprint is 5000, which is extremely high for 'target' (avg ~2000)
        self.assertTrue(z > 1.5)
        
        # Since it's a terrible score relative to 'target', recommendations should be critical
        recs = self.recommendation_engine.generate_recommendations(res.categories)
        has_critical = any("CRITICAL" in r for r in recs)
        self.assertTrue(has_critical, f"Expected CRITICAL recommendations for Z-score {z}, got {recs}")
        
        # Conversely, if we test against US, Z-score should be good
        res_us = self.engine.compare_assessment(latest, 'us')
        z_us = DataNormalizer.z_score_normalize(
            latest.footprint, 
            res_us.categories['footprint'].reference_mean, 
            self.engine.profiles['us'].footprint_stat.std_dev
        )
        self.assertTrue(z_us < -0.5) # better than average
        recs_us = self.recommendation_engine.generate_recommendations(res_us.categories)
        self.assertFalse(any("CRITICAL" in r for r in recs_us))
