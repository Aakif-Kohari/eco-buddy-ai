"""Streamlit card components for the Carbon Offset Marketplace."""

import streamlit as st
from typing import List, Dict
from offset_types import (
    OffsetProject, OffsetPurchase, UserOffsetPortfolio, OffsetImpact,
    ProjectStatus, OffsetCategory, CATEGORY_ICONS, CATEGORY_COLORS,
    SDG_GOAL_LABELS, VerificationStandard,
)


def render_project_card(project: OffsetProject, show_details: bool = True):
    """Render a carbon offset project card."""
    icon = CATEGORY_ICONS.get(project.category, "🌍")
    color = CATEGORY_COLORS.get(project.category, "#22c55e")
    fill = project.funding_percent
    status_color = "#22c55e" if project.status == ProjectStatus.ACTIVE else "#f59e0b"
    status_label = project.status.value.title()

    stars = "★" * int(project.rating) + "☆" * (5 - int(project.rating))

    sdg_html = ""
    for sdg in project.sdg_goals[:4]:
        label = SDG_GOAL_LABELS.get(sdg, f"SDG {sdg}")
        sdg_html += f"""<span style='
            display: inline-block;
            padding: 1px 6px;
            background: rgba(34,197,94,0.1);
            color: #16a34a;
            border-radius: 6px;
            font-size: 9px;
            font-weight: 600;
            margin-right: 3px;
            margin-bottom: 3px;
        '>{label}</span>"""

    tags_html = ""
    for tag in project.tags[:3]:
        tags_html += f"""<span style='
            display: inline-block;
            padding: 1px 6px;
            background: rgba(107,114,128,0.1);
            color: #6b7280;
            border-radius: 6px;
            font-size: 9px;
            font-weight: 500;
            margin-right: 3px;
        '>{tag}</span>"""

    details_html = ""
    if show_details:
        details_html = f"""
        <div style='display: flex; gap: 16px; margin: 10px 0;'>
            <div style='text-align: center;'>
                <div style='font-size: 16px; font-weight: 800; color: {color};'>{project.tons_remaining:,.0f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Tons Left</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 16px; font-weight: 800; color: #111827;'>${project.price_per_ton:.2f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Per Ton</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 16px; font-weight: 800; color: #0ea5e9;'>{project.annual_reduction_tons:,.0f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Annual Tons</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 14px; color: #f59e0b;'>{stars}</div>
                <div style='font-size: 9px; color: #9ca3af;'>{project.review_count} reviews</div>
            </div>
        </div>
        """

    st.markdown(f"""
    <div style='
        padding: 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.97), rgba(240,253,244,0.85));
        border: 1px solid rgba(0,0,0,0.06);
        border-left: 4px solid {color};
        border-radius: 16px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.05);
        margin-bottom: 16px;
        transition: transform 180ms ease, box-shadow 180ms ease;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 6px;'>
            <span style='font-size: 22px;'>{icon}</span>
            <span style='
                padding: 2px 8px;
                background: {color}18;
                color: {color};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
            '>{project.category.value.replace('_', ' ')}</span>
            <span style='
                margin-left: auto;
                padding: 2px 8px;
                background: {status_color}18;
                color: {status_color};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
            '>{status_label}</span>
        </div>
        <div style='font-size: 16px; font-weight: 800; color: #111827; margin-bottom: 4px;'>{project.name}</div>
        <div style='font-size: 11px; color: #6b7280; margin-bottom: 4px;'>📍 {project.location} · {project.continent}</div>
        <div style='font-size: 11px; color: #6b7280; margin-bottom: 4px;'>📋 {project.verification.value}</div>
        <div style='font-size: 12px; color: #374151; line-height: 1.5; margin-bottom: 8px;'>{project.description}</div>
        {details_html}
        <div style='width: 100%; height: 6px; background: #e5e7eb; border-radius: 999px; overflow: hidden; margin-bottom: 8px;'>
            <div style='width: {fill}%; height: 100%; background: linear-gradient(90deg, {color}, {color}cc); border-radius: 999px;'></div>
        </div>
        <div style='display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af; margin-bottom: 8px;'>
            <span>${project.total_funding_usd:,.0f} / ${project.funding_goal_usd:,.0f}</span>
            <span>{fill:.0f}% funded</span>
        </div>
        <div style='margin-bottom: 6px;'>{sdg_html}</div>
        <div>{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)


def render_purchase_card(purchase: OffsetPurchase):
    """Render a purchase history card."""
    status_colors = {
        "completed": ("#22c55e", "✅ Completed"),
        "pending": ("#f59e0b", "⏳ Pending"),
        "refunded": ("#ef4444", "↩️ Refunded"),
        "failed": ("#ef4444", "❌ Failed"),
    }
    color, label = status_colors.get(purchase.transaction_status.value, ("#6b7280", "Unknown"))

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 12px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
            <span style='font-size: 13px; font-weight: 700; color: #111827;'>{purchase.project_name}</span>
            <span style='padding: 2px 8px; background: {color}18; color: {color}; border-radius: 8px; font-size: 10px; font-weight: 700;'>{label}</span>
        </div>
        <div style='display: flex; gap: 16px; font-size: 12px; color: #6b7280;'>
            <span>🌿 {purchase.tons_purchased:.2f} tons</span>
            <span>💰 ${purchase.total_cost:.2f}</span>
            <span>📅 {purchase.purchase_date}</span>
        </div>
        <div style='font-size: 10px; color: #9ca3af; margin-top: 4px;'>Certificate: {purchase.certificate_id}</div>
    </div>
    """, unsafe_allow_html=True)


