"""
World Map & Bathymetry Grid for Ocean Currents.
Represents a simplified global grid (latitude/longitude) defining 
oceans, continents, and coastal emission zones.
"""

import numpy as np
from typing import Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)

class WorldMapGrid:
    def __init__(self, lat_resolution_deg: float = 2.0, lon_resolution_deg: float = 2.0):
        self.lat_res = lat_resolution_deg
        self.lon_res = lon_resolution_deg
        
        # 180 degrees of latitude, 360 degrees of longitude
        self.rows = int(180.0 / self.lat_res)
        self.cols = int(360.0 / self.lon_res)
        
        # 1 = Ocean, 0 = Land
        self.land_mask = np.ones((self.rows, self.cols), dtype=np.int8)
        
        # Initialize some continents roughly
        self._build_rough_continents()
        
    def _build_rough_continents(self):
        """Creates very crude blocky representations of major landmasses."""
        
        def add_block(lat_start, lat_end, lon_start, lon_end):
            r_start = int((90 - lat_start) / self.lat_res)
            r_end = int((90 - lat_end) / self.lat_res)
            
            c_start = int((180 + lon_start) / self.lon_res)
            c_end = int((180 + lon_end) / self.lon_res)
            
            # Ensure valid bounds
            r_s, r_e = sorted([r_start, r_end])
            c_s, c_e = sorted([c_start, c_end])
            
            r_s = max(0, r_s)
            r_e = min(self.rows, r_e)
            c_s = max(0, c_s)
            c_e = min(self.cols, c_e)
            
            self.land_mask[r_s:r_e, c_s:c_e] = 0

        # North America
        add_block(70, 15, -130, -60)
        # South America
        add_block(15, -55, -80, -35)
        # Eurasia
        add_block(70, 10, -10, 180)
        # Africa
        add_block(35, -35, -20, 50)
        # Australia
        add_block(-10, -40, 110, 155)
        
    def get_indices(self, lat: float, lon: float) -> Tuple[int, int]:
        """Converts lat/lon to grid row/col."""
        # clamp
        lat = max(-90.0, min(89.999, lat))
        lon = max(-180.0, min(179.999, lon))
        
        row = int((90 - lat) / self.lat_res)
        col = int((180 + lon) / self.lon_res)
        
        row = max(0, min(self.rows - 1, row))
        col = max(0, min(self.cols - 1, col))
        
        return row, col
        
    def get_lat_lon(self, row: int, col: int) -> Tuple[float, float]:
        """Converts grid row/col to center lat/lon."""
        lat = 90 - (row * self.lat_res) - (self.lat_res / 2)
        lon = -180 + (col * self.lon_res) + (self.lon_res / 2)
        return lat, lon
        
    def is_ocean(self, lat: float, lon: float) -> bool:
        r, c = self.get_indices(lat, lon)
        return self.land_mask[r, c] == 1
        
    def get_coastal_emission_zones(self) -> List[Tuple[float, float]]:
        """Finds ocean cells that touch land (representing coastal cities where plastic enters)."""
        zones = []
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if self.land_mask[r, c] == 1:
                    # Check neighbors
                    if (self.land_mask[r-1, c] == 0 or self.land_mask[r+1, c] == 0 or
                        self.land_mask[r, c-1] == 0 or self.land_mask[r, c+1] == 0):
                        lat, lon = self.get_lat_lon(r, c)
                        zones.append((lat, lon))
        return zones
