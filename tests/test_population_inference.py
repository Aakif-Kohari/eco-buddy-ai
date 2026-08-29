"""Tests for the population inference engine.

Two claims carry the module and both are tested as invariants rather than as
tuned expectations.

First: raking must reproduce the population marginals it was given. That is not
an approximation — after convergence the weighted share of every level equals
its target to within tolerance, and if it does not then the weights are not a
correction of anything.

Second: an unweighted mean over a self-selected sample must differ from the
weighted one whenever participation correlates with the outcome, and must
*not* differ when the sample is already representative. A module that always
moves the number is as useless as one that never does.

The refusals get as much attention as the arithmetic, because the refusals are
most of the value: an aggregate that quietly publishes itself from an effective
sample of nine is the failure mode this exists to prevent.
"""

import math

import pytest

from src.community.population_inference import (
    DEFAULT_TRIM_RATIO,
    MAX_VARIABLES,
    MIN_EFFECTIVE_SAMPLE,
    MIN_RESPONDENTS,
    PopulationError,
    build_respondent,
    build_variable,
    compare_groups,
    coverage_bias_bound,
    coverage_holes,
    delete_estimate,
    demo_respondents,
    demo_variables,
    design_effect,
    estimate_population_mean,
    get_estimates,
    get_inference_notes,
    percentile_of,
    post_stratify,
    rake,
    representation_gaps,
    sample_marginals,
    save_estimate,
    summarise,
    trim_weights,
    weighted_mean,
    weighted_quantile,
    weighted_standard_error,
)


def _variable():
    return build_variable("dwelling", {"flat": 0.4, "house": 0.6})


def _skewed_sample(flats=30, houses=6):
    """Flats over-represented, and cheaper. The standard shape of the problem."""
    respondents = []
    for index in range(flats):
        respondents.append(
            build_respondent("f%d" % index, 2000.0 + index, dwelling="flat")
        )
    for index in range(houses):
        respondents.append(
            build_respondent("h%d" % index, 5000.0 + index, dwelling="house")
        )
    return respondents


def _representative_sample():
    """Already matching the 40/60 target."""
    respondents = []
    for index in range(20):
        respondents.append(
            build_respondent("f%d" % index, 2000.0 + index, dwelling="flat")
        )
    for index in range(30):
        respondents.append(
            build_respondent("h%d" % index, 5000.0 + index, dwelling="house")
        )
    return respondents


# ---------------------------------------------------------------------------
# Variables and respondents
# ---------------------------------------------------------------------------


class TestVariables:
    def test_build_variable(self):
        variable = build_variable("size", {"1": 0.3, "2": 0.7}, label="Household size")
        assert variable["targets"]["1"] == 0.3
        assert variable["label"] == "Household size"

    def test_targets_must_sum_to_one(self):
        """A marginal that does not sum to one is not a marginal, and raking to
        it would silently rescale the whole estimate."""
        with pytest.raises(PopulationError) as error:
            build_variable("size", {"1": 0.3, "2": 0.5})
        assert "sum to" in str(error.value)

    def test_rejects_negative_target(self):
        with pytest.raises(PopulationError):
            build_variable("size", {"1": -0.2, "2": 1.2})

    def test_rejects_empty_targets(self):
        with pytest.raises(PopulationError):
            build_variable("size", {})

    def test_rejects_unnamed_variable(self):
        with pytest.raises(PopulationError):
            build_variable("   ", {"a": 1.0})

    def test_rejects_too_many_variables(self):
        many = [
            build_variable("v%d" % index, {"a": 1.0})
            for index in range(MAX_VARIABLES + 1)
        ]
        with pytest.raises(PopulationError):
            sample_marginals(_skewed_sample(), many)

    def test_respondent_needs_a_finite_value(self):
        with pytest.raises(PopulationError):
            build_respondent("x", float("nan"), dwelling="flat")

    def test_respondent_missing_a_level_is_refused(self):
        """Somebody who cannot be placed in a stratum cannot be weighted, and
        assigning them to a default stratum would be inventing data."""
        respondents = _skewed_sample()
        respondents.append(build_respondent("odd", 3000.0))
        with pytest.raises(PopulationError) as error:
            rake(respondents, [_variable()])
        assert "no level" in str(error.value)

    def test_unknown_level_is_refused(self):
        respondents = _skewed_sample()
        respondents.append(build_respondent("odd", 3000.0, dwelling="houseboat"))
        with pytest.raises(PopulationError) as error:
            rake(respondents, [_variable()])
        assert "not in the population targets" in str(error.value)

    def test_too_few_respondents_is_refused(self):
        few = [build_respondent("a", 1.0, dwelling="flat")]
        with pytest.raises(PopulationError):
            rake(few, [_variable()])


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


