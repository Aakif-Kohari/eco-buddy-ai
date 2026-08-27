"""Co-product allocation: the choice behind every food and material factor.

A litre of milk and a kilogram of beef come out of the same herd. The split
between them was a methodological choice, not a measurement. This page makes
that choice visible and lets you change it.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.lca_allocation import (
    ALL_BASES,
    BASIS_LABELS,
    DISPLACED_INTENSITIES,
    DISPLACED_INTENSITY_RANGES,
    ECONOMIC,
    MASS,
    MATERIALS,
    PARTITIONING_BASES,
    PROCESSES,
    RECYCLING_METHOD_LABELS,
    RECYCLING_METHODS,
    AllocationError,
    allocate,
    chain,
    chain_across_bases,
    compare_bases,
    compare_recycling_methods,
    delete_study,
    displacement_sensitivity,
    get_allocation_insights,
    get_material,
    get_process,
    get_studies,
    list_materials,
    list_outputs,
    list_processes,
    recycling_allocation,
    save_study,
    spread_report,
    system_expansion,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⚖️ Allocation Choices</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A dairy herd produces milk **and** beef. A wheat crop produces grain "
    "**and** straw. A refinery produces four things from one barrel. In each "
    "case one process emits, and the burden has to be divided between outputs "
    "that were made together and cannot be made separately."
)

with st.expander("There is no physically correct division"):
    st.markdown(
        """
There are conventions, and they disagree — often by more than the differences
people use these numbers to argue about.

- **Mass.** Simple, and it says a kilogram of bitumen costs the same to make as
  a kilogram of petrol.
- **Energy content.** Sensible for fuels, and undefined the moment an output has
  no energy function worth speaking of. Hides, for instance.
- **Economic value.** Usually the most defensible, and it moves with prices, and
  it breaks when a co-product is a disposal cost rather than a product.
- **System expansion.** Doesn't divide at all — credits each co-product with
  whatever it displaces on the market. The result can come out **below zero**,
  which is the method saying the co-products do more good elsewhere than the
  process does harm. It also makes the answer a function of market assumptions,
  so it is never mixed into an allocated total here.

