"""
Fashion Circularity & End of Life (EOL) Engine.
Models what happens to a garment when discarded.
Simulates landfill methane off-gassing, incineration energy recovery,
mechanical shredding, and advanced chemical recycling.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EndOfLifeModel:
    """
    Calculates the carbon and material recovery metrics for a garment at EOL.
    """
    
    def __init__(self):
        # Methane Global Warming Potential (GWP) is ~28x higher than CO2 over 100 years.
        self.methane_gwp = 28.0
        
    def simulate_landfill(self, garment_weight_kg: float, material_blend: Dict[str, float]) -> Dict[str, float]:
        """
        Simulates anaerobic decomposition in a landfill.
        Natural fibers decompose and release methane.
        Synthetics do not decompose, but take up space (volume).
        """
        methane_emissions_kg = 0.0
        landfill_volume_occupied_cm3 = 0.0
        
        # Approximate decomposition rates (fraction of mass converted to CH4 over 100 years)
        ch4_yields = {
            'Cotton (Conventional)': 0.06,
            'Cotton (Organic)': 0.06,
            'Wool': 0.08,
            'Linen': 0.05,
            'Viscose/Rayon': 0.07,
            'Silk': 0.04
        }
        
        for material, percentage in material_blend.items():
            mass = garment_weight_kg * percentage
            
            # Synthetics don't decompose, they sit forever
            if 'Polyester' in material or 'Nylon' in material or 'Acrylic' in material:
                # Density of polyester is roughly 1.38 g/cm3 -> 1380 kg/m3
                volume_m3 = mass / 1380.0
                landfill_volume_occupied_cm3 += volume_m3 * 1_000_000
            else:
                # Natural fibers rot and release CH4
                yield_rate = ch4_yields.get(material, 0.0)
                methane_emissions_kg += (mass * yield_rate)
                
        # Convert CH4 to CO2 equivalent
        co2e_from_methane = methane_emissions_kg * self.methane_gwp
        
        return {
            "eol_carbon_kg_co2e": round(co2e_from_methane, 2),
            "methane_kg": round(methane_emissions_kg, 4),
            "legacy_volume_cm3": round(landfill_volume_occupied_cm3, 2),
            "fate": "LANDFILL"
        }

    def simulate_incineration(self, garment_weight_kg: float, material_blend: Dict[str, float], has_energy_recovery: bool = True) -> Dict[str, float]:
        """
        Simulates burning the garment.
        Releases immediate CO2, but synthetics burn hot and can be used to generate electricity.
        """
        immediate_co2_kg = 0.0
        energy_recovered_mj = 0.0
        
        # Heating Values (Megajoules per kg)
        heating_values = {
            'Polyester (Virgin)': 22.0,
            'Polyester (Recycled)': 22.0,
            'Nylon': 30.0,
            'Cotton (Conventional)': 16.0,
            'Wool': 20.0
        }
        
        # Carbon mass fractions
        carbon_fractions = {
            'Polyester (Virgin)': 0.62,
            'Nylon': 0.63,
            'Cotton (Conventional)': 0.44,
            'Wool': 0.50
        }
        
        for material, percentage in material_blend.items():
            mass = garment_weight_kg * percentage
            c_fraction = carbon_fractions.get(material, 0.5)
            
            # 1 kg Carbon -> 3.67 kg CO2
            immediate_co2_kg += mass * c_fraction * 3.667
            
            if has_energy_recovery:
                hv = heating_values.get(material, 15.0)
                # Assume 30% thermal efficiency in waste-to-energy plants
                energy_recovered_mj += mass * hv * 0.30
                
        # Offset grid carbon with recovered energy (assuming grid is 0.1 kg CO2 / MJ)
        offset_co2 = energy_recovered_mj * 0.1 if has_energy_recovery else 0.0
        net_co2e = immediate_co2_kg - offset_co2
        
        return {
            "eol_carbon_kg_co2e": round(net_co2e, 2),
            "immediate_co2_kg": round(immediate_co2_kg, 2),
            "energy_recovered_mj": round(energy_recovered_mj, 2),
            "fate": "INCINERATION_WTE" if has_energy_recovery else "INCINERATION_OPEN"
        }

    def simulate_chemical_recycling(self, garment_weight_kg: float, material_blend: Dict[str, float]) -> Dict[str, float]:
        """
        Simulates advanced depolymerization. Only works on pure synthetics or pure cotton.
        Blends (e.g. Poly-Cotton) ruin the chemical bath and must be rejected.
        """
        # Check for pure blend
        is_pure = False
        primary_material = ""
        for mat, pct in material_blend.items():
            if pct > 0.95:
                is_pure = True
                primary_material = mat
                break
                
        if not is_pure:
            # Poly-cotton blends are rejected by chemical recyclers and sent to landfill
            logger.warning("Garment is a complex blend. Rejected by chemical recycler. Diverting to landfill.")
            return self.simulate_landfill(garment_weight_kg, material_blend)
            
        # If pure, we recover the monomer
        # Processing requires energy (carbon cost), but offsets virgin material creation
        processing_carbon_kg = garment_weight_kg * 2.5 # Cost to run the chemical plant
        
        # Virgin offset depends on material
        virgin_offset_kg = 0.0
        if 'Polyester' in primary_material:
            virgin_offset_kg = garment_weight_kg * 22.0 # From main db
        elif 'Cotton' in primary_material:
            virgin_offset_kg = garment_weight_kg * 20.0
            
        net_co2e = processing_carbon_kg - virgin_offset_kg
        
        return {
            "eol_carbon_kg_co2e": round(net_co2e, 2),
            "virgin_material_offset_kg": round(virgin_offset_kg, 2),
            "processing_cost_kg_co2": round(processing_carbon_kg, 2),
            "fate": "CHEMICAL_RECYCLING"
        }
