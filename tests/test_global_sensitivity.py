"""Tests for the global sensitivity engine.

The load-bearing tests are the Ishigami ones. That function has closed-form
Sobol indices, and one of its inputs has a first-order index of exactly zero
while carrying roughly a quarter of the output variance through an interaction.
Any method that varies one thing at a time reports that input as irrelevant.
If this module ever agrees, the module has no reason to exist, so those tests
are written as assertions about the *gap* between S1 and S_T rather than about
the indices in isolation.

The rest is the usual: the estimators must not go negative where the maths says
they cannot, the refusals must fire, and a study whose sample cannot separate
two parameters must decline to order them.
"""

import math

import pytest

from src.utils.global_sensitivity import (
    ADDITIVE_INTERACTION_CEILING,
    DEMO_MODELS,
    DEFAULT_SEED,
    ISHIGAMI_A,
    ISHIGAMI_B,
    MAX_PARAMETERS,
    MIN_BASE_SAMPLES,
    NEGLIGIBLE_INDEX,
    SensitivityError,
    additive_model,
    additivity_verdict,
    analyse,
    bootstrap_intervals,
    build_parameter,
    convergence,
    delete_study,
    demo_parameters,
    diagnose,
    evaluate_matrix,
    first_order_index,
    get_sensitivity_notes,
    get_studies,
    ishigami_analytic,
    ishigami_model,
    ishigami_parameters,
    list_demo_models,
    list_distributions,
    measurement_priorities,
    morris_screening,
    norm_ppf,
    parameter_bounds,
    percentile,
    rank_with_confidence,
    saltelli_matrices,
    save_study,
    shared_grid_model,
    summarise,
    total_effect_index,
    transform,
    validate_against_ishigami,
)


# ---------------------------------------------------------------------------
# Models used across several tests
# ---------------------------------------------------------------------------


def _product_model(row):
    """Purely multiplicative: every bit of influence is interaction."""
    return row["a"] * row["b"]


def _sum_model(row):
    return row["a"] + row["b"]


def _ignores_b(row):
    return row["a"] * 3.0


def _constant(row):
    return 42.0


def _unit_pair():
    return [
        build_parameter("a", "uniform", low=1.0, high=3.0),
        build_parameter("b", "uniform", low=1.0, high=3.0),
    ]


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------


class TestNormPpf:
    def test_median_is_zero(self):
        assert abs(norm_ppf(0.5)) < 1e-9

    @pytest.mark.parametrize(
        "probability,expected",
        [(0.975, 1.959964), (0.95, 1.644854), (0.84134, 1.0), (0.99, 2.326348)],
    )
    def test_known_quantiles(self, probability, expected):
        assert norm_ppf(probability) == pytest.approx(expected, abs=1e-4)

    def test_symmetry(self):
        for probability in (0.01, 0.1, 0.3, 0.45):
            assert norm_ppf(probability) == pytest.approx(-norm_ppf(1.0 - probability), abs=1e-8)

    def test_monotone(self):
        values = [norm_ppf(p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)]
        assert values == sorted(values)

    @pytest.mark.parametrize("probability", [0.0, 1.0, -0.1, 1.5])
    def test_rejects_out_of_range(self, probability):
        with pytest.raises(SensitivityError):
            norm_ppf(probability)


