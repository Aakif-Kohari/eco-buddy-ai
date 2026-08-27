"""Spend-based consumption footprint by input-output analysis.

A per-category emission factor accounts for what the seller emitted and nothing
for what the seller bought in order to sell it. This page applies the whole
supply chain instead, and shows the gap between the two.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.business.eeio_spend import (
    BASE_PRICE_YEAR,
    DEFLATORS,
    DIRECT_INTENSITY,
    PHYSICAL_OVERLAP,
    SECTORS,
    EEIOError,
    column_sums,
    declare_overlap,
    delete_profile,
    get_eeio_insights,
    get_profiles,
    get_sector,
    hybrid_footprint,
    list_sectors,
    multipliers,
    save_profile,
    sensitivity,
    spend_footprint,
    structural_paths,
    tier_contributions,
    total_intensities,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🧾 Spend Footprint</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A per-category emission factor tells you what the seller emitted. It tells "
    "you nothing about the farm, the freight, the packaging or the factory that "
    "sold to the seller — and for anything you buy from a shop or a restaurant, "
    "that is most of the footprint."
)

with st.expander("Why one factor per category is not enough"):
    st.markdown(
        """
The upstream of a sector is the upstream of *its* suppliers, recursively, and
that recursion does not stop: steel needs coke, coke needs mining, mining needs
steel. You cannot fix it by adding tiers one at a time, because there is no
tier at which it ends.

Input-output analysis solves it in closed form. If `A` holds how much of every
sector each sector buys per unit of output, then the total requirement is

```
(I - A)^-1 = I + A + A^2 + A^3 + ...
```

and the total emission intensity is `e (I - A)^-1`, where `e` is the direct
intensity of each sector. Every tier is in there, including the ones that loop
back on themselves.

**Three things this page also does that a flat factor cannot:**

- **Margins.** What you pay in a shop includes the shop's markup and the
  delivery. Those belong to retail and freight, and carry *their* footprints —
  not the farm's, multiplied by the farm's supply chain.
- **Deflation.** Nominal money from a high-inflation year, run through a factor
  built in an earlier year, reports inflation as emissions growth.
- **Overlap.** If your electricity is already counted in kWh somewhere else,
  counting the electricity bill here too puts it in twice. Every sector below
  declares what it overlaps with.
