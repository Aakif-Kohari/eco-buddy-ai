from bill_categorizer import categorize_bill, get_available_categories
from receipt_parser import mock_ocr_extraction, parse_receipt_text


def test_mock_ocr_extraction_electric():
    text = mock_ocr_extraction("electric_bill.pdf")
    assert "CITY POWER & LIGHT" in text
    assert "850 kWh" in text


def test_parse_receipt_text_electric():
    raw_text = """
    CITY POWER & LIGHT
    Date: 2023-10-15
    Total Amount Due: $145.50
    Energy Used: 850 kWh
    """
    parsed = parse_receipt_text(raw_text)
    assert parsed["vendor"] == "CITY POWER & LIGHT"
    assert parsed["date"] == "2023-10-15"
    assert parsed["total_cost"] == 145.50
    assert parsed["energy_kwh"] == 850.0


def test_parse_receipt_text_grocery():
    raw_text = """
    FRESH MARKET GROCERY
    Date: 2023-10-20
    Total: $52.00
    """
    parsed = parse_receipt_text(raw_text)
    assert parsed["vendor"] == "FRESH MARKET GROCERY"
    assert parsed["total_cost"] == 52.00
    assert parsed["energy_kwh"] is None


def test_categorize_bill_electric():
    parsed = {
        "vendor": "City Power",
        "raw_text": "Your monthly electric bill. Usage: 500 kWh.",
        "total_cost": 100.0,
        "energy_kwh": 500.0,
    }
    categorized = categorize_bill(parsed)
    assert categorized["primary_category"] == "electricity"
    assert "electricity" in categorized["detected_categories"]


def test_categorize_bill_grocery():
    parsed = {
        "vendor": "Fresh Market",
        "raw_text": "Grocery receipt for food items.",
        "total_cost": 50.0,
        "energy_kwh": None,
    }
    categorized = categorize_bill(parsed)
    assert categorized["primary_category"] == "diet"


def test_get_available_categories():
    cats = get_available_categories()
    assert "electricity" in cats
    assert "general" in cats
