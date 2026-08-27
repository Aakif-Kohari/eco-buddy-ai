"""Tests for the plastic fate and leakage model.

The claims worth guarding are the ones that separate this from a recyclability
flag:

*   a fate model conserves mass, so nothing is silently lost or invented;
*   collection is not recycling, and the gap between them is polymer-specific;
*   leakage happens to uncollected waste, not to badly sorted waste, so sorting
    better does not reduce it - the module states that with a zero rather than
    omitting the intervention;
*   most leaked plastic never reaches the sea;
*   every substitution reports plastic and carbon together, because swapping one
    for the other is a trade and not an improvement.

The mass conservation test is the load-bearing one. A fate model that leaks mass
in its own arithmetic cannot be trusted about anything else.
"""

import math
import os
import tempfile
import unittest

import src.environment.plastic_leakage as pl


class TestPolymerTable(unittest.TestCase):

    def test_every_polymer_has_yields_a_residence_time_and_a_note(self):
        for key in pl.POLYMERS:
            with self.subTest(polymer=key):
                spec = pl.get_polymer(key)
                self.assertGreaterEqual(spec["sorting_yield"], 0.0)
                self.assertLessEqual(spec["sorting_yield"], 1.0)
                self.assertGreater(spec["marine_years"], 0.0)
                self.assertGreater(len(spec["note"]), 40)

    def test_real_recycling_rate_is_the_product_of_both_yields(self):
        for key in pl.POLYMERS:
            with self.subTest(polymer=key):
                spec = pl.get_polymer(key)
                self.assertAlmostEqual(
                    pl.real_recycling_rate(key),
                    spec["sorting_yield"] * spec["reprocessing_yield"],
                    places=9,
                )

    def test_pet_is_the_only_polymer_with_a_working_loop(self):
        """The claim on the pack and the reality diverge everywhere else."""
        self.assertGreater(pl.real_recycling_rate("pet"), 0.7)

    def test_multilayer_laminate_is_effectively_unrecyclable(self):
        self.assertLess(pl.real_recycling_rate("multilayer"), 0.01)

    def test_film_sorts_far_worse_than_rigid_packaging(self):
        """A bag in the recycling bin is usually a problem, not a contribution."""
        self.assertLess(
            pl.get_polymer("ldpe_film")["sorting_yield"],
            pl.get_polymer("hdpe")["sorting_yield"] / 2,
        )

    def test_polystyrene_is_widely_labelled_and_rarely_recycled(self):
        self.assertLess(pl.real_recycling_rate("ps"), 0.1)

    def test_polymers_are_listed_worst_first(self):
        rates = [pl.real_recycling_rate(k) for k in pl.list_polymers()]
        self.assertEqual(rates, sorted(rates))

    def test_an_unknown_polymer_is_refused_rather_than_averaged(self):
        with self.assertRaises(pl.PlasticError) as context:
            pl.get_polymer("unobtanium")
        self.assertIn("actively misleading", str(context.exception))


