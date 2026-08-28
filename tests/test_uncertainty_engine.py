import unittest
from unittest.mock import patch

from src.carbon.emissions import (
    apply_uncertainty_bounds,
    calculate_footprint,
    calculate_footprint_range,
    fetch_emission_factors,
    rank_uncertainty_contributors,
)


class TestUncertaintyEngine(unittest.TestCase):

    def setUp(self):
        fetch_emission_factors.clear()

    @patch("src.carbon.emissions.os.environ.get")
    def test_range_matches_deterministic_total_and_is_ordered(self, mock_env_get):
        # No API key -> static-v1 factors are used for both calls.
        mock_env_get.return_value = None

        total, _contributors = calculate_footprint(
            transport="Car", distance=20, electricity=250,
            diet="Non-Vegetarian", flights=2, region="US",
        )

        result = calculate_footprint_range(
            transport="Car", distance=20, electricity=250,
            diet="Non-Vegetarian", flights=2, region="US",
        )

        # Backward compatibility: the deterministic call is untouched, and
        # the range's central estimate agrees with it.
        self.assertAlmostEqual(result["central_kg"], total, places=1)

        # Bounds are properly ordered and non-degenerate for static-v1
        # (documented uncertainty is 25%).
        self.assertLess(result["low_kg"], result["central_kg"])
        self.assertLess(result["central_kg"], result["high_kg"])
        self.assertEqual(result["factor_version"], "static-v1")
        self.assertGreater(result["uncertainty_percent"], 0)

        # Provenance/version is preserved on the range result too.
        self.assertEqual(result["provenance"]["factor_version"], "static-v1")

    @patch("src.carbon.emissions.os.environ.get")
    def test_zero_activity_categories_collapse_to_a_zero_range(self, mock_env_get):
        mock_env_get.return_value = None

        result = calculate_footprint_range(
            transport="Walking", distance=0, electricity=0,
            diet="Vegetarian", flights=0, region="Global",
        )

        # Zero-valued categories have zero width; diet is a fixed annual
        # constant so it still carries a genuine range.
        self.assertEqual(result["category_bounds"]["transport"]["range_kg"], 0.0)
        self.assertEqual(result["category_bounds"]["electricity"]["range_kg"], 0.0)
        self.assertEqual(result["category_bounds"]["flights"]["range_kg"], 0.0)
        self.assertGreater(result["category_bounds"]["diet"]["range_kg"], 0.0)
        self.assertEqual(result["low_kg"], result["category_bounds"]["diet"]["low_kg"])

    def test_uncertainty_contributors_are_ranked_largest_first(self):
        bounds = apply_uncertainty_bounds(
            {"transport": 1000.0, "electricity": 100.0, "diet": 10.0, "flights": 0.0},
            uncertainty_percent=25.0,
        )
        ranked = rank_uncertainty_contributors(bounds)

        self.assertEqual(ranked[0]["category"], "transport")
        self.assertEqual(ranked[-1]["category"], "flights")
        self.assertAlmostEqual(sum(r["share_percent"] for r in ranked), 100.0, places=0)

    def test_apply_uncertainty_bounds_zero_total_range_gives_zero_shares(self):
        # Boundary case: every category is zero, so there is no range to
        # attribute uncertainty to. Shares must not divide by zero.
        bounds = apply_uncertainty_bounds({"a": 0.0, "b": 0.0}, uncertainty_percent=25.0)
        ranked = rank_uncertainty_contributors(bounds)

        self.assertTrue(all(r["share_percent"] == 0.0 for r in ranked))


if __name__ == "__main__":
    unittest.main()