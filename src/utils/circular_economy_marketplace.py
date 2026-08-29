import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SecondaryMaterialListing:
    listing_id: str
    material_name: str
    category: str  # 'Recycled Polymer Plastic', 'Scrap Aluminum Alloy', 'E-Waste Precious Metal Slag', 'Repurposed Textile Fiber'
    purity_grade_pct: float
    quantity_metric_tons: float
    unit_price_usd_ton: float
    embodied_co2_avoided_kg_per_kg: float
    seller_facility_name: str
    certification_status: str  # 'Verified Circular Grade A', 'Grade B Recycled', 'Raw Industrial Byproduct'

@dataclass
class CircularTransactionRecord:
    transaction_id: str
    listing_id: str
    buyer_company_name: str
    purchased_quantity_tons: float
    total_cost_usd: float
    co2_emissions_saved_tons: float
    transaction_timestamp: str

class CircularEconomyEngine:
    """
    Circular Economy Material Life Cycle & Secondary Raw Material Marketplace Engine.
    Tracks secondary industrial scrap recycling, embodied carbon savings,
    and B2B circular material transactions.
    """
    def __init__(self):
        self.listings: List[SecondaryMaterialListing] = [
            SecondaryMaterialListing(
                listing_id="mat-101",
                material_name="Post-Consumer rPET Pellets (Food Grade)",
                category="Recycled Polymer Plastic",
                purity_grade_pct=99.2,
                quantity_metric_tons=450.0,
                unit_price_usd_ton=1250.0,
                embodied_co2_avoided_kg_per_kg=1.85,
                seller_facility_name="Bavarian Polymer Recyclers GmbH",
                certification_status="Verified Circular Grade A"
            ),
            SecondaryMaterialListing(
                listing_id="mat-102",
                material_name="Secondary Aluminum Alloy 6061 Ingot",
                category="Scrap Aluminum Alloy",
                purity_grade_pct=96.5,
                quantity_metric_tons=120.0,
                unit_price_usd_ton=320.0,
                embodied_co2_avoided_kg_per_kg=0.90,
                seller_facility_name="Rhein-Main Scrap Smelter",
                certification_status="Verified Circular Grade A"
            ),
            SecondaryMaterialListing(
                listing_id="mat-103",
                material_name="PCB E-Waste Copper & Gold Concentrate Slag",
                category="E-Waste Precious Metal Slag",
                purity_grade_pct=88.0,
                quantity_metric_tons=35.0,
                unit_price_usd_ton=5400.0,
                embodied_co2_avoided_kg_per_kg=14.20,
                seller_facility_name="Nordic Urban Mining Hub",
                certification_status="Grade B Recycled"
            )
        ]

        self.transactions: List[CircularTransactionRecord] = [
            CircularTransactionRecord(
                transaction_id="tx-701",
                listing_id="mat-102",
                buyer_company_name="AutoForm Lightweight Motors AG",
                purchased_quantity_tons=40.0,
                total_cost_usd=84000.0,
                co2_emissions_saved_tons=356.0,
                transaction_timestamp="1 hour ago"
            )
        ]

    def get_listings(self, category_filter: str = "All") -> List[SecondaryMaterialListing]:
        if category_filter == "All":
            return self.listings
        return [m for m in self.listings if m.category == category_filter]

    def calculate_marketplace_impact(self) -> Dict[str, float]:
        total_tons = sum(m.quantity_metric_tons for m in self.listings)
        total_val = sum(m.quantity_metric_tons * m.unit_price_usd_ton for m in self.listings)
        co2_saved_tons = sum((m.quantity_metric_tons * m.embodied_co2_avoided_kg_per_kg) for m in self.listings)
        total_tx_co2_saved = sum(t.co2_emissions_saved_tons for t in self.transactions)

        return {
            "available_secondary_materials_tons": round(total_tons, 2),
            "marketplace_inventory_value_usd": round(total_val, 2),
            "potential_co2_avoided_tons": round(co2_saved_tons, 2),
            "realized_transaction_co2_saved_tons": round(total_tx_co2_saved, 2)
        }

    def register_listing(
        self,
        material_name: str,
        category: str,
        purity_grade_pct: float,
        quantity_metric_tons: float,
        unit_price_usd_ton: float,
        seller_facility_name: str
    ) -> SecondaryMaterialListing:
        co2_avoided = 2.4 if category == "Recycled Polymer Plastic" else 6.8
        new_item = SecondaryMaterialListing(
            listing_id=f"mat-{len(self.listings) + 101}",
            material_name=material_name,
            category=category,
            purity_grade_pct=purity_grade_pct,
            quantity_metric_tons=quantity_metric_tons,
            unit_price_usd_ton=unit_price_usd_ton,
            embodied_co2_avoided_kg_per_kg=co2_avoided,
            seller_facility_name=seller_facility_name,
            certification_status="Verified Circular Grade A"
        )
        self.listings.append(new_item)
        return new_item

    def execute_circular_purchase(self, listing_id: str, buyer_name: str, qty_tons: float) -> CircularTransactionRecord:
        listing = next((m for m in self.listings if m.listing_id == listing_id), None)
        price_per_ton = listing.unit_price_usd_ton if listing else 1500.0
        co2_factor = listing.embodied_co2_avoided_kg_per_kg if listing else 3.5

        cost = qty_tons * price_per_ton
        co2_saved = (qty_tons * 1000.0 * co2_factor) / 1000.0

        tx = CircularTransactionRecord(
            transaction_id=f"tx-{len(self.transactions) + 701}",
            listing_id=listing_id,
            buyer_company_name=buyer_name,
            purchased_quantity_tons=qty_tons,
            total_cost_usd=round(cost, 2),
            co2_emissions_saved_tons=round(co2_saved, 2),
            transaction_timestamp="Just now"
        )
        self.transactions.append(tx)
        return tx


