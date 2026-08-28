"""When to replace something, which is not the question payback answers.

carbon_payback.py assumes the only alternative to acting now is never acting.
A user with a working boiler is choosing between now, next year, the year
after, and waiting for it to fail — and under a decarbonising grid those have
genuinely different answers, sometimes in the opposite order to what a payback
figure implies.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.carbon.replacement_timing import (
    FUELS,
    ReplacementTimingError,
    break_even_grid_intensity,
    build_grid,
    build_unit,
    compare_objectives,
    delete_plan,
    evaluate,
    failure_distribution,
    get_plans,
    get_timing_insights,
    grid_intensity,
    grid_sensitivity,
    horizon_sensitivity,
    list_fuels,
    regret,
    save_plan,
    scrappage_charge,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⏱️ Replacement Timing</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Payback answers *whether* to buy. This answers *when* to replace — a "
    "different question, because the alternative to acting now is not never "
    "acting, it is acting next year."
)

with st.expander("Why the answer moves, and in which direction"):
    st.markdown(
        """
**Electrification gets better while you wait.** Swap a gas boiler for a heat
pump and the saving grows every year the grid cleans up, because the thing you
are switching *to* keeps improving. On a dirty grid a heat pump can be worse
than the boiler today and clearly better in five years.

**Efficiency gets worse while you wait.** Swap an electric appliance for a more
efficient electric one and the emissions you are avoiding are themselves
shrinking. The longer you wait, the less the upgrade is worth.

Those have opposite signs. A payback ratio has no time axis and cannot
represent either.

**Early replacement scraps carbon that is already paid for.** Retiring a
working appliance throws away the unused share of an emission that has already
happened. Nothing else in this app charges that to the decision.

**Failure is stochastic and the decision is not.** An appliance replaced on
failure incurs no scrappage penalty at all, so waiting for failure is often
better than it sounds. The plan assumes the incumbent survives to the chosen
year; the survival probability is shown next to it rather than folded in,
because mixing the two produces a curve that is neither a plan nor an
expectation.

**Carbon and cost are not blended.** They frequently disagree, and the
disagreement is the useful part. A shadow price is available and is labelled
with its value.