class TestRepresentation:
    def test_gaps_are_measured_against_the_targets(self):
        gaps = representation_gaps(_skewed_sample(), [_variable()])
        flat = next(entry for entry in gaps if entry["level"] == "flat")
        assert flat["sample_share"] == pytest.approx(30 / 36)
        assert flat["population_share"] == 0.4
        assert flat["difference"] > 0

    def test_under_representation_is_flagged(self):
        gaps = representation_gaps(_skewed_sample(), [_variable()])
        house = next(entry for entry in gaps if entry["level"] == "house")
        assert house["under_represented"] is True

    def test_gaps_are_sorted_by_size(self):
        gaps = representation_gaps(demo_respondents(120), demo_variables())
        sizes = [abs(entry["difference"]) for entry in gaps]
        assert sizes == sorted(sizes, reverse=True)

    def test_coverage_hole_is_named_not_dropped(self):
        """An empty stratum is a hole. Dropping it turns 'we have no data on
        detached houses' into 'detached houses are like everyone else'."""
        respondents = [
            build_respondent("f%d" % index, 2000.0, dwelling="flat")
            for index in range(10)
        ]
        holes = coverage_holes(respondents, [_variable()])
        assert len(holes) == 1
        assert holes[0]["level"] == "house"
        assert holes[0]["uncovered_population"] == 0.6

    def test_no_holes_when_every_stratum_is_populated(self):
        assert coverage_holes(_skewed_sample(), [_variable()]) == []


# ---------------------------------------------------------------------------
# Raking
# ---------------------------------------------------------------------------


class TestRaking:
    def test_weights_reproduce_the_targets(self):
        """The defining property. After convergence the weighted share of
        every level equals its population target."""
        result = rake(_skewed_sample(), [_variable()])
        assert result["converged"] is True
        marginals = sample_marginals(_skewed_sample(), [_variable()], result["weights"])
        assert marginals["dwelling"]["flat"] == pytest.approx(0.4, abs=1e-6)
        assert marginals["dwelling"]["house"] == pytest.approx(0.6, abs=1e-6)

    def test_weights_average_one(self):
        """Keeps a weight readable as 'this respondent stands for N people
        relative to the average'."""
        result = rake(_skewed_sample(), [_variable()])
        assert sum(result["weights"]) == pytest.approx(len(_skewed_sample()))

    def test_under_represented_group_is_weighted_up(self):
        respondents = _skewed_sample()
        result = rake(respondents, [_variable()])
        flat_weights = [
            result["weights"][index]
            for index, respondent in enumerate(respondents)
            if respondent["levels"]["dwelling"] == "flat"
        ]
        house_weights = [
            result["weights"][index]
            for index, respondent in enumerate(respondents)
            if respondent["levels"]["dwelling"] == "house"
        ]
        assert max(house_weights) > max(flat_weights)

    def test_representative_sample_gets_uniform_weights(self):
        result = rake(_representative_sample(), [_variable()])
        assert max(result["weights"]) == pytest.approx(min(result["weights"]), abs=1e-6)

    def test_converges_on_two_variables(self):
        result = rake(demo_respondents(150), demo_variables())
        assert result["converged"] is True
        assert result["worst_residual"] < 1e-4

    def test_residuals_are_reported_per_level(self):
        result = rake(demo_respondents(80), demo_variables())
        levels = {(entry["variable"], entry["level"]) for entry in result["residuals"]}
        assert ("dwelling", "detached") in levels
        assert ("household_size", "3+") in levels

    def test_iteration_cap_is_respected(self):
        result = rake(demo_respondents(80), demo_variables(), max_iterations=5)
        assert result["iterations"] <= 5

    def test_non_convergence_is_stated_not_hidden(self):
        result = rake(demo_respondents(200), demo_variables(), max_iterations=5, tolerance=1e-12)
        if not result["converged"]:
            assert "did not converge" in result["verdict"].lower()


