"""Tests for the fugitive refrigerant inventory.

The claim being tested is that direct emissions alone give wrong retrofit
advice, and that the grid intensity at which the answer flips is a real number
rather than a hand-wave. So the central tests are the breakeven ones: that the
threshold falls where the two effects actually cancel, that a swap is judged
correctly on either side of it, and that a swap winning on both counts is
reported as having no threshold rather than a meaningless one.

Everything else is guarding the table and the three-part lifecycle split, which
is the part that makes disposal visible.
"""

import os
import tempfile
import unittest

import src.environment.refrigerant_gases as rg


class TestRefrigerantTable(unittest.TestCase):
    """The gas properties."""

    def test_every_gas_has_every_vintage_and_horizon(self):
        for gas in rg.list_refrigerants():
            for vintage in rg.VINTAGES:
                for horizon in rg.HORIZONS:
                    with self.subTest(gas=gas, vintage=vintage, horizon=horizon):
                        self.assertGreaterEqual(rg.gwp(gas, vintage, horizon), 0.0)

    def test_twenty_year_gwp_is_never_below_hundred_year(self):
        # True for every gas in this family: they are all shorter-lived than
        # CO2, so the shorter horizon concentrates their effect.
        for gas in rg.list_refrigerants():
            for vintage in rg.VINTAGES:
                with self.subTest(gas=gas, vintage=vintage):
                    self.assertGreaterEqual(
                        rg.gwp(gas, vintage, 20), rg.gwp(gas, vintage, 100)
                    )

    def test_every_gas_carries_a_safety_class_and_a_note(self):
        for gas in rg.list_refrigerants():
            with self.subTest(gas=gas):
                entry = rg.get_refrigerant(gas)
                self.assertTrue(entry["safety_class"])
                self.assertTrue(entry["note"])

    def test_every_phase_down_status_has_a_label(self):
        for gas in rg.list_refrigerants():
            with self.subTest(gas=gas):
                self.assertIn(
                    rg.get_refrigerant(gas)["phase_down"], rg.PHASE_DOWN_LABELS
                )

    def test_unknown_gas_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.get_refrigerant("R-999")

    def test_unknown_vintage_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.gwp("R-410A", "ar3")

    def test_unsupported_horizon_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.gwp("R-410A", "ar6", 500)

    def test_the_vintage_spread_is_real(self):
        # AR4 to AR6 on R-410A is a 21% move. Reporting one figure without its
        # vintage hides a difference larger than several the module reports.
        spread = rg.gwp_spread("R-410A")
        self.assertGreater(spread["ratio"], 1.15)

    def test_hydrocarbons_are_far_below_hfcs(self):
        self.assertLess(rg.gwp("R-290"), rg.gwp("R-410A") / 100.0)
        self.assertLess(rg.gwp("R-600a"), rg.gwp("R-134a") / 100.0)


class TestEquipmentClasses(unittest.TestCase):
    """The class defaults that make an estimate possible at all."""

    def test_every_class_is_usable(self):
        for key in rg.list_equipment_classes():
            with self.subTest(equipment=key):
                entry = rg.get_equipment_class(key)
                self.assertGreater(entry["charge_kg"], 0.0)
                self.assertGreater(entry["lifetime_years"], 0.0)
                self.assertGreaterEqual(entry["annual_kwh"], 0.0)

    def test_every_class_defaults_to_a_real_gas(self):
        for key in rg.list_equipment_classes():
            with self.subTest(equipment=key):
                self.assertIn(
                    rg.get_equipment_class(key)["default_gas"], rg.REFRIGERANTS
                )

    def test_leak_rates_are_fractions(self):
        for key in rg.list_equipment_classes():
            with self.subTest(equipment=key):
                entry = rg.get_equipment_class(key)
                self.assertGreater(entry["leak_rate"], 0.0)
                self.assertLess(entry["leak_rate"], 1.0)

    def test_sealed_units_leak_less_than_field_assembled_ones(self):
        # A factory-sealed fridge and a site-piped split system are not the
        # same kind of machine, and the leak rates have to reflect that.
        sealed = rg.get_equipment_class("domestic_fridge")["leak_rate"]
        piped = rg.get_equipment_class("split_ac")["leak_rate"]
        self.assertLess(sealed, piped)

    def test_unknown_class_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.get_equipment_class("time_machine")