class TestFateModel(unittest.TestCase):
    """The load-bearing property: mass in equals mass out."""

    def test_every_polymer_and_region_conserves_mass(self):
        for polymer in pl.POLYMERS:
            for region in pl.REGIONS:
                with self.subTest(polymer=polymer, region=region):
                    result = pl.fate(polymer, 10.0, region)
                    total = (
                        result["recycled"] + result["incinerated"]
                        + result["landfilled"] + result["informally_disposed"]
                        + result["leaked"]
                    )
                    self.assertAlmostEqual(total, 10.0, places=6)

    def test_mass_is_conserved_when_sorted_incorrectly_too(self):
        result = pl.fate("pet", 10.0, "high_income_eu", sorted_correctly=False)
        total = (
            result["recycled"] + result["incinerated"] + result["landfilled"]
            + result["informally_disposed"] + result["leaked"]
        )
        self.assertAlmostEqual(total, 10.0, places=6)

    def test_wrongly_sorted_material_is_not_recycled_but_is_not_destroyed(self):
        result = pl.fate("pet", 10.0, "high_income_eu", sorted_correctly=False)
        self.assertEqual(result["recycled"], 0.0)
        self.assertGreater(result["incinerated"] + result["landfilled"], 0.0)

    def test_the_real_rate_falls_short_of_nominal_recyclability(self):
        """Collection is not recycling, and this is where the gap shows."""
        result = pl.fate("pp", 10.0, "high_income_eu")
        self.assertLess(
            result["real_recycling_rate"], result["nominal_recyclability"]
        )

    def test_leakage_comes_from_uncollected_waste(self):
        good = pl.fate("pet", 10.0, "high_income_eu")
        poor = pl.fate("pet", 10.0, "lower_middle")
        self.assertGreater(poor["leaked"], good["leaked"] * 10)

    def test_sorting_correctly_does_not_change_how_much_leaks(self):
        """Leakage happens to uncollected waste, not to badly sorted src.environment.waste. If
        this ever changes, the intervention ranking becomes wrong."""
        sorted_well = pl.fate("pet", 10.0, "high_income_eu", True)
        sorted_badly = pl.fate("pet", 10.0, "high_income_eu", False)
        self.assertAlmostEqual(
            sorted_well["leaked"], sorted_badly["leaked"], places=9
        )

    def test_incineration_share_follows_the_region(self):
        europe = pl.fate("ps", 10.0, "high_income_eu")
        america = pl.fate("ps", 10.0, "high_income_na")
        self.assertGreater(europe["incinerated"], america["incinerated"])

    def test_pla_is_flagged_where_there_is_no_industrial_composting(self):
        without = pl.fate("pla", 5.0, "high_income_na")
        self.assertIsNotNone(without["pla_warning"])
        with_facility = pl.fate("pla", 5.0, "high_income_eu")
        self.assertIsNone(with_facility["pla_warning"])

    def test_only_pla_gets_the_composting_warning(self):
        self.assertIsNone(pl.fate("pet", 5.0, "high_income_na")["pla_warning"])

    def test_a_negative_mass_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.fate("pet", -1.0)

    def test_an_unknown_region_is_refused(self):
        with self.assertRaises(pl.PlasticError) as context:
            pl.fate("pet", 1.0, "atlantis")
        self.assertIn("Infrastructure decides", str(context.exception))


class TestLeakagePathways(unittest.TestCase):
    """The pathways that have nothing to do with bins."""

    def test_every_pathway_splits_across_compartments_that_sum_to_one(self):
        for key, spec in pl.LEAKAGE_PATHWAYS.items():
            with self.subTest(pathway=key):
                self.assertAlmostEqual(
                    sum(spec["compartments"].values()), 1.0, places=6
                )

    def test_every_pathway_names_its_activity_unit(self):
        """A single 'per person' figure would hide which behaviour drives it."""
        for key in pl.LEAKAGE_PATHWAYS:
            self.assertTrue(pl.LEAKAGE_PATHWAYS[key]["unit"])

    def test_released_mass_is_the_activity_times_the_factor(self):
        result = pl.pathway_leakage("tyre_wear", 10000.0)
        self.assertAlmostEqual(result["kg_released"], 10000.0 * 0.00011, places=9)

    def test_compartment_totals_match_the_released_mass(self):
        result = pl.pathway_leakage("textile_laundry", 100.0)
        self.assertAlmostEqual(
            sum(result["compartments"].values()), result["kg_released"], places=9
        )

    def test_tyre_wear_dwarfs_personal_care(self):
        """The pathway that got the regulation is by a wide margin the smallest."""
        tyres = pl.pathway_leakage("tyre_wear", 12000.0)["kg_released"]
        beads = pl.pathway_leakage("personal_care", 2.0)["kg_released"]
        self.assertGreater(tyres / beads, 100.0)

    def test_textile_fibres_mostly_reach_soil_rather_than_sea(self):
        """The opposite of how this pathway is usually described."""
        compartments = pl.LEAKAGE_PATHWAYS["textile_laundry"]["compartments"]
        self.assertGreater(compartments["soil"], compartments["marine"] * 10)

    def test_an_unknown_pathway_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.pathway_leakage("cosmic_rays", 1.0)

    def test_negative_activity_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.pathway_leakage("tyre_wear", -1.0)


