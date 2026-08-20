"""Tests for the spend-based input-output footprint.

The claim being tested is that a direct emission factor is not a footprint, and
that the gap is a supply chain rather than a fudge factor. So the central tests
are the ones that pin the closed-form inverse against the power series it is the
limit of, and that check the truncated series climbs monotonically towards it -
because "a per-category factor is the one-term truncation" is the whole argument
and it should be visible in the numbers rather than asserted in a docstring.

The rest is guarding the table: a non-productive column, a singular matrix and a
column of margins that eat the whole price are all inputs that produce a
plausible-looking number rather than an error, which is the dangerous kind of
bug for a model nobody can check by eye.
"""

import os
import tempfile
import unittest

import eeio_spend as ee


SAMPLE_SPEND = {
    "hospitality": 1200.0,
    "food_manufacturing": 2400.0,
    "electricity": 900.0,
    "gas_supply": 700.0,
    "textiles": 600.0,
    "passenger_transport": 800.0,
    "recreation": 400.0,
    "communication": 500.0,
}


class TestSectorTable(unittest.TestCase):
    """The table everything else is a rearrangement of."""

    def test_every_sector_has_a_direct_intensity(self):
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertIn(key, ee.DIRECT_INTENSITY)
                self.assertGreater(ee.DIRECT_INTENSITY[key], 0.0)

    def test_every_sector_has_margin_rates(self):
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertIn(key, ee.MARGIN_RATES)

    def test_every_sector_has_coefficients(self):
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertIn(key, ee.TECHNICAL_COEFFICIENTS)

    def test_every_sector_carries_a_label_and_examples(self):
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                entry = ee.get_sector(key)
                self.assertTrue(entry["label"])
                self.assertTrue(entry["examples"])

    def test_unknown_sector_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.get_sector("teleportation")

    def test_overlap_targets_are_real_sectors(self):
        for key in ee.PHYSICAL_OVERLAP:
            with self.subTest(sector=key):
                self.assertIn(key, ee.SECTORS)


class TestMatrix(unittest.TestCase):
    """Building A, and refusing an A that cannot be inverted meaningfully."""

    def test_matrix_is_square_and_the_right_size(self):
        matrix = ee.build_matrix()
        self.assertEqual(len(matrix), len(ee.list_sectors()))
        for row in matrix:
            self.assertEqual(len(row), len(ee.list_sectors()))

    def test_declaration_is_transposed_correctly(self):
        # Declared column-wise by consumer; A[i][j] must be input i per unit j.
        matrix = ee.build_matrix()
        order = ee.list_sectors()
        i = order.index("agriculture")
        j = order.index("food_manufacturing")
        self.assertAlmostEqual(
            matrix[i][j],
            ee.TECHNICAL_COEFFICIENTS["food_manufacturing"]["agriculture"],
        )

    def test_no_negative_coefficients(self):
        for consumer, inputs in ee.TECHNICAL_COEFFICIENTS.items():
            for supplier, value in inputs.items():
                with self.subTest(edge=f"{supplier}->{consumer}"):
                    self.assertGreaterEqual(value, 0.0)

    def test_the_shipped_table_is_productive(self):
        self.assertTrue(ee.check_productive())

    def test_every_column_sums_below_one(self):
        for key, total in ee.column_sums().items():
            with self.subTest(sector=key):
                self.assertLess(total, 1.0)

    def test_a_non_productive_column_is_refused_by_name(self):
        matrix = ee.build_matrix()
        order = ee.list_sectors()
        col = order.index("hospitality")
        for row in range(len(order)):
            matrix[row][col] = 0.9  # far more than a unit of output
        with self.assertRaises(ee.EEIOError) as caught:
            ee.check_productive(matrix)
        self.assertIn("hospitality", str(caught.exception))

    def test_a_column_summing_to_exactly_one_is_refused(self):
        size = len(ee.list_sectors())
        matrix = [[0.0] * size for _ in range(size)]
        matrix[0][0] = 1.0
        with self.assertRaises(ee.EEIOError):
            ee.check_productive(matrix)


