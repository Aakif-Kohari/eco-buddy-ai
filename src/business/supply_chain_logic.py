import pandas as pd
from typing import Dict, Any, Tuple

class SupplyChainLogic:
    """
    Core business logic for calculating Scope 3 emissions, supplier ESG scores,
    and supply chain optimization metrics.
    """

    # Emission factors (kg CO2e per unit)
    TRANSPORT_EMISSION_FACTORS = {
        "Air": 0.500,  # per ton-km
        "Sea": 0.015,  # per ton-km
        "Rail": 0.025, # per ton-km
        "Road": 0.100  # per ton-km
    }

    MATERIAL_EMISSION_FACTORS = {
        "Steel": 1800,      # per ton
        "Aluminum": 11500,  # per ton
        "Plastic": 2500,    # per ton
        "Copper": 4000,     # per ton
        "Lithium": 5000,    # per ton
        "Microchips": 8000, # per ton
        "Batteries": 6000,  # per ton
        "Casings": 1500,    # per ton
        "Screens": 4500,    # per ton
        "Motors": 3500,     # per ton
        "Cardboard": 800,   # per ton
        "Recycled Paper": 500,
        "Bio-Plastic": 1200,
        "Styrofoam": 3000,
        "Wood": 400
    }

    ENERGY_EMISSION_FACTOR = 400 # kg CO2e per MWh (Global Average)

    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.suppliers = data.get("suppliers", pd.DataFrame())
        self.shipments = data.get("shipments", pd.DataFrame())
        self.facilities = data.get("facilities", pd.DataFrame())

    def calculate_transport_emissions(self) -> pd.DataFrame:
        """Calculates emissions for each shipment based on weight, distance, and mode."""
        if self.shipments.empty:
            return self.shipments

        df = self.shipments.copy()
        
        def calc_emission(row):
            factor = self.TRANSPORT_EMISSION_FACTORS.get(row["transport_mode"], 0.1)
            return (row["distance_km"] * row["weight_tons"] * factor) / 1000 # Convert to metric tons CO2e

        df["transport_emissions_mt"] = df.apply(calc_emission, axis=1)
        return df

    def calculate_material_emissions(self) -> pd.DataFrame:
        """Calculates embedded emissions of the materials shipped."""
        if self.shipments.empty:
            return self.shipments

        df = self.shipments.copy()
        
        def calc_emission(row):
            factor = self.MATERIAL_EMISSION_FACTORS.get(row["material_name"], 1000)
            return (row["weight_tons"] * factor) / 1000 # Metric tons CO2e

        df["material_emissions_mt"] = df.apply(calc_emission, axis=1)
        return df

    def calculate_facility_emissions(self) -> pd.DataFrame:
        """Calculates Scope 2/3 emissions from supplier facilities."""
        if self.facilities.empty:
            return self.facilities

        df = self.facilities.copy()
        supplier_dict = self.suppliers.set_index("supplier_id")["renewable_energy_pct"].to_dict()

        def calc_emission(row):
            renewable_pct = supplier_dict.get(row["supplier_id"], 0) / 100.0
            non_renewable_energy = row["annual_energy_mwh"] * (1 - renewable_pct)
            return (non_renewable_energy * self.ENERGY_EMISSION_FACTOR) / 1000 # Metric tons CO2e
            
        df["facility_emissions_mt"] = df.apply(calc_emission, axis=1)
        return df

    def generate_supplier_scorecard(self) -> pd.DataFrame:
        """Aggregates all metrics to provide a comprehensive supplier scorecard."""
        if self.suppliers.empty:
            return pd.DataFrame()

        transport_df = self.calculate_transport_emissions()
        material_df = self.calculate_material_emissions()
        facility_df = self.calculate_facility_emissions()

        # Aggregate shipments per supplier
        agg_shipments = pd.DataFrame()
        if not transport_df.empty:
            transport_grouped = transport_df.groupby("supplier_id")["transport_emissions_mt"].sum()
            material_grouped = material_df.groupby("supplier_id")["material_emissions_mt"].sum()
            total_spend = transport_df.groupby("supplier_id")["cost_usd"].sum()
            
            agg_shipments = pd.DataFrame({
                "total_transport_emissions": transport_grouped,
                "total_material_emissions": material_grouped,
                "total_spend_usd": total_spend
            }).reset_index()
            
        # Aggregate facilities per supplier
        agg_facilities = pd.DataFrame()
        if not facility_df.empty:
            facility_grouped = facility_df.groupby("supplier_id")["facility_emissions_mt"].sum()
            agg_facilities = pd.DataFrame({
                "total_facility_emissions": facility_grouped
            }).reset_index()

        # Merge with suppliers
        scorecard = self.suppliers.copy()
        
        if not agg_shipments.empty:
            scorecard = pd.merge(scorecard, agg_shipments, on="supplier_id", how="left")
        
        if not agg_facilities.empty:
            scorecard = pd.merge(scorecard, agg_facilities, on="supplier_id", how="left")
            
        # Fill NaNs
        scorecard.fillna(0, inplace=True)
        
        # Calculate Total Scope 3
        cols_to_sum = []
        if "total_transport_emissions" in scorecard.columns: cols_to_sum.append("total_transport_emissions")
        if "total_material_emissions" in scorecard.columns: cols_to_sum.append("total_material_emissions")
        if "total_facility_emissions" in scorecard.columns: cols_to_sum.append("total_facility_emissions")
        
        if cols_to_sum:
            scorecard["total_scope3_emissions_mt"] = scorecard[cols_to_sum].sum(axis=1)
        else:
            scorecard["total_scope3_emissions_mt"] = 0
            
        return scorecard

    def get_summary_metrics(self) -> Dict[str, float]:
        """Provides high-level dashboard summary metrics."""
        scorecard = self.generate_supplier_scorecard()
        
        if scorecard.empty:
            return {}
            
        metrics = {
            "total_suppliers": len(scorecard),
            "compliant_suppliers": len(scorecard[scorecard["compliance_status"] == "Compliant"]),
            "at_risk_suppliers": len(scorecard[scorecard["compliance_status"] == "At Risk"]),
            "avg_esg_score": scorecard["esg_score"].mean(),
            "total_scope3_emissions": scorecard["total_scope3_emissions_mt"].sum(),
            "avg_renewable_energy": scorecard["renewable_energy_pct"].mean()
        }
        
        return metrics
