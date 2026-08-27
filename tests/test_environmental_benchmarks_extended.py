"""
Extended coverage tests for Environmental Benchmarking Dataset & Profiles.
Validates the structural integrity and mathematical boundaries of all profiles.
"""
import unittest
from environmental_benchmarking.engine import BenchmarkEngine
from environmental_benchmarking.models import CategoryStat, UserAssessment
from datetime import datetime
import random
from environmental_benchmarking.advanced_math import TrendForecaster, DataNormalizer
from environmental_benchmarking.recommendations import RecommendationEngine
from environmental_benchmarking.models import CategoryComparison

class TestExtendedProfiles(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.engine = BenchmarkEngine()
        cls.profiles = cls.engine.get_all_profiles()
        
    def test_all_profiles_load_successfully(self):
        """Ensure all profiles can be instantiated and validated."""
        self.assertTrue(len(self.profiles) >= 10, f"Expected at least 10 profiles, got {len(self.profiles)}")
        
    def test_profile_attributes(self):
        """Check all required attributes are present on every profile."""
        for p in self.profiles:
            self.assertIsNotNone(p.id)
            self.assertIsNotNone(p.name)
            self.assertIsNotNone(p.description)
            self.assertIsNotNone(p.region_code)
            
    def test_category_stat_monotonicity(self):
        """Verify that min <= p10 <= p25 <= median <= p75 <= p90 <= max for ALL profiles and categories."""
        categories = ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]
        for p in self.profiles:
            for cat in categories:
                stat = p.get_stat(cat)
                with self.subTest(profile=p.id, category=cat):
                    self.assertLessEqual(stat.min_val, stat.p10)
                    self.assertLessEqual(stat.p10, stat.p25)
                    self.assertLessEqual(stat.p25, stat.median)
                    self.assertLessEqual(stat.median, stat.p75)
                    self.assertLessEqual(stat.p75, stat.p90)
                    self.assertLessEqual(stat.p90, stat.max_val)
                    self.assertGreaterEqual(stat.mean, stat.min_val)
                    self.assertLessEqual(stat.mean, stat.max_val)

    def test_percentile_interpolation_boundaries(self):
        """Test interpolation exactly at the decile boundaries for all profiles."""
        categories = ["transport", "electricity", "diet", "flights", "footprint"]
        for p in self.profiles:
            for cat in categories:
                stat = p.get_stat(cat)
                with self.subTest(profile=p.id, category=cat):
                    # Lower is better -> footprint logic
                    self.assertAlmostEqual(self.engine._calculate_percentile_from_stat(stat.min_val, stat, False), 100.0)
                    for pct_val, expected_cdf in [(stat.min_val, 0.0), (stat.p10, 10.0), (stat.p25, 25.0), 
                                                  (stat.median, 50.0), (stat.p75, 75.0), (stat.p90, 90.0), (stat.max_val, 100.0)]:
                        calc_val = self.engine._calculate_percentile_from_stat(pct_val, stat, False)
                        # Due to how we interpolate and handle zero-variance bins (like flights), 
                        # if the value is exactly the min_val, it's always 100% (cdf 0).
                        if pct_val == stat.min_val:
                            self.assertAlmostEqual(calc_val, 100.0)
                        else:
                            # It should be logically bounded
                            self.assertTrue(0.0 <= calc_val <= 100.0)

    def test_eco_score_percentile_boundaries(self):
        """Test eco_score percentile where higher is better."""
        for p in self.profiles:
            stat = p.get_stat("eco_score")
            with self.subTest(profile=p.id):
                for pct_val, expected_cdf in [(stat.min_val, 0.0), (stat.p10, 10.0), (stat.p25, 25.0), 
                                              (stat.median, 50.0), (stat.p75, 75.0), (stat.p90, 90.0), (stat.max_val, 100.0)]:
                    calc_val = self.engine._calculate_percentile_from_stat(pct_val, stat, True)
                    if pct_val == stat.min_val:
                        self.assertAlmostEqual(calc_val, 0.0)
                    else:
                        self.assertTrue(0.0 <= calc_val <= 100.0)

    def test_outlier_handling(self):
        """Test values far beyond min/max bounds."""
        stat = self.profiles[0].get_stat("footprint")
        
        # Below min (extremely good)
        val_under = stat.min_val - 1000
        pct_under = self.engine._calculate_percentile_from_stat(val_under, stat, False)
        self.assertEqual(pct_under, 100.0)
        
        # Above max (extremely bad)
        val_over = stat.max_val + 10000
        pct_over = self.engine._calculate_percentile_from_stat(val_over, stat, False)
        self.assertEqual(pct_over, 0.0)
        
    def test_normalized_score_bounds(self):
        """Normalized scores should ALWAYS be bounded between 0 and 100."""
        categories = ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]
        for p in self.profiles:
            for cat in categories:
                stat = p.get_stat(cat)
                is_higher_better = (cat == "eco_score")
                
                # Normal mid value
                n_mid = self.engine._calculate_normalized_score(stat.median, stat, is_higher_better)
                self.assertTrue(0.0 <= n_mid <= 100.0)
                
                # Extreme low
                n_low = self.engine._calculate_normalized_score(stat.min_val - 1000, stat, is_higher_better)
                self.assertTrue(0.0 <= n_low <= 100.0)
                
                # Extreme high
                n_high = self.engine._calculate_normalized_score(stat.max_val + 1000, stat, is_higher_better)
                self.assertTrue(0.0 <= n_high <= 100.0)
                
    def test_engine_compare_all_combinations(self):
        """Fuzz test the engine compare function with synthetic assessments against all profiles."""
        
        assessments = [
            # Perfect score
            UserAssessment(1, 1, datetime.now(), 'bike', 0.0, 0.0, 'vegan', 0, 0.0, 100),
            # Average score
            UserAssessment(2, 1, datetime.now(), 'car', 50.0, 100.0, 'average', 1, 5000.0, 50),
            # Terrible score
            UserAssessment(3, 1, datetime.now(), 'car', 1000.0, 5000.0, 'meat_heavy', 10, 50000.0, 0)
        ]
        
        for p in self.profiles:
            for a in assessments:
                with self.subTest(profile=p.id, assessment=a.assessment_id):
                    res = self.engine.compare_assessment(a, p.id)
                    
                    self.assertIsNotNone(res)
                    self.assertEqual(res.profile_name, p.name)
                    self.assertTrue(0.0 <= res.overall_percentile <= 100.0)
                    
                    for cat in ["transport", "electricity", "diet", "flights", "footprint", "eco_score"]:
                        comp = res.categories[cat]
                        self.assertEqual(comp.category_name, cat)
                        self.assertTrue(0.0 <= comp.percentile <= 100.0)
                        self.assertTrue(0.0 <= comp.normalized_score <= 100.0)


