import pytest
import os
import numpy as np

from plugins.eco_rag_engine import EcoRAGEngine
from plugins.eco_rag_vector_store import SQLiteVectorStore
from plugins.eco_rag_data_connectors import DocumentSplitter
from plugins.eco_agent_tools import EcoAgentTools
from plugins.eco_agent_memory import EcoAgentMemory

# --- 1. Test SQLite Vector Store ---
def test_vector_store_persistence():
    db_path = "test_vector_store.db"
    store = SQLiteVectorStore(db_path=db_path)
    store.clear()
    
    # Create fake embedding (384 dimensions typical for all-MiniLM)
    emb = np.random.rand(384).astype(np.float32)
    
    store.insert("doc1", "Sustainability is important.", emb, {"source": "test"})
    
    # Retrieve
    doc = store.get_by_id("doc1")
    assert doc is not None
    assert doc["text"] == "Sustainability is important."
    assert doc["metadata"]["source"] == "test"
    
    # Search
    # Should find itself with similarity 1.0 (or very close)
    results = store.search(emb, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] > 0.99
    
    # Clean up
    os.remove(db_path)

def test_vector_store_batch_insert():
    db_path = "test_batch_store.db"
    store = SQLiteVectorStore(db_path=db_path)
    store.clear()
    
    docs = [
        {"id": "doc1", "text": "Text 1", "metadata": {}},
        {"id": "doc2", "text": "Text 2", "metadata": {}}
    ]
    embs = [np.random.rand(384).astype(np.float32), np.random.rand(384).astype(np.float32)]
    
    store.insert_batch(docs, embs)
    
    res1 = store.get_by_id("doc1")
    res2 = store.get_by_id("doc2")
    
    assert res1 is not None
    assert res2 is not None
    
    os.remove(db_path)


# --- 2. Test Document Splitter ---
def test_document_splitter():
    splitter = DocumentSplitter(chunk_size=50, chunk_overlap=10)
    text = "This is a very long sentence. " * 10 # ~300 chars
    
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 1
    # Check that chunks respect the size limit roughly
    for chunk in chunks:
        assert len(chunk) <= 60 # 50 + small buffer for breaking points


# --- 3. Test Agent Tools ---
def test_agent_tools_registry():
    tools = EcoAgentTools()
    schemas = tools.get_tool_schemas()
    
    assert len(schemas) == 3
    names = [s["function"]["name"] for s in schemas]
    assert "calculate_flight_emissions" in names
    assert "get_current_grid_intensity" in names

def test_agent_tool_execution():
    tools = EcoAgentTools()
    
    # Test valid execution
    args = '{"distance_km": 1000, "class_type": "economy"}'
    result_str = tools.execute_tool("calculate_flight_emissions", args)
    
    import json
    result = json.loads(result_str)
    
    assert result["success"] is True
    assert result["result"]["emissions_kg_co2"] == 150.0 # 1000 * 0.15
    
    # Test invalid tool
    result_str2 = tools.execute_tool("fake_tool", "{}")
    result2 = json.loads(result_str2)
    assert "error" in result2


# --- 4. Test RAG Engine Refactor ---
def test_eco_rag_initialization_and_mock_build():
    db_path = "test_rag.db"
    engine = EcoRAGEngine(db_path=db_path)
    
    # Build the mock profile which tests vector DB insertion
    engine.build_mock_user_profile()
    
    if engine.model is not None:
        # Test semantic retrieval from the SQLite DB
        docs = engine.retrieve_context("What do I eat?", top_k=1)
        assert len(docs) == 1
        assert "diet" in docs[0]["content"].lower()
        
        # Test LLM prompt generation
        response = engine.mock_llm_generation("How can I reduce emissions from my car?")
        assert "Recommendation" in response
        assert "carpooling" in response.lower()
        
    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)


# --- 5. Test Agent Memory ---
def test_agent_memory_sliding_window():
    db_path = "test_memory.db"
    mem = EcoAgentMemory(db_path=db_path, max_history_tokens=10) # tiny limit ~40 chars
    
    mem.clear_session("test_session")
    
    # Message 1 (22 chars)
    mem.append_message("test_session", "user", "Hello, who are you?")
    # Message 2 (27 chars)
    mem.append_message("test_session", "assistant", "I am your Eco-Assistant.")
    # Message 3 (20 chars)
    mem.append_message("test_session", "user", "What is my footprint?")
    
    # Total chars = 69. Max allowed = 40. 
    # It should only return the last message (or two if they fit)
    context = mem.get_context_window("test_session")
    
    assert len(context) > 0
    # The newest message must definitely be in there
    assert context[-1]["content"] == "What is my footprint?"
    # The oldest message should be truncated
    assert context[0]["content"] != "Hello, who are you?"
    
    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)
