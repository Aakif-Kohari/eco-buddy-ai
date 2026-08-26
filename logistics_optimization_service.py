from route_planning_engine import RoutePlanningEngine
import datetime
from typing import Dict, List, Any

class LogisticsOptimizationService:
    """
    Manages daily commercial delivery routes and aggregates potential CO2 savings
    by forcing eco-friendly routing over traditional fast-routing.
    """
    
    def __init__(self, route_engine: RoutePlanningEngine):
        self.engine = route_engine
        self.jobs = []
        
    def add_delivery_job(self, start: str, end: str):
        self.jobs.append({"start": start, "end": end, "timestamp": datetime.datetime.now().isoformat()})
        
    def optimize_fleet(self) -> Dict[str, Any]:
        """
        Processes all queued jobs, tracks total emissions using the eco-router,
        and estimates what the "traditional" (ICE_VAN) emissions would have been.
        """
        results = []
        total_optimized_co2 = 0
        total_baseline_co2 = 0
        
        for job in self.jobs:
            eco_result = self.engine.find_safest_eco_path(job["start"], job["end"])
            
            if eco_result["status"] == "success":
                # Assuming baseline was ICE_VAN across the entire distance
                dist = eco_result["total_dist_km"]
                baseline_co2 = dist * 0.25 # ICE_VAN factor
                
                total_optimized_co2 += eco_result["total_co2_kg"]
                total_baseline_co2 += baseline_co2
                
                results.append({
                    "start": job["start"],
                    "end": job["end"],
                    "segments": eco_result["path"],
                    "optimized_co2": eco_result["total_co2_kg"],
                    "baseline_co2": baseline_co2,
                    "saved_co2": baseline_co2 - eco_result["total_co2_kg"]
                })

        savings_pct = (total_baseline_co2 - total_optimized_co2) / total_baseline_co2 * 100 if total_baseline_co2 > 0 else 0
        
        return {
            "jobs_processed": len(results),
            "total_baseline_co2_kg": round(total_baseline_co2, 2),
            "total_optimized_co2_kg": round(total_optimized_co2, 2),
            "total_co2_saved_kg": round(total_baseline_co2 - total_optimized_co2, 2),
            "savings_percentage": round(savings_pct, 1),
            "details": results
        }
