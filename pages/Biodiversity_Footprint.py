"""What a household's consumption displaces, in species rather than in carbon.

`local_biodiversity.py` says what lives near you. This page says what your
consumption displaces elsewhere, through the land it occupies and the land it
converts — the largest driver of terrestrial biodiversity loss, and the one the
rest of the app has no representation of.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from biodiversity_footprint import (
    AMORTISATION_OPTIONS,
    DEFAULT_AMORTISATION_YEARS,
    LAND_USE_CLASSES,
    REGIONS,
    TAXA,
    BiodiversityError,
    basket_footprint,
    compare_land_uses,
    compare_regions,
    delete_basket,
    get_baskets,
    get_biodiversity_insights,
    get_land_use,
    get_product,
    get_region,
    list_categories,
    list_land_uses,
    list_products,
    list_regions,
    save_basket,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🦋 Consumption Biodiversity Footprint</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Biodiversity is the planetary boundary being crossed fastest, and until "
    "now this app's only representation of it was a catalogue of local species. "
    "This page connects what a household buys to the land it takes."
)

with st.expander("How this is counted, and what it deliberately does not do"):
    st.markdown(
        """
**Occupation and transformation are different impacts.** Occupation is holding
land in production so it cannot recover — a rate, measured in m²·yr.
Transformation is converting it in the first place — a one-off, measured in m²,
whose damage is the recovery period the ecosystem now owes. They are never
summed into one figure, because one is a rate and the other is a stock.

**Two periods are at work and conflating them is the usual error.** Recovery
time is a property of the ecosystem and is not a choice. The attribution window
— how many years of production one conversion is charged against — is a
convention. Twenty years is the conventional choice and the basis this table is
built on.

**Where the hectare is matters more than how many.** A hectare of oil palm in
Borneo and a hectare of barley in Denmark differ by more than an order of
magnitude, because a species lost from an ecoregion where it occurs nowhere else
is lost outright.

**The taxa are reported separately.** Plants, mammals, birds, amphibians and
reptiles disagree about which land use is worst. Aggregating first hides that.

**Nothing here is a point estimate.** These characterisation factors are
uncertain by roughly an order of magnitude — considerably wider than carbon
factors — so every headline number carries a range.

