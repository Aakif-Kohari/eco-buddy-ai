"""How much material had to move, which no emission figure can tell you.

Every other page in this app measures an output. This one measures the input:
the rock, ore, sand, biomass and soil moved to put a product in your hand — and
the ratio between what you hold and what was moved for it.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.environment.material_footprint import (
    CATEGORIES,
    CATEGORY_LABELS,
    MATERIALS,
    SUSTAINABLE_ABIOTIC_PER_CAPITA_TONNES,
    MaterialError,
    abiotic_depletion,
    circularity_saving,
    compare_products,
    concentration,
    criticality,
    delete_footprint,
    get_footprints,
    get_material,
    get_material_insights,
    get_product,
    grade_sensitivity,
    list_families,
    list_materials,
    list_products,
    per_capita_context,
    product_footprint,
    save_footprint,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⛏️ Material Footprint & Resource Depletion</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A smartphone's manufacturing carbon is modest. The material moved to make "
    "one is around two hundred and forty times the phone's own mass, almost "
    "all of it overburden and tailings from mining fractions of a gram of gold "
    "and palladium."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**The ratio, not the tonnage.** Direct material input, product mass, and the
unused extraction behind both are reported separately. The ratio between what
you hold and what was moved is the number worth remembering.

**Categories are never summed.** Abiotic rock and ore, biotic harvest, soil
moved by erosion, water and air stay apart. Adding moved topsoil to extracted
ore produces a big number with no meaning — and that aggregate is the standard
reason this metric gets published and then ignored.

**Grade is geology, not inefficiency.** A metal's rucksack scales inversely with
ore grade, and grades are falling. Copper at 0.6% moves ~350 kg of rock per kg;
at 0.3% it moves twice that. No process improvement touches it.

**Depletion and criticality are different questions.** Depletion asks how much
of a finite stock a use consumes. Criticality asks whether supply can be
interrupted. Cobalt is abundant in the crust and critical in practice, and a
combined "resource score" would make both dimensions unreadable.

**Reserves are economic, not geological.** "Years remaining" moves with price
and exploration, so these figures compare materials rather than counting down.

**Recycling is capped at what it can actually deliver.** Secondary supply in the
circularity model is limited by the real end-of-life recycling input rates of
the materials carrying the footprint. For rare earths, tantalum and indium that
is close to nothing.
        """
    )

st.markdown("---")

