"""
carbon_offsetting_module.py
====================================
Carbon Offsetting Module
Version: 1.0.0

This module provides comprehensive carbon offsetting functionality including:
- Educational content about carbon offsetting
- Estimation of offset requirements based on lifestyle inputs
- Information about offset methods and projects
- Tracking capabilities for future enhancements

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import json
import logging
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import random
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OffsetMethod(Enum):
    """Enumeration of carbon offset methods."""
    TREE_PLANTING = "tree_planting"
    RENEWABLE_ENERGY = "renewable_energy"
    ENERGY_EFFICIENCY = "energy_efficiency"
    METHANE_CAPTURE = "methane_capture"
    FOREST_CONSERVATION = "forest_conservation"
    SOIL_CARBON = "soil_carbon"
    BLUE_CARBON = "blue_carbon"
    DIRECT_AIR_CAPTURE = "direct_air_capture"
    BIOCHAR = "biochar"
    OCEAN_ALKALINITY = "ocean_alkalinity"
    ENHANCED_WEATHERING = "enhanced_weathering"
    BAMBOO_PLANTING = "bamboo_planting"


class OffsetProjectStatus(Enum):
    """Enumeration of project statuses."""
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class OffsetVerificationStandard(Enum):
    """Enumeration of verification standards."""
    VERRA = "verra_vcs"
    GOLD_STANDARD = "gold_standard"
    CAR = "climate_action_reserve"
    ACR = "american_carbon_register"
    CCB = "climate_community_biodiversity"
    CDM = "clean_development_mechanism"


@dataclass
class CarbonOffsetProject:
    """Data class representing a carbon offset project."""
    project_id: str
    project_name: str
    project_description: str
    method: OffsetMethod
    location: str
    country: str
    status: OffsetProjectStatus
    verification_standard: Optional[OffsetVerificationStandard] = None
    verified_credits: float = 0.0
    total_credits: float = 0.0
    price_per_credit_usd: float = 10.0
    co2_removed_per_credit_kg: float = 1000.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    website: Optional[str] = None
    additional_benefits: List[str] = field(default_factory=list)
    certification_details: Dict[str, Any] = field(default_factory=dict)
    community_impact_score: float = 0.0
    biodiversity_impact_score: float = 0.0
    social_impact_score: float = 0.0


@dataclass
class OffsetRequirement:
    """Data class representing carbon offset requirements."""
    total_annual_emissions_kg: float
    recommended_offsets_kg: float
    minimum_offsets_kg: float
    suggested_offset_methods: List[OffsetMethod]
    estimated_cost_usd: float
    recommended_projects: List[CarbonOffsetProject]
    offset_breakdown: Dict[str, float]  # Category -> emissions
    confidence_level: float  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OffsetPurchase:
    """Data class representing an offset purchase."""
    purchase_id: str
    user_id: str
    project_id: str
    credits_purchased: float
    total_cost_usd: float
    purchase_date: datetime
    verification_code: Optional[str] = None
    certificate_url: Optional[str] = None
    status: str = "pending"
    carbon_equivalent_removed_kg: float = 0.0


@dataclass
class OffsetTracking:
    """Data class for tracking offset progress."""
    user_id: str
    year: int
    total_emissions_kg: float
    total_offsets_kg: float
    offset_percentage: float
    projects_supported: List[str]
    monthly_breakdown: Dict[str, Dict[str, float]]
    goals: Dict[str, Any]
    achievements: List[str]
    next_milestone: Optional[Dict[str, Any]] = None


class CarbonOffsettingEducation:
    """
    Educational content about carbon offsetting.
    """
    
    @staticmethod
    def get_offsetting_explanation() -> Dict[str, Any]:
        """
        Returns comprehensive explanation of carbon offsetting.
        
        Returns:
            Dictionary with educational content
        """
        return {
            "title": "Understanding Carbon Offsetting",
            "description": "Carbon offsetting is a process of compensating for carbon emissions by funding projects that reduce or remove greenhouse gases from the atmosphere.",
            "key_concepts": {
                "what_is_offsetting": "Carbon offsetting allows individuals and organizations to balance their unavoidable emissions by supporting emissions reduction projects elsewhere.",
                "how_it_works": "One carbon credit typically represents one metric ton of CO2 equivalent (CO2e) that has been reduced or removed from the atmosphere.",
                "why_its_important": "Offsetting helps accelerate the transition to a low-carbon economy while addressing unavoidable emissions in the short term.",
                "when_to_offset": "Offsetting should be combined with direct emissions reduction efforts, not used as a substitute for them."
            },
            "offset_methods": {
                "nature_based": [
                    "Reforestation and afforestation projects",
                    "Forest conservation and REDD+ projects",
                    "Blue carbon projects (mangroves, seagrass, salt marshes)",
                    "Soil carbon sequestration through regenerative agriculture",
                    "Bamboo planting for carbon capture"
                ],
                "technology_based": [
                    "Renewable energy projects (solar, wind, hydro)",
                    "Energy efficiency improvements",
                    "Methane capture from landfills and agriculture",
                    "Direct air capture (DAC) technology",
                    "Biochar production and application",
                    "Enhanced weathering of rocks to capture CO2"
                ],
                "community_based": [
                    "Clean cookstove projects",
                    "Improved water purification systems",
                    "Sustainable agriculture practices",
                    "Community forestry projects"
                ]
            },
            "quality_criteria": [
                "Additionality: The project would not have happened without offset funding",
                "Permanence: The carbon reductions are permanent or long-lasting",
                "Leakage: The project does not simply shift emissions elsewhere",
                "Verification: The project is independently verified by recognized standards",
                "Co-benefits: The project provides social and environmental benefits beyond carbon"
            ],
            "verification_standards": {
                "Verra VCS": "The most widely used carbon offset standard globally.",
                "Gold Standard": "Known for rigorous environmental and social safeguards.",
                "Climate Action Reserve": "Focuses on US-based projects with high integrity.",
                "American Carbon Register": "Offers comprehensive carbon accounting.",
                "CCB Standards": "Integrates climate, community, and biodiversity benefits."
            },
            "common_misconceptions": [
                "Offsetting is not a solution for continuing high emissions; it's a complement to reduction.",
                "Not all offsets are created equal; quality varies significantly.",
                "Offset prices should reflect true environmental and social costs.",
                "Tree planting alone is insufficient for climate goals; multiple strategies needed."
            ]
        }
    
    @staticmethod
    def get_offsetting_faq() -> List[Dict[str, str]]:
        """
        Returns frequently asked questions about carbon offsetting.
        
        Returns:
            List of FAQ dictionaries
        """
        return [
            {
                "question": "What is a carbon credit?",
                "answer": "A carbon credit represents one metric ton of carbon dioxide equivalent (CO2e) that has been reduced, avoided, or removed from the atmosphere through a verified project."
            },
            {
                "question": "How much does carbon offsetting typically cost?",
                "answer": "Carbon offset prices vary widely from $5-50 per ton of CO2e. High-quality offsets with additional co-benefits typically cost $15-30 per ton."
            },
            {
                "question": "Is carbon offsetting effective for climate change?",
                "answer": "When done properly with verified, additional projects, carbon offsetting can contribute meaningfully to climate goals. However, it should be part of a broader strategy that prioritizes emissions reduction."
            },
            {
                "question": "How do I choose a high-quality offset project?",
                "answer": "Look for projects with independent verification (VCS, Gold Standard), additional co-benefits, transparent reporting, and proven additionality. Consider projects that align with your values and interests."
            },
            {
                "question": "What are co-benefits of carbon offset projects?",
                "answer": "Co-benefits include biodiversity conservation, community development, job creation, improved air quality, water conservation, and enhanced ecosystem services."
            },
            {
                "question": "Can I offset my entire carbon footprint?",
                "answer": "Yes, but it's recommended to first reduce emissions as much as possible before offsetting the remainder. Many calculators can help determine your remaining unavoidable emissions."
            }
        ]
    
    @staticmethod
    def get_offset_method_details(method: OffsetMethod) -> Dict[str, Any]:
        """
        Returns detailed information about a specific offset method.
        
        Args:
            method: OffsetMethod enum
            
        Returns:
            Dictionary with method details
        """
        details = {
            OffsetMethod.TREE_PLANTING: {
                "name": "Tree Planting / Reforestation",
                "description": "Planting trees in degraded areas to absorb CO2 as they grow.",
                "typical_cost": "$5-20 per ton CO2e",
                "removal_rate": "100-1000 kg CO2e per tree over 30 years",
                "co_benefits": ["Biodiversity", "Soil conservation", "Water cycle regulation", "Livelihoods"],
                "challenges": ["Long timeline", "Fire risk", "Monitoring complexity"],
                "duration": "25-100 years",
                "carbon_removal_efficiency": 0.75
            },
            OffsetMethod.RENEWABLE_ENERGY: {
                "name": "Renewable Energy Projects",
                "description": "Funding solar, wind, hydro, or geothermal energy projects to replace fossil fuel energy.",
                "typical_cost": "$5-15 per ton CO2e",
                "removal_rate": "Varies by project size and displacement",
                "co_benefits": ["Energy access", "Air quality", "Job creation", "Energy independence"],
                "challenges": ["Intermittency", "Land use", "Grid integration"],
                "duration": "15-30 years",
                "carbon_removal_efficiency": 0.85
            },
            OffsetMethod.ENERGY_EFFICIENCY: {
                "name": "Energy Efficiency Improvements",
                "description": "Projects that improve energy efficiency in buildings, industries, or transportation.",
                "typical_cost": "$3-12 per ton CO2e",
                "removal_rate": "Varies by project type and implementation",
                "co_benefits": ["Cost savings", "Comfort", "Productivity", "Health"],
                "challenges": ["High upfront costs", "Behavioral change needed", "Monitoring"],
                "duration": "10-25 years",
                "carbon_removal_efficiency": 0.90
            },
            OffsetMethod.METHANE_CAPTURE: {
                "name": "Methane Capture Projects",
                "description": "Capturing methane from landfills, agriculture, or wastewater for energy production.",
                "typical_cost": "$8-25 per ton CO2e",
                "removal_rate": "High immediate impact",
                "co_benefits": ["Waste management", "Energy recovery", "Odor reduction", "Water quality"],
                "challenges": ["Infrastructure costs", "Leak detection", "Maintenance"],
                "duration": "15-20 years",
                "carbon_removal_efficiency": 0.95
            },
            OffsetMethod.FOREST_CONSERVATION: {
                "name": "Forest Conservation / REDD+",
                "description": "Preventing deforestation and forest degradation to maintain carbon stores.",
                "typical_cost": "$8-30 per ton CO2e",
                "removal_rate": "Prevents 100-1000 tons CO2e per hectare over time",
                "co_benefits": ["Biodiversity", "Indigenous rights", "Ecosystem services", "Climate regulation"],
                "challenges": ["Leakage concerns", "Governance issues", "Additionally verification"],
                "duration": "20-50 years",
                "carbon_removal_efficiency": 0.70
            },
            OffsetMethod.SOIL_CARBON: {
                "name": "Soil Carbon Sequestration",
                "description": "Increasing soil organic carbon through regenerative agriculture practices.",
                "typical_cost": "$10-40 per ton CO2e",
                "removal_rate": "0.5-2 tons CO2e per hectare per year",
                "co_benefits": ["Soil health", "Water retention", "Crop resilience", "Biodiversity"],
                "challenges": ["Measurement complexity", "Monitoring costs", "Potential reversibility"],
                "duration": "10-50 years",
                "carbon_removal_efficiency": 0.65
            },
            OffsetMethod.BLUE_CARBON: {
                "name": "Blue Carbon Projects",
                "description": "Restoring and protecting coastal ecosystems like mangroves, seagrass, and salt marshes.",
                "typical_cost": "$15-50 per ton CO2e",
                "removal_rate": "Mangroves: 1000-3000 tons CO2e per hectare over 25 years",
                "co_benefits": ["Coastal protection", "Biodiversity", "Fisheries", "Water quality"],
                "challenges": ["Saltwater intrusion", "Sea level rise", "Limited land availability"],
                "duration": "20-50 years",
                "carbon_removal_efficiency": 0.80
            },
            OffsetMethod.DIRECT_AIR_CAPTURE: {
                "name": "Direct Air Capture (DAC)",
                "description": "Using technology to capture CO2 directly from the atmosphere.",
                "typical_cost": "$100-600 per ton CO2e",
                "removal_rate": "Varies by technology scale",
                "co_benefits": ["Technological innovation", "Carbon utilization", "Permanence"],
                "challenges": ["High energy input", "Cost", "Scale-up challenges"],
                "duration": "Permanent storage",
                "carbon_removal_efficiency": 0.95
            },
            OffsetMethod.BIOCHAR: {
                "name": "Biochar Production",
                "description": "Creating stable carbon from biomass and applying it to soil.",
                "typical_cost": "$20-60 per ton CO2e",
                "removal_rate": "1-3 kg CO2e per kg biochar",
                "co_benefits": ["Soil fertility", "Water retention", "Crop yields", "Waste management"],
                "challenges": ["Feedstock availability", "Quality control", "Soil impacts"],
                "duration": "100-1000+ years",
                "carbon_removal_efficiency": 0.85
            },
            OffsetMethod.BAMBOO_PLANTING: {
                "name": "Bamboo Planting Projects",
                "description": "Planting bamboo species for rapid carbon sequestration and sustainable materials.",
                "typical_cost": "$15-35 per ton CO2e",
                "removal_rate": "Bamboo can sequester 20-25 tons CO2e per hectare per year",
                "co_benefits": ["Rapid growth", "Soil stabilization", "Economic opportunities", "Biodiversity"],
                "challenges": ["Invasive potential", "Water demands", "Harvest timing"],
                "duration": "10-30 years",
                "carbon_removal_efficiency": 0.90
            }
        }
        return details.get(method, {"description": "Method details not available"})


class OffsetRequirementEstimator:
    """
    Estimates carbon offset requirements based on lifestyle emissions.
    """
    
    def __init__(self):
        self._education = CarbonOffsettingEducation()
        self._projects = self._initialize_projects()
        self._offset_costs = {
            OffsetMethod.TREE_PLANTING: 12.50,
            OffsetMethod.RENEWABLE_ENERGY: 8.75,
            OffsetMethod.ENERGY_EFFICIENCY: 7.50,
            OffsetMethod.METHANE_CAPTURE: 15.00,
            OffsetMethod.FOREST_CONSERVATION: 18.00,
            OffsetMethod.SOIL_CARBON: 25.00,
            OffsetMethod.BLUE_CARBON: 30.00,
            OffsetMethod.DIRECT_AIR_CAPTURE: 250.00,
            OffsetMethod.BIOCHAR: 35.00,
            OffsetMethod.OCEAN_ALKALINITY: 40.00,
            OffsetMethod.ENHANCED_WEATHERING: 45.00,
            OffsetMethod.BAMBOO_PLANTING: 20.00
        }
    
    def _initialize_projects(self) -> List[CarbonOffsetProject]:
        """
        Initializes sample carbon offset projects.
        
        Returns:
            List of CarbonOffsetProject objects
        """
        return [
            CarbonOffsetProject(
                project_id="P001",
                project_name="Amazon Rainforest Conservation",
                project_description="Protecting 50,000 hectares of Amazon rainforest from deforestation and degradation.",
                method=OffsetMethod.FOREST_CONSERVATION,
                location="Amazon Basin",
                country="Brazil",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.VERRA,
                verified_credits=250000,
                total_credits=500000,
                price_per_credit_usd=18.00,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2020, 1, 1),
                end_date=datetime(2050, 12, 31),
                website="https://example.com/amazon-conservation",
                additional_benefits=["Biodiversity protection", "Indigenous community support", "Climate regulation"],
                community_impact_score=8.5,
                biodiversity_impact_score=9.5,
                social_impact_score=8.0
            ),
            CarbonOffsetProject(
                project_id="P002",
                project_name="Great Plains Wind Farm",
                project_description="Large-scale wind energy project displacing fossil fuel electricity generation.",
                method=OffsetMethod.RENEWABLE_ENERGY,
                location="Great Plains",
                country="USA",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.GOLD_STANDARD,
                verified_credits=1000000,
                total_credits=2000000,
                price_per_credit_usd=8.75,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2018, 6, 1),
                end_date=datetime(2038, 5, 31),
                website="https://example.com/great-plains-wind",
                additional_benefits=["Clean energy", "Job creation", "Energy independence"],
                community_impact_score=7.5,
                biodiversity_impact_score=6.0,
                social_impact_score=8.0
            ),
            CarbonOffsetProject(
                project_id="P003",
                project_name="Mangrove Restoration Project",
                project_description="Restoring coastal mangrove ecosystems in Southeast Asia for carbon capture and coastal protection.",
                method=OffsetMethod.BLUE_CARBON,
                location="Coastal Region",
                country="Indonesia",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.CCB,
                verified_credits=50000,
                total_credits=150000,
                price_per_credit_usd=30.00,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2019, 3, 1),
                end_date=datetime(2049, 2, 28),
                website="https://example.com/mangrove-restoration",
                additional_benefits=["Coastal protection", "Fishery enhancement", "Biodiversity", "Community livelihoods"],
                community_impact_score=8.0,
                biodiversity_impact_score=9.0,
                social_impact_score=8.5
            ),
            CarbonOffsetProject(
                project_id="P004",
                project_name="Landfill Methane Capture",
                project_description="Capturing methane from municipal landfills for electricity generation.",
                method=OffsetMethod.METHANE_CAPTURE,
                location="Metropolitan Area",
                country="India",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.CDM,
                verified_credits=300000,
                total_credits=600000,
                price_per_credit_usd=15.00,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2017, 8, 1),
                end_date=datetime(2037, 7, 31),
                website="https://example.com/methane-capture",
                additional_benefits=["Waste reduction", "Renewable energy", "Air quality", "Job creation"],
                community_impact_score=7.0,
                biodiversity_impact_score=5.5,
                social_impact_score=7.5
            ),
            CarbonOffsetProject(
                project_id="P005",
                project_name="Biochar Initiative for Africa",
                project_description="Producing biochar from agricultural waste and applying it to improve soil health.",
                method=OffsetMethod.BIOCHAR,
                location="Agricultural Region",
                country="Kenya",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.GOLD_STANDARD,
                verified_credits=40000,
                total_credits=100000,
                price_per_credit_usd=35.00,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2021, 1, 1),
                end_date=datetime(2041, 12, 31),
                website="https://example.com/biochar-africa",
                additional_benefits=["Soil health", "Crop yields", "Waste management", "Community income"],
                community_impact_score=9.0,
                biodiversity_impact_score=7.5,
                social_impact_score=9.0
            ),
            CarbonOffsetProject(
                project_id="P006",
                project_name="Bamboo for Carbon Capture",
                project_description="Planting bamboo forests to sequester carbon rapidly while providing sustainable materials.",
                method=OffsetMethod.BAMBOO_PLANTING,
                location="Tropical Region",
                country="Vietnam",
                status=OffsetProjectStatus.ACTIVE,
                verification_standard=OffsetVerificationStandard.VERRA,
                verified_credits=25000,
                total_credits=75000,
                price_per_credit_usd=20.00,
                co2_removed_per_credit_kg=1000,
                start_date=datetime(2022, 6, 1),
                end_date=datetime(2052, 5, 31),
                website="https://example.com/bamboo-carbon",
                additional_benefits=["Rapid growth", "Soil stabilization", "Local employment", "Sustainable materials"],
                community_impact_score=7.5,
                biodiversity_impact_score=7.0,
                social_impact_score=8.0
            )
        ]
    
    def estimate_offset_requirements(self, emissions_breakdown: Dict[str, float], 
                                    lifestyle_category: str = "individual") -> OffsetRequirement:
        """
        Estimates offset requirements based on emissions breakdown.
        
        Args:
            emissions_breakdown: Dictionary of emission categories and values in kg CO2e
            lifestyle_category: Type of lifestyle (individual, household, business)
            
        Returns:
            OffsetRequirement object
        """
        total_emissions = sum(emissions_breakdown.values())
        
        # Calculate recommended offsets (typically 100% of emissions after considering reduction potential)
        # For individuals, we recommend offsetting 50-100% depending on lifestyle
        reduction_factor = 0.7 if lifestyle_category == "individual" else 0.6
        if lifestyle_category == "business":
            reduction_factor = 0.5
        
        recommended_offsets = total_emissions * reduction_factor
        minimum_offsets = total_emissions * 0.3  # Minimum 30% offset recommendation
        
        # Determine suggested offset methods based on emission categories
        suggested_methods = []
        
        # Energy-related emissions → Renewable Energy or Energy Efficiency
        if emissions_breakdown.get('energy', 0) > total_emissions * 0.2:
            suggested_methods.extend([OffsetMethod.RENEWABLE_ENERGY, OffsetMethod.ENERGY_EFFICIENCY])
        
        # Transportation-related emissions → Renewable Energy or Tree Planting
        if emissions_breakdown.get('transportation', 0) > total_emissions * 0.15:
            suggested_methods.append(OffsetMethod.TREE_PLANTING)
        
        # Food-related emissions → Soil Carbon or Biochar
        if emissions_breakdown.get('food', 0) > total_emissions * 0.1:
            suggested_methods.extend([OffsetMethod.SOIL_CARBON, OffsetMethod.BIOCHAR])
        
        # Ensure we have at least some methods
        if not suggested_methods:
            suggested_methods = [OffsetMethod.TREE_PLANTING, OffsetMethod.RENEWABLE_ENERGY]
        
        # Limit to top 3 methods
        suggested_methods = list(set(suggested_methods))[:3]
        
        # Calculate estimated cost
        avg_cost_per_ton = sum(self._offset_costs.get(m, 15.0) for m in suggested_methods) / len(suggested_methods)
        estimated_cost = (recommended_offsets / 1000) * avg_cost_per_ton
        
        # Get recommended projects
        recommended_projects = self._select_projects(suggested_methods, recommended_offsets)
        
        # Calculate confidence level based on emissions data completeness
        confidence_level = min(1.0, len(emissions_breakdown) / 10)
        
        return OffsetRequirement(
            total_annual_emissions_kg=total_emissions,
            recommended_offsets_kg=recommended_offsets,
            minimum_offsets_kg=minimum_offsets,
            suggested_offset_methods=suggested_methods,
            estimated_cost_usd=estimated_cost,
            recommended_projects=recommended_projects,
            offset_breakdown=emissions_breakdown,
            confidence_level=confidence_level
        )
    
    def _select_projects(self, methods: List[OffsetMethod], offset_amount: float) -> List[CarbonOffsetProject]:
        """
        Selects appropriate projects based on methods and offset amount.
        
        Args:
            methods: List of preferred offset methods
            offset_amount: Amount of offset required in kg
            
        Returns:
            List of CarbonOffsetProject objects
        """
        selected_projects = []
        
        # Filter projects by method
        available_projects = [p for p in self._projects if p.method in methods]
        
        if not available_projects:
            # Fall back to all active projects
            available_projects = [p for p in self._projects if p.status == OffsetProjectStatus.ACTIVE]
        
        # Sort by price and availability
        available_projects.sort(key=lambda x: x.price_per_credit_usd)
        
        # Select projects to meet offset amount
        remaining_offset = offset_amount
        for project in available_projects:
            if remaining_offset <= 0:
                break
            
            # How many credits can we buy from this project?
            credits_needed = min(
                remaining_offset / project.co2_removed_per_credit_kg,
                project.total_credits - project.verified_credits
            )
            
            if credits_needed > 0:
                # Create a partial project representation
                partial_project = CarbonOffsetProject(
                    project_id=project.project_id,
                    project_name=project.project_name,
                    project_description=project.project_description,
                    method=project.method,
                    location=project.location,
                    country=project.country,
                    status=project.status,
                    verification_standard=project.verification_standard,
                    verified_credits=project.verified_credits,
                    total_credits=credits_needed,
                    price_per_credit_usd=project.price_per_credit_usd,
                    co2_removed_per_credit_kg=project.co2_removed_per_credit_kg,
                    additional_benefits=project.additional_benefits,
                    community_impact_score=project.community_impact_score,
                    biodiversity_impact_score=project.biodiversity_impact_score,
                    social_impact_score=project.social_impact_score
                )
                selected_projects.append(partial_project)
                remaining_offset -= credits_needed * project.co2_removed_per_credit_kg
        
        return selected_projects[:3]  # Return top 3 projects
    
    def get_offset_cost_estimate(self, emissions_kg: float, 
                               preferred_methods: List[OffsetMethod] = None) -> Dict[str, float]:
        """
        Estimates offset cost for a given emission amount.
        
        Args:
            emissions_kg: Emissions in kilograms
            preferred_methods: List of preferred offset methods
            
        Returns:
            Dictionary with cost estimates
        """
        if preferred_methods is None:
            preferred_methods = [OffsetMethod.TREE_PLANTING, OffsetMethod.RENEWABLE_ENERGY]
        
        costs = {}
        for method in preferred_methods:
            cost_per_ton = self._offset_costs.get(method, 15.0)
            total_cost = (emissions_kg / 1000) * cost_per_ton
            costs[method.value] = total_cost
        
        # Add average cost
        if costs:
            costs['average'] = sum(costs.values()) / len(costs)
        else:
            costs['average'] = (emissions_kg / 1000) * 15.0
        
        return costs


class OffsetPurchaseManager:
    """
    Manages carbon offset purchases and transactions.
    """
    
    def __init__(self):
        self.purchases: List[OffsetPurchase] = []
        self._purchase_counter = 0
    
    def purchase_credits(self, user_id: str, project: CarbonOffsetProject, 
                        credits: float, payment_method: str = "credit_card") -> OffsetPurchase:
        """
        Purchases carbon offset credits from a project.
        
        Args:
            user_id: User identifier
            project: CarbonOffsetProject to purchase from
            credits: Number of credits to purchase
            payment_method: Method of payment
            
        Returns:
            OffsetPurchase object
        """
        if credits <= 0:
            raise ValueError("Credits must be greater than 0")
        
        if credits > (project.total_credits - project.verified_credits):
            raise ValueError(f"Not enough credits available. Available: {project.total_credits - project.verified_credits}")
        
        total_cost = credits * project.price_per_credit_usd
        carbon_removed = credits * project.co2_removed_per_credit_kg
        
        self._purchase_counter += 1
        purchase = OffsetPurchase(
            purchase_id=f"PUR-{datetime.now().strftime('%Y%m%d')}-{self._purchase_counter:04d}",
            user_id=user_id,
            project_id=project.project_id,
            credits_purchased=credits,
            total_cost_usd=total_cost,
            purchase_date=datetime.now(),
            verification_code=f"VC-{random.randint(100000, 999999)}",
            certificate_url=f"https://certificates.example.com/purchase/{self._purchase_counter}",
            status="completed",
            carbon_equivalent_removed_kg=carbon_removed
        )
        
        self.purchases.append(purchase)
        logger.info(f"Purchase completed: {purchase.purchase_id} - {credits} credits from {project.project_name}")
        
        return purchase
    
    def get_user_purchase_history(self, user_id: str) -> List[OffsetPurchase]:
        """
        Gets purchase history for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of OffsetPurchase objects
        """
        return [p for p in self.purchases if p.user_id == user_id]
    
    def get_total_offset_credits(self, user_id: str) -> Dict[str, float]:
        """
        Gets total offset credits and carbon removed for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with totals
        """
        user_purchases = self.get_user_purchase_history(user_id)
        
        total_credits = sum(p.credits_purchased for p in user_purchases)
        total_cost = sum(p.total_cost_usd for p in user_purchases)
        total_carbon_removed = sum(p.carbon_equivalent_removed_kg for p in user_purchases)
        
        return {
            "total_credits": total_credits,
            "total_cost_usd": total_cost,
            "total_carbon_removed_kg": total_carbon_removed,
            "total_purchases": len(user_purchases)
        }


class OffsetTracker:
    """
    Tracks carbon offset progress and goals.
    """
    
    def __init__(self):
        self.tracking_data: Dict[str, OffsetTracking] = {}
    
    def initialize_tracking(self, user_id: str, yearly_emissions_kg: float) -> OffsetTracking:
        """
        Initializes tracking for a user.
        
        Args:
            user_id: User identifier
            yearly_emissions_kg: Annual emissions in kilograms
            
        Returns:
            OffsetTracking object
        """
        current_year = datetime.now().year
        
        tracking = OffsetTracking(
            user_id=user_id,
            year=current_year,
            total_emissions_kg=yearly_emissions_kg,
            total_offsets_kg=0.0,
            offset_percentage=0.0,
            projects_supported=[],
            monthly_breakdown={},
            goals={
                "annual_target_kg": yearly_emissions_kg * 0.7,
                "target_date": datetime(current_year, 12, 31),
                "priority_methods": [OffsetMethod.RENEWABLE_ENERGY.value, OffsetMethod.TREE_PLANTING.value]
            },
            achievements=[],
            next_milestone={
                "milestone_kg": yearly_emissions_kg * 0.25,
                "description": "Offset 25% of annual emissions",
                "completion_date": None
            }
        )
        
        self.tracking_data[user_id] = tracking
        return tracking
    
    def update_tracking(self, user_id: str, offsets_kg: float, project_ids: List[str]) -> OffsetTracking:
        """
        Updates tracking with new offsets.
        
        Args:
            user_id: User identifier
            offsets_kg: New offsets in kilograms
            project_ids: IDs of projects supported
            
        Returns:
            Updated OffsetTracking object
        """
        if user_id not in self.tracking_data:
            raise ValueError(f"Tracking not initialized for user {user_id}")
        
        tracking = self.tracking_data[user_id]
        tracking.total_offsets_kg += offsets_kg
        tracking.offset_percentage = (tracking.total_offsets_kg / tracking.total_emissions_kg) * 100
        
        # Update projects supported
        for project_id in project_ids:
            if project_id not in tracking.projects_supported:
                tracking.projects_supported.append(project_id)
        
        # Update monthly breakdown
        current_month = datetime.now().strftime("%Y-%m")
        if current_month not in tracking.monthly_breakdown:
            tracking.monthly_breakdown[current_month] = {"offsets_kg": 0, "emissions_kg": 0}
        tracking.monthly_breakdown[current_month]["offsets_kg"] += offsets_kg
        
        # Check achievements
        if tracking.offset_percentage >= 25 and "25% Offset Achievement" not in tracking.achievements:
            tracking.achievements.append("25% Offset Achievement")
        
        if tracking.offset_percentage >= 50 and "50% Offset Achievement" not in tracking.achievements:
            tracking.achievements.append("50% Offset Achievement")
        
        if tracking.offset_percentage >= 75 and "75% Offset Achievement" not in tracking.achievements:
            tracking.achievements.append("75% Offset Achievement")
        
        if tracking.offset_percentage >= 100 and "Carbon Neutral Achievement" not in tracking.achievements:
            tracking.achievements.append("Carbon Neutral Achievement")
        
        # Update next milestone
        milestones = [0.25, 0.50, 0.75, 1.0]
        for milestone in milestones:
            if tracking.offset_percentage < milestone * 100:
                tracking.next_milestone = {
                    "milestone_kg": tracking.total_emissions_kg * milestone,
                    "description": f"Offset {int(milestone * 100)}% of annual emissions",
                    "completion_date": None
                }
                break
        
        self.tracking_data[user_id] = tracking
        return tracking
    
    def get_tracking_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Gets tracking summary for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with tracking summary
        """
        if user_id not in self.tracking_data:
            return {"message": "No tracking data found for this user"}
        
        tracking = self.tracking_data[user_id]
        
        return {
            "user_id": tracking.user_id,
            "year": tracking.year,
            "total_emissions_kg": tracking.total_emissions_kg,
            "total_offsets_kg": tracking.total_offsets_kg,
            "offset_percentage": tracking.offset_percentage,
            "projects_supported_count": len(tracking.projects_supported),
            "projects_supported": tracking.projects_supported,
            "achievements": tracking.achievements,
            "next_milestone": tracking.next_milestone,
            "goals": tracking.goals
        }
    
    def generate_offset_progress_report(self, user_id: str) -> str:
        """
        Generates a progress report for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Progress report as string
        """
        summary = self.get_tracking_summary(user_id)
        if "message" in summary:
            return summary["message"]
        
        report = []
        report.append("=" * 60)
        report.append(f"  CARBON OFFSET PROGRESS REPORT - {user_id}")
        report.append("=" * 60)
        report.append(f"  Year: {summary['year']}")
        report.append(f"  Total Annual Emissions: {summary['total_emissions_kg']:,.0f} kg CO2e")
        report.append(f"  Total Offsets Purchased: {summary['total_offsets_kg']:,.0f} kg CO2e")
        report.append(f"  Offset Percentage: {summary['offset_percentage']:.1f}%")
        report.append(f"  Projects Supported: {summary['projects_supported_count']}")
        report.append("")
        report.append(f"  Achievements: {', '.join(summary['achievements']) if summary['achievements'] else 'None yet'}")
        report.append("")
        if summary['next_milestone']:
            report.append(f"  Next Milestone: {summary['next_milestone']['description']}")
            report.append(f"  Target: {summary['next_milestone']['milestone_kg']:,.0f} kg")
        report.append("")
        report.append("  Goals:")
        for goal, value in summary['goals'].items():
            if isinstance(value, float):
                report.append(f"    - {goal}: {value:,.0f}")
            else:
                report.append(f"    - {goal}: {value}")
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