The standards prefer a physical relationship where one exists. Where one does
not, the choice is a judgement — and it should be stated rather than absorbed
into a number that looks like a measurement.
"""
    )

tab_process, tab_expansion, tab_chain, tab_recycling, tab_saved = st.tabs(
    ["One process", "System expansion", "Through a chain", "Recycling", "Saved"]
)


with tab_process:
    st.subheader("Pick a process")
    process = st.selectbox(
        "Process", options=list_processes(),
        format_func=lambda key: PROCESSES[key]["label"],
    )
    entry = get_process(process)
    st.caption(entry["note"])

    comparison = compare_bases(process)
    st.metric("Burden to divide", f"{entry['burden_kg_co2e']:,.0f} kg CO2e")

    if comparison["unavailable_bases"]:
        for basis, reason in comparison["unavailable_bases"].items():
            if basis in PARTITIONING_BASES:
                st.warning(reason)

    rows = []
    for row in comparison["rows"]:
        record = {"Output": row["label"], "Mass (kg)": row["mass_kg"]}
        for basis in PARTITIONING_BASES:
            if basis in row["per_kg"]:
                record[BASIS_LABELS[basis]] = round(row["per_kg"][basis], 4)
        if row.get("ratio"):
            record["Highest ÷ lowest"] = row["ratio"]
        rows.append(record)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("kg CO2e per kg of that output, under each basis.")

    plot_rows = []
    for row in comparison["rows"]:
        for basis, value in row["per_kg"].items():
            plot_rows.append({
                "Output": row["label"],
                "Basis": BASIS_LABELS[basis],
                "kg CO2e per kg": value,
            })
    if plot_rows:
        basis_chart = px.bar(
            pd.DataFrame(plot_rows), x="Output", y="kg CO2e per kg",
            color="Basis", barmode="group",
        )
        basis_chart.update_layout(
            height=440, margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(basis_chart, use_container_width=True)
        st.caption(
            "The bars for one output are the same physical system measured the "
            "same way. Only the convention differs."
        )

    report = spread_report(process)
    if report["widest"]:
        st.error(
            f"**{report['widest']}** carries **{report['widest_ratio']:.2f}×** "
            f"as much burden on {report['widest_low_basis'].lower()} as on "
            f"{report['widest_high_basis'].lower()}. That ratio is the honest "
            "uncertainty on its footprint, and no amount of better measurement "
            "will narrow it — it is not a measurement problem."
        )

    st.markdown("#### What this says")
    for line in get_allocation_insights(comparison):
        st.markdown(f"- {line}")

    st.markdown("#### The division itself")
    basis = st.radio(
        "Basis", options=comparison["available_bases"],
        format_func=lambda key: BASIS_LABELS[key], horizontal=True,
    )
    try:
        allocation = allocate(process, basis)
    except AllocationError as exc:
        st.error(str(exc))
    else:
        share_chart = px.pie(
            pd.DataFrame(allocation["lines"]), names="label", values="share",
            hole=0.45,
        )
        share_chart.update_layout(
            height=380, margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(share_chart, use_container_width=True)
        st.success(
            f"Allocated {allocation['allocated_total']:,.2f} kg against "
            f"{allocation['burden_kg_co2e']:,.2f} kg available — the shares sum "
            "to exactly the burden, which is checked rather than assumed."
        )

        with st.form("save_allocation_study"):
            name = st.text_input("Name this study", value=entry["label"])
            if st.form_submit_button("Save study"):
                if not name.strip():
                    st.error("Give the study a name.")
                elif save_study(user_id, name.strip(), process, basis, comparison):
                    st.success("Saved.")
                else:
                    st.error("Could not save the study.")


with tab_expansion:
    st.subheader("Credit instead of divide")
    st.markdown(
        "System expansion puts the whole burden on the primary output, less "
        "the emissions of whatever each co-product displaces on the market. "
        "That makes it the only method whose answer depends on something "
        "outside the process."
    )

    expansion_columns = st.columns(2)
    with expansion_columns[0]:
        expansion_process = st.selectbox(
            "Process", options=list_processes(),
            format_func=lambda key: PROCESSES[key]["label"],
            key="expansion_process",
        )
    with expansion_columns[1]:
        primary = st.selectbox(
            "Primary output", options=list_outputs(expansion_process),
            format_func=lambda key: (
                PROCESSES[expansion_process]["outputs"][key]["label"]
            ),
        )

    st.markdown("**Intensity of what the co-products displace**")
    overrides = {}
    intensity_columns = st.columns(min(3, len(DISPLACED_INTENSITIES)))
    for n, (product, central) in enumerate(DISPLACED_INTENSITIES.items()):
        bounds = DISPLACED_INTENSITY_RANGES[product]
        with intensity_columns[n % len(intensity_columns)]:
            overrides[product] = st.slider(
                product.replace("_", " ").title(),
                min_value=float(bounds["low"]),
                max_value=float(bounds["high"]),
                value=float(central),
                step=(bounds["high"] - bounds["low"]) / 40.0,
                key=f"intensity_{product}",
            )

    try:
        result = system_expansion(expansion_process, primary, overrides)
    except AllocationError as exc:
        st.error(str(exc))
        st.stop()

    a, b, c = st.columns(3)
    a.metric("Process burden", f"{result['burden_kg_co2e']:,.0f} kg")
    b.metric("Credited away", f"{result['total_credit_kg_co2e']:,.0f} kg")
    c.metric(
        f"Left with {result['primary_label']}",
        f"{result['net_kg_co2e']:,.0f} kg",
    )

    if result["is_negative"]:
        st.warning(
            "This comes out **below zero**. The method is saying the "
            "co-products displace more emissions elsewhere than this process "
            "produces. That is a real result of the method — not an error — "
            "and it is exactly why it cannot be added to an allocated total."
        )

    if result["credits"]:
        st.dataframe(
            pd.DataFrame(result["credits"])[[
                "label", "displaces", "displaced_intensity",
                "displacement_ratio", "credit_kg_co2e"
            ]].rename(columns={
                "label": "Co-product", "displaces": "Displaces",
                "displaced_intensity": "Its intensity",
                "displacement_ratio": "Ratio", "credit_kg_co2e": "Credit",
            }),
            use_container_width=True, hide_index=True,
        )
    if result["uncredited_outputs"]:
        st.caption(
            f"No credit taken for: {', '.join(result['uncredited_outputs'])} — "
            "nothing stated that they displace."
        )

    st.markdown("#### Across the plausible range")
    sensitivity = displacement_sensitivity(expansion_process, primary)
    sensitivity_frame = pd.DataFrame(sensitivity["rows"])
    range_chart = go.Figure()
    range_chart.add_trace(go.Bar(
        x=sensitivity_frame["level"], y=sensitivity_frame["per_kg"],
        marker_color=[
            "#b45309" if value < 0 else "#0f766e"
            for value in sensitivity_frame["per_kg"]
        ],
    ))
    range_chart.add_hline(y=0, line_dash="dot")
    range_chart.update_layout(
        height=380, yaxis_title="kg CO2e per kg of primary output",
        xaxis_title="Displaced-product intensity assumption",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(range_chart, use_container_width=True)

    if sensitivity["changes_sign"]:
        st.error(
            f"Between the low and high assumptions this footprint runs from "
            f"**{sensitivity['high']:+.3f}** to **{sensitivity['low']:+.3f}** kg "
            "per kg — it changes sign. Same process, same physics, same method. "
            "Only the assumption about what the co-product displaces has moved."
        )
    else:
        st.caption(
            f"Between the low and high assumptions this runs from "
            f"{sensitivity['low']:.3f} to {sensitivity['high']:.3f} kg per kg."
        )


with tab_chain:
    st.subheader("Through more than one step")
    st.markdown(
        "Milk becomes cheese and whey. Allocate at the herd and again at the "
        "dairy, and the choices multiply — so a cheese factor cannot be traced "
        "back to the assumption that produced it unless the basis travels with it."
    )

    chain_columns = st.columns(2)
    with chain_columns[0]:
        first_quantity = st.number_input(
            "kg of milk into the dairy", min_value=0.1, value=10.0, step=1.0
        )
    with chain_columns[1]:
        chain_basis = st.radio(
            "Basis, applied throughout", options=PARTITIONING_BASES,
            format_func=lambda key: BASIS_LABELS[key], horizontal=True,
            index=PARTITIONING_BASES.index(ECONOMIC),
        )

    steps = [
        {"process": "dairy_herd", "output": "milk", "quantity": first_quantity},
        {"process": "cheese_making", "output": "cheese", "quantity": 1.0},
    ]

    try:
        result = chain([dict(step, basis=chain_basis) for step in steps])
    except AllocationError as exc:
        st.error(str(exc))
    else:
        st.metric(
            f"Reaching the {result['final_output'].lower()}",
            f"{result['total_kg_co2e']:,.3f} kg CO2e",
        )
        st.dataframe(
            pd.DataFrame(result["steps"])[[
                "step", "process_label", "output_label", "basis_label",
                "share_at_this_step", "own_kg_co2e", "inherited_kg_co2e",
                "running_kg_co2e"
            ]].rename(columns={
                "step": "#", "process_label": "Process",
                "output_label": "Output", "basis_label": "Basis",
                "share_at_this_step": "Share taken",
                "own_kg_co2e": "From this step",
                "inherited_kg_co2e": "Carried in",
                "running_kg_co2e": "Running total",
            }),
            use_container_width=True, hide_index=True,
        )
        if result["mixed_bases"]:
            st.warning(
                "This chain uses more than one basis. That is allowed, and it "
                "means the final number cannot be described as being on any "
                "single one of them."
            )

    st.markdown("#### The same chain, each basis applied consistently")
    across = chain_across_bases(steps)
    for row in across:
        if row["total_kg_co2e"] is None:
            st.markdown(f"- **{row['basis_label']}** — not available: {row['error']}")
        else:
            st.markdown(
                f"- **{row['basis_label']}** — {row['total_kg_co2e']:,.3f} kg CO2e"
            )
    st.caption(
        "A basis that is undefined at any step is undefined for the whole "
        "chain. It fails there rather than silently switching to another one."
    )


with tab_recycling:
    st.subheader("Who gets the benefit of recycling?")
    st.markdown(
        "Cut-off, avoided burden and 50/50 give different answers for the same "
        "physical loop. The difference is not arithmetic — it is about which "
        "lever gets rewarded, and therefore what a buyer should pay for."
    )

    material = st.selectbox(
        "Material", options=list_materials(),
        format_func=lambda key: MATERIALS[key]["label"],
    )
    material_entry = get_material(material)
    st.caption(material_entry["note"])

    lever_columns = st.columns(2)
    with lever_columns[0]:
        recycled_content = st.slider(
            "Recycled content", 0.0, 1.0,
            float(material_entry["recycled_content"]), 0.05, format="%.0f%%",
        )
    with lever_columns[1]:
        recovery_rate = st.slider(
            "Recovered at end of life", 0.0, 1.0,
            float(material_entry["recovery_rate"]), 0.05, format="%.0f%%",
        )

    methods = compare_recycling_methods(material, recycled_content, recovery_rate)
    method_frame = pd.DataFrame(methods["rows"])

    method_chart = px.bar(
        method_frame, x="method_label", y="burden_kg_co2e",
        labels={"method_label": "", "burden_kg_co2e": "kg CO2e per kg"},
    )
    method_chart.update_traces(marker_color="#0f766e")
    method_chart.add_hline(
        y=material_entry["virgin_kg_co2e"], line_dash="dot",
        annotation_text="all virgin",
    )
    method_chart.add_hline(
        y=material_entry["recycled_kg_co2e"], line_dash="dot",
        annotation_text="all recycled",
    )
    method_chart.update_layout(
        height=420, margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(method_chart, use_container_width=True)

    st.dataframe(
        method_frame[[
            "method_label", "burden_kg_co2e", "saving_vs_virgin",
            "rewards_recycled_content", "rewards_recyclability"
        ]].rename(columns={
            "method_label": "Method", "burden_kg_co2e": "kg CO2e per kg",
            "saving_vs_virgin": "Saving vs virgin",
            "rewards_recycled_content": "Rewards recycled content",
            "rewards_recyclability": "Rewards recyclability",
        }),
        use_container_width=True, hide_index=True,
    )

    for row in methods["rows"]:
        st.markdown(f"- **{row['method_label']}** — {row['method_note']}")

    st.info(
        f"Across the three methods this material spans "
        f"{methods['spread']:.3f} kg CO2e per kg"
        + (f" — a factor of {methods['ratio']:.2f}." if methods["ratio"] else ".")
        + " Move the two sliders and watch which methods respond: cut-off is "
        "flat against the recovery slider, and avoided burden is flat against "
        "the recycled content slider. That is the whole difference between them."
    )


with tab_saved:
    st.subheader("Saved studies")
    saved = get_studies(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for study in saved:
            with st.expander(
                f"{study['name']} — {PROCESSES.get(study['process'], {}).get('label', study['process'])}"
                f" on {BASIS_LABELS.get(study['basis'], study['basis'])}"
            ):
                a, b = st.columns(2)
                a.metric("Burden", f"{study['burden_kg_co2e']:,.0f} kg")
                if study.get("widest_ratio"):
                    b.metric("Widest spread", f"{study['widest_ratio']:.2f}×")
                detail = study.get("detail") or {}
                if detail.get("rows"):
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Output": row["label"],
                                "Lowest": row.get("low"),
                                "Highest": row.get("high"),
                                "Ratio": row.get("ratio"),
                            }
                            for row in detail["rows"]
                        ]),
                        use_container_width=True, hide_index=True,
                    )
                if st.button("Delete", key=f"delete_study_{study['id']}"):
                    if delete_study(study["id"], user_id):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete it.")
