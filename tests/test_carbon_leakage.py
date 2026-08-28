"""Tests for the carbon leakage and trade adjustment engine.

Two properties are load-bearing. The three accounting frames must reconcile -
territorial plus imports equals consumption - or the module is comparing
different quantities, which is the error it exists to prevent. And the
substitution split must be exact, because a residual in an analysis of whether
a reduction was real invites the reader to assume the remainder was the real
part.
"""

import pytest

from src.carbon.carbon_leakage import (
    CBAM_PHASE_IN,
    FREIGHT_MODES,
    REGIONS,
    SECTORS,
    LeakageError,
    accounting_split,
    benchmark_correction,
    build_basket,
    build_item,
    cbam_exposure,
    cbam_phase_in,
    cbam_trajectory,
    compare_to_territorial_target,
    delete_basket,
    embodied_emissions,
    freight_versus_origin,
    get_baskets,
    get_leakage_insights,
    get_region,
    get_sector,
    intensity_breakdown,
    leakage_rate,
    list_freight_modes,
    list_regions,
    list_sectors,
    origin_intensity,
    save_basket,
    substitution,
)


def _domestic_washer():
    return build_item("Washing machine", "machinery", "eu", 60.0, 300.0, "road_truck")


def _imported_washer():
    return build_item(
        "Washing machine", "machinery", "china", 60.0, 19_000.0, "sea_container"
    )


def _basket(items=None):
    return build_basket("Household", items or [
        _imported_washer(),
        build_item("Steel", "steel", "turkey", 200.0, 2_500.0, "sea_container"),
        build_item("Sofa", "furniture", "eu", 45.0, 400.0, "road_truck"),
    ])


# ---------------------------------------------------------------------------
# Intensity
# ---------------------------------------------------------------------------

class TestIntensity:

    def test_a_dirtier_grid_raises_intensity(self):
        assert origin_intensity("aluminium", "china") > origin_intensity(
            "aluminium", "eu"
        )

    def test_a_cleaner_grid_can_beat_the_home_one(self):
        # The case that stops 'imported' being a synonym for 'dirtier'.
        assert origin_intensity("aluminium", "brazil") < origin_intensity(
            "aluminium", "eu"
        )

    def test_aluminium_is_dominated_by_electricity(self):
        breakdown = intensity_breakdown("aluminium", "eu")
        assert breakdown["electricity_share"] > 0.6

    def test_cement_is_barely_moved_by_the_grid(self):
        # Calcination releases CO2 from the limestone and no grid cleans it up.
        breakdown = intensity_breakdown("cement", "india")
        assert breakdown["electricity_share"] < 0.2

    def test_cement_varies_less_between_origins_than_aluminium(self):
        cement_spread = (
            origin_intensity("cement", "india") / origin_intensity("cement", "brazil")
        )
        aluminium_spread = (
            origin_intensity("aluminium", "india")
            / origin_intensity("aluminium", "brazil")
        )
        assert aluminium_spread > cement_spread

    def test_imported_electricity_is_exactly_the_origin_grid(self):
        for key in REGIONS:
            assert origin_intensity("electricity", key) == pytest.approx(
                REGIONS[key]["grid_intensity"]
            )

    def test_the_breakdown_sums_to_the_intensity(self):
        breakdown = intensity_breakdown("steel", "china")
        assert breakdown["process"] + breakdown["electricity"] == pytest.approx(
            breakdown["total"], rel=1e-12
        )

    def test_an_unknown_region_is_refused_with_the_list(self):
        with pytest.raises(LeakageError, match="Known:"):
            origin_intensity("steel", "atlantis")

    def test_an_unknown_sector_is_refused_with_the_list(self):
        with pytest.raises(LeakageError, match="Known:"):
            origin_intensity("unobtanium", "eu")

    def test_a_missing_origin_is_refused_with_the_reason(self):
        with pytest.raises(LeakageError, match="assumption this module exists"):
            build_item("x", "steel", None, 10)


