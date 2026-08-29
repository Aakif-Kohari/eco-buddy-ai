"""How much of a footprint was never counted, and which way the error runs.

Every process-based figure in this app is precise about what it counted and
silent about what it left out. The omission is not random and it is not
symmetric: a boundary can only leave things out. This page estimates the size
of it and, more usefully, flags the comparisons whose answer depends on it.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.carbon.truncation_correction import (
    SECTORS,
    TruncationError,
    build_process_estimate,
    compare_options,
    convergence_profile,
    correct,
    coverage_grade,
    delete_correction,
    get_corrections,
    get_truncation_insights,
    io_upper_bound,
    list_sectors,
    modelled_tiers,
    portfolio_coverage,
    save_correction,
    screening_loss,
    tiers_to_coverage,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>✂️ Truncation Correction</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A process-based footprint is a sum over everything somebody decided to "
    "include. Upstream of that decision sit the accountant who invoiced the "
    "supplier, the insurance on the shipping, the software licence used to "
    "design the part. Each is small. There is an unbounded number of them, "
    "and the series does not close as fast as the boundary assumed."
)

with st.expander("Why this is worth a page of its own"):
    st.markdown(
        """
**The error only goes one way.** Truncation cannot overstate. A figure with an
unstated cutoff is not approximate in the ordinary sense that it might be high
or low — it is biased low, and every comparison against a target inherits that
bias. The published estimates put the typical omission at twenty to fifty
percent.

**It does not cancel out in a comparison.** A steel beam's chain converges
quickly. A consultancy's does not. Comparing a material-intensive option
against a service-intensive one on process data alone systematically favours
the service, and that is the shape of a great many recommendations this app
makes.

**This app already holds both methods and never reconciles them.**
`eeio_spend.py` is complete by construction and coarse. `building_materials_lca.py`
and `product_carbon_footprint.py` are specific and incomplete. Neither is
wrong. Their disagreement is measurable and is currently discarded.

**A flat uplift would be worse than nothing.** A blanket +30% is a guess
wearing a decimal point, and it would make the service-versus-material
comparison worse rather than better, because it applies the same correction to
chains that converge at different rates.

