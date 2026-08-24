"""Tests for the consumption-linked biodiversity footprint.

The claims worth guarding are the ones that make this module different from a
land-area total:

*   occupation and transformation stay separate, because one is a rate and the
    other is a stock and summing them produces a number nobody can interpret;
*   the region changes the answer by more than the product does;
*   land use intensity changes it by more than the product does too, so
    "agriculture" cannot be treated as one thing;
*   the taxa are reported separately, because they disagree about which land use
    is worst;
*   nothing returns a bare point estimate - every headline figure carries a
    range, since these characterisation factors are uncertain by roughly an
    order of magnitude;
*   a default sourcing assumption is always labelled as an assumption.

That last one is the guard that matters most in practice. Sourcing dominates the
answer, and a default that stops announcing itself turns an assumption into a
finding.
"""

import os
import tempfile
import unittest

import biodiversity_footprint as bf


class TestLandUseClasses(unittest.TestCase):

    def test_every_class_covers_every_taxon(self):
        for key in bf.LAND_USE_CLASSES:
            with self.subTest(land_use=key):
                for taxon in bf.TAXA:
                    self.assertIn(taxon, bf.get_land_use(key)["pdf"])

    def test_every_fraction_is_a_fraction(self):
        for key in bf.LAND_USE_CLASSES:
            for taxon, value in bf.get_land_use(key)["pdf"].items():
                with self.subTest(land_use=key, taxon=taxon):
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)

    def test_every_class_explains_itself(self):
        for key in bf.LAND_USE_CLASSES:
            self.assertGreater(len(bf.get_land_use(key)["note"]), 40)

    def test_managed_forest_is_the_least_damaging_productive_use(self):
        ordered = bf.list_land_uses()
        self.assertEqual(ordered[0], "managed_forest")

    def test_urban_and_oil_palm_are_the_most_damaging(self):
        ordered = bf.list_land_uses()
        self.assertIn(ordered[-1], ("urban", "oil_palm"))

    def test_agroforestry_beats_intensive_arable_by_a_wide_margin(self):
        """The largest improvement available for tropical commodity crops."""
        agro = bf.get_land_use("agroforestry")["pdf"]
        intensive = bf.get_land_use("intensive_arable")["pdf"]
        for taxon in bf.TAXA:
            with self.subTest(taxon=taxon):
                self.assertLess(agro[taxon], intensive[taxon] * 0.75)

    def test_birds_tolerate_mosaic_farming_better_than_plants(self):
        """The taxa disagree, and this is the clearest case of it."""
        pdf = bf.get_land_use("extensive_arable")["pdf"]
        self.assertLess(pdf["birds"], pdf["plants"])

    def test_mutating_a_returned_class_does_not_corrupt_the_table(self):
        copy = bf.get_land_use("urban")
        copy["pdf"]["birds"] = 0.0
        self.assertGreater(bf.get_land_use("urban")["pdf"]["birds"], 0.0)

    def test_an_unknown_class_is_refused(self):
        with self.assertRaises(bf.BiodiversityError) as context:
            bf.get_land_use("vibes_based_farming")
        self.assertIn("not one thing", str(context.exception))


class TestRegions(unittest.TestCase):

    def test_tropical_forest_outweighs_temperate_by_an_order_of_magnitude(self):
        """The reason a global-average factor would be meaningless."""
        tropical = bf.get_region("tropical_forest_seasia")["vulnerability"]
        temperate = bf.get_region("temperate_grassland")["vulnerability"]
        self.assertGreater(tropical / temperate, 5.0)

    def test_boreal_recovers_slowest(self):
        recoveries = {
            key: bf.get_region(key)["recovery_years"] for key in bf.REGIONS
        }
        self.assertEqual(max(recoveries, key=recoveries.get), "boreal_forest")

    def test_low_vulnerability_does_not_imply_fast_recovery(self):
        """Boreal is species-poor and very slow, which pull opposite ways."""
        boreal = bf.get_region("boreal_forest")
        tropical = bf.get_region("tropical_forest_seasia")
        self.assertLess(boreal["vulnerability"], tropical["vulnerability"])
        self.assertGreater(boreal["recovery_years"], tropical["recovery_years"])

    def test_regions_are_listed_most_vulnerable_first(self):
        values = [bf.get_region(k)["vulnerability"] for k in bf.list_regions()]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_an_unknown_region_is_refused_rather_than_averaged(self):
        with self.assertRaises(bf.BiodiversityError) as context:
            bf.get_region("somewhere_nice")
        self.assertIn("matters more than", str(context.exception))


