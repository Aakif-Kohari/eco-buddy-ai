import streamlit as st
import time
from plugins.eco_rag_engine import EcoRAGEngine

# Configure the Streamlit page
st.set_page_config(
    page_title="Eco-Assistant AI",
    page_icon="🤖",
    layout="wide"
)

# Initialize the RAG engine in session state so we don't reload the model on every render
if "rag_engine" not in st.session_state:
    with st.spinner("Initializing AI and loading embedding models..."):
        # This will download the 80MB model on first run if not cached
        st.session_state.rag_engine = EcoRAGEngine()

rag_engine = st.session_state.rag_engine

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your AI Eco-Assistant. I have access to your carbon footprint data, goals, and habits. How can I help you reduce your environmental impact today? 🌱"}
    ]

st.title("🤖 Eco-Assistant Chat")
st.markdown("Ask me anything about your carbon footprint, sustainability goals, or how to reduce your emissions!")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about your diet, driving, or digital footprint..."):
    
    # 1. Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate and display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Simulate thinking delay
        with st.spinner("Searching your personal footprint data..."):
            time.sleep(1.0)
            
            # Retrieve relevant context to show the user what the AI "read"
            contexts = rag_engine.retrieve_context(prompt, top_k=2)
            
            # Show a brief expander with the retrieved context (for transparency)
            if contexts:
                with st.expander("View Retrieved Context"):
                    for i, ctx in enumerate(contexts):
                        st.markdown(f"**Context {i+1}:** {ctx['content']} *(Score: {ctx.get('relevance_score', 0)})*")
            
            # Generate the response using our mock RAG generation
            full_response = rag_engine.mock_llm_generation(prompt)
            
        # Simulate "typing" the response chunk by chunk
        typed_response = ""
        for chunk in full_response.split():
            typed_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(typed_response + "▌")
            
        message_placeholder.markdown(full_response)
        
    # 3. Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
