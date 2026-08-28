"""Whole-life carbon for a renovation, counted against a real starting debt.

The rest of the app computes retrofit payback against zero, which makes every
measure look worth doing. This page counts what the measure costs to build, in
EN 15978 stages, and reports the cases where the debt is never repaid.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.environment.building_materials_lca import (
    ASSESSMENT_PERIODS,
    DEFAULT_ASSESSMENT_PERIOD,
    DEFAULT_HEATING_DEGREE_DAYS,
    HEAT_SOURCES,
    TRANSPORT_MODES,
    BuildingLCAError,
    carbon_payback,
    compare_at_u_value,
    delete_project,
    get_lca_insights,
    get_material,
    get_projects,
    list_categories,
    list_materials,
    operational_saving,
    renovate_versus_rebuild,
    save_project,
    thickness_for_u_value,
    time_weighted_payback,
    u_value_after,
    whole_life_carbon,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🧱 Whole-Life Carbon for Renovation</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Insulation, glazing and structure all carry manufacturing emissions that "
    "land in the atmosphere the day the work is done, while the savings arrive "
    "over the following decades. Payback computed against zero makes every "
    "retrofit look worth doing. Some are not."
)

with st.expander("How this is counted, and what it refuses to do"):
    st.markdown(
        """
**The functional unit is the job, not the kilogram.** Insulation is compared at
a target U-value over a square metre, with the thickness derived from the
conductivity. Aerogel and mineral wool are not comparable per kilogram; they are
comparable at a U-value.

**Stages are kept apart, per EN 15978.** A1–A3 product, A4 transport, A5
construction including cut-and-fit waste, B4 replacement inside the assessment
period, C3–C4 end of life.

**Replacement is counted.** A component with a 30-year life inside a 60-year
study is manufactured twice. A "low carbon" material replaced twice as often is
not low carbon, and a shorter study period hides that.

**Module D is reported and never netted.** A steel section credited with its
future recycling looks competitive with timber, on the strength of a market that
has to still exist in sixty years. It is shown separately and excluded from
every total on this page.

**Both biogenic conventions are shown.** −1/+1 credits sequestration and charges
the release; 0/0 does neither. They disagree for timber and agree for everything
mineral. Neither is presented as settled.

