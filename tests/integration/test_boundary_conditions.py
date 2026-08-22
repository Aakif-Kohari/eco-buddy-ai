import pytest
from typing import List, Union

# --- Simulated Domain Validators ---
class ValidationEngine:
    """Core domain validation rules for EcoBuddy tracking profiles."""
    
    @staticmethod
    def validate_carbon_metric(value: float) -> float:
        # Boundaries: Must be between 0.00 and 100,000.00 kg CO2
        if not isinstance(value, (int, float)):
            raise TypeError("Metric must be a numeric value.")
        if value < 0.0:
            raise ValueError("Carbon emissions cannot be negative.")
        if value > 100000.0:
            raise ValueError("Value exceeds maximum supported single log threshold.")
        return float(value)

    @staticmethod
    def validate_tags(tags: List[str]) -> List[str]:
        if not isinstance(tags, list):
            raise TypeError("Tags must be structured inside a collection list.")
        if len(tags) > 1000:
            raise ValueError("Collection exceeds maximum safe processing size.")
        for tag in tags:
            if len(tag) > 255:
                raise ValueError("Individual tag string length exceeds limits.")
        return tags

# --- Boundary Testing Suite ---

# 1 & 4. Minimum Valid & Zero Boundaries
@pytest.mark.parametrize("min_val", [0.0, 0.01])
def test_minimum_and_zero_valid_boundaries(min_val):
    """Scenarios: Zero and absolute absolute minimum positive values."""
    assert ValidationEngine.validate_carbon_metric(min_val) == float(min_val)


# 2. Maximum Valid Boundaries
def test_maximum_valid_boundaries():
    """Scenario: Absolute maximum valid threshold."""
    assert ValidationEngine.validate_carbon_metric(100000.0) == 100000.0


# 3 & 5. Values Outside Accepted Boundaries & Negative Values
@pytest.mark.parametrize("invalid_val, expected_msg", [
    (-0.01, "Carbon emissions cannot be negative."),
    (-1500.0, "Carbon emissions cannot be negative."),
    (100000.01, "Value exceeds maximum supported single log threshold."),
    (500000.0, "Value exceeds maximum supported single log threshold.")
])
def test_outside_numerical_boundaries(invalid_val, expected_msg):
    """Scenarios: Immediate out-of-bounds bounds testing and negative metrics."""
    with pytest.raises(ValueError, match=expected_msg):
        ValidationEngine.validate_carbon_metric(invalid_val)


# 6. Empty Collections
def test_empty_collections():
    """Scenario: Empty tracking tag structures configuration."""
    assert ValidationEngine.validate_tags([]) == []


# 7. Extremely Large Collections
def test_extremely_large_collections():
    """Scenario: Overly inflated collections payload stress test."""
    oversized_list = ["eco"] * 1001
    with pytest.raises(ValueError, match="Collection exceeds maximum safe processing size."):
        ValidationEngine.validate_tags(oversized_list)


# 8 & 9. Long Strings & Unicode Input
@pytest.mark.parametrize("string_input, should_pass", [
    ("A" * 255, True),
    ("A" * 256, False),
    ("🌿_éçô_Б_🎯_" * 20, True),  # Multi-byte characters boundary check
])
def test_string_lengths_and_unicode_compliance(string_input, should_pass):
    """Scenarios: Excessive buffer length validation and global Unicode character processing."""
    if should_pass:
        assert ValidationEngine.validate_tags([string_input]) == [string_input]
    else:
        with pytest.raises(ValueError, match="Individual tag string length exceeds limits."):
            ValidationEngine.validate_tags([string_input])


# 10. Repeated Values
def test_repeated_values_in_collections():
    """Scenario: Processing non-unique duplicate tags safely."""
    repeated_tags = ["transport", "transport", "transport"]
    assert ValidationEngine.validate_tags(repeated_tags) == repeated_tags
