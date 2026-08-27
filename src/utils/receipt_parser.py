import re
from datetime import datetime
from typing import Any


def mock_ocr_extraction(file_name: str) -> str:
    """
    Simulates OCR text extraction from an uploaded file.
    In production, this would be replaced by a call to ocr_utils.extract_text_from_file().
    """
    if "electric" in file_name.lower() or "bill" in file_name.lower():
        return """
        CITY POWER & LIGHT
        Account: 123456789
        Date: 2023-10-15
        Billing Period: Sep 1 - Sep 30
        Total Amount Due: $145.50
        Energy Used: 850 kWh
        Thank you for your business.
        """
    elif "grocery" in file_name.lower() or "receipt" in file_name.lower():
        return """
        FRESH MARKET GROCERY
        Date: 2023-10-20
        Items:
        - Organic Vegetables $15.00
        - Local Beef $25.00
        - Imported Coffee $12.00
        Total: $52.00
        """
    else:
        return """
        UNKNOWN VENDOR
        Date: 2023-10-25
        Total: $30.00
        """


def parse_receipt_text(ocr_text: str) -> dict[str, Any]:
    """
    Processes raw OCR text and extracts structured data points.
    """
    
    data = {
        "vendor": "Unknown Vendor",
        "date": None,
        "total_cost": 0.0,
        "energy_kwh": None,
        "raw_text": ocr_text.strip(),
    }

    # Extract Vendor (simple heuristic: first all-caps line or specific keywords)
    vendor_match = re.search(r"^([A-Z\s&]+)", ocr_text, re.MULTILINE)
    if vendor_match:
        data["vendor"] = vendor_match.group(1).strip()

    # Extract Date (YYYY-MM-DD or similar)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ocr_text)
    if date_match:
        data["date"] = date_match.group(1)
    else:
        data["date"] = datetime.now().strftime("%Y-%m-%d")

    # Extract Total Cost
    total_match = re.search(
        r"(?:Total|Amount Due)[:\s]*\$?(\d+\.\d{2})", ocr_text, re.IGNORECASE
    )
    if total_match:
        data["total_cost"] = float(total_match.group(1))

    # Extract Energy Usage (kWh)
    kwh_match = re.search(r"(\d+(?:\.\d+)?)\s*kWh", ocr_text, re.IGNORECASE)
    if kwh_match:
        data["energy_kwh"] = float(kwh_match.group(1))

    return data
