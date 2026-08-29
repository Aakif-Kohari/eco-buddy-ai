"""Tests for the missingness and imputation engine.

The load-bearing tests are the ones about direction and about variance.

Direction: zero fill must come out *below* a pooled estimate on data with
positive activity gaps, every time. That is not a tuning artefact, it is what
zero fill means, and if the module ever fails to show it then it is not
measuring the thing it exists to measure.

Variance: mean fill must report a *smaller* standard error than multiple
imputation on the same data. It is not more precise — it has discarded the
uncertainty rather than accounted for it — and the test is written to fail if
the module ever starts flattering single imputation.

The distribution functions are checked against published critical values,
because a p-value from a home-rolled chi-square is worth exactly as much as
its arithmetic.
"""

import math

import pytest

from src.data.imputation_bias import (
    DEFAULT_SEED,
    HIGH_FMI,
    MAX_FIELDS,
    MIN_IMPUTATIONS,
    MIN_RECORDS,
    MISSINGNESS_CEILING,
    ImputationError,
    betai,
    build_field,
    chi2_sf,
    compare_periods,
    compare_strategies,
    default_fields,
    delete_analysis,
    delta_sensitivity,
    fit_regression,
    gamma_upper_regularised,
    get_analyses,
    get_imputation_notes,
    impute_centre,
    impute_constant,
    impute_locf,
    impute_regression,
    little_mcar_test,
    mar_evidence,
    mechanism_report,
    missingness_map,
    multiple_imputation,
    normalise_records,
    pool,
    record_footprint,
    sample_history,
    save_analysis,
    summarise,
    t_cdf,
    t_ppf,
)


def _fields():
    return [
        build_field("a", 1.0, "unit"),
        build_field("b", 2.0, "unit"),
    ]


def _rows(raw):
    return normalise_records(raw, _fields())


def _complete():
    return _rows(
        [
            {"a": 10.0, "b": 5.0},
            {"a": 12.0, "b": 6.0},
            {"a": 11.0, "b": 4.0},
            {"a": 13.0, "b": 7.0},
            {"a": 9.0, "b": 5.0},
            {"a": 14.0, "b": 6.0},
            {"a": 10.5, "b": 5.5},
            {"a": 12.5, "b": 6.5},
        ]
    )


def _with_gaps():
    rows = _complete()
    rows[1]["b"] = None
    rows[4]["b"] = None
    rows[6]["a"] = None
    return rows


# ---------------------------------------------------------------------------
# Distribution functions
# ---------------------------------------------------------------------------


class TestDistributionFunctions:
    @pytest.mark.parametrize(
        "statistic,degrees,expected",
        [
            (3.841, 1, 0.05),
            (5.991, 2, 0.05),
            (11.070, 5, 0.05),
            (18.307, 10, 0.05),
            (6.635, 1, 0.01),
            (23.209, 10, 0.01),
        ],
    )
    def test_chi2_matches_published_critical_values(self, statistic, degrees, expected):
        assert chi2_sf(statistic, degrees) == pytest.approx(expected, abs=5e-4)

    def test_chi2_is_one_at_zero(self):
        assert chi2_sf(0.0, 3) == 1.0

    def test_chi2_is_monotone_decreasing(self):
        values = [chi2_sf(value, 4) for value in (1.0, 3.0, 6.0, 12.0)]
        assert values == sorted(values, reverse=True)

    def test_chi2_rejects_zero_degrees(self):
        with pytest.raises(ImputationError):
            chi2_sf(1.0, 0)

    def test_gamma_rejects_negative_arguments(self):
        with pytest.raises(ImputationError):
            gamma_upper_regularised(1.0, -1.0)

    @pytest.mark.parametrize(
        "degrees,expected",
        [(1, 12.7062), (2, 4.3027), (5, 2.5706), (10, 2.2281), (30, 2.0423), (100, 1.9840)],
    )
    def test_t_quantiles_match_published_tables(self, degrees, expected):
        assert t_ppf(0.975, degrees) == pytest.approx(expected, abs=1e-3)

    def test_t_cdf_is_symmetric(self):
        for value in (0.3, 1.0, 2.5):
            assert t_cdf(value, 7) == pytest.approx(1.0 - t_cdf(-value, 7), abs=1e-10)

    def test_t_cdf_median(self):
        assert t_cdf(0.0, 5) == pytest.approx(0.5, abs=1e-10)

    def test_t_approaches_normal_at_high_df(self):
        assert t_ppf(0.975, 100000) == pytest.approx(1.95996, abs=1e-3)

    def test_t_ppf_rejects_bad_probability(self):
        with pytest.raises(ImputationError):
            t_ppf(0.0, 5)

    def test_betai_endpoints(self):
        assert betai(2.0, 3.0, 0.0) == 0.0
        assert betai(2.0, 3.0, 1.0) == 1.0


