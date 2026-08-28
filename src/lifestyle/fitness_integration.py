import time
import random
from datetime import datetime, timedelta
from src.core.database import save_fitness_oauth_token, save_health_transport_metric

# Mock API credentials
MOCK_CLIENT_ID = "mock_client_id"
MOCK_CLIENT_SECRET = "mock_client_secret"

def get_oauth_url(provider: str) -> str:
    """Generates a mock OAuth authorization URL."""
    return f"https://mock-{provider}.com/oauth/authorize?client_id={MOCK_CLIENT_ID}&response_type=code&redirect_uri=http://localhost:8501"

def handle_oauth_callback(provider: str, code: str, user_id: str) -> bool:
    """Mocks the token exchange process and saves tokens."""
    if not code:
        return False
        
    # Simulate API call latency
    time.sleep(0.5)
    
    # Mock token response
    access_token = f"mock_access_token_{random.randint(1000, 9999)}"
    refresh_token = f"mock_refresh_token_{random.randint(1000, 9999)}"
    expires_at = time.time() + 3600  # 1 hour from now
    
    save_fitness_oauth_token(user_id, provider, access_token, refresh_token, expires_at)
    return True

def deduce_commute(activity_type: str, distance_km: float, hour: int) -> bool:
    """
    Deduces if an activity is likely a commute.
    Heuristic: Walk/Ride, distance between 1km and 20km, and during typical commute hours (6-9 AM or 4-7 PM).
    """
    if activity_type not in ["Walk", "Ride"]:
        return False
    
    is_commute_distance = 1.0 <= distance_km <= 20.0
    is_commute_time = (6 <= hour <= 9) or (16 <= hour <= 19)
    
    return is_commute_distance and is_commute_time

def fetch_and_process_activities(user_id: str, provider: str) -> int:
    """
    Mocks fetching activities from a fitness API for the past 7 days,
    processes them to find active transport, and calculates avoided CO2.
    Returns the number of new activities processed.
    """
    # In a real scenario, we'd use the stored access token to query the API.
    # Here, we generate mock data.
    
    processed_count = 0
    today = datetime.now()
    
    # 0.192 kg CO2 per km for an average car
    EMISSION_FACTOR_CAR_KG_PER_KM = 0.192 
    
    for i in range(7):
        date_obj = today - timedelta(days=i)
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # Randomly decide if there's an activity this day
        if random.random() > 0.3:
            activity_type = random.choice(["Walk", "Ride", "Run", "Yoga"])
            duration_minutes = random.uniform(15.0, 90.0)
            
            # Calculate distance based on activity
            if activity_type == "Ride":
                distance_km = duration_minutes * random.uniform(0.3, 0.5) # approx 18-30 km/h
                calories = duration_minutes * 8.0
            elif activity_type == "Run":
                distance_km = duration_minutes * random.uniform(0.15, 0.25) # approx 9-15 km/h
                calories = duration_minutes * 11.0
            elif activity_type == "Walk":
                distance_km = duration_minutes * random.uniform(0.06, 0.1) # approx 4-6 km/h
                calories = duration_minutes * 4.0
            else:
                distance_km = 0.0
                calories = duration_minutes * 3.0
            
            # Mock the start hour
            hour = random.choice([7, 8, 12, 17, 18, 19])
            
            # Calculate avoided CO2 if it's considered active transport (commute)
            avoided_co2 = 0.0
            if deduce_commute(activity_type, distance_km, hour):
                avoided_co2 = distance_km * EMISSION_FACTOR_CAR_KG_PER_KM
                
            save_health_transport_metric(
                user_id=user_id,
                date=date_str,
                activity_type=activity_type,
                duration_minutes=round(duration_minutes, 1),
                distance_km=round(distance_km, 2),
                calories_burned=round(calories, 1),
                avoided_co2_kg=round(avoided_co2, 2)
            )
            processed_count += 1
            
    return processed_count
