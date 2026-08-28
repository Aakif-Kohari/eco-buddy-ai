"""Carbon released when the land changed hands, and the choice that sizes it.

Nothing else in this app accounts for the clearing. For most of a diet that is
a small omission. For beef, soy, palm oil, cocoa and coffee it is frequently
larger than every other stage combined, and the app currently reports one
number for a kilogram from recently cleared forest and a kilogram from pasture
established a century ago.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.environment.luc_amortisation import (
    AMORTISATION_SCHEMES,
    ATTRIBUTIONS,
    ILUC_SCENARIOS,
    LAND_COVERS,
    LUCError,
    amortisation_weights,
    assess,
    compare_schemes,
    delete_assessment,
    foregone_sequestration,
    get_assessments,
    get_luc_insights,
    list_iluc_scenarios,
    list_land_covers,
    list_schemes,
    save_assessment,
    scheme_sensitivity,
    soil_decay_profile,
    soil_released_by,
    sourcing_comparison,
    stock_change,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🌳 Land-Use Change Carbon</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Clearing land releases a stock, once. Turning that into a per-kilogram "
    "figure means choosing how to spread it, and the choice moves the answer "
    "by more than a factor of two. This page makes the choice explicit "
    "instead of burying it in a constant."
)

with st.expander("The four things this page refuses to decide for you"):
    st.markdown(
        """
**Which amortisation period is correct.** PAS 2050, the IPCC guidelines and
the EU Product Environmental Footprint method all say twenty years. Several
national inventories say thirty. A discounted attribution front-loads instead,
which is the only scheme here that reflects when the carbon is actually in the
atmosphere. All four are shown side by side; none is nominated.

**Whether to trace the plot or average the region.** Charging the full stock to
the land actually used, and spreading national conversion across national
output, answer different questions. The ratio between them is reported,
because a large ratio means sourcing matters for this commodity and a small
one means it does not.

**Whether indirect land-use change belongs in the total.** Displaced production
moves somewhere and the published estimates span an order of magnitude.
Excluding it is not the neutral option — it is the bottom of that range,
selected silently, and it is what every other module in this app currently
does. Here it is available only as a named scenario, and any total containing
one says so.

**Whether foregone sequestration is an emission.** Land held as pasture is land
not regrowing forest. It is computed, shown on its own line, and never folded
into a total.

