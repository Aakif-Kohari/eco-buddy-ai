"""When an emission happens, and why the app has been ignoring it.

Every other carbon surface in this app multiplies kilograms by a fixed factor
and adds. That is a defensible convention and it contains an assumption nobody
states: that a kilogram released in 2070 and a kilogram released this morning
do the same thing to a target dated 2050. This page makes the assumption
visible and gives the alternative.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.carbon.dynamic_lca import (
    GASES,
    METRICS,
    DynamicLCAError,
    build_emission,
    build_inventory,
    category_table,
    characterisation_factor,
    compare_inventories,
    delete_inventory,
    dynamic_payback_year,
    dynamic_score,
    emission_table,
    expand_annual,
    expand_first_order_decay,
    forcing_series,
    get_dynamic_insights,
    get_inventories,
    gwp,
    list_gases,
    list_metrics,
    metric_comparison,
    model_fidelity,
    save_inventory,
    temporary_storage_credit,
    ton_year_equivalence,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⏳ Time-Explicit LCA</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A kilogram of CO2 released in 2070 and a kilogram released today are not "
    "the same kilogram, and against a target with a date on it they are not "
    "close. This page carries emission timing all the way through to the "
    "impact figure instead of discarding it at the inventory stage."
)

with st.expander("What this changes, and what it deliberately does not"):
    st.markdown(
        """
**GWP100 restarts the clock at every emission.** It integrates radiative
forcing over the hundred years *following* an emission. Applied to something
emitted in year 40 it quietly runs the analysis to year 140; applied to
something emitted today it stops at year 100. Adding those two together is
adding integrals over different intervals.

**Two modules in this app already know the timing and throw it away.** The
landfill methane engine produces a fifty-year release profile. The building
materials engine dates replacements at years 15, 25 and 40. Both then collapse
their time series with a single factor.

**Nothing here is a different opinion about the physics.** The radiative
efficiencies are back-calculated from the published AR6 GWP100 values, so a
CO2 emission scored across exactly a hundred years reproduces the conventional
answer to the last decimal. Any gap you see below is timing and nothing else.

**No discounting.** The atmosphere does not apply one. The decay functions are
the real thing.

**Forcing is not temperature.** Converting one to the other needs a climate
model with its own contested parameters. Every question this page answers is
answerable in forcing terms, so it stops there.