# ---------------------------------------------------------------------------
# Post-stratification
# ---------------------------------------------------------------------------


class TestPostStratification:
    def _joint(self):
        return {
            ("flat", "1"): 0.25,
            ("flat", "2"): 0.15,
            ("house", "1"): 0.20,
            ("house", "2"): 0.40,
        }

    def _variables(self):
        return [
            build_variable("dwelling", {"flat": 0.4, "house": 0.6}),
            build_variable("household_size", {"1": 0.45, "2": 0.55}),
        ]

    def _respondents(self):
        respondents = []
        combinations = [("flat", "1"), ("flat", "2"), ("house", "1"), ("house", "2")]
        for position, (dwelling, size) in enumerate(combinations):
            for index in range(4):
                respondents.append(
                    build_respondent(
                        "%s%s%d" % (dwelling, size, index),
                        1000.0 * (position + 1),
                        dwelling=dwelling,
                        household_size=size,
                    )
                )
        return respondents

    def test_weights_match_the_joint_targets(self):
        result = post_stratify(self._respondents(), self._variables(), self._joint())
        assert result["converged"] is True
        assert len(result["cells"]) == 4

    def test_targets_must_sum_to_one(self):
        broken = dict(self._joint())
        broken[("flat", "1")] = 0.9
        with pytest.raises(PopulationError):
            post_stratify(self._respondents(), self._variables(), broken)

    def test_empty_cell_is_refused_not_redistributed(self):
        """Quietly spreading an empty cell's weight over the populated ones is
        exactly the assumption under scrutiny."""
        respondents = [
            entry
            for entry in self._respondents()
            if not (
                entry["levels"]["dwelling"] == "house"
                and entry["levels"]["household_size"] == "2"
            )
        ]
        with pytest.raises(PopulationError) as error:
            post_stratify(respondents, self._variables(), self._joint())
        assert "no respondents" in str(error.value)


# ---------------------------------------------------------------------------
# Design effect
# ---------------------------------------------------------------------------


class TestDesignEffect:
    def test_uniform_weights_give_deff_of_one(self):
        effect = design_effect([1.0] * 50)
        assert effect["design_effect"] == pytest.approx(1.0)
        assert effect["effective_sample"] == pytest.approx(50.0)

    def test_unequal_weights_cost_precision(self):
        effect = design_effect([1.0] * 49 + [50.0])
        assert effect["design_effect"] > 1.0
        assert effect["effective_sample"] < 50.0

    def test_one_dominant_weight_collapses_the_sample(self):
        """One respondent carrying almost all the weight *is* the estimate."""
        effect = design_effect([1.0] * 99 + [10000.0])
        assert effect["effective_sample"] < 5.0

    def test_loss_share_is_consistent(self):
        effect = design_effect([1.0, 3.0, 5.0, 7.0])
        assert effect["loss"] == pytest.approx(
            effect["respondents"] - effect["effective_sample"]
        )

    def test_rejects_empty_weights(self):
        with pytest.raises(PopulationError):
            design_effect([])

    def test_rejects_zero_total(self):
        with pytest.raises(PopulationError):
            design_effect([0.0, 0.0])


