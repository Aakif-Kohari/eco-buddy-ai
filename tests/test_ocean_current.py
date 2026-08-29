import pytest
import math
from plugins.ocean_current.world_map import WorldMapGrid
from plugins.ocean_current.fluid_dynamics import OceanCurrentSolver
from plugins.ocean_current.degradation_model import PlasticParticle
from plugins.ocean_current.particle_tracker import LagrangianTracker

def test_world_map_grid():
    grid = WorldMapGrid(lat_resolution_deg=2.0, lon_resolution_deg=2.0)
    
    assert grid.rows == 90
    assert grid.cols == 180
    
    # Test valid coords
    r, c = grid.get_indices(0.0, 0.0)
    assert 0 <= r < grid.rows
    assert 0 <= c < grid.cols
    
    # North pole
    r_n, c_n = grid.get_indices(90.0, 0.0)
    assert r_n == 0
    
    # South pole
    r_s, c_s = grid.get_indices(-90.0, 0.0)
    assert r_s == 89 # due to clamp
    
    lat, lon = grid.get_lat_lon(r_n, c_n)
    assert lat > 0

def test_fluid_dynamics_solver():
    grid = WorldMapGrid()
    solver = OceanCurrentSolver(grid)
    
    # Check Coriolis
    f_eq = solver.get_coriolis_parameter(0.0)
    assert f_eq == 0.0
    
    f_n = solver.get_coriolis_parameter(90.0)
    assert f_n > 0.0
    
    # Step simulation
    solver.step_simulation(3600.0)
    
    u, v = solver.get_velocity(0.0, 0.0)
    assert isinstance(u, float)
    assert isinstance(v, float)
    
def test_degradation_model():
    p = PlasticParticle("1", 0.0, 0.0, 10.0) # 10 kg
    
    assert not p.is_microplastic
    
    # Tick for 100 days
    p.tick_degradation(100.0, uv_index=10.0, surface_temp_c=30.0)
    
    # Should have lost mass
    assert p.current_mass_kg < 10.0
    
    # Sinking
    p.tick_degradation(1000.0, uv_index=0.0, surface_temp_c=30.0)
    assert p.sunk
    
def test_lagrangian_tracker():
    grid = WorldMapGrid()
    solver = OceanCurrentSolver(grid)
    tracker = LagrangianTracker(grid, solver)
    
    # Spawn particle in ocean
    # Let's find an ocean cell
    ocean_lat, ocean_lon = 0.0, -150.0 # Middle of Pacific
    
    p = PlasticParticle("1", ocean_lat, ocean_lon, 1.0)
    tracker.add_particle(p)
    
    assert len(tracker.particles) == 1
    
    tracker.tick(86400.0, uv_index=5.0, surface_temp_c=20.0)
    
    # Particle should have moved
    assert tracker.particles[0].lat != ocean_lat or tracker.particles[0].lon != ocean_lon
    
    accum = tracker.get_gyre_accumulation()
    assert "Great Pacific Garbage Patch" in accum

def test_marine_biology_impact():
    from plugins.ocean_current.marine_biology_impact import BiologyImpactModel
    grid = WorldMapGrid()
    solver = OceanCurrentSolver(grid)
    tracker = LagrangianTracker(grid, solver)
    
    # Spawn particle right in the North Pacific Gyre (zone1)
    p = PlasticParticle("1", 30.0, -145.0, 100.0) # 100kg of macro plastics
    tracker.add_particle(p)
    
    bio_model = BiologyImpactModel(tracker)
    bio_model.tick_biology(dt_days=10.0)
    
    report = bio_model.get_impact_report()
    assert "North Pacific Gyre Ecosystem" in report
    
    turtle_impact = report["North Pacific Gyre Ecosystem"]["Loggerhead Sea Turtle"]
    assert turtle_impact["ingested_kg"] > 0
    assert turtle_impact["entanglements"] >= 0

def test_cleanup_fleet():
    from plugins.ocean_current.cleanup_fleet import CleanupVessel, FleetManager
    grid = WorldMapGrid()
    solver = OceanCurrentSolver(grid)
    tracker = LagrangianTracker(grid, solver)
    
    p = PlasticParticle("1", 0.0, -170.0, 1000.0)
    tracker.add_particle(p)
    
    fleet = FleetManager(tracker)
    vessel = CleanupVessel("V1", 0.0, -171.0, sweep_width_m=200000.0, speed_ms=10.0)
    fleet.add_vessel(vessel)
    
    fleet.tick_cleanup(86400.0) # 1 day
    # Should move closer
    assert vessel.target_lat is not None
    
    # Tick for a long time to extract gradually
    for _ in range(10):
        fleet.tick_cleanup(86400.0)
    assert vessel.extracted_mass_kg > 0
    assert len(tracker.particles) == 0
