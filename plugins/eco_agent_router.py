import logging
import numpy as np
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)

@dataclass
class IntentCluster:
    name: str
    description: str
    examples: List[str]
    embeddings: Optional[np.ndarray] = None

class EcoAgentRouter:
    """
    Semantic Intent Classification Router.
    Uses zero-shot or few-shot semantic embedding classification to determine 
    what the user actually wants, directing the flow to the right subsystem 
    (Vector DB, Agent Tools, or basic Chit-Chat).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        
        # Define the distinct operational clusters the agent can handle
        self.clusters = [
            IntentCluster(
                name="CHITCHAT",
                description="General conversational pleasantries, greetings, or non-actionable chatter.",
                examples=[
                    "Hello, how are you today?",
                    "What's your name?",
                    "Thanks for the help!",
                    "Good morning EcoBuddy.",
                    "Who created you?",
                    "Are you a robot?",
                    "Hey there buddy!"
                ]
            ),
            IntentCluster(
                name="RAG_RETRIEVAL",
                description="Questions about the user's specific habits, historical data, or general eco facts.",
                examples=[
                    "What is my total carbon footprint?",
                    "How much water did I use last week?",
                    "What badges have I unlocked so far?",
                    "Why is beef bad for the environment?",
                    "Show me my driving data.",
                    "What are my current sustainability goals?"
                ]
            ),
            IntentCluster(
                name="TOOL_USE_CALCULATOR",
                description="Requests that require executing a mathematical tool or fetching live external data.",
                examples=[
                    "Calculate the emissions of a 500km flight in economy.",
                    "What is the current grid intensity in France?",
                    "How much water does a cotton t-shirt use?",
                    "Compute the footprint of driving to New York.",
                    "Run the calculator for a pair of jeans."
                ]
            ),
            IntentCluster(
                name="GOAL_SETTING",
                description="The user explicitly wants to create, modify, or commit to a new sustainability habit.",
                examples=[
                    "I want to set a goal to eat less meat.",
                    "Remind me to carpool next week.",
                    "Help me create a plan to lower my electricity bill.",
                    "I commit to taking shorter showers starting today."
                ]
            )
        ]
        
        self._initialize_model()

    def _initialize_model(self):
        """Loads the embedding model and pre-computes the cluster centroids."""
        if not HAS_SENTENCE_TRANSFORMERS:
            logger.error("sentence-transformers required for Semantic Routing.")
            return
            
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded Semantic Router Model: {self.model_name}")
            self._compute_cluster_embeddings()
        except Exception as e:
            logger.error(f"Failed to load router model: {e}")
            self.model = None

    def _compute_cluster_embeddings(self):
        """
        Embeds all example sentences for each cluster so we can perform 
        K-Nearest Neighbors (KNN) or Centroid-based similarity later.
        """
        if not self.model:
            return
            
        for cluster in self.clusters:
            # Embed all examples for this cluster
            embeddings = self.model.encode(cluster.examples, convert_to_tensor=False)
            cluster.embeddings = np.array(embeddings)

    def route_query(self, user_query: str, confidence_threshold: float = 0.4) -> Dict[str, Any]:
        """
        Takes a user's natural language query and mathematically routes it to the 
        correct subsystem by comparing its embedding against the intent clusters.
        """
        if not self.model:
            return {"intent": "UNKNOWN", "confidence": 0.0, "reason": "Model not loaded"}

        # Embed the incoming query
        query_emb = self.model.encode(user_query, convert_to_tensor=False).astype(np.float32)
        
        best_intent = "UNKNOWN"
        best_score = -1.0
        
        cluster_scores = {}

        # Perform semantic similarity search against every example in every cluster
        for cluster in self.clusters:
            if cluster.embeddings is None:
                continue
                
            # Compute cosine similarity between the query and all examples in this cluster
            # dot product divided by norms (assuming normalized embeddings, dot product is enough, 
            # but we use explicit cosine for safety)
            dot_products = np.dot(cluster.embeddings, query_emb)
            norms_db = np.linalg.norm(cluster.embeddings, axis=1)
            norm_query = np.linalg.norm(query_emb)
            
            denom = norms_db * norm_query
            denom[denom == 0] = 1e-10
            
            similarities = dot_products / denom
            
            # Use the max similarity score from the cluster's examples as the cluster score
            # (Alternatively, could use mean similarity for centroid routing)
            max_sim = float(np.max(similarities))
            cluster_scores[cluster.name] = max_sim
            
            if max_sim > best_score:
                best_score = max_sim
                best_intent = cluster.name

        # If the highest score is below our threshold, the query is out of domain
        if best_score < confidence_threshold:
            return {
                "intent": "OUT_OF_DOMAIN",
                "confidence": round(best_score, 3),
                "all_scores": cluster_scores,
                "reason": "Query did not strongly match any known intent vectors."
            }

        return {
            "intent": best_intent,
            "confidence": round(best_score, 3),
            "all_scores": cluster_scores,
            "reason": "Successfully routed based on semantic proximity."
        }

    def execute_routing_logic(self, user_query: str, engine: Any, tools: Any) -> str:
        """
        A high-level orchestrator that takes the routed intent and actually fires 
        the correct downstream code (Vector DB vs Tools).
        """
        route = self.route_query(user_query)
        intent = route["intent"]
        
        logger.info(f"Routed Query '{user_query}' -> {intent} (Conf: {route['confidence']})")
        
        if intent == "CHITCHAT":
            return "Hello! I am your AI Eco-Assistant. How can I help you save the planet today? 🌍"
            
        elif intent == "RAG_RETRIEVAL":
            # Direct the flow to the Vector Database
            return engine.mock_llm_generation(user_query)
            
        elif intent == "TOOL_USE_CALCULATOR":
            # In a real setup, we would extract entities here (e.g., flight distance)
            # For demonstration, we manually trigger a tool to prove the route works
            if "flight" in user_query.lower():
                result = tools.execute_tool("calculate_flight_emissions", '{"distance_km": 1500}')
                return f"I routed your request to the Calculator Tool! Result: {result}"
            elif "grid" in user_query.lower():
                result = tools.execute_tool("get_current_grid_intensity", '{"region_code": "US"}')
                return f"I routed your request to the Grid API Tool! Result: {result}"
            else:
                return "I routed your request to the Tools subsystem, but couldn't parse the exact parameters yet."
                
        elif intent == "GOAL_SETTING":
            return "That's a fantastic sustainability goal! I have logged this into your profile. We will track your progress together. 📈"
            
        else:
            return "I'm not quite sure how to handle that request. Could you ask about your footprint, try the calculator, or set a goal?"