class TestLeontiefInverse(unittest.TestCase):
    """The closed form, and the thing it is the closed form of."""

    def test_inverse_times_i_minus_a_is_the_identity(self):
        matrix = ee.build_matrix()
        inverse = ee.leontief_inverse(matrix)
        size = len(matrix)
        for i in range(size):
            for j in range(size):
                product = sum(
                    ((1.0 if i == k else 0.0) - matrix[i][k]) * inverse[k][j]
                    for k in range(size)
                )
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(product, expected, places=9)

    def test_diagonal_is_at_least_one(self):
        # A unit of final demand always requires at least a unit of itself.
        inverse = ee.leontief_inverse()
        for n in range(len(inverse)):
            with self.subTest(sector=ee.list_sectors()[n]):
                self.assertGreaterEqual(inverse[n][n], 1.0)

    def test_no_negative_entries(self):
        # Guaranteed for a productive non-negative A. A negative entry here
        # means the productivity check let something through.
        for row in ee.leontief_inverse():
            for value in row:
                self.assertGreaterEqual(value, -1e-12)

    def test_a_singular_matrix_is_refused(self):
        size = len(ee.list_sectors())
        matrix = [[0.0] * size for _ in range(size)]
        for row in range(size):
            matrix[row][0] = 1.0 / size  # makes (I - A) singular
            matrix[row][1] = 1.0 / size
        with self.assertRaises(ee.EEIOError):
            ee.leontief_inverse(matrix)

    def test_pivoting_survives_a_zero_on_the_diagonal(self):
        # Several real sectors have no own-use coefficient. Without partial
        # pivoting the elimination dies on a matrix that is perfectly fine.
        size = len(ee.list_sectors())
        matrix = [[0.0] * size for _ in range(size)]
        matrix[1][0] = 0.5
        matrix[0][1] = 0.5
        inverse = ee.leontief_inverse(matrix)
        self.assertAlmostEqual(inverse[0][0], 4.0 / 3.0, places=9)


class TestIntensities(unittest.TestCase):
    """Total intensity, and why it is bigger than the direct one."""

    def test_total_is_never_below_direct(self):
        totals = ee.total_intensities()
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertGreaterEqual(totals[key], ee.DIRECT_INTENSITY[key] - 1e-12)

    def test_power_series_converges_to_the_inverse(self):
        # The two are derived independently. If they agree to six places the
        # elimination is right.
        totals = ee.total_intensities()
        series = ee.series_intensities(60)
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertAlmostEqual(series[key], totals[key], places=6)

    def test_truncation_climbs_towards_the_total(self):
        # This is the argument. A per-category factor is the one-term
        # truncation, and every extra tier of supply chain adds emissions.
        totals = ee.total_intensities()
        previous = {key: 0.0 for key in ee.list_sectors()}
        for terms in range(1, 9):
            current = ee.series_intensities(terms)
            for key in ee.list_sectors():
                with self.subTest(sector=key, terms=terms):
                    self.assertGreaterEqual(current[key], previous[key] - 1e-12)
                    self.assertLessEqual(current[key], totals[key] + 1e-9)
            previous = current

    def test_one_term_is_exactly_the_direct_intensity(self):
        series = ee.series_intensities(1)
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                self.assertAlmostEqual(series[key], ee.DIRECT_INTENSITY[key])

    def test_zero_terms_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.series_intensities(0)

    def test_electricity_is_mostly_direct(self):
        # The sanity check on the whole table: a sector that emits at the point
        # of production should have a small multiplier.
        self.assertLess(ee.multipliers()["electricity"], 1.6)

    def test_hospitality_is_mostly_upstream(self):
        # And a sector that buys everything in should have a large one. If
        # these two were close, the coefficients would be wrong.
        self.assertGreater(ee.multipliers()["hospitality"], 3.0)

    def test_services_have_larger_multipliers_than_utilities(self):
        multipliers = ee.multipliers()
        for service in ("hospitality", "finance", "recreation"):
            for utility in ("electricity", "gas_supply"):
                with self.subTest(service=service, utility=utility):
                    self.assertGreater(multipliers[service], multipliers[utility])

    def test_tier_contributions_are_cumulative(self):
        rows = ee.tier_contributions("hospitality", tiers=6)
        self.assertEqual(len(rows), 6)
        for earlier, later in zip(rows, rows[1:]):
            self.assertGreaterEqual(later["cumulative"], earlier["cumulative"])
            self.assertGreaterEqual(later["added"], -1e-9)

    def test_tier_contributions_reject_unknown_sectors(self):
        with self.assertRaises(ee.EEIOError):
            ee.tier_contributions("nowhere")


