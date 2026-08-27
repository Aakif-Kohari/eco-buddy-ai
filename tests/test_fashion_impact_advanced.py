import pytest
from plugins.fashion_impact_microplastics import MicroplasticSheddingModel
from plugins.fashion_impact_supply_chain import GlobalSupplyChainGraph
from plugins.fashion_impact_circularity import EndOfLifeModel

# --- Microplastics Tests ---

def test_microplastic_shedding():
    model = MicroplasticSheddingModel()
    
    blend = {"Polyester (Virgin)": 1.0}
    
    # Baseline cold wash
    res_cold = model.simulate_lifetime_shedding(
        garment_weight_kg=0.5,
        material_blend=blend,
        washes_per_year=12,
        lifespan_years=2.0, # 24 washes total
        wash_temp_c=30,
        spin_speed_rpm=800,
        has_guppyfriend_bag=False
    )
    
    # Hot wash, fast spin
    res_hot = model.simulate_lifetime_shedding(
        garment_weight_kg=0.5,
        material_blend=blend,
        washes_per_year=12,
        lifespan_years=2.0,
        wash_temp_c=60,
        spin_speed_rpm=1200,
        has_guppyfriend_bag=False
    )
    
    assert res_cold["total_microplastics_grams"] > 0
    assert res_hot["total_microplastics_grams"] > res_cold["total_microplastics_grams"]
    
    # Guppyfriend test
    res_bag = model.simulate_lifetime_shedding(
        garment_weight_kg=0.5,
        material_blend=blend,
        has_guppyfriend_bag=True
    )
    
    # Bag reduces shedding by ~90%
    assert res_bag["total_microplastics_grams"] < (res_cold["total_microplastics_grams"] * 0.2)

def test_natural_fibers_dont_shed_microplastics():
    model = MicroplasticSheddingModel()
    blend = {"Cotton (Organic)": 1.0}
    
    res = model.simulate_lifetime_shedding(0.5, blend)
    assert res["total_microplastics_grams"] == 0.0
    assert res["estimated_particle_count"] == 0

# --- Supply Chain Tests ---

def test_supply_chain_dijkstra():
    graph = GlobalSupplyChainGraph()
    
    # Route from India Farm to US Retail
    # India -> Bangladesh (1200 truck) -> Bangladesh Assembly (50 truck) -> EU Retail (8000 ocean)
    # India -> China (4500 ocean) -> Vietnam Assembly (2000 rail) -> USA Retail (13000 ocean)
    
    res = graph.find_lowest_carbon_path("FARM_INDIA", "RETAIL_USA")
    
    assert "error" not in res
    assert res["start_node"] == "FARM_INDIA"
    assert res["end_node"] == "RETAIL_USA"
    
    path = res["optimal_path"]
    assert path[0] == "FARM_INDIA"
    assert path[-1] == "RETAIL_USA"
    assert res["total_distance_km"] > 0
    
    # Fast fashion route (Air Freight)
    res_fast = graph.find_lowest_carbon_path("FARM_INDIA", "RETAIL_USA_FAST")
    assert res_fast["logistics_carbon_kg_per_tonne"] > res["logistics_carbon_kg_per_tonne"]

def test_garment_transport_footprint():
    graph = GlobalSupplyChainGraph()
    res = graph.find_lowest_carbon_path("FARM_INDIA", "RETAIL_USA")
    
    # 0.2 kg T-Shirt
    footprint = graph.calculate_garment_transport_footprint(res, 0.2)
    assert footprint > 0
    assert footprint < res["logistics_carbon_kg_per_tonne"] # Must be a tiny fraction (0.2 / 1000)

# --- Circularity Tests ---

def test_landfill_methane():
    eol = EndOfLifeModel()
    
    # Cotton decomposes
    blend_cotton = {"Cotton (Conventional)": 1.0}
    res_cotton = eol.simulate_landfill(1.0, blend_cotton)
    
    assert res_cotton["methane_kg"] > 0
    assert res_cotton["eol_carbon_kg_co2e"] > 0
    assert res_cotton["legacy_volume_cm3"] == 0.0 # Rots away
    
    # Poly does not decompose
    blend_poly = {"Polyester (Virgin)": 1.0}
    res_poly = eol.simulate_landfill(1.0, blend_poly)
    
    assert res_poly["methane_kg"] == 0.0
    assert res_poly["eol_carbon_kg_co2e"] == 0.0
    assert res_poly["legacy_volume_cm3"] > 0.0

def test_incineration():
    eol = EndOfLifeModel()
    blend = {"Polyester (Virgin)": 1.0}
    
    res_open = eol.simulate_incineration(1.0, blend, has_energy_recovery=False)
    res_wte = eol.simulate_incineration(1.0, blend, has_energy_recovery=True)
    
    assert res_open["immediate_co2_kg"] == res_wte["immediate_co2_kg"]
    assert res_open["energy_recovered_mj"] == 0.0
    assert res_wte["energy_recovered_mj"] > 0.0
    
    # Net CO2e should be lower for Waste-to-Energy because it offsets grid power
    assert res_wte["eol_carbon_kg_co2e"] < res_open["eol_carbon_kg_co2e"]

def test_chemical_recycling():
    eol = EndOfLifeModel()
    
    pure_poly = {"Polyester (Virgin)": 1.0}
    mixed = {"Polyester (Virgin)": 0.5, "Cotton (Conventional)": 0.5}
    
    res_pure = eol.simulate_chemical_recycling(1.0, pure_poly)
    assert res_pure["fate"] == "CHEMICAL_RECYCLING"
    assert res_pure["eol_carbon_kg_co2e"] < 0 # Huge offset means net negative
    
    res_mixed = eol.simulate_chemical_recycling(1.0, mixed)
    # Mixed blends ruin the bath and go to landfill
    assert res_mixed["fate"] == "LANDFILL"
