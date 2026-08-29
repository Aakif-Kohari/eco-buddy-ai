"""
Form helper utilities for EcoBuddy AI.
Provides flash message helpers and form rendering utilities.
"""

import streamlit as st
from typing import Dict, List, Optional, Any


def display_form_errors(errors: Dict[str, List[str]]) -> None:
    """
    Display form validation errors in Streamlit.
    
    Args:
        errors: Dictionary of field names to list of error messages
    """
    if not errors:
        return
    
    error_messages = []
    for field, field_errors in src.core.errors.items():
        for error in field_errors:
            error_messages.append(f"❌ **{field.replace('_', ' ').title()}**: {error}")
    
    if error_messages:
        st.error("\n".join(error_messages))


def display_field_error(field_name: str, errors: Dict[str, List[str]]) -> Optional[str]:
    """
    Get error message for a specific field.
    
    Args:
        field_name: Name of the field
        errors: Dictionary of field names to list of error messages
    
    Returns:
        Error message if exists, else None
    """
    if field_name in errors and errors[field_name]:
        return errors[field_name][0]
    return None


def get_field_value(field_name: str, data: Dict[str, Any], default: Any = "") -> Any:
    """
    Get field value from data dictionary.
    
    Args:
        field_name: Name of the field
        data: Dictionary containing form data
        default: Default value if field not found
    
    Returns:
        Field value or default
    """
    return data.get(field_name, default)


def render_form_field(
    label: str,
    field_name: str,
    value: Any = "",
    errors: Dict[str, List[str]] = None,
    type: str = "text",
    placeholder: str = "",
    help_text: str = "",
    **kwargs
) -> Any:
    """
    Render a form field with error handling.
    
    Args:
        label: Field label
        field_name: Name of the field
        value: Current value
        errors: Dictionary of field errors
        type: Input type ('text', 'number', 'date', 'textarea')
        placeholder: Placeholder text
        help_text: Help text
        **kwargs: Additional arguments passed to Streamlit widget
    
    Returns:
        The value entered by the user
    """
    errors = errors or {}
    error = display_field_error(field_name, errors)
    
    # Display field with error styling
    if error:
        st.markdown(f"<span style='color: red;'>⚠️ {error}</span>", unsafe_allow_html=True)
    
    # Render appropriate widget
    if type == "textarea":
        return st.text_area(label, value=value, placeholder=placeholder, help=help_text, **kwargs)
    elif type == "number":
        return st.number_input(label, value=float(value) if value else 0.0, **kwargs)
    elif type == "date":
        return st.date_input(label, value=value if value else None, help=help_text, **kwargs)
    else:
        return st.text_input(label, value=value, placeholder=placeholder, help=help_text, **kwargs)


def sanitize_form_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize form data by stripping whitespace from string values.
    
    Args:
        data: Dictionary containing form data
    
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = value.strip()
        elif isinstance(value, list):
            sanitized[key] = [v.strip() if isinstance(v, str) else v for v in value]
        else:
            sanitized[key] = value
    return sanitized


def render_success_message(message: str) -> None:
    """
    Render a success message with green styling.
    
    Args:
        message: Success message to display
    """
    st.success(f"✅ {message}")


def render_error_message(message: str) -> None:
    """
    Render an error message with red styling.
    
    Args:
        message: Error message to display
    """
    st.error(f"❌ {message}")


def render_info_message(message: str) -> None:
    """
    Render an info message with blue styling.
    
    Args:
        message: Info message to display
    """
    st.info(f"ℹ️ {message}")


def render_warning_message(message: str) -> None:
    """
    Render a warning message with yellow styling.
    
    Args:
        message: Warning message to display
    """
    st.warning(f"⚠️ {message}")