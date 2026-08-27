import json
import csv
import io
import datetime
from typing import Dict, Any, List

class DataPortabilityEngine:
    """
    Manages the export of user data into portable formats (JSON, CSV, XML) 
    in compliance with GDPR Article 20 (Right to Data Portability).
    """

    def __init__(self, user_id: str, fetch_user_data_cb=None):
        self.user_id = user_id
        # mock fetching function if none provided
        self.fetch_data = fetch_user_data_cb or self._mock_fetch_data

    def _mock_fetch_data(self) -> Dict[str, Any]:
        return {
            "account": {
                "user_id": self.user_id,
                "email": f"user_{self.user_id}@example.com",
                "created_at": "2023-01-15T10:00:00",
                "last_login": datetime.datetime.now().isoformat()
            },
            "footprints": [
                {"date": "2023-10-01", "type": "Transport", "co2_kg": 15.4},
                {"date": "2023-10-02", "type": "Diet", "co2_kg": 5.2},
                {"date": "2023-10-03", "type": "Energy", "co2_kg": 12.0}
            ],
            "preferences": {
                "theme": "dark",
                "notifications_enabled": True,
                "newsletter_subscribed": False
            }
        }

    def export_as_json(self) -> str:
        """Exports the entire user profile as a formatted JSON string."""
        data = self.fetch_data()
        metadata = {
            "exported_at": datetime.datetime.now().isoformat(),
            "compliance_standard": "GDPR-Article-20"
        }
        payload = {
            "metadata": metadata,
            "data": data
        }
        return json.dumps(payload, indent=4)

    def export_as_csv(self) -> str:
        """Exports the user footprints array as a CSV string."""
        data = self.fetch_data()
        footprints = data.get("footprints", [])
        
        output = io.StringIO()
        if not footprints:
            return ""
            
        writer = csv.DictWriter(output, fieldnames=["date", "type", "co2_kg"])
        writer.writeheader()
        for f in footprints:
            writer.writerow(f)
            
        return output.getvalue()

    def generate_personal_data_summary(self) -> str:
        """Generates a human-readable summary of the data held by the controller."""
        data = self.fetch_data()
        acc = data.get("account", {})
        
        summary = (
            f"Personal Data Summary for {acc.get('email', 'Unknown')}\n"
            f"=====================================================\n"
            f"Account created: {acc.get('created_at', 'Unknown')}\n"
            f"Last login: {acc.get('last_login', 'Unknown')}\n\n"
            f"Total footprint records stored: {len(data.get('footprints', []))}\n"
            f"Marketing preferences: {'Opted In' if data.get('preferences', {}).get('newsletter_subscribed') else 'Opted Out'}\n"
        )
        return summary
