import pytest
import os
import numpy as np

from plugins.eco_rag_engine import EcoRAGEngine
from plugins.eco_rag_vector_store import SQLiteVectorStore
from plugins.eco_rag_data_connectors import DocumentSplitter
from plugins.eco_agent_tools import EcoAgentTools
from plugins.eco_agent_memory import EcoAgentMemory
from plugins.eco_agent_router import EcoAgentRouter

# --- 1. Test SQLite Vector Store ---
def test_vector_store_persistence():
    db_path = "test_vector_store.db"
    store = SQLiteVectorStore(db_path=db_path)
    store.clear()
    
    emb = np.random.rand(384).astype(np.float32)
    store.insert("doc1", "Sustainability is important.", emb, {"source": "test"})
    
    doc = store.get_by_id("doc1")
    assert doc is not None
    assert doc["text"] == "Sustainability is important."
    
    results = store.search(emb, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    
    os.remove(db_path)

def test_vector_store_batch_insert():
    db_path = "test_batch_store.db"
    store = SQLiteVectorStore(db_path=db_path)
    store.clear()
    
    docs = [{"id": "doc1", "text": "T1"}, {"id": "doc2", "text": "T2"}]
    embs = [np.random.rand(384).astype(np.float32), np.random.rand(384).astype(np.float32)]
    
    store.insert_batch(docs, embs)
    assert store.get_by_id("doc1") is not None
    os.remove(db_path)

# --- 2. Test Document Splitter ---
def test_document_splitter():
    splitter = DocumentSplitter(chunk_size=50, chunk_overlap=10)
    text = "This is a very long sentence. " * 10
    chunks = splitter.split_text(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 60

# --- 3. Test Agent Tools ---
def test_agent_tools_registry():
    tools = EcoAgentTools()
    schemas = tools.get_tool_schemas()
    assert len(schemas) == 3

def test_agent_tool_execution():
    tools = EcoAgentTools()
    args = '{"distance_km": 1000, "class_type": "economy"}'
    result_str = tools.execute_tool("calculate_flight_emissions", args)
    
    import json
    result = json.loads(result_str)
    assert result["success"] is True
    assert result["result"]["emissions_kg_co2"] == 150.0

# --- 4. Test RAG Engine Refactor ---
def test_eco_rag_initialization_and_mock_build():
    db_path = "test_rag.db"
    engine = EcoRAGEngine(db_path=db_path)
    engine.build_mock_user_profile()
    
    if engine.model is not None:
        docs = engine.retrieve_context("What do I eat?", top_k=1)
        assert len(docs) == 1
        assert "diet" in docs[0]["content"].lower()
    if os.path.exists(db_path):
        os.remove(db_path)

# --- 5. Test Agent Memory ---
def test_agent_memory_sliding_window():
    db_path = "test_memory.db"
    mem = EcoAgentMemory(db_path=db_path, max_history_tokens=10)
    mem.clear_session("test_session")
    
    mem.append_message("test_session", "user", "Hello, who are you?")
    mem.append_message("test_session", "assistant", "I am your Eco-Assistant.")
    mem.append_message("test_session", "user", "What is my footprint?")
    
    context = mem.get_context_window("test_session")
    assert len(context) > 0
    assert context[-1]["content"] == "What is my footprint?"
    if os.path.exists(db_path):
        os.remove(db_path)

# --- 6. Test Semantic Router ---
def test_eco_agent_router_classification():
    router = EcoAgentRouter()
    
    if router.model is not None:
        # Test ChitChat intent
        res_chit = router.route_query("Hey there buddy!")
        assert res_chit["intent"] == "CHITCHAT"
        
        # Test Tool Use intent
        res_tool = router.route_query("Calculate my flight to London.")
        assert res_tool["intent"] == "TOOL_USE_CALCULATOR"
        
        # Test RAG intent
        res_rag = router.route_query("Show me my carbon footprint from last week.")
        assert res_rag["intent"] == "RAG_RETRIEVAL"
        
        # Test Goal Setting intent
        res_goal = router.route_query("I want to set a goal to eat less beef.")
        assert res_goal["intent"] == "GOAL_SETTING"
        
        # Test Out of Domain
        res_out = router.route_query("What is the capital of Mars?", confidence_threshold=0.8)
        assert res_out["intent"] == "OUT_OF_DOMAIN"