class TestPercentile:
    def test_endpoints(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile(values, 0.0) == 1.0
        assert percentile(values, 100.0) == 5.0

    def test_interpolates(self):
        assert percentile([0.0, 10.0], 50.0) == pytest.approx(5.0)

    def test_single_value(self):
        assert percentile([7.0], 42.0) == 7.0

    def test_rejects_empty(self):
        with pytest.raises(SensitivityError):
            percentile([], 50.0)


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


class TestBuildParameter:
    def test_uniform(self):
        parameter = build_parameter("grid", "uniform", low=0.1, high=0.5, unit="kg/kWh")
        assert parameter["distribution"] == "uniform"
        assert parameter["low"] == 0.1
        assert parameter["unit"] == "kg/kWh"

    def test_triangular_defaults_mode_to_midpoint(self):
        parameter = build_parameter("x", "triangular", low=0.0, high=10.0)
        assert parameter["mode"] == 5.0

    def test_requires_a_name(self):
        with pytest.raises(SensitivityError):
            build_parameter("   ", "uniform", low=0.0, high=1.0)

    def test_rejects_unknown_distribution(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "cauchy", low=0.0, high=1.0)

    def test_rejects_degenerate_range(self):
        """A parameter with no spread has no variance to contribute.

        Allowing it would produce an index of exactly zero that reads as a
        finding about the model rather than about the input specification.
        """
        with pytest.raises(SensitivityError):
            build_parameter("x", "uniform", low=2.0, high=2.0)

    def test_rejects_inverted_range(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "uniform", low=5.0, high=1.0)

    def test_rejects_mode_outside_bounds(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "triangular", low=0.0, high=1.0, mode=4.0)

    def test_rejects_non_positive_sigma(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "normal", mean=1.0, sigma=0.0)

    def test_rejects_gsd_of_one(self):
        """GSD 1.0 is a constant dressed as a distribution."""
        with pytest.raises(SensitivityError):
            build_parameter("x", "lognormal", median=1.0, gsd=1.0)

    def test_rejects_non_positive_median(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "lognormal", median=0.0, gsd=1.2)

    def test_rejects_missing_fields(self):
        with pytest.raises(SensitivityError):
            build_parameter("x", "uniform")

    def test_distribution_catalogue_is_complete(self):
        catalogue = list_distributions()
        assert {entry["key"] for entry in catalogue} == {
            "uniform",
            "triangular",
            "normal",
            "lognormal",
        }
        assert all(entry["needs"] for entry in catalogue)


class TestTransform:
    def test_uniform_endpoints(self):
        parameter = build_parameter("x", "uniform", low=2.0, high=6.0)
        assert transform(parameter, 0.0) == pytest.approx(2.0, abs=1e-6)
        assert transform(parameter, 1.0) == pytest.approx(6.0, abs=1e-6)
        assert transform(parameter, 0.5) == pytest.approx(4.0)

    def test_triangular_stays_inside_bounds(self):
        parameter = build_parameter("x", "triangular", low=1.0, high=9.0, mode=2.0)
        for step in range(21):
            value = transform(parameter, step / 20.0)
            assert 1.0 - 1e-9 <= value <= 9.0 + 1e-9

    def test_triangular_is_monotone(self):
        parameter = build_parameter("x", "triangular", low=0.0, high=1.0, mode=0.3)
        values = [transform(parameter, step / 10.0) for step in range(11)]
        assert values == sorted(values)

    def test_normal_median_is_the_mean(self):
        parameter = build_parameter("x", "normal", mean=5.0, sigma=2.0)
        assert transform(parameter, 0.5) == pytest.approx(5.0, abs=1e-6)

    def test_lognormal_median_and_gsd(self):
        parameter = build_parameter("x", "lognormal", median=100.0, gsd=1.5)
        assert transform(parameter, 0.5) == pytest.approx(100.0, abs=1e-4)
        # One sigma up on the log scale is exactly the GSD multiple.
        upper = transform(parameter, 0.8413447)
        assert upper / 100.0 == pytest.approx(1.5, rel=1e-3)

    def test_lognormal_is_strictly_positive(self):
        parameter = build_parameter("x", "lognormal", median=1.0, gsd=3.0)
        assert transform(parameter, 1e-9) > 0.0

    def test_parameter_bounds_are_ordered(self):
        parameter = build_parameter("x", "normal", mean=0.0, sigma=1.0)
        low, high = parameter_bounds(parameter)
        assert low < 0.0 < high


# ---------------------------------------------------------------------------
# Saltelli design
# ---------------------------------------------------------------------------


class TestSaltelliMatrices:
    def test_shape(self):
        design = saltelli_matrices(_unit_pair(), base_samples=32, seed=1)
        assert len(design["A"]) == 32
        assert len(design["B"]) == 32
        assert len(design["AB"]) == 2
        assert design["evaluations"] == 32 * (2 + 2)

    def test_ab_swaps_exactly_one_column(self):
        """AB_i must differ from A in parameter i and nowhere else.

        This is the property the whole estimator rests on. If a second column
        moves, the index attributed to parameter i is contaminated by whatever
        else changed.
        """
        design = saltelli_matrices(_unit_pair(), base_samples=16, seed=3)
        for column, name in enumerate(("a", "b")):
            other = "b" if name == "a" else "a"
            for index in range(16):
                swapped = design["AB"][column][index]
                assert swapped[other] == design["A"][index][other]
                assert swapped[name] == design["B"][index][name]

    def test_a_and_b_are_independent_draws(self):
        design = saltelli_matrices(_unit_pair(), base_samples=64, seed=5)
        identical = sum(
            1 for index in range(64) if design["A"][index]["a"] == design["B"][index]["a"]
        )
        assert identical == 0

    def test_seed_is_reproducible(self):
        first = saltelli_matrices(_unit_pair(), base_samples=16, seed=11)
        second = saltelli_matrices(_unit_pair(), base_samples=16, seed=11)
        assert first["A"] == second["A"]
        assert first["AB"] == second["AB"]

    def test_sample_count_is_clamped(self):
        design = saltelli_matrices(_unit_pair(), base_samples=2, seed=1)
        assert design["base_samples"] == MIN_BASE_SAMPLES

    def test_rejects_empty_parameters(self):
        with pytest.raises(SensitivityError):
            saltelli_matrices([], base_samples=32)

    def test_rejects_duplicate_names(self):
        duplicated = [
            build_parameter("a", "uniform", low=0.0, high=1.0),
            build_parameter("a", "uniform", low=0.0, high=1.0),
        ]
        with pytest.raises(SensitivityError):
            saltelli_matrices(duplicated, base_samples=32)

    def test_rejects_too_many_parameters(self):
        many = [
            build_parameter("p%d" % index, "uniform", low=0.0, high=1.0)
            for index in range(MAX_PARAMETERS + 1)
        ]
        with pytest.raises(SensitivityError):
            saltelli_matrices(many, base_samples=32)

    def test_rejects_raw_dicts(self):
        with pytest.raises(SensitivityError):
            saltelli_matrices([{"name": "a", "low": 0, "high": 1}], base_samples=32)


class TestEvaluateMatrix:
    def test_counts_failures_without_dropping_rows(self):
        rows = [{"a": value} for value in (1.0, 2.0, 3.0)]

        def flaky(row):
            if row["a"] == 2.0:
                raise ZeroDivisionError("boom")
            return row["a"]

        values, failures = evaluate_matrix(flaky, rows)
        assert failures == 1
        assert values == [1.0, None, 3.0]

    def test_non_finite_counts_as_failure(self):
        rows = [{"a": 1.0}]
        values, failures = evaluate_matrix(lambda row: float("nan"), rows)
        assert failures == 1
        assert values == [None]

    def test_rejects_non_callable(self):
        with pytest.raises(SensitivityError):
            evaluate_matrix("not a model", [{"a": 1.0}])


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


class TestEstimators:
    def test_zero_variance_gives_zero_indices(self):
        assert first_order_index([1.0, 1.0], [1.0, 1.0], [1.0, 1.0], 0.0) == 0.0
        assert total_effect_index([1.0, 1.0], [1.0, 1.0], 0.0) == 0.0

    def test_total_effect_is_never_negative(self):
        """Jansen's estimator is a mean of squares; it cannot go below zero.

        This is why it is used here. The alternatives produce small negative
        totals that users read as a bug rather than as estimator noise.
        """
        f_a = [1.0, 5.0, 3.0, 9.0]
        f_ab = [4.0, 2.0, 8.0, 1.0]
        assert total_effect_index(f_a, f_ab, 4.0) >= 0.0

    def test_total_effect_is_zero_when_column_is_irrelevant(self):
        f_a = [1.0, 2.0, 3.0, 4.0]
        assert total_effect_index(f_a, list(f_a), 2.0) == 0.0


# ---------------------------------------------------------------------------
# Ishigami — the reason the module exists
# ---------------------------------------------------------------------------


class TestIshigami:
    def test_analytic_indices_are_self_consistent(self):
        truth = ishigami_analytic()
        assert truth["x1"]["first_order"] == pytest.approx(0.3139, abs=1e-3)
        assert truth["x2"]["first_order"] == pytest.approx(0.4424, abs=1e-3)
        assert truth["x3"]["first_order"] == 0.0
        assert truth["x3"]["total_effect"] == pytest.approx(0.2437, abs=1e-3)
        # x2 takes part in no interaction at all.
        assert truth["x2"]["total_effect"] == pytest.approx(truth["x2"]["first_order"])

    def test_model_matches_its_definition(self):
        row = {"x1": 0.4, "x2": 1.1, "x3": 2.0}
        expected = (
            math.sin(0.4)
            + ISHIGAMI_A * math.sin(1.1) ** 2
            + ISHIGAMI_B * (2.0 ** 4) * math.sin(0.4)
        )
        assert ishigami_model(row) == pytest.approx(expected)

    def test_estimates_recover_the_analytic_indices(self):
        report = validate_against_ishigami(base_samples=4096, seed=DEFAULT_SEED)
        assert report["max_error"] < 0.05

    def test_x3_is_invisible_to_one_at_a_time_and_not_to_this(self):
        """The entire argument of this module, as a single assertion.

        x3 acting alone explains none of the variance. x3 in combination with
        x1 explains about a quarter of it. A tornado chart or a component-pin
        would report the first number and stop.
        """
        result = analyse(
            ishigami_model, ishigami_parameters(), base_samples=4096, bootstrap=40
        )
        rows = {row["name"]: row for row in result["rows"]}
        assert abs(rows["x3"]["first_order"]) < 0.05
        assert rows["x3"]["total_effect"] > 0.18
        assert rows["x3"]["interaction_dominated"] is True

    def test_verdict_is_interacting(self):
        result = analyse(
            ishigami_model, ishigami_parameters(), base_samples=2048, bootstrap=30
        )
        assert result["additivity"]["verdict"] in (
            "mildly_interacting",
            "strongly_interacting",
        )
        assert result["interaction_share"] > 0.1

    def test_x2_shows_no_interaction(self):
        result = analyse(
            ishigami_model, ishigami_parameters(), base_samples=4096, bootstrap=30
        )
        rows = {row["name"]: row for row in result["rows"]}
        assert rows["x2"]["interaction"] < 0.08


# ---------------------------------------------------------------------------
# Additive versus multiplicative
# ---------------------------------------------------------------------------


class TestAdditivityDetection:
    def test_sum_model_is_reported_as_additive(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=2048, bootstrap=30)
        assert result["interaction_share"] <= ADDITIVE_INTERACTION_CEILING
        assert result["additivity"]["verdict"] == "additive"
        assert result["sum_first_order"] == pytest.approx(1.0, abs=0.1)

    def test_product_model_carries_interaction(self):
        """a*b over a range that does not include zero still interacts.

        Not enormously — a product of two positive uniforms is close to
        additive on the log scale — but the interaction is real and must not
        come back as exactly zero.
        """
        result = analyse(_product_model, _unit_pair(), base_samples=4096, bootstrap=30)
        for row in result["rows"]:
            assert row["total_effect"] > row["first_order"] - 0.05
        assert result["sum_total_effect"] > result["sum_first_order"] - 0.05

    def test_symmetric_model_gives_symmetric_indices(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=4096, bootstrap=30)
        indices = [row["total_effect"] for row in result["rows"]]
        assert indices[0] == pytest.approx(indices[1], abs=0.08)

    def test_ignored_parameter_is_negligible(self):
        result = analyse(_ignores_b, _unit_pair(), base_samples=1024, bootstrap=30)
        rows = {row["name"]: row for row in result["rows"]}
        assert rows["b"]["total_effect"] < NEGLIGIBLE_INDEX
        assert rows["b"]["is_negligible"] is True
        assert rows["a"]["total_effect"] > 0.9

    def test_large_offset_does_not_destroy_convergence(self):
        """A constant added to an additive model must not make it look
        interacting.

        The uncentred Saltelli estimator has a variance proportional to E[f^2],
        so shifting a model's mean away from zero — which every footprint model
        does, they are all large positive numbers — slows convergence by
        orders of magnitude and shows up as first-order indices that sum to
        well under one on a provably additive model. Centring the outputs
        removes it. This test is the regression guard for that.
        """
        def offset_sum(row):
            return 50_000.0 + row["a"] + row["b"]

        result = analyse(offset_sum, _unit_pair(), base_samples=1024, bootstrap=25)
        assert result["sum_first_order"] == pytest.approx(1.0, abs=0.15)
        assert result["interaction_share"] <= ADDITIVE_INTERACTION_CEILING

    def test_offset_does_not_change_the_indices(self):
        """The decomposition is a statement about variance, so adding a
        constant to the output must leave every index alone."""
        plain = analyse(_sum_model, _unit_pair(), base_samples=1024, bootstrap=25)
        shifted = analyse(
            lambda row: _sum_model(row) + 1_000.0,
            _unit_pair(),
            base_samples=1024,
            bootstrap=25,
        )
        for left, right in zip(plain["rows"], shifted["rows"]):
            assert left["name"] == right["name"]
            assert left["total_effect"] == pytest.approx(right["total_effect"], abs=1e-9)
            assert left["first_order"] == pytest.approx(right["first_order"], abs=1e-9)

    def test_additivity_verdict_bands(self):
        assert additivity_verdict(1.0, 0.0)["verdict"] == "additive"
        assert additivity_verdict(0.9, 0.10)["verdict"] == "mildly_interacting"
        assert additivity_verdict(0.5, 0.50)["verdict"] == "strongly_interacting"


# ---------------------------------------------------------------------------
# Shared parameters — the case component pinning cannot express
# ---------------------------------------------------------------------------


class TestSharedParameter:
    def test_grid_intensity_is_ranked_as_one_input(self):
        """Grid intensity multiplies into three components.

        A component-level ranking has to split its influence across home
        electricity, EV charging and heating, and can never report it as one
        thing. Here it is one row, and it is a large one.
        """
        result = analyse(
            shared_grid_model,
            demo_parameters("shared_grid"),
            base_samples=2048,
            bootstrap=30,
        )
        rows = {row["name"]: row for row in result["rows"]}
        assert "grid_intensity" in rows
        assert rows["grid_intensity"]["total_effect"] > 0.2
        # It outranks every one of the demand terms it multiplies into. A
        # component-level ranking would have divided this influence between
        # three line items and put none of them near the top.
        for component in ("home_kwh", "ev_km", "heat_demand_kwh", "heat_pump_cop"):
            assert rows["grid_intensity"]["total_effect"] > rows[component]["total_effect"]

    def test_shared_parameter_shows_interaction_once_converged(self):
        """The joint share is real but small, so it only clears estimator
        noise at a sample size worth paying for. Asserting it at 2k would be
        asserting noise."""
        result = analyse(
            shared_grid_model,
            demo_parameters("shared_grid"),
            base_samples=8192,
            bootstrap=25,
        )
        rows = {row["name"]: row for row in result["rows"]}
        assert rows["grid_intensity"]["interaction"] > 0.0
        assert rows["grid_intensity"]["total_effect"] > rows["grid_intensity"]["first_order"]

    def test_every_declared_parameter_appears_once(self):
        parameters = demo_parameters("shared_grid")
        result = analyse(shared_grid_model, parameters, base_samples=256, bootstrap=25)
        names = [row["name"] for row in result["rows"]]
        assert sorted(names) == sorted(parameter["name"] for parameter in parameters)
        assert len(names) == len(set(names))

    def test_rows_are_sorted_by_total_effect(self):
        result = analyse(
            shared_grid_model,
            demo_parameters("shared_grid"),
            base_samples=512,
            bootstrap=25,
        )
        totals = [row["total_effect"] for row in result["rows"]]
        assert totals == sorted(totals, reverse=True)


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_constant_model_is_refused(self):
        """No variance means nothing to decompose, and saying so beats
        returning a table of zeros that looks like a result."""
        with pytest.raises(SensitivityError) as error:
            analyse(_constant, _unit_pair(), base_samples=128)
        assert "variance" in str(error.value).lower()

    def test_model_that_mostly_fails_is_refused(self):
        def mostly_broken(row):
            if row["a"] < 2.99:
                raise ValueError("nope")
            return row["a"]

        with pytest.raises(SensitivityError) as error:
            analyse(mostly_broken, _unit_pair(), base_samples=64)
        assert "finite" in str(error.value).lower()

    def test_partial_failures_are_reported_not_hidden(self):
        def occasionally_broken(row):
            if 1.5 < row["a"] < 1.55:
                return float("inf")
            return row["a"] + row["b"]

        result = analyse(occasionally_broken, _unit_pair(), base_samples=512, bootstrap=25)
        assert result["failures"] > 0
        assert result["usable_samples"] < result["base_samples"]
        codes = {problem["code"] for problem in result["diagnostics"]}
        assert "model_failures" in codes or result["failure_rate"] <= 0.02


# ---------------------------------------------------------------------------
# Bootstrap, ranking and diagnostics
# ---------------------------------------------------------------------------


class TestBootstrapAndRanking:
    def test_intervals_bracket_the_point_estimate_reasonably(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=1024, bootstrap=200)
        for row in result["rows"]:
            assert row["total_effect_low"] <= row["total_effect_high"]
            assert row["first_order_low"] <= row["first_order_high"]

    def test_bootstrap_returns_a_bound_per_parameter(self):
        f_a = [float(index) for index in range(40)]
        f_b = [float(index) * 1.1 for index in range(40)]
        f_ab = [[float(index) * 0.9 for index in range(40)]]
        bounds = bootstrap_intervals(f_a, f_b, f_ab, resamples=30, seed=1)
        assert len(bounds["total_low"]) == 1
        assert len(bounds["first_high"]) == 1

    def test_identical_parameters_are_reported_as_tied(self):
        """Two inputs the study cannot separate must not be ranked 1 and 2."""
        rows = [
            {
                "name": "a",
                "total_effect": 0.50,
                "total_effect_low": 0.40,
                "total_effect_high": 0.60,
            },
            {
                "name": "b",
                "total_effect": 0.48,
                "total_effect_low": 0.38,
                "total_effect_high": 0.58,
            },
        ]
        bands = rank_with_confidence(rows)
        assert len(bands) == 1
        assert bands[0]["separated"] is False
        assert set(bands[0]["names"]) == {"a", "b"}

    def test_clearly_separated_parameters_get_their_own_band(self):
        rows = [
            {
                "name": "a",
                "total_effect": 0.80,
                "total_effect_low": 0.75,
                "total_effect_high": 0.85,
            },
            {
                "name": "b",
                "total_effect": 0.10,
                "total_effect_low": 0.05,
                "total_effect_high": 0.15,
            },
        ]
        bands = rank_with_confidence(rows)
        assert len(bands) == 2
        assert all(band["separated"] for band in bands)

    def test_diagnose_flags_impossible_first_order_sum(self):
        problems = diagnose(
            {
                "sum_first_order": 1.9,
                "sum_total_effect": 2.0,
                "failure_rate": 0.0,
                "rows": [],
                "base_samples": 512,
            }
        )
        assert any(problem["code"] == "first_order_sum_exceeds_one" for problem in problems)

    def test_diagnose_flags_small_samples(self):
        problems = diagnose(
            {
                "sum_first_order": 1.0,
                "sum_total_effect": 1.0,
                "failure_rate": 0.0,
                "rows": [],
                "base_samples": 32,
            }
        )
        assert any(problem["code"] == "small_sample" for problem in problems)

    def test_clean_study_has_no_errors(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=2048, bootstrap=60)
        assert not [
            problem for problem in result["diagnostics"] if problem["severity"] == "error"
        ]


# ---------------------------------------------------------------------------
# Convergence and screening
# ---------------------------------------------------------------------------


class TestConvergence:
    def test_history_grows_monotonically(self):
        history = convergence(_sum_model, _unit_pair(), base_samples=512, stages=4)
        sizes = [step["samples"] for step in history["history"]]
        assert sizes == sorted(sizes)
        assert sizes[-1] <= history["usable_samples"]

    def test_well_behaved_model_converges(self):
        history = convergence(_sum_model, _unit_pair(), base_samples=2048, stages=3)
        assert history["converged"] is True

    def test_verdict_mentions_the_drift(self):
        history = convergence(_sum_model, _unit_pair(), base_samples=512, stages=3)
        assert "%.3f" % history["max_drift"] in history["verdict"]


class TestMorrisScreening:
    def test_irrelevant_parameter_is_screened_out(self):
        screening = morris_screening(_ignores_b, _unit_pair(), trajectories=24, levels=8)
        assert "b" in screening["drop"]
        assert "a" in screening["keep"]

    def test_costs_far_less_than_a_full_study(self):
        parameters = demo_parameters("pathway")
        screening = morris_screening(
            DEMO_MODELS["pathway"]["model"],
            parameters,
            trajectories=16,
            levels=8,
        )
        full_cost = 512 * (len(parameters) + 2)
        assert screening["evaluations"] < full_cost

    def test_linear_model_is_not_flagged_non_linear(self):
        screening = morris_screening(_sum_model, _unit_pair(), trajectories=30, levels=8)
        rows = {row["name"]: row for row in screening["rows"]}
        assert rows["a"]["sigma"] == pytest.approx(0.0, abs=1e-6)
        assert rows["a"]["non_linear"] is False

    def test_ishigami_x3_is_not_screened_out(self):
        """Morris is a screen, not a decomposition, but it must still keep the
        parameter whose entire contribution is an interaction."""
        screening = morris_screening(
            ishigami_model, ishigami_parameters(), trajectories=40, levels=8
        )
        assert "x3" not in screening["drop"]

    def test_trajectory_count_is_clamped(self):
        screening = morris_screening(_sum_model, _unit_pair(), trajectories=1, levels=8)
        assert screening["trajectories"] >= 4


# ---------------------------------------------------------------------------
# Reading the result
# ---------------------------------------------------------------------------


class TestReadingTheResult:
    def test_priorities_report_the_residual_spread(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=1024, bootstrap=30)
        priorities = measurement_priorities(result, limit=2)
        assert len(priorities) == 2
        for item in priorities:
            assert 0.0 <= item["residual_variance_share"] <= 1.0
            assert item["residual_stdev"] <= item["current_stdev"] + 1e-9

    def test_priorities_respect_the_limit(self):
        result = analyse(
            shared_grid_model, demo_parameters("shared_grid"), base_samples=256, bootstrap=25
        )
        assert len(measurement_priorities(result, limit=3)) == 3

    def test_notes_mention_the_top_parameter(self):
        result = analyse(_ignores_b, _unit_pair(), base_samples=1024, bootstrap=30)
        notes = " ".join(get_sensitivity_notes(result))
        assert "a" in notes
        assert "variance" in notes.lower()

    def test_notes_call_out_interaction_dominated_inputs(self):
        result = analyse(
            ishigami_model, ishigami_parameters(), base_samples=4096, bootstrap=30
        )
        notes = " ".join(get_sensitivity_notes(result))
        assert "interaction" in notes.lower()

    def test_summarise_is_one_line(self):
        result = analyse(_sum_model, _unit_pair(), base_samples=256, bootstrap=25)
        line = summarise(result)
        assert "\n" not in line
        assert "params" in line

    def test_demo_catalogue_builds(self):
        for entry in list_demo_models():
            parameters = demo_parameters(entry["key"])
            assert parameters
            assert all("distribution" in parameter for parameter in parameters)

    def test_unknown_demo_is_refused(self):
        with pytest.raises(SensitivityError):
            demo_parameters("does-not-exist")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.utils.global_sensitivity.DB_NAME", str(tmp_path / "test.db")
        )

    def _result(self):
        return analyse(_sum_model, _unit_pair(), base_samples=256, bootstrap=25, label="demo")

    def test_round_trip(self):
        result = self._result()
        study_id = save_study("user-1", result)
        assert study_id is not None

        studies = get_studies("user-1")
        assert len(studies) == 1
        assert studies[0]["label"] == "demo"
        assert studies[0]["payload"]["rows"]

    def test_studies_are_scoped_to_the_user(self):
        save_study("user-1", self._result())
        assert get_studies("user-2") == []

    def test_delete_removes_only_the_named_study(self):
        first = save_study("user-1", self._result())
        save_study("user-1", self._result())
        assert delete_study("user-1", first) is True
        assert len(get_studies("user-1")) == 1

    def test_delete_refuses_another_users_study(self):
        study_id = save_study("user-1", self._result())
        assert delete_study("user-2", study_id) is False

    def test_missing_user_saves_nothing(self):
        assert save_study(None, self._result()) is None
        assert get_studies(None) == []
        assert delete_study(None, 1) is False

    def test_empty_result_is_not_saved(self):
        assert save_study("user-1", {"rows": []}) is None