# ---------------------------------------------------------------------------
# Fields and records
# ---------------------------------------------------------------------------


class TestFieldsAndRecords:
    def test_build_field(self):
        field = build_field("kwh", 0.233, "kWh", label="Electricity")
        assert field["factor"] == 0.233
        assert field["label"] == "Electricity"

    def test_build_field_requires_a_name(self):
        with pytest.raises(ImputationError):
            build_field("  ", 1.0)

    def test_build_field_requires_a_finite_factor(self):
        with pytest.raises(ImputationError):
            build_field("x", float("nan"))

    def test_absent_key_and_none_are_the_same_thing(self):
        """A key that is absent and a key present with None are the same
        question downstream, so they must have the same representation."""
        rows = normalise_records([{"a": 1.0}, {"a": 1.0, "b": None}], _fields())
        assert rows[0]["b"] is None
        assert rows[1]["b"] is None

    def test_non_numeric_values_are_missing(self):
        rows = normalise_records([{"a": "", "b": "n/a"}], _fields())
        assert rows[0]["a"] is None
        assert rows[0]["b"] is None

    def test_floor_is_applied(self):
        rows = normalise_records([{"a": -5.0, "b": 1.0}], _fields())
        assert rows[0]["a"] == 0.0

    def test_rejects_duplicate_fields(self):
        with pytest.raises(ImputationError):
            normalise_records([{"a": 1.0}], [build_field("a"), build_field("a")])

    def test_rejects_too_many_fields(self):
        many = [build_field("f%d" % index) for index in range(MAX_FIELDS + 1)]
        with pytest.raises(ImputationError):
            normalise_records([{"f0": 1.0}], many)

    def test_rejects_empty_records(self):
        with pytest.raises(ImputationError):
            normalise_records([], _fields())

    def test_footprint_is_none_when_incomplete(self):
        assert record_footprint({"a": 1.0, "b": None}, _fields()) is None
        assert record_footprint({"a": 1.0, "b": 2.0}, _fields()) == 5.0


# ---------------------------------------------------------------------------
# Missingness map
# ---------------------------------------------------------------------------


class TestMissingnessMap:
    def test_counts_per_field(self):
        overview = missingness_map(_with_gaps(), _fields())
        rates = {entry["name"]: entry["missing"] for entry in overview["per_field"]}
        assert rates["b"] == 2
        assert rates["a"] == 1

    def test_complete_cases(self):
        overview = missingness_map(_with_gaps(), _fields())
        assert overview["complete_cases"] == 5
        assert overview["records"] == 8

    def test_patterns_are_counted(self):
        overview = missingness_map(_with_gaps(), _fields())
        patterns = {entry["pattern"]: entry["records"] for entry in overview["patterns"]}
        assert patterns["11"] == 5
        assert patterns["10"] == 2
        assert patterns["01"] == 1

    def test_co_occurrence_is_reported(self):
        overview = missingness_map(_with_gaps(), _fields())
        assert overview["co_occurrence"]["a"]["b"] == 0.0

    def test_monotone_pattern_is_detected(self):
        rows = _complete()
        rows[0]["b"] = None
        rows[1]["b"] = None
        overview = missingness_map(rows, _fields())
        assert overview["monotone"] is True

    def test_arbitrary_pattern_is_not_called_monotone(self):
        overview = missingness_map(_with_gaps(), _fields())
        assert overview["monotone"] is False

    def test_all_missing_field_is_flagged(self):
        rows = _complete()
        for row in rows:
            row["b"] = None
        overview = missingness_map(rows, _fields())
        entry = next(item for item in overview["per_field"] if item["name"] == "b")
        assert entry["all_missing"] is True

    def test_rejects_too_few_records(self):
        with pytest.raises(ImputationError):
            missingness_map(_rows([{"a": 1.0, "b": 1.0}]), _fields())