class TestPrices(unittest.TestCase):
    """Deflation and the margin split."""

    def test_deflating_to_the_same_year_changes_nothing(self):
        self.assertAlmostEqual(ee.deflate(100.0, 2020, 2020), 100.0)

    def test_later_money_is_worth_less_in_base_prices(self):
        self.assertLess(ee.deflate(100.0, 2026), 100.0)

    def test_earlier_money_is_worth_more_in_base_prices(self):
        self.assertGreater(ee.deflate(100.0, 2016), 100.0)

    def test_deflation_round_trips(self):
        there = ee.deflate(250.0, 2026, 2020)
        back = ee.deflate(there, 2020, 2026)
        self.assertAlmostEqual(back, 250.0, places=9)

    def test_an_unknown_year_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.deflate(100.0, 1901)
        with self.assertRaises(ee.EEIOError):
            ee.deflate(100.0, 2020, 2100)

    def test_the_margin_split_conserves_money(self):
        for key in ee.list_sectors():
            with self.subTest(sector=key):
                split = ee.split_purchaser_price(key, 100.0)
                self.assertAlmostEqual(sum(split.values()), 100.0, places=9)

    def test_margins_go_to_retail_and_freight(self):
        split = ee.split_purchaser_price("textiles", 100.0)
        self.assertIn("retail", split)
        self.assertIn("freight", split)
        self.assertLess(split["textiles"], 100.0)

    def test_a_direct_supplied_sector_keeps_the_whole_price(self):
        split = ee.split_purchaser_price("electricity", 100.0)
        self.assertAlmostEqual(split["electricity"], 100.0, places=9)

    def test_negative_spend_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.split_purchaser_price("textiles", -5.0)

    def test_margins_that_eat_the_whole_price_are_refused(self):
        original = ee.MARGIN_RATES["textiles"]
        ee.MARGIN_RATES["textiles"] = {"retail": 0.7, "freight": 0.4}
        try:
            with self.assertRaises(ee.EEIOError):
                ee.split_purchaser_price("textiles", 100.0)
        finally:
            ee.MARGIN_RATES["textiles"] = original


class TestSpendFootprint(unittest.TestCase):
    """Turning money into kilograms."""

    def test_total_exceeds_direct_only(self):
        result = ee.spend_footprint(SAMPLE_SPEND)
        self.assertGreater(result["total_kg"], result["direct_only_kg"])
        self.assertGreater(result["understatement_factor"], 1.0)

    def test_lines_are_ordered_by_size(self):
        lines = ee.spend_footprint(SAMPLE_SPEND)["lines"]
        for earlier, later in zip(lines, lines[1:]):
            self.assertGreaterEqual(earlier["total_kg"], later["total_kg"])

    def test_more_spend_never_means_less_carbon(self):
        base = ee.spend_footprint(SAMPLE_SPEND)["total_kg"]
        more = dict(SAMPLE_SPEND)
        more["textiles"] += 500.0
        self.assertGreater(ee.spend_footprint(more)["total_kg"], base)

    def test_the_footprint_is_linear_in_spend(self):
        single = ee.spend_footprint({"hospitality": 100.0})["total_kg"]
        double = ee.spend_footprint({"hospitality": 200.0})["total_kg"]
        self.assertAlmostEqual(double, 2.0 * single, places=6)

    def test_splitting_margins_changes_the_answer(self):
        with_margins = ee.spend_footprint(SAMPLE_SPEND, apply_margins=True)
        without = ee.spend_footprint(SAMPLE_SPEND, apply_margins=False)
        self.assertNotAlmostEqual(with_margins["total_kg"], without["total_kg"])

    def test_nominal_spend_is_reported_unchanged(self):
        result = ee.spend_footprint(SAMPLE_SPEND, year=2026)
        self.assertAlmostEqual(result["nominal_spend"], sum(SAMPLE_SPEND.values()))

    def test_real_spend_is_below_nominal_for_a_later_year(self):
        result = ee.spend_footprint(SAMPLE_SPEND, year=2026)
        self.assertLess(result["real_spend"], result["nominal_spend"])

    def test_inflation_is_not_reported_as_emissions(self):
        # The same real basket, quoted in two years' money, must give the same
        # carbon. Skipping deflation is what turns inflation into growth.
        base = ee.spend_footprint({"textiles": 100.0}, year=2020)["total_kg"]
        inflated = 100.0 * ee.DEFLATORS[2026] / ee.DEFLATORS[2020]
        later = ee.spend_footprint({"textiles": inflated}, year=2026)["total_kg"]
        self.assertAlmostEqual(base, later, places=6)

    def test_empty_spend_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.spend_footprint({})

    def test_unknown_sector_in_spend_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.spend_footprint({"unicorns": 100.0})

    def test_negative_spend_in_a_profile_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.spend_footprint({"textiles": -100.0})

    def test_margins_add_retail_and_freight_lines(self):
        sectors = {
            row["sector"] for row in ee.spend_footprint({"textiles": 500.0})["lines"]
        }
        self.assertIn("retail", sectors)
        self.assertIn("freight", sectors)


