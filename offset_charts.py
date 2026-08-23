"""Chart visualizations for the Carbon Offset Marketplace."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict
from offset_types import (
    OffsetProject, MarketplaceStats, OffsetCategory,
    CATEGORY_COLORS,
)


def create_marketplace_overview(stats: MarketplaceStats) -> go.Figure:
    """Create a multi-metric overview chart."""
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Tons Sold", "Total Revenue", "Avg Price/Ton"),
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
    )

    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=stats.total_tons_sold,
        number={"font": {"size": 36, "color": "#22c55e"}},
        delta={"reference": stats.total_tons_sold * 0.85, "suffix": " tons"},
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=stats.total_funding_usd,
        number={"font": {"size": 36, "color": "#0ea5e9"}, "prefix": "$"},
        delta={"reference": stats.total_funding_usd * 0.8, "prefix": "$"},
    ), row=1, col=2)

    fig.add_trace(go.Indicator(
        mode="number",
        value=stats.avg_price_per_ton,
        number={"font": {"size": 36, "color": "#8b5cf6"}, "prefix": "$", "suffix": "/ton"},
    ), row=1, col=3)

    fig.update_layout(
        height=200,
        margin=dict(t=40, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_category_distribution(stats: MarketplaceStats) -> go.Figure:
    """Create a pie chart of project categories."""
    labels = list(stats.top_categories.keys())
    values = list(stats.top_categories.values())
    colors = [CATEGORY_COLORS.get(OffsetCategory(l), "#6b7280") for l in labels]

    fig = go.Figure(go.Pie(
        labels=[l.replace("_", " ").title() for l in labels],
        values=values,
        hole=0.5,
        marker=dict(colors=colors, line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=11, color="#374151"),
        hovertemplate="<b>%{label}</b><br>%{value} projects<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Projects by Category", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_geographic_distribution(stats: MarketplaceStats) -> go.Figure:
    """Create a bar chart of projects by continent."""
    labels = list(stats.top_continents.keys())
    values = list(stats.top_continents.values())
    colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker=dict(color=colors[:len(labels)], cornerradius=6),
        text=values,
        textposition="auto",
        textfont=dict(size=12, color="white"),
    ))

    fig.update_layout(
        title=dict(text="Projects by Region", font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=40, l=40, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#374151")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11, color="#9ca3af")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_monthly_sales_chart(monthly_data: List[Dict]) -> go.Figure:
    """Create a grouped bar chart of monthly sales."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    periods = [d["period"] for d in monthly_data]
    tons = [d["tons_sold"] for d in monthly_data]
    revenue = [d["revenue"] for d in monthly_data]

    fig.add_trace(go.Bar(
        x=periods,
        y=tons,
        name="Tons Sold",
        marker=dict(color="#22c55e", cornerradius=4),
        text=[f"{t:,.0f}" for t in tons],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=periods,
        y=revenue,
        name="Revenue ($)",
        mode="lines+markers",
        line=dict(color="#0ea5e9", width=3, shape="spline"),
        marker=dict(size=8, color="#0ea5e9", line=dict(width=2, color="white")),
    ), secondary_y=True)

    fig.update_layout(
        title=dict(text="Monthly Marketplace Performance", font=dict(size=14, color="#374151")),
        height=320,
        margin=dict(t=40, b=40, l=50, r=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#9ca3af")),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11, color="#9ca3af"), title="Tons"),
        yaxis2=dict(tickfont=dict(size=11, color="#9ca3af"), title="Revenue ($)", gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_price_comparison_chart(projects: List[OffsetProject]) -> go.Figure:
    """Create a scatter chart comparing price vs rating."""
    names = [p.name[:25] + "..." if len(p.name) > 25 else p.name for p in projects]
    prices = [p.price_per_ton for p in projects]
    ratings = [p.rating for p in projects]
    sizes = [max(p.tons_sold / 500, 10) for p in projects]
    colors = [CATEGORY_COLORS.get(p.category, "#6b7280") for p in projects]
    categories = [p.category.value.replace("_", " ").title() for p in projects]

    fig = go.Figure(go.Scatter(
        x=prices,
        y=ratings,
        mode="markers+text",
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.8,
            line=dict(width=1, color="white"),
        ),
        text=names,
        textposition="top center",
        textfont=dict(size=9, color="#6b7280"),
        hovertemplate="<b>%{text}</b><br>Price: $%{x:.2f}/ton<br>Rating: %{y:.1f}/5<br>Category: " +
                      "<br>".join(categories) + "<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Price vs Rating", font=dict(size=14, color="#374151")),
        height=350,
        margin=dict(t=40, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Price per Ton ($)", showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11, color="#9ca3af")),
        yaxis=dict(title="Rating", range=[3, 5.2], showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=11, color="#9ca3af")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_funding_progress_chart(projects: List[OffsetProject]) -> go.Figure:
    """Create a horizontal bar chart of funding progress."""
    top = sorted(projects, key=lambda p: p.funding_percent, reverse=True)[:10]
    names = [p.name[:30] + "..." if len(p.name) > 30 else p.name for p in top]
    percents = [p.funding_percent for p in top]
    colors = [CATEGORY_COLORS.get(p.category, "#6b7280") for p in top]

    fig = go.Figure(go.Bar(
        x=percents,
        y=names,
        orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{p:.0f}%" for p in percents],
        textposition="auto",
        textfont=dict(size=10, color="white"),
    ))

    fig.add_vline(x=100, line_dash="dash", line_color="#d1d5db", line_width=1)

    fig.update_layout(
        title=dict(text="Funding Progress", font=dict(size=14, color="#374151")),
        height=380,
        margin=dict(t=40, b=20, l=180, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 110], showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10, color="#9ca3af")),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10, color="#374151")),
        font={"family": "Inter, sans-serif"},
    )
    return fig


def create_verification_distribution(projects: List[OffsetProject]) -> go.Figure:
    """Create a donut chart of verification standards."""
    from collections import Counter
    standards = Counter(p.verification.value for p in projects)
    labels = list(standards.keys())
    values = list(standards.values())
    colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors[:len(labels)], line=dict(width=2, color="white")),
        textinfo="percent+label",
        textfont=dict(size=10, color="#374151"),
    ))

    fig.update_layout(
        title=dict(text="Verification Standards", font=dict(size=14, color="#374151")),
        height=300,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=9)),
        font={"family": "Inter, sans-serif"},
    )
    return fig