class TestBuildEquipment(unittest.TestCase):
    """Turning "I have a heat pump" into something computable."""

    def test_defaults_are_filled_in(self):
        item = rg.build_equipment("air_source_heat_pump")
        defaults = rg.get_equipment_class("air_source_heat_pump")
        self.assertEqual(item["gas"], defaults["default_gas"])
        self.assertEqual(item["charge_kg"], defaults["charge_kg"])

    def test_overrides_are_honoured(self):
        item = rg.build_equipment("split_ac", charge_kg=2.5, leak_rate=0.08)
        self.assertEqual(item["charge_kg"], 2.5)
        self.assertEqual(item["leak_rate"], 0.08)

    def test_a_zero_charge_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", charge_kg=0.0)

    def test_a_leak_rate_above_one_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", leak_rate=1.4)

    def test_a_zero_lifetime_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", lifetime_years=0.0)

    def test_negative_energy_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", annual_kwh=-50.0)

    def test_equipment_older_than_its_lifetime_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", lifetime_years=10.0, age_years=12.0)

    def test_unknown_gas_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.build_equipment("split_ac", gas="R-999")


class TestLeakage(unittest.TestCase):
    """Charge times leak rate, and what happens when nobody tops it up."""

    def setUp(self):
        self.item = rg.build_equipment("air_source_heat_pump")

    def test_topped_up_leakage_is_charge_times_rate(self):
        self.assertAlmostEqual(
            rg.annual_leakage_kg(self.item),
            self.item["charge_kg"] * self.item["leak_rate"],
        )

    def test_a_topped_up_machine_keeps_its_charge(self):
        self.assertAlmostEqual(
            rg.remaining_charge_kg(self.item, 10.0), self.item["charge_kg"]
        )

    def test_an_untopped_machine_empties(self):
        early = rg.remaining_charge_kg(self.item, 1.0, topped_up=False)
        late = rg.remaining_charge_kg(self.item, 15.0, topped_up=False)
        self.assertLess(late, early)
        self.assertGreater(late, 0.0)

    def test_charge_never_goes_negative(self):
        for years in (0.0, 5.0, 50.0, 500.0):
            with self.subTest(years=years):
                self.assertGreaterEqual(
                    rg.remaining_charge_kg(self.item, years, topped_up=False), 0.0
                )

    def test_looking_before_installation_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.remaining_charge_kg(self.item, -1.0)


class TestLifecycle(unittest.TestCase):
    """The three-part split that makes disposal visible."""

    def setUp(self):
        self.item = rg.build_equipment("air_source_heat_pump")

    def test_the_parts_sum_to_the_total(self):
        result = rg.lifecycle_emissions(self.item)
        self.assertAlmostEqual(
            result["install_co2e"] + result["operating_co2e"]
            + result["disposal_co2e"],
            result["total_co2e"],
            places=2,
        )

    def test_gas_mass_and_co2e_agree(self):
        result = rg.lifecycle_emissions(self.item)
        self.assertAlmostEqual(
            result["total_kg_gas"] * result["gwp"], result["total_co2e"], places=2
        )

    def test_scrapping_it_intact_is_the_worst_case(self):
        scrapped = rg.lifecycle_emissions(self.item, recovery=0.0)
        recovered = rg.lifecycle_emissions(self.item, recovery=0.95)
        self.assertGreater(scrapped["total_co2e"], recovered["total_co2e"])

    def test_full_recovery_removes_the_disposal_term_entirely(self):
        self.assertAlmostEqual(
            rg.lifecycle_emissions(self.item, recovery=1.0)["disposal_co2e"], 0.0
        )

    def test_disposal_can_exceed_several_years_of_operation(self):
        # The reason it is reported separately: on a scrapped unit it is the
        # single largest event in the machine's life.
        result = rg.lifecycle_emissions(self.item, recovery=0.0)
        self.assertGreater(result["disposal_co2e"], result["annual_operating_co2e"] * 5)

    def test_a_recovery_above_one_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.lifecycle_emissions(self.item, recovery=1.5)

    def test_a_negative_recovery_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.lifecycle_emissions(self.item, recovery=-0.1)

    def test_topping_up_emits_more_in_total(self):
        # A machine kept full leaks a full charge's worth every time; one left
        # to empty cannot leak more than it holds.
        topped = rg.lifecycle_emissions(self.item, topped_up=True)
        untopped = rg.lifecycle_emissions(self.item, topped_up=False)
        self.assertGreater(topped["total_co2e"], untopped["total_co2e"])

    def test_an_untopped_machine_can_never_lose_more_than_its_charge(self):
        result = rg.lifecycle_emissions(self.item, topped_up=False, recovery=0.0)
        self.assertLessEqual(
            result["total_kg_gas"], self.item["charge_kg"] + 1e-9
        )

    def test_a_longer_life_leaks_more_when_topped_up(self):
        short = rg.build_equipment("air_source_heat_pump", lifetime_years=8.0)
        long = rg.build_equipment("air_source_heat_pump", lifetime_years=20.0)
        self.assertGreater(
            rg.lifecycle_emissions(long)["total_co2e"],
            rg.lifecycle_emissions(short)["total_co2e"],
        )

    def test_the_horizon_changes_the_answer(self):
        century = rg.lifecycle_emissions(self.item, horizon=100)["total_co2e"]
        twenty = rg.lifecycle_emissions(self.item, horizon=20)["total_co2e"]
        self.assertGreater(twenty, century)


