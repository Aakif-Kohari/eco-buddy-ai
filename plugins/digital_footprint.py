import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from plugins.base import CalculatorPlugin, InputField, CalcResult

# --- Global Constants & Emission Factors Dataset ---
# These are highly detailed representative estimations (in kg CO2e) per unit.
# Sources derived from various lifecycle assessments (LCA) on digital footprint.

# 1. Device Power (Watts) & Amortized Embodied Carbon (kg CO2e / year assuming 3-4 year lifespan)
DEVICE_MODELS = [
    {"device": "Smartphone", "power_w": 2.0, "embodied_annual": 20.0},
    {"device": "Tablet", "power_w": 5.0, "embodied_annual": 35.0},
    {"device": "Laptop", "power_w": 25.0, "embodied_annual": 80.0},
    {"device": "Desktop_PC", "power_w": 100.0, "embodied_annual": 150.0},
    {"device": "Smart_TV_4K", "power_w": 120.0, "embodied_annual": 120.0},
]
df_devices = pd.DataFrame(DEVICE_MODELS).set_index("device")

# 2. Network Transmission Intensity (kWh / GB)
NETWORK_TYPES = [
    {"network": "WiFi", "kwh_per_gb": 0.04},
    {"network": "4G", "kwh_per_gb": 0.15},
    {"network": "5G", "kwh_per_gb": 0.08},
    {"network": "Wired", "kwh_per_gb": 0.02},
]
df_networks = pd.DataFrame(NETWORK_TYPES).set_index("network")

# 3. Regional Grid Carbon Intensity (kg CO2e / kWh)
REGIONAL_GRIDS = [
    {"region": "Global_Average", "intensity": 0.436},
    {"region": "USA", "intensity": 0.380},
    {"region": "European_Union", "intensity": 0.250},
    {"region": "United_Kingdom", "intensity": 0.210},
    {"region": "India", "intensity": 0.700},
    {"region": "China", "intensity": 0.540},
    {"region": "Australia", "intensity": 0.650},
]
df_grids = pd.DataFrame(REGIONAL_GRIDS).set_index("region")

# 4. Activity Data Consumption (GB / hour)
ACTIVITY_DATA = [
    {"activity": "Streaming_4K", "gb_per_hr": 7.0},
    {"activity": "Streaming_1080p", "gb_per_hr": 3.0},
    {"activity": "Streaming_720p", "gb_per_hr": 1.0},
    {"activity": "Social_Media_Video", "gb_per_hr": 1.5},
    {"activity": "Social_Media_Text", "gb_per_hr": 0.1},
    {"activity": "Video_Call_Video", "gb_per_hr": 1.2},
    {"activity": "Video_Call_Audio", "gb_per_hr": 0.1},
    {"activity": "Web_Browsing", "gb_per_hr": 0.06},
]
df_activities = pd.DataFrame(ACTIVITY_DATA).set_index("activity")

# 5. Data Center / Cloud / Misc Static Factors (kg CO2e)
STATIC_FACTORS = [
    {"item": "Cloud_Storage_AWS", "category": "Data Center", "unit": "gb_year", "co2_kg": 0.003},
    {"item": "Cloud_Storage_GCP", "category": "Data Center", "unit": "gb_year", "co2_kg": 0.002}, # Slightly lower due to aggressive PPA matching
    {"item": "Cloud_Storage_Azure", "category": "Data Center", "unit": "gb_year", "co2_kg": 0.0035},
    {"item": "Cloud_Storage_Generic", "category": "Data Center", "unit": "gb_year", "co2_kg": 0.004},
    {"item": "Email_Text", "category": "Communication", "unit": "email", "co2_kg": 0.004},
    {"item": "Email_Attachment", "category": "Communication", "unit": "email", "co2_kg": 0.050},
    {"item": "AI_Query_Text", "category": "AI Usage", "unit": "query", "co2_kg": 0.0043},
    {"item": "AI_Query_Image", "category": "AI Usage", "unit": "query", "co2_kg": 0.022},
    {"item": "Crypto_Tx_Bitcoin", "category": "Cryptocurrency", "unit": "tx", "co2_kg": 250.0},
    {"item": "Crypto_Tx_Ethereum", "category": "Cryptocurrency", "unit": "tx", "co2_kg": 0.01}, 
]
df_static = pd.DataFrame(STATIC_FACTORS).set_index("item")