class CarbonOffsettingMain:
    """
    Main class for carbon offsetting functionality.
    """
    
    def __init__(self):
        self.education = CarbonOffsettingEducation()
        self.estimator = OffsetRequirementEstimator()
        self.purchase_manager = OffsetPurchaseManager()
        self.tracker = OffsetTracker()
    
    def get_comprehensive_offset_info(self) -> Dict[str, Any]:
        """
        Returns comprehensive information about carbon offsetting.
        
        Returns:
            Dictionary with comprehensive offsetting information
        """
        return {
            "education": self.education.get_offsetting_explanation(),
            "faq": self.education.get_offsetting_faq(),
            "methods": {
                method.value: self.education.get_offset_method_details(method)
                for method in OffsetMethod
            },
            "available_projects": self.estimator._projects,
            "pricing": self.estimator._offset_costs
        }
    
    def estimate_and_recommend(self, emissions_breakdown: Dict[str, float], 
                               lifestyle_category: str = "individual") -> Dict[str, Any]:
        """
        Estimates offset requirements and provides recommendations.
        
        Args:
            emissions_breakdown: Dictionary of emission categories and values
            lifestyle_category: Type of lifestyle
            
        Returns:
            Dictionary with estimates and recommendations
        """
        requirement = self.estimator.estimate_offset_requirements(
            emissions_breakdown, lifestyle_category
        )
        
        return {
            "requirement": requirement,
            "total_annual_emissions_kg": requirement.total_annual_emissions_kg,
            "recommended_offsets_kg": requirement.recommended_offsets_kg,
            "estimated_cost_usd": requirement.estimated_cost_usd,
            "suggested_methods": [m.value for m in requirement.suggested_offset_methods],
            "recommended_projects": [
                {
                    "name": p.project_name,
                    "method": p.method.value,
                    "price": p.price_per_credit_usd,
                    "verification": p.verification_standard.value if p.verification_standard else None
                }
                for p in requirement.recommended_projects
            ],
            "confidence_level": requirement.confidence_level,
            "offset_breakdown": requirement.offset_breakdown
        }