class TestTEWI(unittest.TestCase):
    """Leakage and electricity on the same axis."""

    def setUp(self):
        self.item = rg.build_equipment("air_source_heat_pump")

    def test_total_is_direct_plus_indirect(self):
        result = rg.tewi(self.item)
        self.assertAlmostEqual(
            result["direct_co2e"] + result["indirect_co2e"],
            result["total_co2e"],
            places=2,
        )

    def test_a_zero_carbon_grid_leaves_only_the_leak(self):
        result = rg.tewi(self.item, grid_intensity=0.0)
        self.assertAlmostEqual(result["indirect_co2e"], 0.0)
        self.assertAlmostEqual(result["total_co2e"], result["direct_co2e"])

    def test_a_dirtier_grid_raises_the_total(self):
        clean = rg.tewi(self.item, grid_intensity=0.05)["total_co2e"]
        dirty = rg.tewi(self.item, grid_intensity=0.82)["total_co2e"]
        self.assertGreater(dirty, clean)

    def test_the_direct_share_falls_as_the_grid_dirties(self):
        clean = rg.tewi(self.item, grid_intensity=0.05)["direct_share"]
        dirty = rg.tewi(self.item, grid_intensity=0.82)["direct_share"]
        self.assertGreater(clean, dirty)

    def test_an_efficiency_penalty_raises_the_indirect_term(self):
        base = rg.tewi(self.item)["indirect_co2e"]
        worse = rg.tewi(self.item, efficiency_penalty=0.2)["indirect_co2e"]
        self.assertAlmostEqual(worse, base * 1.2, places=2)

    def test_a_negative_grid_intensity_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.tewi(self.item, grid_intensity=-0.1)

    def test_an_impossible_efficiency_gain_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.tewi(self.item, efficiency_penalty=-1.0)

    def test_every_grid_preset_works(self):
        for name, intensity in rg.GRID_INTENSITIES.items():
            with self.subTest(grid=name):
                self.assertGreater(rg.tewi(self.item, intensity)["total_co2e"], 0.0)


