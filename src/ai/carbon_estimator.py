import time
import logging
from typing import List, Dict, Any
from .carbon_ml_manager import carbon_model_manager
from src.integrations.watt_time_api import watt_time_client

logger = logging.getLogger(__name__)

class CarbonEstimator:
    """
    Predictive engine that transforms user activity logs into carbon footprint estimates.
    Refactored to utilize the CarbonModelManager (Singleton) and support request batching
    to prevent memory leaks and OOM crashes under load (Issue #1469).
    """
    
    def __init__(self):
        # We maintain a small local queue for batching requests
        self._request_queue = []
        self._batch_size = 50
        
    def add_to_queue(self, user_id: str, zip_code: str, activity_features: List[float]):
        """
        Appends a user request to the batch queue.
        """
        # Fetch real-time grid emissions scalar from WattTime to improve accuracy
        grid_emissions_scalar = watt_time_client.get_realtime_emissions(zip_code)
        
        # Append the external API data as a dynamic feature vector to the user's base features
        enriched_features = activity_features + [grid_emissions_scalar / 1000.0] # Normalize

        self._request_queue.append({
            'user_id': user_id,
            'features': enriched_features
        })

    def flush_queue(self) -> List[Dict[str, Any]]:
        """
        Processes the queue in batches and routes them to the Singleton ML Manager.
        Returns the calculated footprint estimates.
        """
        if not self._request_queue:
            return []

        results = []
        
        # Chunk the queue into defined batch sizes (e.g. 50)
        for i in range(0, len(self._request_queue), self._batch_size):
            batch = self._request_queue[i:i + self._batch_size]
            
            # Extract just the tensors
            batch_tensors = [item['features'] for item in batch]
            
            # Pass the batched tensors to the thread-safe Model Manager
            logger.info(f"Flushing batch of {len(batch)} to CarbonModelManager...")
            predictions = carbon_model_manager.predict_batch(batch_tensors)
            
            # Re-associate predictions with user_ids
            for j, item in enumerate(batch):
                results.append({
                    'user_id': item['user_id'],
                    'estimated_kg_co2': predictions[j]
                })

        # Clear the queue
        self._request_queue = []
        
        return results

    def estimate_single_user_synchronous(self, user_id: str, zip_code: str, activity_features: List[float]) -> float:
        """
        Utility for synchronously predicting a single user.
        Useful for low-traffic endpoints, but still routes through the Singleton to prevent RAM spikes.
        """
        self.add_to_queue(user_id, zip_code, activity_features)
        res = self.flush_queue()
        return res[0]['estimated_kg_co2']

# Export a default instance for standard usage
carbon_estimator = CarbonEstimator()
