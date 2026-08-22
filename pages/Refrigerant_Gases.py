"""Fugitive refrigerant emissions, TEWI, and whether a gas swap is worth it.

Nobody knows how much refrigerant their fridge leaked last year, which is why
asking for the quantity gets a zero. This asks what the machine is instead.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from refrigerant_gases import (
    DEFAULT_GRID_INTENSITY,
    DEFAULT_RECOVERY,
    EQUIPMENT_CLASSES,
    GRID_INTENSITIES,
    HORIZONS,
    PHASE_DOWN_LABELS,
    REFRIGERANTS,
    VINTAGES,
    RefrigerantError,
    build_equipment,
    delete_register,
    get_refrigerant,
    get_refrigerant_insights,
    get_registers,
    gwp,
    gwp_spread,
    lifecycle_emissions,
    list_equipment_classes,
    list_refrigerants,
    phase_down_exposure,
    register_summary,
    retrofit_comparison,
    retrofit_options,
    save_register,
    sensitivity,
    tewi,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>❄️ Refrigerant Emissions</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A domestic heat pump holds two or three kilograms of R-410A at a global "
    "warming potential of 2,088. At a 3.5% annual leak rate that is around "
    "150 kg CO2e a year escaping from a machine bought to reduce emissions — "
    "and it is reported as zero almost everywhere, because the question asked "
    "is usually *how much did you lose*, which nobody knows."
)

with st.expander("Why this is estimated differently from everything else"):
    st.markdown(
        """
Commercial operators estimate leakage by mass balance: gas bought, minus gas
still in stock. A household has no such record, so the estimate has to run the
other way — from what you *can* say, which is what the machine is and roughly
how big.

**Lifetime is not the annual rate times the lifetime.** There are three separate
events:

- **Installation.** A one-off loss when the system is charged and commissioned.
- **Operation.** The annual leak. Whether it stays constant depends on whether
  the machine gets topped up during servicing — if it does, it holds a full
  charge and keeps leaking a full charge's fraction every year.
- **Disposal.** Whatever is still inside when the machine is thrown away. On a
  unit that is scrapped rather than degassed, this single event often exceeds
  the entire operating life's leakage. It is also the only part still under your
  control at the moment it happens, which is the moment nobody is thinking
  about it.