class TestOccupationAndTransformation(unittest.TestCase):
    """One is a rate, the other is a stock. They never merge."""

    def test_occupation_scales_with_area_and_time(self):
        one = bf.occupation_impact(100.0, "temperate_forest", "intensive_arable")
        ten = bf.occupation_impact(1000.0, "temperate_forest", "intensive_arable")
        self.assertAlmostEqual(
            ten["pdf_m2_yr"], one["pdf_m2_yr"] * 10.0, places=6
        )

    def test_occupation_and_transformation_are_labelled_differently(self):
        occupation = bf.occupation_impact(100.0, "temperate_forest", "urban")
        transformation = bf.transformation_impact(
            100.0, "temperate_forest", "urban"
        )
        self.assertEqual(occupation["kind"], "occupation")
        self.assertEqual(transformation["kind"], "transformation")

    def test_transformation_carries_the_recovery_period(self):
        result = bf.transformation_impact(
            100.0, "boreal_forest", "plantation_forestry"
        )
        self.assertEqual(
            result["recovery_years"],
            bf.get_region("boreal_forest")["recovery_years"],
        )

    def test_a_shorter_amortisation_window_makes_conversion_look_worse(self):
        """The window changes the ranking, which is why it is a parameter."""
        short = bf.transformation_impact(
            100.0, "tropical_forest_seasia", "oil_palm", amortisation_years=20
        )
        long = bf.transformation_impact(
            100.0, "tropical_forest_seasia", "oil_palm", amortisation_years=100
        )
        self.assertAlmostEqual(
            short["pdf_m2_yr"] / long["pdf_m2_yr"], 5.0, places=6
        )

    def test_recovery_time_is_not_scaled_by_the_attribution_window(self):
        """Two different periods, and conflating them is the usual way this
        calculation goes wrong. Recovery is a property of the ecosystem; the
        attribution window is a convention about the converted area."""
        for window in (20, 50, 100):
            with self.subTest(window=window):
                result = bf.transformation_impact(
                    100.0, "boreal_forest", "plantation_forestry",
                    amortisation_years=window,
                )
                self.assertEqual(result["recovery_years"], 110)

    def test_the_attributed_area_is_reported_alongside_the_raw_area(self):
        result = bf.transformation_impact(
            100.0, "temperate_forest", "urban", amortisation_years=100
        )
        self.assertEqual(result["area_m2"], 100.0)
        self.assertAlmostEqual(result["attributed_area_m2"], 20.0, places=9)

    def test_the_amortisation_window_is_reported_in_the_result(self):
        result = bf.transformation_impact(
            100.0, "temperate_forest", "urban", amortisation_years=50
        )
        self.assertEqual(result["amortisation_years"], 50)

    def test_a_zero_amortisation_window_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.transformation_impact(
                100.0, "temperate_forest", "urban", amortisation_years=0
            )

    def test_negative_areas_are_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.occupation_impact(-1.0, "temperate_forest", "urban")
        with self.assertRaises(bf.BiodiversityError):
            bf.transformation_impact(-1.0, "temperate_forest", "urban")

    def test_every_impact_carries_a_range(self):
        for result in (
            bf.occupation_impact(100.0, "temperate_forest", "urban"),
            bf.transformation_impact(100.0, "temperate_forest", "urban"),
        ):
            self.assertIn("range", result)
            self.assertLess(result["range"]["low"], result["range"]["central"])
            self.assertGreater(result["range"]["high"], result["range"]["central"])


class TestUncertaintyRange(unittest.TestCase):

    def test_the_range_is_geometrically_centred_on_the_estimate(self):
        """0.32 and 3.10 multiply to almost exactly one, so the central figure
        sits at the geometric centre rather than pretending to be a mean."""
        product = bf.UNCERTAINTY_LOWER * bf.UNCERTAINTY_UPPER
        self.assertAlmostEqual(product, 1.0, places=1)

    def test_the_range_spans_roughly_an_order_of_magnitude(self):
        band = bf._range(100.0)
        self.assertGreater(band["high"] / band["low"], 8.0)

    def test_the_basis_warns_against_reading_the_centre_as_more_reliable(self):
        self.assertIn("not more trustworthy", bf._range(1.0)["basis"])