**What the page will not let you do:** mix direct and country-average
attribution inside one figure. That produces a number that is not an answer to
any question.
        """
    )


tab_conversion, tab_schemes, tab_commodity, tab_reference = st.tabs([
    "The conversion",
    "Amortisation choices",
    "Per kilogram, and sourcing",
    "Land covers and saved work",
])


# ---------------------------------------------------------------------------
# The conversion
# ---------------------------------------------------------------------------

with tab_conversion:
    st.subheader("What the clearing released")

    first, second, third = st.columns(3)
    with first:
        prior = st.selectbox(
            "Land cover before",
            sorted(LAND_COVERS),
            index=sorted(LAND_COVERS).index("tropical_moist_forest"),
            format_func=lambda key: LAND_COVERS[key]["label"],
        )
    with second:
        subsequent = st.selectbox(
            "Land cover after",
            sorted(LAND_COVERS),
            index=sorted(LAND_COVERS).index("pasture"),
            format_func=lambda key: LAND_COVERS[key]["label"],
        )
    with third:
        area = st.number_input(
            "Area converted (ha)", min_value=0.01, value=1.0, step=0.5
        )

    st.caption(LAND_COVERS[prior]["note"])

    change = None
    try:
        change = stock_change(prior, subsequent, area)
    except LUCError as error:
        st.error(str(error))

    if change:
        first, second, third, fourth = st.columns(4)
        first.metric("Biomass", "%.0f t CO2" % change["biomass_co2"])
        second.metric("Soil", "%.0f t CO2" % change["soil_co2"])
        third.metric("Total", "%.0f t CO2" % change["total_co2"])
        fourth.metric(
            "Per hectare", "%.0f t CO2" % (change["total_co2"] / change["area_ha"])
        )

        if change["sequestering"]:
            st.success(
                "This conversion accumulates carbon rather than releasing it. "
                "Going from %s to %s adds stock, which is the one common case "
                "in this table that runs the other way."
                % (change["prior_label"], change["subsequent_label"])
            )
        else:
            st.warning(
                "%.0f%% of the release is soil rather than biomass. Soil is "
                "the part that keeps going for decades after the clearing, "
                "and the part no emission factor in this app represents."
                % ((change["soil_share"] or 0.0) * 100.0)
            )

        st.markdown("#### The soil pool does not go all at once")
        decay_years = st.slider("Show soil release over", 10, 150, 60, 5)
        profile = soil_decay_profile(change, years=decay_years)
        frame = pd.DataFrame(profile)

        figure = go.Figure()
        figure.add_bar(
            x=frame["year_offset"],
            y=frame["co2"],
            name="Released that year",
        )
        figure.add_scatter(
            x=frame["year_offset"],
            y=frame["cumulative_share"] * 100.0,
            name="Cumulative %",
            yaxis="y2",
            mode="lines",
        )
        figure.update_layout(
            xaxis_title="Years after conversion",
            yaxis_title="t CO2 released",
            yaxis2=dict(
                title="Cumulative %", overlaying="y", side="right", range=[0, 100]
            ),
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)

        elapsed = st.slider("Years since this conversion", 0, 100, 10)
        released = soil_released_by(change, elapsed)
        st.write(
            "After **%d years**, %.0f t CO2 of the soil pool has gone and "
            "**%.0f t CO2 is still to come**. A conversion a decade ago is "
            "not a finished event."
            % (elapsed, released, change["soil_co2"] - released)
        )

        st.divider()
        st.markdown("#### Foregone sequestration — reported apart, on purpose")
        foregone_years = st.slider("Over how many years", 1, 100, 20)
        foregone = foregone_sequestration(prior, area, foregone_years)
        st.metric(
            "Carbon the land would have taken up",
            "%.0f t CO2" % foregone["co2"],
        )
        st.caption(foregone["note"])


# ---------------------------------------------------------------------------
# Amortisation choices
# ---------------------------------------------------------------------------

with tab_schemes:
    st.subheader("Four defensible ways to spread one stock")

    for scheme in list_schemes():
        st.markdown("**%s** — %s" % (scheme["label"], scheme["note"]))

    st.divider()

    first, second, third = st.columns(3)
    with first:
        stock_co2 = st.number_input(
            "Stock released (t CO2)", min_value=1.0, value=500.0, step=25.0
        )
    with second:
        conversion_year = st.number_input(
            "Conversion year", min_value=1900, max_value=2100, value=2016, step=1
        )
    with third:
        assessment_year = st.number_input(
            "Assessment year", min_value=1900, max_value=2100, value=2026, step=1
        )

    try:
        comparison = compare_schemes(stock_co2, conversion_year, assessment_year)
    except LUCError as error:
        comparison = None
        st.error(str(error))

    if comparison:
        rows = []
        for row in comparison["rows"]:
            rows.append({
                "Scheme": row["scheme_label"],
                "Window": "%d years" % row["period"],
                "Years elapsed": row["years_elapsed"],
                "Charged this year (t CO2)": round(row["annual_co2"], 2),
                "Charged so far (t CO2)": round(row["cumulative_co2"], 1),
                "Window closed": "yes" if row["obligation_complete"] else "no",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if comparison["all_complete"]:
            st.info(
                "Every window has closed for this conversion. The obligation "
                "is discharged, which is not the same as the carbon having "
                "come back."
            )
        elif comparison["spread"]:
            st.warning(
                "The schemes still in their window differ by a factor of "
                "**%.1f** for the same physical event. That is a policy "
                "choice, not biology, and it is larger than most of the "
                "uncertainty in the stock figures themselves."
                % comparison["spread"]
            )

        st.markdown("#### How each scheme distributes the stock")
        weight_figure = go.Figure()
        for key in sorted(AMORTISATION_SCHEMES):
            weights = amortisation_weights(key)
            weight_figure.add_scatter(
                x=list(range(len(weights))),
                y=[value * 100.0 for value in weights],
                mode="lines+markers",
                name=AMORTISATION_SCHEMES[key]["label"],
            )
        weight_figure.update_layout(
            xaxis_title="Years after conversion",
            yaxis_title="Share of the stock charged, %",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(weight_figure, use_container_width=True)
        st.caption(
            "Every curve integrates to 100%. That is the only property that "
            "makes them comparable at all, and there is a test asserting it "
            "for each scheme."
        )


# ---------------------------------------------------------------------------
# Per kilogram and sourcing
# ---------------------------------------------------------------------------

with tab_commodity:
    st.subheader("From a hectare to a kilogram")

    first, second = st.columns(2)
    with first:
        commodity = st.selectbox(
            "Commodity",
            ["beef", "soy", "palm_oil", "maize", "sugar", "wheat"],
            format_func=lambda key: key.replace("_", " ").title(),
        )
        yield_rate = st.number_input(
            "Yield (tonnes per hectare per year)",
            min_value=0.001, value=0.05, step=0.01, format="%.3f",
        )
        consumption = st.number_input(
            "Your annual consumption (kg)", min_value=0.0, value=25.0, step=1.0
        )
    with second:
        scheme_choice = st.selectbox(
            "Amortisation scheme",
            sorted(AMORTISATION_SCHEMES),
            format_func=lambda key: AMORTISATION_SCHEMES[key]["label"],
        )
        attribution_choice = st.radio(
            "Attribution",
            sorted(ATTRIBUTIONS),
            format_func=lambda key: key.replace("_", " ").title(),
        )
        st.caption(ATTRIBUTIONS[attribution_choice])
        iluc_choice = st.selectbox(
            "Indirect land-use change",
            sorted(ILUC_SCENARIOS),
            format_func=lambda key: ILUC_SCENARIOS[key]["label"],
        )
        st.caption(ILUC_SCENARIOS[iluc_choice]["note"])

    st.markdown("**National figures** — needed for country-average attribution.")
    first, second = st.columns(2)
    with first:
        national_conversion = st.number_input(
            "National conversion (ha per year)",
            min_value=0.0, value=1_200_000.0, step=10_000.0,
        )
    with second:
        national_output = st.number_input(
            "National output (tonnes per year)",
            min_value=1.0, value=10_500_000.0, step=100_000.0,
        )

    result = None
    try:
        result = assess(
            commodity=commodity,
            prior_cover=prior,
            subsequent_cover=subsequent,
            area_ha=area,
            annual_yield_t_per_ha=yield_rate,
            conversion_year=conversion_year,
            assessment_year=assessment_year,
            scheme=scheme_choice,
            attribution=attribution_choice,
            iluc_scenario=iluc_choice,
            annual_consumption_kg=consumption,
            national_conversion_ha=national_conversion,
            national_output_t=national_output,
        )
    except LUCError as error:
        st.error(str(error))

    if result:
        st.caption("Every figure below: **%s**" % result["label"])

        first, second, third, fourth = st.columns(4)
        first.metric(
            "Direct attribution",
            "%.1f kg CO2/kg" % result["direct_intensity_t_co2_per_t"],
        )
        second.metric(
            "Country average",
            "%.2f kg CO2/kg" % (
                result["country_average_intensity_t_co2_per_t"] or 0.0
            ),
        )
        third.metric(
            "Indirect term",
            "%.2f kg CO2/kg" % result["iluc_intensity_t_co2_per_t"],
        )
        fourth.metric(
            "Your year", "%.0f kg CO2" % result["total_annual_kg_co2"]
        )

        for insight in get_luc_insights(result):
            if insight["level"] == "warning":
                st.warning("**%s**\n\n%s" % (insight["title"], insight["body"]))
            else:
                st.info("**%s**\n\n%s" % (insight["title"], insight["body"]))

        st.markdown("#### The same commodity under every scheme")
        sensitivity = scheme_sensitivity(result)
        st.dataframe(
            pd.DataFrame([{
                "Scheme": row["label"],
                "kg CO2 per kg": round(row["intensity_t_co2_per_t"], 2),
                "Your year (kg CO2)": round(row["annual_kg_co2"], 0),
            } for row in sensitivity["rows"]]),
            use_container_width=True,
            hide_index=True,
        )
        if sensitivity["spread"]:
            st.warning(
                "A factor of **%.1f** between the largest and smallest, for "
                "the same clearing, the same yield and the same consumption. "
                "Nothing physical changed between those rows."
                % sensitivity["spread"]
            )

        st.markdown("#### What switching to a verified conversion-free source buys")
        clean_intensity = st.number_input(
            "Conversion-free intensity (kg CO2 per kg)",
            min_value=0.0,
            value=min(25.0, float(result["total_intensity_t_co2_per_t"])),
            step=1.0,
        )
        try:
            switch = sourcing_comparison(result, clean_intensity)
            first, second, third = st.columns(3)
            first.metric(
                "Saving per kg", "%.1f kg CO2" % switch["saving_per_kg"]
            )
            second.metric(
                "Saving per year", "%.0f kg CO2" % switch["annual_saving_kg_co2"]
            )
            third.metric(
                "Reduction", "%.0f%%" % ((switch["reduction_share"] or 0) * 100.0)
            )
        except LUCError as error:
            st.error(str(error))

        if st.button("Save this assessment"):
            try:
                save_assessment(user_id, result)
                st.success("Saved.")
            except LUCError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# Reference and saved work
# ---------------------------------------------------------------------------

with tab_reference:
    st.subheader("Carbon stocks by land cover")

    cover_rows = []
    for entry in list_land_covers():
        cover_rows.append({
            "Cover": entry["label"],
            "Biomass (tC/ha)": entry["biomass_c"],
            "Soil (tC/ha)": entry["soil_c"],
            "Total (tC/ha)": entry["total_c"],
            "Total (t CO2/ha)": round(entry["total_co2_per_ha"], 0),
            "Regrowth (tC/ha/yr)": entry["regrowth_c_per_year"],
        })
    st.dataframe(
        pd.DataFrame(cover_rows), use_container_width=True, hide_index=True
    )

    stock_figure = go.Figure()
    stock_figure.add_bar(
        name="Biomass",
        x=[entry["label"] for entry in list_land_covers()],
        y=[entry["biomass_c"] for entry in list_land_covers()],
    )
    stock_figure.add_bar(
        name="Soil",
        x=[entry["label"] for entry in list_land_covers()],
        y=[entry["soil_c"] for entry in list_land_covers()],
    )
    stock_figure.update_layout(
        barmode="stack",
        yaxis_title="tonnes carbon per hectare",
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(stock_figure, use_container_width=True)
    st.caption(
        "Peatland is off the scale of everything else and is the reason any "
        "conversion involving organic soils dominates whatever else is in an "
        "assessment."
    )

    for entry in list_land_covers():
        with st.expander(entry["label"]):
            st.markdown(entry["note"])

    st.markdown("#### The indirect land-use change range")
    iluc_rows = []
    for commodity_key in ("beef", "palm_oil", "soy", "maize", "sugar", "wheat"):
        row = {"Commodity": commodity_key.replace("_", " ").title()}
        for scenario in list_iluc_scenarios():
            factor = scenario["factors"].get(commodity_key)
            row[scenario["label"]] = factor if factor is not None else "—"
        iluc_rows.append(row)
    st.dataframe(
        pd.DataFrame(iluc_rows), use_container_width=True, hide_index=True
    )
    st.caption(
        "Tonnes CO2e per tonne of commodity. The spread between models is "
        "wider than the spread between commodities, which is the honest "
        "summary of the state of this literature."
    )

    st.divider()
    st.subheader("Saved assessments")
    saved = get_assessments(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    for record in saved:
        with st.expander(
            "%s — %.1f kg CO2 per kg (%s)"
            % (
                record["commodity"].title(),
                record["intensity"],
                AMORTISATION_SCHEMES[record["scheme"]]["label"],
            )
        ):
            st.write(record["payload"].get("label", ""))
            st.write("Your year: %.0f kg CO2" % record["annual_kg_co2"])
            st.write(
                "Attribution: %s. Indirect: %s."
                % (
                    record["attribution"].replace("_", " "),
                    ILUC_SCENARIOS[record["iluc_scenario"]]["label"],
                )
            )
            st.write("Saved: %s" % record["created_at"])
            if st.button("Delete", key="luc_delete_%s" % record["id"]):
                delete_assessment(user_id, record["id"])
                st.rerun()