# ---------------------------------------------------------------------------
# Items and freight
# ---------------------------------------------------------------------------

class TestItems:

    def test_production_and_freight_are_reported_apart(self):
        emissions = embodied_emissions(_imported_washer())
        assert emissions["production_kg_co2"] > 0
        assert emissions["freight_kg_co2"] > 0
        assert emissions["total_kg_co2"] == pytest.approx(
            emissions["production_kg_co2"] + emissions["freight_kg_co2"]
        )

    def test_sea_freight_across_the_world_is_a_small_term(self):
        # The number that stops 'shipped from the other side of the world'
        # doing more argumentative work than it can support.
        emissions = embodied_emissions(_imported_washer())
        assert emissions["freight_share"] < 0.15

    def test_air_freight_is_not_a_small_term(self):
        flown = build_item("Parts", "electronics", "china", 5.0, 8_000.0, "air_freight")
        shipped = build_item(
            "Parts", "electronics", "china", 5.0, 8_000.0, "sea_container"
        )
        assert (
            embodied_emissions(flown)["freight_kg_co2"]
            > 50 * embodied_emissions(shipped)["freight_kg_co2"]
        )

    def test_electricity_carries_no_freight(self):
        item = build_item("Imported power", "electricity", "brazil", 1_000.0, 500.0)
        assert embodied_emissions(item)["freight_kg_co2"] == 0.0

    def test_freight_scales_with_distance(self):
        near = build_item("Steel", "steel", "turkey", 100.0, 1_000.0)
        far = build_item("Steel", "steel", "turkey", 100.0, 2_000.0)
        assert embodied_emissions(far)["freight_kg_co2"] == pytest.approx(
            2 * embodied_emissions(near)["freight_kg_co2"]
        )

    def test_a_negative_quantity_is_refused(self):
        with pytest.raises(LeakageError, match="cannot be negative"):
            build_item("x", "steel", "eu", -1)

    def test_a_negative_distance_is_refused(self):
        with pytest.raises(LeakageError, match="cannot be negative"):
            build_item("x", "steel", "eu", 1, -100)

    def test_an_unknown_freight_mode_is_refused(self):
        with pytest.raises(LeakageError, match="Unknown freight mode"):
            build_item("x", "steel", "eu", 1, 100, "teleport")

    def test_an_empty_basket_is_refused(self):
        with pytest.raises(LeakageError, match="at least one item"):
            build_basket("empty", [])


# ---------------------------------------------------------------------------
# Accounting frames
# ---------------------------------------------------------------------------

class TestAccounting:

    def test_the_three_frames_reconcile(self):
        split = accounting_split(_basket(), "eu")
        assert split["reconciles"] is True
        assert split["consumption_kg_co2"] == pytest.approx(
            split["territorial_kg_co2"] + split["imported_kg_co2"], rel=1e-12
        )

    def test_domestic_goods_land_in_the_territorial_column(self):
        split = accounting_split(
            build_basket("home only", [_domestic_washer()]), "eu"
        )
        assert split["imported_kg_co2"] == 0.0
        assert split["import_share"] == 0.0

    def test_imported_goods_land_outside_it(self):
        split = accounting_split(
            build_basket("imports only", [_imported_washer()]), "eu"
        )
        assert split["territorial_kg_co2"] == 0.0
        assert split["import_share"] == pytest.approx(1.0)

    def test_moving_home_moves_the_boundary(self):
        basket = _basket()
        as_european = accounting_split(basket, "eu")
        as_chinese = accounting_split(basket, "china")
        assert as_european["consumption_kg_co2"] == pytest.approx(
            as_chinese["consumption_kg_co2"], rel=1e-12
        )
        assert as_european["territorial_kg_co2"] != as_chinese["territorial_kg_co2"]

    def test_comparing_consumption_to_a_territorial_target_is_refused(self):
        # The single error the module exists to stop. It raises rather than
        # returning a caveated number that would be quoted without the caveat.
        split = accounting_split(_basket(), "eu")
        with pytest.raises(LeakageError, match="not comparable"):
            compare_to_territorial_target(split, 5_000)

    def test_the_refusal_names_both_quantities(self):
        split = accounting_split(_basket(), "eu")
        with pytest.raises(LeakageError, match="emitted abroad"):
            compare_to_territorial_target(split, 5_000)


