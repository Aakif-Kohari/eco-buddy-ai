
import streamlit as st

@st.cache_data
def calculate_appliance_energy(power_rating_watts, hours_used_per_day, standby_draw_watts, quantity):
    standby_hours = max(0, 24 - hours_used_per_day)
    active_energy_kwh = (power_rating_watts * hours_used_per_day * quantity) / 1000.0
    standby_energy_kwh = (standby_draw_watts * standby_hours * quantity) / 1000.0
    total_daily_kwh = active_energy_kwh + standby_energy_kwh
    return total_daily_kwh, active_energy_kwh, standby_energy_kwh

@st.cache_data
def calculate_appliance_cost(daily_kwh, rate_per_kwh):
    daily_cost = daily_kwh * rate_per_kwh
    return daily_cost, daily_cost * 30, daily_cost * 365

@st.cache_data
def calculate_home_energy_summary(appliances):
    total_daily_kwh = sum(calculate_appliance_energy(a['power_rating_watts'], a['hours_used_per_day'], a['standby_draw_watts'], a['quantity'])[0] for a in appliances)
    return total_daily_kwh, total_daily_kwh * 30, total_daily_kwh * 365

@st.cache_data
def generate_hourly_energy_profile(appliances):
    profile = [0.0] * 24
    for app in appliances:
        pwr = app['power_rating_watts'] * app['quantity']
        hrs = app['hours_used_per_day']
        stdby = app['standby_draw_watts'] * app['quantity']
        
        for i in range(24):
            profile[i] += stdby / 1000.0
            
        if hrs > 0:
            full_hours = int(hrs)
            fraction = hrs - full_hours
            start_hr = max(0, 18 - int(hrs / 2))
            
            for i in range(full_hours):
                hr = (start_hr + i) % 24
                profile[hr] += pwr / 1000.0
            
            if fraction > 0 and full_hours < 24:
                hr = (start_hr + full_hours) % 24
                profile[hr] += (pwr * fraction) / 1000.0
    return profile

@st.cache_data
def calculate_solar_system_size(roof_space_m2, panel_efficiency_pct):
    return roof_space_m2 * (panel_efficiency_pct / 100.0)

@st.cache_data
def calculate_annual_solar_generation(system_size_kw, peak_sun_hours, performance_ratio=0.75):
    return system_size_kw * peak_sun_hours * 365 * performance_ratio

@st.cache_data
def calculate_solar_installation_cost(system_size_kw, cost_per_kw):
    return system_size_kw * cost_per_kw

@st.cache_data
def calculate_solar_payback_period(installation_cost, annual_savings):
    if annual_savings <= 0: return float('inf')
    return installation_cost / annual_savings

@st.cache_data
def calculate_long_term_solar_savings(annual_generation_kwh, utility_rate, years, rate_increase_pct, maintenance_cost):
    total_savings = 0
    current_rate = utility_rate
    for _ in range(years):
        yearly_savings = (annual_generation_kwh * current_rate) - maintenance_cost
        total_savings += yearly_savings
        current_rate *= (1 + rate_increase_pct / 100.0)
    return total_savings

@st.cache_data
def calculate_solar_carbon_offset(annual_generation_kwh, grid_carbon_intensity_kg_kwh=0.4):
    return annual_generation_kwh * grid_carbon_intensity_kg_kwh