**This is a partial footprint.** Land use is the largest driver of terrestrial
biodiversity loss and it is not the only one. Overexploitation, invasive
species, pollution and climate change are all outside this page.
        """
    )

st.markdown("---")

tab_basket, tab_sourcing, tab_intensity, tab_saved = st.tabs(
    [
        "🧺 Basket",
        "🌍 Where it came from",
        "🚜 How it was grown",
        "💾 Saved baskets",
    ]
)


# ---------------------------------------------------------------------------
# Basket
# ---------------------------------------------------------------------------
with tab_basket:
    st.markdown("### What a basket displaces")

    if "biodiversity_basket" not in st.session_state:
        st.session_state.biodiversity_basket = {
            "beef_pasture": 15.0,
            "chicken": 25.0,
            "wheat": 60.0,
            "cocoa": 2.0,
            "palm_oil": 8.0,
        }
    if "biodiversity_overrides" not in st.session_state:
        st.session_state.biodiversity_overrides = {}

    category = st.selectbox(
        "Category",
        list_categories(),
        format_func=lambda c: c.title(),
        key="bio_category",
    )
    add_col, qty_col, button_col = st.columns([3, 1, 1])
    with add_col:
        product_key = st.selectbox(
            "Product",
            list_products(category),
            format_func=lambda k: get_product(k)["label"],
            key="bio_product",
        )
    with qty_col:
        quantity = st.number_input(
            "kg", min_value=0.0, value=1.0, step=0.5, key="bio_qty"
        )
    with button_col:
        st.write("")
        st.write("")
        if st.button("Add", use_container_width=True, key="bio_add"):
            current = st.session_state.biodiversity_basket.get(product_key, 0.0)
            st.session_state.biodiversity_basket[product_key] = current + quantity
            st.rerun()

    st.caption(get_product(product_key)["note"])

    basket = {
        k: v for k, v in st.session_state.biodiversity_basket.items() if v > 0
    }

    if not basket:
        st.info("Add at least one product to see a footprint.")
        st.stop()

    window = st.select_slider(
        "Conversion attribution window (years)",
        options=list(AMORTISATION_OPTIONS),
        value=DEFAULT_AMORTISATION_YEARS,
        key="bio_window",
        help="How many years of production one conversion event is charged "
             "against. A longer window spreads the same conversion thinner and "
             "changes the ranking of products.",
    )

    try:
        result = basket_footprint(
            basket,
            amortisation_years=window,
            overrides=st.session_state.biodiversity_overrides,
        )
    except BiodiversityError as error:
        st.error(str(error))
        st.stop()

    band = result["range"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Footprint", f"{result['pdf_m2_yr']:,.0f} PDF·m²·yr")
    m2.metric(
        "Plausible range",
        f"{band['low']:,.0f} – {band['high']:,.0f}",
    )
    m3.metric(
        "Share of a per-capita boundary",
        f"{result['boundary']['share']:.2f}×",
    )

    st.info(result["anchor"]["phrasing"])
    st.caption(result["anchor"]["caveat"])

    st.markdown("#### Occupation versus transformation")
    st.caption(
        "Occupation is land held out of nature. Transformation is land taken "
        "from nature now. The second is the part a sourcing change can remove "
        "outright; the first needs less consumption."
    )
    split_fig = go.Figure(
        go.Bar(
            x=["Occupation", "Transformation"],
            y=[
                result["occupation_pdf_m2_yr"],
                result["transformation_pdf_m2_yr"],
            ],
            marker_color=["#5f8f36", "#e07a5f"],
            text=[
                f"{result['occupation_pdf_m2_yr']:,.0f}",
                f"{result['transformation_pdf_m2_yr']:,.0f}",
            ],
            textposition="auto",
        )
    )
    split_fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="PDF·m²·yr",
    )
    st.plotly_chart(split_fig, use_container_width=True)

    st.markdown("#### By taxon")
    st.caption(result["taxon_disagreement"]["verdict"] or "")
    taxon_fig = go.Figure(
        go.Bar(
            x=[result["by_taxon"][taxon] for taxon in TAXA],
            y=[taxon.title() for taxon in TAXA],
            orientation="h",
            marker_color="#3d5a80",
            text=[f"{result['by_taxon'][t]:,.0f}" for t in TAXA],
            textposition="auto",
        )
    )
    taxon_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="PDF·m²·yr",
    )
    st.plotly_chart(taxon_fig, use_container_width=True)

    st.markdown("#### What this basket is telling you")
    for insight in get_biodiversity_insights(result):
        st.markdown(f"- {insight}")

    st.markdown("#### Contribution by product")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Product": row["label"],
                    "kg": round(row["kg"], 2),
                    "PDF·m²·yr": round(row["pdf_m2_yr"]),
                    "Transformation share": f"{row['transformation_share'] * 100:.0f}%",
                    "Region assumed": REGIONS[row["region"]]["label"],
                    "Land use assumed": LAND_USE_CLASSES[row["land_use"]]["label"],
                }
                for row in result["items"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.warning(result["scope_limitation"])

    clear_col, save_col = st.columns([1, 3])
    with clear_col:
        if st.button("Clear basket", key="bio_clear"):
            st.session_state.biodiversity_basket = {}
            st.session_state.biodiversity_overrides = {}
            st.rerun()
    with save_col:
        with st.form("save_biodiversity_basket"):
            name = st.text_input("Save this basket as", value="")
            if st.form_submit_button("Save") and name.strip():
                try:
                    save_basket(user_id, name, result)
                    st.success(f"Saved '{name.strip()}'.")
                except BiodiversityError as error:
                    st.error(str(error))


# ---------------------------------------------------------------------------
# Sourcing
# ---------------------------------------------------------------------------
with tab_sourcing:
    st.markdown("### Where it came from")
    st.caption(
        "Sourcing moves this number by more than switching product does. If "
        "you know where something actually came from, override the default "
        "here — those defaults are the assumptions worth challenging first."
    )

    basket = {
        k: v for k, v in st.session_state.get("biodiversity_basket", {}).items()
        if v > 0
    }
    if not basket:
        st.info("Build a basket on the first tab.")
    else:
        override_product = st.selectbox(
            "Product",
            sorted(basket),
            format_func=lambda k: get_product(k)["label"],
            key="bio_override_product",
        )
        current = st.session_state.biodiversity_overrides.get(override_product, {})
        default_region = current.get(
            "region", get_product(override_product)["default_region"]
        )

        o1, o2 = st.columns(2)
        with o1:
            chosen_region = st.selectbox(
                "Sourcing region",
                list_regions(),
                index=list_regions().index(default_region),
                format_func=lambda k: REGIONS[k]["label"],
                key="bio_override_region",
            )
        with o2:
            st.write("")
            st.write("")
            if st.button("Apply", use_container_width=True, key="bio_apply_region"):
                st.session_state.biodiversity_overrides.setdefault(
                    override_product, {}
                )["region"] = chosen_region
                st.rerun()

        st.caption(get_region(chosen_region)["note"])

        st.markdown("#### The same product from every region")
        st.caption(
            "Counterfactual by design — oil palm does not grow on temperate "
            "grassland. The point is how far the regional weight alone moves "
            "the answer. Read the rows that are physically possible."
        )
        rows = compare_regions(
            override_product, basket[override_product], amortisation_years=
            st.session_state.get("bio_window", DEFAULT_AMORTISATION_YEARS),
        )
        region_fig = go.Figure(
            go.Bar(
                x=[row["pdf_m2_yr"] for row in rows],
                y=[row["label"] for row in rows],
                orientation="h",
                marker_color="#78a945",
            )
        )
        region_fig.update_layout(
            height=440,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="PDF·m²·yr",
        )
        st.plotly_chart(region_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Region": row["label"],
                        "Vulnerability weight": row["vulnerability"],
                        "PDF·m²·yr": round(row["pdf_m2_yr"]),
                        "Why": row["note"],
                    }
                    for row in rows
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        if st.session_state.biodiversity_overrides:
            st.markdown("#### Overrides in force")
            st.json(st.session_state.biodiversity_overrides)
            if st.button("Reset all overrides", key="bio_reset_overrides"):
                st.session_state.biodiversity_overrides = {}
                st.rerun()


# ---------------------------------------------------------------------------
# Intensity
# ---------------------------------------------------------------------------
with tab_intensity:
    st.markdown("### How it was grown")
    st.caption(
        "'Agriculture' is not one thing. Intensive arable, extensive grazing "
        "and agroforestry leave very different residual species abundance on "
        "the same hectare, and for tropical commodity crops that difference is "
        "larger than most substitutions between products."
    )

    i1, i2 = st.columns(2)
    with i1:
        intensity_product = st.selectbox(
            "Product",
            list_products(),
            index=list_products().index("cocoa"),
            format_func=lambda k: get_product(k)["label"],
            key="bio_intensity_product",
        )
    with i2:
        intensity_kg = st.number_input(
            "kg", min_value=0.1, value=5.0, step=1.0, key="bio_intensity_kg"
        )

    intensity_region = st.selectbox(
        "Region",
        list_regions(),
        index=list_regions().index(
            get_product(intensity_product)["default_region"]
        ),
        format_func=lambda k: REGIONS[k]["label"],
        key="bio_intensity_region",
    )

    use_rows = compare_land_uses(
        intensity_product, intensity_kg, region=intensity_region
    )

    use_fig = go.Figure()
    for taxon, color in zip(
        TAXA, ("#2f5e32", "#5f8f36", "#78a945", "#3d5a80", "#8d5a97")
    ):
        use_fig.add_trace(
            go.Bar(
                name=taxon.title(),
                y=[row["label"] for row in use_rows],
                x=[row["by_taxon"][taxon] / len(TAXA) for row in use_rows],
                orientation="h",
                marker_color=color,
            )
        )
    use_fig.update_layout(
        barmode="stack",
        height=440,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="PDF·m²·yr (taxon contributions to the mean)",
        legend=dict(orientation="h", y=-0.18),
    )
    st.plotly_chart(use_fig, use_container_width=True)

    best, worst = use_rows[0], use_rows[-1]
    if best["pdf_m2_yr"] > 0:
        st.success(
            f"**{worst['label']}** is "
            f"{worst['pdf_m2_yr'] / best['pdf_m2_yr']:.1f}× "
            f"**{best['label']}** for the same {intensity_kg:g} kg of "
            f"{get_product(intensity_product)['label'].lower()}."
        )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Land use": row["label"],
                    "PDF·m²·yr": round(row["pdf_m2_yr"]),
                    "Why": row["note"],
                }
                for row in use_rows
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### The classes themselves")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Land use": get_land_use(key)["label"],
                    **{
                        taxon.title(): get_land_use(key)["pdf"][taxon]
                        for taxon in TAXA
                    },
                }
                for key in list_land_uses()
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Fractions of the original species pool absent under each use. These "
        "are local relative losses, not global extinction probabilities: 0.75 "
        "means three quarters of what was on that ground no longer is."
    )


# ---------------------------------------------------------------------------
# Saved baskets
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved baskets")
    baskets = get_baskets(user_id)
    if not baskets:
        st.info("Nothing saved yet. Build a basket and save it.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": row["name"],
                        "PDF·m²·yr": round(row["pdf_m2_yr"]),
                        "Transformation share": (
                            f"{row['transformation_share'] * 100:.0f}%"
                        ),
                        "Saved": row["created_at"],
                    }
                    for row in baskets
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        if len(baskets) > 1:
            trend = go.Figure(
                go.Scatter(
                    x=[row["created_at"] for row in reversed(baskets)],
                    y=[row["pdf_m2_yr"] for row in reversed(baskets)],
                    mode="lines+markers",
                    line=dict(color="#5f8f36", width=3),
                )
            )
            trend.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=20, b=10),
                yaxis_title="PDF·m²·yr",
            )
            st.plotly_chart(trend, use_container_width=True)
            st.caption(
                "Movement between saved baskets is only meaningful if the "
                "sourcing assumptions were the same in both. They are stored "
                "with each basket for exactly that reason."
            )

        to_delete = st.selectbox(
            "Remove a basket",
            [row["id"] for row in baskets],
            format_func=lambda i: next(
                row["name"] for row in baskets if row["id"] == i
            ),
            key="bio_delete",
        )
        if st.button("Delete", key="bio_delete_button"):
            if delete_basket(user_id, to_delete):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Could not delete that basket.")