# ---------------------------------------------------------------------------
# Benchmark correction
# ---------------------------------------------------------------------------

class TestBenchmark:

    def test_a_net_importer_is_corrected_upward(self):
        correction = benchmark_correction(6_000, import_share=0.30)
        assert correction["consumption_per_capita_kg"] > 6_000
        assert correction["net_importer"] is True

    def test_a_net_exporter_is_corrected_downward(self):
        correction = benchmark_correction(6_000, import_share=0.0, export_share=0.25)
        assert correction["consumption_per_capita_kg"] < 6_000
        assert correction["net_importer"] is False

    def test_a_balanced_economy_needs_no_correction(self):
        correction = benchmark_correction(6_000, import_share=0.0, export_share=0.0)
        assert correction["adjustment_kg"] == pytest.approx(0.0)

    def test_the_correction_explains_which_way_it_ran(self):
        assert "understates the household" in benchmark_correction(
            6_000, import_share=0.3
        )["note"]

    def test_a_non_positive_benchmark_is_refused(self):
        with pytest.raises(LeakageError, match="must be positive"):
            benchmark_correction(0, 0.3)

    def test_a_share_of_one_is_refused(self):
        with pytest.raises(LeakageError, match="below 1"):
            benchmark_correction(6_000, import_share=1.0)


# ---------------------------------------------------------------------------
# Substitution
# ---------------------------------------------------------------------------

class TestSubstitution:

    def test_offshoring_is_detected(self):
        swap = substitution(_domestic_washer(), _imported_washer(), "eu")
        assert swap["offshored"] is True
        assert swap["leakage_detected"] is True

    def test_the_territorial_figure_falls_while_the_global_one_rises(self):
        swap = substitution(_domestic_washer(), _imported_washer(), "eu")
        assert swap["territorial_change"] < 0
        assert swap["global_change"] > 0

    def test_the_relocated_quantity_is_reported(self):
        swap = substitution(_domestic_washer(), _imported_washer(), "eu")
        assert swap["relocated_kg_co2"] < 0

    def test_the_split_is_exact(self):
        # A residual here would invite the reader to assume it was the good
        # part, so there is not one.
        swap = substitution(_domestic_washer(), _imported_washer(), "eu")
        assert swap["residual"] == pytest.approx(0.0, abs=1e-9)

    def test_buying_less_of_the_same_thing_is_a_quantity_effect(self):
        before = build_item("Steel", "steel", "eu", 200.0)
        after = build_item("Steel", "steel", "eu", 100.0)
        swap = substitution(before, after, "eu")
        assert swap["quantity_effect"] < 0
        assert swap["intensity_effect"] == pytest.approx(0.0)
        assert swap["origin_changed"] is False
        assert swap["leakage_detected"] is False

    def test_switching_to_a_cleaner_origin_is_an_intensity_effect(self):
        before = build_item("Aluminium", "aluminium", "china", 10.0)
        after = build_item("Aluminium", "aluminium", "brazil", 10.0)
        swap = substitution(before, after, "eu")
        assert swap["intensity_effect"] < 0
        assert swap["quantity_effect"] == pytest.approx(0.0)
        assert swap["leakage_detected"] is False

    def test_relocation_and_improvement_are_kept_apart(self):
        # Moving aluminium production to Brazil relocates emissions AND
        # reduces them. Collapsing the two would hide the case, so the module
        # reports both flags and the note names the overstatement.
        before = build_item("Aluminium", "aluminium", "eu", 10.0)
        after = build_item("Aluminium", "aluminium", "brazil", 10.0, 9_000.0)
        swap = substitution(before, after, "eu")
        assert swap["offshored"] is True
        assert swap["leakage_detected"] is True
        assert swap["net_global_improvement"] is True
        assert "still an improvement" in swap["note"]

    def test_offshoring_to_a_dirtier_grid_is_not_an_improvement(self):
        swap = substitution(_domestic_washer(), _imported_washer(), "eu")
        assert swap["leakage_detected"] is True
        assert swap["net_global_improvement"] is False
        assert "Nothing was reduced" in swap["note"]

    def test_a_swap_with_no_origin_change_says_so(self):
        swap = substitution(
            build_item("Steel", "steel", "eu", 100.0),
            build_item("Steel", "steel", "eu", 90.0),
            "eu",
        )
        assert "No relocation" in swap["note"]


