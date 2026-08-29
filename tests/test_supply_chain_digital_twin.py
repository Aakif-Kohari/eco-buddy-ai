import pytest
from src.services.supply_chain_digital_twin import (
    Port, Vessel, WeatherObstacle, NavigationEngine, LogisticsLP,
    GeneticFleetOptimizer, TrendDetector, PredictiveAnalytics
)

def test_simplex_linear_programming_bounds():
    """Test LP approximation for rebalancing empty containers."""
    p1 = Port("P1", 0.0, 0.0, capacity=1000, current_load=900)  # Surplus
    p2 = Port("P2", 10.0, 10.0, capacity=1000, current_load=100) # Deficit
    lp = LogisticsLP([p1, p2])
    
    transfers = lp.optimize_empty_rebalancing()
    assert len(transfers) == 1
    t = transfers[0]
    assert t["from"] == "P1"
    assert t["to"] == "P2"
    assert t["amount"] == 400  # (900+100)/2000 = 0.5. Ideal = 500. 900-500 = 400 surplus.

def test_genetic_algorithm_crossover_and_mutation():
    """Test Genetic Algorithm optimization of fleet speeds."""
    v1 = Vessel("V1", 0.0, 0.0, 5000)
    v2 = Vessel("V2", 0.0, 0.0, 5000)
    
    target_times = {"V1": 60.0, "V2": 80.0}
    ga = GeneticFleetOptimizer([v1, v2], target_times)
    
    # Test crossover
    p1 = {"V1": 20.0, "V2": 25.0}
    p2 = {"V1": 15.0, "V2": 15.0}
    child = ga._crossover(p1, p2)
    assert child["V1"] in [20.0, 15.0]
    assert child["V2"] in [25.0, 15.0]
    
    # Test evolution
    best = ga.evolve()
    assert "V1" in best
    assert "V2" in best
    assert len(ga.history) == ga.generations

def test_astar_pathfinding_around_weather():
    """Test A* algorithm avoiding weather obstacles."""
    nav = NavigationEngine()
    
    # Direct path from 0,0 to 10,0
    path_clear = nav.find_path((0.0, 0.0), (10.0, 0.0))
    # Path length should be around 11 points (0 to 10)
    assert len(path_clear) > 2
    
    # Place a massive storm in the middle (5,0)
    nav.add_obstacle(WeatherObstacle(5.0, 0.0, radius=3.0, severity=1.0))
    
    path_blocked = nav.find_path((0.0, 0.0), (10.0, 0.0))
    # It should route around it
    for node in path_blocked:
        # Distance to storm center should be >= radius
        dist = ((node[0] - 5.0)**2 + (node[1] - 0.0)**2)**0.5
        assert dist >= 2.9  # slight float tolerance

def test_analytics_and_trends():
    p = Port("P", 0.0, 0.0, 1000, 950)
    p.congestion_history = [0.6, 0.7, 0.8, 0.9]
    v = Vessel("V", 0.0, 0.0, 5000, speed=25.0, destination_port_id="P")
    
    detector = TrendDetector([p], [v])
    recs = detector.get_recommendations(NavigationEngine())
    assert any("critically trending upward" in r for r in recs)
    assert any("slow steaming" in r for r in recs)
    
    pred = PredictiveAnalytics([p], [v])
    assert "P" in pred.predict_bottlenecks()
    eta = pred.estimate_arrival_times()
    assert "V" in eta
