"""Streamlit card components for the Green Transportation Planner."""

import streamlit as st
from typing import List, Dict
from transport_types import (
    Route, TripLog, Vehicle, EmissionComparison, TransportMode,
    TripCategory, MODE_ICONS, MODE_COLORS, EMISSION_FACTORS,
)


def render_metric_card(
    title: str, value: str, subtitle: str = "",
    icon: str = "📊", delta: str = "", delta_color: str = "normal"
):
    """Render a styled metric card."""
    delta_html = ""
    if delta:
        color = "#22c55e" if delta_color == "normal" else "#ef4444"
        delta_html = f"<div style='margin-top: 4px; font-size: 12px; font-weight: 600; color: {color};'>{delta}</div>"

    st.markdown(f"""
    <div style='
        padding: 18px 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,253,244,0.85));
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 6px;'>
            <span style='font-size: 20px;'>{icon}</span>
            <span style='font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;'>{title}</span>
        </div>
        <div style='font-size: 26px; font-weight: 800; color: #111827; line-height: 1.2;'>{value}</div>
        {f'<div style="font-size: 11px; color: #6b7280; margin-top: 2px;">{subtitle}</div>' if subtitle else ''}
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_route_card(route: Route, index: int = 0):
    """Render a route option card."""
    icon = MODE_ICONS.get(route.mode, "🚗")
    color = MODE_COLORS.get(route.mode, "#6b7280")
    rec_badge = "⭐ Recommended" if route.is_recommended else ""

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: {"linear-gradient(145deg, rgba(34,197,94,0.06), rgba(255,255,255,0.95))" if route.is_recommended else "rgba(255,255,255,0.9)"};
        border: {"2px solid rgba(34,197,94,0.3)" if route.is_recommended else "1px solid rgba(0,0,0,0.06)"};
        border-left: 4px solid {color};
        border-radius: 14px;
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 10px;'>
            <span style='font-size: 24px;'>{icon}</span>
            <div style='flex: 1;'>
                <div style='font-size: 15px; font-weight: 700; color: #111827;'>{route.mode.value.replace('_', ' ').title()}</div>
                <div style='font-size: 11px; color: #6b7280;'>{route.origin} → {route.destination}</div>
            </div>
            {f'<span style="padding: 2px 8px; background: #22c55e20; color: #22c55e; border-radius: 8px; font-size: 10px; font-weight: 700;">{rec_badge}</span>' if rec_badge else ''}
        </div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 10px;'>
            <div style='text-align: center; padding: 8px; background: #f9fafb; border-radius: 10px;'>
                <div style='font-size: 14px; font-weight: 800; color: #111827;'>{route.distance_km:.1f} km</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Distance</div>
            </div>
            <div style='text-align: center; padding: 8px; background: #f9fafb; border-radius: 10px;'>
                <div style='font-size: 14px; font-weight: 800; color: #0ea5e9;'>{route.duration_minutes:.0f} min</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Duration</div>
            </div>
            <div style='text-align: center; padding: 8px; background: #f9fafb; border-radius: 10px;'>
                <div style='font-size: 14px; font-weight: 800; color: {"#22c55e" if route.emission_kg < 1 else "#f59e0b" if route.emission_kg < 3 else "#ef4444"};'>{route.emission_kg:.2f} kg</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>CO₂ Emission</div>
            </div>
            <div style='text-align: center; padding: 8px; background: #f9fafb; border-radius: 10px;'>
                <div style='font-size: 14px; font-weight: 800; color: #f59e0b;'>${route.cost_usd:.2f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Cost</div>
            </div>
        </div>
        <div style='display: flex; gap: 16px; font-size: 11px; color: #6b7280;'>
            <span>🔥 {route.calories_burned:.0f} cal</span>
            <span>📊 Score: {route.preference_score:.0%}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_trip_log_card(log: TripLog):
    """Render a trip log entry card."""
    icon = MODE_ICONS.get(log.mode, "🚗")
    color = MODE_COLORS.get(log.mode, "#6b7280")
    cat_icons = {"commute": "🏢", "errands": "🛒", "recreation": "🎉", "business": "💼", "travel": "✈️", "school": "📚"}

    st.markdown(f"""
    <div style='
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: rgba(255,255,255,0.8);
        border: 1px solid rgba(0,0,0,0.05);
        border-left: 3px solid {color};
        border-radius: 10px;
        margin-bottom: 6px;
    '>
        <span style='font-size: 20px;'>{icon}</span>
        <div style='flex: 1; min-width: 0;'>
            <div style='font-size: 13px; font-weight: 600; color: #111827;'>{log.origin} → {log.destination}</div>
            <div style='font-size: 10px; color: #9ca3af;'>{log.date} · {cat_icons.get(log.category.value, '📌')} {log.category.value.title()}</div>
        </div>
        <div style='text-align: right;'>
            <div style='font-size: 12px; font-weight: 700; color: {color};'>{log.distance_km:.1f} km</div>
            <div style='font-size: 10px; color: #9ca3af;'>{log.emission_kg:.2f} kg · ${log.cost_usd:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_emission_comparison_card(comp: EmissionComparison):
    """Render an emission comparison row."""
    icon = MODE_ICONS.get(comp.mode, "🚗")
    color = MODE_COLORS.get(comp.mode, "#6b7280")
    bar_width = min(comp.emission_kg / 5, 1.0) * 100

    st.markdown(f"""
    <div style='
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: {"rgba(34,197,94,0.05)" if comp.is_greenest else "rgba(255,255,255,0.6)"};
        border: {"1px solid rgba(34,197,94,0.2)" if comp.is_greenest else "1px solid rgba(0,0,0,0.04)"};
        border-radius: 10px;
        margin-bottom: 6px;
    '>
        <span style='font-size: 20px;'>{icon}</span>
        <div style='flex: 1; min-width: 0;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 4px;'>
                <span style='font-size: 12px; font-weight: 600; color: #111827;'>{comp.mode_name}</span>
                <span style='font-size: 11px; font-weight: 700; color: {color};'>{comp.emission_kg:.3f} kg CO₂</span>
            </div>
            <div style='width: 100%; height: 5px; background: #e5e7eb; border-radius: 999px; overflow: hidden;'>
                <div style='width: {bar_width}%; height: 100%; background: {color}; border-radius: 999px;'></div>
            </div>
            <div style='display: flex; gap: 12px; margin-top: 4px; font-size: 10px; color: #9ca3af;'>
                <span>⏱ {comp.time_minutes:.0f} min</span>
                <span>💰 ${comp.cost_usd:.2f}</span>
                <span>🔥 {comp.calories:.0f} cal</span>
                {f'<span style="color: #22c55e; font-weight: 600;">💚 Saves {comp.savings_vs_car_kg:.2f} kg vs car</span>' if comp.savings_vs_car_kg > 0 else ''}
            </div>
        </div>
        {f'<span style="padding: 2px 6px; background: #22c55e20; color: #22c55e; border-radius: 6px; font-size: 9px; font-weight: 700;">GREENEST</span>' if comp.is_greenest else ''}
    </div>
    """, unsafe_allow_html=True)


def render_vehicle_card(vehicle: Vehicle):
    """Render a vehicle info card."""
    type_colors = {
        "gasoline": "#ef4444", "diesel": "#f97316", "hybrid": "#f59e0b",
        "plug_in_hybrid": "#eab308", "electric": "#22c55e", "none": "#94a3b8",
    }
    color = type_colors.get(vehicle.vehicle_type.value, "#6b7280")

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: {"linear-gradient(145deg, rgba(34,197,94,0.06), rgba(255,255,255,0.95))" if vehicle.is_default else "rgba(255,255,255,0.9)"};
        border: {"2px solid rgba(34,197,94,0.2)" if vehicle.is_default else "1px solid rgba(0,0,0,0.06)"};
        border-radius: 14px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
            <span style='font-size: 24px;'>{"⚡" if vehicle.vehicle_type.value == "electric" else "🚗"}</span>
            <div style='flex: 1;'>
                <div style='font-size: 14px; font-weight: 700; color: #111827;'>{vehicle.name}</div>
                <div style='font-size: 11px; color: #6b7280;'>{vehicle.year} {vehicle.make} {vehicle.model}</div>
            </div>
            <span style='
                padding: 2px 8px;
                background: {color}20;
                color: {color};
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
            '>{vehicle.vehicle_type.value.replace('_', ' ')}</span>
        </div>
        <div style='display: flex; gap: 16px; font-size: 11px; color: #6b7280;'>
            <span>⛽ {vehicle.fuel_efficiency_km_per_l} km/L</span>
            <span>🌿 {vehicle.emission_factor_kg_per_km} kg/km</span>
            {f'<span style="color: #22c55e; font-weight: 600;">⭐ Default</span>' if vehicle.is_default else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_commute_insight_card(stats):
    """Render commute insight summary card."""
    trend_icon = "📈" if stats.monthly_co2_saved_kg > 10 else "➡️"

    st.markdown(f"""
    <div style='
        padding: 20px;
        background: linear-gradient(145deg, rgba(34,197,94,0.05), rgba(14,165,233,0.03));
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 16px;
        margin-bottom: 16px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 12px;'>
            <span style='font-size: 20px;'>{trend_icon}</span>
            <span style='font-size: 15px; font-weight: 700; color: #111827;'>Commute Insights</span>
        </div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px;'>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #111827;'>{stats.avg_daily_distance_km:.1f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Avg km/day</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #22c55e;'>${stats.monthly_savings_usd:.0f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Monthly Saved</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #0ea5e9;'>{stats.monthly_co2_saved_kg:.1f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>kg CO₂ Avoided</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 18px; font-weight: 800; color: #8b5cf6;'>{stats.total_monthly_trips}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>Monthly Trips</div>
            </div>
        </div>
        <div style='font-size: 11px; color: #6b7280;'>
            🌿 Greenest day: <strong>{stats.greenest_day}</strong> ·
            ⚠️ Busiest: <strong>{stats.worst_day}</strong> ·
            🚀 Most used: <strong>{stats.most_used_mode.value.replace('_', ' ').title()}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
