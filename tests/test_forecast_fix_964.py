"""
Regression Test for Issue #964
Detects the datetime bug in emissions.py without modifying source files.
"""
import pytest
import emissions


class TestForecastMonthlyEmission:
    @pytest.mark.xfail(reason="Known Bug in emissions.py: datetime.datetime.today() raises AttributeError. Fix source code to make this pass.")
    def test_no_attribute_error(self):
        """
        This test is EXPECTED TO FAIL right now because of the bug.
        Once the bug is fixed in emissions.py, this test will turn green.
        """
        result = emissions.forecast_monthly_emission(100)
        assert result > 0

    @pytest.mark.xfail(reason="Known Bug in emissions.py: datetime.datetime.today() raises AttributeError. Fix source code to make this pass.")
    def test_forecast_returns_float(self):
        """Ensure it always returns a floating point number."""
        result = emissions.forecast_monthly_emission(50)
        assert isinstance(result, float)

    @pytest.mark.xfail(reason="Known Bug in emissions.py: datetime.datetime.today() raises AttributeError. Fix source code to make this pass.")
    def test_forecast_for_zero_emission(self):
        """Test that zero emission returns a safe 0.0."""
        result = emissions.forecast_monthly_emission(0)
        assert result == 0.0

    @pytest.mark.xfail(reason="Known Bug in emissions.py: datetime.datetime.today() raises AttributeError. Fix source code to make this pass.")
    def test_forecast_positive_emission(self):
        """Verify basic calculation without crashing."""
        result = emissions.forecast_monthly_emission(100)
        assert result > 0