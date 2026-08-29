"""Whose footprint it is.

Every per-person figure in this app is a household total divided by headcount.
This page shows what that division gets wrong, who it penalises, and what the
answer looks like once sharing, age and decision authority are accounted for.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.lifestyle.household_allocation import (
    ATTRIBUTION_BASES,
    CATEGORIES,
    DEFAULT_SCALE,
    EQUIVALENCE_SCALES,
    REFERENCE_HOUSEHOLD,
    AllocationError,
    build_member,
    compare_bases,
    composition_adjusted_benchmark,
    delete_allocation,
    equivalent_adults,
    fair_share_reallocation,
    get_allocation_insights,
    get_allocations,
    get_category,
    get_scale,
    list_categories,
    list_scales,
    per_person_footprint,
    reconcile_joint_activities,
    save_allocation,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🏠 Household Allocation</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "One person heats a whole dwelling. Four people share it. Dividing a "
    "household footprint by headcount charges that difference to the person "
    "living alone and calls it behaviour."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**Equal division is a choice, and not a neutral one.** Household footprint does
not scale linearly with occupancy. Dividing as though it does makes a person
living alone look profligate and a member of a large household look virtuous,
when most of the difference is arithmetic.

**Sharing is not uniform across categories.** Heating is close to a household
public good — the dwelling is heated whether one person or four are in it. Food
is close to purely private. Applying one scale to both gets both wrong, in
opposite directions, so each category here carries its own elasticity with a
note saying why.

**Which scale you pick is a value judgement.** It changes the answer materially.
This page offers four, including plain per-capita, so the app's current
behaviour is visible as a choice rather than as the absence of one.

**Consumption, benefit and control are three different questions.** A child
consumes some heating, benefits from all of it, and controls none of it. All
three are shown. Reduction advice should follow control; benchmarking should
follow consumption.

**Two people in a car both log the trip.** The household total is right and the
sum of individual footprints is inflated by exactly the shared portion. Nothing
else in this app catches that.

**Fair share is redistributed, not increased.** The reallocation is calibrated
against a reference household so switching scales changes how the budget is
distributed and not how much of it there is. Anything else would be a much
larger claim than this page is making.
        """
    )

st.markdown("---")

DEFAULT_MEMBERS = pd.DataFrame([
    {"Name": "Sam", "Age": 41, "Days present": 365,
     "Heating say": 0.8, "Transport say": 0.7},
    {"Name": "Rowan", "Age": 39, "Days present": 365,
     "Heating say": 0.2, "Transport say": 0.3},
    {"Name": "Kit", "Age": 11, "Days present": 365,
     "Heating say": 0.0, "Transport say": 0.0},
    {"Name": "Wren", "Age": 7, "Days present": 182,
     "Heating say": 0.0, "Transport say": 0.0},
])

st.markdown("### Who lives here")
st.caption(
    "Days present covers visitors, part-time residents and shared custody — "
    "all common, and none of them expressible as a headcount. The 'say' "
    "columns are decision authority over that category, between 0 and 1."
)

member_edit = st.data_editor(
    DEFAULT_MEMBERS, num_rows="dynamic", width="stretch", key="hh_members"
)

scale = st.radio(
    "Equivalence scale",
    list_scales(),
    index=list_scales().index(DEFAULT_SCALE),
    format_func=lambda k: EQUIVALENCE_SCALES[k]["label"],
    horizontal=False,
    key="hh_scale",
)
st.caption(get_scale(scale)["note"])

members = []
errors = []
for _, row in member_edit.iterrows():
    name = str(row.get("Name") or "").strip()
    if not name:
        continue
    agency = {}
    heating = row.get("Heating say")
    transport = row.get("Transport say")
    if heating is not None and not pd.isna(heating):
        agency["space_heating"] = float(heating)
    if transport is not None and not pd.isna(transport):
        agency["personal_transport"] = float(transport)
    try:
        members.append(build_member(
            name,
            float(row.get("Age") or 0),
            person_days=float(row.get("Days present") or 365),
            agency=agency,
        ))
    except AllocationError as error:
        errors.append(f"{name}: {error}")

for message in errors:
    st.error(message)

if not members:
    st.info("Add at least one household member.")
    st.stop()

st.markdown("### What the household emits")
DEFAULT_FOOTPRINT = pd.DataFrame([
    {"Category": key, "kg CO2e / year": value}
    for key, value in (
        ("space_heating", 3200.0), ("lighting_and_standby", 450.0),
        ("appliances", 600.0), ("water", 300.0), ("food", 2400.0),
        ("personal_transport", 2800.0), ("goods_and_clothing", 1400.0),
        ("waste", 320.0), ("digital", 260.0),
    )
])
footprint_edit = st.data_editor(
    DEFAULT_FOOTPRINT,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "Category": st.column_config.SelectboxColumn(
            "Category", options=list_categories(), required=True,
        ),
    },
    key="hh_footprint",
)