class TestProductFootprint(unittest.TestCase):

    def test_defaults_are_flagged_as_defaults(self):
        """Sourcing dominates the answer; a silent default would be a finding
        dressed up as a fact."""
        result = bf.product_footprint("palm_oil", 10.0)
        self.assertTrue(result["used_default_region"])
        self.assertIsNotNone(result["sourcing_warning"])

    def test_supplying_both_removes_the_warning(self):
        result = bf.product_footprint(
            "palm_oil", 10.0, region="tropical_forest_seasia",
            land_use="agroforestry",
        )
        self.assertFalse(result["used_default_region"])
        self.assertFalse(result["used_default_land_use"])
        self.assertIsNone(result["sourcing_warning"])

    def test_a_product_without_a_conversion_front_has_no_transformation(self):
        result = bf.product_footprint("wheat", 10.0)
        self.assertEqual(result["transformation"]["pdf_m2_yr"], 0.0)
        self.assertEqual(result["transformation_share"], 0.0)

    def test_deforestation_beef_carries_a_transformation_term(self):
        result = bf.product_footprint("beef_deforestation", 10.0)
        self.assertGreater(result["transformation"]["pdf_m2_yr"], 0.0)

    def test_the_same_food_from_two_fronts_differs_by_more_than_the_food_does(self):
        """The finding the module exists to surface."""
        pasture = bf.product_footprint("beef_pasture", 10.0)
        cleared = bf.product_footprint("beef_deforestation", 10.0)
        chicken = bf.product_footprint("chicken", 10.0)
        beef_gap = abs(cleared["pdf_m2_yr"] - pasture["pdf_m2_yr"])
        product_gap = abs(pasture["pdf_m2_yr"] - chicken["pdf_m2_yr"])
        self.assertGreater(beef_gap, product_gap)

    def test_soy_eaten_directly_is_far_below_soy_eaten_through_a_pig(self):
        direct = bf.product_footprint("soy_direct", 10.0)["pdf_m2_yr"]
        through_pig = bf.product_footprint("pork", 10.0)["pdf_m2_yr"]
        self.assertGreater(through_pig / direct, 5.0)

    def test_every_taxon_is_present_in_the_breakdown(self):
        result = bf.product_footprint("cocoa", 5.0)
        for taxon in bf.TAXA:
            self.assertIn(taxon, result["by_taxon"])

    def test_a_negative_quantity_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.product_footprint("wheat", -1.0)

    def test_an_unknown_product_is_refused(self):
        with self.assertRaises(bf.BiodiversityError) as context:
            bf.product_footprint("moon_cheese", 1.0)
        self.assertIn("two orders of magnitude", str(context.exception))