# ---------------------------------------------------------------------------
# Mechanism
# ---------------------------------------------------------------------------


class TestMechanism:
    def test_mcar_is_not_rejected_when_gaps_are_random(self):
        rows = normalise_records(
            sample_history(36, 0.2, mnar=False, seed=DEFAULT_SEED), default_fields()
        )
        result = little_mcar_test(rows, default_fields())
        assert result["verdict"] in ("mcar_not_rejected", "untestable")

    def test_mcar_test_reports_a_statistic_and_df(self):
        result = little_mcar_test(_with_gaps(), _fields())
        assert result["statistic"] >= 0.0
        assert result["degrees_of_freedom"] >= 0

    def test_single_pattern_is_untestable(self):
        """With no second pattern there is nothing to compare against, and
        saying so beats returning p = 1 as though it were a finding."""
        result = little_mcar_test(_complete(), _fields())
        assert result["verdict"] == "untestable"
        assert result["p_value"] is None

    def test_non_significant_result_is_worded_as_absence_of_evidence(self):
        rows = normalise_records(
            sample_history(30, 0.15, mnar=False, seed=7), default_fields()
        )
        result = little_mcar_test(rows, default_fields())
        if result["verdict"] == "mcar_not_rejected":
            assert "absence of evidence" in result["headline"]

    def test_mar_evidence_finds_the_association(self):
        """Construct a dataset where 'b' goes missing precisely when 'a' is
        large. That is MAR, it is recoverable, and the module must see it."""
        raw = []
        for index in range(24):
            a = float(index)
            b = None if index >= 16 else float(index) * 0.5 + 1.0
            raw.append({"a": a, "b": b})
        rows = _rows(raw)
        evidence = mar_evidence(rows, _fields(), "b")
        assert evidence["verdict"] == "mar_supported"
        assert "a" in evidence["informative_predictors"]

    def test_mar_evidence_on_complete_field(self):
        evidence = mar_evidence(_complete(), _fields(), "a")
        assert evidence["verdict"] == "complete"
        assert evidence["missing_records"] == 0

    def test_mar_refuses_a_field_missing_everywhere(self):
        rows = _complete()
        for row in rows:
            row["b"] = None
        with pytest.raises(ImputationError) as error:
            mar_evidence(rows, _fields(), "b")
        assert "every record" in str(error.value)

    def test_mar_rejects_unknown_field(self):
        with pytest.raises(ImputationError):
            mar_evidence(_with_gaps(), _fields(), "nope")

    def test_mnar_is_never_given_a_verdict(self):
        """The single most important refusal in the module.

        MNAR is unfalsifiable from observed data. A module that returned
        'MNAR: no' would be making a claim it cannot support, and users would
        act on it.
        """
        report = mechanism_report(_with_gaps(), _fields())
        assert report["mnar"]["testable"] is False
        assert "cannot be tested" in report["mnar"]["headline"]
        assert "verdict" not in report["mnar"]


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