"""
    )

tab_spend, tab_paths, tab_table, tab_saved = st.tabs(
    ["Your spending", "Where it comes from", "The table", "Saved profiles"]
)


with tab_spend:
    st.subheader("Annual spending by category")
    st.caption(
        "Purchaser prices — what you actually paid, including the shop's markup. "
        "Leave anything you do not spend on at zero."
    )

    year = st.selectbox(
        "Which year is this money from?",
        options=sorted(DEFLATORS, reverse=True),
        index=0,
        help=(
            f"Spending is deflated to {BASE_PRICE_YEAR} prices before the "
            "intensities are applied, so inflation is not counted as carbon."
        ),
    )

    spend: dict[str, float] = {}
    sector_keys = list_sectors()
    columns = st.columns(2)
    for n, key in enumerate(sector_keys):
        entry = SECTORS[key]
        with columns[n % 2]:
            spend[key] = st.number_input(
                entry["label"],
                min_value=0.0,
                value=0.0,
                step=50.0,
                key=f"spend_{key}",
                help=entry["examples"],
            )

    apply_margins = st.checkbox(
        "Split retail and transport margins out of the price",
        value=True,
        help=(
            "On by default. Turning it off applies the producing sector's "
            "supply chain multiplier to the shopkeeper's markup, which "
            "overstates."
        ),
    )

    active = {key: value for key, value in spend.items() if value > 0}

    if not active:
        st.info("Enter some spending above to see a footprint.")
    else:
        try:
            result = spend_footprint(active, year=year, apply_margins=apply_margins)
        except EEIOError as exc:
            st.error(str(exc))
            st.stop()

        left, middle, right = st.columns(3)
        left.metric("Total footprint", f"{result['total_kg']:,.0f} kg CO2e")
        middle.metric(
            "Direct factors only",
            f"{result['direct_only_kg']:,.0f} kg",
            help="What a per-category emission factor would have reported.",
        )
        right.metric(
            "Understated by",
            f"{result['understatement_factor']:.2f}x",
            help="How much the supply chain adds on top of the direct factors.",
        )

        st.caption(
            f"{result['nominal_spend']:,.0f} of {year} money is "
            f"{result['real_spend']:,.0f} in {BASE_PRICE_YEAR} prices."
        )

        frame = pd.DataFrame(result["lines"])
        chart = go.Figure()
        chart.add_trace(
            go.Bar(
                x=frame["label"],
                y=frame["direct_only_kg"],
                name="Direct (the seller's own emissions)",
                marker_color="#94a3b8",
            )
        )
        chart.add_trace(
            go.Bar(
                x=frame["label"],
                y=frame["total_kg"] - frame["direct_only_kg"],
                name="Upstream (their supply chain)",
                marker_color="#0f766e",
            )
        )
        chart.update_layout(
            barmode="stack",
            height=460,
            yaxis_title="kg CO2e",
            xaxis_title="",
            legend=dict(orientation="h", y=1.08),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(chart, use_container_width=True)
        st.caption(
            "The grey block is what a flat factor would have counted. The "
            "coloured block is everything it would have missed."
        )

        display = frame[[
            "label", "purchaser_spend", "producer_spend", "direct_only_kg", "total_kg"
        ]].rename(columns={
            "label": "Sector",
            "purchaser_spend": "You paid",
            "producer_spend": "At producer prices",
            "direct_only_kg": "Direct kg",
            "total_kg": "Total kg",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(
            "Retail and freight appear even if you entered nothing against them "
            "— that is the margin taken out of everything else."
        )

        st.markdown("#### What this says")
        for line in get_eeio_insights(result):
            st.markdown(f"- {line}")

        overlap = declare_overlap(active)
        if overlap:
            st.markdown("#### Overlap with physical measurements")
            st.warning(
                "These categories are usually also measured directly — in kWh, "
                "in litres, in kilometres. If they are counted somewhere else "
                "in your inventory, they are in it twice."
            )
            st.dataframe(
                pd.DataFrame(overlap)[["label", "physical_category", "spend"]].rename(
                    columns={
                        "label": "Sector",
                        "physical_category": "Also measured as",
                        "spend": "Spend",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            with st.form("hybrid_form"):
                st.markdown(
                    "**Already have physical numbers?** Enter them and the "
                    "matching spend is dropped rather than added twice."
                )
                physical: dict[str, float] = {}
                categories = sorted({row["physical_category"] for row in overlap})
                hybrid_columns = st.columns(min(3, len(categories)))
                for n, category in enumerate(categories):
                    with hybrid_columns[n % len(hybrid_columns)]:
                        entered = st.number_input(
                            f"{category} (kg CO2e)",
                            min_value=0.0,
                            value=0.0,
                            step=50.0,
                            key=f"physical_{category}",
                        )
                        if entered > 0:
                            physical[category] = entered
                if st.form_submit_button("Build a hybrid inventory"):
                    if not physical:
                        st.info("Enter at least one physical figure.")
                    else:
                        hybrid = hybrid_footprint(active, physical, year=year)
                        a, b, c = st.columns(3)
                        a.metric("Hybrid total", f"{hybrid['total_kg']:,.0f} kg")
                        b.metric(
                            "Adding them naively",
                            f"{hybrid['naive_total_kg']:,.0f} kg",
                        )
                        c.metric(
                            "Double count avoided",
                            f"{hybrid['double_count_avoided_kg']:,.0f} kg",
                        )
                        st.caption(
                            "The difference is the part that would have been "
                            "counted twice: physically and again through the bill."
                        )

        st.markdown("#### How much of this is a modelling choice")
        variants = pd.DataFrame(sensitivity(active, year=year))
        variant_chart = px.bar(
            variants,
            x="total_kg",
            y="variant",
            orientation="h",
            hover_data=["note"],
            labels={"total_kg": "kg CO2e", "variant": ""},
        )
        variant_chart.update_traces(marker_color="#0f766e")
        variant_chart.update_layout(
            height=400, margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(variant_chart, use_container_width=True)
        st.caption(
            "The truncated rows are what you get by following the supply chain "
            "only so far up. One tier is exactly what a per-category factor does."
        )

        with st.form("save_profile_form"):
            name = st.text_input("Name this profile", value=f"{year} spending")
            if st.form_submit_button("Save profile"):
                if not name.strip():
                    st.error("Give the profile a name.")
                elif save_profile(user_id, name.strip(), result):
                    st.success("Saved.")
                else:
                    st.error("Could not save the profile.")


with tab_paths:
    st.subheader("Where a sector's footprint actually comes from")
    st.markdown(
        "A number being bigger than you expected is not an argument on its own. "
        "This traces it: which supply chains carry the emissions, and how far up "
        "they sit."
    )

    path_sector = st.selectbox(
        "Sector",
        options=list_sectors(),
        format_func=lambda key: SECTORS[key]["label"],
        index=list_sectors().index("hospitality"),
    )
    path_amount = st.number_input(
        "Spend on it", min_value=1.0, value=1000.0, step=100.0
    )
    depth, cutoff = st.columns(2)
    with depth:
        max_depth = st.slider("How far up the chain to trace", 1, 6, 4)
    with cutoff:
        threshold = st.select_slider(
            "Ignore paths smaller than",
            options=[0.05, 0.02, 0.01, 0.005, 0.001],
            value=0.01,
            format_func=lambda value: f"{value:.1%}",
        )

    paths = structural_paths(
        path_sector, path_amount, max_depth=max_depth, threshold=threshold
    )

    a, b, c = st.columns(3)
    a.metric("Total", f"{paths['total_kg']:,.1f} kg")
    b.metric("Traced", f"{paths['explained_kg']:,.1f} kg")
    c.metric("Too diffuse to name", f"{paths['unexplained_kg']:,.1f} kg")
    st.caption(
        f"{paths['explained_share']:.0%} of the total is accounted for by named "
        "chains. The rest is real — it is spread across too many small paths to "
        "list, which is exactly why adding tiers by hand does not work."
    )

    if paths["paths"]:
        rows = [
            {
                "Chain": " ← ".join(SECTORS[step]["label"] for step in row["path"]),
                "kg CO2e": row["kg"],
                "Share": row["share"],
                "Steps": row["depth"],
            }
            for row in paths["paths"][:25]
        ]
        st.dataframe(
            pd.DataFrame(rows), use_container_width=True, hide_index=True
        )
        st.caption("Read each chain right to left: the money enters on the right.")

    st.markdown("#### Adding one tier at a time")
    tiers = pd.DataFrame(tier_contributions(path_sector, tiers=6))
    tier_chart = go.Figure()
    tier_chart.add_trace(
        go.Bar(
            x=tiers["tier"], y=tiers["added"], name="Added by this tier",
            marker_color="#0f766e",
        )
    )
    tier_chart.add_trace(
        go.Scatter(
            x=tiers["tier"], y=tiers["cumulative"], name="Running total",
            mode="lines+markers", line=dict(color="#b45309", width=3),
            yaxis="y2",
        )
    )
    tier_chart.add_hline(
        y=total_intensities()[path_sector],
        line_dash="dot",
        annotation_text="closed form",
        yref="y2",
    )
    tier_chart.update_layout(
        height=420,
        xaxis_title="Tiers of supply chain included",
        yaxis_title="kg CO2e per unit added",
        yaxis2=dict(title="cumulative", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(tier_chart, use_container_width=True)
    st.caption(
        "The running total approaches the closed form and never reaches it in "
        "finite steps. Any truncation understates; the only question is by how "
        "much."
    )


with tab_table:
    st.subheader("The table underneath")
    st.markdown(
        "Nothing here is a black box, so here is the table. Multipliers say how "
        "much the supply chain adds to each sector's own src.carbon.emissions."
    )

    totals = total_intensities()
    factors = multipliers()
    rows = []
    for key in list_sectors():
        entry = get_sector(key)
        rows.append({
            "Sector": entry["label"],
            "Direct": round(DIRECT_INTENSITY[key], 3),
            "Total": round(totals[key], 3),
            "Multiplier": round(factors[key], 2),
            "Bought in": round(column_sums()[key], 3),
            "Also measured as": PHYSICAL_OVERLAP.get(key) or "—",
        })
    table = pd.DataFrame(rows).sort_values("Multiplier", ascending=False)
    st.dataframe(table, use_container_width=True, hide_index=True)

    multiplier_chart = px.bar(
        table.sort_values("Multiplier"),
        x="Multiplier",
        y="Sector",
        orientation="h",
        labels={"Multiplier": "Total intensity ÷ direct intensity"},
    )
    multiplier_chart.update_traces(marker_color="#0f766e")
    multiplier_chart.add_vline(x=1.0, line_dash="dot")
    multiplier_chart.update_layout(
        height=620, margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(multiplier_chart, use_container_width=True)
    st.caption(
        "Electricity sits near 1 — it emits where it is made, so a direct "
        "factor nearly works. Services sit far above it, because almost "
        "everything they emit was emitted by somebody else on their behalf. A "
        "table where those two were close would be a table with a mistake in it."
    )

    st.markdown(
        "**Every column of the table sums to less than one.** A sector that "
        "consumed a unit of output to produce a unit of output could not produce "
        "anything net, and the inverse of such a table comes back with negative "
        "entries rather than failing. It is checked before every solve."
    )


with tab_saved:
    st.subheader("Saved profiles")
    saved = get_profiles(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for profile in saved:
            with st.expander(
                f"{profile['name']} — {profile['total_kg']:,.0f} kg "
                f"({profile['year']})"
            ):
                a, b, c = st.columns(3)
                a.metric("Spend", f"{profile['nominal_spend']:,.0f}")
                b.metric("Total", f"{profile['total_kg']:,.0f} kg")
                c.metric("Direct only", f"{profile['direct_only_kg']:,.0f} kg")
                detail = profile.get("detail")
                if detail and detail.get("lines"):
                    st.dataframe(
                        pd.DataFrame(detail["lines"])[["label", "total_kg"]].rename(
                            columns={"label": "Sector", "total_kg": "kg CO2e"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                if st.button("Delete", key=f"delete_{profile['id']}"):
                    if delete_profile(profile["id"], user_id):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete it.")