**No opinion about which metric is right.** Cumulative forcing to a target,
forcing *at* that target, and static GWP100 rank options differently and
sometimes in opposite orders. Where they disagree, this page says so and
leaves the choice with you.
        """
    )

BASE_YEAR = 2026

PRESETS = {
    "Gas boiler kept for twenty more years": {
        "note": (
            "The case that motivated this page. Twenty years of operation, "
            "scored against 2100. Static GWP100 gives the year-2045 tonne a "
            "full century to act; it has fifty-five years."
        ),
        "build": lambda: expand_annual(
            "co2", 2000, BASE_YEAR, 20, "Boiler operation", "Heating"
        ),
    },
    "Food waste to landfill, first order decay": {
        "note": (
            "The release profile src/environment/landfill_methane.py already "
            "computes, scored as the time series it is rather than as a "
            "single dated-today total."
        ),
        "build": lambda: expand_first_order_decay(
            "ch4_biogenic", 600, 0.06, BASE_YEAR, 60,
            "Landfill methane", "Waste",
        ),
    },
    "Renovation with staged replacements": {
        "note": (
            "EN 15978 phases: A1-A5 up front, B4 replacements at 15, 25 and "
            "40 years, C1-C4 at end of life. Four dated events, one of which "
            "is most of the total."
        ),
        "build": lambda: [
            build_emission(BASE_YEAR, "co2", 14_000, "A1-A5 product and construction", "Embodied"),
            build_emission(BASE_YEAR + 15, "co2", 2_600, "B4 first replacement", "Embodied"),
            build_emission(BASE_YEAR + 25, "co2", 2_600, "B4 second replacement", "Embodied"),
            build_emission(BASE_YEAR + 40, "co2", 3_100, "B4 third replacement", "Embodied"),
            build_emission(BASE_YEAR + 60, "co2", 1_800, "C1-C4 end of life", "Embodied"),
        ],
    },
    "Refrigerant leaking over a system's life": {
        "note": (
            "A charge escaping gradually rather than all at once. Short "
            "atmospheric lifetime plus late release is the combination where "
            "the static figure is furthest out."
        ),
        "build": lambda: expand_annual(
            "hfc134a", 0.09, BASE_YEAR, 15, "Fugitive charge loss", "Refrigerant"
        ),
    },
}


def _inventory_from_state():
    """Whatever the user has assembled, as a validated inventory."""
    rows = st.session_state.get("dynamic_lca_rows") or []
    if not rows:
        return None
    return build_inventory(
        st.session_state.get("dynamic_lca_name", "Working inventory"),
        rows,
        base_year=min(row["year"] for row in rows),
    )


if "dynamic_lca_rows" not in st.session_state:
    st.session_state["dynamic_lca_rows"] = PRESETS[
        "Gas boiler kept for twenty more years"
    ]["build"]()
    st.session_state["dynamic_lca_name"] = "Gas boiler kept for twenty more years"


tab_score, tab_forcing, tab_metrics, tab_delay, tab_payback, tab_reference = st.tabs([
    "Score",
    "Forcing over time",
    "Metric disagreement",
    "Delay and storage",
    "Dynamic payback",
    "Gases and saved work",
])


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

with tab_score:
    st.subheader("Build a dated inventory")

    preset_name = st.selectbox(
        "Start from a worked example",
        list(PRESETS),
        key="dynamic_lca_preset",
    )
    st.caption(PRESETS[preset_name]["note"])

    load_column, clear_column = st.columns(2)
    with load_column:
        if st.button("Load this example", use_container_width=True):
            st.session_state["dynamic_lca_rows"] = PRESETS[preset_name]["build"]()
            st.session_state["dynamic_lca_name"] = preset_name
            st.rerun()
    with clear_column:
        if st.button("Clear the inventory", use_container_width=True):
            st.session_state["dynamic_lca_rows"] = []
            st.rerun()

    with st.form("dynamic_lca_add"):
        st.markdown("**Add a single dated emission**")
        first, second, third = st.columns(3)
        with first:
            entry_year = st.number_input(
                "Year", min_value=1990, max_value=2200, value=BASE_YEAR, step=1
            )
            entry_gas = st.selectbox(
                "Gas",
                sorted(GASES),
                format_func=lambda key: GASES[key]["label"],
            )
        with second:
            entry_amount = st.number_input(
                "Amount (kg of that gas)", value=1000.0, step=10.0,
                help="Negative values are removals and are allowed.",
            )
            entry_category = st.text_input("Category", value="Heating")
        with third:
            entry_label = st.text_input("Label", value="")
            st.caption(
                "Kilograms of the gas itself, not CO2 equivalent. The whole "
                "point of this page is to do the conversion properly."
            )
        if st.form_submit_button("Add emission", use_container_width=True):
            try:
                st.session_state["dynamic_lca_rows"].append(build_emission(
                    entry_year, entry_gas, entry_amount,
                    entry_label, entry_category,
                ))
                st.rerun()
            except DynamicLCAError as error:
                st.error(str(error))

    inventory = None
    try:
        inventory = _inventory_from_state()
    except DynamicLCAError as error:
        st.error(str(error))

    if inventory is None:
        st.info("Add an emission or load an example to score something.")
    else:
        target_year = st.slider(
            "Target year",
            min_value=int(inventory["last_year"]),
            max_value=2200,
            value=max(2100, int(inventory["last_year"]) + 10),
            help=(
                "Every emission is integrated to this one shared year. That "
                "is the only way contributions released decades apart are "
                "commensurable."
            ),
        )

        try:
            result = dynamic_score(inventory, target_year)
        except DynamicLCAError as error:
            st.error(str(error))
            result = None

        if result:
            first, second, third, fourth = st.columns(4)
            first.metric(
                "Time-explicit total",
                "%.0f kg CO2e" % result["dynamic_total_co2e"],
            )
            second.metric(
                "Conventional GWP100",
                "%.0f kg CO2e" % result["static_total_co2e"],
            )
            third.metric(
                "Difference",
                "%+.0f kg" % result["difference_co2e"],
                delta="%+.1f%%" % (
                    (result["ratio"] - 1.0) * 100.0
                    if result["ratio"] is not None else 0.0
                ),
            )
            fourth.metric("Peak forcing year", str(result["peak_year"]))

            for insight in get_dynamic_insights(result):
                if insight["level"] == "warning":
                    st.warning("**%s**\n\n%s" % (insight["title"], insight["body"]))
                else:
                    st.info("**%s**\n\n%s" % (insight["title"], insight["body"]))

            st.markdown("#### Every emission, and what the window cost it")
            rows = emission_table(result)
            table = pd.DataFrame([{
                "Year": row["year"],
                "Gas": row["gas_label"],
                "What": row["label"],
                "Category": row["category"],
                "kg of gas": round(row["amount_kg"], 3),
                "Years to target": row["years_available"],
                "Dynamic factor": round(row["dynamic_factor"], 3),
                "Static factor": round(row["static_factor"], 3),
                "Dynamic kg CO2e": round(row["dynamic_co2e"], 1),
                "Static kg CO2e": round(row["static_co2e"], 1),
            } for row in rows])
            st.dataframe(table, use_container_width=True, hide_index=True)

            categories = category_table(result)
            if len(categories) > 1:
                st.markdown("#### By category")
                figure = go.Figure()
                figure.add_bar(
                    name="Conventional GWP100",
                    x=[row["category"] for row in categories],
                    y=[row["static_co2e"] for row in categories],
                )
                figure.add_bar(
                    name="Time-explicit",
                    x=[row["category"] for row in categories],
                    y=[row["dynamic_co2e"] for row in categories],
                )
                figure.update_layout(
                    barmode="group",
                    yaxis_title="kg CO2e",
                    height=380,
                    margin=dict(l=10, r=10, t=30, b=10),
                )
                st.plotly_chart(figure, use_container_width=True)

            with st.form("dynamic_lca_save"):
                save_name = st.text_input(
                    "Save this inventory as", value=inventory["name"]
                )
                if st.form_submit_button("Save"):
                    try:
                        stored = build_inventory(
                            save_name, inventory["emissions"],
                            base_year=inventory["base_year"],
                        )
                        save_inventory(user_id, stored, result)
                        st.success("Saved.")
                    except DynamicLCAError as error:
                        st.error(str(error))


# ---------------------------------------------------------------------------
# Forcing over time
# ---------------------------------------------------------------------------

with tab_forcing:
    st.subheader("What the inventory is actually doing, year by year")
    st.caption(
        "The upper trace is the forcing still being exerted at that moment. "
        "The lower is what has accumulated. A pathway can satisfy a "
        "cumulative budget and still overshoot on the way, and only the first "
        "trace shows that."
    )

    try:
        inventory = _inventory_from_state()
    except DynamicLCAError as error:
        inventory = None
        st.error(str(error))

    if inventory is None:
        st.info("Build an inventory on the Score tab first.")
    else:
        horizon = st.slider(
            "Plot to year",
            min_value=int(inventory["last_year"]) + 1,
            max_value=2250,
            value=max(2120, int(inventory["last_year"]) + 20),
            key="dynamic_lca_plot_year",
        )
        try:
            series = forcing_series(inventory, horizon)
        except DynamicLCAError as error:
            series = []
            st.error(str(error))

        if series:
            frame = pd.DataFrame(series)

            instantaneous = go.Figure()
            instantaneous.add_scatter(
                x=frame["year"],
                y=frame["instantaneous_forcing"],
                mode="lines",
                name="Instantaneous forcing",
                fill="tozeroy",
            )
            instantaneous.update_layout(
                yaxis_title="W/m2",
                xaxis_title="Year",
                height=320,
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(instantaneous, use_container_width=True)

            cumulative = go.Figure()
            cumulative.add_scatter(
                x=frame["year"],
                y=frame["cumulative_co2e"],
                mode="lines",
                name="Accumulated",
            )
            cumulative.update_layout(
                yaxis_title="Accumulated kg CO2e",
                xaxis_title="Year",
                height=320,
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(cumulative, use_container_width=True)

            peak_row = frame.loc[frame["instantaneous_forcing"].idxmax()]
            st.markdown(
                "Forcing peaks at **%.3g W/m2** in **%d**, and **%.3g W/m2** "
                "is still acting in **%d**."
                % (
                    peak_row["instantaneous_forcing"],
                    int(peak_row["year"]),
                    frame.iloc[-1]["instantaneous_forcing"],
                    int(frame.iloc[-1]["year"]),
                )
            )


# ---------------------------------------------------------------------------
# Metric disagreement
# ---------------------------------------------------------------------------

with tab_metrics:
    st.subheader("Four metrics, four questions")
    st.caption(
        "These are not four attempts at the same number. Where they rank "
        "options differently, that difference is the finding."
    )

    for metric in list_metrics():
        st.markdown(
            "**%s** (%s) — *%s*  \n%s"
            % (metric["label"], metric["unit"], metric["question"], metric["note"])
        )

    st.divider()

    try:
        inventory = _inventory_from_state()
    except DynamicLCAError:
        inventory = None

    if inventory is None:
        st.info("Build an inventory on the Score tab first.")
    else:
        compare_year = st.number_input(
            "Score everything to",
            min_value=int(inventory["last_year"]),
            max_value=2200,
            value=2100,
            step=5,
            key="dynamic_lca_metric_year",
        )
        try:
            comparison = metric_comparison(inventory, compare_year)
        except DynamicLCAError as error:
            comparison = None
            st.error(str(error))

        if comparison:
            values = comparison["values"]
            columns = st.columns(4)
            for column, key in zip(columns, METRICS):
                column.metric(
                    METRICS[key]["label"],
                    "%.3g %s" % (values[key], METRICS[key]["unit"]),
                )
            if comparison["co2e_spread"]:
                st.info(
                    "The three CO2e-denominated metrics span a factor of "
                    "**%.2f** on this inventory. All three are correct "
                    "answers to different questions."
                    % comparison["co2e_spread"]
                )

        st.markdown("#### Set two inventories against each other")
        st.caption(
            "Equal-weighted under GWP100, ranked differently under the "
            "others. That is the disagreement this tab exists to expose."
        )
        methane_kg = st.number_input(
            "Methane released in %d (kg)" % BASE_YEAR,
            min_value=1.0, value=500.0, step=50.0,
        )
        equivalent = methane_kg * GASES["ch4_fossil"]["gwp100"]
        st.caption(
            "Compared against %.0f kg of CO2, which is the same number of "
            "kilograms of CO2e under GWP100." % equivalent
        )
        try:
            head_to_head = compare_inventories(
                [
                    build_inventory(
                        "Methane",
                        [build_emission(BASE_YEAR, "ch4_fossil", methane_kg)],
                    ),
                    build_inventory(
                        "Carbon dioxide",
                        [build_emission(BASE_YEAR, "co2", equivalent)],
                    ),
                ],
                compare_year,
            )
        except DynamicLCAError as error:
            head_to_head = None
            st.error(str(error))

        if head_to_head:
            ranking_rows = []
            for metric, order in head_to_head["rankings"].items():
                ranking_rows.append({
                    "Metric": METRICS[metric]["label"],
                    "Lowest impact first": " → ".join(order),
                })
            st.dataframe(
                pd.DataFrame(ranking_rows),
                use_container_width=True,
                hide_index=True,
            )
            if head_to_head["robust"]:
                st.success(
                    "Every metric agrees on the ordering. That is a genuinely "
                    "robust conclusion and worth trusting."
                )
            else:
                st.warning(
                    "The metrics disagree. Which of these is 'worse' is a "
                    "question about whether you care about cumulative "
                    "warming to the target or warming still present at it. "
                    "No calculation settles that."
                )


# ---------------------------------------------------------------------------
# Delay and storage
# ---------------------------------------------------------------------------

with tab_delay:
    st.subheader("Delaying an emission, and storing carbon temporarily")
    st.caption(
        "Both are worth something and neither is a removal. The credit comes "
        "entirely from the years the carbon was not in the air before the "
        "target, which is why the target year changes the answer so much."
    )

    first, second, third = st.columns(3)
    with first:
        stored_kg = st.number_input(
            "Quantity (kg CO2)", min_value=1.0, value=1000.0, step=100.0
        )
    with second:
        storage_years = st.slider("Held out of the air for (years)", 1, 120, 30)
    with third:
        storage_target = st.number_input(
            "Target year", min_value=BASE_YEAR + 1, max_value=2300,
            value=2126, step=1, key="dynamic_lca_storage_target",
        )

    try:
        storage = temporary_storage_credit(
            stored_kg, storage_years, storage_target, base_year=BASE_YEAR
        )
    except DynamicLCAError as error:
        storage = None
        st.error(str(error))

    if storage:
        first, second, third = st.columns(3)
        first.metric(
            "Credit from the delay", "%.0f kg CO2e" % storage["credit_co2e"]
        )
        second.metric(
            "As a share of permanent removal",
            "%.1f%%" % (storage["credit_fraction"] * 100.0),
        )
        third.metric(
            "Moura-Costa ton-year",
            "%.1f%%" % (storage["moura_costa_equivalent"] * 100.0),
        )

        st.info(storage["note"])

        st.markdown(
            """