**A measure that never pays back is told to you in words.** If payback exceeds
the component's own service life, the page says so instead of printing a large
number and leaving you to notice.
        """
    )

st.markdown("---")

tab_element, tab_compare, tab_project, tab_saved = st.tabs(
    [
        "🧮 One element",
        "⚖️ Like-for-like",
        "🏚️ Renovate vs rebuild",
        "💾 Saved projects",
    ]
)


# ---------------------------------------------------------------------------
# One element
# ---------------------------------------------------------------------------
with tab_element:
    st.markdown("### A single measure, stage by stage")

    c1, c2 = st.columns(2)
    with c1:
        category = st.selectbox(
            "Category",
            list_categories(),
            format_func=lambda c: c.title(),
            key="lca_category",
        )
        material = st.selectbox(
            "Material",
            list_materials(category),
            format_func=lambda k: get_material(k)["label"],
            key="lca_material",
        )
        area = st.number_input(
            "Area (m²)", min_value=0.5, value=50.0, step=5.0, key="lca_area"
        )
    with c2:
        period = st.selectbox(
            "Assessment period (years)",
            ASSESSMENT_PERIODS,
            index=ASSESSMENT_PERIODS.index(DEFAULT_ASSESSMENT_PERIOD),
            key="lca_period",
        )
        convention = st.radio(
            "Biogenic carbon convention",
            ["0/0", "-1/+1"],
            horizontal=True,
            key="lca_convention",
            help="0/0 neither credits sequestration nor charges the release. "
                 "-1/+1 does both. They disagree for timber.",
        )
        mode = st.selectbox(
            "Transport mode",
            sorted(TRANSPORT_MODES),
            index=sorted(TRANSPORT_MODES).index(
                get_material(material)["transport_mode"]
            ),
            format_func=lambda m: TRANSPORT_MODES[m]["label"],
            key="lca_mode",
        )
        distance = st.number_input(
            "Distance to site (km)",
            min_value=0.0,
            value=float(get_material(material)["default_transport_km"]),
            step=50.0,
            key="lca_distance",
        )

    st.caption(get_material(material)["note"])

    spec = get_material(material)
    thickness = None
    u_before = None
    u_after_value = None

    if spec.get("conductivity") and spec["category"] == "insulation":
        t1, t2 = st.columns(2)
        with t1:
            u_before = st.number_input(
                "Existing U-value (W/m²K)",
                min_value=0.05, value=2.30, step=0.10, key="lca_u_before",
                help="An uninsulated loft is around 2.3, a solid wall around "
                     "2.1, a suspended timber floor around 0.7.",
            )
        with t2:
            u_target = st.number_input(
                "Target U-value (W/m²K)",
                min_value=0.05, value=0.16, step=0.02, key="lca_u_target",
            )
        try:
            thickness = thickness_for_u_value(material, u_target, u_before)
        except BuildingLCAError as error:
            st.error(str(error))
            st.stop()
        u_after_value = u_value_after(material, thickness, u_before)
        st.info(
            f"**{thickness * 1000:.0f} mm** of {spec['label'].lower()} takes this "
            f"element from {u_before:.2f} to {u_after_value:.2f} W/m²K."
        )
    elif spec.get("unit_u_value"):
        u_before = st.number_input(
            "U-value being replaced (W/m²K)",
            min_value=0.05, value=1.40, step=0.10, key="lca_u_replaced",
        )
        u_after_value = spec["unit_u_value"]
        st.info(
            f"This unit is {u_after_value:.2f} W/m²K, replacing "
            f"{u_before:.2f} W/m²K."
        )
    else:
        thickness = st.number_input(
            "Thickness (m)", min_value=0.005, value=0.10, step=0.01,
            key="lca_thickness",
        )

    try:
        result = whole_life_carbon(
            material,
            area,
            thickness_m=thickness,
            assessment_period=period,
            transport_km=distance,
            transport_mode=mode,
            biogenic_convention=convention,
        )
    except BuildingLCAError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Upfront (A1–A5)", f"{result['upfront_kg_co2e']:,.0f} kg CO₂e")
    m2.metric("Whole life", f"{result['total_kg_co2e']:,.0f} kg CO₂e")
    m3.metric("Replacements", f"{result['replacements']}")
    m4.metric("Mass", f"{result['mass_kg']:,.0f} kg")

    st.markdown("#### Stages")
    stage_fig = go.Figure(
        go.Bar(
            x=list(result["stages"]),
            y=list(result["stages"].values()),
            marker_color=["#2f5e32", "#5f8f36", "#78a945", "#e07a5f", "#9aa5a0"],
            text=[f"{v:,.0f}" for v in result["stages"].values()],
            textposition="auto",
        )
    )
    stage_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO₂e",
    )
    st.plotly_chart(stage_fig, use_container_width=True)

    if result["module_d_kg_co2e"] != 0:
        st.warning(
            f"**Module D: {result['module_d_kg_co2e']:,.0f} kg CO₂e.** "
            f"{result['module_d_warning']}"
        )

    st.markdown("#### What this element is telling you")
    for insight in get_lca_insights(result):
        st.markdown(f"- {insight}")

    if u_before is not None and u_after_value is not None and u_after_value < u_before:
        st.markdown("---")
        st.markdown("### Does it pay back?")

        p1, p2 = st.columns(2)
        with p1:
            heat_source = st.selectbox(
                "Heat source",
                sorted(HEAT_SOURCES),
                format_func=lambda k: HEAT_SOURCES[k]["label"],
                key="lca_heat_source",
            )
        with p2:
            degree_days = st.number_input(
                "Heating degree days",
                min_value=200.0,
                value=float(DEFAULT_HEATING_DEGREE_DAYS),
                step=100.0,
                key="lca_degree_days",
                help="src.energy.degree_days.py holds the location-specific model; this "
                     "is a temperate default.",
            )

        saving = operational_saving(
            area, u_before, u_after_value, heat_source, degree_days
        )
        payback = carbon_payback(
            result["upfront_kg_co2e"],
            saving["annual_kg_co2e"],
            result["service_life"],
        )

        s1, s2, s3 = st.columns(3)
        s1.metric("Heat saved", f"{saving['heat_saved_kwh']:,.0f} kWh/yr")
        s2.metric("Carbon saved", f"{saving['annual_kg_co2e']:,.0f} kg CO₂e/yr")
        s3.metric(
            "Payback",
            f"{payback['years']:.1f} yr" if payback["years"] else "never",
        )

        if payback["pays_back"]:
            st.success(payback["verdict"])
        else:
            st.error(payback["verdict"])

        st.caption(f"**{saving['heat_source_label']}.** {saving['note']}")

        weighted = time_weighted_payback(
            result["upfront_kg_co2e"], saving["annual_kg_co2e"], period
        )
        st.markdown("#### Flat arithmetic versus time-weighted")
        w1, w2 = st.columns(2)
        w1.metric(
            "Net, undiscounted",
            f"{weighted['undiscounted_net']:,.0f} kg CO₂e",
        )
        w2.metric(
            f"Net, discounted at {weighted['discount_rate'] * 100:.0f}%",
            f"{weighted['discounted_net']:,.0f} kg CO₂e",
        )
        st.caption(weighted["note"])

        with st.form("save_lca_project"):
            name = st.text_input("Save this element as", value="")
            if st.form_submit_button("Save project") and name.strip():
                try:
                    save_project(user_id, name, result, payback)
                    st.success(f"Saved '{name.strip()}'.")
                except BuildingLCAError as error:
                    st.error(str(error))


# ---------------------------------------------------------------------------
# Like-for-like
# ---------------------------------------------------------------------------
with tab_compare:
    st.markdown("### Same job, same U-value, different materials")
    st.caption(
        "Per kilogram, PIR looks three times worse than mineral wool. At a "
        "U-value you need far less of it, and the ranking changes. That is why "
        "the functional unit is the job rather than the kilogram."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        comp_area = st.number_input(
            "Area (m²)", min_value=1.0, value=50.0, step=5.0, key="cmp_area"
        )
    with c2:
        comp_existing = st.number_input(
            "Existing U-value", min_value=0.10, value=2.30, step=0.10,
            key="cmp_existing",
        )
    with c3:
        comp_target = st.number_input(
            "Target U-value", min_value=0.05, value=0.16, step=0.02,
            key="cmp_target",
        )

    comp_period = st.select_slider(
        "Assessment period (years)",
        options=list(ASSESSMENT_PERIODS),
        value=DEFAULT_ASSESSMENT_PERIOD,
        key="cmp_period",
    )
    comp_convention = st.radio(
        "Biogenic convention",
        ["0/0", "-1/+1"],
        horizontal=True,
        key="cmp_convention",
    )

    try:
        rows = compare_at_u_value(
            list_materials("insulation"),
            comp_area,
            comp_target,
            comp_existing,
            assessment_period=comp_period,
            biogenic_convention=comp_convention,
        )
    except BuildingLCAError as error:
        st.error(str(error))
        rows = []

    if rows:
        comp_fig = go.Figure()
        comp_fig.add_trace(
            go.Bar(
                name="Upfront (A1–A5)",
                y=[row["label"] for row in rows],
                x=[row["upfront_kg_co2e"] for row in rows],
                orientation="h",
                marker_color="#2f5e32",
            )
        )
        comp_fig.add_trace(
            go.Bar(
                name="Replacement and end of life",
                y=[row["label"] for row in rows],
                x=[
                    row["total_kg_co2e"] - row["upfront_kg_co2e"] for row in rows
                ],
                orientation="h",
                marker_color="#e07a5f",
            )
        )
        comp_fig.update_layout(
            barmode="stack",
            height=400,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="kg CO₂e over the assessment period",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(comp_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Material": row["label"],
                        "Thickness (mm)": round(row["thickness_mm"]),
                        "Mass (kg)": round(row["mass_kg"]),
                        "Upfront (kg CO₂e)": round(row["upfront_kg_co2e"]),
                        "Whole life (kg CO₂e)": round(row["total_kg_co2e"]),
                        "Replacements": row["replacements"],
                        "Per m² (kg CO₂e)": round(row["per_m2"], 1),
                    }
                    for row in rows
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("#### Thickness is the trade-off nobody prices")
        thickness_fig = go.Figure(
            go.Scatter(
                x=[row["thickness_mm"] for row in rows],
                y=[row["total_kg_co2e"] for row in rows],
                mode="markers+text",
                text=[row["label"] for row in rows],
                textposition="top center",
                marker=dict(size=14, color="#5f8f36"),
            )
        )
        thickness_fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="Thickness needed (mm)",
            yaxis_title="Whole-life carbon (kg CO₂e)",
        )
        st.plotly_chart(thickness_fig, use_container_width=True)
        st.caption(
            "Bottom left is the material that does the job with the least "
            "carbon and the least depth. Where nothing sits there, the choice "
            "is a genuine trade between wall thickness and embodied carbon."
        )


# ---------------------------------------------------------------------------
# Renovate versus rebuild
# ---------------------------------------------------------------------------
with tab_project:
    st.markdown("### Renovate or rebuild")
    st.caption(
        "A new build is more efficient in operation and starts several hundred "
        "kilograms of CO₂e per square metre in debt, plus demolishing whatever "
        "stood there. The crossover year is the number worth arguing about."
    )

    r1, r2 = st.columns(2)
    with r1:
        floor_area = st.number_input(
            "Floor area (m²)", min_value=20.0, value=90.0, step=10.0,
            key="rvb_area",
        )
        retrofit_upfront = st.number_input(
            "Retrofit upfront carbon (kg CO₂e)",
            min_value=0.0, value=12000.0, step=500.0, key="rvb_upfront",
            help="Total A1–A5 across every measure. Build it up on the "
                 "'One element' tab.",
        )
        retrofit_saving = st.number_input(
            "Retrofit annual saving (kg CO₂e/yr)",
            min_value=0.0, value=3500.0, step=100.0, key="rvb_saving",
        )
    with r2:
        new_build_carbon = st.number_input(
            "New build upfront (kg CO₂e/m²)",
            min_value=100.0, value=550.0, step=25.0, key="rvb_new_carbon",
            help="300–800 is the usual range for domestic construction; "
                 "structure dominates it.",
        )
        demolition_carbon = st.number_input(
            "Demolition (kg CO₂e/m²)",
            min_value=0.0, value=60.0, step=10.0, key="rvb_demolition",
        )
        existing_demand = st.number_input(
            "Existing demand (kWh/m²/yr)",
            min_value=10.0, value=120.0, step=5.0, key="rvb_existing_demand",
        )
        new_demand = st.number_input(
            "New build demand (kWh/m²/yr)",
            min_value=5.0, value=25.0, step=5.0, key="rvb_new_demand",
        )

    rvb_source = st.selectbox(
        "Heat source under both options",
        sorted(HEAT_SOURCES),
        format_func=lambda k: HEAT_SOURCES[k]["label"],
        key="rvb_source",
    )
    rvb_period = st.select_slider(
        "Assessment period (years)",
        options=list(ASSESSMENT_PERIODS),
        value=DEFAULT_ASSESSMENT_PERIOD,
        key="rvb_period",
    )

    try:
        comparison = renovate_versus_rebuild(
            floor_area,
            retrofit_upfront,
            retrofit_saving,
            new_build_carbon_per_m2=new_build_carbon,
            demolition_carbon_per_m2=demolition_carbon,
            new_build_annual_demand_kwh_per_m2=new_demand,
            existing_annual_demand_kwh_per_m2=existing_demand,
            heat_source=rvb_source,
            assessment_period=rvb_period,
        )
    except BuildingLCAError as error:
        st.error(str(error))
        st.stop()

    v1, v2, v3 = st.columns(3)
    v1.metric("Retrofit, whole life", f"{comparison['retrofit_total']:,.0f} kg")
    v2.metric("Rebuild, whole life", f"{comparison['rebuild_total']:,.0f} kg")
    v3.metric(
        "Crossover",
        f"{comparison['crossover_years']:.0f} yr"
        if comparison["crossover_years"] else "never",
    )

    verdict_fig = go.Figure()
    for label, upfront, operational, color in (
        ("Retrofit", comparison["retrofit_upfront"],
         comparison["retrofit_operational"], "#5f8f36"),
        ("Rebuild", comparison["rebuild_upfront"],
         comparison["rebuild_operational"], "#e07a5f"),
    ):
        verdict_fig.add_trace(
            go.Bar(name=f"{label} upfront", x=[label], y=[upfront],
                   marker_color=color)
        )
        verdict_fig.add_trace(
            go.Bar(name=f"{label} operational", x=[label], y=[operational],
                   marker_color=color, opacity=0.45)
        )
    verdict_fig.update_layout(
        barmode="stack",
        height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title=f"kg CO₂e over {rvb_period} years",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(verdict_fig, use_container_width=True)

    if comparison["better"] == "retrofit":
        st.success(
            f"Retrofit wins by {abs(comparison['difference']):,.0f} kg CO₂e over "
            f"{rvb_period} years."
        )
    else:
        st.warning(
            f"On these inputs the rebuild wins by "
            f"{abs(comparison['difference']):,.0f} kg CO₂e over {rvb_period} "
            f"years. A deeper retrofit is what changes that answer."
        )
    st.caption(comparison["note"])


# ---------------------------------------------------------------------------
# Saved projects
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved projects")
    projects = get_projects(user_id)
    if not projects:
        st.info("Nothing saved yet. Build an element and save it.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": row["name"],
                        "Upfront (kg CO₂e)": round(row["upfront_kg_co2e"]),
                        "Whole life (kg CO₂e)": round(row["total_kg_co2e"]),
                        "Payback (yr)": (
                            round(row["payback_years"], 1)
                            if row["payback_years"] else "—"
                        ),
                        "Saved": row["created_at"],
                    }
                    for row in projects
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        total_upfront = sum(row["upfront_kg_co2e"] for row in projects)
        st.metric(
            "Combined upfront carbon across saved elements",
            f"{total_upfront:,.0f} kg CO₂e",
            help="Carry this into the renovate-versus-rebuild tab.",
        )

        to_delete = st.selectbox(
            "Remove a project",
            [row["id"] for row in projects],
            format_func=lambda i: next(
                row["name"] for row in projects if row["id"] == i
            ),
            key="lca_delete",
        )
        if st.button("Delete", key="lca_delete_button"):
            if delete_project(user_id, to_delete):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Could not delete that project.")

    st.markdown("---")
    st.caption(
        "Material data is generic and functional-unit based rather than "
        "product-specific. A manufacturer's EPD for the exact product will "
        "differ, usually by less than the difference between materials."
    )
