"""Mock data generator and calculation utilities for Carbon Offset Marketplace."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.carbon.offset_types import (
    OffsetProject, OffsetPurchase, UserOffsetPortfolio, OffsetImpact,
    MarketplaceStats, OffsetCategory, ProjectStatus, VerificationStandard,
    TransactionStatus, CATEGORY_COLORS,
)


def generate_id(prefix: str, seed: int = None) -> str:
    """Generate a deterministic ID."""
    if seed is not None:
        h = hashlib.md5(f"{prefix}_{seed}".encode()).hexdigest()[:8]
    else:
        h = hashlib.md5(f"{prefix}_{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{h}"


def calculate_offset_impact(tons: float) -> OffsetImpact:
    """Calculate equivalent impact metrics from tons of CO2 offset."""
    return OffsetImpact(
        trees_planted=int(tons * 15),
        homes_powered=int(tons * 0.12),
        cars_removed=int(tons * 0.22),
        flights_offset=int(tons * 0.53),
        swimming_pools_saved=int(tons * 0.4),
        co2_saved_tons=round(tons, 2),
        equivalent_years_driving=round(tons * 0.22, 1),
    )


def generate_mock_projects(count: int = 16) -> List[OffsetProject]:
    """Generate mock offset projects."""
    projects_data = [
        ("Amazon Rainforest Conservation", "Protect 50,000 hectares of primary rainforest in the Brazilian Amazon from deforestation, preserving biodiversity and indigenous communities.", OffsetCategory.FORESTRY, "Brazil", "South America", VerificationStandard.GOLD_STANDARD, 12.50, 50000, 32000, 400000, 625000, 25000, ["forest", "biodiversity", "indigenous"]),
        ("Kenya Solar Farm", "Build and operate a 50MW solar farm in rural Kenya, providing clean electricity to 100,000+ households and displacing diesel generators.", OffsetCategory.RENEWABLE_ENERGY, "Kenya", "Africa", VerificationStandard.VCS, 8.75, 30000, 18000, 157500, 262500, 15000, ["solar", "energy access", "rural"]),
        ("India Clean Cookstove", "Distribute 100,000 efficient cookstoves to rural Indian families, reducing indoor air pollution and deforestation for fuelwood.", OffsetCategory.COOKSTOVE, "India", "Asia", VerificationStandard.GOLD_STANDARD, 6.25, 20000, 14000, 87500, 125000, 10000, ["health", "women", "clean air"]),
        ("Oregon Forest Carbon", "Reforest 2,000 acres of degraded timber land in Oregon with native species, creating wildlife corridors and carbon sinks.", OffsetCategory.FORESTRY, "United States", "North America", VerificationStandard.CARBON_TRUST, 18.00, 15000, 8500, 153000, 270000, 7500, ["reforestation", "wildlife", "native species"]),
        ("Methane Capture — Chile", "Install methane capture systems at three landfills in Chile, converting waste gas to electricity for local communities.", OffsetCategory.METHANE_CAPTURE, "Chile", "South America", VerificationStandard.VCS, 9.50, 25000, 20000, 190000, 237500, 12500, ["waste", "energy", "methane"]),
        ("Congo Basin Protection", "Protect 80,000 hectares of peatland forest in the Congo Basin, one of the world's largest tropical peatland complexes.", OffsetCategory.FORESTRY, "DR Congo", "Africa", VerificationStandard.GOLD_STANDARD, 14.00, 40000, 12000, 168000, 560000, 20000, ["peatland", "biodiversity", "climate"]),
        ("Morocco Wind Farm", "Develop a 100MW wind farm in Morocco's Atlas Mountains, powering 200,000 homes with clean energy.", OffsetCategory.RENEWABLE_ENERGY, "Morocco", "Africa", VerificationStandard.VCS, 7.25, 35000, 22000, 159250, 253750, 17500, ["wind", "energy", "homes"]),
        ("Borneo Peatland Restoration", "Restore 10,000 hectares of degraded peatland in Borneo, rewetting drained areas to prevent fires and carbon release.", OffsetCategory.FORESTRY, "Indonesia", "Asia", VerificationStandard.VCS, 11.00, 20000, 9000, 99000, 220000, 10000, ["peatland", "fire prevention", "restoration"]),
        ("Colombia Efficient Stoves", "Replace open-fire cooking with LPG stoves in 50,000 Colombian households, reducing deforestation and respiratory illness.", OffsetCategory.COOKSTOVE, "Colombia", "South America", VerificationStandard.GOLD_STANDARD, 5.50, 18000, 12000, 66000, 99000, 9000, ["health", "LPG", "deforestation"]),
        ("Pacific Blue Carbon", "Restore 500 hectares of mangrove forests along the Pacific coast, sequestering carbon and protecting coastlines.", OffsetCategory.OCEAN, "Ecuador", "South America", VerificationStandard.Plan_VIVO, 22.00, 8000, 3200, 70400, 176000, 4000, ["mangrove", "coastal", "blue carbon"]),
        ("Sahel Agroforestry", "Plant 2 million drought-resistant trees across the Sahel region, combining agriculture with carbon sequestration.", OffsetCategory.AGRICULTURE, "Niger", "Africa", VerificationStandard.VCS, 4.75, 60000, 35000, 166250, 285000, 30000, ["agroforestry", "drought", "food security"]),
        ("Iceland Geothermal", "Expand geothermal heating in rural Icelandic communities, replacing fossil fuel heating systems.", OffsetCategory.RENEWABLE_ENERGY, "Iceland", "Europe", VerificationStandard.CARBON_TRUST, 15.50, 12000, 7000, 108500, 186000, 6000, ["geothermal", "heating", "rural"]),
        ("Nepal Micro-Hydro", "Install 200 micro-hydro systems in remote Nepali villages, providing reliable clean electricity off-grid.", OffsetCategory.RENEWABLE_ENERGY, "Nepal", "Asia", VerificationStandard.GOLD_STANDARD, 9.00, 25000, 16000, 144000, 225000, 12500, ["hydro", "off-grid", "villages"]),
        ("Australian Savanna Burning", "Implement traditional fire management in Australian savannas, reducing late-season wildfires and greenhouse gas emissions.", OffsetCategory.AGRICULTURE, "Australia", "Oceania", VerificationStandard.VCS, 13.25, 15000, 8000, 106000, 198750, 7500, ["fire management", "indigenous", "savanna"]),
        ("Swiss DAC Facility", "Operate a direct air capture facility in Switzerland, permanently removing CO2 from the atmosphere and storing it geologically.", OffsetCategory.DIRECT_AIR_CAPTURE, "Switzerland", "Europe", VerificationStandard.CARBON_TRUST, 45.00, 5000, 1500, 67500, 225000, 2500, ["DAC", "permanent", "geological"]),
        ("Tanzania Reforestation", "Reforest 15,000 hectares of degraded hillside in Tanzania with indigenous tree species, creating jobs for local communities.", OffsetCategory.FORESTRY, "Tanzania", "Africa", VerificationStandard.Plan_VIVO, 10.25, 30000, 18000, 184500, 307500, 15000, ["reforestation", "jobs", "indigenous"]),
    ]

    projects = []
    for i, (name, desc, cat, country, continent, verification, price,
            available, sold, funding, goal, annual, tags) in enumerate(projects_data[:count]):
        start = datetime.now() - timedelta(days=random.randint(30, 365))
        end = start + timedelta(days=random.randint(365, 1095))

        projects.append(OffsetProject(
            project_id=generate_id("proj", i),
            name=name,
            description=desc[:120] + "...",
            long_description=desc,
            category=cat,
            status=ProjectStatus.ACTIVE if funding < goal else ProjectStatus.FUNDED,
            location=country,
            country=country,
            continent=continent,
            verification=verification,
            price_per_ton=price,
            total_tons_available=available,
            tons_sold=sold,
            total_funding_usd=funding,
            funding_goal_usd=goal,
            annual_reduction_tons=annual,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            partner_organization=f"{continent} Climate Initiative",
            tags=tags,
            sdg_goals=random.sample([7, 13, 15, 11, 6, 3, 8], k=random.randint(2, 4)),
            rating=round(random.uniform(3.5, 5.0), 1),
            review_count=random.randint(10, 200),
        ))

    return projects


def generate_mock_purchases(user_id: str, projects: List[OffsetProject]) -> List[OffsetPurchase]:
    """Generate mock purchase history for a user."""
    purchases = []
    selected = random.sample(projects, min(5, len(projects)))

    for i, proj in enumerate(selected):
        tons = round(random.uniform(0.5, 5.0), 2)
        purchases.append(OffsetPurchase(
            purchase_id=generate_id("purch", i),
            user_id=user_id,
            project_id=proj.project_id,
            project_name=proj.name,
            tons_purchased=tons,
            price_per_ton=proj.price_per_ton,
            total_cost=round(tons * proj.price_per_ton, 2),
            transaction_status=TransactionStatus.COMPLETED,
            purchase_date=(datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
            certificate_id=generate_id("cert", i),
        ))

    return purchases


def generate_user_portfolio(
    user_id: str, purchases: List[OffsetPurchase]
) -> UserOffsetPortfolio:
    """Generate user offset portfolio from purchases."""
    total_tons = sum(p.tons_purchased for p in purchases)
    total_spent = sum(p.total_cost for p in purchases)
    unique_projects = len(set(p.project_id for p in purchases))

    return UserOffsetPortfolio(
        user_id=user_id,
        total_tons_offset=round(total_tons, 2),
        total_spent_usd=round(total_spent, 2),
        projects_supported=unique_projects,
        purchases=purchases,
        certificates=[p.certificate_id for p in purchases],
    )


def generate_marketplace_stats(projects: List[OffsetProject]) -> MarketplaceStats:
    """Generate aggregate marketplace statistics."""
    total_sold = sum(p.tons_sold for p in projects)
    total_funding = sum(p.total_funding_usd for p in projects)
    active = sum(1 for p in projects if p.status == ProjectStatus.ACTIVE)

    cat_counts = {}
    for p in projects:
        cat = p.category.value
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    cont_counts = {}
    for p in projects:
        cont = p.continent
        cont_counts[cont] = cont_counts.get(cont, 0) + 1

    avg_price = sum(p.price_per_ton for p in projects) / len(projects) if projects else 0

    monthly = []
    for m in range(6):
        date = (datetime.now() - timedelta(days=30 * (5 - m))).strftime("%Y-%m")
        monthly.append({
            "period": date,
            "tons_sold": round(random.uniform(500, 3000), 0),
            "revenue": round(random.uniform(5000, 40000), 0),
        })

    return MarketplaceStats(
        total_projects=len(projects),
        active_projects=active,
        total_tons_sold=round(total_sold, 0),
        total_funding_usd=round(total_funding, 0),
        total_users=random.randint(800, 2500),
        avg_price_per_ton=round(avg_price, 2),
        top_categories=cat_counts,
        top_continents=cont_counts,
        monthly_sales=monthly,
    )


def generate_mock_reviews(project_id: str, count: int = 5) -> List[Dict]:
    """Generate mock reviews for a project."""
    reviewers = ["Alex R.", "Beatrix V.", "Chloe L.", "Daniel K.", "Elena R.", "Fujita S.", "Grace W.", "Hassan M."]
    comments = [
        "Excellent project with transparent reporting. Love seeing the community impact!",
        "Great verification standards. Happy to support this initiative.",
        "Strong project with measurable outcomes. Will definitely continue supporting.",
        "Impressive restoration work. The biodiversity metrics are encouraging.",
        "Solid project with good carbon accounting. Recommended for offset portfolios.",
        "Amazing community engagement. The local impact goes beyond just carbon.",
        "Well-managed project with clear milestones. Very satisfied with my contribution.",
        "Outstanding work on renewable energy deployment in underserved regions.",
    ]

    reviews = []
    for i in range(count):
        reviews.append({
            "reviewer": random.choice(reviewers),
            "rating": random.randint(3, 5),
            "comment": random.choice(comments),
            "date": (datetime.now() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
            "verified": random.random() > 0.3,
        })

    return reviews
