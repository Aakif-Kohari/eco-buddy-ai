"""
Extended test suite for advanced environmental benchmarking features.
"""
import unittest
import math
from environmental_benchmarking.advanced_math import DataNormalizer, TrendForecaster
from environmental_benchmarking.recommendations import RecommendationEngine
from environmental_benchmarking.models import CategoryComparison

class TestDataNormalizer(unittest.TestCase):
    
    def test_min_max_normalize(self):
        self.assertAlmostEqual(DataNormalizer.min_max_normalize(50, 0, 100), 0.5)
        self.assertAlmostEqual(DataNormalizer.min_max_normalize(150, 0, 100), 1.0)
        self.assertAlmostEqual(DataNormalizer.min_max_normalize(-50, 0, 100), 0.0)
        
        # Inverted
        self.assertAlmostEqual(DataNormalizer.min_max_normalize(25, 0, 100, invert=True), 0.75)
        
        # Edge cases
        self.assertEqual(DataNormalizer.min_max_normalize(math.nan, 0, 100), 0.5)
        self.assertEqual(DataNormalizer.min_max_normalize(50, 100, 100), 0.5) # zero range

    def test_z_score_normalize(self):
        self.assertAlmostEqual(DataNormalizer.z_score_normalize(120, 100, 10), 2.0)
        self.assertAlmostEqual(DataNormalizer.z_score_normalize(80, 100, 10), -2.0)
        self.assertEqual(DataNormalizer.z_score_normalize(120, 100, 0), 0.0)

    def test_sigmoid_normalize(self):
        # Sigmoid of 0 is 0.5
        self.assertAlmostEqual(DataNormalizer.sigmoid_normalize(100, 100, 10), 0.5)
        # Large positive should approach 1
        self.assertTrue(DataNormalizer.sigmoid_normalize(200, 100, 10) > 0.99)
        # Large negative should approach 0
        self.assertTrue(DataNormalizer.sigmoid_normalize(0, 100, 10) < 0.01)
        self.assertEqual(DataNormalizer.sigmoid_normalize(150, 100, 0), 0.5)
        
    def test_robust_scale(self):
        self.assertAlmostEqual(DataNormalizer.robust_scale(75, 50, 25, 75), 0.5) # (75-50)/50
        self.assertEqual(DataNormalizer.robust_scale(100, 50, 50, 50), 0.0) # zero iqr

class TestTrendForecaster(unittest.TestCase):
    
    def test_simple_linear_regression(self):
        x = [0, 1, 2, 3, 4]
        y = [10, 20, 30, 40, 50]
        slope, intercept = TrendForecaster.simple_linear_regression(x, y)
        self.assertAlmostEqual(slope, 10.0)
        self.assertAlmostEqual(intercept, 10.0)
        
        # Edge cases
        s, i = TrendForecaster.simple_linear_regression([1], [10])
        self.assertEqual(s, 0.0)
        self.assertEqual(i, 10.0)
        
        s, i = TrendForecaster.simple_linear_regression([], [])
        self.assertEqual(s, 0.0)
        self.assertEqual(i, 0.0)
        
        # Zero denominator case (all x same)
        s, i = TrendForecaster.simple_linear_regression([1, 1], [10, 20])
        self.assertEqual(s, 0.0)
        self.assertEqual(i, 15.0)

    def test_forecast_next_periods(self):
        history = [100, 90, 80] # decreasing by 10 each time
        preds = TrendForecaster.forecast_next_periods(history, 2)
        self.assertAlmostEqual(preds[0], 70.0)
        self.assertAlmostEqual(preds[1], 60.0)
        
        # Clamp at zero
        history_fast_drop = [100, 50, 0]
        preds2 = TrendForecaster.forecast_next_periods(history_fast_drop, 2)
        self.assertEqual(preds2[0], 0.0) # would be -50 but clamped
        
        self.assertEqual(TrendForecaster.forecast_next_periods([]), [])
        self.assertEqual(TrendForecaster.forecast_next_periods([50], 3), [50, 50, 50])

    def test_calculate_projection_confidence(self):
        # Perfect line = 100% confidence
        conf1 = TrendForecaster.calculate_projection_confidence([10, 20, 30, 40])
        self.assertAlmostEqual(conf1, 100.0)
        
        # No variance (flat line) -> R^2 denominator is 0 -> mapped to 100
        conf2 = TrendForecaster.calculate_projection_confidence([10, 10, 10])
        self.assertAlmostEqual(conf2, 100.0)
        
        # High variance -> low confidence
        conf3 = TrendForecaster.calculate_projection_confidence([10, 100, 10, 100])
        self.assertLess(conf3, 20.0)

class TestRecommendationEngine(unittest.TestCase):
    
    def setUp(self):
        self.re = RecommendationEngine()
        
    def _make_comp(self, cat, pct, val=0):
        return CategoryComparison(
            category_name=cat,
            user_value=val,
            reference_mean=100,
            reference_median=100,
            percentile=pct,
            is_better_than_average=pct>50,
            difference_from_mean=0,
            percentage_difference=0,
            normalized_score=pct
        )
        
    def test_transport_recs(self):
        recs = self.re.generate_recommendations({"transport": self._make_comp("transport", 10)})
        self.assertTrue(any("CRITICAL" in r for r in recs))
        
        recs2 = self.re.generate_recommendations({"transport": self._make_comp("transport", 30)})
        self.assertTrue(any("cycling or walking" in r for r in recs2))
        
        recs3 = self.re.generate_recommendations({"transport": self._make_comp("transport", 90)})
        self.assertTrue(any("EXCELLENT" in r for r in recs3))
        
    def test_electricity_recs(self):
        recs = self.re.generate_recommendations({"electricity": self._make_comp("electricity", 15)})
        self.assertTrue(any("CRITICAL" in r for r in recs))
        
        recs2 = self.re.generate_recommendations({"electricity": self._make_comp("electricity", 35)})
        self.assertTrue(any("LED" in r for r in recs2))
        
    def test_diet_recs(self):
        recs = self.re.generate_recommendations({"diet": self._make_comp("diet", 15)})
        self.assertTrue(any("CRITICAL" in r for r in recs))
        
    def test_flight_recs(self):
        recs = self.re.generate_recommendations({"flights": self._make_comp("flights", 10, 2500)})
        self.assertTrue(any("dominating" in r for r in recs))
        
        recs2 = self.re.generate_recommendations({"flights": self._make_comp("flights", 10, 500)})
        self.assertEqual(len(recs2), 0) # Below threshold for the specific high absolute value rule

if __name__ == '__main__':
    unittest.main()
