"""Tests for the ML Categorizer."""

import pytest
from src.data.data_import_ml_categorizer import TextCategorizer, categorize_missing_fields

class TestMLCategorizer:
    
    def test_tokenize(self):
        cat = TextCategorizer()
        tokens = cat._tokenize("I took an Uber ride!!")
        assert tokens == ["took", "uber", "ride"]
        
    def test_predict_category_energy(self):
        cat = TextCategorizer()
        predicted, conf = cat.predict_category("Paid my monthly electricity and gas bill")
        assert predicted == "Energy"
        assert conf > 0
        
    def test_predict_category_transport(self):
        cat = TextCategorizer()
        predicted, conf = cat.predict_category("Flight from NY to LA on American Airlines")
        assert predicted == "Transport"
        
    def test_predict_category_food(self):
        cat = TextCategorizer()
        predicted, conf = cat.predict_category("Bought some vegan groceries at whole foods")
        assert predicted == "Food"
        
    def test_predict_category_unknown(self):
        cat = TextCategorizer()
        predicted, conf = cat.predict_category("Just doing random stuff xyz")
        assert predicted == "Other"
        
    def test_categorize_missing_fields(self):
        records = [
            {"activity": "Uber trip to airport", "category": None},
            {"activity": "Electricity bill", "category": "Other"},
            {"activity": "Lunch at restaurant", "category": ""},
            {"activity": "Trash disposal", "category": "Waste"}, # Already valid
            {"activity": "Random thing", "category": None}
        ]
        
        updated, stats = categorize_missing_fields(records)
        
        assert stats["auto_categorized"] == 3
        
        assert updated[0]["category"] == "Transport"
        assert updated[1]["category"] == "Energy"
        assert updated[2]["category"] == "Food"
        assert updated[3]["category"] == "Waste" # Unchanged
        assert updated[4]["category"] == "Other" # Fallback