footprint = {}
for _, row in footprint_edit.iterrows():
    category = row.get("Category")
    value = row.get("kg CO2e / year")
    if category not in CATEGORIES or value is None or pd.isna(value):
        continue
    footprint[category] = float(value)

if not footprint:
    st.info("Add at least one footprint category.")
    st.stop()

try:
    sizing = equivalent_adults(members, scale)
    division = per_person_footprint(footprint, members, scale)
    comparison = compare_bases(footprint, members, scale)
except AllocationError as error:
    st.error(str(error))
    st.stop()

st.markdown("---")

tab_divide, tab_share, tab_who, tab_double, tab_bench, tab_saved = st.tabs(
    [
        "➗ The division",
        "🧩 What is shared",
        "👥 Whose is it",
        "🔁 Double counting",
        "📐 Fair comparison",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# The division
# ---------------------------------------------------------------------------
with tab_divide:
    st.markdown("### Three answers to 'what is my footprint'")

    d1, d2, d3 = st.columns(3)
    d1.metric(
        "Per capita",
        f"{division['per_capita']:,.0f} kg",
        help="Household total divided by headcount. What this app does now.",
    )
    d2.metric(
        "Per equivalent adult",
        f"{division['per_equivalent_adult']:,.0f} kg",
        delta=f"{division['difference_share'] * 100:+.0f}%",
        delta_color="off",
    )
    d3.metric(
        "Comparable footprint",
        f"{division['comparable_footprint']:,.0f} kg",
        help="Each category divided by its own equivalised size. The figure "
             "to compare against households of a different composition.",
    )

    st.markdown(
        f"Headcount **{division['headcount']:.1f}**, equivalent adults "
        f"**{division['equivalent_adults']:.2f}** — economies of scale of "
        f"**{sizing['economies_of_scale'] * 100:.0f}%** under "
        f"{get_scale(scale)['label']}."
    )

    scale_rows = []
    for key in list_scales():
        try:
            other = per_person_footprint(footprint, members, key)
        except AllocationError:
            continue
        scale_rows.append({
            "Scale": EQUIVALENCE_SCALES[key]["label"],
            "Equivalent adults": other["equivalent_adults"],
            "Per capita": other["per_capita"],
            "Per equivalent adult": other["per_equivalent_adult"],
            "Comparable": other["comparable_footprint"],
        })
    st.dataframe(pd.DataFrame(scale_rows), width="stretch", hide_index=True)
    st.caption(
        "The spread across these rows is the size of the value judgement. A "
        "household judged differently under a different scale is entitled to "
        "know that, which is why none of them is buried in a constant."
    )

    st.markdown("#### Findings")
    for line in get_allocation_insights(division, comparison):
        st.markdown(f"- {line}")


# ---------------------------------------------------------------------------
# What is shared
# ---------------------------------------------------------------------------
with tab_share:
    st.markdown("### How much of each category a second person adds")

    rows = []
    for row in division["categories"]:
        rows.append({
            "Category": row["label"],
            "Household total": row["household_total"],
            "Sharing elasticity": row["sharing_elasticity"],
            "Divides across": row["units"],
            "Per equivalent adult": row["per_equivalent_adult"],
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    units_fig = go.Figure()
    units_fig.add_trace(go.Bar(
        name="Headcount",
        x=[row["label"] for row in division["categories"]],
        y=[division["headcount"]] * len(division["categories"]),
        marker_color="#b4553f",
    ))
    units_fig.add_trace(go.Bar(
        name="Actual divisor",
        x=[row["label"] for row in division["categories"]],
        y=[row["units"] for row in division["categories"]],
        marker_color="#2e7d63",
    ))
    units_fig.update_layout(
        barmode="group", height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Units the category divides across",
    )
    st.plotly_chart(units_fig, width="stretch")
    st.caption(
        "The red bar is what per-capita division assumes. The gap on heating "
        "is the single largest error in the current approach: a dwelling is "
        "heated whether one person or four are in it."
    )

    st.markdown("#### Why each elasticity is what it is")
    for key in list_categories():
        meta = get_category(key)
        st.markdown(
            f"**{meta['label']}** — elasticity "
            f"{meta['sharing_elasticity']:.2f}"
        )
        st.caption(meta["note"])


# ---------------------------------------------------------------------------
# Whose is it
# ---------------------------------------------------------------------------
with tab_who:
    st.markdown("### Consumption, benefit and control")

    if comparison["bases_disagree"]:
        st.warning(
            f"The three bases disagree by up to "
            f"{comparison['largest_spread']:,.0f} kg CO2e for one member — "
            f"{comparison['largest_spread_share'] * 100:.0f}% of the household "
            f"total. Picking one silently is how this goes wrong."
        )
    else:
        st.info(
            "The three bases agree here. This household has no dependants and "
            "no concentration of decision authority, so the choice would not "
            "have mattered."
        )

    basis_fig = go.Figure()
    palette = {"consumption": "#2e7d63", "benefit": "#5b6b78",
               "control": "#c0873f"}
    for basis in ATTRIBUTION_BASES:
        basis_fig.add_trace(go.Bar(
            name=ATTRIBUTION_BASES[basis]["label"],
            x=[row["name"] for row in comparison["members"]],
            y=[row[basis] for row in comparison["members"]],
            marker_color=palette[basis],
        ))
    basis_fig.update_layout(
        barmode="group", height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="kg CO2e attributed",
    )
    st.plotly_chart(basis_fig, width="stretch")

    st.dataframe(
        pd.DataFrame([
            {
                "Member": row["name"],
                "Consumption": row["consumption"],
                "Benefit": row["benefit"],
                "Control": row["control"],
                "Spread": row["spread"],
            }
            for row in comparison["members"]
        ]),
        width="stretch", hide_index=True,
    )

    for basis in ATTRIBUTION_BASES:
        st.markdown(f"**{ATTRIBUTION_BASES[basis]['label']}**")
        st.caption(ATTRIBUTION_BASES[basis]["note"])

    unattributed = comparison["results"]["control"]["unattributed_categories"]
    if unattributed:
        names = ", ".join(
            CATEGORIES[category]["label"] for category in unattributed
        )
        st.error(
            f"Nobody in this household holds decision authority over: {names}. "
            f"That is a real answer rather than missing data — reduction "
            f"advice about it belongs with a landlord or a provider, not here."
        )


# ---------------------------------------------------------------------------
# Double counting
# ---------------------------------------------------------------------------
with tab_double:
    st.markdown("### Activities logged by more than one member")
    st.caption(
        "Tick *shared* where the same real activity was logged by several "
        "people — one car journey, one flight, one household meal."
    )

    default_logs = pd.DataFrame([
        {"Member": "Sam", "Activity": "school run",
         "kg CO2e": 180.0, "Shared": True},
        {"Member": "Rowan", "Activity": "school run",
         "kg CO2e": 180.0, "Shared": True},
        {"Member": "Sam", "Activity": "commute",
         "kg CO2e": 600.0, "Shared": False},
        {"Member": "Rowan", "Activity": "holiday flight",
         "kg CO2e": 900.0, "Shared": True},
        {"Member": "Sam", "Activity": "holiday flight",
         "kg CO2e": 900.0, "Shared": True},
    ])
    log_edit = st.data_editor(
        default_logs, num_rows="dynamic", width="stretch", key="hh_logs"
    )

    logs = []
    for _, row in log_edit.iterrows():
        member = str(row.get("Member") or "").strip()
        activity = str(row.get("Activity") or "").strip()
        amount = row.get("kg CO2e")
        if not member or not activity or amount is None or pd.isna(amount):
            continue
        logs.append({
            "member": member,
            "activity": activity,
            "emissions": float(amount),
            "shared": bool(row.get("Shared")),
        })

    if not logs:
        st.info("Add at least one logged activity.")
        reconciliation = None
    else:
        try:
            reconciliation = reconcile_joint_activities(logs)
        except AllocationError as error:
            st.error(str(error))
            reconciliation = None

    if reconciliation:
        r1, r2, r3 = st.columns(3)
        r1.metric("Sum of member logs",
                  f"{reconciliation['raw_sum']:,.0f} kg")
        r2.metric("Reconciled household total",
                  f"{reconciliation['reconciled_total']:,.0f} kg")
        r3.metric(
            "Counted twice",
            f"{reconciliation['double_counted']:,.0f} kg",
            delta=f"{reconciliation['double_counted_share'] * 100:.0f}% of the "
                  f"raw sum",
            delta_color="off",
        )

        st.dataframe(
            pd.DataFrame([
                {
                    "Activity": row["activity"],
                    "Logged by": ", ".join(row["logged_by"]),
                    "Reported": row["reported"],
                    "Counted": row["counted"],
                    "Double counted": row["double_counted"],
                }
                for row in reconciliation["activities"]
            ]),
            width="stretch", hide_index=True,
        )

        if reconciliation["double_counted"] > 0:
            st.warning(
                f"The household total is right. The sum of individual "
                f"footprints is inflated by "
                f"{reconciliation['double_counted']:,.0f} kg CO2e. "
                f"boundary_reconciliation.py catches this between modules; "
                f"nothing catches it between people."
            )
        else:
            st.success("No activity is counted more than once.")


# ---------------------------------------------------------------------------
# Fair comparison
# ---------------------------------------------------------------------------
with tab_bench:
    st.markdown("### Against a household of your own shape")

    reference_total = st.number_input(
        "Reference footprint per equivalent adult (kg CO2e/yr)",
        min_value=100.0, value=5586.0, step=100.0,
        help="A national or regional average expressed per equivalent adult.",
        key="hh_reference",
    )
    weights = {
        key: footprint.get(key, 0.0) for key in footprint
    }
    weight_total = sum(weights.values()) or 1.0
    reference = {
        key: reference_total * value / weight_total
        for key, value in weights.items()
    }

    try:
        benchmark = composition_adjusted_benchmark(
            footprint, members, reference, scale
        )
        fair = fair_share_reallocation(2500.0, members, scale)
    except AllocationError as error:
        st.error(str(error))
    else:
        b1, b2, b3 = st.columns(3)
        b1.metric("Your household",
                  f"{benchmark['actual_total']:,.0f} kg")
        b2.metric("Expected for this composition",
                  f"{benchmark['expected_for_this_composition']:,.0f} kg")
        b3.metric("Per-capita comparison",
                  f"{benchmark['expected_per_capita_comparison']:,.0f} kg")

        if benchmark["verdict_flips"]:
            st.error(
                f"Against a national per-capita average this household reads "
                f"as **{benchmark['naive_verdict']}**. Against a household of "
                f"the same composition it reads as "
                f"**{benchmark['adjusted_verdict']}**. Only the second one is "
                f"about anything this household did."
            )

        split_fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Per-capita expectation", "Composition", "Behaviour",
               "Your household"],
            y=[
                benchmark["expected_per_capita_comparison"],
                benchmark["composition_effect"],
                benchmark["behaviour_effect"],
                benchmark["actual_total"],
            ],
            connector={"line": {"color": "#9aa5a0"}},
            decreasing={"marker": {"color": "#2e7d63"}},
            increasing={"marker": {"color": "#b4553f"}},
            totals={"marker": {"color": "#5b6b78"}},
        ))
        split_fig.update_layout(
            height=420, margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="kg CO2e", showlegend=False,
        )
        st.plotly_chart(split_fig, width="stretch")
        st.caption(
            "Only the behaviour bar is something this household could act on. "
            "Reporting the two together as a single verdict is what every "
            "benchmarking surface in this app currently does."
        )

        st.markdown("#### Fair share on equivalent adults")
        f1, f2, f3 = st.columns(3)
        f1.metric("By headcount", f"{fair['naive_budget']:,.0f} kg")
        f2.metric("By equivalent adults",
                  f"{fair['adjusted_budget']:,.0f} kg",
                  delta=f"{fair['difference_share'] * 100:+.0f}%")
        f3.metric("Equivalent adults", f"{fair['equivalent_adults']:.2f}")
        st.caption(
            f"Calibrated so a reference household of "
            f"{len(REFERENCE_HOUSEHOLD)} (two adults, two children) receives "
            f"the same budget either way. The reallocation redistributes; it "
            f"does not change the total handed out."
        )


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Save this allocation")
    name = st.text_input("Name", value="Our household", key="hh_save_name")
    if st.button("Save", key="hh_save"):
        try:
            save_allocation(user_id, name, division)
            st.success("Saved.")
        except AllocationError as error:
            st.error(str(error))

    st.markdown("---")
    saved = get_allocations(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for entry in saved:
            with st.container(border=True):
                head, action = st.columns([5, 1])
                with head:
                    st.markdown(f"**{entry['name']}** · {entry['created_at']}")
                    st.caption(
                        f"{EQUIVALENCE_SCALES.get(entry['scale'], {}).get('label', entry['scale'])} · "
                        f"per capita {entry['per_capita']:,.0f} kg · "
                        f"per equivalent adult "
                        f"{entry['per_equivalent_adult']:,.0f} kg"
                    )
                with action:
                    if st.button("Delete", key=f"hh_del_{entry['id']}"):
                        if delete_allocation(user_id, entry["id"]):
                            st.rerun()

st.markdown("---")
st.caption(
    "Method: OECD and square-root equivalence scales with per-category sharing "
    "elasticities, three attribution bases, occupancy weighting by person-days. "
    "Related: src.lifestyle.household.py, src.carbon.carbon_budget_equity.py, "
    "src.carbon.carbon_benchmarking.py, src.utils.boundary_reconciliation.py."
)
