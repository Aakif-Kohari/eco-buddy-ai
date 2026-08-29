"""Machine Learning Categorizer for Eco Activities.

Provides a heuristic Natural Language Processing (NLP) pipeline to categorize
unstructured activity descriptions into standard EcoBuddy categories
(Energy, Transport, Waste, Water, Food, Shopping) when the category column
is missing from the imported dataset.

Uses a lightweight Bag-of-Words (BoW) approach with TF-IDF approximation
for zero-dependency fast execution.
"""

import math
import logging
import re
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# Corpus of keywords per category, weighted by importance
CATEGORY_CORPUS = {
    "Energy": {
        "electricity": 3.0, "power": 2.5, "gas": 2.5, "heating": 2.0, "cooling": 2.0,
        "kwh": 3.0, "utility": 2.0, "bill": 1.0, "grid": 2.0, "solar": 3.0,
        "generator": 2.0, "hvac": 2.5, "ac": 1.5, "furnace": 2.5, "thermostat": 2.0
    },
    "Transport": {
        "flight": 3.0, "car": 2.0, "drive": 2.0, "driving": 2.0, "uber": 2.5,
        "lyft": 2.5, "taxi": 2.0, "bus": 2.0, "train": 2.0, "subway": 2.0,
        "commute": 2.5, "gasoline": 2.5, "diesel": 2.5, "mileage": 2.0, "miles": 1.5,
        "km": 1.0, "vehicle": 2.0, "transit": 2.5, "travel": 1.5, "airplane": 3.0
    },
    "Waste": {
        "trash": 3.0, "garbage": 3.0, "recycle": 3.0, "recycling": 3.0, "compost": 3.0,
        "landfill": 3.0, "waste": 2.5, "dump": 2.0, "disposal": 2.5, "bin": 1.5,
        "plastic": 2.0, "paper": 1.5, "cardboard": 1.5, "glass": 1.5, "scrap": 1.5
    },
    "Water": {
        "water": 3.0, "shower": 2.5, "bath": 2.0, "sink": 1.5, "hose": 2.0,
        "sprinkler": 2.5, "irrigation": 3.0, "plumbing": 2.0, "leak": 2.0, "gallon": 1.5,
        "liter": 1.5, "washing": 1.5, "laundry": 2.0, "dishwasher": 2.0, "pool": 2.5
    },
    "Food": {
        "meal": 2.5, "food": 2.5, "grocery": 2.5, "groceries": 2.5, "restaurant": 2.0,
        "dining": 2.0, "meat": 3.0, "beef": 3.0, "chicken": 2.0, "pork": 2.5,
        "fish": 2.0, "vegan": 3.0, "vegetarian": 3.0, "dairy": 2.5, "milk": 2.0,
        "cheese": 2.0, "vegetable": 2.0, "fruit": 2.0, "diet": 2.0, "snack": 1.5
    },
    "Shopping": {
        "buy": 1.5, "bought": 1.5, "purchase": 2.0, "clothes": 2.5, "clothing": 2.5,
        "shoes": 2.0, "electronics": 3.0, "laptop": 2.5, "phone": 2.5, "tv": 2.0,
        "appliance": 2.0, "furniture": 2.0, "amazon": 2.0, "store": 1.5, "mall": 1.5
    }
}

class TextCategorizer:
    
    def __init__(self):
        # Build document frequency (DF) for IDF calculation
        self.doc_freq: Dict[str, int] = {}
        self.total_docs = len(CATEGORY_CORPUS)
        
        for cat, words in CATEGORY_CORPUS.items():
            for word in words:
                self.doc_freq[word] = self.doc_freq.get(word, 0) + 1
                
        # Calculate IDF (Inverse Document Frequency)
        self.idf: Dict[str, float] = {}
        for word, count in self.doc_freq.items():
            self.idf[word] = math.log(self.total_docs / (1 + count)) + 1.0
            
    def _tokenize(self, text: str) -> List[str]:
        """Convert text to lowercase alphanumeric tokens."""
        if not text or not isinstance(text, str):
            return []
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return [w for w in text.split() if len(w) > 2]
        
    def predict_category(self, description: str) -> Tuple[str, float]:
        """Predict the category of an activity description.
        
        Returns:
            (Best Category, Confidence Score)
        """
        tokens = self._tokenize(description)
        if not tokens:
            return "Other", 0.0
            
        scores = {cat: 0.0 for cat in CATEGORY_CORPUS.keys()}
        
        for token in tokens:
            for cat, keywords in CATEGORY_CORPUS.items():
                if token in keywords:
                    # Score = Base Weight * IDF
                    tf_idf = keywords[token] * self.idf.get(token, 1.0)
                    scores[cat] += tf_idf
                    
                # Sub-token matching (e.g., "uber_ride" matches "uber")
                else:
                    for keyword, weight in keywords.items():
                        if keyword in token and len(keyword) > 3:
                            scores[cat] += weight * 0.5 * self.idf.get(keyword, 1.0)
                            
        best_cat = max(scores.items(), key=lambda x: x[1])
        
        if best_cat[1] > 1.5:
            return best_cat[0], best_cat[1]
        return "Other", best_cat[1]

def categorize_missing_fields(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Scan imported records and auto-categorize those missing a valid category."""
    categorizer = TextCategorizer()
    stats = {"auto_categorized": 0, "failed_categorization": 0}
    
    valid_cats = set(CATEGORY_CORPUS.keys())
    
    for r in records:
        cat = r.get("category")
        activity = r.get("activity")
        
        if not cat or cat == "Other" or cat not in valid_cats:
            if activity:
                predicted, confidence = categorizer.predict_category(activity)
                if predicted != "Other":
                    r["category"] = predicted
                    if "_warnings" not in r:
                        r["_warnings"] = []
                    r["_warnings"].append(f"[ML Auto-Cat] Categorized as {predicted} based on description (confidence: {confidence:.2f}).")
                    stats["auto_categorized"] += 1
                else:
                    r["category"] = "Other"
                    stats["failed_categorization"] += 1
            else:
                r["category"] = "Other"
                stats["failed_categorization"] += 1
                
    return records, stats
