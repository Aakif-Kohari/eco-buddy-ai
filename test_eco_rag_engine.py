import pytest
from plugins.eco_rag_engine import EcoRAGEngine

def test_eco_rag_initialization():
    engine = EcoRAGEngine()
    assert len(engine.knowledge_base) > 0
    # Check if a fact exists
    topics = [doc["topic"] for doc in engine.knowledge_base]
    assert "Carbon Footprint" in topics
    assert "Diet" in topics

def test_eco_rag_fallback_retrieval():
    # If the model fails or we explicitly test fallback
    engine = EcoRAGEngine()
    
    # Test a keyword query
    docs = engine._fallback_keyword_search("beef diet", top_k=2)
    assert len(docs) > 0
    # The first document should likely be about beef/diet
    assert "beef" in docs[0]["content"].lower()

def test_eco_rag_semantic_retrieval():
    engine = EcoRAGEngine()
    
    if engine.model is not None:
        # Test semantic query
        docs = engine.retrieve_context("What do I eat?", top_k=1)
        assert len(docs) == 1
        assert "diet" in docs[0]["topic"].lower()
        
        # Test another semantic query
        docs2 = engine.retrieve_context("How long are my showers?", top_k=1)
        assert len(docs2) == 1
        assert "water" in docs2[0]["topic"].lower()
        
def test_mock_llm_generation():
    engine = EcoRAGEngine()
    
    # Test generation based on driving
    response = engine.mock_llm_generation("How can I reduce emissions from my car?")
    assert "Recommendation" in response
    assert "carpooling" in response.lower()
    
    # Test generation based on diet
    response2 = engine.mock_llm_generation("What should I change about my diet?")
    assert "Recommendation" in response2
    assert "plant-based" in response2.lower()