def render_portfolio_summary(portfolio: UserOffsetPortfolio):
    """Render user portfolio summary card."""
    impact = _calc_impact(portfolio.total_tons_offset)

    st.markdown(f"""
    <div style='
        padding: 24px;
        background: linear-gradient(145deg, rgba(34,197,94,0.06), rgba(14,165,233,0.04));
        border: 1px solid rgba(74,222,128,0.2);
        border-radius: 18px;
        margin-bottom: 20px;
    '>
        <div style='font-size: 18px; font-weight: 800; color: #111827; margin-bottom: 12px;'>🌿 Your Offset Portfolio</div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px;'>
            <div style='text-align: center;'>
                <div style='font-size: 28px; font-weight: 800; color: #22c55e;'>{portfolio.total_tons_offset:.2f}</div>
                <div style='font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: 600;'>Tons Offset</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 28px; font-weight: 800; color: #0ea5e9;'>${portfolio.total_spent_usd:.2f}</div>
                <div style='font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: 600;'>Total Spent</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 28px; font-weight: 800; color: #8b5cf6;'>{portfolio.projects_supported}</div>
                <div style='font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: 600;'>Projects</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 28px; font-weight: 800; color: #f59e0b;'>${portfolio.avg_price_per_ton:.2f}</div>
                <div style='font-size: 10px; color: #6b7280; text-transform: uppercase; font-weight: 600;'>Avg $/Ton</div>
            </div>
        </div>
        <div style='display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;'>
            <div style='text-align: center; padding: 10px; background: rgba(34,197,94,0.08); border-radius: 12px;'>
                <div style='font-size: 22px;'>🌳</div>
                <div style='font-size: 16px; font-weight: 800; color: #16a34a;'>{impact.trees_planted:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Trees Planted</div>
            </div>
            <div style='text-align: center; padding: 10px; background: rgba(14,165,233,0.08); border-radius: 12px;'>
                <div style='font-size: 22px;'>🏠</div>
                <div style='font-size: 16px; font-weight: 800; color: #0284c7;'>{impact.homes_powered:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Homes Powered</div>
            </div>
            <div style='text-align: center; padding: 10px; background: rgba(239,68,68,0.08); border-radius: 12px;'>
                <div style='font-size: 22px;'>🚗</div>
                <div style='font-size: 16px; font-weight: 800; color: #dc2626;'>{impact.cars_removed:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Cars Removed</div>
            </div>
            <div style='text-align: center; padding: 10px; background: rgba(139,92,246,0.08); border-radius: 12px;'>
                <div style='font-size: 22px;'>✈️</div>
                <div style='font-size: 16px; font-weight: 800; color: #7c3aed;'>{impact.flights_offset:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Flights Offset</div>
            </div>
            <div style='text-align: center; padding: 10px; background: rgba(245,158,11,0.08); border-radius: 12px;'>
                <div style='font-size: 22px;'>🏊</div>
                <div style='font-size: 16px; font-weight: 800; color: #d97706;'>{impact.swimming_pools_saved:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Pools Saved</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_impact_calculator_card(tons: float):
    """Render an impact calculator result card."""
    impact = _calc_impact(tons)

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: linear-gradient(145deg, rgba(34,197,94,0.05), rgba(255,255,255,0.95));
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 14px;
        margin-bottom: 12px;
    '>
        <div style='font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 10px;'>🧮 Impact of {tons:.2f} Tons CO₂</div>
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;'>
            <div style='text-align: center; padding: 8px; background: #f0fdf4; border-radius: 10px;'>
                <div style='font-size: 20px;'>🌳</div>
                <div style='font-size: 14px; font-weight: 800; color: #16a34a;'>{impact.trees_planted:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Trees</div>
            </div>
            <div style='text-align: center; padding: 8px; background: #eff6ff; border-radius: 10px;'>
                <div style='font-size: 20px;'>🚗</div>
                <div style='font-size: 14px; font-weight: 800; color: #2563eb;'>{impact.cars_removed:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Cars/Year</div>
            </div>
            <div style='text-align: center; padding: 8px; background: #faf5ff; border-radius: 10px;'>
                <div style='font-size: 20px;'>✈️</div>
                <div style='font-size: 14px; font-weight: 800; color: #7c3aed;'>{impact.flights_offset:,}</div>
                <div style='font-size: 9px; color: #6b7280;'>Flights</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_certificate_card(certificate_id: str, project_name: str, tons: float, date: str):
    """Render a certificate card."""
    st.markdown(f"""
    <div style='
        padding: 20px;
        background: linear-gradient(145deg, #fefce8, #fffbeb);
        border: 2px solid #f59e0b;
        border-radius: 14px;
        text-align: center;
        margin-bottom: 12px;
    '>
        <div style='font-size: 28px; margin-bottom: 6px;'>🏆</div>
        <div style='font-size: 10px; color: #92400e; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;'>Carbon Offset Certificate</div>
        <div style='font-size: 16px; font-weight: 800; color: #78350f; margin: 6px 0;'>{project_name}</div>
        <div style='font-size: 13px; color: #92400e;'>{tons:.2f} tons CO₂ offset</div>
        <div style='font-size: 11px; color: #b45309; margin-top: 4px;'>Issued: {date}</div>
        <div style='font-size: 9px; color: #d97706; margin-top: 6px; font-family: monospace;'>ID: {certificate_id}</div>
    </div>
    """, unsafe_allow_html=True)


def render_review_card(review: Dict):
    """Render a review card."""
    stars = "★" * review.get("rating", 5) + "☆" * (5 - review.get("rating", 5))
    verified_badge = "✅ Verified" if review.get("verified") else ""

    st.markdown(f"""
    <div style='
        padding: 12px 16px;
        background: rgba(255,255,255,0.8);
        border: 1px solid rgba(0,0,0,0.05);
        border-radius: 10px;
        margin-bottom: 8px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>
            <span style='font-size: 12px; font-weight: 700; color: #111827;'>{review.get('reviewer', 'Anonymous')}</span>
            <span style='font-size: 11px; color: #f59e0b;'>{stars}</span>
        </div>
        <div style='font-size: 12px; color: #374151; line-height: 1.5;'>{review.get('comment', '')}</div>
        <div style='display: flex; gap: 8px; margin-top: 4px; font-size: 10px; color: #9ca3af;'>
            <span>{review.get('date', '')}</span>
            <span>{verified_badge}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _calc_impact(tons: float):
    """Calculate impact metrics from tons."""
    from offset_types import OffsetImpact
    return OffsetImpact(
        trees_planted=int(tons * 15),
        homes_powered=int(tons * 0.12),
        cars_removed=int(tons * 0.22),
        flights_offset=int(tons * 0.53),
        swimming_pools_saved=int(tons * 0.4),
        co2_saved_tons=round(tons, 2),
        equivalent_years_driving=round(tons * 0.22, 1),
    )
