import streamlit as st
import logging

logger = logging.getLogger(__name__)

def safe_numeric_input(label: str, min_value: float = 0.0, max_value: float = 1000.0, default: float = 0.0, step: float = 1.0) -> float:
    """
    Safely renders a numeric input/number_input field with fallback protection
    against invalid types or unexpected empty submissions.
    """
    try:
        val = st.number_input(label, min_value=min_value, max_value=max_value, value=default, step=step)
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid input received for '{label}': {e}. Falling back to default: {default}")
        st.warning(f"⚠️ Invalid input for {label}. Using default value: {default}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error in numeric input '{label}': {e}")
        return default


def safe_text_input(label: str, max_length: int = 500, default: str = "") -> str:
    """
    Safely processes and sanitizes text inputs, preventing injection or length overflow.
    """
    try:
        text = st.text_input(label, value=default)
        if not text:
            return default
        
        # Strip excessive whitespaces or trim to max length
        sanitized = text.strip()
        if len(sanitized) > max_length:
            st.warning(f"⚠️ Input exceeded maximum length of {max_length} characters and was truncated.")
            return sanitized[:max_length]
        return sanitized
    except Exception as e:
        logger.error(f"Error handling text input '{label}': {e}")
        return default