**And direct emissions on their own give wrong advice.** Propane has a GWP of 3
against R-410A's 2,088, so a swap looks unanswerable. But if the replacement
runs less efficiently the machine draws more electricity, and on a dirty grid
that extra electricity can outweigh the entire direct saving. TEWI puts both on
the same axis. The output below is not a yes or a no — it is the grid intensity
at which the answer flips.
"""
    )

tab_register, tab_retrofit, tab_gases, tab_saved = st.tabs(
    ["Your equipment", "Should I switch gas?", "The gases", "Saved registers"]
)


with tab_register:
    st.subheader("What is in the house")

    settings = st.columns(3)
    with settings[0]:
        grid_name = st.selectbox(
            "Grid intensity",
            options=list(GRID_INTENSITIES),
            index=list(GRID_INTENSITIES).index("mixed"),
            format_func=lambda key: (
                f"{key.replace('_', ' ').title()} "
                f"({GRID_INTENSITIES[key]:.3f} kg/kWh)"
            ),
        )
        grid_intensity = GRID_INTENSITIES[grid_name]
    with settings[1]:
        recovery = st.slider(
            "End-of-life recovery",
            min_value=0.0, max_value=1.0, value=DEFAULT_RECOVERY, step=0.05,
            format="%.0f%%",
            help=(
                "Nothing recovered means the machine was crushed with the "
                "charge still in it."
            ),
        )
    with settings[2]:
        topped_up = st.checkbox(
            "Serviced and topped up",
            value=True,
            help=(
                "A machine kept full leaks a full charge's fraction every year. "
                "One left to empty leaks less in total and runs worse doing it."
            ),
        )

    basis = st.columns(2)
    with basis[0]:
        vintage = st.selectbox(
            "GWP vintage", options=VINTAGES, index=VINTAGES.index("ar6"),
            format_func=str.upper,
        )
    with basis[1]:
        horizon = st.selectbox(
            "Horizon", options=HORIZONS, index=HORIZONS.index(100),
            format_func=lambda years: f"{years} years",
        )

    if "refrigerant_items" not in st.session_state:
        st.session_state.refrigerant_items = [
            build_equipment("domestic_fridge"),
            build_equipment("air_source_heat_pump"),
        ]

    with st.form("add_equipment"):
        st.markdown("**Add a piece of equipment**")
        add = st.columns(3)
        with add[0]:
            equipment_class = st.selectbox(
                "What is it?",
                options=list_equipment_classes(),
                format_func=lambda key: EQUIPMENT_CLASSES[key]["label"],
            )
        with add[1]:
            chosen_gas = st.selectbox(
                "Refrigerant",
                options=["(class default)"] + list_refrigerants(),
            )
        with add[2]:
            age = st.number_input("Age in years", min_value=0.0, value=0.0, step=1.0)

        override = st.checkbox("I know the charge size and leak rate")
        charge_kg = leak_rate = None
        if override:
            fine = st.columns(2)
            with fine[0]:
                charge_kg = st.number_input(
                    "Charge (kg)", min_value=0.01, value=1.0, step=0.1
                )
            with fine[1]:
                leak_rate = st.number_input(
                    "Annual leak rate (%)", min_value=0.0, max_value=99.0,
                    value=5.0, step=0.5,
                ) / 100.0

        if st.form_submit_button("Add it"):
            try:
                st.session_state.refrigerant_items.append(
                    build_equipment(
                        equipment_class,
                        gas=None if chosen_gas == "(class default)" else chosen_gas,
                        charge_kg=charge_kg,
                        leak_rate=leak_rate,
                        age_years=age,
                    )
                )
                st.success("Added.")
            except RefrigerantError as exc:
                st.error(str(exc))

    items = st.session_state.refrigerant_items
    if not items:
        st.info("Add something above to see a footprint.")
    else:
        if st.button("Clear the list"):
            st.session_state.refrigerant_items = []
            st.rerun()

        summary = register_summary(
            items, grid_intensity=grid_intensity, recovery=recovery,
            vintage=vintage, horizon=horizon, topped_up=topped_up,
        )

        a, b, c, d = st.columns(4)
        a.metric("Leaking now", f"{summary['annual_leak_co2e']:,.0f} kg/yr")
        b.metric("Lifetime leakage", f"{summary['lifetime_direct_co2e']:,.0f} kg")
        c.metric("Of that, disposal", f"{summary['disposal_co2e']:,.0f} kg")
        d.metric("Lifetime TEWI", f"{summary['lifetime_tewi']:,.0f} kg")
        st.caption(
            f"Refrigerant is {summary['direct_share']:.0%} of the total warming "
            "impact of this equipment; the rest is the electricity it uses."
        )

        frame = pd.DataFrame(summary["items"])
        split = go.Figure()
        split.add_trace(go.Bar(
            x=frame["label"], y=frame["lifetime_direct_co2e"],
            name="Refrigerant leaked", marker_color="#0ea5e9",
        ))
        split.add_trace(go.Bar(
            x=frame["label"], y=frame["lifetime_indirect_co2e"],
            name="Electricity used", marker_color="#94a3b8",
        ))
        split.update_layout(
            barmode="stack", height=440, yaxis_title="kg CO2e over its life",
            xaxis_title="", legend=dict(orientation="h", y=1.1),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(split, use_container_width=True)

        display = frame[[
            "label", "gas", "charge_kg", "annual_leak_co2e",
            "disposal_co2e", "lifetime_tewi", "years_left"
        ]].rename(columns={
            "label": "Equipment", "gas": "Gas", "charge_kg": "Charge (kg)",
            "annual_leak_co2e": "Leaking (kg/yr)",
            "disposal_co2e": "At disposal (kg)",
            "lifetime_tewi": "Lifetime TEWI (kg)",
            "years_left": "Years left",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

        st.markdown("#### What this says")
        for line in get_refrigerant_insights(summary):
            st.markdown(f"- {line}")

        exposure = phase_down_exposure(items)
        if exposure:
            st.markdown("#### Gases being phased down")
            st.warning(
                "Servicing gas for these gets scarcer and dearer before the "
                "equipment wears out, so the replacement decision arrives "
                "earlier than the machine's age suggests."
            )
            st.dataframe(
                pd.DataFrame(exposure)[
                    ["label", "gas", "status_label", "years_left"]
                ].rename(columns={
                    "label": "Equipment", "gas": "Gas",
                    "status_label": "Status", "years_left": "Years left",
                }),
                use_container_width=True, hide_index=True,
            )

        st.markdown("#### One machine, four uncertain inputs")
        focus_index = st.selectbox(
            "Which one?",
            options=list(range(len(items))),
            format_func=lambda n: items[n]["label"],
        )
        rows = pd.DataFrame(sensitivity(items[focus_index], grid_intensity))
        sensitivity_chart = px.bar(
            rows, x="total_co2e", y="setting", color="parameter",
            orientation="h", labels={"total_co2e": "Lifetime TEWI (kg)", "setting": ""},
        )
        sensitivity_chart.update_layout(
            height=640, margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", y=1.06),
        )
        st.plotly_chart(sensitivity_chart, use_container_width=True)
        st.caption(
            "Recovery at disposal and grid intensity move this more than the "
            "leak rate does — and the GWP vintage alone, with nothing else "
            "changed, moves it enough to matter."
        )

        with st.form("save_register_form"):
            name = st.text_input("Name this register", value="Home")
            if st.form_submit_button("Save register"):
                if not name.strip():
                    st.error("Give the register a name.")
                elif save_register(user_id, name.strip(), items, summary):
                    st.success("Saved.")
                else:
                    st.error("Could not save the register.")


with tab_retrofit:
    st.subheader("Would a different gas actually be better?")
    st.markdown(
        "A lower-GWP gas cuts the leak. If the machine also runs less "
        "efficiently on it, the extra electricity has to come from somewhere. "
        "Which effect wins depends on the grid — so the answer here is a "
        "threshold, not a verdict."
    )

    items = st.session_state.get("refrigerant_items") or [
        build_equipment("air_source_heat_pump")
    ]
    choice = st.columns(3)
    with choice[0]:
        target_index = st.selectbox(
            "Equipment",
            options=list(range(len(items))),
            format_func=lambda n: f"{items[n]['label']} ({items[n]['gas']})",
            key="retrofit_target",
        )
    with choice[1]:
        alternative = st.selectbox(
            "Switch to",
            options=[
                gas for gas in list_refrigerants()
                if gas != items[target_index]["gas"]
            ],
            format_func=lambda gas: REFRIGERANTS[gas]["label"],
        )
    with choice[2]:
        penalty = st.slider(
            "Energy use changes by",
            min_value=-20, max_value=60, value=15, step=5, format="%d%%",
            help="Positive means the machine draws more on the new gas.",
        ) / 100.0

    target = items[target_index]
    grid_choice = st.select_slider(
        "Your grid",
        options=list(GRID_INTENSITIES),
        value="mixed",
        format_func=lambda key: (
            f"{key.replace('_', ' ').title()} ({GRID_INTENSITIES[key]:.3f})"
        ),
    )
    here = GRID_INTENSITIES[grid_choice]

    result = retrofit_comparison(
        target, alternative, efficiency_penalty=penalty, grid_intensity=here
    )

    a, b, c = st.columns(3)
    a.metric("Now", f"{result['current_tewi']:,.0f} kg")
    b.metric(
        f"On {alternative}", f"{result['swapped_tewi']:,.0f} kg",
        delta=f"{result['net_change']:,.0f} kg", delta_color="inverse",
    )
    c.metric(
        "Threshold",
        f"{result['breakeven_grid_intensity']:.3f} kg/kWh"
        if result["breakeven_grid_intensity"] is not None else "none",
    )

    if result["worthwhile_here"]:
        st.success(f"On your grid this swap helps. It {result['verdict']}.")
    else:
        st.error(f"On your grid this swap makes things worse. It {result['verdict']}.")

    st.caption(
        f"GWP falls from {result['from_gwp']:,.0f} to {result['to_gwp']:,.0f}, "
        f"which saves {abs(result['direct_change']):,.0f} kg of direct emissions "
        f"— and the efficiency change adds "
        f"{result['indirect_change']:,.0f} kg of electricity."
    )

    if result["safety_note"]:
        st.warning(result["safety_note"])

    sweep = []
    for name, intensity in GRID_INTENSITIES.items():
        row = retrofit_comparison(
            target, alternative, efficiency_penalty=penalty, grid_intensity=intensity
        )
        sweep.append({
            "Grid": name.replace("_", " ").title(),
            "Intensity": intensity,
            "Now": row["current_tewi"],
            "After the swap": row["swapped_tewi"],
        })
    sweep_frame = pd.DataFrame(sweep).sort_values("Intensity")

    crossing = go.Figure()
    crossing.add_trace(go.Scatter(
        x=sweep_frame["Intensity"], y=sweep_frame["Now"], name=f"Stay on {target['gas']}",
        mode="lines+markers", line=dict(color="#94a3b8", width=3),
    ))
    crossing.add_trace(go.Scatter(
        x=sweep_frame["Intensity"], y=sweep_frame["After the swap"],
        name=f"Switch to {alternative}", mode="lines+markers",
        line=dict(color="#0ea5e9", width=3),
    ))
    if result["breakeven_grid_intensity"] is not None:
        crossing.add_vline(
            x=result["breakeven_grid_intensity"], line_dash="dot",
            annotation_text="they cross here",
        )
    crossing.add_vline(x=here, line_dash="dash", annotation_text="your grid")
    crossing.update_layout(
        height=440, xaxis_title="Grid intensity (kg CO2e per kWh)",
        yaxis_title="Lifetime TEWI (kg)",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(crossing, use_container_width=True)
    st.caption(
        "Where the two lines cross is where the direct saving stops covering "
        "the extra electricity. Which side of it you are on is the decision."
    )

    st.markdown("#### Every gas, ranked at your grid")
    options = retrofit_options(target, efficiency_penalty=penalty, grid_intensity=here)
    st.dataframe(
        pd.DataFrame([{
            "Gas": REFRIGERANTS[row["to_gas"]]["label"],
            "GWP": row["to_gwp"],
            "Lifetime TEWI": row["swapped_tewi"],
            "Change": row["net_change"],
            "Threshold": row["breakeven_grid_intensity"] or "—",
            "Safety": get_refrigerant(row["to_gas"])["safety_class"],
        } for row in options]),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        "Ranked on total impact at your grid, not on GWP. Those are different "
        "orderings, which is the whole reason for the column."
    )


with tab_gases:
    st.subheader("The gases")
    rows = []
    for gas in list_refrigerants():
        entry = get_refrigerant(gas)
        spread = gwp_spread(gas)
        rows.append({
            "Gas": entry["label"],
            "GWP-100 (AR6)": gwp(gas, "ar6", 100),
            "GWP-20 (AR6)": gwp(gas, "ar6", 20),
            "AR4 → AR6 spread": spread["spread"],
            "Lifetime (yr)": entry["lifetime_years"],
            "Safety": entry["safety_class"],
            "Status": entry["phase_down_label"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown(
        "**The horizon does not rescale this table, it reorders it.** These "
        "gases have atmospheric lifetimes running from a few days to a few "
        "decades, so shortening the horizon from 100 years to 20 does not "
        "affect them all in the same proportion."
    )

    horizon_frame = pd.DataFrame([
        {
            "Gas": REFRIGERANTS[gas]["label"],
            "100 years": gwp(gas, "ar6", 100),
            "20 years": gwp(gas, "ar6", 20),
        }
        for gas in list_refrigerants()
        if gwp(gas, "ar6", 100) > 1
    ])
    horizon_chart = px.bar(
        horizon_frame.melt(id_vars="Gas", var_name="Horizon", value_name="GWP"),
        x="Gas", y="GWP", color="Horizon", barmode="group",
    )
    horizon_chart.update_layout(
        height=420, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(horizon_chart, use_container_width=True)

    st.markdown("#### Phase-down status")
    for status, label in PHASE_DOWN_LABELS.items():
        gases = [
            REFRIGERANTS[gas]["label"] for gas in list_refrigerants()
            if REFRIGERANTS[gas]["phase_down"] == status
        ]
        if gases:
            st.markdown(f"- **{label}:** {', '.join(gases)}")


with tab_saved:
    st.subheader("Saved registers")
    saved = get_registers(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for register in saved:
            with st.expander(
                f"{register['name']} — {register['annual_leak_co2e']:,.0f} kg/yr "
                f"leaking, {register['item_count']} item(s)"
            ):
                a, b, c = st.columns(3)
                a.metric("Charge held", f"{register['total_charge_kg']:.2f} kg")
                b.metric("Leaking", f"{register['annual_leak_co2e']:,.0f} kg/yr")
                c.metric("Lifetime TEWI", f"{register['lifetime_tewi']:,.0f} kg")
                detail = register.get("detail") or {}
                if detail.get("summary", {}).get("items"):
                    st.dataframe(
                        pd.DataFrame(detail["summary"]["items"])[
                            ["label", "gas", "annual_leak_co2e", "lifetime_tewi"]
                        ].rename(columns={
                            "label": "Equipment", "gas": "Gas",
                            "annual_leak_co2e": "kg/yr",
                            "lifetime_tewi": "Lifetime TEWI",
                        }),
                        use_container_width=True, hide_index=True,
                    )
                if st.button("Delete", key=f"delete_register_{register['id']}"):
                    if delete_register(register["id"], user_id):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete it.")
