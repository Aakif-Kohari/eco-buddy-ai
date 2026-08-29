"""The footprint a person cannot go below.

The fair-share page tells you your ceiling. This one tells you your floor — and
whether there is any space between the two in the circumstances you are
actually in.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.utils.sufficiency_floor import (
    AGENCY_STATES,
    BARRIERS,
    BUILDING_EFFICIENCY,
    DLS_DIMENSIONS,
    REFERENCE_CONTEXT,
    SETTLEMENT_DENSITY,
    SufficiencyError,
    build_context,
    classify_agency,
    consumption_position,
    delete_assessment,
    feasible_corridor,
    get_assessments,
    get_barrier,
    get_dimension,
    get_sufficiency_insights,
    list_barriers,
    list_building_efficiencies,
    list_densities,
    list_dimensions,
    reduction_targets,
    save_assessment,
    sufficiency_floor,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🧭 Sufficiency Floor & the Feasible Corridor</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A fair-share ceiling tells you how much you may emit. It does not tell "
    "you how little you can emit and still have heat, food and a way to reach "
    "work. Without that second number, every reduction target this app "
    "produces is implicitly bounded by zero."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**A floor is a right, not a budget.** This is the footprint a decent life
requires in your circumstances. A footprint below it is very likely energy
poverty or food insecurity, and this page will say so rather than congratulate
you for it.

**The floor is context-dependent, and by a factor of several.** Climate,
building stock, settlement density, grid intensity and household size all move
it. A single global minimum would make a cold-climate renter's unavoidable
heating look like overconsumption, which is the opposite of the point.

**Agency has three states, not two.** Structurally fixed, movable if a stated
barrier is removed, and discretionary. The middle one carries the useful
information: a binary split turns "movable if the landlord agrees" into either
"immovable" or "your choice", and both readings produce bad advice.

**Some targets are arithmetically impossible.** Where a fair-share ceiling falls
below the floor, the gap is in the housing stock, the grid mix or the transport
provision. This page names the dimensions responsible and declines to issue a
target, because presenting a structural problem as a personal shortfall is the
specific harm it exists to prevent.

**Advice is restricted to what can actually move.** Reduction targets are drawn
only from the discretionary and conditionally-movable portions, and each one
says who has to act — sometimes a landlord or a transport authority rather than
you.
        """
    )

st.markdown("---")

st.markdown("### Your circumstances")
c1, c2, c3 = st.columns(3)
with c1:
    hdd = st.number_input(
        "Heating degree days", min_value=0.0,
        value=float(REFERENCE_CONTEXT["heating_degree_days"]), step=100.0,
        help="From src.energy.degree_days.py, or your local climate normals.",
        key="sx_hdd",
    )
    cdd = st.number_input(
        "Cooling degree days", min_value=0.0,
        value=float(REFERENCE_CONTEXT["cooling_degree_days"]), step=50.0,
        key="sx_cdd",
    )
with c2:
    efficiency = st.selectbox(
        "Building efficiency",
        list_building_efficiencies(),
        index=list_building_efficiencies().index("average"),
        format_func=lambda k: BUILDING_EFFICIENCY[k]["label"],
        key="sx_efficiency",
    )
    density = st.selectbox(
        "Settlement density",
        list_densities(),
        index=list_densities().index("urban"),
        format_func=lambda k: SETTLEMENT_DENSITY[k]["label"],
        key="sx_density",
    )
with c3:
    grid = st.number_input(
        "Grid intensity (kg CO2/kWh)", min_value=0.0,
        value=float(REFERENCE_CONTEXT["grid_intensity_kg_per_kwh"]),
        step=0.05, key="sx_grid",
    )
    people = st.number_input(
        "People in the household", min_value=1.0,
        value=float(REFERENCE_CONTEXT["household_size"]), step=1.0,
        key="sx_people",
    )

barriers = st.multiselect(
    "Barriers outside your control",
    list_barriers(),
    format_func=lambda k: BARRIERS[k]["label"],
    help="Each of these moves part of your footprint out of 'your choice' and "
         "into 'movable if someone else acts'.",
    key="sx_barriers",
)
for barrier in barriers:
    st.caption(
        f"**{get_barrier(barrier)['label']}** — {get_barrier(barrier)['note']} "
        f"Removed by {get_barrier(barrier)['removed_by']}."
    )

