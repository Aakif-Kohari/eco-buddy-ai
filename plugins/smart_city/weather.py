"""
Weather impacts on city traffic and physics.
Rain/Snow increases rolling resistance and lowers speed limits.
"""

class CityWeather:
    def __init__(self):
        self.condition = "CLEAR" # CLEAR, RAIN, SNOW
        self.temperature_c = 20.0
        
    def apply_to_physics(self, drag_coeff: float, rolling_coeff: float) -> tuple:
        if self.condition == "RAIN":
            # Water on road increases rolling resistance
            return drag_coeff, rolling_coeff * 1.2
        elif self.condition == "SNOW":
            return drag_coeff, rolling_coeff * 2.0
        return drag_coeff, rolling_coeff
        
    def apply_to_speed_limit(self, limit_kmh: float) -> float:
        if self.condition == "RAIN":
            return limit_kmh * 0.9
        elif self.condition == "SNOW":
            return limit_kmh * 0.6
        return limit_kmh