# ============ EXAMPLE USAGE AND TESTING FUNCTIONS ============

def test_carbon_offsetting():
    """
    Test function for carbon offsetting module.
    """
    print("\n" + "=" * 60)
    print("  CARBON OFFSETTING MODULE TEST")
    print("=" * 60)
    
    # Initialize main class
    offsetting = CarbonOffsettingMain()
    
    # Sample emissions breakdown
    emissions_breakdown = {
        "energy": 5000.0,
        "transportation": 3000.0,
        "food": 2000.0,
        "waste": 1000.0,
        "water": 500.0,
        "shopping": 1500.0,
        "housing": 2000.0
    }
    
    # Get education
    print("\n📚 EDUCATIONAL CONTENT")
    print("-" * 40)
    education = offsetting.education.get_offsetting_explanation()
    print(f"Title: {education['title']}")
    print(f"Description: {education['description'][:100]}...")
    
    # Get FAQ
    print("\n❓ FREQUENTLY ASKED QUESTIONS")
    print("-" * 40)
    faq = offsetting.education.get_offsetting_faq()
    for i, q in enumerate(faq[:3], 1):
        print(f"{i}. Q: {q['question']}")
        print(f"   A: {q['answer'][:100]}...")
    
    # Estimate offsets
    print("\n📊 OFFSET REQUIREMENT ESTIMATION")
    print("-" * 40)
    result = offsetting.estimate_and_recommend(emissions_breakdown)
    print(f"Total Annual Emissions: {result['total_annual_emissions_kg']:,.0f} kg CO2e")
    print(f"Recommended Offsets: {result['recommended_offsets_kg']:,.0f} kg CO2e")
    print(f"Estimated Cost: ${result['estimated_cost_usd']:.2f}")
    print(f"Suggested Methods: {', '.join(result['suggested_methods'])}")
    print(f"Confidence Level: {result['confidence_level'] * 100:.0f}%")
    
    # Purchase credits
    print("\n🛒 PURCHASE CREDITS")
    print("-" * 40)
    project = offsetting.estimator._projects[0]
    purchase = offsetting.purchase_manager.purchase_credits(
        "user123", project, 5.0
    )
    print(f"Purchase ID: {purchase.purchase_id}")
    print(f"Credits: {purchase.credits_purchased}")
    print(f"Cost: ${purchase.total_cost_usd:.2f}")
    print(f"Carbon Removed: {purchase.carbon_equivalent_removed_kg:,.0f} kg")
    print(f"Verification Code: {purchase.verification_code}")
    
    # Track progress
    print("\n📈 TRACKING PROGRESS")
    print("-" * 40)
    tracking = offsetting.tracker.initialize_tracking("user123", 15000.0)
    print(f"Initial Offset Percentage: {tracking.offset_percentage:.1f}%")
    
    tracking = offsetting.tracker.update_tracking("user123", 5000.0, ["P001"])
    print(f"Updated Offset Percentage: {tracking.offset_percentage:.1f}%")
    print(f"Achievements: {', '.join(tracking.achievements)}")
    
    # Generate report
    print("\n📋 PROGRESS REPORT")
    print("-" * 40)
    report = offsetting.tracker.generate_offset_progress_report("user123")
    print(report)
    
    # Get method details
    print("\n🌳 OFFSET METHOD DETAILS")
    print("-" * 40)
    method_details = offsetting.education.get_offset_method_details(OffsetMethod.TREE_PLANTING)
    print(f"Method: {method_details['name']}")
    print(f"Description: {method_details['description']}")
    print(f"Typical Cost: {method_details['typical_cost']}")
    print(f"Co-benefits: {', '.join(method_details['co_benefits'])}")
    
    print("\n✅ Carbon offsetting module test completed successfully!")
    print("=" * 60)


def main():
    """Main function to run the carbon offsetting module."""
    test_carbon_offsetting()


if __name__ == "__main__":
    main()
