"""Lightweight session state management utilities for EcoBuddy AI."""

from typing import Any, Mapping
import streamlit as st


def ensure_session_state(defaults: Mapping[str, Any]) -> None:
    """Initialize missing key-value pairs in st.session_state from a defaults dictionary."""
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_session_state_if_changed(key: str, value: Any) -> bool:
    """Set a session state key only if its value actually changed, avoiding redundant reruns."""
    if key not in st.session_state or st.session_state[key] != value:
        st.session_state[key] = value
        return True
    return False