**The one real assumption.** The tail is modelled as a geometric series with a
constant pass-through per tier. It is not exactly constant. Where two or more
tiers are supplied, the ratio is fitted from that data rather than assumed,
the individual tier ratios are shown, and their spread drives a warning when
the model fits the chain in front of it badly.
        """
    )


PRESETS = {
    "Heat pump — three tiers of bill of materials": {
        "sector": "manufacturing",
        "tiers": [
            {"tier": 0, "co2e_kg": 400.0, "label": "Final assembly"},
            {"tier": 1, "co2e_kg": 180.0, "label": "Components"},
            {"tier": 2, "co2e_kg": 70.0, "label": "Raw materials"},
        ],
        "spend": 3200.0,
    },
    "Consultancy engagement — reported operations only": {
        "sector": "services",
        "tiers": [
            {"tier": 0, "co2e_kg": 600.0, "label": "Reported operations"},
        ],
        "spend": 24_000.0,
    },
    "Cloud hosting — operational plus one tier": {
        "sector": "ict",
        "tiers": [
            {"tier": 0, "co2e_kg": 850.0, "label": "Metered electricity"},
            {"tier": 1, "co2e_kg": 320.0, "label": "Hardware amortised"},
        ],
        "spend": 9_000.0,
    },
    "Loft insulation — well characterised materials": {
        "sector": "construction",
        "tiers": [
            {"tier": 0, "co2e_kg": 210.0, "label": "Installed material"},
            {"tier": 1, "co2e_kg": 74.0, "label": "Material production"},
            {"tier": 2, "co2e_kg": 26.0, "label": "Feedstock"},
            {"tier": 3, "co2e_kg": 9.0, "label": "Feedstock extraction"},
        ],
        "spend": 1_400.0,
    },
}


tab_correct, tab_compare, tab_portfolio, tab_sectors = st.tabs([
    "Correct an estimate",
    "Compare two options",
    "Portfolio and screening",
    "Sectors and saved work",
])


# ---------------------------------------------------------------------------
# Correct one estimate
# ---------------------------------------------------------------------------

with tab_correct:
    st.subheader("A process figure, and what its boundary left out")

    preset_name = st.selectbox("Worked example", list(PRESETS))
    preset = PRESETS[preset_name]

    sector_key = st.selectbox(
        "Sector",
        sorted(SECTORS),
        index=sorted(SECTORS).index(preset["sector"]),
        format_func=lambda key: SECTORS[key]["label"],
    )
    st.caption(SECTORS[sector_key]["note"])

    st.markdown("**Tiers you have data for** — tier zero is the direct stage.")
    tier_frame = st.data_editor(
        pd.DataFrame(preset["tiers"]),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "tier": st.column_config.NumberColumn("Tier", min_value=0, step=1),
            "co2e_kg": st.column_config.NumberColumn("kg CO2e", min_value=0.0),
            "label": st.column_config.TextColumn("What it covers"),
        },
        key="truncation_tiers",
    )

    first, second = st.columns(2)
    with first:
        use_io = st.checkbox(
            "Apply an input-output ceiling from spend", value=True,
            help=(
                "The spend-based route is complete by construction, so it is "
                "an approximate upper bound on the total."
            ),
        )
    with second:
        spend = st.number_input(
            "Spend on this item", min_value=0.0,
            value=float(preset["spend"]), step=100.0,
            disabled=not use_io,
        )

    override = st.checkbox("Override the pass-through ratio")
    ratio_override = None
    if override:
        ratio_override = st.slider(
            "Pass-through per tier", 0.05, 0.95,
            float(SECTORS[sector_key]["tier_ratio"]), 0.01,
        )

    result = None
    try:
        estimate = build_process_estimate(
            preset_name, sector_key,
            tier_frame.to_dict("records"),
            spend=spend if use_io else None,
        )
        bound = io_upper_bound(spend, sector_key) if use_io and spend > 0 else None
        result = correct(estimate, ratio=ratio_override, io_bound=bound)
    except (TruncationError, KeyError) as error:
        st.error(str(error))

    if result:
        first, second, third, fourth = st.columns(4)
        first.metric("Counted", "%.0f kg CO2e" % result["process_total"])
        second.metric("Estimated missing", "%.0f kg CO2e" % result["remainder"])
        third.metric(
            "Best estimate", "%.0f kg CO2e" % result["corrected_total"],
            delta="+%.0f%%" % result["uplift_percent"],
        )
        fourth.metric("Coverage", "%.0f%%" % (result["coverage_ratio"] * 100.0))

        st.markdown("**%s**" % coverage_grade(result).capitalize())

        for insight in get_truncation_insights(result):
            if insight["level"] == "warning":
                st.warning("**%s**\n\n%s" % (insight["title"], insight["body"]))
            else:
                st.info("**%s**\n\n%s" % (insight["title"], insight["body"]))

        for warning in result["warnings"]:
            st.caption("⚠️ %s" % warning)

        st.markdown("#### Where the tail goes")
        rows = modelled_tiers(result, 12)
        figure = go.Figure()
        figure.add_bar(
            x=[row["tier"] for row in rows if not row["modelled"]],
            y=[row["co2e_kg"] for row in rows if not row["modelled"]],
            name="Counted",
        )
        figure.add_bar(
            x=[row["tier"] for row in rows if row["modelled"]],
            y=[row["co2e_kg"] for row in rows if row["modelled"]],
            name="Modelled tail",
        )
        figure.update_layout(
            barmode="stack",
            xaxis_title="Supply chain tier",
            yaxis_title="kg CO2e",
            height=360,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)
        st.caption(
            "The counted bars are measured. The rest is a geometric "
            "extrapolation and is drawn separately for that reason — showing "
            "them identically would be the original problem again in "
            "miniature."
        )

        st.markdown("#### The range, not a point")
        band = pd.DataFrame([
            {
                "Estimate": "Low (fast convergence)",
                "kg CO2e": round(result["corrected_low"], 1),
                "Coverage": "%.0f%%" % (result["coverage_high"] * 100.0),
            },
            {
                "Estimate": "Central",
                "kg CO2e": round(result["corrected_total"], 1),
                "Coverage": "%.0f%%" % (result["coverage_ratio"] * 100.0),
            },
            {
                "Estimate": "High (slow convergence)",
                "kg CO2e": round(result["corrected_high"], 1),
                "Coverage": "%.0f%%" % (result["coverage_low"] * 100.0),
            },
        ])
        st.dataframe(band, use_container_width=True, hide_index=True)
        st.caption(
            "The band comes from the published range for this sector's "
            "pass-through. A midpoint alone would imply a precision the "
            "literature does not have."
        )

        if result["observed_ratios"]:
            st.markdown("#### The tier ratios actually observed")
            st.dataframe(
                pd.DataFrame([{
                    "From tier": row["from_tier"],
                    "To tier": row["to_tier"],
                    "Ratio": round(row["ratio"], 3),
                } for row in result["observed_ratios"]]),
                use_container_width=True,
                hide_index=True,
            )
            if result["ratio_dispersion"]:
                st.caption(
                    "Spread: a factor of %.1f between the largest and "
                    "smallest. The constant-ratio model is a good description "
                    "when this is near 1 and a poor one when it is not."
                    % result["ratio_dispersion"]
                )

        if st.button("Save this correction"):
            try:
                save_correction(user_id, result)
                st.success("Saved.")
            except TruncationError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

with tab_compare:
    st.subheader("Two options with their boundaries put on the same footing")
    st.caption(
        "This is the output that matters most. A ranking that survives "
        "correction is a conclusion about the options. One that flips was an "
        "artefact of how deeply each had been investigated."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Option A**")
        name_a = st.text_input("Name A", value="Replace the equipment")
        sector_a = st.selectbox(
            "Sector A", sorted(SECTORS),
            index=sorted(SECTORS).index("manufacturing"),
            format_func=lambda key: SECTORS[key]["label"],
        )
        direct_a = st.number_input("Direct kg CO2e (A)", value=400.0, step=10.0)
        tier1_a = st.number_input("Tier 1 kg CO2e (A)", value=180.0, step=10.0)
        tier2_a = st.number_input("Tier 2 kg CO2e (A)", value=70.0, step=10.0)
    with right:
        st.markdown("**Option B**")
        name_b = st.text_input("Name B", value="Buy the service instead")
        sector_b = st.selectbox(
            "Sector B", sorted(SECTORS),
            index=sorted(SECTORS).index("services"),
            format_func=lambda key: SECTORS[key]["label"],
        )
        direct_b = st.number_input("Direct kg CO2e (B)", value=600.0, step=10.0)
        tier1_b = st.number_input("Tier 1 kg CO2e (B)", value=0.0, step=10.0)
        tier2_b = st.number_input("Tier 2 kg CO2e (B)", value=0.0, step=10.0)


    def _tiers(direct, first_tier, second_tier):
        rows = [{"tier": 0, "co2e_kg": direct}]
        if first_tier > 0:
            rows.append({"tier": 1, "co2e_kg": first_tier})
            if second_tier > 0:
                rows.append({"tier": 2, "co2e_kg": second_tier})
        return rows


    comparison = None
    try:
        comparison = compare_options([
            build_process_estimate(name_a, sector_a, _tiers(direct_a, tier1_a, tier2_a)),
            build_process_estimate(name_b, sector_b, _tiers(direct_b, tier1_b, tier2_b)),
        ])
    except TruncationError as error:
        st.error(str(error))

    if comparison:
        rows = []
        for row in comparison["results"]:
            rows.append({
                "Option": row["name"],
                "Sector": row["sector_label"],
                "Counted": round(row["process_total"], 1),
                "Missing": round(row["remainder"], 1),
                "Corrected": round(row["corrected_total"], 1),
                "Coverage": "%.0f%%" % (row["coverage_ratio"] * 100.0),
                "Tiers supplied": row["tier_count"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        figure = go.Figure()
        figure.add_bar(
            name="Counted",
            x=[row["name"] for row in comparison["results"]],
            y=[row["process_total"] for row in comparison["results"]],
        )
        figure.add_bar(
            name="Estimated missing",
            x=[row["name"] for row in comparison["results"]],
            y=[row["remainder"] for row in comparison["results"]],
        )
        figure.update_layout(
            barmode="stack",
            yaxis_title="kg CO2e",
            height=360,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)

        st.write(
            "On process data: **%s**. After correction: **%s**."
            % (
                " → ".join(comparison["process_order"]),
                " → ".join(comparison["corrected_order"]),
            )
        )
        if comparison["ranking_flipped"]:
            st.error(comparison["note"])
        else:
            st.success(comparison["note"])

        if comparison["cross_sector"]:
            st.caption(
                "These options sit in different sectors, which is exactly "
                "when an uncorrected comparison is least safe: the two chains "
                "converge at different rates, so they were never truncated by "
                "the same amount."
            )


# ---------------------------------------------------------------------------
# Portfolio and screening
# ---------------------------------------------------------------------------

with tab_portfolio:
    st.subheader("Coverage across a set of estimates")
    st.caption(
        "A portfolio average hides the case that matters: one badly truncated "
        "service line inside an otherwise well-characterised set of physical "
        "products."
    )

    portfolio_frame = st.data_editor(
        pd.DataFrame([
            {"name": "Heat pump", "sector": "manufacturing", "co2e_kg": 650.0},
            {"name": "Consultancy", "sector": "services", "co2e_kg": 600.0},
            {"name": "Freight", "sector": "transport", "co2e_kg": 1200.0},
            {"name": "Cloud hosting", "sector": "ict", "co2e_kg": 1170.0},
        ]),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Line"),
            "sector": st.column_config.SelectboxColumn(
                "Sector", options=sorted(SECTORS)
            ),
            "co2e_kg": st.column_config.NumberColumn("kg CO2e", min_value=0.0),
        },
        key="truncation_portfolio",
    )

    portfolio = None
    try:
        portfolio = portfolio_coverage([
            build_process_estimate(
                row["name"], row["sector"],
                [{"tier": 0, "co2e_kg": row["co2e_kg"]}],
            )
            for row in portfolio_frame.to_dict("records")
            if row.get("name") and (row.get("co2e_kg") or 0) > 0
        ])
    except TruncationError as error:
        st.error(str(error))

    if portfolio:
        first, second, third = st.columns(3)
        first.metric("Reported", "%.0f kg" % portfolio["process_total"])
        second.metric("Best estimate", "%.0f kg" % portfolio["corrected_total"])
        third.metric(
            "Coverage", "%.0f%%" % (portfolio["coverage_ratio"] * 100.0)
        )

        st.warning(
            "The weakest line is **%s** at %.0f%% coverage. The portfolio "
            "average of %.0f%% conceals it, which is why both numbers are "
            "shown."
            % (
                portfolio["worst_covered"],
                portfolio["worst_coverage"] * 100.0,
                portfolio["coverage_ratio"] * 100.0,
            )
        )

        st.dataframe(
            pd.DataFrame([{
                "Line": row["name"],
                "Sector": row["sector_label"],
                "Reported": round(row["process_total"], 1),
                "Best estimate": round(row["corrected_total"], 1),
                "Coverage": "%.0f%%" % (row["coverage_ratio"] * 100.0),
            } for row in portfolio["results"]]),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("What a screening threshold really excludes")
    st.caption(
        "scope3_screener.py drops categories below a share of the total. That "
        "share is a share of an already-truncated total."
    )

    threshold = st.slider("Screening threshold", 0.01, 0.25, 0.05, 0.01)
    screening_sector = st.selectbox(
        "Sector for the screened line", sorted(SECTORS),
        index=sorted(SECTORS).index("services"),
        format_func=lambda key: SECTORS[key]["label"],
        key="truncation_screening_sector",
    )
    screened_total = st.number_input(
        "Reported total for that line", min_value=1.0, value=600.0, step=50.0
    )

    try:
        loss = screening_loss(
            build_process_estimate(
                "Screened line", screening_sector,
                [{"tier": 0, "co2e_kg": screened_total}],
            ),
            threshold,
        )
        first, second, third = st.columns(3)
        first.metric("Cutoff", "%.0f kg CO2e" % loss["apparent_cutoff_kg"])
        second.metric(
            "As written", "%.0f%%" % (loss["threshold_share"] * 100.0)
        )
        third.metric(
            "Of the corrected total",
            "%.1f%%" % (loss["effective_share_of_corrected"] * 100.0),
        )
        st.info(loss["note"])
    except TruncationError as error:
        st.error(str(error))


# ---------------------------------------------------------------------------
# Sectors and saved work
# ---------------------------------------------------------------------------

with tab_sectors:
    st.subheader("How fast each sector's supply chain closes")

    sector_rows = []
    for entry in list_sectors():
        sector_rows.append({
            "Sector": entry["label"],
            "Pass-through": entry["tier_ratio"],
            "Range": "%.2f – %.2f" % (entry["ratio_low"], entry["ratio_high"]),
            "Missed after 2 tiers": "%.0f%%" % (
                entry["truncation_at_two_tiers"] * 100.0
            ),
            "Missed after 3 tiers": "%.0f%%" % (
                entry["truncation_at_three_tiers"] * 100.0
            ),
            "Tiers to 95%": tiers_to_coverage(entry["tier_ratio"], 0.95),
        })
    st.dataframe(
        pd.DataFrame(sector_rows), use_container_width=True, hide_index=True
    )

    st.caption(
        "Read the last two columns together. Construction misses about a "
        "twentieth after three tiers and gets there in seven. Services miss "
        "nearly a quarter after three and need eleven, which is deeper than "
        "any bill of materials in this app goes."
    )

    for entry in list_sectors():
        with st.expander(entry["label"]):
            st.markdown(entry["note"])
            profile = convergence_profile(entry["tier_ratio"])
            st.write(
                "Full-chain multiplier on the direct tier: **%.2f×**. "
                "Tiers to 90%%: %d. To 95%%: %d. To 99%%: %d."
                % (
                    profile["series_multiplier"],
                    profile["tiers_to_90"],
                    profile["tiers_to_95"],
                    profile["tiers_to_99"],
                )
            )

    st.markdown("#### Coverage against tiers counted")
    curve = go.Figure()
    for entry in list_sectors():
        depths = list(range(1, 11))
        curve.add_scatter(
            x=depths,
            y=[
                (1.0 - entry["tier_ratio"] ** depth) * 100.0
                for depth in depths
            ],
            mode="lines",
            name=entry["label"],
        )
    curve.update_layout(
        xaxis_title="Tiers counted",
        yaxis_title="Coverage, %",
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(curve, use_container_width=True)

    st.divider()
    st.subheader("Saved corrections")
    saved = get_corrections(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    for record in saved:
        with st.expander(
            "%s — %.0f kg counted, %.0f kg best estimate"
            % (record["name"], record["process_total"], record["corrected_total"])
        ):
            if record["coverage_ratio"]:
                st.write("Coverage: %.0f%%" % (record["coverage_ratio"] * 100.0))
            st.write("Sector: %s" % SECTORS[record["sector"]]["label"])
            st.write(
                "Ratio: %.2f (%s)"
                % (
                    record["payload"].get("ratio", 0.0),
                    record["payload"].get("ratio_source", "unknown"),
                )
            )
            st.write("Saved: %s" % record["created_at"])
            if st.button("Delete", key="truncation_delete_%s" % record["id"]):
                delete_correction(user_id, record["id"])
                st.rerun()
