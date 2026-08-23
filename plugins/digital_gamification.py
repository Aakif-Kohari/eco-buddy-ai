from typing import List, Dict, Any

class DigitalGamificationEngine:
    """
    Evaluates a user's digital footprint results and unlocks specific achievements,
    badges, and streaks to encourage sustainable digital habits.
    """
    
    BADGES = {
        "LOW_RES_LEGEND": {
            "name": "Low-Res Legend",
            "icon": "📺",
            "description": "You primarily stream in 720p or 1080p instead of 4K, saving massive amounts of data."
        },
        "CLOUD_CLEANER": {
            "name": "Cloud Cleaner",
            "icon": "☁️",
            "description": "You maintain a highly efficient cloud storage footprint (< 10GB)."
        },
        "DEVICE_VETERAN": {
            "name": "Device Veteran",
            "icon": "🛡️",
            "description": "You have kept your primary device for over 4 years, dramatically reducing embodied carbon."
        },
        "WIFI_WARRIOR": {
            "name": "WiFi Warrior",
            "icon": "📶",
            "description": "You exclusively use WiFi instead of energy-heavy cellular networks."
        },
        "AI_MINIMALIST": {
            "name": "AI Minimalist",
            "icon": "🤖",
            "description": "You use generative AI sparingly, avoiding unnecessary server compute."
        },
        "GREEN_GRID": {
            "name": "Green Grid",
            "icon": "🌍",
            "description": "Your digital devices are powered by a low-carbon energy grid (< 0.3 kg CO2/kWh)."
        }
    }

    def __init__(self, ui_metadata: Dict[str, Any], lifecycle_metadata: Dict[str, Any], total_kg: float):
        self.meta = ui_metadata
        self.life = lifecycle_metadata
        self.total_kg = total_kg
        self.unlocked_badges = []

    def evaluate(self) -> Dict[str, Any]:
        """Runs all rules to determine unlocked badges and current streaks."""
        self._evaluate_streaming()
        self._evaluate_cloud()
        self._evaluate_hardware()
        self._evaluate_network()
        self._evaluate_ai()
        self._evaluate_grid()
        
        # Calculate a completely arbitrary "Digital Eco Score" (0-100)
        # Based on badges unlocked and total footprint
        base_score = 50
        base_score += len(self.unlocked_badges) * 5
        
        # Penalize for massive footprints
        if self.total_kg > 500:
            base_score -= 10
        if self.total_kg > 1000:
            base_score -= 20
            
        eco_score = max(0, min(100, base_score))
        
        return {
            "score": eco_score,
            "badges": [self.BADGES[b] for b in self.unlocked_badges],
            "next_goal": self._get_next_goal()
        }

    def _evaluate_streaming(self):
        if not self.meta.get("is_high_res"):
            self.unlocked_badges.append("LOW_RES_LEGEND")
            
    def _evaluate_cloud(self):
        # We need to extract cloud storage GB if available, else check boolean
        if not self.meta.get("cloud_heavy"):
            self.unlocked_badges.append("CLOUD_CLEANER")

    def _evaluate_hardware(self):
        if self.life.get("age_years", 0) >= 4.0:
            self.unlocked_badges.append("DEVICE_VETERAN")
            
    def _evaluate_network(self):
        if self.meta.get("network") in ["WiFi", "Wired"]:
            self.unlocked_badges.append("WIFI_WARRIOR")
            
    def _evaluate_ai(self):
        if not self.meta.get("ai_heavy"):
            self.unlocked_badges.append("AI_MINIMALIST")
            
    def _evaluate_grid(self):
        if self.meta.get("grid_intensity", 1.0) < 0.3:
            self.unlocked_badges.append("GREEN_GRID")
            
    def _get_next_goal(self) -> str:
        """Determines the easiest badge the user has not yet unlocked."""
        locked = set(self.BADGES.keys()) - set(self.unlocked_badges)
        if not locked:
            return "You are a Digital Sustainability Master! You've unlocked everything."
            
        if "DEVICE_VETERAN" in locked:
            return "Try to keep your current device for at least 4 years to unlock 'Device Veteran'."
        if "LOW_RES_LEGEND" in locked:
            return "Drop your streaming resolution to 1080p to unlock 'Low-Res Legend'."
        if "WIFI_WARRIOR" in locked:
            return "Connect to WiFi instead of 4G/5G to unlock 'WiFi Warrior'."
            
        return "Keep lowering your total screen time to improve your Eco Score!"