try:
    context = build_context(
        heating_degree_days=hdd, cooling_degree_days=cdd,
        building_efficiency=efficiency, density=density,
        grid_intensity_kg_per_kwh=grid, household_size=people,
    )
except SufficiencyError as error:
    st.error(str(error))
    st.stop()

floor = sufficiency_floor(context)

st.markdown("---")

tab_floor, tab_corridor, tab_agency, tab_targets, tab_saved = st.tabs(
    [
        "🧱 Your floor",
        "↔️ The corridor",
        "🔓 What can move",
        "🎯 Targets",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# Your floor
# ---------------------------------------------------------------------------
with tab_floor:
    st.markdown("### What a decent life costs where you are")

    m1, m2, m3 = st.columns(3)
    m1.metric("Your floor", f"{floor['floor_kg_co2e']:,.0f} kg CO2e/yr")
    m2.metric(
        "Reference context",
        f"{floor['reference_floor_kg_co2e']:,.0f} kg CO2e/yr",
    )
    m3.metric(
        "Context multiplier",
        f"{floor['context_multiplier']:.2f}×",
        delta=(
            "harder than reference"
            if floor["context_multiplier"] > 1.05 else
            "easier than reference"
            if floor["context_multiplier"] < 0.95 else "about reference"
        ),
        delta_color="off",
    )

    floor_fig = go.Figure()
    floor_fig.add_trace(
        go.Bar(
            name="Reference context",
            x=[row["label"] for row in floor["dimensions"]],
            y=[row["reference_kg_co2e"] for row in floor["dimensions"]],
            marker_color="#9aa5a0",
        )
    )
    floor_fig.add_trace(
        go.Bar(
            name="Your context",
            x=[row["label"] for row in floor["dimensions"]],
            y=[row["floor_kg_co2e"] for row in floor["dimensions"]],
            marker_color="#3d5a80",
        )
    )
    floor_fig.update_layout(
        height=400,
        barmode="group",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO2e per person per year",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(floor_fig, use_container_width=True)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Dimension": row["label"],
                    "Reference": round(row["reference_kg_co2e"]),
                    "Your floor": round(row["floor_kg_co2e"]),
                    "Multiplier": f"{row['context_multiplier']:.2f}×",
                    "Driven by": ", ".join(
                        d.replace("_", " ") for d in row["drivers_applied"]
                    ) or "nothing — context-independent",
                }
                for row in floor["dimensions"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.info(floor["rights_note"])
    st.caption(floor["basis_note"])

    st.markdown("#### The dimensions")
    for key in list_dimensions():
        st.caption(f"**{get_dimension(key)['label']}** — {get_dimension(key)['note']}")


# ---------------------------------------------------------------------------
# The corridor
# ---------------------------------------------------------------------------
with tab_corridor:
    st.markdown("### The space between your floor and your ceiling")
    st.caption(
        "The ceiling comes from the fair-share allocation in "
        "`src.carbon.carbon_budget_equity.py`. This page supplies the floor. The gap "
        "between them is where you actually operate — and sometimes there "
        "isn't one."
    )

    ceiling = st.number_input(
        "Fair-share ceiling (kg CO2e per person per year)",
        min_value=1.0, value=2500.0, step=100.0, key="sx_ceiling",
    )
    actual_total = st.number_input(
        "Your current footprint (kg CO2e per person per year)",
        min_value=0.0, value=6500.0, step=100.0, key="sx_actual_total",
    )

    corridor = feasible_corridor(ceiling, context)
    position = consumption_position(actual_total, ceiling, context)

    if corridor["is_feasible"]:
        st.success(corridor["verdict"])
    else:
        st.error(corridor["verdict"])
        st.warning(corridor["structural_note"])

    corridor_fig = go.Figure()
    corridor_fig.add_trace(
        go.Bar(
            name="Decent living floor",
            y=["Corridor"],
            x=[corridor["floor_kg_co2e"]],
            orientation="h",
            marker_color="#7b506f",
        )
    )
    if corridor["is_feasible"]:
        corridor_fig.add_trace(
            go.Bar(
                name="Feasible corridor",
                y=["Corridor"],
                x=[corridor["corridor_width_kg_co2e"]],
                orientation="h",
                marker_color="#4f772d",
            )
        )
    corridor_fig.add_trace(
        go.Scatter(
            name="Your footprint",
            y=["Corridor"],
            x=[actual_total],
            mode="markers",
            marker=dict(size=18, symbol="diamond", color="#1d3557"),
        )
    )
    corridor_fig.add_vline(
        x=ceiling, line_dash="dash", line_color="#c1666b",
        annotation_text="fair-share ceiling",
    )
    corridor_fig.update_layout(
        height=250,
        barmode="stack",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="kg CO2e per person per year",
        legend=dict(orientation="h", y=1.3),
    )
    st.plotly_chart(corridor_fig, use_container_width=True)

    if position["position"] == "below_floor":
        st.error(position["verdict"])
        st.warning(position["no_congratulation_note"])
    elif position["position"] == "within_corridor":
        st.success(position["verdict"])
    else:
        st.info(position["verdict"])

    if not corridor["is_feasible"] and corridor["responsible_dimensions"]:
        st.markdown("#### What is pushing the floor above the ceiling")
        st.caption(
            "These are the dimensions your circumstances inflate. Each is "
            "addressed by changing a building, a grid or a transport network — "
            "not by the household trying harder."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Dimension": row["label"],
                        "Reference": round(row["reference_kg_co2e"]),
                        "Your floor": round(row["floor_kg_co2e"]),
                        "Added by context": round(row["context_excess_kg_co2e"]),
                        "Share of the gap": f"{row['share_of_overshoot']:.0%}",
                    }
                    for row in corridor["responsible_dimensions"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# What can move
# ---------------------------------------------------------------------------
with tab_agency:
    st.markdown("### Which parts of your footprint you can actually change")

    st.caption(
        "Enter your footprint by dimension. Everything up to the floor is a "
        "need. What sits above it is yours to change — unless a barrier holds "
        "it, in which case this page says who could release it."
    )

    actual = {}
    cols = st.columns(3)
    defaults = {
        "nutrition": 900.0,
        "shelter_thermal": 1800.0,
        "shelter_construction": 200.0,
        "water_sanitation": 60.0,
        "clothing": 200.0,
        "healthcare": 180.0,
        "education": 90.0,
        "communication": 120.0,
        "mobility_access": 1400.0,
    }
    for i, key in enumerate(list_dimensions()):
        with cols[i % 3]:
            actual[key] = st.number_input(
                f"{DLS_DIMENSIONS[key]['label']} (kg CO2e/yr)",
                min_value=0.0, value=defaults.get(key, 100.0), step=25.0,
                key=f"sx_actual_{key}",
            )

    classification = classify_agency(actual, context, barriers)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total", f"{classification['actual_kg_co2e']:,.0f} kg")
    a2.metric(
        "Structurally fixed",
        f"{classification['totals']['structurally_fixed']:,.0f} kg",
    )
    a3.metric(
        "Movable if a barrier goes",
        f"{classification['totals']['conditionally_movable']:,.0f} kg",
    )
    a4.metric(
        "Discretionary",
        f"{classification['totals']['discretionary']:,.0f} kg",
        delta=f"{classification['discretionary_share']:.0%} of the total",
        delta_color="off",
    )

    agency_fig = go.Figure()
    for state, colour in (
        ("structurally_fixed", "#7b506f"),
        ("conditionally_movable", "#e0a458"),
        ("discretionary", "#4f772d"),
    ):
        agency_fig.add_trace(
            go.Bar(
                name=AGENCY_STATES[state]["label"],
                x=[row["label"] for row in classification["dimensions"]],
                y=[row[state] for row in classification["dimensions"]],
                marker_color=colour,
            )
        )
    agency_fig.update_layout(
        height=420,
        barmode="stack",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO2e per person per year",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(agency_fig, use_container_width=True)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Dimension": row["label"],
                    "Actual": round(row["actual_kg_co2e"]),
                    "Floor": round(row["floor_kg_co2e"]),
                    "Fixed": round(row["structurally_fixed"]),
                    "Conditional": round(row["conditionally_movable"]),
                    "Discretionary": round(row["discretionary"]),
                    "Barriers": ", ".join(
                        b["label"] for b in row["active_barriers"]
                    ) or "—",
                    "Below floor": "Yes" if row["under_provided"] else "",
                }
                for row in classification["dimensions"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.info(classification["three_states_note"])

    for state in AGENCY_STATES:
        st.caption(f"**{AGENCY_STATES[state]['label']}** — {AGENCY_STATES[state]['note']}")

    st.markdown("#### What this is telling you")
    for insight in get_sufficiency_insights(classification, corridor):
        st.markdown(f"- {insight}")

    with st.form("save_sufficiency_assessment"):
        name = st.text_input("Save this as", value="")
        if st.form_submit_button("Save") and name.strip():
            try:
                save_assessment(user_id, name, classification)
                st.success(f"Saved '{name.strip()}'.")
            except SufficiencyError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------
with tab_targets:
    st.markdown("### Where a reduction could come from, and who has to act")

    targets = reduction_targets(classification, ceiling)

    t1, t2, t3 = st.columns(3)
    t1.metric(
        "Required reduction",
        f"{targets['required_reduction_kg_co2e']:,.0f} kg",
    )
    t2.metric(
        "You can move",
        f"{targets['available_discretionary_kg_co2e']:,.0f} kg",
    )
    t3.metric(
        "Someone else can unlock",
        f"{targets['available_conditional_kg_co2e']:,.0f} kg",
    )

    if targets["required_reduction_kg_co2e"] == 0:
        st.success(targets["verdict"])
    elif targets["achievable_by_household_alone"]:
        st.success(targets["verdict"])
    elif targets["achievable_at_all"]:
        st.warning(targets["verdict"])
    else:
        st.error(targets["verdict"])

    if targets["targets"]:
        target_fig = go.Figure(
            go.Bar(
                x=[t["available_kg_co2e"] for t in targets["targets"]],
                y=[
                    f"{t['label']} ({t['agency'].replace('_', ' ')})"
                    for t in targets["targets"]
                ],
                orientation="h",
                marker_color=[
                    "#4f772d" if t["agency"] == "discretionary" else "#e0a458"
                    for t in targets["targets"]
                ],
            )
        )
        target_fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="kg CO2e available",
        )
        st.plotly_chart(target_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Dimension": t["label"],
                        "Agency": AGENCY_STATES[t["agency"]]["label"],
                        "Available (kg)": round(t["available_kg_co2e"]),
                        "Who has to act": t["who_acts"],
                        "Conditional on": t["condition"] or "—",
                    }
                    for t in targets["targets"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "Nothing in this footprint sits above the decent living floor, so "
            "there is no legitimate reduction target to offer."
        )

    if targets["unmet_kg_co2e"] > 0:
        st.error(
            f"{targets['unmet_kg_co2e']:,.0f} kg CO2e of the required "
            f"reduction cannot be found anywhere except inside the decent "
            f"living floor. That residual is not a target and this page will "
            f"not present it as one."
        )

    st.info(targets["restriction_note"])


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved assessments")
    saved = get_assessments(user_id)
    if not saved:
        st.info("Nothing saved yet. Save an assessment from the third tab.")
    else:
        for record in saved:
            with st.expander(
                f"{record['name']} — {record['actual_kg_co2e']:,.0f} kg against "
                f"a {record['floor_kg_co2e']:,.0f} kg floor"
            ):
                payload = record["payload"]
                st.write(
                    f"Discretionary: "
                    f"{record['discretionary_kg_co2e']:,.0f} kg "
                    f"({payload.get('discretionary_share', 0):.0%} of the total)"
                )
                saved_barriers = payload.get("barriers", [])
                st.write(
                    "Barriers: "
                    + (
                        ", ".join(
                            BARRIERS.get(b, {}).get("label", b)
                            for b in saved_barriers
                        )
                        if saved_barriers else "none recorded"
                    )
                )
                if payload.get("under_provided_dimensions"):
                    st.warning(
                        "Below the floor on: "
                        + ", ".join(
                            DLS_DIMENSIONS.get(d, {}).get("label", d)
                            for d in payload["under_provided_dimensions"]
                        )
                        + ". A welfare signal, not a saving."
                    )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Dimension": DLS_DIMENSIONS.get(
                                    row["dimension"], {}
                                ).get("label", row["dimension"]),
                                "Actual": round(row["actual_kg_co2e"]),
                                "Floor": round(row["floor_kg_co2e"]),
                                "Discretionary": round(row["discretionary"]),
                            }
                            for row in payload.get("dimensions", [])
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(f"Saved {record['created_at']}")
                if st.button("Delete", key=f"sx_del_{record['id']}"):
                    if delete_assessment(user_id, record["id"]):
                        st.success("Deleted.")
                        st.rerun()
