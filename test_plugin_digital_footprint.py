import pytest
from plugins.digital_footprint import DigitalFootprintPlugin

def test_digital_footprint_plugin():
    plugin = DigitalFootprintPlugin()
    
    assert plugin.name == "digital_footprint"
    assert plugin.category == "Digital"
    
    # Test getting input fields
    fields = plugin.get_input_fields()
    assert len(fields) > 5
    field_names = [f.name for f in fields]
    assert "streaming_hours_daily" in field_names
    assert "crypto_tx_monthly" in field_names
    
    # Test calculation
    inputs = {
        "streaming_hours_daily": 2.0,
        "streaming_resolution": "1080p",
        "social_media_hours_daily": 1.0, 
        "cloud_storage_gb": 100.0,       
        "cloud_provider": "Generic",
        "emails_text_daily": 10.0,       
        "emails_attachment_daily": 1.0,  
        "ai_queries_daily": 2.0,         
        "video_calls_hours_weekly": 1.0, 
        "crypto_tx_monthly": 1.0,        
        "web_browsing_hours_daily": 1.0  
    }
    
    result = plugin.calculate(inputs)
    
    assert result.unit == "kg CO2/year"
    assert result.total > 3000 # Crypto alone is 3000
    
    # Check contributors
    assert "Video Streaming" in result.contributors
    assert "Cryptocurrency" in result.contributors
    assert "Communication" in result.contributors
    
    # Check recommendations
    recs = plugin.get_recommendations(result)
    assert len(recs) > 0
    assert any("Bitcoin" in r or "Proof-of-Stake" in r for r in recs)