class TestStructuralPaths(unittest.TestCase):
    """Saying where the number comes from."""

    def test_the_first_path_is_the_sector_itself(self):
        result = ee.structural_paths("hospitality", 1000.0)
        self.assertEqual(result["paths"][0]["path"][0], "hospitality")

    def test_paths_never_explain_more_than_the_total(self):
        for sector in ee.list_sectors():
            with self.subTest(sector=sector):
                result = ee.structural_paths(sector, 100.0)
                self.assertLessEqual(result["explained_kg"], result["total_kg"] + 1e-6)

    def test_the_unexplained_remainder_is_never_negative(self):
        for sector in ee.list_sectors():
            with self.subTest(sector=sector):
                self.assertGreaterEqual(
                    ee.structural_paths(sector, 100.0)["unexplained_kg"], -1e-6
                )

    def test_deeper_search_explains_more(self):
        shallow = ee.structural_paths("hospitality", 1000.0, max_depth=2)
        deep = ee.structural_paths("hospitality", 1000.0, max_depth=5)
        self.assertGreaterEqual(deep["explained_kg"], shallow["explained_kg"])

    def test_a_lower_threshold_explains_more(self):
        coarse = ee.structural_paths("hospitality", 1000.0, threshold=0.05)
        fine = ee.structural_paths("hospitality", 1000.0, threshold=0.001)
        self.assertGreaterEqual(fine["explained_kg"], coarse["explained_kg"])

    def test_paths_are_ordered_by_size(self):
        paths = ee.structural_paths("hospitality", 1000.0)["paths"]
        for earlier, later in zip(paths, paths[1:]):
            self.assertGreaterEqual(earlier["kg"], later["kg"])

    def test_a_zero_depth_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.structural_paths("hospitality", 100.0, max_depth=0)

    def test_unknown_sector_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.structural_paths("nowhere")

    def test_a_deep_enough_search_explains_most_of_it(self):
        result = ee.structural_paths("hospitality", 1000.0, max_depth=5, threshold=0.001)
        self.assertGreater(result["explained_share"], 0.75)


class TestHybrid(unittest.TestCase):
    """The subtraction that makes this safe to add to a physical inventory."""

    def test_overlap_is_declared_for_utilities(self):
        rows = ee.declare_overlap(SAMPLE_SPEND)
        sectors = {row["sector"] for row in rows}
        self.assertIn("electricity", sectors)
        self.assertIn("gas_supply", sectors)

    def test_declaring_overlap_on_an_unknown_sector_is_refused(self):
        with self.assertRaises(ee.EEIOError):
            ee.declare_overlap({"nowhere": 100.0})

    def test_hybrid_drops_the_sectors_covered_physically(self):
        result = ee.hybrid_footprint(
            SAMPLE_SPEND, {"home.electricity": 1400.0, "home.gas": 2200.0}
        )
        sectors = {row["sector"] for row in result["spend_detail"]["lines"]}
        self.assertNotIn("gas_supply", sectors)

    def test_hybrid_is_below_the_naive_sum(self):
        result = ee.hybrid_footprint(
            SAMPLE_SPEND, {"home.electricity": 1400.0, "home.gas": 2200.0}
        )
        self.assertLess(result["total_kg"], result["naive_total_kg"])
        self.assertGreater(result["double_count_avoided_kg"], 0.0)

    def test_no_physical_data_means_nothing_is_removed(self):
        result = ee.hybrid_footprint(SAMPLE_SPEND, {})
        self.assertAlmostEqual(
            result["double_count_avoided_kg"], 0.0, places=6
        )

    def test_the_displaced_spend_is_reported(self):
        result = ee.hybrid_footprint(SAMPLE_SPEND, {"home.electricity": 1400.0})
        self.assertIn("electricity", result["displaced_spend"])

    def test_physical_data_still_counts(self):
        result = ee.hybrid_footprint(SAMPLE_SPEND, {"home.electricity": 1400.0})
        self.assertAlmostEqual(result["physical_kg"], 1400.0)


