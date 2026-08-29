"""
Green Vendor Matcher.
Manages a mock directory of sustainable vendors and matches them to user preferences based on eco-certifications.
"""

from typing import Dict, Any, List


class GreenVendorMatcher:
    """Filters and recommends sustainable vendors for events."""

    # Mock database of sustainable vendors
    VENDOR_DATABASE = [
        {
            "id": "v1",
            "name": "EcoBites Catering",
            "category": "catering",
            "certifications": ["zero_waste", "organic", "local_sourced"],
            "description": "100% plant-based catering with compostable serveware.",
            "rating": 4.8,
        },
        {
            "id": "v2",
            "name": "GreenGrid Venues",
            "category": "venue",
            "certifications": ["renewable_energy", "leed_platinum"],
            "description": "Event spaces powered entirely by onsite solar and wind.",
            "rating": 4.9,
        },
        {
            "id": "v3",
            "name": "Nature's Decor",
            "category": "decorations",
            "certifications": ["upcycled", "biodegradable"],
            "description": "Floral and decor arrangements using only locally foraged or upcycled materials.",
            "rating": 4.7,
        },
        {
            "id": "v4",
            "name": "Transit-Friendly Halls",
            "category": "venue",
            "certifications": ["public_transit_accessible", "bike_parking"],
            "description": "Venues located directly adjacent to major public transit hubs.",
            "rating": 4.5,
        },
        {
            "id": "v5",
            "name": "Rooted Catering Co.",
            "category": "catering",
            "certifications": ["local_sourced", "regenerative_agriculture"],
            "description": "Menu focused on regenerative agriculture ingredients.",
            "rating": 4.6,
        },
    ]

    def __init__(self):
        self.vendors = self.VENDOR_DATABASE

    def get_vendors_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Retrieves all vendors in a specific category."""
        return [v for v in self.vendors if v["category"].lower() == category.lower()]

    def match_vendors(
        self, required_certifications: List[str], category: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Matches vendors based on required certifications and optional category filter.
        A vendor matches if they possess ALL required certifications.
        """
        matched = []
        req_certs_lower = [cert.lower() for cert in required_certifications]

        for vendor in self.vendors:
            if category and vendor["category"].lower() != category.lower():
                continue

            vendor_certs_lower = [cert.lower() for cert in vendor["certifications"]]

            # Check if all required certifications are present in the vendor's certifications
            if all(req in vendor_certs_lower for req in req_certs_lower):
                matched.append(vendor)

        # Sort by rating descending
        return sorted(matched, key=lambda x: x["rating"], reverse=True)

    def get_all_certifications(self) -> List[str]:
        """Returns a unique list of all available certifications in the database."""
        certs = set()
        for vendor in self.vendors:
            certs.update(vendor["certifications"])
        return sorted(list(certs))