class TestRetrofit(unittest.TestCase):
    """The threshold, which is the whole point of the module."""

    def setUp(self):
        self.item = rg.build_equipment("air_source_heat_pump")

    def test_a_cleaner_gas_at_equal_efficiency_wins_everywhere(self):
        result = rg.retrofit_comparison(self.item, "R-290", efficiency_penalty=0.0)
        self.assertIsNone(result["breakeven_grid_intensity"])
        self.assertIn("every grid intensity", result["verdict"])

    def test_a_dirtier_gas_at_equal_efficiency_never_wins(self):
        item = rg.build_equipment("air_source_heat_pump", gas="R-32")
        result = rg.retrofit_comparison(item, "R-404A", efficiency_penalty=0.0)
        self.assertIsNone(result["breakeven_grid_intensity"])
        self.assertIn("never wins", result["verdict"])

    def test_a_penalty_produces_a_finite_threshold(self):
        result = rg.retrofit_comparison(self.item, "R-290", efficiency_penalty=0.25)
        self.assertIsNotNone(result["breakeven_grid_intensity"])
        self.assertGreater(result["breakeven_grid_intensity"], 0.0)

    def test_the_threshold_is_where_the_two_effects_cancel(self):
        # Evaluated exactly at the breakeven, the swap must be a wash.
        result = rg.retrofit_comparison(self.item, "R-290", efficiency_penalty=0.25)
        at_threshold = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.25,
            grid_intensity=result["breakeven_grid_intensity"],
        )
        self.assertAlmostEqual(at_threshold["net_change"], 0.0, places=1)

    def test_the_swap_wins_below_the_threshold_and_loses_above_it(self):
        threshold = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.25
        )["breakeven_grid_intensity"]
        below = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.25,
            grid_intensity=threshold * 0.5,
        )
        above = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.25,
            grid_intensity=threshold * 2.0,
        )
        self.assertTrue(below["worthwhile_here"])
        self.assertFalse(above["worthwhile_here"])

    def test_a_bigger_penalty_lowers_the_threshold(self):
        # More extra electricity means a cleaner grid is needed to absorb it.
        thresholds = [
            rg.retrofit_comparison(
                self.item, "R-290", efficiency_penalty=penalty
            )["breakeven_grid_intensity"]
            for penalty in (0.10, 0.20, 0.30, 0.40)
        ]
        for earlier, later in zip(thresholds, thresholds[1:]):
            self.assertLess(later, earlier)

    def test_direct_only_advice_would_be_wrong_here(self):
        # The case the module exists for: the gas is 100x cleaner, the direct
        # saving is large, and the swap still loses on a coal grid.
        result = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.40,
            grid_intensity=rg.GRID_INTENSITIES["coal_heavy"],
        )
        self.assertLess(result["direct_change"], 0.0)
        self.assertFalse(result["worthwhile_here"])

    def test_the_same_swap_wins_on_a_clean_grid(self):
        result = rg.retrofit_comparison(
            self.item, "R-290", efficiency_penalty=0.40,
            grid_intensity=rg.GRID_INTENSITIES["low_carbon"],
        )
        self.assertTrue(result["worthwhile_here"])

    def test_a_flammability_change_is_flagged(self):
        note = rg.retrofit_comparison(self.item, "R-290")["safety_note"]
        self.assertIsNotNone(note)
        self.assertIn("flammable", note)

    def test_a_like_for_like_safety_class_is_not_flagged(self):
        self.assertIsNone(rg.retrofit_comparison(self.item, "R-134a")["safety_note"])

    def test_a_toxic_alternative_is_flagged(self):
        note = rg.retrofit_comparison(self.item, "R-717")["safety_note"]
        self.assertIn("toxic", note)

    def test_unknown_alternative_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.retrofit_comparison(self.item, "R-999")

    def test_options_are_ranked_and_exclude_the_current_gas(self):
        options = rg.retrofit_options(self.item)
        self.assertEqual(len(options), len(rg.list_refrigerants()) - 1)
        for option in options:
            self.assertNotEqual(option["to_gas"], self.item["gas"])
        for earlier, later in zip(options, options[1:]):
            self.assertLessEqual(earlier["swapped_tewi"], later["swapped_tewi"])


class TestRegister(unittest.TestCase):
    """A whole src.lifestyle.household."""

    def setUp(self):
        self.items = [
            rg.build_equipment("air_source_heat_pump"),
            rg.build_equipment("domestic_fridge"),
            rg.build_equipment("split_ac"),
            rg.build_equipment("car_ac"),
        ]

    def test_the_summary_adds_up(self):
        summary = rg.register_summary(self.items)
        self.assertEqual(summary["count"], len(self.items))
        self.assertAlmostEqual(
            summary["lifetime_direct_co2e"] + summary["lifetime_indirect_co2e"],
            summary["lifetime_tewi"],
            places=1,
        )

    def test_items_are_ranked_by_impact(self):
        rows = rg.register_summary(self.items)["items"]
        for earlier, later in zip(rows, rows[1:]):
            self.assertGreaterEqual(earlier["lifetime_tewi"], later["lifetime_tewi"])

    def test_total_charge_is_the_sum_of_charges(self):
        summary = rg.register_summary(self.items)
        self.assertAlmostEqual(
            summary["total_charge_kg"],
            sum(item["charge_kg"] for item in self.items),
            places=4,
        )

    def test_an_empty_register_is_refused(self):
        with self.assertRaises(rg.RefrigerantError):
            rg.register_summary([])

    def test_phase_down_exposure_finds_the_restricted_gases(self):
        rows = rg.phase_down_exposure(self.items)
        gases = {row["gas"] for row in rows}
        self.assertIn("R-410A", gases)
        self.assertNotIn("R-600a", gases)

    def test_unrestricted_equipment_shows_no_exposure(self):
        self.assertEqual(
            rg.phase_down_exposure([rg.build_equipment("domestic_fridge")]), []
        )

    def test_insights_are_produced(self):
        insights = rg.get_refrigerant_insights(rg.register_summary(self.items))
        self.assertTrue(insights)
        for line in insights:
            self.assertIsInstance(line, str)

    def test_an_empty_summary_says_so(self):
        self.assertEqual(
            rg.get_refrigerant_insights({"items": []}), ["No equipment registered."]
        )