**The horizon is a boundary and boundaries leak.** The new unit's embodied
carbon is charged only for the share of its life used inside the horizon, so a
later replacement carries a smaller charge. Part of any "wait" answer is
therefore about where the boundary was drawn. The last tab moves the boundary
and shows you whether the answer survives.
        """
    )

PRESETS = {
    "Gas boiler → heat pump, dirty grid": {
        "incumbent": ("Gas boiler", "natural_gas", 18_000.0, 20.0, 900.0, 8.0),
        "replacement": ("Heat pump", "electricity", 6_000.0, 20.0, 2_400.0, 9_000.0),
        "grid": (0.71, 0.06),
        "horizon": 25,
        "note": (
            "The case the module exists for. On a 0.71 kg/kWh grid the heat "
            "pump is dirtier than the boiler today. With no decarbonisation "
            "the answer is never; at six percent a year it is a date."
        ),
    },
    "Gas boiler → heat pump, clean grid": {
        "incumbent": ("Gas boiler", "natural_gas", 18_000.0, 20.0, 900.0, 8.0),
        "replacement": ("Heat pump", "electricity", 6_000.0, 20.0, 2_400.0, 9_000.0),
        "grid": (0.25, 0.04),
        "horizon": 25,
        "note": (
            "Same appliances, cleaner starting grid. The saving is immediate "
            "and large, and waiting only forfeits it."
        ),
    },
    "Working fridge → marginally better fridge": {
        "incumbent": ("Old fridge", "electricity", 300.0, 15.0, 320.0, 3.0),
        "replacement": ("New fridge", "electricity", 200.0, 15.0, 420.0, 750.0),
        "grid": (0.30, 0.05),
        "horizon": 20,
        "note": (
            "The case every other tool in this app gets wrong. A positive "
            "payback, a real efficiency gain, and replacing is still the "
            "worse option once the scrapped life and the falling grid are "
            "counted."
        ),
    },
    "Oil boiler → heat pump": {
        "incumbent": ("Oil boiler", "heating_oil", 20_000.0, 20.0, 950.0, 14.0),
        "replacement": ("Heat pump", "electricity", 6_500.0, 20.0, 2_400.0, 9_500.0),
        "grid": (0.40, 0.04),
        "horizon": 25,
        "note": (
            "The dirtiest incumbent here and one already most of the way "
            "through its life, so there is very little paid-for life left to "
            "scrap."
        ),
    },
}


tab_plan, tab_curve, tab_failure, tab_robustness = st.tabs([
    "The decision",
    "The whole curve",
    "Failure and scrappage",
    "Does the answer survive?",
])


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------

with tab_plan:
    preset_name = st.selectbox("Worked example", list(PRESETS))
    preset = PRESETS[preset_name]
    st.caption(preset["note"])

    left, right = st.columns(2)
    with left:
        st.markdown("**What you have**")
        incumbent_label = st.text_input("Label", value=preset["incumbent"][0])
        incumbent_fuel = st.selectbox(
            "Fuel", sorted(FUELS),
            index=sorted(FUELS).index(preset["incumbent"][1]),
            format_func=lambda key: FUELS[key]["label"],
        )
        incumbent_energy = st.number_input(
            "Annual energy (kWh)", min_value=0.0,
            value=preset["incumbent"][2], step=100.0,
        )
        incumbent_life = st.number_input(
            "Rated life (years)", min_value=1.0,
            value=preset["incumbent"][3], step=1.0,
        )
        incumbent_embodied = st.number_input(
            "Embodied carbon (kg CO2e)", min_value=0.0,
            value=preset["incumbent"][4], step=50.0,
        )
        incumbent_age = st.number_input(
            "Current age (years)", min_value=0.0,
            value=preset["incumbent"][5], step=1.0,
        )
    with right:
        st.markdown("**What you would buy**")
        replacement_label = st.text_input(
            "Label ", value=preset["replacement"][0]
        )
        replacement_fuel = st.selectbox(
            "Fuel ", sorted(FUELS),
            index=sorted(FUELS).index(preset["replacement"][1]),
            format_func=lambda key: FUELS[key]["label"],
        )
        replacement_energy = st.number_input(
            "Annual energy (kWh) ", min_value=0.0,
            value=preset["replacement"][2], step=100.0,
        )
        replacement_life = st.number_input(
            "Rated life (years) ", min_value=1.0,
            value=preset["replacement"][3], step=1.0,
        )
        replacement_embodied = st.number_input(
            "Embodied carbon (kg CO2e) ", min_value=0.0,
            value=preset["replacement"][4], step=50.0,
        )
        replacement_capital = st.number_input(
            "Capital cost", min_value=0.0,
            value=preset["replacement"][5], step=250.0,
        )

    st.markdown("**The grid you will be running on**")
    first, second, third = st.columns(3)
    with first:
        grid_start = st.number_input(
            "Grid today (kg CO2e/kWh)", min_value=0.01,
            value=preset["grid"][0], step=0.01, format="%.3f",
        )
    with second:
        grid_decline = st.slider(
            "Annual decline", 0.0, 0.15, preset["grid"][1], 0.005,
            format="%.3f",
        )
    with third:
        horizon = st.slider(
            "Horizon (years)", 15, 50, preset["horizon"]
        )

    first, second = st.columns(2)
    with first:
        discount_rate = st.slider("Discount rate (cost only)", 0.0, 0.10, 0.03, 0.005)
    with second:
        capital_decline = st.slider(
            "Annual fall in capital cost", 0.0, 0.10, 0.0, 0.005,
            help="Technology getting cheaper is another reason waiting can pay.",
        )

    result = None
    try:
        incumbent = build_unit(
            incumbent_label, incumbent_fuel, incumbent_energy,
            incumbent_life, incumbent_embodied, age_years=incumbent_age,
        )
        replacement = build_unit(
            replacement_label, replacement_fuel, replacement_energy,
            replacement_life, replacement_embodied,
            capital_cost=replacement_capital,
        )
        grid = build_grid(grid_start, grid_decline)
        result = evaluate(
            incumbent, replacement, grid, horizon,
            discount_rate=discount_rate, capital_decline=capital_decline,
        )
    except ReplacementTimingError as error:
        st.error(str(error))

    if result:
        first, second, third, fourth = st.columns(4)
        first.metric(
            "Lowest carbon",
            "now" if result["optimal_carbon_year"] == 0
            else ("never" if result["optimal_carbon_year"] >= horizon
                  else "in %d years" % result["optimal_carbon_year"]),
        )
        second.metric(
            "Lowest cost",
            "now" if result["optimal_cost_year"] == 0
            else ("never" if result["optimal_cost_year"] >= horizon
                  else "in %d years" % result["optimal_cost_year"]),
        )
        third.metric(
            "Cost of acting now",
            "%.0f kg CO2e" % result["acting_now_costs"],
        )
        fourth.metric(
            "Survives to then",
            "%.0f%%" % (
                result["paths"][result["optimal_carbon_year"]][
                    "survival_probability"
                ] * 100.0
            ),
        )

        for insight in get_timing_insights(result):
            if insight["level"] == "warning":
                st.warning("**%s**\n\n%s" % (insight["title"], insight["body"]))
            else:
                st.info("**%s**\n\n%s" % (insight["title"], insight["body"]))

        comparison = compare_objectives(result)
        st.markdown("#### Carbon and cost, unblended")
        st.dataframe(
            pd.DataFrame([
                {
                    "Optimising": "Carbon",
                    "Replace in year": comparison["carbon_optimum"]["year"],
                    "Total kg CO2e": round(comparison["carbon_optimum"]["carbon"]),
                    "Total cost": round(comparison["carbon_optimum"]["cost"]),
                },
                {
                    "Optimising": "Cost",
                    "Replace in year": comparison["cost_optimum"]["year"],
                    "Total kg CO2e": round(comparison["cost_optimum"]["carbon"]),
                    "Total cost": round(comparison["cost_optimum"]["cost"]),
                },
            ]),
            use_container_width=True,
            hide_index=True,
        )
        if comparison["agree"]:
            st.success(
                "Both objectives point at the same year, which makes this an "
                "unusually easy decision."
            )
        else:
            st.warning(
                "Following the cost optimum costs **%.0f kg CO2e**; following "
                "the carbon optimum costs **%.0f** in money. No calculation "
                "settles which matters more."
                % (
                    comparison["carbon_penalty_of_cost_choice"],
                    comparison["cost_penalty_of_carbon_choice"],
                )
            )

        st.markdown("#### Regret, which is more actionable than the optimum")
        penalties = regret(result)
        first, second, third = st.columns(3)
        first.metric(
            "A year early",
            "%.0f kg" % (penalties["one_year_early"] or 0.0),
        )
        second.metric(
            "A year late",
            "%.0f kg" % (penalties["one_year_late"] or 0.0),
        )
        third.metric(
            "Years within 2%", "%d" % len(penalties["years_within_two_percent"])
        )
        st.caption(penalties["note"])

        if st.button("Save this analysis"):
            try:
                save_plan(user_id, result)
                st.success("Saved.")
            except ReplacementTimingError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# The curve
# ---------------------------------------------------------------------------

with tab_curve:
    st.subheader("Every replacement year, not just now against never")
    st.caption(
        "The curve is not monotonic. Waiting improves the electrification "
        "case and worsens the efficiency case, so the optimum is frequently "
        "in the middle — which is exactly what a pairwise comparison misses."
    )

    if not result:
        st.info("Set up a decision on the first tab.")
    else:
        frame = pd.DataFrame([{
            "year": row["replacement_year"],
            "carbon": row["total_carbon"],
            "cost": row["total_cost"],
            "operating": row["operating_carbon"],
            "embodied": row["embodied_carbon"],
            "scrappage": row["scrappage_carbon"],
            "survival": row["survival_probability"],
        } for row in result["paths"]])

        figure = go.Figure()
        figure.add_scatter(
            x=frame["year"], y=frame["carbon"],
            mode="lines+markers", name="Total carbon",
        )
        figure.add_vline(
            x=result["optimal_carbon_year"], line_dash="dash",
            annotation_text="carbon optimum",
        )
        figure.add_vline(
            x=result["optimal_cost_year"], line_dash="dot",
            annotation_text="cost optimum",
        )
        figure.update_layout(
            xaxis_title="Replace in year",
            yaxis_title="Total kg CO2e over the horizon",
            height=400,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)

        st.markdown("#### What makes up each total")
        stacked = go.Figure()
        stacked.add_bar(x=frame["year"], y=frame["operating"], name="Operating")
        stacked.add_bar(x=frame["year"], y=frame["embodied"], name="New unit embodied")
        stacked.add_bar(x=frame["year"], y=frame["scrappage"], name="Scrapped life")
        stacked.update_layout(
            barmode="stack",
            xaxis_title="Replace in year",
            yaxis_title="kg CO2e",
            height=400,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(stacked, use_container_width=True)
        st.caption(
            "The scrappage band shrinks as you wait and vanishes once the "
            "incumbent passes its rated life. That is a real reason to wait, "
            "and it is the term no other module here accounts for."
        )

        st.markdown("#### The grid you are betting on")
        grid_frame = pd.DataFrame([{
            "year": year,
            "intensity": grid_intensity(result["grid"], year),
        } for year in range(result["horizon_years"] + 1)])
        grid_figure = go.Figure()
        grid_figure.add_scatter(
            x=grid_frame["year"], y=grid_frame["intensity"], mode="lines"
        )
        grid_figure.update_layout(
            xaxis_title="Year",
            yaxis_title="kg CO2e per kWh",
            height=300,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(grid_figure, use_container_width=True)

        st.dataframe(
            frame.assign(
                carbon=frame["carbon"].round(0),
                cost=frame["cost"].round(0),
                survival=(frame["survival"] * 100).round(0),
            )[["year", "carbon", "cost", "survival"]].rename(columns={
                "year": "Replace in year",
                "carbon": "Total kg CO2e",
                "cost": "Total cost",
                "survival": "Survives to then (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------------------------
# Failure and scrappage
# ---------------------------------------------------------------------------

with tab_failure:
    st.subheader("Waiting for it to break")
    st.caption(
        "A forced replacement scraps no unused life, which is why waiting for "
        "failure is often better than it sounds. Failure is modelled with a "
        "Weibull hazard conditioned on the incumbent's current age."
    )

    if not result:
        st.info("Set up a decision on the first tab.")
    else:
        failure = result["failure"]
        first, second, third = st.columns(3)
        first.metric(
            "Expected failure",
            "year %.1f" % failure["expected_year"]
            if failure["expected_year"] else "beyond horizon",
        )
        second.metric(
            "Fails within horizon",
            "%.0f%%" % (failure["probability_fails_within_horizon"] * 100.0),
        )
        third.metric(
            "Survives the horizon",
            "%.0f%%" % (failure["probability_survives_horizon"] * 100.0),
        )

        distribution = failure_distribution(
            result["incumbent"], result["horizon_years"]
        )
        hazard_frame = pd.DataFrame(distribution)
        hazard = go.Figure()
        hazard.add_bar(
            x=hazard_frame["year"], y=hazard_frame["fails_this_year"],
            name="Fails this year",
        )
        hazard.add_scatter(
            x=hazard_frame["year"], y=hazard_frame["survives_to_start"],
            name="Still working", yaxis="y2", mode="lines",
        )
        hazard.update_layout(
            xaxis_title="Year",
            yaxis_title="Probability of failing that year",
            yaxis2=dict(
                title="Still working", overlaying="y", side="right", range=[0, 1]
            ),
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(hazard, use_container_width=True)

        if result["replace_on_failure"]:
            on_failure = result["replace_on_failure"]
            difference = on_failure["total_carbon"] - result["optimal_carbon"]
            st.metric(
                "Replacing on failure, against the best plan",
                "%+.0f kg CO2e" % difference,
            )
            if difference < 50:
                st.success(
                    "Waiting for failure is within 50 kg of the best plan. "
                    "Planning the replacement buys you almost nothing here, "
                    "and it does cost you the certainty of a working "
                    "appliance."
                )

        st.divider()
        st.markdown("#### Paid-for carbon thrown away by acting early")
        scrappage_frame = pd.DataFrame([{
            "year": year,
            "scrapped": scrappage_charge(result["incumbent"], year),
        } for year in range(result["horizon_years"] + 1)])
        scrap_figure = go.Figure()
        scrap_figure.add_scatter(
            x=scrappage_frame["year"], y=scrappage_frame["scrapped"],
            mode="lines", fill="tozeroy",
        )
        scrap_figure.update_layout(
            xaxis_title="Replace in year",
            yaxis_title="kg CO2e of unused life discarded",
            height=320,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(scrap_figure, use_container_width=True)
        st.write(
            "The incumbent has **%.1f years** of its rated life left. Acting "
            "today throws away **%.0f kg CO2e** that has already been emitted."
            % (
                result["incumbent"]["remaining_life_years"],
                scrappage_charge(result["incumbent"], 0),
            )
        )


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

with tab_robustness:
    st.subheader("Does the answer survive its own assumptions?")

    if not result:
        st.info("Set up a decision on the first tab.")
    else:
        st.markdown("#### Against the grid trajectory")
        sensitivity = grid_sensitivity(
            result["incumbent"], result["replacement"],
            result["horizon_years"],
            initial_intensity=result["grid"]["initial"],
        )
        st.dataframe(
            pd.DataFrame([{
                "Annual grid decline": "%.0f%%" % (row["decline"] * 100.0),
                "Replace in year": row["optimal_carbon_year"],
                "Total kg CO2e": round(row["optimal_carbon"]),
                "Cost of acting now (kg)": round(row["acting_now_costs"]),
            } for row in sensitivity["rows"]]),
            use_container_width=True,
            hide_index=True,
        )
        if sensitivity["recommendation_moves"]:
            st.warning(
                "The recommendation moves by **%d years** across plausible "
                "decarbonisation rates. The grid trajectory is not a "
                "background assumption here; it is the input that decides the "
                "answer."
                % sensitivity["span"]
            )
        else:
            st.success(
                "The same year is optimal at every decarbonisation rate "
                "tested, which makes it a conclusion about the appliances "
                "rather than about the grid forecast."
            )

        st.markdown("#### Against the horizon")
        st.caption(
            "The new unit's embodied carbon is charged only for the share of "
            "its life used inside the horizon, so a later replacement carries "
            "a smaller charge. If the answer changes when the boundary moves, "
            "part of it was about the boundary."
        )
        try:
            robustness = horizon_sensitivity(
                result["incumbent"], result["replacement"], result["grid"]
            )
            st.dataframe(
                pd.DataFrame([{
                    "Horizon (years)": row["horizon"],
                    "Replace in year": row["optimal_carbon_year"],
                    "Acts within horizon": "yes" if row["acts_within_horizon"] else "no",
                } for row in robustness["rows"]]),
                use_container_width=True,
                hide_index=True,
            )
            if robustness["decision_flips"]:
                st.error(robustness["note"])
            elif robustness["optimum_moves"]:
                st.warning(
                    "%s The year moves, but whether to act does not."
                    % robustness["note"]
                )
            else:
                st.success(robustness["note"])
        except ReplacementTimingError as error:
            st.info(str(error))

        st.markdown("#### The condition you can check for yourself")
        threshold = break_even_grid_intensity(
            result["incumbent"], result["replacement"], result["horizon_years"]
        )
        if threshold["break_even_intensity"] is not None:
            st.metric(
                "Break-even grid intensity",
                "%.3f kg CO2e/kWh" % threshold["break_even_intensity"],
            )
        st.info(threshold["note"])

        st.markdown("#### Fuels")
        for entry in list_fuels():
            st.markdown("**%s** — %s" % (entry["label"], entry["note"]))

    st.divider()
    st.subheader("Saved analyses")
    saved = get_plans(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    for record in saved:
        with st.expander(
            "%s → %s — carbon optimum year %d"
            % (
                record["incumbent"], record["replacement"],
                record["optimal_carbon_year"],
            )
        ):
            st.write("Cost optimum year: %d" % record["optimal_cost_year"])
            st.write("Total at the carbon optimum: %.0f kg CO2e"
                     % record["optimal_carbon"])
            payload = record["payload"]
            if payload.get("grid"):
                st.write(
                    "Grid assumed: %.3f kg/kWh falling %.1f%% a year"
                    % (
                        payload["grid"]["initial"],
                        payload["grid"]["decline"] * 100.0,
                    )
                )
            st.write("Saved: %s" % record["created_at"])
            if st.button("Delete", key="timing_delete_%s" % record["id"]):
                delete_plan(user_id, record["id"])
                st.rerun()
