import pytest
from src.services.climate_policy_nlp import (
    VectorMath,
    Tokenizer,
    TFIDF,
    SentimentPolarity,
    ClimatePolicyEngine,
    PolicyDocument
)

def test_tokenization_edge_cases():
    tokens = Tokenizer.tokenize("Hello, World! Eco-Friendly 123.")
    assert tokens == ["hello", "world", "eco", "friendly", "123"]
    
def test_vector_math_cosine_similarity():
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0]
    assert VectorMath.cosine_similarity(v1, v2) == 1.0
    
    v3 = [0.0, 1.0]
    assert VectorMath.cosine_similarity(v1, v3) == 0.0
    
    assert VectorMath.cosine_similarity([0.0], [0.0]) == 0.0

def test_rag_pipeline_retrieval_accuracy():
    engine = ClimatePolicyEngine()
    docs = [
        {"id": "1", "entity_name": "A", "year": 2020, "text": "solar wind energy"},
        {"id": "2", "entity_name": "B", "year": 2020, "text": "oil gas fossil fuels"}
    ]
    engine.ingest_documents(docs)
    
    results = engine.rag.retrieve("solar energy", top_k=1)
    assert len(results) == 1
    assert results[0].entity_name == "A"
    
def test_regression_detection():
    engine = ClimatePolicyEngine()
    docs = [
        {"id": "1", "entity_name": "Corp", "year": 2020, "text": "invest reduce execute budget"}, # Actionable
        {"id": "2", "entity_name": "Corp", "year": 2022, "text": "hope explore consider aim"}    # Greenwashing
    ]
    engine.ingest_documents(docs)
    
    reg = engine.detect_regression("Corp")
    assert reg["regression_detected"] is True
    assert reg["score_change"] < 0
    
def test_predictive_progress():
    engine = ClimatePolicyEngine()
    docs = [
        {"id": "1", "entity_name": "Corp", "year": 2020, "text": "invest reduce execute budget"}, 
        {"id": "2", "entity_name": "Corp", "year": 2022, "text": "hope explore consider aim"}    
    ]
    engine.ingest_documents(docs)
    
    prob = engine.predict_goal_adherence("Corp")
    assert 0.0 <= prob <= 1.0
