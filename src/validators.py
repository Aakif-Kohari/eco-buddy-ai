"""
Input validation utilities for EcoBuddy AI forms.
Provides validation functions for assessment, profile, and quiz forms.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Custom exception for validation src.core.errors."""
    pass


def validate_required(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a field is not empty.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error message
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required."
    if isinstance(value, str) and not value.strip():
        return False, f"{field_name} is required."
    if isinstance(value, list) and len(value) == 0:
        return False, f"{field_name} is required."
    return True, None


def validate_length(value: str, field_name: str, min_length: int = 1, max_length: int = 500) -> Tuple[bool, Optional[str]]:
    """
    Validate string length is within range.
    
    Args:
        value: The string to validate
        field_name: Name of the field for error message
        min_length: Minimum allowed length
        max_length: Maximum allowed length
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return True, None
    
    length = len(value.strip())
    if length < min_length:
        return False, f"{field_name} must be at least {min_length} characters."
    if length > max_length:
        return False, f"{field_name} cannot exceed {max_length} characters."
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, None
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Please enter a valid email address."
    return True, None


def validate_number(value: Any, field_name: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is a number within range.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error message
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a valid number."
    
    if min_value is not None and num < min_value:
        return False, f"{field_name} must be at least {min_value}."
    if max_value is not None and num > max_value:
        return False, f"{field_name} cannot exceed {max_value}."
    
    return True, None


def validate_date(date_str: str, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate date format.
    
    Args:
        date_str: Date string to validate
        field_name: Name of the field for error message
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return True, None
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, f"{field_name} must be in YYYY-MM-DD format."


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, None
    
    phone_pattern = r'^\+?[0-9\s\-]{10,15}$'
    if not re.match(phone_pattern, phone.strip()):
        return False, "Please enter a valid phone number (10-15 digits)."
    return True, None


def validate_eco_score(score: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate eco-score is between 0 and 100.
    
    Args:
        score: Score to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_number(score, "Eco score", min_value=0, max_value=100)


def validate_carbon_footprint(value: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate carbon footprint value.
    
    Args:
        value: Carbon footprint value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_number(value, "Carbon footprint", min_value=0)


def validate_energy_usage(value: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate energy usage value.
    
    Args:
        value: Energy usage value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_number(value, "Energy usage", min_value=0)


def validate_waste_generated(value: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate waste generated value.
    
    Args:
        value: Waste generated value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_number(value, "Waste generated", min_value=0)


# ============================================================================
# FORM VALIDATION FUNCTIONS
# ============================================================================

def validate_assessment_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate assessment form data.
    
    Args:
        data: Dictionary containing assessment data
    
    Returns:
        Dictionary of field names to list of error messages
    """
    errors = {}
    validators = {
        "user_id": (data.get("user_id"), lambda v: validate_required(v, "User ID")),
        "carbon_footprint": (data.get("carbon_footprint"), validate_carbon_footprint),
        "energy_used": (data.get("energy_used"), validate_energy_usage),
        "waste_generated": (data.get("waste_generated"), validate_waste_generated),
        "eco_score": (data.get("eco_score"), validate_eco_score),
        "date": (data.get("date"), lambda v: validate_date(v, "Date")),
        "notes": (data.get("notes", ""), lambda v: validate_length(v, "Notes", max_length=1000)),
    }
    
    for field_name, (value, validator) in src.validators.items():
        is_valid, error = validator(value)
        if not is_valid and error:
            src.core.errors.setdefault(field_name, []).append(error)
    
    return errors


def validate_profile_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate user profile form data.
    
    Args:
        data: Dictionary containing profile data
    
    Returns:
        Dictionary of field names to list of error messages
    """
    errors = {}
    validators = {
        "username": (data.get("username"), lambda v: validate_length(v, "Username", min_length=3, max_length=50)),
        "email": (data.get("email"), validate_email),
        "phone": (data.get("phone"), validate_phone),
        "full_name": (data.get("full_name"), lambda v: validate_length(v, "Full name", min_length=2, max_length=100)),
        "bio": (data.get("bio", ""), lambda v: validate_length(v, "Bio", max_length=500)),
    }
    
    for field_name, (value, validator) in src.validators.items():
        if value is None:
            continue
        is_valid, error = validator(value)
        if not is_valid and error:
            src.core.errors.setdefault(field_name, []).append(error)
    
    return errors


def validate_quiz_answer(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate quiz answer submission.
    
    Args:
        data: Dictionary containing quiz answer data
    
    Returns:
        Dictionary of field names to list of error messages
    """
    errors = {}
    
    # Validate quiz_id
    quiz_id = data.get("quiz_id")
    is_valid, error = validate_required(quiz_id, "Quiz ID")
    if not is_valid and error:
        src.core.errors.setdefault("quiz_id", []).append(error)
    
    # Validate answers
    answers = data.get("answers", {})
    if not answers or not isinstance(answers, dict):
        src.core.errors.setdefault("answers", []).append("Answers are required.")
    elif len(answers) == 0:
        src.core.errors.setdefault("answers", []).append("Please answer all questions.")
    
    return errors


def validate_recommendation_feedback(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate recommendation feedback form data.
    
    Args:
        data: Dictionary containing feedback data
    
    Returns:
        Dictionary of field names to list of error messages
    """
    errors = {}
    
    validators = {
        "recommendation_id": (data.get("recommendation_id"), lambda v: validate_required(v, "Recommendation ID")),
        "feedback": (data.get("feedback"), lambda v: validate_length(v, "Feedback", min_length=5, max_length=500)),
        "rating": (data.get("rating"), lambda v: validate_number(v, "Rating", min_value=1, max_value=5)),
        "useful": (data.get("useful"), lambda v: validate_required(v, "Usefulness")),
    }
    
    for field_name, (value, validator) in src.validators.items():
        is_valid, error = validator(value)
        if not is_valid and error:
            src.core.errors.setdefault(field_name, []).append(error)
    
    return errors


def validate_widget_preferences(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate dashboard widget preferences.
    
    Args:
        data: Dictionary containing widget preferences
    
    Returns:
        Dictionary of field names to list of error messages
    """
    errors = {}
    
    widgets = data.get("widgets", [])
    if not widgets or not isinstance(widgets, list):
        src.core.errors.setdefault("widgets", []).append("Widget selection is required.")
    elif len(widgets) == 0:
        src.core.errors.setdefault("widgets", []).append("Please select at least one widget.")
    
    return errors


# ============================================================================
# FORM VALIDATION WRAPPER
# ============================================================================

def validate_form(data: Dict[str, Any], form_type: str) -> Dict[str, List[str]]:
    """
    Validate form data based on form type.
    
    Args:
        data: Dictionary containing form data
        form_type: Type of form ('assessment', 'profile', 'quiz', 'feedback', 'widgets')
    
    Returns:
        Dictionary of field names to list of error messages
    """
    validators = {
        "assessment": validate_assessment_data,
        "profile": validate_profile_data,
        "quiz": validate_quiz_answer,
        "feedback": validate_recommendation_feedback,
        "widgets": validate_widget_preferences,
    }
    
    validator = src.validators.get(form_type)
    if not validator:
        return {"form": [f"Unknown form type: {form_type}"]}
    
    return validator(data)


def is_valid_form(data: Dict[str, Any], form_type: str) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Check if form data is valid.
    
    Args:
        data: Dictionary containing form data
        form_type: Type of form
    
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = validate_form(data, form_type)
    return len(errors) == 0, errors