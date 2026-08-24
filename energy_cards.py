"""Streamlit card components for the Energy Monitoring Dashboard."""

import streamlit as st
from typing import List, Dict
from energy_types import (
    Appliance, EnergyDevice, EnergyAlert, EnergyGoal, EnergyBill,
    EnergyInsight, ApplianceCategory, AlertType,
    APPLIANCE_ICONS, APPLIANCE_COLORS, EFFICIENCY_COLORS,
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


def render_appliance_card(appliance: Appliance):
    """Render an appliance monitoring card."""
    icon = APPLIANCE_ICONS.get(appliance.category, "🔌")
    color = APPLIANCE_COLORS.get(appliance.category, "#6b7280")
    eff_color = EFFICIENCY_COLORS.get(appliance.efficiency_rating, "#6b7280")
    status_color = "#22c55e" if appliance.is_active else "#ef4444"
    status_label = "Active" if appliance.is_active else "Off"

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-left: 4px solid {color};
        border-radius: 12px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
            <span style='font-size: 22px;'>{icon}</span>
            <div style='flex: 1;'>
                <div style='font-size: 13px; font-weight: 700; color: #111827;'>{appliance.name}</div>
                <div style='font-size: 10px; color: #9ca3af;'>{appliance.rated_power_watts}W · {appliance.usage_hours_daily}h/day</div>
            </div>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <span style='padding: 2px 8px; background: {eff_color}20; color: {eff_color}; border-radius: 6px; font-size: 10px; font-weight: 700;'>{appliance.efficiency_rating}</span>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: {status_color};'></span>
            </div>
        </div>
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;'>
            <div style='text-align: center; padding: 6px; background: #f9fafb; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #111827;'>{appliance.avg_daily_kwh:.1f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>kWh/day</div>
            </div>
            <div style='text-align: center; padding: 6px; background: #f9fafb; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #f59e0b;'>${appliance.monthly_cost_usd:.2f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>$/month</div>
            </div>
            <div style='text-align: center; padding: 6px; background: #f9fafb; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #6b7280;'>{appliance.usage_hours_daily:.1f}h</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Usage</div>
            </div>
        </div>
        <div style='font-size: 10px; color: #9ca3af; margin-top: 6px;'>Last used: {appliance.last_used}</div>
    </div>
    """, unsafe_allow_html=True)


def render_device_card(device: EnergyDevice):
    """Render a smart device monitoring card."""
    status_color = "#22c55e" if device.is_online else "#ef4444"
    status_label = "Online" if device.is_online else "Offline"

    st.markdown(f"""
    <div style='
        padding: 14px;
        background: {"rgba(255,255,255,0.9)" if device.is_online else "rgba(255,255,255,0.6)"};
        border: 1px solid {"rgba(0,0,0,0.06)" if device.is_online else "rgba(239,68,68,0.2)"};
        border-radius: 12px;
        margin-bottom: 8px;
    '>
        <div style='display: flex; align-items: center; gap: 8px;'>
            <span style='width: 8px; height: 8px; border-radius: 50%; background: {status_color}; flex-shrink: 0;'></span>
            <div style='flex: 1;'>
                <div style='font-size: 12px; font-weight: 700; color: #111827;'>{device.name}</div>
                <div style='font-size: 10px; color: #9ca3af;'>{device.location} · {device.firmware_version}</div>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 12px; font-weight: 700; color: #111827;'>{device.current_power_watts}W</div>
                <div style='font-size: 10px; color: #9ca3af;'>{device.today_kwh:.1f} kWh today</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_alert_card(alert: EnergyAlert):
    """Render an energy alert card."""
    severity_colors = {
        "low": ("#f59e0b", "#fffbeb"),
        "medium": ("#f97316", "#fff7ed"),
        "high": ("#ef4444", "#fef2f2"),
        "critical": ("#dc2626", "#fef2f2"),
    }
    color, bg = severity_colors.get(alert.severity, ("#6b7280", "#f9fafb"))

    st.markdown(f"""
    <div style='
        padding: 14px;
        background: {bg};
        border: 1px solid {color}30;
        border-left: 4px solid {color};
        border-radius: 12px;
        margin-bottom: 8px;
        opacity: {"0.6" if alert.is_read else "1"};
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 6px;'>
            <span style='
                padding: 2px 8px;
                background: {color}20;
                color: {color};
                border-radius: 6px;
                font-size: 9px;
                font-weight: 700;
                text-transform: uppercase;
            '>{alert.severity}</span>
            <span style='font-size: 12px; font-weight: 700; color: #111827;'>{alert.title}</span>
        </div>
        <div style='font-size: 11px; color: #374151; line-height: 1.5; margin-bottom: 6px;'>{alert.message}</div>
        <div style='display: flex; justify-content: space-between; font-size: 10px; color: #9ca3af;'>
            <span>📍 {alert.device_name}</span>
            <span>💡 {alert.recommended_action}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_goal_card(goal: EnergyGoal):
    """Render an energy goal progress card."""
    progress = goal.progress_percent
    color = "#22c55e" if progress >= 80 else "#f59e0b" if progress >= 50 else "#ef4444"
    status = "✅ Done" if goal.is_completed else f"{progress:.0f}%"

    st.markdown(f"""
    <div style='
        padding: 14px;
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 12px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='font-size: 12px; font-weight: 700; color: #111827;'>{goal.title}</span>
            <span style='font-size: 10px; color: {color}; font-weight: 600;'>{status}</span>
        </div>
        <div style='font-size: 11px; color: #6b7280; margin-bottom: 6px;'>
            {goal.current_value:.1f} / {goal.target_value:.1f} {goal.unit}
        </div>
        <div style='width: 100%; height: 7px; background: #e5e7eb; border-radius: 999px; overflow: hidden;'>
            <div style='width: {progress}%; height: 100%; background: {color}; border-radius: 999px;'></div>
        </div>
        <div style='font-size: 10px; color: #9ca3af; margin-top: 4px;'>Deadline: {goal.deadline}</div>
    </div>
    """, unsafe_allow_html=True)


def render_bill_card(bill: EnergyBill):
    """Render a monthly energy bill card."""
    renewable_pct = bill.renewable_percent
    rec_color = "#22c55e" if renewable_pct >= 40 else "#f59e0b"

    st.markdown(f"""
    <div style='
        padding: 16px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,253,244,0.85));
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        margin-bottom: 10px;
    '>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
            <span style='font-size: 14px; font-weight: 700; color: #111827;'>📅 {bill.month}</span>
            <span style='font-size: 16px; font-weight: 800; color: #f59e0b;'>${bill.total_cost_usd:.2f}</span>
        </div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 8px;'>
            <div style='text-align: center;'>
                <div style='font-size: 14px; font-weight: 800; color: #111827;'>{bill.total_kwh:.0f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Total kWh</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 14px; font-weight: 800; color: #f59e0b;'>{bill.peak_kwh:.0f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Peak</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 14px; font-weight: 800; color: #0ea5e9;'>{bill.off_peak_kwh:.0f}</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Off-Peak</div>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 14px; font-weight: 800; color: {rec_color};'>{renewable_pct:.0f}%</div>
                <div style='font-size: 9px; color: #9ca3af; text-transform: uppercase;'>Renewable</div>
            </div>
        </div>
        <div style='width: 100%; height: 5px; background: #e5e7eb; border-radius: 999px; overflow: hidden;'>
            <div style='width: {renewable_pct}%; height: 100%; background: {rec_color}; border-radius: 999px;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_insight_card(insight: EnergyInsight):
    """Render an AI energy insight card."""
    conf_color = "#22c55e" if insight.confidence >= 0.85 else "#f59e0b"

    actions_html = ""
    for action in insight.recommended_actions:
        actions_html += f"<div style='font-size: 10px; color: #374151; padding: 2px 0;'>• {action}</div>"

    st.markdown(f"""
    <div style='
        padding: 18px;
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,253,244,0.85));
        border: 1px solid rgba(74,222,128,0.15);
        border-radius: 14px;
        margin-bottom: 12px;
    '>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px;'>
            <span style='font-size: 18px;'>🤖</span>
            <span style='font-size: 14px; font-weight: 700; color: #111827;'>{insight.title}</span>
            <span style='margin-left: auto; padding: 2px 8px; background: {conf_color}20; color: {conf_color}; border-radius: 6px; font-size: 9px; font-weight: 700;'>{insight.confidence:.0%} confident</span>
        </div>
        <div style='font-size: 12px; color: #374151; line-height: 1.6; margin-bottom: 10px;'>{insight.description}</div>
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px;'>
            <div style='text-align: center; padding: 6px; background: #f0fdf4; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #16a34a;'>{insight.potential_savings_kwh:.0f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>kWh/year</div>
            </div>
            <div style='text-align: center; padding: 6px; background: #fffbeb; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #d97706;'>${insight.potential_savings_usd:.2f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>$/year saved</div>
            </div>
            <div style='text-align: center; padding: 6px; background: #eff6ff; border-radius: 8px;'>
                <div style='font-size: 14px; font-weight: 800; color: #2563eb;'>{insight.potential_carbon_kg:.0f}</div>
                <div style='font-size: 9px; color: #6b7280; text-transform: uppercase;'>kg CO₂</div>
            </div>
        </div>
        <div style='font-size: 11px; font-weight: 600; color: #374151; margin-bottom: 4px;'>Recommended Actions:</div>
        {actions_html}
    </div>
    """, unsafe_allow_html=True)