class TestBasketFootprint(unittest.TestCase):

    BASKET = {
        "beef_pasture": 20.0,
        "chicken": 30.0,
        "wheat": 60.0,
        "cocoa": 2.0,
        "palm_oil": 8.0,
    }

    def test_occupation_and_transformation_are_reported_separately(self):
        result = bf.basket_footprint(self.BASKET)
        self.assertIn("occupation_pdf_m2_yr", result)
        self.assertIn("transformation_pdf_m2_yr", result)
        self.assertAlmostEqual(
            result["pdf_m2_yr"],
            result["occupation_pdf_m2_yr"] + result["transformation_pdf_m2_yr"],
            places=6,
        )

    def test_items_are_returned_worst_first(self):
        rows = bf.basket_footprint(self.BASKET)["items"]
        values = [row["pdf_m2_yr"] for row in rows]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_taxon_totals_match_the_sum_of_the_items(self):
        result = bf.basket_footprint(self.BASKET)
        for taxon in bf.TAXA:
            with self.subTest(taxon=taxon):
                self.assertAlmostEqual(
                    result["by_taxon"][taxon],
                    sum(row["by_taxon"][taxon] for row in result["items"]),
                    places=6,
                )

    def test_a_sourcing_override_changes_the_answer(self):
        default = bf.basket_footprint({"palm_oil": 10.0})
        overridden = bf.basket_footprint(
            {"palm_oil": 10.0},
            overrides={"palm_oil": {"region": "tropical_savanna"}},
        )
        self.assertLess(overridden["pdf_m2_yr"], default["pdf_m2_yr"])

    def test_the_scope_limitation_is_always_carried(self):
        """A partial footprint that does not say so reads as a complete one."""
        result = bf.basket_footprint(self.BASKET)
        self.assertIn("largest driver", result["scope_limitation"])
        self.assertIn("invasive species", result["scope_limitation"])

    def test_an_empty_basket_is_refused_rather_than_scored_zero(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.basket_footprint({})

    def test_the_basket_carries_an_anchor_and_a_boundary_share(self):
        result = bf.basket_footprint(self.BASKET)
        self.assertGreater(result["anchor"]["hectare_years"], 0.0)
        self.assertGreater(result["boundary"]["share"], 0.0)


class TestAnchoring(unittest.TestCase):

    def test_a_hectare_year_is_ten_thousand_square_metre_years(self):
        result = bf.anchor(10000.0)
        self.assertAlmostEqual(result["hectare_years"], 1.0, places=9)

    def test_the_scientific_unit_is_always_returned_alongside(self):
        result = bf.anchor(5000.0)
        self.assertEqual(result["pdf_m2_yr"], 5000.0)

    def test_the_anchor_says_it_is_an_anchor(self):
        self.assertIn("not a measurement", bf.anchor(1000.0)["caveat"])

    def test_a_negative_impact_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.anchor(-1.0)


class TestBoundaryShare(unittest.TestCase):

    def test_the_share_scales_linearly(self):
        one = bf.boundary_share(1000.0)["share"]
        two = bf.boundary_share(2000.0)["share"]
        self.assertAlmostEqual(two, one * 2, places=9)

    def test_the_downscaling_is_labelled_as_an_ethical_choice(self):
        self.assertIn("ethical choice", bf.boundary_share(1000.0)["basis"])

    def test_a_negative_impact_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.boundary_share(-1.0)


class TestTaxonDisagreement(unittest.TestCase):

    def test_a_wide_spread_is_reported_as_a_warning_about_the_aggregate(self):
        spread = bf.taxon_disagreement(
            {"plants": 100.0, "mammals": 30.0, "birds": 20.0,
             "amphibians": 90.0, "reptiles": 60.0}
        )
        self.assertGreater(spread["spread"], 1.6)
        self.assertIn("describe neither", spread["verdict"])

    def test_a_narrow_spread_says_the_aggregate_is_fair(self):
        spread = bf.taxon_disagreement(
            {"plants": 100.0, "mammals": 95.0, "birds": 92.0,
             "amphibians": 98.0, "reptiles": 96.0}
        )
        self.assertIn("broadly agree", spread["verdict"])

    def test_the_worst_and_best_hit_taxa_are_named(self):
        spread = bf.taxon_disagreement(
            {"plants": 100.0, "mammals": 30.0, "birds": 20.0,
             "amphibians": 90.0, "reptiles": 60.0}
        )
        self.assertEqual(spread["worst"], "plants")
        self.assertEqual(spread["best"], "birds")

    def test_an_all_zero_breakdown_produces_no_verdict(self):
        spread = bf.taxon_disagreement({taxon: 0.0 for taxon in bf.TAXA})
        self.assertIsNone(spread["verdict"])


class TestComparisons(unittest.TestCase):

    def test_changing_land_use_beats_changing_product(self):
        """Shade-grown against full-sun cocoa is a larger change than most
        substitutions between products."""
        by_use = bf.compare_land_uses("cocoa", 2.0)
        use_spread = by_use[-1]["pdf_m2_yr"] - by_use[0]["pdf_m2_yr"]
        cocoa = bf.product_footprint("cocoa", 2.0)["pdf_m2_yr"]
        coffee = bf.product_footprint("coffee", 2.0)["pdf_m2_yr"]
        self.assertGreater(use_spread, abs(cocoa - coffee))

    def test_the_land_use_comparison_covers_every_class(self):
        rows = bf.compare_land_uses("wheat", 10.0)
        self.assertEqual(len(rows), len(bf.LAND_USE_CLASSES))

    def test_the_land_use_comparison_is_ranked_best_first(self):
        values = [row["pdf_m2_yr"] for row in bf.compare_land_uses("wheat", 10.0)]
        self.assertEqual(values, sorted(values))

    def test_the_region_comparison_covers_every_region(self):
        rows = bf.compare_regions("palm_oil", 8.0)
        self.assertEqual(len(rows), len(bf.REGIONS))

    def test_the_region_comparison_is_ranked_best_first(self):
        values = [row["pdf_m2_yr"] for row in bf.compare_regions("palm_oil", 8.0)]
        self.assertEqual(values, sorted(values))

    def test_region_alone_moves_the_answer_by_an_order_of_magnitude(self):
        rows = bf.compare_regions("chicken", 20.0)
        self.assertGreater(rows[-1]["pdf_m2_yr"] / rows[0]["pdf_m2_yr"], 5.0)


class TestInsights(unittest.TestCase):

    def test_a_conversion_heavy_basket_is_told_where_its_damage_comes_from(self):
        result = bf.basket_footprint({"beef_deforestation": 30.0})
        insights = bf.get_biodiversity_insights(result)
        self.assertTrue(any("transformation rather than" in i for i in insights))

    def test_a_long_converted_basket_is_told_the_conversion_already_happened(self):
        result = bf.basket_footprint({"wheat": 100.0})
        insights = bf.get_biodiversity_insights(result)
        self.assertTrue(any("already happened" in i for i in insights))

    def test_the_range_is_always_restated_in_the_insights(self):
        result = bf.basket_footprint({"wheat": 100.0})
        insights = bf.get_biodiversity_insights(result)
        self.assertTrue(any("plausible range" in i for i in insights))

    def test_default_sourcing_is_called_out_as_the_thing_to_challenge(self):
        result = bf.basket_footprint({"cocoa": 5.0, "coffee": 5.0})
        insights = bf.get_biodiversity_insights(result)
        self.assertTrue(any("assumed sourcing region" in i for i in insights))

    def test_a_fully_specified_basket_is_not_lectured_about_sourcing(self):
        result = bf.basket_footprint(
            {"cocoa": 5.0},
            overrides={
                "cocoa": {
                    "region": "tropical_forest_africa",
                    "land_use": "agroforestry",
                }
            },
        )
        insights = bf.get_biodiversity_insights(result)
        self.assertFalse(any("assumed sourcing region" in i for i in insights))

    def test_a_dominant_item_is_named(self):
        result = bf.basket_footprint({"wool": 5.0, "wheat": 1.0})
        insights = bf.get_biodiversity_insights(result)
        self.assertTrue(any("rounding error" in i for i in insights))


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self._original = bf.DB_NAME
        bf.DB_NAME = self.path
        self.result = bf.basket_footprint({"chicken": 20.0, "wheat": 40.0})

    def tearDown(self):
        bf.DB_NAME = self._original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_basket_comes_back(self):
        basket_id = bf.save_basket("u1", "Weekly shop", self.result)
        self.assertGreater(basket_id, 0)
        baskets = bf.get_baskets("u1")
        self.assertEqual(len(baskets), 1)
        self.assertEqual(baskets[0]["name"], "Weekly shop")

    def test_the_transformation_share_is_stored_alongside_the_total(self):
        bf.save_basket("u1", "Weekly shop", self.result)
        stored = bf.get_baskets("u1")[0]
        self.assertGreaterEqual(stored["transformation_share"], 0.0)
        self.assertLessEqual(stored["transformation_share"], 1.0)

    def test_the_sourcing_used_is_stored_so_a_result_can_be_read_back(self):
        bf.save_basket("u1", "Weekly shop", self.result)
        items = bf.get_baskets("u1")[0]["payload"]["items"]
        self.assertTrue(all("region" in item for item in items))
        self.assertTrue(all("land_use" in item for item in items))

    def test_baskets_are_scoped_to_their_user(self):
        bf.save_basket("u1", "Mine", self.result)
        self.assertEqual(bf.get_baskets("u2"), [])

    def test_deleting_someone_elses_basket_does_nothing(self):
        basket_id = bf.save_basket("u1", "Mine", self.result)
        self.assertFalse(bf.delete_basket("u2", basket_id))
        self.assertEqual(len(bf.get_baskets("u1")), 1)

    def test_deleting_your_own_basket_removes_it(self):
        basket_id = bf.save_basket("u1", "Mine", self.result)
        self.assertTrue(bf.delete_basket("u1", basket_id))
        self.assertEqual(bf.get_baskets("u1"), [])

    def test_an_unnamed_basket_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.save_basket("u1", "   ", self.result)

    def test_an_anonymous_basket_is_refused(self):
        with self.assertRaises(bf.BiodiversityError):
            bf.save_basket("", "Shop", self.result)


if __name__ == "__main__":
    unittest.main()
