"""
Theme Manager for EcoBuddy AI
Handles dark/light theme toggle with persistence.
"""

import streamlit as st
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ThemeManager:
    """
    Manages dark/light theme with persistence in session state and localStorage.
    """
    
    THEMES = {
        "light": {
            "name": "Light",
            "icon": "☀️",
            "background": "#f8fafc",
            "surface": "#ffffff",
            "text": "#1a1a2e",
            "text_secondary": "#64748b",
            "border": "#e2e8f0",
            "shadow": "rgba(0,0,0,0.1)",
            "card_bg": "rgba(255,255,255,0.9)",
            "accent": "#22c55e",
            "accent_hover": "#16a34a",
            "input_bg": "#ffffff",
            "input_border": "#d1d5db",
            "sidebar_bg": "rgba(255,255,255,0.92)",
            "footer_bg": "#f8fafc"
        },
        "dark": {
            "name": "Dark",
            "icon": "🌙",
            "background": "#0f172a",
            "surface": "#1e293b",
            "text": "#f1f5f9",
            "text_secondary": "#94a3b8",
            "border": "#334155",
            "shadow": "rgba(0,0,0,0.4)",
            "card_bg": "rgba(30,41,59,0.9)",
            "accent": "#4ade80",
            "accent_hover": "#22c55e",
            "input_bg": "#1e293b",
            "input_border": "#475569",
            "sidebar_bg": "rgba(15,23,42,0.95)",
            "footer_bg": "#0f172a"
        }
    }
    
    def __init__(self):
        self._current_theme = self._load_theme()
    
    def _load_theme(self) -> str:
        """Load theme from session state or localStorage."""
        # Check session state first
        if "theme" in st.session_state:
            theme = st.session_state.theme
            if theme in self.THEMES:
                return theme
        
        # Try to load from localStorage via JavaScript
        try:
            import streamlit.components.v1 as components
            # Note: This is a fallback, actual loading is done via JavaScript
        except:
            pass
        
        return "light"
    
    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme
    
    def get_theme_colors(self, theme: Optional[str] = None) -> Dict[str, str]:
        """Get color palette for a theme."""
        if theme is None:
            theme = self._current_theme
        return self.THEMES.get(theme, self.THEMES["light"])
    
    def toggle_theme(self) -> str:
        """Toggle between dark and light themes."""
        current = self._current_theme
        new_theme = "dark" if current == "light" else "light"
        self.set_theme(new_theme)
        return new_theme
    
    def set_theme(self, theme: str) -> None:
        """Set the current theme."""
        if theme in self.THEMES:
            self._current_theme = theme
            st.session_state.theme = theme
            self._apply_theme(theme)
    
    def _apply_theme(self, theme: str) -> None:
        """Apply theme to the app."""
        colors = self.THEMES[theme]
        
        # CSS for theme
        css = f"""
        <style>
        /* Theme variables */
        :root {{
            --bg-primary: {colors["background"]};
            --bg-surface: {colors["surface"]};
            --text-primary: {colors["text"]};
            --text-secondary: {colors["text_secondary"]};
            --border-color: {colors["border"]};
            --shadow-color: {colors["shadow"]};
            --card-bg: {colors["card_bg"]};
            --accent-color: {colors["accent"]};
            --accent-hover: {colors["accent_hover"]};
            --input-bg: {colors["input_bg"]};
            --input-border: {colors["input_border"]};
            --sidebar-bg: {colors["sidebar_bg"]};
            --footer-bg: {colors["footer_bg"]};
        }}
        
        /* Apply theme */
        body, .stApp {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
        }}
        
        .stSidebar {{
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
        }}
        
        .stTextInput > div > div > input,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"],
        .stTextArea textarea {{
            background-color: var(--input-bg) !important;
            border-color: var(--input-border) !important;
            color: var(--text-primary) !important;
        }}
        
        .stButton > button {{
            background-color: var(--accent-color) !important;
            color: var(--text-primary) !important;
        }}
        
        .stButton > button:hover {{
            background-color: var(--accent-hover) !important;
        }}
        
        .stExpander {{
            background-color: var(--bg-surface) !important;
            border-color: var(--border-color) !important;
        }}
        
        .stDataFrame {{
            background-color: var(--bg-surface) !important;
        }}
        
        .metric-card {{
            background-color: var(--card-bg) !important;
            border-color: var(--border-color) !important;
        }}
        
        .footer {{
            background-color: var(--footer-bg) !important;
        }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)
        
        # JavaScript to persist theme
        js = f"""
        <script>
        // Save theme to localStorage
        localStorage.setItem('ecobuddy_theme', '{theme}');
        
        // Apply theme class to body
        document.body.className = '{theme}-theme';
        document.documentElement.setAttribute('data-theme', '{theme}');
        </script>
        """
        st.markdown(js, unsafe_allow_html=True)
    
    def render_theme_toggle(self) -> None:
        """Render the theme toggle button."""
        current = self.get_current_theme()
        next_theme = "dark" if current == "light" else "light"
        icon = self.THEMES[next_theme]["icon"]
        label = self.THEMES[next_theme]["name"]
        
        if st.button(
            f"{icon} {label}",
            key="theme_toggle_btn",
            help=f"Switch to {label} mode",
            use_container_width=True
        ):
            self.toggle_theme()
            st.rerun()
    
    def render_theme_selector(self) -> None:
        """Render theme selector with both options."""
        current = self.get_current_theme()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if current == "light":
                st.success("☀️ Light")
            else:
                if st.button("☀️ Light", key="theme_light", use_container_width=True):
                    self.set_theme("light")
                    st.rerun()
        
        with col2:
            if current == "dark":
                st.success("🌙 Dark")
            else:
                if st.button("🌙 Dark", key="theme_dark", use_container_width=True):
                    self.set_theme("dark")
                    st.rerun()


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def apply_theme(theme: Optional[str] = None) -> None:
    """Apply theme to the app."""
    manager = get_theme_manager()
    if theme:
        manager.set_theme(theme)
    else:
        manager._apply_theme(manager.get_current_theme())


def get_theme_colors() -> Dict[str, str]:
    """Get current theme colors."""
    manager = get_theme_manager()
    return manager.get_theme_colors()


def toggle_theme() -> str:
    """Toggle theme and return new theme name."""
    manager = get_theme_manager()
    return manager.toggle_theme()


def render_theme_toggle() -> None:
    """Render the theme toggle button."""
    manager = get_theme_manager()
    manager.render_theme_toggle()


def render_theme_selector() -> None:
    """Render theme selector with both options."""
    manager = get_theme_manager()
    manager.render_theme_selector()