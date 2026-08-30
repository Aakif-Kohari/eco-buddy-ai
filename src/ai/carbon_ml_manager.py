import threading
import time
import logging

logger = logging.getLogger(__name__)

class MockMLModel:
    """Simulates a heavy TensorFlow/ONNX model that takes time to load and run."""
    def __init__(self):
        logger.info("Initializing heavy Machine Learning model into RAM...")
        time.sleep(2) # Simulate heavy load time
        logger.info("Model loaded successfully.")

    def predict(self, batch_tensor: list) -> list:
        # Simulate inference time
        time.sleep(0.1)
        # Mock calculation: sum of features * random multiplier
        return [sum(features) * 1.5 for features in batch_tensor]


class CarbonModelManager:
    """
    Singleton Manager for the Carbon Footprint ML Model.
    Ensures the heavy model is only loaded into RAM exactly once during the application lifecycle,
    resolving the massive memory leak that was crashing the backend (Issue #1469).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CarbonModelManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self.model = MockMLModel()
        # Use a semaphore to limit concurrent inference threads to prevent CPU starvation
        self.inference_pool = threading.BoundedSemaphore(value=10)

    def predict_batch(self, batch_tensor: list) -> list:
        """
        Executes a batched inference request.
        Locks via semaphore to ensure we don't overwhelm the CPU if 1000s of requests hit at once.
        """
        with self.inference_pool:
            logger.debug(f"Processing inference for batch of size {len(batch_tensor)}")
            return self.model.predict(batch_tensor)

# Export the singleton instance
carbon_model_manager = CarbonModelManager()
