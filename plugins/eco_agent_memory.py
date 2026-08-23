import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EcoAgentMemory:
    """
    Manages long-term conversational memory for the AI Agent.
    Implements sliding window token limits and persistent history logging to SQLite.
    """

    def __init__(self, db_path: str = "eco_chat_history.db", max_history_tokens: int = 4000):
        self.db_path = db_path
        self.max_history_tokens = max_history_tokens
        # Very rough approximation: 1 token ~= 4 characters
        self.max_chars = max_history_tokens * 4 
        self._init_db()

    def _init_db(self):
        """Initializes the database schema for chat logs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        session_id TEXT,
                        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize Chat Memory DB: {e}")

    def append_message(self, session_id: str, role: str, content: str):
        """Adds a message to the persistent history."""
        if role not in ["user", "assistant", "system", "tool"]:
            raise ValueError(f"Invalid role: {role}")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)',
                    (session_id, role, content)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to save message: {e}")

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict[str, str]]:
        """Retrieves raw chat history for a given session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Get the most recent X messages, ordered properly
                cursor.execute('''
                    SELECT role, content FROM (
                        SELECT role, content, message_id 
                        FROM conversations 
                        WHERE session_id = ? 
                        ORDER BY message_id DESC 
                        LIMIT ?
                    ) ORDER BY message_id ASC
                ''', (session_id, limit))
                
                rows = cursor.fetchall()
                return [{"role": row[0], "content": row[1]} for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch history: {e}")
            return []

    def get_context_window(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieves chat history and applies a sliding window to ensure it doesn't 
        exceed the LLM's maximum token context limit. Drops oldest messages first.
        """
        raw_history = self.get_history(session_id, limit=100) # Fetch a large chunk
        if not raw_history:
            return []
            
        context = []
        current_chars = 0
        
        # Iterate backwards (newest to oldest) to ensure we keep the most recent context
        for msg in reversed(raw_history):
            msg_len = len(msg["content"])
            
            # If adding this message exceeds the limit, stop including older messages
            if current_chars + msg_len > self.max_chars:
                break
                
            context.insert(0, msg) # Prepend so chronological order is maintained
            current_chars += msg_len
            
        # Ensure the conversation doesn't start with an assistant message abruptly
        # unless it's the only thing left. OpenAI APIs prefer User -> Assistant alternating.
        if context and context[0]["role"] == "assistant" and len(context) > 1:
            context.pop(0)
            
        return context

    def clear_session(self, session_id: str):
        """Deletes all messages for a specific session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to clear session: {e}")

    def format_for_prompt(self, session_id: str) -> str:
        """
        Formats the context window into a single string for legacy LLMs that don't 
        support structured JSON message arrays.
        """
        messages = self.get_context_window(session_id)
        formatted = ""
        for msg in messages:
            role = "Human" if msg["role"] == "user" else "AI"
            formatted += f"{role}: {msg['content']}\n\n"
        return formatted.strip()
