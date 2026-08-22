import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta

class ScreenTimeParser:
    """
    Advanced parser for Apple Screen Time and Google Digital Wellbeing data exports.
    Normalizes complex JSON/CSV app usage metrics into categorized digital footprint inputs.
    """
    
    # Categorization engine to map millions of potential apps to our emission factors
    APP_CATEGORY_MAP = {
        "Netflix": "Streaming_1080p",
        "YouTube": "Streaming_1080p",
        "Hulu": "Streaming_1080p",
        "Disney+": "Streaming_1080p",
        "Twitch": "Streaming_1080p",
        "Instagram": "Social_Media_Video",
        "TikTok": "Social_Media_Video",
        "Snapchat": "Social_Media_Video",
        "Facebook": "Social_Media_Video",
        "Twitter": "Social_Media_Text",
        "Reddit": "Social_Media_Text",
        "LinkedIn": "Social_Media_Text",
        "Chrome": "Web_Browsing",
        "Safari": "Web_Browsing",
        "Firefox": "Web_Browsing",
        "Zoom": "Video_Call_Video",
        "Teams": "Video_Call_Video",
        "Meet": "Video_Call_Video",
        "Mail": "Email_Text",
        "Gmail": "Email_Text",
        "Outlook": "Email_Text",
        "ChatGPT": "AI_Query_Text",
        "Claude": "AI_Query_Text"
    }

    def __init__(self, raw_data_string: str, format_type: str = "apple_json"):
        self.raw_data = raw_data_string
        self.format_type = format_type
        self.parsed_df = pd.DataFrame()

    def parse(self) -> pd.DataFrame:
        """Parses the raw string into a normalized Pandas DataFrame."""
        if self.format_type == "apple_json":
            self.parsed_df = self._parse_apple_json()
        elif self.format_type == "google_csv":
            self.parsed_df = self._parse_google_csv()
        else:
            raise ValueError(f"Unsupported format type: {self.format_type}")
            
        return self._normalize_data()

    def _parse_apple_json(self) -> pd.DataFrame:
        """
        Simulates parsing a complex nested JSON from Apple Screen Time.
        Expected format: {"device": "iPhone", "usage": [{"app": "Netflix", "seconds": 7200, "date": "2023-10-01"}]}
        """
        try:
            data = json.loads(self.raw_data)
            usage_list = data.get("usage", [])
            df = pd.DataFrame(usage_list)
            if not df.empty:
                df["hours"] = df["seconds"] / 3600.0
            return df
        except Exception as e:
            raise ValueError(f"Failed to parse Apple JSON: {str(e)}")

    def _parse_google_csv(self) -> pd.DataFrame:
        """
        Simulates parsing a CSV from Google Digital Wellbeing.
        Expected format: Date,App,Duration_Milliseconds
        """
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(self.raw_data))
            # Normalize column names
            df = df.rename(columns={"App": "app", "Date": "date", "Duration_Milliseconds": "ms"})
            if not df.empty:
                df["hours"] = df["ms"] / 3600000.0
            return df
        except Exception as e:
            raise ValueError(f"Failed to parse Google CSV: {str(e)}")

    def _normalize_data(self) -> pd.DataFrame:
        """Applies mapping algorithms to categorize raw app usage into emission categories."""
        if self.parsed_df.empty:
            return pd.DataFrame(columns=["date", "app", "hours", "emission_category"])
            
        df = self.parsed_df.copy()
        
        # Apply the category map, defaulting to 'Web_Browsing' for unknown apps
        df["emission_category"] = df["app"].map(self.APP_CATEGORY_MAP).fillna("Web_Browsing")
        return df

    def get_daily_averages_for_plugin(self) -> Dict[str, float]:
        """
        Aggregates the normalized DataFrame into exact dictionary inputs 
        expected by the DigitalFootprintPlugin.
        """
        if self.parsed_df.empty:
            return {}
            
        # Group by category and sum hours
        total_by_category = self.parsed_df.groupby("emission_category")["hours"].sum()
        
        # Calculate number of unique days in the dataset to find daily averages
        unique_days = self.parsed_df["date"].nunique()
        if unique_days == 0:
            unique_days = 1
            
        daily_averages = (total_by_category / unique_days).to_dict()
        
        # Translate categorized averages to plugin input keys
        plugin_inputs = {}
        
        streaming_total = 0.0
        for key, val in daily_averages.items():
            if key.startswith("Streaming_"):
                streaming_total += val
        if streaming_total > 0:
            plugin_inputs["streaming_hours_daily"] = round(streaming_total, 2)
            
        if "Social_Media_Video" in daily_averages or "Social_Media_Text" in daily_averages:
            sm_total = daily_averages.get("Social_Media_Video", 0) + daily_averages.get("Social_Media_Text", 0)
            plugin_inputs["social_media_hours_daily"] = round(sm_total, 2)
            
        if "Web_Browsing" in daily_averages:
            plugin_inputs["web_browsing_hours_daily"] = round(daily_averages["Web_Browsing"], 2)
            
        if "Video_Call_Video" in daily_averages:
            # Plugin expects weekly
            plugin_inputs["video_calls_hours_weekly"] = round(daily_averages["Video_Call_Video"] * 7, 2)
            
        if "Email_Text" in daily_averages:
            # Very rough heuristic: 1 hour in mail app = ~20 emails sent/read
            plugin_inputs["emails_text_daily"] = round(daily_averages["Email_Text"] * 20, 0)
            
        if "AI_Query_Text" in daily_averages:
            # 1 hour in AI app = ~15 queries
            plugin_inputs["ai_queries_daily"] = round(daily_averages["AI_Query_Text"] * 15, 0)
            
        return plugin_inputs

    @staticmethod
    def generate_mock_apple_data(days: int = 7) -> str:
        """Utility to generate mock JSON for testing the UI integration."""
        import random
        usage = []
        base_date = datetime.now()
        apps = ["Netflix", "Instagram", "Chrome", "Mail", "Zoom", "ChatGPT", "UnknownGame"]
        
        for i in range(days):
            current_date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            for app in apps:
                # Random usage between 0 and 3 hours (in seconds)
                seconds = random.randint(0, 10800) 
                usage.append({"app": app, "seconds": seconds, "date": current_date})
                
        return json.dumps({"device": "iPhone 13 Pro", "usage": usage})