class TestStrategies:
    def test_zero_fill_asserts_the_activity_did_not_happen(self):
        filled = impute_constant(_with_gaps(), _fields(), 0.0)
        assert filled[1]["b"] == 0.0
        assert filled[6]["a"] == 0.0

    def test_mean_fill_uses_observed_values_only(self):
        rows = _with_gaps()
        filled = impute_centre(rows, _fields(), "mean")
        observed = [row["b"] for row in rows if row["b"] is not None]
        assert filled[1]["b"] == pytest.approx(sum(observed) / len(observed))

    def test_median_fill_differs_from_mean_on_skewed_data(self):
        raw = [{"a": 1.0, "b": value} for value in (1.0, 1.0, 1.0, 1.0, 100.0)]
        raw.append({"a": 1.0, "b": None})
        rows = _rows(raw)
        mean_filled = impute_centre(rows, _fields(), "mean")
        median_filled = impute_centre(rows, _fields(), "median")
        assert mean_filled[-1]["b"] > median_filled[-1]["b"]

    def test_locf_carries_the_previous_value(self):
        rows = _with_gaps()
        filled = impute_locf(rows, _fields())
        assert filled[1]["b"] == rows[0]["b"]

    def test_locf_back_fills_a_leading_gap(self):
        rows = _complete()
        rows[0]["a"] = None
        filled = impute_locf(rows, _fields())
        assert filled[0]["a"] == rows[1]["a"]

    def test_every_strategy_refuses_a_field_missing_everywhere(self):
        rows = _complete()
        for row in rows:
            row["b"] = None
        for strategy in (impute_centre, impute_locf, impute_regression):
            with pytest.raises(ImputationError):
                strategy(rows, _fields())

    def test_regression_conditions_on_the_other_field(self):
        """With b = 2a exactly, regression imputation must recover it."""
        raw = [{"a": float(index), "b": 2.0 * index} for index in range(1, 12)]
        raw.append({"a": 20.0, "b": None})
        rows = _rows(raw)
        filled = impute_regression(rows, _fields(), noise=False)
        assert filled[-1]["b"] == pytest.approx(40.0, rel=0.02)

    def test_regression_respects_the_floor(self):
        raw = [{"a": float(index), "b": 100.0 - 10.0 * index} for index in range(1, 12)]
        raw.append({"a": 40.0, "b": None})
        rows = _rows(raw)
        filled = impute_regression(rows, _fields(), noise=False)
        assert filled[-1]["b"] >= 0.0

    def test_noise_makes_imputations_differ(self):
        """Without residual noise every imputation is identical and the
        between-imputation variance is zero — which is exactly the failure
        that makes single imputation over-confident."""
        import random

        rows = _with_gaps()
        quiet_one = impute_regression(rows, _fields(), noise=False)
        quiet_two = impute_regression(rows, _fields(), noise=False)
        assert quiet_one[1]["b"] == quiet_two[1]["b"]

        noisy_one = impute_regression(rows, _fields(), noise=True, rng=random.Random(1))
        noisy_two = impute_regression(rows, _fields(), noise=True, rng=random.Random(2))
        assert noisy_one[1]["b"] != noisy_two[1]["b"]

    def test_fit_regression_returns_none_without_enough_rows(self):
        rows = _rows([{"a": 1.0, "b": 1.0}, {"a": 2.0, "b": 2.0}])
        assert fit_regression(rows, "b", ["a"]) is None

    def test_fit_regression_recovers_a_known_slope(self):
        raw = [{"a": float(index), "b": 3.0 * index + 5.0} for index in range(12)]
        model = fit_regression(_rows(raw), "b", ["a"])
        assert model is not None
        assert model["coefficients"][1] == pytest.approx(3.0, rel=1e-4)
        assert model["coefficients"][0] == pytest.approx(5.0, abs=1e-3)
        assert model["residual_sd"] == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Rubin's rules
# ---------------------------------------------------------------------------


class TestPooling:
    def test_no_between_variance_gives_the_within_variance(self):
        pooled = pool([10.0, 10.0, 10.0], [4.0, 4.0, 4.0])
        assert pooled["estimate"] == 10.0
        assert pooled["between_variance"] == 0.0
        assert pooled["total_variance"] == pytest.approx(4.0)
        assert pooled["fraction_missing_information"] == pytest.approx(0.0)

    def test_between_variance_inflates_the_total(self):
        """This is the entire point of Rubin's rules and the entire thing
        single imputation throws away."""
        tight = pool([10.0, 10.0, 10.0, 10.0], [4.0] * 4)
        spread = pool([8.0, 10.0, 12.0, 10.0], [4.0] * 4)
        assert spread["total_variance"] > tight["total_variance"]
        assert spread["fraction_missing_information"] > 0.0

    def test_total_uses_the_one_plus_one_over_m_correction(self):
        estimates = [8.0, 10.0, 12.0]
        variances = [4.0, 4.0, 4.0]
        pooled = pool(estimates, variances)
        between = 4.0  # variance of 8, 10, 12
        assert pooled["total_variance"] == pytest.approx(4.0 + (1 + 1 / 3) * between)

    def test_fmi_is_bounded(self):
        pooled = pool([1.0, 100.0, 200.0], [0.01, 0.01, 0.01])
        assert 0.0 <= pooled["fraction_missing_information"] <= 1.0

    def test_interval_widens_with_between_variance(self):
        tight = pool([10.0, 10.0, 10.0, 10.0], [1.0] * 4)
        spread = pool([5.0, 10.0, 15.0, 10.0], [1.0] * 4)
        assert (spread["upper"] - spread["lower"]) > (tight["upper"] - tight["lower"])

    def test_rejects_a_single_imputation(self):
        with pytest.raises(ImputationError) as error:
            pool([10.0], [1.0])
        assert "between-imputation" in str(error.value)

    def test_rejects_mismatched_lengths(self):
        with pytest.raises(ImputationError):
            pool([1.0, 2.0], [1.0])