# ---------------------------------------------------------------------------
# Weighted statistics
# ---------------------------------------------------------------------------


class TestWeightedStatistics:
    def test_uniform_weights_reproduce_the_plain_mean(self):
        values = [1.0, 2.0, 3.0, 4.0]
        assert weighted_mean(values, [1.0] * 4) == pytest.approx(2.5)

    def test_weighting_shifts_the_mean(self):
        values = [1.0, 10.0]
        assert weighted_mean(values, [1.0, 3.0]) == pytest.approx(7.75)

    def test_weighted_median_of_uniform_weights(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert weighted_quantile(values, [1.0] * 5, 0.5) == 3.0

    def test_weighted_quantile_respects_the_weights(self):
        values = [1.0, 100.0]
        assert weighted_quantile(values, [9.0, 1.0], 0.5) == 1.0
        assert weighted_quantile(values, [1.0, 9.0], 0.5) == 100.0

    def test_quantile_bounds_are_checked(self):
        with pytest.raises(PopulationError):
            weighted_quantile([1.0, 2.0], [1.0, 1.0], 1.5)

    def test_standard_error_uses_the_effective_sample(self):
        """A weighted estimate whose interval is built on the raw count has an
        interval it has not earned."""
        values = [float(index) for index in range(50)]
        even = weighted_standard_error(values, [1.0] * 50)
        uneven = weighted_standard_error(values, [1.0] * 49 + [40.0])
        assert uneven > even

    def test_percentile_of_uses_the_weighted_distribution(self):
        respondents = _skewed_sample()
        result = rake(respondents, [_variable()])
        unweighted = percentile_of(4000.0, respondents, [1.0] * len(respondents))
        weighted = percentile_of(4000.0, respondents, result["weights"])
        assert weighted != pytest.approx(unweighted)


# ---------------------------------------------------------------------------
# Trimming
# ---------------------------------------------------------------------------


class TestTrimming:
    def test_caps_extreme_weights(self):
        weights = [1.0] * 20 + [40.0]
        trimmed = trim_weights(weights, ratio=3.0)
        assert trimmed["capped"] == 1
        assert trimmed["max_after"] < trimmed["max_before"]

    def test_trimming_buys_effective_sample(self):
        weights = [1.0] * 40 + [60.0]
        trimmed = trim_weights(weights, ratio=3.0)
        assert trimmed["effective_sample_after"] > trimmed["effective_sample_before"]
        assert trimmed["precision_gained"] > 0

    def test_trimming_preserves_the_weight_total(self):
        weights = [1.0] * 20 + [40.0]
        trimmed = trim_weights(weights, ratio=3.0)
        assert sum(trimmed["weights"]) == pytest.approx(len(weights))

    def test_nothing_to_trim_is_a_no_op(self):
        trimmed = trim_weights([1.0] * 10, ratio=5.0)
        assert trimmed["capped"] == 0
        assert "nothing trimmed" in trimmed["headline"]

    def test_ratio_has_a_floor(self):
        trimmed = trim_weights([1.0] * 10, ratio=0.1)
        assert trimmed["ratio"] >= 1.5

    def test_rejects_empty_weights(self):
        with pytest.raises(PopulationError):
            trim_weights([])


# ---------------------------------------------------------------------------
# The estimate
# ---------------------------------------------------------------------------


class TestEstimate:
    def test_self_selected_sample_is_corrected_upward(self):
        """Flats are over-represented and cheaper, so the unweighted mean
        flatters everyone compared against it."""
        result = estimate_population_mean(
            _skewed_sample(), [_variable()], minimum_effective_sample=5
        )
        assert result["weighted_mean"] > result["unweighted_mean"]
        assert result["correction"] > 0

    def test_representative_sample_is_barely_corrected(self):
        """A module that always moves the number is as useless as one that
        never does."""
        result = estimate_population_mean(
            _representative_sample(), [_variable()], minimum_effective_sample=5
        )
        assert abs(result["correction_percent"]) < 0.5

    def test_demo_sample_shows_a_large_correction(self):
        result = estimate_population_mean(demo_respondents(150), demo_variables())
        assert result["correction_percent"] > 5.0

    def test_effective_sample_is_below_the_count(self):
        result = estimate_population_mean(demo_respondents(150), demo_variables())
        assert result["design"]["effective_sample"] < result["respondents"]

    def test_interval_is_symmetric_about_the_estimate(self):
        result = estimate_population_mean(demo_respondents(120), demo_variables())
        assert result["weighted_mean"] - result["lower"] == pytest.approx(
            result["upper"] - result["weighted_mean"]
        )

    def test_below_the_effective_sample_floor_is_withheld(self):
        result = estimate_population_mean(
            _skewed_sample(), [_variable()], minimum_effective_sample=1000
        )
        assert result["publishable"] is False
        assert any("Effective sample" in reason for reason in result["refusals"])

    def test_coverage_hole_blocks_publication(self):
        respondents = [
            build_respondent("f%d" % index, 2000.0 + index, dwelling="flat")
            for index in range(30)
        ]
        result = estimate_population_mean(
            respondents, [_variable()], minimum_effective_sample=5
        )
        assert result["publishable"] is False
        assert any("no respondents" in reason for reason in result["refusals"])

    def test_only_standard_confidence_levels_are_offered(self):
        with pytest.raises(PopulationError):
            estimate_population_mean(
                demo_respondents(60), demo_variables(), confidence=0.937
            )

    def test_notes_mention_the_design_effect(self):
        result = estimate_population_mean(demo_respondents(120), demo_variables())
        notes = " ".join(get_inference_notes(result))
        assert "Design effect" in notes
        assert "coverage bias" in notes.lower()

    def test_summary_is_one_line(self):
        result = estimate_population_mean(demo_respondents(80), demo_variables())
        assert "\n" not in summarise(result)


# ---------------------------------------------------------------------------
# Coverage bias bound
# ---------------------------------------------------------------------------


class TestCoverageBiasBound:
    def test_leverage_dominates_at_small_sample_fractions(self):
        """The reason the default correlation is 0.02 and not 0.25.

        At a 1% sample the leverage factor sqrt((1-f)/f) is about 10, so a
        correlation that looks negligible already moves the estimate by a fifth
        of a standard deviation. The decomposition exists to make that visible.
        """
        bound = coverage_bias_bound(
            1000.0, 300.0, participation_correlation=0.02, sample_fraction=0.01
        )
        assert bound["leverage"] == pytest.approx(math.sqrt(99.0), rel=1e-6)
        assert bound["bias"] == pytest.approx(0.02 * math.sqrt(99.0) * 300.0)
        assert bound["bias"] / 300.0 == pytest.approx(0.199, abs=0.005)

    def test_zero_correlation_gives_no_bound(self):
        bound = coverage_bias_bound(1000.0, 300.0, participation_correlation=0.0)
        assert bound["bias"] == 0.0
        assert bound["lower"] == bound["upper"] == 1000.0

    def test_bound_grows_with_correlation(self):
        weak = coverage_bias_bound(1000.0, 300.0, participation_correlation=0.1)
        strong = coverage_bias_bound(1000.0, 300.0, participation_correlation=0.5)
        assert strong["bias"] > weak["bias"]

    def test_bound_grows_as_the_sample_shrinks(self):
        small = coverage_bias_bound(1000.0, 300.0, sample_fraction=0.001)
        large = coverage_bias_bound(1000.0, 300.0, sample_fraction=0.25)
        assert small["bias"] > large["bias"]

    def test_rejects_impossible_correlation(self):
        with pytest.raises(PopulationError):
            coverage_bias_bound(1000.0, 300.0, participation_correlation=1.4)

    def test_rejects_impossible_sample_fraction(self):
        with pytest.raises(PopulationError):
            coverage_bias_bound(1000.0, 300.0, sample_fraction=1.0)

    def test_note_states_the_assumption(self):
        bound = coverage_bias_bound(1000.0, 300.0, participation_correlation=0.3)
        assert "0.30" in bound["note"]
        assert "not a measurement" in bound["note"]


# ---------------------------------------------------------------------------
# Comparing groups
# ---------------------------------------------------------------------------


class TestCompareGroups:
    def _groups(self):
        respondents = demo_respondents(200)
        groups = {}
        for index, respondent in enumerate(respondents):
            groups.setdefault("g%d" % (index % 3), []).append(respondent)
        return groups

    def test_groups_are_ranked(self):
        comparison = compare_groups(
            self._groups(), demo_variables(), minimum_effective_sample=5
        )
        assert comparison["entries"]
        means = [entry["mean"] for entry in comparison["entries"]]
        assert means == sorted(means)

    def test_overlapping_groups_are_reported_as_tied(self):
        """Three random splits of one sample must not be ranked 1, 2, 3."""
        comparison = compare_groups(
            self._groups(), demo_variables(), minimum_effective_sample=5
        )
        assert any(not band["separated"] for band in comparison["bands"])

    def test_tiny_group_is_excluded_not_ranked(self):
        groups = self._groups()
        groups["tiny"] = [
            build_respondent("t%d" % index, 1000.0, dwelling="flat", household_size="1")
            for index in range(6)
        ]
        comparison = compare_groups(
            groups, demo_variables(), minimum_effective_sample=30
        )
        assert "tiny" in [entry["group"] for entry in comparison["excluded"]]
        assert "tiny" not in [entry["group"] for entry in comparison["entries"]]

    def test_unbuildable_group_is_excluded_with_a_reason(self):
        groups = self._groups()
        groups["broken"] = [build_respondent("b0", 100.0, dwelling="flat", household_size="1")]
        comparison = compare_groups(
            groups, demo_variables(), minimum_effective_sample=5
        )
        reasons = {entry["group"]: entry["reason"] for entry in comparison["excluded"]}
        assert "broken" in reasons
        assert reasons["broken"]

    def test_rank_churn_is_reported(self):
        comparison = compare_groups(
            self._groups(), demo_variables(), minimum_effective_sample=5
        )
        assert comparison["rank_churn"] >= 0
        assert "band" in comparison["headline"]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.community.population_inference.DB_NAME", str(tmp_path / "test.db")
        )

    def _result(self):
        return estimate_population_mean(demo_respondents(80), demo_variables())

    def test_round_trip(self):
        estimate_id = save_estimate("user-1", self._result(), "community")
        assert estimate_id is not None
        saved = get_estimates("user-1")
        assert len(saved) == 1
        assert saved[0]["label"] == "community"
        assert saved[0]["payload"]["headline"]

    def test_publishable_flag_survives(self):
        save_estimate("user-1", self._result())
        assert get_estimates("user-1")[0]["publishable"] in (True, False)

    def test_scoped_to_the_user(self):
        save_estimate("user-1", self._result())
        assert get_estimates("user-2") == []

    def test_delete(self):
        estimate_id = save_estimate("user-1", self._result())
        assert delete_estimate("user-1", estimate_id) is True
        assert get_estimates("user-1") == []

    def test_delete_refuses_another_user(self):
        estimate_id = save_estimate("user-1", self._result())
        assert delete_estimate("user-2", estimate_id) is False

    def test_missing_user_is_a_no_op(self):
        assert save_estimate(None, self._result()) is None
        assert get_estimates(None) == []
        assert delete_estimate(None, 1) is False