**The two ton-year conventions do not agree, and one of them is not really a
separate method.** Lashof accounting counts the forcing pushed beyond the
horizon, which turns out to be algebraically identical to the calculation
above — the numbers match to the last decimal. Moura-Costa divides the storage
duration by a fixed equivalence time and is consistently the more generous.
Both are quoted in offset documentation, frequently without saying which.
            """
        )
        comparison_rows = [{
            "Method": "Radiative forcing (this page)",
            "Credit as share of permanence": "%.1f%%" % (
                storage["credit_fraction"] * 100.0
            ),
        }, {
            "Method": "Lashof ton-year",
            "Credit as share of permanence": "%.1f%%" % (
                storage["lashof_equivalent"] * 100.0
            ),
        }, {
            "Method": "Moura-Costa ton-year",
            "Credit as share of permanence": "%.1f%%" % (
                storage["moura_costa_equivalent"] * 100.0
            ),
        }]
        st.dataframe(
            pd.DataFrame(comparison_rows),
            use_container_width=True,
            hide_index=True,
        )

        durations = list(range(0, 121, 5))
        curve = go.Figure()
        curve.add_scatter(
            x=durations,
            y=[
                temporary_storage_credit(
                    stored_kg, max(duration, 1), storage_target,
                    base_year=BASE_YEAR,
                )["credit_fraction"] * 100.0
                for duration in durations
            ],
            mode="lines",
            name="Radiative forcing",
        )
        curve.add_scatter(
            x=durations,
            y=[ton_year_equivalence(duration) * 100.0 for duration in durations],
            mode="lines",
            name="Moura-Costa",
        )
        curve.update_layout(
            xaxis_title="Years held",
            yaxis_title="Credit, % of permanent removal",
            height=360,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(curve, use_container_width=True)


# ---------------------------------------------------------------------------
# Dynamic payback
# ---------------------------------------------------------------------------

with tab_payback:
    st.subheader("Payback, with both sides dated")
    st.caption(
        "src/carbon/carbon_payback.py divides an upfront figure by an annual "
        "one. That treats a kilogram emitted at manufacture and a kilogram "
        "avoided twelve years later as cancelling exactly. They do not: the "
        "first has been forcing the climate for twelve years longer."
    )

    first, second, third = st.columns(3)
    with first:
        upfront = st.number_input(
            "Upfront burden (kg CO2)", min_value=1.0, value=6000.0, step=100.0
        )
    with second:
        annual_saving = st.number_input(
            "Annual saving (kg CO2)", min_value=1.0, value=900.0, step=50.0
        )
    with third:
        saving_years = st.slider("Saving lasts (years)", 1, 60, 40)

    try:
        payback = dynamic_payback_year(
            build_inventory(
                "Manufacture",
                [build_emission(BASE_YEAR, "co2", upfront, "Upfront", "Capital")],
            ),
            build_inventory(
                "Avoided",
                expand_annual(
                    "co2", annual_saving, BASE_YEAR + 1, saving_years,
                    "Avoided operation", "Operation",
                ),
            ),
            2100,
        )
    except DynamicLCAError as error:
        payback = None
        st.error(str(error))

    if payback:
        first, second, third = st.columns(3)
        first.metric(
            "Simple payback",
            "%.1f years" % payback["naive_payback_years"]
            if payback["naive_payback_years"] else "n/a",
        )
        second.metric(
            "Time-explicit payback",
            "%d years" % payback["breakeven_years_from_start"]
            if payback["breakeven_years_from_start"] is not None else "never",
        )
        third.metric(
            "Worst point",
            "%.0f kg CO2e in %d" % (
                payback["peak_deficit_co2e"], payback["peak_deficit_year"]
            ),
        )

        if payback["never_repays"]:
            st.error(
                "This never repays within the window. The simple calculation "
                "still reports a payback period, because it compares "
                "quantities rather than effects."
            )
        elif payback["breakeven_years_from_start"] is not None:
            gap = (
                payback["breakeven_years_from_start"]
                - (payback["naive_payback_years"] or 0)
            )
            st.warning(
                "The time-explicit answer is **%.1f years later** than the "
                "simple one. The difference is not a correction factor; it is "
                "the forcing the upfront burden exerted while the savings "
                "were still accruing."
                % gap
            )

        trajectory = pd.DataFrame(payback["trajectory"])
        figure = go.Figure()
        figure.add_scatter(
            x=trajectory["year"],
            y=trajectory["net_co2e"],
            mode="lines",
            name="Net accumulated",
            fill="tozeroy",
        )
        figure.add_hline(y=0, line_dash="dash")
        figure.update_layout(
            yaxis_title="Net accumulated kg CO2e",
            xaxis_title="Year",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)


# ---------------------------------------------------------------------------
# Reference and saved work
# ---------------------------------------------------------------------------

with tab_reference:
    st.subheader("The gases, and how well the model reproduces the standard")

    reference_rows = []
    for entry in list_gases():
        reference_rows.append({
            "Gas": entry["label"],
            "Formula": entry["formula"],
            "Lifetime (yr)": entry["lifetime"] if entry["lifetime"] else "—",
            "GWP20": round(entry["gwp20"], 1),
            "GWP100": entry["gwp100"],
            "GWP500": round(entry["gwp500"], 1),
        })
    st.dataframe(
        pd.DataFrame(reference_rows), use_container_width=True, hide_index=True
    )

    for entry in list_gases():
        with st.expander(entry["label"]):
            st.markdown(entry["note"])

    st.markdown("#### Where the model departs from the published values")
    st.caption(
        "The calibration is anchored at a hundred years, so agreement at "
        "twenty years is a property of the decay model rather than an input. "
        "Methane is the outlier, because the published methane values apply a "
        "different feedback treatment at each horizon and a single exponential "
        "cannot follow that."
    )
    fidelity_rows = []
    for row in model_fidelity():
        fidelity_rows.append({
            "Gas": row["label"],
            "Modelled GWP20": round(row["modelled_gwp20"], 1),
            "Published GWP20": row["published_gwp20"],
            "Deviation": "%+.1f%%" % (row["deviation"] * 100.0),
            "Within 5%": "yes" if row["within_tolerance"] else "no",
        })
    st.dataframe(
        pd.DataFrame(fidelity_rows), use_container_width=True, hide_index=True
    )

    st.markdown("#### How much a decade of delay costs a factor")
    factor_rows = []
    for gas_key in ("co2", "ch4_fossil", "n2o", "sf6"):
        factor_rows.append({
            "Gas": GASES[gas_key]["label"],
            "Emitted 2026": round(characterisation_factor(gas_key, 2026, 2100), 1),
            "Emitted 2050": round(characterisation_factor(gas_key, 2050, 2100), 1),
            "Emitted 2080": round(characterisation_factor(gas_key, 2080, 2100), 1),
            "Static GWP100": round(gwp(gas_key, 100), 1),
        })
    st.dataframe(
        pd.DataFrame(factor_rows), use_container_width=True, hide_index=True
    )
    st.caption(
        "Read across a row: that is how much of the conventional factor "
        "survives once the emission has to fit inside a window ending in "
        "2100. Sulphur hexafluoride barely notices. Methane holds its value "
        "far longer than carbon dioxide, which is the opposite of what most "
        "people expect and follows directly from delivering its effect early."
    )

    st.divider()
    st.subheader("Saved inventories")
    saved = get_inventories(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    for record in saved:
        ratio = (
            record["dynamic_total"] / record["static_total"]
            if record["static_total"] else None
        )
        with st.expander(
            "%s — %.0f kg CO2e to %d"
            % (record["name"], record["dynamic_total"], record["target_year"])
        ):
            st.write(
                "Conventional GWP100: %.0f kg CO2e" % record["static_total"]
            )
            if ratio is not None:
                st.write("Ratio: %.3f" % ratio)
            st.write("Saved: %s" % record["created_at"])
            if st.button("Delete", key="dynamic_lca_delete_%s" % record["id"]):
                delete_inventory(user_id, record["id"])
                st.rerun()