# ---------------------------------------------------------------------------
# The claims the module is making
# ---------------------------------------------------------------------------


class TestTheClaims:
    def _history(self):
        return normalise_records(
            sample_history(30, 0.25, mnar=True, seed=DEFAULT_SEED), default_fields()
        )

    def test_zero_fill_is_biased_downward(self):
        """Not a tuning artefact — it is what zero fill means. Every gap is
        read as 'none of this activity happened'."""
        comparison = compare_strategies(self._history(), default_fields(), imputations=20)
        zero = next(e for e in comparison["results"] if e["strategy"] == "zero")
        assert zero["difference_from_pooled"] < 0
        assert comparison["zero_fill_bias"] < 0

    def test_mean_fill_reports_a_smaller_error_than_it_has_earned(self):
        """Mean fill is not more precise than multiple imputation. It has
        discarded the uncertainty rather than accounted for it, and this test
        fails if the module ever starts flattering it."""
        comparison = compare_strategies(self._history(), default_fields(), imputations=30)
        mean_entry = next(e for e in comparison["results"] if e["strategy"] == "mean")
        assert mean_entry["standard_error"] < comparison["pooled"]["standard_error"]

    def test_strategy_choice_moves_the_answer_materially(self):
        comparison = compare_strategies(self._history(), default_fields(), imputations=20)
        assert comparison["spread"] > 0
        assert comparison["spread_percent"] > 1.0

    def test_all_six_strategies_are_reported(self):
        comparison = compare_strategies(self._history(), default_fields(), imputations=10)
        assert {entry["strategy"] for entry in comparison["results"]} == {
            "zero", "mean", "median", "locf", "regression", "multiple",
        }

    def test_complete_case_analysis_is_reported_as_a_different_population(self):
        comparison = compare_strategies(self._history(), default_fields(), imputations=10)
        assert comparison["complete_case_records"] < 30
        notes = " ".join(get_imputation_notes(comparison))
        assert "different population" in notes

    def test_notes_call_out_the_downward_bias(self):
        comparison = compare_strategies(self._history(), default_fields(), imputations=10)
        notes = " ".join(get_imputation_notes(comparison))
        assert "downward" in notes

    def test_summary_is_one_line(self):
        comparison = compare_strategies(self._history(), default_fields(), imputations=10)
        assert "\n" not in summarise(comparison)

    def test_complete_data_has_no_missing_information(self):
        pooled = multiple_imputation(_complete(), _fields(), imputations=10)
        assert pooled["fraction_missing_information"] == pytest.approx(0.0, abs=1e-9)
        assert pooled["between_variance"] == pytest.approx(0.0, abs=1e-9)

    def test_more_missing_data_means_more_missing_information(self):
        light = normalise_records(
            sample_history(40, 0.08, mnar=False, seed=3), default_fields()
        )
        heavy = normalise_records(
            sample_history(40, 0.40, mnar=False, seed=3), default_fields()
        )
        light_fmi = multiple_imputation(light, default_fields(), imputations=25)[
            "fraction_missing_information"
        ]
        heavy_fmi = multiple_imputation(heavy, default_fields(), imputations=25)[
            "fraction_missing_information"
        ]
        assert heavy_fmi > light_fmi


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_field_missing_everywhere_is_refused(self):
        rows = _complete()
        for row in rows:
            row["b"] = None
        with pytest.raises(ImputationError) as error:
            multiple_imputation(rows, _fields(), imputations=5)
        assert "every record" in str(error.value)

    def test_above_the_missingness_ceiling_is_refused(self):
        rows = _complete()
        for index, row in enumerate(rows):
            if index % 4:
                row["a"] = None
                row["b"] = None
        with pytest.raises(ImputationError) as error:
            multiple_imputation(rows, _fields(), imputations=5)
        assert "ceiling" in str(error.value)

    def test_imputation_count_is_clamped_upward(self):
        pooled = multiple_imputation(_with_gaps(), _fields(), imputations=1)
        assert pooled["imputations"] >= MIN_IMPUTATIONS