tab_product, tab_grade, tab_critical, tab_life, tab_saved = st.tabs(
    [
        "📱 A product",
        "⛏️ Ore grade",
        "🌐 Criticality",
        "🔧 Life extension",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# A product
# ---------------------------------------------------------------------------
with tab_product:
    st.markdown("### What one object moved")

    c1, c2 = st.columns([3, 1])
    with c1:
        product = st.selectbox(
            "Product",
            list_products(),
            format_func=lambda k: get_product(k)["label"],
            key="mf_product",
        )
    with c2:
        quantity = st.number_input(
            "How many", min_value=1.0, value=1.0, step=1.0, key="mf_quantity"
        )

    st.caption(get_product(product)["note"])

    try:
        result = product_footprint(product, quantity)
    except MaterialError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Product mass", f"{result['direct_mass_kg']:,.2f} kg")
    m2.metric("Abiotic material moved", f"{result['abiotic_kg']:,.1f} kg")
    m3.metric("Ratio", f"{result['ratio']:,.0f} : 1")
    m4.metric(
        "Per year of service",
        f"{result['abiotic_per_year']:,.1f} kg",
        help=f"Over a typical {result['typical_life_years']:.0f}-year life.",
    )

    st.markdown("#### The five flow categories")
    st.caption(result["categories_not_summed"])
    category_fig = go.Figure(
        go.Bar(
            x=[result["flows"][category] for category in CATEGORIES],
            y=[CATEGORY_LABELS[category] for category in CATEGORIES],
            orientation="h",
            marker_color=["#6b5b45", "#5f8f36", "#8a6f4a", "#3d5a80", "#9aa5a0"],
            text=[f"{result['flows'][c]:,.0f} kg" for c in CATEGORIES],
            textposition="auto",
        )
    )
    category_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="kg moved",
        xaxis_type="log",
    )
    st.plotly_chart(category_fig, use_container_width=True)
    st.caption("Log scale — the categories differ by orders of magnitude.")

    focus = concentration(result, top_n=3)
    st.markdown("#### Where the footprint actually sits")
    f1, f2 = st.columns(2)
    f1.metric(
        "Top three materials",
        f"{focus['top_share_of_abiotic'] * 100:.0f}% of the material moved",
    )
    f2.metric(
        "...for this share of the product's mass",
        f"{focus['top_share_of_mass'] * 100:.1f}%",
    )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Material": row["label"],
                    "In the product (g)": round(row["kg"] * 1000, 3),
                    "Abiotic moved (kg)": round(row["abiotic_kg"], 2),
                    "Rucksack ratio": f"{row['ratio']:,.0f} : 1",
                    "Water (kg)": round(row["flows"]["water"], 1),
                }
                for row in result["materials"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### What this is telling you")
    for insight in get_material_insights(result):
        st.markdown(f"- {insight}")

    context = per_capita_context(result["abiotic_per_year"])
    st.metric(
        "Share of a per-capita resource-safe year",
        f"{context['share'] * 100:.1f}%",
        help=f"Against {SUSTAINABLE_ABIOTIC_PER_CAPITA_TONNES:.0f} tonnes of "
             f"abiotic material per person per year.",
    )
    st.caption(context["basis"])

    with st.form("save_material_footprint"):
        name = st.text_input("Save this as", value="")
        if st.form_submit_button("Save") and name.strip():
            try:
                save_footprint(user_id, name, result)
                st.success(f"Saved '{name.strip()}'.")
            except MaterialError as error:
                st.error(str(error))

    st.markdown("---")
    st.markdown("### Products, per year of service")
    st.caption(
        "Per year rather than per unit: a laptop that lasts five years and a "
        "phone that lasts three are not comparable on a per-unit basis."
    )
    comparison = compare_products()
    compare_fig = go.Figure(
        go.Bar(
            x=[row["abiotic_per_year"] for row in comparison],
            y=[row["label"] for row in comparison],
            orientation="h",
            marker_color="#6b5b45",
        )
    )
    compare_fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="kg abiotic material per year of service",
        xaxis_type="log",
    )
    st.plotly_chart(compare_fig, use_container_width=True)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Product": row["label"],
                    "Life (yr)": row["life_years"],
                    "Mass (kg)": round(row["direct_mass_kg"], 2),
                    "Abiotic (kg)": round(row["abiotic_kg"], 1),
                    "Ratio": f"{row['ratio']:,.0f} : 1",
                    "Per year (kg)": round(row["abiotic_per_year"], 1),
                }
                for row in comparison
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Ore grade
# ---------------------------------------------------------------------------
with tab_grade:
    st.markdown("### How much of a metal's footprint is geology")
    st.caption(
        "The rucksack of a mined metal scales inversely with ore grade. Grades "
        "have been falling for a century, so the same kilogram of copper moves "
        "roughly twice the rock it used to. That is not something a process "
        "improvement can address."
    )

    mined = [
        key for key in list_materials()
        if get_material(key)["reference_grade"] is not None
    ]
    metal = st.selectbox(
        "Metal",
        mined,
        index=mined.index("copper"),
        format_func=lambda k: MATERIALS[k]["label"],
        key="mf_grade_metal",
    )
    st.caption(get_material(metal)["note"])

    rows = grade_sensitivity(metal)
    grade_fig = go.Figure(
        go.Scatter(
            x=[row["grade_percent"] for row in rows],
            y=[row["abiotic_kg_per_kg"] for row in rows],
            mode="lines+markers",
            line=dict(color="#6b5b45", width=3),
            marker=dict(
                size=[16 if row["is_reference"] else 9 for row in rows],
                color=[
                    "#e07a5f" if row["is_reference"] else "#6b5b45"
                    for row in rows
                ],
            ),
        )
    )
    grade_fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Ore grade (%)",
        yaxis_title="kg of rock moved per kg of metal",
    )
    grade_fig.update_xaxes(autorange="reversed")
    st.plotly_chart(grade_fig, use_container_width=True)
    st.caption(
        "The highlighted point is today's typical grade. Everything to the "
        "right of it is where the industry is heading."
    )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Ore grade": f"{row['grade_percent']:.4g}%",
                    "kg moved per kg metal": round(row["abiotic_kg_per_kg"], 1),
                    "Relative to today": f"{row['relative_to_reference']:.2f}×",
                    "Today": "←" if row["is_reference"] else "",
                }
                for row in rows
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### Rucksack ratios across the table")
    ratio_rows = sorted(
        list_materials(), key=lambda k: -MATERIALS[k]["abiotic"]
    )
    ratio_fig = go.Figure(
        go.Bar(
            x=[MATERIALS[k]["abiotic"] for k in ratio_rows],
            y=[MATERIALS[k]["label"] for k in ratio_rows],
            orientation="h",
            marker_color="#6b5b45",
        )
    )
    ratio_fig.update_layout(
        height=560,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="kg abiotic material moved per kg delivered",
        xaxis_type="log",
    )
    st.plotly_chart(ratio_fig, use_container_width=True)
    st.caption(
        "Six orders of magnitude from concrete to palladium, which is why "
        "there is no average material in this module."
    )