class TestSensitivity(unittest.TestCase):
    """The variants, which are the argument for the full model."""

    def test_every_variant_is_reported(self):
        rows = ee.sensitivity(SAMPLE_SPEND, year=2026)
        self.assertGreaterEqual(len(rows), 7)
        for row in rows:
            with self.subTest(variant=row["variant"]):
                self.assertGreaterEqual(row["total_kg"], 0.0)
                self.assertTrue(row["note"])

    def test_direct_only_is_the_smallest_variant(self):
        rows = {row["variant"]: row["total_kg"] for row in ee.sensitivity(SAMPLE_SPEND)}
        self.assertLess(rows["Direct intensities only"], rows["Full model"])

    def test_truncated_variants_climb(self):
        rows = {row["variant"]: row["total_kg"] for row in ee.sensitivity(SAMPLE_SPEND)}
        self.assertLess(rows["Truncated at 1 tier"], rows["Truncated at 2 tiers"])
        self.assertLess(rows["Truncated at 2 tiers"], rows["Truncated at 3 tiers"])
        self.assertLess(rows["Truncated at 3 tiers"], rows["Truncated at 5 tiers"])
        self.assertLess(rows["Truncated at 5 tiers"], rows["Full model"])

    def test_a_non_base_year_adds_the_undeflated_variant(self):
        variants = {row["variant"] for row in ee.sensitivity(SAMPLE_SPEND, year=2026)}
        self.assertIn("Not deflated", variants)

    def test_the_base_year_has_no_undeflated_variant(self):
        variants = {row["variant"] for row in ee.sensitivity(SAMPLE_SPEND, year=2020)}
        self.assertNotIn("Not deflated", variants)


class TestInsights(unittest.TestCase):
    """The plain-language layer."""

    def test_insights_are_produced(self):
        insights = ee.get_eeio_insights(ee.spend_footprint(SAMPLE_SPEND))
        self.assertTrue(insights)
        for line in insights:
            self.assertIsInstance(line, str)

    def test_an_empty_result_says_so(self):
        self.assertEqual(
            ee.get_eeio_insights({"lines": []}), ["No spend to analyse."]
        )

    def test_the_overlap_warning_appears_when_it_should(self):
        insights = ee.get_eeio_insights(ee.spend_footprint({"electricity": 900.0}))
        self.assertTrue(any("physically" in line for line in insights))


class TestStorage(unittest.TestCase):
    """Persistence, against a throwaway database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = ee.DB_NAME
        ee.DB_NAME = self.path
        ee.init_eeio_db()

    def tearDown(self):
        ee.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_init_is_idempotent(self):
        self.assertTrue(ee.init_eeio_db())
        self.assertTrue(ee.init_eeio_db())

    def test_a_saved_profile_comes_back(self):
        result = ee.spend_footprint(SAMPLE_SPEND, year=2026)
        profile_id = ee.save_profile(1, "This year", result)
        self.assertIsNotNone(profile_id)
        profiles = ee.get_profiles(1)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "This year")
        self.assertAlmostEqual(profiles[0]["total_kg"], result["total_kg"], places=3)

    def test_detail_survives_the_round_trip(self):
        result = ee.spend_footprint(SAMPLE_SPEND)
        ee.save_profile(1, "Detail", result)
        stored = ee.get_profiles(1)[0]["detail"]
        self.assertEqual(len(stored["lines"]), len(result["lines"]))

    def test_profiles_are_newest_first(self):
        for name in ("first", "second", "third"):
            ee.save_profile(1, name, ee.spend_footprint(SAMPLE_SPEND))
        names = [row["name"] for row in ee.get_profiles(1)]
        self.assertEqual(names[0], "third")

    def test_users_do_not_see_each_other(self):
        ee.save_profile(1, "mine", ee.spend_footprint(SAMPLE_SPEND))
        ee.save_profile(2, "theirs", ee.spend_footprint(SAMPLE_SPEND))
        self.assertEqual(len(ee.get_profiles(1)), 1)
        self.assertEqual(ee.get_profiles(1)[0]["name"], "mine")

    def test_delete_removes_it(self):
        profile_id = ee.save_profile(1, "gone", ee.spend_footprint(SAMPLE_SPEND))
        self.assertTrue(ee.delete_profile(profile_id, 1))
        self.assertEqual(ee.get_profiles(1), [])

    def test_you_cannot_delete_someone_elses(self):
        profile_id = ee.save_profile(1, "mine", ee.spend_footprint(SAMPLE_SPEND))
        self.assertFalse(ee.delete_profile(profile_id, 2))
        self.assertEqual(len(ee.get_profiles(1)), 1)

    def test_the_limit_is_respected(self):
        for n in range(6):
            ee.save_profile(1, f"p{n}", ee.spend_footprint(SAMPLE_SPEND))
        self.assertEqual(len(ee.get_profiles(1, limit=3)), 3)


if __name__ == "__main__":
    unittest.main()
