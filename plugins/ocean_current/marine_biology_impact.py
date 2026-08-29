"""
Marine Biology Impact Model.
Calculates the statistical impact of macro and microplastics on marine species.
"""

from typing import Dict, List
from plugins.ocean_current.particle_tracker import LagrangianTracker

class MarineSpecies:
    def __init__(self, name: str, ingestion_rate_kg_per_day: float, entanglement_risk: float):
        self.name = name
        self.ingestion_rate_kg_per_day = ingestion_rate_kg_per_day
        self.entanglement_risk = entanglement_risk
        
        self.total_plastic_ingested_kg = 0.0
        self.entanglement_events = 0
        
class EcosystemZone:
    def __init__(self, name: str, lat_bounds: tuple, lon_bounds: tuple):
        self.name = name
        self.lat_bounds = lat_bounds
        self.lon_bounds = lon_bounds
        self.species: List[MarineSpecies] = []
        
    def add_species(self, species: MarineSpecies):
        self.species.append(species)
        
class BiologyImpactModel:
    def __init__(self, tracker: LagrangianTracker):
        self.tracker = tracker
        self.zones: List[EcosystemZone] = []
        self._initialize_zones()
        
    def _initialize_zones(self):
        # North Pacific (overlaps with Garbage Patch)
        zone1 = EcosystemZone("North Pacific Gyre Ecosystem", (20, 40), (-155, -135))
        zone1.add_species(MarineSpecies("Laysan Albatross", 0.001, 0.05))
        zone1.add_species(MarineSpecies("Loggerhead Sea Turtle", 0.005, 0.15))
        self.zones.append(zone1)
        
        # Coral Triangle
        zone2 = EcosystemZone("Coral Triangle", (-10, 15), (100, 140))
        zone2.add_species(MarineSpecies("Whale Shark", 0.02, 0.05))
        zone2.add_species(MarineSpecies("Manta Ray", 0.01, 0.08))
        self.zones.append(zone2)
        
    def tick_biology(self, dt_days: float):
        """
        Assesses the plastic density in each ecosystem zone and 
        applies impact metrics to the resident species.
        """
        for zone in self.zones:
            # 1. Calculate plastic density in this zone
            macro_kg = 0.0
            micro_kg = 0.0
            
            for p in self.tracker.particles:
                if p.sunk: continue
                
                if (zone.lat_bounds[0] <= p.lat <= zone.lat_bounds[1] and 
                    zone.lon_bounds[0] <= p.lon <= zone.lon_bounds[1]):
                    
                    if p.is_microplastic:
                        micro_kg += p.current_mass_kg
                    else:
                        macro_kg += p.current_mass_kg
                        
            # 2. Apply impact based on density
            # Assuming a simplistic volume/area distribution factor
            density_factor = (macro_kg + micro_kg) / 1000.0 # Arbitrary scaling
            
            for species in zone.species:
                # Ingestion (primarily microplastics for filter feeders, macro for turtles)
                if species.name == "Loggerhead Sea Turtle":
                    # They eat macro-plastics (plastic bags look like jellyfish)
                    species.total_plastic_ingested_kg += (macro_kg / 100.0) * species.ingestion_rate_kg_per_day * dt_days
                else:
                    # Filter feeders/birds ingest microplastics
                    species.total_plastic_ingested_kg += (micro_kg / 100.0) * species.ingestion_rate_kg_per_day * dt_days
                    
                # Entanglement (only from macro-plastics)
                if macro_kg > 0:
                    entangle_chance = species.entanglement_risk * density_factor * dt_days
                    if entangle_chance > 0.01:
                        # Statistical likelihood of an event
                        species.entanglement_events += int(entangle_chance * 100)
                        
    def get_impact_report(self) -> Dict[str, dict]:
        report = {}
        for zone in self.zones:
            z_report = {}
            for sp in zone.species:
                z_report[sp.name] = {
                    "ingested_kg": sp.total_plastic_ingested_kg,
                    "entanglements": sp.entanglement_events
                }
            report[zone.name] = z_report
        return report