# ---------------------------------------------------------------------------
# Criticality
# ---------------------------------------------------------------------------
with tab_critical:
    st.markdown("### Depletion and criticality are different questions")
    st.caption(
        "Depletion asks how much of a finite stock a use consumes. Criticality "
        "asks whether the supply can be interrupted. Cobalt is abundant in the "
        "crust and critical in practice, and a single score would make both "
        "unreadable."
    )

    family = st.selectbox(
        "Family",
        ["all"] + list_families(),
        format_func=lambda f: f.replace("_", " ").title(),
        key="mf_family",
    )
    keys = list_materials() if family == "all" else list_materials(family)

    rows = []
    for key in keys:
        crit = criticality(key)
        rows.append({
            "Material": crit["label"],
            "Depletion (kg Sb-eq/kg)": f"{crit['adp_per_kg']:.3g}",
            "Supply concentration (HHI)": crit["hhi"],
            "Verdict": crit["concentration_verdict"],
            "Substitutability": crit["substitutability"],
            "Recycling input rate": f"{crit['recycling_input_rate'] * 100:.0f}%",
            "Abundant and critical": "yes" if crit["abundant_but_critical"] else "",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("#### The two dimensions plotted against each other")
    scatter = go.Figure(
        go.Scatter(
            x=[max(criticality(k)["adp_per_kg"], 1e-11) for k in keys],
            y=[criticality(k)["hhi"] for k in keys],
            mode="markers+text",
            text=[MATERIALS[k]["label"] for k in keys],
            textposition="top center",
            marker=dict(
                size=14,
                color=[
                    "#e07a5f" if criticality(k)["abundant_but_critical"]
                    else "#3d5a80"
                    for k in keys
                ],
            ),
        )
    )
    scatter.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="Depletion potential (kg Sb-eq per kg, log scale)",
        yaxis_title="Supply concentration (HHI)",
        xaxis_type="log",
    )
    st.plotly_chart(scatter, use_container_width=True)
    st.caption(
        "Top left is the quadrant a single score would hide: geologically "
        "abundant and strategically fragile. Highlighted materials sit there."
    )

    st.markdown("#### Depletion for a specific mass")
    d1, d2 = st.columns(2)
    with d1:
        depletion_material = st.selectbox(
            "Material",
            list_materials(),
            format_func=lambda k: MATERIALS[k]["label"],
            key="mf_depletion_material",
        )
    with d2:
        depletion_kg = st.number_input(
            "kg", min_value=0.0, value=1.0, step=0.5, key="mf_depletion_kg"
        )
    depletion = abiotic_depletion(depletion_material, depletion_kg)
    st.metric("Depletion", f"{depletion['adp_sb_eq']:.4g} kg Sb-eq")
    st.caption(depletion["basis"])


# ---------------------------------------------------------------------------
# Life extension
# ---------------------------------------------------------------------------
with tab_life:
    st.markdown("### The size of the prize for using things longer")
    st.caption(
        "src.utils.circular_economy_engine.py argues for repair and reuse without a "
        "metric that shows how much it is worth. Material footprint is that "
        "metric, and it is a far more striking number than the carbon saving."
    )

    l1, l2 = st.columns(2)
    with l1:
        life_product = st.selectbox(
            "Product",
            list_products(),
            index=list_products().index("smartphone"),
            format_func=lambda k: get_product(k)["label"],
            key="mf_life_product",
        )
        horizon = st.number_input(
            "Horizon (years)", min_value=5.0, value=20.0, step=5.0,
            key="mf_horizon",
        )
    with l2:
        life_before = st.number_input(
            "Current service life (years)",
            min_value=0.5,
            value=float(get_product(life_product)["typical_life_years"]),
            step=0.5,
            key="mf_life_before",
        )
        life_after = st.number_input(
            "Extended service life (years)",
            min_value=0.5,
            value=float(get_product(life_product)["typical_life_years"]) * 2,
            step=0.5,
            key="mf_life_after",
        )

    secondary = st.slider(
        "Share of replacement material from end-of-life recycling",
        min_value=0.0, max_value=1.0, value=0.3, step=0.05,
        key="mf_secondary",
        help="Capped at what the recycling input rates of this product's own "
             "materials can deliver.",
    )

    try:
        saving = circularity_saving(
            life_product, life_before, life_after, horizon, secondary
        )
    except MaterialError as error:
        st.error(str(error))
        st.stop()

    s1, s2, s3 = st.columns(3)
    s1.metric(
        f"Over {horizon:.0f} years, as-is",
        f"{saving['abiotic_before_kg']:,.0f} kg",
    )
    s2.metric(
        "With the longer life",
        f"{saving['abiotic_after_kg']:,.0f} kg",
    )
    s3.metric(
        "Avoided by life extension alone",
        f"{saving['avoided_kg']:,.0f} kg",
        delta=f"-{saving['avoided_share'] * 100:.0f}%",
    )

    life_fig = go.Figure(
        go.Bar(
            x=["As-is", "Longer life"],
            y=[saving["abiotic_before_kg"], saving["abiotic_after_kg"]],
            marker_color=["#e07a5f", "#5f8f36"],
            text=[
                f"{saving['abiotic_before_kg']:,.0f} kg",
                f"{saving['abiotic_after_kg']:,.0f} kg",
            ],
            textposition="auto",
        )
    )
    life_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg abiotic material over the horizon",
    )
    st.plotly_chart(life_fig, use_container_width=True)

    st.info(
        f"Recycling contributes a further **{saving['secondary_avoided_kg']:,.0f} "
        f"kg** on top, at the applied secondary share of "
        f"{saving['secondary_share_applied'] * 100:.0f}%. It is reported "
        f"separately so life extension is not credited with a saving that has "
        f"nothing to do with it."
    )

    if saving["secondary_capped"]:
        st.warning(
            f"You asked for {saving['secondary_share_requested'] * 100:.0f}% "
            f"secondary material. This product's own materials can deliver at "
            f"most {saving['achievable_secondary_share'] * 100:.0f}%, so the "
            f"model used that."
        )
    st.caption(saving["recycling_caveat"])


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved footprints")
    footprints = get_footprints(user_id)
    if not footprints:
        st.info("Nothing saved yet. Work out a product and save it.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": row["name"],
                        "Product mass (kg)": round(row["direct_mass_kg"], 2),
                        "Abiotic moved (kg)": round(row["abiotic_kg"], 1),
                        "Ratio": f"{row['ratio']:,.0f} : 1",
                        "Saved": row["created_at"],
                    }
                    for row in footprints
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        total = sum(row["abiotic_kg"] for row in footprints)
        st.metric(
            "Combined abiotic material across saved items",
            f"{total:,.0f} kg",
        )
        st.caption(per_capita_context(total)["basis"])

        to_delete = st.selectbox(
            "Remove a saved footprint",
            [row["id"] for row in footprints],
            format_func=lambda i: next(
                row["name"] for row in footprints if row["id"] == i
            ),
            key="mf_delete",
        )
        if st.button("Delete", key="mf_delete_button"):
            if delete_footprint(user_id, to_delete):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Could not delete that footprint.")

    st.markdown("---")
    st.caption(
        "Rucksack factors are generic and derived from published MIPS work. "
        "A specific mine will differ, sometimes considerably, and the ordering "
        "between materials is far more robust than any individual figure."
    )