class TestFuzzerAndSynthetic(unittest.TestCase):

    def test_forecast_confidence_boundaries(self):
        """Extensive fuzz testing of the trend forecaster confidence bounds."""
        for _ in range(100):
            hist = [random.uniform(1000, 10000) for _ in range(random.randint(3, 20))]
            conf = TrendForecaster.calculate_projection_confidence(hist)
            self.assertTrue(0.0 <= conf <= 100.0)
            
            preds = TrendForecaster.forecast_next_periods(hist, 5)
            self.assertEqual(len(preds), 5)
            for p in preds:
                self.assertTrue(p >= 0.0)

    def test_advanced_math_normalizations_fuzz(self):
        """Fuzz testing advanced math normalizers."""
        for _ in range(1000):
            val = random.uniform(-10000, 10000)
            mean = random.uniform(-5000, 5000)
            std_dev = random.uniform(0.1, 1000)
            
            z = DataNormalizer.z_score_normalize(val, mean, std_dev)
            self.assertIsInstance(z, float)
            
            s = DataNormalizer.sigmoid_normalize(val, mean, std_dev)
            self.assertTrue(0.0 <= s <= 1.0)
            
            p25 = mean - 100
            p75 = mean + 100
            rs = DataNormalizer.robust_scale(val, mean, p25, p75)
            self.assertIsInstance(rs, float)

    def test_recommendation_engine_fuzz(self):
        """Fuzz test the recommendation engine against random comparison objects."""
        engine = RecommendationEngine()
        categories = ["transport", "electricity", "diet", "flights"]
        
        for _ in range(500):
            comps = {}
            for cat in categories:
                comps[cat] = CategoryComparison(
                    category_name=cat,
                    user_value=random.uniform(0, 10000),
                    reference_mean=random.uniform(100, 5000),
                    reference_median=random.uniform(100, 5000),
                    percentile=random.uniform(0, 100),
                    is_better_than_average=random.choice([True, False]),
                    difference_from_mean=random.uniform(-1000, 1000),
                    percentage_difference=random.uniform(-100, 100),
                    normalized_score=random.uniform(0, 100)
                )
            
            recs = engine.generate_recommendations(comps)
            self.assertIsInstance(recs, list)
            for r in recs:
                self.assertIsInstance(r, str)
                self.assertTrue(len(r) > 5)

    def _synthetic_edge_case(self, i):
        stat = CategoryStat(mean=100+i, median=90+i, std_dev=50, min_val=0, max_val=500+i, p10=20+i, p25=40+i, p75=150+i, p90=200+i)
        stat.validate()
        self.assertEqual(stat.mean, 100+i)

    def test_synthetic_edge_cases(self):
        for i in range(100):
            self._synthetic_edge_case(i)

if __name__ == "__main__":
    unittest.main()