class DigitalFootprintPlugin(CalculatorPlugin):
    """
    Advanced plugin for calculating a comprehensive digital carbon footprint.
    Models energy consumption dynamically using Pandas based on device type, 
    network connection, regional grid intensity, data centers, and embodied carbon.
    """

    @property
    def name(self) -> str:
        return "digital_footprint"

    @property
    def description(self) -> str:
        return "Advanced digital footprint modeling analyzing devices, networks, regional grids, and cloud habits."

    @property
    def category(self) -> str:
        return "Digital"

    def get_input_fields(self) -> list[InputField]:
        return [
            # Region & Infrastructure Setup
            InputField(
                name="region",
                label="Your Geographic Region",
                type="select",
                default="Global_Average",
                options=tuple(df_grids.index.tolist()),
                help_text="Determines the carbon intensity of the electricity powering your devices and local networks."
            ),
            InputField(
                name="primary_device",
                label="Primary Personal Device",
                type="select",
                default="Smartphone",
                options=tuple(df_devices.index.tolist()),
                help_text="Used to estimate power draw and manufacturing (embodied) carbon footprint."
            ),
            InputField(
                name="primary_network",
                label="Primary Network Connection",
                type="select",
                default="WiFi",
                options=tuple(df_networks.index.tolist()),
                help_text="Cellular networks (4G/5G) are significantly more energy-intensive than WiFi."
            ),
            # Streaming & Media
            InputField(
                name="streaming_hours_daily",
                label="Daily Video Streaming (hours)",
                type="number",
                default=2.0,
                min_val=0.0,
                max_val=24.0,
            ),
            InputField(
                name="streaming_resolution",
                label="Primary Streaming Resolution",
                type="select",
                default="1080p",
                options=("720p", "1080p", "4K"),
            ),
            InputField(
                name="social_media_hours_daily",
                label="Daily Social Media (hours)",
                type="number",
                default=1.5,
                min_val=0.0,
                max_val=24.0,
            ),
            # Work & Communication
            InputField(
                name="web_browsing_hours_daily",
                label="Daily General Web Browsing (hours)",
                type="number",
                default=4.0,
                min_val=0.0,
                max_val=24.0,
            ),
            InputField(
                name="video_calls_hours_weekly",
                label="Weekly Video Calls (hours)",
                type="number",
                default=3.0,
                min_val=0.0,
            ),
            InputField(
                name="emails_text_daily",
                label="Text Emails Sent/Received Daily",
                type="number",
                default=30.0,
                min_val=0.0,
            ),
            InputField(
                name="emails_attachment_daily",
                label="Emails with Attachments Daily",
                type="number",
                default=5.0,
                min_val=0.0,
            ),
            # Advanced Tech & Cloud
            InputField(
                name="cloud_storage_gb",
                label="Total Cloud Storage (GB)",
                type="number",
                default=50.0,
                min_val=0.0,
            ),
            InputField(
                name="cloud_provider",
                label="Primary Cloud Provider",
                type="select",
                default="Generic",
                options=("AWS", "GCP", "Azure", "Generic"),
            ),
            InputField(
                name="ai_queries_daily",
                label="Daily AI Queries (ChatGPT, Claude, Gemini)",
                type="number",
                default=5.0,
                min_val=0.0,
            ),
            InputField(
                name="crypto_tx_monthly",
                label="Monthly Crypto Transactions (Bitcoin)",
                type="number",
                default=0.0,
                min_val=0.0,
            ),
        ]

    def _calc_dynamic_energy_footprint(self, 
                                       activity_key: str, 
                                       hours_yr: float, 
                                       device: str, 
                                       network: str, 
                                       grid_intensity: float) -> float:
        """
        Calculates the carbon footprint of an activity based on:
        1. Device power consumption
        2. Network data transmission
        3. Data Center processing (estimated baseline)
        Multiplied by local grid carbon intensity where applicable.
        """
        if activity_key not in df_activities.index:
            return 0.0

        gb_per_hr = df_activities.loc[activity_key, "gb_per_hr"]
        device_watts = df_devices.loc[device, "power_w"]
        net_kwh_per_gb = df_networks.loc[network, "kwh_per_gb"]
        
        # 1. End-User Device Energy (kWh)
        device_kwh = (device_watts / 1000.0) * hours_yr
        device_co2 = device_kwh * grid_intensity
        
        # 2. Network Transmission Energy (kWh)
        total_gb = gb_per_hr * hours_yr
        network_kwh = total_gb * net_kwh_per_gb
        # Network infrastructure is globally distributed, we use a blended global/local rate.
        # For simplicity, we use local grid intensity.
        network_co2 = network_kwh * grid_intensity
        
        # 3. Data Center generic baseline for this data (approximated at 0.05 kWh/GB)
        # Using global average intensity for cloud data centers unless regionalized.
        global_intensity = df_grids.loc["Global_Average", "intensity"]
        dc_kwh = total_gb * 0.05
        dc_co2 = dc_kwh * global_intensity
        
        return float(device_co2 + network_co2 + dc_co2)

    def calculate(self, inputs: dict) -> CalcResult:
        # --- 1. Extract & Sanitize User Inputs ---
        region = inputs.get("region", "Global_Average")
        device = inputs.get("primary_device", "Smartphone")
        network = inputs.get("primary_network", "WiFi")
        
        grid_intensity = float(df_grids.loc[region, "intensity"])
        embodied_co2 = float(df_devices.loc[device, "embodied_annual"])

        res = inputs.get("streaming_resolution", "1080p")
        
        # Annualized usage factors
        stream_hours_yr = float(inputs.get("streaming_hours_daily", 0)) * 365
        sm_hours_yr = float(inputs.get("social_media_hours_daily", 0)) * 365
        web_hours_yr = float(inputs.get("web_browsing_hours_daily", 0)) * 365
        vc_hours_yr = float(inputs.get("video_calls_hours_weekly", 0)) * 52
        
        # Static usage factors
        cloud_gb = float(inputs.get("cloud_storage_gb", 0))
        cloud_provider = inputs.get("cloud_provider", "Generic")
        emails_text = float(inputs.get("emails_text_daily", 0)) * 365
        emails_att = float(inputs.get("emails_attachment_daily", 0)) * 365
        ai_queries = float(inputs.get("ai_queries_daily", 0)) * 365
        crypto_tx = float(inputs.get("crypto_tx_monthly", 0)) * 12

        # --- 2. Dynamic Emissions (Dependent on device, network, grid) ---
        dynamic_activities = {}
        
        # Streaming
        dynamic_activities["Video Streaming"] = self._calc_dynamic_energy_footprint(
            f"Streaming_{res}", stream_hours_yr, device, network, grid_intensity
        )
        
        # Social Media (Split 70% Video, 30% Text)
        sm_video_co2 = self._calc_dynamic_energy_footprint(
            "Social_Media_Video", sm_hours_yr * 0.7, device, network, grid_intensity
        )
        sm_text_co2 = self._calc_dynamic_energy_footprint(
            "Social_Media_Text", sm_hours_yr * 0.3, device, network, grid_intensity
        )
        dynamic_activities["Social Media"] = sm_video_co2 + sm_text_co2
        
        # Web Browsing
        dynamic_activities["Web Browsing"] = self._calc_dynamic_energy_footprint(
            "Web_Browsing", web_hours_yr, device, network, grid_intensity
        )
        
        # Video Calls
        dynamic_activities["Video Calls"] = self._calc_dynamic_energy_footprint(
            "Video_Call_Video", vc_hours_yr, device, network, grid_intensity
        )

        # --- 3. Static Emissions (Backend Server/Cloud dominated) ---
        static_series = pd.Series({
            f"Cloud_Storage_{cloud_provider}": cloud_gb,
            "Email_Text": emails_text,
            "Email_Attachment": emails_att,
            "AI_Query_Text": ai_queries,
            "Crypto_Tx_Bitcoin": crypto_tx
        }, name="quantity").fillna(0)
        
        # Filter static indices to ensure matching
        valid_keys = [k for k in static_series.index if k in df_static.index]
        static_series = static_series[valid_keys]
        
        df_static_calc = pd.DataFrame(static_series).join(df_static, how="inner")
        df_static_calc["total_co2"] = df_static_calc["quantity"] * df_static_calc["co2_kg"]
        
        static_grouped = df_static_calc.groupby("category")["total_co2"].sum().to_dict()

        # --- 4. Consolidate Results ---
        contributors = {
            "Embodied Carbon (Hardware)": round(embodied_co2, 2),
            **{k: round(v, 2) for k, v in dynamic_activities.items() if v > 0},
            **{k: round(v, 2) for k, v in static_grouped.items() if v > 0}
        }
        
        total_emission = sum(contributors.values())
        
        # Detailed metadata for recommendations
        metadata = {
            "device": device,
            "network": network,
            "region": region,
            "is_high_res": res == "4K",
            "crypto_heavy": crypto_tx > 0,
            "cloud_heavy": cloud_gb > 500,
            "ai_heavy": ai_queries > 3000,
            "grid_intensity": grid_intensity,
            "dynamic_details": dynamic_activities,
            "static_details": df_static_calc.reset_index().to_dict(orient="records")
        }

        return CalcResult(
            total=round(total_emission, 2),
            unit="kg CO2/year",
            contributors=contributors,
            metadata=metadata
        )

    def get_recommendations(self, result: CalcResult) -> list[str]:
        recommendations = []
        meta = result.metadata
        
        device = meta.get("device")
        network = meta.get("network")
        region = meta.get("region")
        grid_int = meta.get("grid_intensity", 0.436)
        
        contributors = result.contributors
        if not contributors:
            return ["No digital activity logged."]
            
        # Identify top contributor
        top_category = max(contributors, key=contributors.get)
        top_val = contributors[top_category]
        
        # 1. Total-based recommendations
        if result.total > 1000:
            recommendations.append(
                f"Your digital footprint is quite high ({result.total} kg CO2). Consider a 'digital detox' day once a month to offset this."
            )
            
        # 2. Embodied Carbon (Hardware) Tips
        if top_category == "Embodied Carbon (Hardware)":
            recommendations.append(
                f"Your highest footprint comes from manufacturing your {device}. The best thing you can do is hold onto your device for an extra year instead of upgrading!"
            )
            if device in ["Desktop_PC", "Smart_TV_4K"]:
                recommendations.append(
                    "Large devices contain massive amounts of embodied carbon and toxic rare earth metals. Consider buying refurbished for your next purchase."
                )

        # 3. Grid & Region Tips
        if grid_int > 0.5:
            recommendations.append(
                f"Because the power grid in {region} relies heavily on fossil fuels, reducing your screen time has an amplified positive effect on the environment."
            )
            
        # 4. Network Tips
        if network in ["4G", "5G"]:
            recommendations.append(
                f"You primarily use a cellular ({network}) network. Cellular data uses 2-4x more energy than WiFi. Connect to WiFi when streaming video or downloading large files."
            )
            
        # 5. Activity Specific Tips
        if top_category == "Video Streaming":
            if meta.get("is_high_res"):
                recommendations.append(
                    "Downgrading your default streaming resolution from 4K to 1080p can reduce data transmission energy by over 50%."
                )
            else:
                recommendations.append(
                    "Try downloading your favorite shows or podcasts over WiFi instead of continuously streaming them."
                )
                
        elif top_category == "Social Media":
            recommendations.append(
                "Social media apps infinitely preload video streams. Turn off 'autoplay' and 'background app refresh' to save massive amounts of data and carbon."
            )
            
        elif top_category == "Video Calls":
            recommendations.append(
                "For casual or long video calls, turning off your camera when you aren't speaking cuts the environmental impact by 96%."
            )
            
        # 6. Static backend tips
        if meta.get("cloud_heavy"):
            recommendations.append(
                "Cloud servers run 24/7. Do a spring cleaning of your cloud drive: delete duplicates, old backups, and giant video files."
            )
            
        if meta.get("crypto_heavy"):
            recommendations.append(
                "Bitcoin transactions are notoriously energy-intensive due to Proof-of-Work. Consider supporting green blockchains (Proof-of-Stake) which use 99.9% less energy."
            )
            
        if meta.get("ai_heavy"):
            recommendations.append(
                "Generative AI queries take up to 10x more computing power than standard Google searches. Use them mindfully for complex tasks rather than simple searches."
            )
            
        # 7. Generic tip
        recommendations.append(
            "E-waste is a massive global issue. Always recycle old electronics at certified centers rather than throwing them in the trash."
        )

        return recommendations