# ---------------------------------------------------------------------------
# Leakage over a period
# ---------------------------------------------------------------------------

class TestLeakageRate:

    def _before(self):
        return build_basket("2024", [
            build_item("Washing machine", "machinery", "eu", 60.0, 300.0, "road_truck"),
            build_item("Steel", "steel", "eu", 200.0, 500.0, "road_truck"),
        ])

    def _after_offshored(self):
        return build_basket("2026", [
            build_item(
                "Washing machine", "machinery", "china", 60.0, 19_000.0,
                "sea_container",
            ),
            build_item("Steel", "steel", "turkey", 200.0, 2_500.0, "sea_container"),
        ])

    def _after_genuine(self):
        return build_basket("2026", [
            build_item("Washing machine", "machinery", "eu", 30.0, 300.0, "road_truck"),
            build_item("Steel", "steel", "eu", 100.0, 500.0, "road_truck"),
        ])

    def test_the_two_factor_split_is_exact(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        assert result["residual"] == pytest.approx(0.0, abs=1e-9)

    def test_offshoring_collapses_the_territorial_figure(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        assert result["territorial_change"] < 0
        assert result["consumption_change"] > result["territorial_change"]

    def test_offshoring_shows_up_as_an_origin_effect(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        assert result["origin_effect"] != 0
        assert result["quantity_effect"] == pytest.approx(0.0)

    def test_buying_less_shows_up_as_a_quantity_effect(self):
        result = leakage_rate(self._before(), self._after_genuine(), "eu")
        assert result["quantity_effect"] < 0
        assert result["origin_effect"] == pytest.approx(0.0)

    def test_a_genuine_reduction_has_no_leakage_share(self):
        result = leakage_rate(self._before(), self._after_genuine(), "eu")
        assert result["leakage_share_of_reduction"] == 0.0

    def test_an_item_appearing_counts_as_a_quantity_change(self):
        # Buying something new is a change in what is consumed, not in where
        # it came from, and it belongs in the quantity term.
        after = build_basket("2026", list(self._before()["items"]) + [
            build_item("Sofa", "furniture", "eu", 45.0, 400.0, "road_truck"),
        ])
        result = leakage_rate(self._before(), after, "eu")
        assert result["quantity_effect"] > 0
        assert result["origin_effect"] == pytest.approx(0.0)

    def test_an_item_disappearing_counts_as_a_quantity_change(self):
        after = build_basket("2026", [self._before()["items"][0]])
        result = leakage_rate(self._before(), after, "eu")
        assert result["quantity_effect"] < 0
        assert result["origin_effect"] == pytest.approx(0.0)

    def test_the_item_table_names_both_origins(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        moved = [row for row in result["items"] if row["before_origin"] != row["after_origin"]]
        assert len(moved) == 2

    def test_a_reduction_that_is_mostly_relocation_is_flagged(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        insights = get_leakage_insights(result)
        assert any("did not happen" in item["title"] for item in insights)

    def test_a_real_reduction_is_not_flagged(self):
        result = leakage_rate(self._before(), self._after_genuine(), "eu")
        insights = get_leakage_insights(result)
        assert any("survives a consumption frame" in item["title"] for item in insights)

    def test_every_insight_has_a_level_and_a_body(self):
        result = leakage_rate(self._before(), self._after_offshored(), "eu")
        for item in get_leakage_insights(result):
            assert item["level"] in {"info", "warning"}
            assert item["title"] and item["body"]


# ---------------------------------------------------------------------------
# CBAM
# ---------------------------------------------------------------------------

class TestCBAM:

    def test_the_phase_in_rises_monotonically(self):
        shares = [CBAM_PHASE_IN[year] for year in sorted(CBAM_PHASE_IN)]
        assert shares == sorted(shares)

    def test_it_reaches_full_charge_and_stops(self):
        assert cbam_phase_in(2034) == 1.0
        assert cbam_phase_in(2050) == 1.0

    def test_nothing_is_charged_before_it_starts(self):
        assert cbam_phase_in(2020) == 0.0

    def test_a_non_year_is_refused(self):
        with pytest.raises(LeakageError, match="whole year"):
            cbam_phase_in("soon")

    def test_only_covered_imported_sectors_are_charged(self):
        exposure = cbam_exposure(_basket(), 85.0, 2030, "eu")
        assert [row["sector"] for row in exposure["covered"]] == ["steel"]
        assert [row["sector"] for row in exposure["uncovered"]] == ["machinery"]
        assert [row["sector"] for row in exposure["domestic"]] == ["furniture"]

    def test_domestic_goods_are_never_charged(self):
        exposure = cbam_exposure(
            build_basket("home", [build_item("Steel", "steel", "eu", 200.0)]),
            85.0, 2034, "eu",
        )
        assert exposure["cost"] == 0.0
        assert exposure["covered"] == []

    def test_uncovered_is_reported_as_uncovered_not_as_zero(self):
        # Zero and out-of-scope mean very different things to anyone planning.
        exposure = cbam_exposure(_basket(), 85.0, 2030, "eu")
        assert exposure["uncovered_emissions_kg"] > 0
        assert 0 < exposure["coverage_share"] < 1

    def test_the_cost_rises_with_the_phase_in(self):
        trajectory = cbam_trajectory(_basket(), 85.0, "eu")
        costs = [row["cost"] for row in trajectory]
        assert costs == sorted(costs)
        assert costs[-1] > 10 * costs[0]

    def test_the_full_phase_in_cost_is_reported_from_the_start(self):
        exposure = cbam_exposure(_basket(), 85.0, 2026, "eu")
        assert exposure["cost_at_full_phase_in"] > exposure["cost"]

    def test_freight_is_excluded_from_the_charge(self):
        exposure = cbam_exposure(_basket(), 85.0, 2034, "eu")
        covered = exposure["covered"][0]
        assert covered["chargeable_kg_co2"] == pytest.approx(
            covered["production_kg_co2"]
        )
        assert covered["freight_kg_co2"] > 0

    def test_a_negative_carbon_price_is_refused(self):
        with pytest.raises(LeakageError, match="cannot be negative"):
            cbam_exposure(_basket(), -10, 2030, "eu")

    def test_the_covered_sectors_are_the_legislated_ones(self):
        covered = {key for key, value in SECTORS.items() if value["cbam_covered"]}
        assert covered == {
            "steel", "aluminium", "cement", "fertiliser", "electricity", "hydrogen"
        }


# ---------------------------------------------------------------------------
# Local versus low-carbon
# ---------------------------------------------------------------------------

class TestLocalVersusClean:

    def test_the_factory_usually_beats_the_shipping(self):
        comparison = freight_versus_origin(
            build_item("Aluminium", "aluminium", "china", 50.0, 19_000.0), "eu"
        )
        assert comparison["dominant_term"] == "production"
        assert comparison["production_over_freight"] > 5

    def test_local_is_not_always_better(self):
        # Brazilian aluminium beats European even after nine thousand
        # kilometres of sea freight, which is the whole point of separating
        # the two terms.
        comparison = freight_versus_origin(
            build_item("Aluminium", "aluminium", "brazil", 50.0, 9_000.0), "eu"
        )
        assert comparison["net_gap"] > 0
        assert comparison["local_is_better"] is False

    def test_switching_to_a_dirtier_local_origin_is_reported_as_worse(self):
        comparison = freight_versus_origin(
            build_item("Aluminium", "aluminium", "brazil", 50.0, 9_000.0), "india"
        )
        assert comparison["production_gap"] > 0


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

class TestReference:

    def test_every_region_carries_a_note(self):
        for entry in list_regions():
            assert len(entry["note"]) > 40
            assert entry["grid_intensity"] > 0

    def test_every_sector_carries_a_note_and_a_unit(self):
        for entry in list_sectors():
            assert len(entry["note"]) > 40
            assert entry["unit"] in {"kg", "kWh"}

    def test_every_freight_mode_carries_a_note(self):
        for entry in list_freight_modes():
            assert len(entry["note"]) > 30
            assert entry["intensity"] > 0

    def test_air_freight_is_the_most_intense_mode(self):
        assert FREIGHT_MODES["air_freight"]["intensity"] == max(
            mode["intensity"] for mode in FREIGHT_MODES.values()
        )

    def test_get_region_returns_none_for_an_unknown_key(self):
        assert get_region("narnia") is None

    def test_get_sector_returns_none_for_an_unknown_key(self):
        assert get_sector("alchemy") is None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.carbon.carbon_leakage.DB_NAME", str(tmp_path / "test.db")
        )

    def _save(self, user="user-1"):
        basket = _basket()
        split = accounting_split(basket, "eu")
        return save_basket(user, basket, split), split

    def test_a_saved_basket_comes_back(self):
        row_id, split = self._save()
        saved = get_baskets("user-1")
        assert len(saved) == 1
        assert saved[0]["id"] == row_id
        assert saved[0]["home_region"] == "eu"

    def test_the_three_frames_round_trip(self):
        _, split = self._save()
        saved = get_baskets("user-1")[0]
        assert saved["territorial_kg"] == pytest.approx(
            split["territorial_kg_co2"], rel=1e-9
        )
        assert saved["imported_kg"] == pytest.approx(
            split["imported_kg_co2"], rel=1e-9
        )
        assert saved["consumption_kg"] == pytest.approx(
            split["consumption_kg_co2"], rel=1e-9
        )

    def test_the_payload_keeps_the_origins(self):
        self._save()
        payload = get_baskets("user-1")[0]["payload"]
        assert "china" in payload["origins"]

    def test_users_do_not_see_each_others_baskets(self):
        self._save("user-1")
        self._save("user-2")
        assert len(get_baskets("user-1")) == 1
        assert len(get_baskets("user-2")) == 1

    def test_saving_without_a_user_is_refused(self):
        basket = _basket()
        with pytest.raises(LeakageError, match="needs a user"):
            save_basket("", basket, accounting_split(basket, "eu"))

    def test_reading_without_a_user_returns_nothing(self):
        assert get_baskets(None) == []

    def test_deleting_removes_the_row(self):
        row_id, _ = self._save()
        assert delete_basket("user-1", row_id) is True
        assert get_baskets("user-1") == []

    def test_deleting_another_users_row_does_nothing(self):
        row_id, _ = self._save()
        assert delete_basket("user-2", row_id) is False
        assert len(get_baskets("user-1")) == 1

    def test_deleting_without_a_user_returns_false(self):
        assert delete_basket(None, 1) is False