class TestSensitivity(unittest.TestCase):
    """The four uncertain inputs."""

    def setUp(self):
        self.item = rg.build_equipment("air_source_heat_pump")

    def test_all_four_parameters_appear(self):
        parameters = {row["parameter"] for row in rg.sensitivity(self.item)}
        self.assertEqual(
            parameters,
            {"Leak rate", "End-of-life recovery", "Grid intensity", "GWP basis"},
        )

    def test_every_row_is_positive_and_labelled(self):
        for row in rg.sensitivity(self.item):
            with self.subTest(setting=row["setting"]):
                self.assertGreater(row["total_co2e"], 0.0)
                self.assertTrue(row["setting"])

    def test_the_recovery_rows_span_a_real_range(self):
        rows = [
            row for row in rg.sensitivity(self.item)
            if row["parameter"] == "End-of-life recovery"
        ]
        values = [row["direct_co2e"] for row in rows]
        self.assertGreater(max(values), min(values))

    def test_the_gwp_basis_rows_span_a_real_range(self):
        rows = [
            row for row in rg.sensitivity(self.item)
            if row["parameter"] == "GWP basis"
        ]
        values = [row["direct_co2e"] for row in rows]
        self.assertGreater(max(values) / min(values), 1.5)


class TestStorage(unittest.TestCase):
    """Persistence, against a throwaway src.core.database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = rg.DB_NAME
        rg.DB_NAME = self.path
        rg.init_refrigerant_db()
        self.items = [
            rg.build_equipment("air_source_heat_pump"),
            rg.build_equipment("domestic_fridge"),
        ]
        self.summary = rg.register_summary(self.items)

    def tearDown(self):
        rg.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_init_is_idempotent(self):
        self.assertTrue(rg.init_refrigerant_db())
        self.assertTrue(rg.init_refrigerant_db())

    def test_a_saved_register_comes_back(self):
        register_id = rg.save_register(1, "Home", self.items, self.summary)
        self.assertIsNotNone(register_id)
        registers = rg.get_registers(1)
        self.assertEqual(len(registers), 1)
        self.assertEqual(registers[0]["name"], "Home")
        self.assertEqual(registers[0]["item_count"], 2)

    def test_equipment_survives_the_round_trip(self):
        rg.save_register(1, "Home", self.items, self.summary)
        stored = rg.get_registers(1)[0]["detail"]
        self.assertEqual(len(stored["equipment"]), 2)
        self.assertEqual(stored["equipment"][0]["gas"], self.items[0]["gas"])

    def test_registers_are_newest_first(self):
        for name in ("first", "second", "third"):
            rg.save_register(1, name, self.items, self.summary)
        self.assertEqual(rg.get_registers(1)[0]["name"], "third")

    def test_users_do_not_see_each_other(self):
        rg.save_register(1, "mine", self.items, self.summary)
        rg.save_register(2, "theirs", self.items, self.summary)
        self.assertEqual(len(rg.get_registers(1)), 1)

    def test_delete_removes_it(self):
        register_id = rg.save_register(1, "gone", self.items, self.summary)
        self.assertTrue(rg.delete_register(register_id, 1))
        self.assertEqual(rg.get_registers(1), [])

    def test_you_cannot_delete_someone_elses(self):
        register_id = rg.save_register(1, "mine", self.items, self.summary)
        self.assertFalse(rg.delete_register(register_id, 2))

    def test_the_limit_is_respected(self):
        for n in range(5):
            rg.save_register(1, f"r{n}", self.items, self.summary)
        self.assertEqual(len(rg.get_registers(1, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
