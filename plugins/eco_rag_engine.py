import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from plugins.eco_rag_vector_store import SQLiteVectorStore
from plugins.eco_rag_data_connectors import EcoDataIngestionPipeline

logger = logging.getLogger(__name__)

class EcoRAGEngine:
    """
    Advanced Retrieval-Augmented Generation (RAG) engine.
    Uses sentence-transformers for embedding generation and a custom SQLite 
    database for persistent vector storage and rapid cosine similarity search.
    """

    def __init__(self, db_path: str = "eco_vector_store.db", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model_name = model_name
        self.model = None
        self.vector_store = SQLiteVectorStore(db_path=self.db_path)
        self.pipeline = EcoDataIngestionPipeline()
        
        self._initialize_model()

    def _initialize_model(self):
        """Loads the local sentence transformer model for semantic search."""
        if not HAS_SENTENCE_TRANSFORMERS:
            logger.warning("sentence-transformers not installed. RAG degraded.")
            return
            
        try:
            # all-MiniLM-L6-v2 is extremely fast and lightweight (~80MB)
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer model: {e}")
            self.model = None

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Generates an embedding vector for a given string."""
        if not self.model:
            return None
        # Convert tensor to numpy array immediately for SQLite storage
        return self.model.encode(text, convert_to_tensor=False)

    def ingest_document(self, file_path_or_url: str):
        """
        Ingests a PDF or URL, splits it into chunks, embeds them, 
        and stores them persistently in the SQLite Vector Database.
        """
        if not self.model:
            logger.error("Cannot ingest without embedding model.")
            return False
            
        # Parse and chunk
        if file_path_or_url.startswith("http"):
            docs = self.pipeline.ingest_url(file_path_or_url)
        else:
            docs = self.pipeline.ingest_pdf(file_path_or_url)
            
        if not docs:
            return False
            
        # Embed all chunks
        texts = [doc["text"] for doc in docs]
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        
        # Batch insert into Vector DB
        self.vector_store.insert_batch(docs, embeddings)
        logger.info(f"Successfully ingested {len(docs)} chunks into Vector Store.")
        return True

    def build_mock_user_profile(self):
        """Injects the user's specific footprint profile into the persistent DB."""
        if not self.model:
            return
            
        # Clear old profile data
        self.vector_store.clear()
        
        raw_data = [
            {"id": "usr_1", "text": "The user's total annual carbon footprint is 14,500 kg CO2e.", "metadata": {"source": "profile"}},
            {"id": "usr_2", "text": "The user drives a gasoline SUV.", "metadata": {"source": "profile"}},
            {"id": "usr_3", "text": "The user eats a high-meat diet, specifically beef 4 times a week.", "metadata": {"source": "profile"}},
            {"id": "usr_4", "text": "The user streams 4K video for 4 hours daily on a 5G network.", "metadata": {"source": "profile"}},
            {"id": "usr_5", "text": "The user takes 20-minute hot showers daily.", "metadata": {"source": "profile"}},
            {"id": "usr_6", "text": "The user has unlocked the 'Recycling Hero' badge.", "metadata": {"source": "profile"}}
        ]
        
        texts = [doc["text"] for doc in raw_data]
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        self.vector_store.insert_batch(raw_data, embeddings)

    def retrieve_context(self, user_query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Queries the persistent SQLite Vector Database using Cosine Similarity.
        """
        if not self.model:
            return []
            
        query_embedding = self.embed_text(user_query)
        if query_embedding is None:
            return []
            
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        # Format for legacy compatibility with the UI
        formatted = []
        for r in results:
            formatted.append({
                "content": r["text"],
                "relevance_score": round(r["score"], 3),
                "metadata": r["metadata"]
            })
            
        return formatted

    def mock_llm_generation(self, user_query: str) -> str:
        """
        Simulates an LLM response using the persistent vector store.
        """
        contexts = self.retrieve_context(user_query)
        
        if not contexts:
            return "I couldn't find any specific data about that in your footprint profile. Could you clarify your question? 🌱"
            
        primary_context = contexts[0]['content']
        
        response = f"Based on your profile and our knowledge base, here is what I found:\n\n> *\"{primary_context}\"*\n\n"
        
        if "diet" in user_query.lower() or "beef" in user_query.lower() or "food" in user_query.lower():
            response += "🥩 **Recommendation:** Try swapping beef for chicken or plant-based alternatives just twice a week to significantly lower this metric!"
        elif "drive" in user_query.lower() or "car" in user_query.lower() or "transport" in user_query.lower():
            response += "🚗 **Recommendation:** You mentioned carpooling as a goal. Setting up a schedule with coworkers can cut these emissions in half!"
        elif "digital" in user_query.lower() or "stream" in user_query.lower():
            response += "📱 **Recommendation:** Lowering your streaming resolution from 4K to 1080p on cellular networks saves massive amounts of energy."
        else:
            response += "💡 **Recommendation:** Small incremental changes are the best way to reach your sustainability goals. Keep it up!"
            
        return response
