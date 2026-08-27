"""
Smart City plugin initialization.
"""
from plugins.smart_city.engine import SmartCitySimulation
from plugins.smart_city.telemetry_city import CityTelemetry

__all__ = ["SmartCitySimulation", "CityTelemetry"]