class TestHouseholdLeakage(unittest.TestCase):

    PACKAGING = {
        "pet": 6.0, "hdpe": 4.0, "ldpe_film": 5.0,
        "pp": 4.0, "multilayer": 3.0, "ps": 1.5,
    }
    PATHWAYS = {"tyre_wear": 12000.0, "textile_laundry": 90.0,
                "personal_care": 2.0}

    def test_non_bin_pathways_dominate_a_car_owning_household(self):
        """The finding the module was written to surface."""
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        self.assertGreater(result["pathway_share"], 0.5)

    def test_the_totals_are_the_sum_of_their_parts(self):
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        self.assertAlmostEqual(
            result["total_leakage_kg"],
            result["bin_leakage_kg"] + result["pathway_leakage_kg"],
            places=9,
        )

    def test_compartments_account_for_the_whole_leaked_mass(self):
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        self.assertAlmostEqual(
            sum(result["compartments"].values()),
            result["total_leakage_kg"],
            places=6,
        )

    def test_most_of_it_does_not_reach_the_sea(self):
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        marine = result["compartments"]["marine"]
        self.assertLess(marine / result["total_leakage_kg"], 0.15)

    def test_better_sorting_raises_recycling_and_leaves_leakage_alone(self):
        careless = pl.household_leakage(self.PACKAGING, self.PATHWAYS,
                                        sorting_accuracy=0.5)
        careful = pl.household_leakage(self.PACKAGING, self.PATHWAYS,
                                       sorting_accuracy=1.0)
        self.assertGreater(
            careful["packaging_recycled_kg"], careless["packaging_recycled_kg"]
        )
        self.assertAlmostEqual(
            careful["bin_leakage_kg"], careless["bin_leakage_kg"], places=9
        )

    def test_a_worse_region_leaks_far_more_from_the_same_packaging(self):
        europe = pl.household_leakage(self.PACKAGING, {}, region="high_income_eu")
        elsewhere = pl.household_leakage(self.PACKAGING, {}, region="lower_middle")
        self.assertGreater(elsewhere["bin_leakage_kg"],
                           europe["bin_leakage_kg"] * 10)

    def test_packaging_rows_come_back_heaviest_first(self):
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        values = [row["kg"] for row in result["packaging"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_an_empty_household_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.household_leakage({}, {})

    def test_a_sorting_accuracy_outside_zero_to_one_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.household_leakage(self.PACKAGING, {}, sorting_accuracy=1.4)

    def test_a_negative_packaging_mass_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.household_leakage({"pet": -1.0}, {})

    def test_carbon_is_reported_alongside_the_plastic(self):
        result = pl.household_leakage(self.PACKAGING, self.PATHWAYS)
        self.assertGreater(result["carbon_kg_co2e"], 0.0)


class TestPersistence(unittest.TestCase):
    """Mass alone files EPS and paper as equivalent litter. It should not."""

    def test_the_curve_starts_at_the_leaked_mass(self):
        profile = pl.persistence_profile("eps", 1.0, "marine", 100)
        self.assertAlmostEqual(profile["remaining_kg"][0], 1.0, places=9)

    def test_the_curve_falls_monotonically(self):
        profile = pl.persistence_profile("pet", 1.0, "marine", 100)
        for earlier, later in zip(profile["remaining_kg"],
                                  profile["remaining_kg"][1:]):
            self.assertLessEqual(later, earlier)

    def test_a_long_lived_polymer_leaves_more_behind_at_the_horizon(self):
        pvc = pl.persistence_profile("pvc", 1.0, "marine", 100)
        pla = pl.persistence_profile("pla", 1.0, "marine", 100)
        self.assertGreater(
            pvc["share_remaining_at_horizon"], pla["share_remaining_at_horizon"]
        )

    def test_half_life_follows_from_the_residence_time(self):
        """For first-order decay the half-life is ln(2) times the mean
        residence time, so it is shorter than the residence time rather than
        longer. Getting that backwards would overstate persistence by 44%."""
        profile = pl.persistence_profile("pet", 1.0, "marine", 100)
        self.assertLess(profile["half_life_years"], profile["residence_years"])
        self.assertAlmostEqual(
            profile["half_life_years"],
            profile["residence_years"] * math.log(2),
            places=6,
        )

    def test_the_fragmentation_caveat_is_always_present(self):
        """The mass curve falls while the particle count rises."""
        profile = pl.persistence_profile("eps", 1.0, "soil", 50)
        self.assertIn("fragment", profile["caveat"])

    def test_freshwater_is_refused_because_decay_is_the_wrong_model_there(self):
        with self.assertRaises(pl.PlasticError) as context:
            pl.persistence_profile("pet", 1.0, "freshwater", 100)
        self.assertIn("transport out of the compartment", str(context.exception))

    def test_a_zero_horizon_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.persistence_profile("pet", 1.0, "marine", 0)

    def test_a_negative_leaked_mass_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.persistence_profile("pet", -1.0, "marine", 100)


class TestSubstitution(unittest.TestCase):
    """Both numbers, always, because the swap is a trade."""

    def test_a_cotton_tote_takes_about_fifty_uses_to_repay_its_carbon(self):
        """The well-known figure, and the reason plastic-only advice misleads."""
        break_even = pl.carbon_break_even("ldpe_bag", "cotton_tote")
        self.assertGreater(break_even, 40)
        self.assertLess(break_even, 70)

    def test_a_woven_pp_bag_repays_far_faster_than_cotton(self):
        self.assertLess(
            pl.carbon_break_even("ldpe_bag", "pp_woven_bag"),
            pl.carbon_break_even("ldpe_bag", "cotton_tote"),
        )

    def test_a_steel_bottle_repays_within_a_month_of_daily_use(self):
        self.assertLess(pl.carbon_break_even("pet_bottle", "steel_bottle"), 35)

    def test_a_short_run_of_uses_makes_cotton_a_trade_not_an_improvement(self):
        result = pl.substitution("ldpe_bag", "cotton_tote", 10)
        self.assertTrue(result["is_a_trade"])
        self.assertIn("does not come free", result["verdict"])

    def test_a_long_run_of_uses_makes_cotton_an_improvement_on_both(self):
        # 208 rather than 200: a tote lasts 52 uses, and buying a fourth tote
        # for the 200th shop is what tips the arithmetic. Whole units matter.
        result = pl.substitution("ldpe_bag", "cotton_tote", 208)
        self.assertFalse(result["is_a_trade"])
        self.assertIn("No trade involved", result["verdict"])

    def test_both_plastic_and_carbon_are_always_returned(self):
        result = pl.substitution("pet_bottle", "steel_bottle", 100)
        for row in result["options"]:
            self.assertIn("plastic_kg", row)
            self.assertIn("carbon_kg_co2e", row)

    def test_units_needed_accounts_for_reuses(self):
        result = pl.substitution("ldpe_bag", "cotton_tote", 104)
        by_option = {row["option"]: row for row in result["options"]}
        self.assertEqual(by_option["ldpe_bag"]["units_needed"], 104)
        self.assertEqual(by_option["cotton_tote"]["units_needed"], 2)

    def test_a_paper_bag_removes_the_plastic_and_adds_carbon(self):
        result = pl.substitution("ldpe_bag", "paper_bag", 20)
        self.assertLess(result["plastic_delta_kg"], 0.0)
        self.assertGreater(result["carbon_delta_kg_co2e"], 0.0)

    def test_zero_uses_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.substitution("ldpe_bag", "cotton_tote", 0)

    def test_an_unknown_option_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.substitution("ldpe_bag", "hemp_sack", 10)


class TestInterventionRanking(unittest.TestCase):

    HOUSEHOLD = {
        "packaging": {"pet": 6.0, "ldpe_film": 5.0, "multilayer": 3.0},
        "pathways": {"tyre_wear": 12000.0, "textile_laundry": 90.0},
    }

    def setUp(self):
        self.result = pl.household_leakage(
            self.HOUSEHOLD["packaging"], self.HOUSEHOLD["pathways"]
        )

    def test_driving_less_outranks_anything_to_do_with_bags(self):
        """The opposite of where consumer attention goes."""
        ranked = pl.rank_interventions(self.result)
        names = [row["intervention"] for row in ranked]
        self.assertLess(
            names.index("Drive 20% fewer kilometres"),
            names.index("Avoid film and laminate packaging"),
        )

    def test_the_ranking_is_by_effect_size(self):
        values = [row["avoided_kg"] for row in pl.rank_interventions(self.result)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_perfect_sorting_is_listed_with_a_zero_rather_than_omitted(self):
        """Stating it explicitly is the point: sorting is worth doing and it is
        not a leakage intervention."""
        ranked = pl.rank_interventions(self.result)
        sorting = next(
            row for row in ranked if row["intervention"].startswith("Sort")
        )
        self.assertEqual(sorting["avoided_kg"], 0.0)
        self.assertIn("not a leakage intervention", sorting["note"])

    def test_a_household_without_a_car_gets_no_tyre_interventions(self):
        result = pl.household_leakage({"pet": 6.0}, {"textile_laundry": 90.0})
        names = [row["intervention"] for row in pl.rank_interventions(result)]
        self.assertNotIn("Drive 20% fewer kilometres", names)

    def test_every_intervention_explains_its_mechanism(self):
        for row in pl.rank_interventions(self.result):
            with self.subTest(intervention=row["intervention"]):
                self.assertGreater(len(row["note"]), 40)


class TestInsights(unittest.TestCase):

    def test_a_car_owning_household_is_told_bins_are_not_the_issue(self):
        result = pl.household_leakage(
            {"pet": 6.0}, {"tyre_wear": 12000.0}
        )
        insights = pl.get_plastic_insights(result)
        self.assertTrue(any("nothing to do with bins" in i for i in insights))

    def test_the_marine_share_is_always_reported(self):
        result = pl.household_leakage({"pet": 6.0}, {"tyre_wear": 12000.0})
        insights = pl.get_plastic_insights(result)
        self.assertTrue(any("marine environment" in i for i in insights))

    def test_an_unrecyclable_polymer_is_named_with_its_real_rate(self):
        result = pl.household_leakage({"multilayer": 5.0}, {})
        insights = pl.get_plastic_insights(result)
        self.assertTrue(any("whatever the symbol" in i for i in insights))

    def test_the_gap_between_collection_and_recycling_is_stated(self):
        result = pl.household_leakage({"pp": 5.0}, {})
        insights = pl.get_plastic_insights(result)
        self.assertTrue(any("becomes" in i and "secondary material" in i
                            for i in insights))

    def test_pla_in_the_wrong_region_produces_a_warning_insight(self):
        result = pl.household_leakage(
            {"pla": 3.0}, {}, region="high_income_na"
        )
        insights = pl.get_plastic_insights(result)
        self.assertTrue(any("industrial composting" in i for i in insights))


class TestProfileStorage(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self._original = pl.DB_NAME
        pl.DB_NAME = self.path
        self.result = pl.household_leakage(
            {"pet": 6.0, "ldpe_film": 5.0}, {"tyre_wear": 12000.0}
        )

    def tearDown(self):
        pl.DB_NAME = self._original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_profile_comes_back(self):
        profile_id = pl.save_profile("u1", "This year", self.result)
        self.assertGreater(profile_id, 0)
        profiles = pl.get_profiles("u1")
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "This year")

    def test_the_pathway_share_is_stored_so_a_trend_is_readable(self):
        pl.save_profile("u1", "This year", self.result)
        stored = pl.get_profiles("u1")[0]
        self.assertGreater(stored["pathway_share"], 0.0)
        self.assertLessEqual(stored["pathway_share"], 1.0)

    def test_the_region_and_sorting_accuracy_are_stored_with_the_result(self):
        pl.save_profile("u1", "This year", self.result)
        payload = pl.get_profiles("u1")[0]["payload"]
        self.assertIn("region", payload)
        self.assertIn("sorting_accuracy", payload)

    def test_profiles_are_scoped_to_their_user(self):
        pl.save_profile("u1", "Mine", self.result)
        self.assertEqual(pl.get_profiles("u2"), [])

    def test_deleting_someone_elses_profile_does_nothing(self):
        profile_id = pl.save_profile("u1", "Mine", self.result)
        self.assertFalse(pl.delete_profile("u2", profile_id))
        self.assertEqual(len(pl.get_profiles("u1")), 1)

    def test_deleting_your_own_profile_removes_it(self):
        profile_id = pl.save_profile("u1", "Mine", self.result)
        self.assertTrue(pl.delete_profile("u1", profile_id))
        self.assertEqual(pl.get_profiles("u1"), [])

    def test_an_unnamed_profile_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.save_profile("u1", "  ", self.result)

    def test_an_anonymous_profile_is_refused(self):
        with self.assertRaises(pl.PlasticError):
            pl.save_profile("", "Mine", self.result)


if __name__ == "__main__":
    unittest.main()
