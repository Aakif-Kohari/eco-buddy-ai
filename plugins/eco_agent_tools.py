import json
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class EcoAgentTools:
    """
    A registry of callable tools (functions) that a Large Language Model (LLM) 
    can invoke during a conversation (e.g., via OpenAI Function Calling or Gemini Tool Use).
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(self, name: str, description: str, func: Callable, parameters: Dict[str, Any]):
        """Registers a new function that the LLM can use."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func
        }
        logger.info(f"Registered Agent Tool: {name}")

    def get_tool_schemas(self) -> list:
        """Returns the JSON schema definitions expected by OpenAI/Gemini APIs."""
        schemas = []
        for name, data in self._tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": data["name"],
                    "description": data["description"],
                    "parameters": data["parameters"]
                }
            })
        return schemas

    def execute_tool(self, tool_name: str, arguments: str) -> str:
        """
        Executes the tool requested by the LLM and returns the stringified result.
        """
        if tool_name not in self._tools:
            return json.dumps({"error": f"Tool '{tool_name}' not found."})
            
        try:
            # Parse arguments provided by the LLM
            args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            # Execute the python function
            func = self._tools[tool_name]["func"]
            result = func(**args_dict)
            
            # Return result as JSON string to feed back into the LLM context
            return json.dumps({"success": True, "result": result})
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    # --- Tool Implementations ---

    def _register_default_tools(self):
        """Registers the core eco-calculation tools available to the chatbot."""
        
        self.register_tool(
            name="calculate_flight_emissions",
            description="Calculates the carbon footprint of a flight between two locations.",
            parameters={
                "type": "object",
                "properties": {
                    "distance_km": {"type": "number", "description": "The distance of the flight in kilometers."},
                    "class_type": {"type": "string", "enum": ["economy", "business", "first"], "description": "The seating class."}
                },
                "required": ["distance_km"]
            },
            func=self._calc_flight
        )
        
        self.register_tool(
            name="get_current_grid_intensity",
            description="Fetches the real-time carbon intensity (gCO2eq/kWh) of the power grid in a specific region.",
            parameters={
                "type": "object",
                "properties": {
                    "region_code": {"type": "string", "description": "The country or region code (e.g., 'US', 'GB', 'FR')."}
                },
                "required": ["region_code"]
            },
            func=self._get_grid_intensity
        )
        
        self.register_tool(
            name="calculate_clothing_impact",
            description="Calculates the water and carbon impact of a specific clothing item.",
            parameters={
                "type": "object",
                "properties": {
                    "item_type": {"type": "string", "description": "Type of clothing (e.g. 'jeans', 't-shirt', 'jacket')."},
                    "material": {"type": "string", "description": "Primary material (e.g. 'cotton', 'polyester', 'wool')."}
                },
                "required": ["item_type", "material"]
            },
            func=self._calc_clothing
        )

    # --- Tool Logic Methods ---
    
    def _calc_flight(self, distance_km: float, class_type: str = "economy") -> Dict[str, Any]:
        """Mock calculation for flight emissions."""
        # Standard factors: 0.15 kg CO2/km for economy, 0.30 for business
        multiplier = 1.0 if class_type == "economy" else 2.0
        emissions = distance_km * 0.15 * multiplier
        return {
            "emissions_kg_co2": round(emissions, 2),
            "distance_km": distance_km,
            "class": class_type
        }

    def _get_grid_intensity(self, region_code: str) -> Dict[str, Any]:
        """Mock API call for grid intensity."""
        # Simulated data map
        intensities = {
            "US": 386.0,
            "GB": 253.0,
            "FR": 58.0,  # Nuclear heavy
            "IN": 708.0, # Coal heavy
            "CA": 130.0  # Hydro heavy
        }
        val = intensities.get(region_code.upper(), 450.0) # Default to global avg
        return {
            "region": region_code.upper(),
            "intensity_g_co2_per_kwh": val,
            "status": "real-time mock"
        }

    def _calc_clothing(self, item_type: str, material: str) -> Dict[str, Any]:
        """Mock calculation for fashion footprint."""
        water_liters = 2500 if material.lower() == "cotton" else 500
        carbon_kg = 15.0 if material.lower() == "polyester" else 8.0
        
        if item_type.lower() == "jeans":
            water_liters *= 3
            carbon_kg *= 2
            
        return {
            "item": item_type,
            "material": material,
            "water_impact_liters": water_liters,
            "carbon_impact_kg": carbon_kg
        }
