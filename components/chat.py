"""
EcoBuddy AI Chat Component
Handles chat interface with error handling.
"""

import streamlit as st
from src.lib.api_error_handler import safe_api_call, get_error_handler


def render_chat_ui():
    """Render the chat interface with responsive styling."""
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Chat header
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-info">
            <div class="bot-avatar">🌱</div>
            <div>
                <h3>EcoBuddy Chat</h3>
                <span class="online-status">Online • Ask about sustainability</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat messages area
    st.markdown('<div class="chat-messages" id="chat-messages">', unsafe_allow_html=True)
    
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat history
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="message user-message">
                <div class="message-avatar">👤</div>
                <div class="message-bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message bot-message">
                <div class="message-avatar">🌱</div>
                <div class="message-bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input area
    st.markdown("""
    <div class="chat-input-area">
        <input type="text" id="chat-input" placeholder="Type your question..." style="flex:1; padding:10px; border-radius:10px; border:1px solid rgba(74,222,128,0.15); background:rgba(255,255,255,0.05); color:#f8fafc;">
        <button class="btn-send" id="btn-send" style="padding:10px 16px; border-radius:10px; background:linear-gradient(135deg,#22c55e,#16a34a); color:white; border:none; cursor:pointer;">➤</button>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle user input
    user_input = st.chat_input("Ask about sustainability...")
    
    if user_input:
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        
        # Get AI response with error handling
        def _call_ai_api():
            # Replace with your actual AI API call
            # For demo, simulate response
            if "error" in user_input.lower():
                raise Exception("API service unavailable")
            return {"response": f"🌱 Here's an eco-tip about: {user_input}"}
        
        result, error = safe_api_call(
            _call_ai_api,
            error_message="Failed to get AI response"
        )
        
        if error:
            bot_response = f"❌ {error.to_user_message()}"
        else:
            bot_response = result.get("response", "Sorry, I couldn't process that.")
        
        # Add bot response
        st.session_state.chat_messages.append({"role": "bot", "content": bot_response})
        st.rerun()