# ---------------------------------------------------------------------------
# MNAR sensitivity and period comparison
# ---------------------------------------------------------------------------


class TestSensitivity:
    def test_zero_delta_reproduces_the_base_estimate(self):
        rows = normalise_records(sample_history(24, 0.2, seed=5), default_fields())
        sensitivity = delta_sensitivity(
            rows, default_fields(), deltas=(0.0, 0.5), imputations=8, seed=5
        )
        assert sensitivity["curve"][0]["delta"] == 0.0
        assert sensitivity["curve"][0]["estimate"] == pytest.approx(
            sensitivity["base_estimate"], rel=1e-9
        )

    def test_positive_delta_raises_the_estimate(self):
        rows = normalise_records(sample_history(24, 0.25, seed=5), default_fields())
        sensitivity = delta_sensitivity(
            rows, default_fields(), deltas=(0.0, 0.5), imputations=8, seed=5
        )
        assert sensitivity["curve"][1]["estimate"] > sensitivity["curve"][0]["estimate"]

    def test_only_imputed_values_are_shifted(self):
        """A delta applied to observed values would be a different and much
        stronger claim than the one this analysis is making."""
        rows = normalise_records(sample_history(24, 0.05, seed=11), default_fields())
        light = delta_sensitivity(
            rows, default_fields(), deltas=(0.0, 1.0), imputations=8, seed=11
        )
        rows_heavy = normalise_records(sample_history(24, 0.4, seed=11), default_fields())
        heavy = delta_sensitivity(
            rows_heavy, default_fields(), deltas=(0.0, 1.0), imputations=8, seed=11
        )
        light_shift = abs(light["curve"][1]["shift_from_base"] / light["base_estimate"])
        heavy_shift = abs(heavy["curve"][1]["shift_from_base"] / heavy["base_estimate"])
        assert heavy_shift > light_shift

    def test_identical_periods_are_not_distinguishable(self):
        rows = normalise_records(sample_history(20, 0.15, seed=9), default_fields())
        result = compare_periods(rows, list(rows), default_fields(), imputations=10, seed=9)
        assert result["distinguishable"] is False
        assert "not distinguishable" in result["headline"]

    def test_a_large_real_change_is_distinguishable(self):
        earlier = _rows(
            [{"a": 10.0 + index * 0.1, "b": 5.0 + index * 0.05} for index in range(10)]
        )
        later = _rows(
            [{"a": 40.0 + index * 0.1, "b": 20.0 + index * 0.05} for index in range(10)]
        )
        result = compare_periods(earlier, later, _fields(), imputations=5)
        assert result["distinguishable"] is True
        assert result["direction"] == "up"

    def test_change_carries_both_periods_uncertainty(self):
        rows = normalise_records(sample_history(24, 0.2, seed=4), default_fields())
        midpoint = len(rows) // 2
        result = compare_periods(
            rows[:midpoint], rows[midpoint:], default_fields(), imputations=10, seed=4
        )
        assert result["standard_error"] >= result["earlier"]["standard_error"]
        assert result["standard_error"] >= result["later"]["standard_error"]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.data.imputation_bias.DB_NAME", str(tmp_path / "test.db")
        )

    def _comparison(self):
        return compare_strategies(_with_gaps(), _fields(), imputations=5)

    def test_round_trip(self):
        analysis_id = save_analysis("user-1", self._comparison(), "history")
        assert analysis_id is not None
        saved = get_analyses("user-1")
        assert len(saved) == 1
        assert saved[0]["label"] == "history"
        assert saved[0]["payload"]["results"]

    def test_scoped_to_the_user(self):
        save_analysis("user-1", self._comparison())
        assert get_analyses("user-2") == []

    def test_delete(self):
        analysis_id = save_analysis("user-1", self._comparison())
        assert delete_analysis("user-1", analysis_id) is True
        assert get_analyses("user-1") == []

    def test_delete_refuses_another_user(self):
        analysis_id = save_analysis("user-1", self._comparison())
        assert delete_analysis("user-2", analysis_id) is False

    def test_missing_user_is_a_no_op(self):
        assert save_analysis(None, self._comparison()) is None
        assert get_analyses(None) == []
        assert delete_analysis(None, 1) is False