def render_circular_economy_dashboard():
    """
    Streamlit interactive dashboard for Circular Economy & Secondary Raw Material Marketplace.
    """
    st.title("♻️ Circular Economy & Secondary Raw Material Marketplace Suite")
    st.markdown(
        "Trade verified secondary industrial raw materials, reduce embodied carbon footprints, and track zero-waste supply chain compliance."
    )

    engine = CircularEconomyEngine()
    impact = engine.calculate_marketplace_impact()

    # Metric Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Available Raw Materials", f"{impact['available_secondary_materials_tons']} Tons")
    with col2:
        st.metric("Inventory Market Value", f"${impact['marketplace_inventory_value_usd']:,.2f} USD")
    with col3:
        st.metric("Potential CO2 Avoided", f"{impact['potential_co2_avoided_tons']} Tons CO2e")
    with col4:
        st.metric("Realized CO2 Savings", f"{impact['realized_transaction_co2_saved_tons']} Tons CO2e", delta="Purchased Trades")

    st.markdown("---")

    # Category Filter
    cat_filter = st.selectbox("Filter Secondary Materials by Category", ["All", "Recycled Polymer Plastic", "Scrap Aluminum Alloy", "E-Waste Precious Metal Slag"])
    listings = engine.get_listings(cat_filter)

    # Plotly Visual
    df_mat = pd.DataFrame([m.__dict__ for m in listings])
    if not df_mat.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_mat['material_name'],
            y=df_mat['quantity_metric_tons'],
            name='Available Supply (Tons)',
            marker_color='#10b981'
        ))
        fig.update_layout(
            title="Secondary Material Supply Volume by Listing",
            xaxis_title="Material Listing",
            yaxis_title="Quantity (Metric Tons)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("📦 Active Secondary Raw Material Listings")
    st.dataframe(df_mat, use_container_width=True)

    # B2B Transaction History
    with st.expander("📜 View B2B Circular Material Transaction History"):
        df_tx = pd.DataFrame([t.__dict__ for t in engine.transactions])
        st.dataframe(df_tx, use_container_width=True)

if __name__ == "__main__":
    render_circular_economy_dashboard()
