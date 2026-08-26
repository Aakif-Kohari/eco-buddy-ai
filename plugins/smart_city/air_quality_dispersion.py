"""
Air Quality Dispersion Model.
Calculates how PM2.5 and NOx pollutants spread from roads to residential zones
using an Eulerian grid and wind advection/diffusion physics.
"""

import numpy as np
from typing import Dict, Tuple
from plugins.smart_city.road_network import CityGrid

class AirQualityGrid:
    def __init__(self, width_m: float, height_m: float, cell_size_m: float = 50.0):
        self.width_m = width_m
        self.height_m = height_m
        self.cell_size_m = cell_size_m
        
        self.cols = int(width_m / cell_size_m)
        self.rows = int(height_m / cell_size_m)
        
        # Grid layers for pollutants (micrograms per cubic meter)
        self.pm25_grid = np.zeros((self.rows, self.cols))
        self.nox_grid = np.zeros((self.rows, self.cols))
        
        # Dispersion parameters
        self.diffusion_coeff = 0.5
        self.wind_speed_m_s = 2.0
        self.wind_dir_deg = 90.0 # Blowing East
        
    def add_emissions(self, x: float, y: float, pm25_g: float, nox_g: float):
        """Injects pollutants at a specific coordinate."""
        col = int(x / self.cell_size_m)
        row = int(y / self.cell_size_m)
        
        if 0 <= col < self.cols and 0 <= row < self.rows:
            # Convert grams to micrograms (x 1_000_000)
            # Assume mixing height of 10 meters for volume
            vol_m3 = self.cell_size_m * self.cell_size_m * 10.0
            
            pm25_ug_m3 = (pm25_g * 1e6) / vol_m3
            nox_ug_m3 = (nox_g * 1e6) / vol_m3
            
            self.pm25_grid[row, col] += pm25_ug_m3
            self.nox_grid[row, col] += nox_ug_m3

    def tick_dispersion(self, dt_seconds: float):
        """Simulates wind blowing and diffusion of pollutants."""
        # 1. Diffusion (blurring the grid)
        # Simplified finite difference for diffusion
        pm25_new = np.copy(self.pm25_grid)
        nox_new = np.copy(self.nox_grid)
        
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                # Laplacian
                pm25_lap = (self.pm25_grid[r+1, c] + self.pm25_grid[r-1, c] + 
                            self.pm25_grid[r, c+1] + self.pm25_grid[r, c-1] - 
                            4 * self.pm25_grid[r, c])
                
                nox_lap = (self.nox_grid[r+1, c] + self.nox_grid[r-1, c] + 
                           self.nox_grid[r, c+1] + self.nox_grid[r, c-1] - 
                           4 * self.nox_grid[r, c])
                           
                pm25_new[r, c] += self.diffusion_coeff * pm25_lap * dt_seconds
                nox_new[r, c] += self.diffusion_coeff * nox_lap * dt_seconds
                
        # 2. Advection (Wind)
        import math
        wind_rad = math.radians(self.wind_dir_deg)
        u = self.wind_speed_m_s * math.cos(wind_rad)
        v = self.wind_speed_m_s * math.sin(wind_rad)
        
        # Shift grids based on wind (Simplified upwind scheme)
        shift_col = int((u * dt_seconds) / self.cell_size_m)
        shift_row = int((v * dt_seconds) / self.cell_size_m)
        
        if shift_col != 0 or shift_row != 0:
            pm25_shifted = np.roll(pm25_new, shift_row, axis=0)
            pm25_shifted = np.roll(pm25_shifted, shift_col, axis=1)
            pm25_new = pm25_shifted
            
            nox_shifted = np.roll(nox_new, shift_row, axis=0)
            nox_shifted = np.roll(nox_shifted, shift_col, axis=1)
            nox_new = nox_shifted
            
        # 3. Decay (Pollutants settling or breaking down)
        decay_rate = 0.99 # 1% lost per tick
        self.pm25_grid = pm25_new * decay_rate
        self.nox_grid = nox_new * decay_rate

    def get_aqi_at(self, x: float, y: float) -> Tuple[float, float]:
        """Returns PM2.5 and NOx concentration at a location."""
        col = int(x / self.cell_size_m)
        row = int(y / self.cell_size_m)
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.pm25_grid[row, col], self.nox_grid[row, col]
        return 0.0, 0.0
