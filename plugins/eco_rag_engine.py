import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Any, Tuple
import logging

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)

class EcoRAGEngine:
    """
    Retrieval-Augmented Generation (RAG) engine for the Eco-Assistant Chatbot.
    Uses sentence-transformers to embed the user's local SQLite footprint data,
    allowing the chatbot to answer highly personalized questions.
    """

    def __init__(self, db_path: str = "eco_buddy.db", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model_name = model_name
        self.model = None
        self.knowledge_base: List[Dict[str, Any]] = []
        self.kb_embeddings = None
        
        self._initialize_model()
        self._build_knowledge_base()

    def _initialize_model(self):
        """Loads the local sentence transformer model for semantic search."""
        if not HAS_SENTENCE_TRANSFORMERS:
            logger.warning("sentence-transformers not installed. RAG will fallback to keyword search.")
            return
            
        try:
            # all-MiniLM-L6-v2 is extremely fast and lightweight (~80MB)
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer model: {e}")
            self.model = None

    def _build_knowledge_base(self):
        """
        Extracts all relevant user footprint data, gamification badges, and goals 
        from the local SQLite database and converts them into natural language 'documents' 
        that the LLM can understand.
        """
        # In a real scenario, we would query the actual tables.
        # For this implementation, we will simulate the extraction of rich context
        # from the various modules we have (e.g. emissions, water, digital, gamification).
        
        # Mocking the database extraction process to ensure robust structural code
        raw_data_extracts = [
            {"topic": "Carbon Footprint", "content": "The user's total annual carbon footprint is 14,500 kg CO2e, which is 20% higher than the global average."},
            {"topic": "Transportation", "content": "The user primarily drives a gasoline SUV, contributing to 45% of their total emissions."},
            {"topic": "Diet", "content": "The user eats a high-meat diet, specifically beef 4 times a week, resulting in 3,200 kg CO2e annually."},
            {"topic": "Digital Footprint", "content": "The user streams 4K video for 4 hours daily on a 5G network, causing high digital emissions."},
            {"topic": "Water Usage", "content": "The user takes 20-minute hot showers daily, using 150 gallons of water per week."},
            {"topic": "Gamification Badges", "content": "The user has unlocked the 'Recycling Hero' and 'Meatless Monday' badges."},
            {"topic": "Current Goals", "content": "The user's active goal is to reduce their transportation footprint by carpooling twice a week."},
            {"topic": "Home Energy", "content": "The user's home uses a natural gas furnace and lacks solar panels. Monthly electricity usage is 900 kWh."}
        ]
        
        # Append general sustainability facts to supplement personal data
        general_facts = [
            {"topic": "Beef Impact", "content": "Producing 1 kg of beef emits about 60 kg of greenhouse gases."},
            {"topic": "EV Savings", "content": "Switching to an electric vehicle can reduce transportation emissions by up to 70% depending on the local grid."},
            {"topic": "Cold Wash", "content": "Washing clothes in cold water saves up to 90% of the energy used by a washing machine."},
            {"topic": "LED Bulbs", "content": "LED light bulbs use 75% less energy and last 25 times longer than incandescent lighting."}
        ]
        
        self.knowledge_base = raw_data_extracts + general_facts
        
        if self.model:
            # Pre-compute embeddings for the entire knowledge base
            documents = [doc["content"] for doc in self.knowledge_base]
            self.kb_embeddings = self.model.encode(documents, convert_to_tensor=True)

    def retrieve_context(self, user_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Uses cosine similarity to find the most relevant facts from the knowledge base 
        based on the user's natural language query.
        """
        if not self.model or self.kb_embeddings is None:
            return self._fallback_keyword_search(user_query, top_k)
            
        try:
            # Embed the user's query
            query_embedding = self.model.encode(user_query, convert_to_tensor=True)
            
            # Compute cosine similarities
            cosine_scores = util.cos_sim(query_embedding, self.kb_embeddings)[0]
            
            # Find the top_k highest scores
            top_results = np.argpartition(-cosine_scores.cpu().numpy(), range(top_k))[:top_k]
            
            retrieved_docs = []
            for idx in top_results:
                score = cosine_scores[idx].item()
                if score > 0.1: # Minimum relevance threshold
                    doc = self.knowledge_base[idx].copy()
                    doc["relevance_score"] = round(score, 3)
                    retrieved_docs.append(doc)
                    
            # Sort by relevance descending
            retrieved_docs = sorted(retrieved_docs, key=lambda x: x["relevance_score"], reverse=True)
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._fallback_keyword_search(user_query, top_k)

    def _fallback_keyword_search(self, user_query: str, top_k: int) -> List[Dict[str, Any]]:
        """A simple keyword matching algorithm if ML embeddings fail."""
        query_words = set(user_query.lower().split())
        
        scored_docs = []
        for doc in self.knowledge_base:
            content_words = set(doc["content"].lower().split())
            intersection = query_words.intersection(content_words)
            score = len(intersection) / max(1, len(query_words))
            
            if score > 0:
                d = doc.copy()
                d["relevance_score"] = round(score, 3)
                scored_docs.append(d)
                
        scored_docs = sorted(scored_docs, key=lambda x: x["relevance_score"], reverse=True)
        return scored_docs[:top_k]

    def construct_llm_prompt(self, user_query: str, chat_history: List[Dict[str, str]] = None) -> str:
        """
        Constructs the final highly-engineered prompt to send to the LLM.
        Injects the retrieved context dynamically.
        """
        contexts = self.retrieve_context(user_query)
        
        context_block = "\n".join([f"- {doc['content']}" for doc in contexts])
        
        prompt = f"""You are 'EcoBuddy', a highly intelligent, empathetic, and encouraging AI sustainability assistant.
Your goal is to help the user understand their environmental impact and provide actionable advice.

Here is the retrieved context about the user's specific lifestyle and relevant environmental facts:
{context_block if context_block else "- No specific context found."}

Please answer the user's question accurately using ONLY the context provided above. 
If the context does not contain the answer, provide general sustainable advice but admit you don't have their exact data.
Be concise, use formatting (bullet points, bold text), and include relevant emojis.

User Question: "{user_query}"
EcoBuddy Response:"""
        
        return prompt

    def mock_llm_generation(self, user_query: str) -> str:
        """
        Simulates an LLM response for local testing without an API key.
        Uses the RAG retrieval to construct a smart template response.
        """
        contexts = self.retrieve_context(user_query)
        
        if not contexts:
            return "I couldn't find any specific data about that in your footprint profile. Could you clarify your question? 🌱"
            
        primary_context = contexts[0]['content']
        
        # Simple heuristic generation
        response = f"Based on your profile data, here is what I found:\n\n> *\"{primary_context}\"*\n\n"
        
        if "diet" in user_query.lower() or "beef" in user_query.lower() or "food" in user_query.lower():
            response += "🥩 **Recommendation:** Try swapping beef for chicken or plant-based alternatives just twice a week to significantly lower this metric!"
        elif "drive" in user_query.lower() or "car" in user_query.lower() or "transport" in user_query.lower():
            response += "🚗 **Recommendation:** You mentioned carpooling as a goal. Setting up a schedule with coworkers can cut these emissions in half!"
        elif "digital" in user_query.lower() or "stream" in user_query.lower():
            response += "📱 **Recommendation:** Lowering your streaming resolution from 4K to 1080p on cellular networks saves massive amounts of energy."
        else:
            response += "💡 **Recommendation:** Small incremental changes are the best way to reach your sustainability goals. Keep it up!"
            
        return response
