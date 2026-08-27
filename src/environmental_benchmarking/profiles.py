"""
Pre-defined reference profiles for benchmarking.
"""
from .models import ReferenceProfile, CategoryStat

def get_default_profiles() -> dict:
    """Returns a dictionary of default reference profiles."""
    profiles = {}
    
    # 1. Global Average Profile
    profiles['global'] = ReferenceProfile(
        id='global',
        name='Global Average',
        description='Average environmental footprint worldwide.',
        region_code='GLO',
        transport_stat=CategoryStat(mean=1200, median=900, std_dev=800, min_val=0, max_val=10000, p10=100, p25=300, p75=1500, p90=2500),
        electricity_stat=CategoryStat(mean=3000, median=2500, std_dev=2000, min_val=0, max_val=20000, p10=500, p25=1200, p75=4000, p90=6000),
        diet_stat=CategoryStat(mean=1500, median=1400, std_dev=500, min_val=500, max_val=4000, p10=800, p25=1100, p75=1800, p90=2200),
        flights_stat=CategoryStat(mean=1, median=0, std_dev=2, min_val=0, max_val=50, p10=0, p25=0, p75=1, p90=3),
        footprint_stat=CategoryStat(mean=4500, median=4000, std_dev=2500, min_val=500, max_val=30000, p10=1500, p25=2500, p75=6000, p90=8500),
        eco_score_stat=CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=20, p25=35, p75=65, p90=80)
    )
    
    # 2. US Average (High Consumption)
    profiles['us'] = ReferenceProfile(
        id='us',
        name='United States Average',
        description='Average environmental footprint in the US.',
        region_code='US',
        transport_stat=CategoryStat(mean=4500, median=4000, std_dev=2000, min_val=0, max_val=20000, p10=1000, p25=2500, p75=6000, p90=8000),
        electricity_stat=CategoryStat(mean=10000, median=9000, std_dev=4000, min_val=0, max_val=30000, p10=3000, p25=6000, p75=12000, p90=16000),
        diet_stat=CategoryStat(mean=2500, median=2400, std_dev=800, min_val=800, max_val=6000, p10=1200, p25=1800, p75=3000, p90=3800),
        flights_stat=CategoryStat(mean=3, median=2, std_dev=4, min_val=0, max_val=100, p10=0, p25=0, p75=4, p90=8),
        footprint_stat=CategoryStat(mean=15000, median=14000, std_dev=6000, min_val=2000, max_val=60000, p10=6000, p25=10000, p75=19000, p90=24000),
        eco_score_stat=CategoryStat(mean=35, median=35, std_dev=15, min_val=0, max_val=100, p10=15, p25=25, p75=45, p90=60)
    )
    
    # 3. EU Average
    profiles['eu'] = ReferenceProfile(
        id='eu',
        name='European Union Average',
        description='Average environmental footprint in the EU.',
        region_code='EU',
        transport_stat=CategoryStat(mean=2000, median=1800, std_dev=1200, min_val=0, max_val=12000, p10=400, p25=1000, p75=2800, p90=3800),
        electricity_stat=CategoryStat(mean=4000, median=3500, std_dev=1800, min_val=0, max_val=15000, p10=1500, p25=2500, p75=5000, p90=6500),
        diet_stat=CategoryStat(mean=1800, median=1700, std_dev=600, min_val=600, max_val=4500, p10=1000, p25=1400, p75=2200, p90=2800),
        flights_stat=CategoryStat(mean=2, median=1, std_dev=3, min_val=0, max_val=50, p10=0, p25=0, p75=3, p90=6),
        footprint_stat=CategoryStat(mean=7000, median=6500, std_dev=3000, min_val=1500, max_val=25000, p10=3000, p25=4500, p75=9000, p90=12000),
        eco_score_stat=CategoryStat(mean=55, median=55, std_dev=18, min_val=0, max_val=100, p10=30, p25=42, p75=68, p90=82)
    )

    # 4. India Average (Developing Nation Example)
    profiles['in'] = ReferenceProfile(
        id='in',
        name='India Average',
        description='Average environmental footprint in India.',
        region_code='IN',
        transport_stat=CategoryStat(mean=600, median=400, std_dev=500, min_val=0, max_val=5000, p10=50, p25=150, p75=800, p90=1200),
        electricity_stat=CategoryStat(mean=900, median=700, std_dev=600, min_val=0, max_val=8000, p10=100, p25=300, p75=1200, p90=1800),
        diet_stat=CategoryStat(mean=900, median=800, std_dev=300, min_val=300, max_val=2500, p10=400, p25=600, p75=1100, p90=1400),
        flights_stat=CategoryStat(mean=0.2, median=0, std_dev=0.8, min_val=0, max_val=20, p10=0, p25=0, p75=0, p90=1),
        footprint_stat=CategoryStat(mean=1800, median=1500, std_dev=1000, min_val=200, max_val=15000, p10=500, p25=900, p75=2200, p90=3000),
        eco_score_stat=CategoryStat(mean=65, median=65, std_dev=15, min_val=0, max_val=100, p10=45, p25=55, p75=75, p90=85)
    )

    # 5. Sustainable Target (Paris Agreement)
    profiles['target'] = ReferenceProfile(
        id='target',
        name='Sustainable Target (Paris Agreement)',
        description='Target footprint to meet global climate goals (1.5C pathway).',
        region_code='TGT',
        transport_stat=CategoryStat(mean=500, median=400, std_dev=300, min_val=0, max_val=3000, p10=100, p25=200, p75=700, p90=1000),
        electricity_stat=CategoryStat(mean=1000, median=800, std_dev=500, min_val=0, max_val=5000, p10=200, p25=400, p75=1200, p90=1800),
        diet_stat=CategoryStat(mean=800, median=750, std_dev=300, min_val=400, max_val=2000, p10=500, p25=600, p75=1000, p90=1300),
        flights_stat=CategoryStat(mean=0, median=0, std_dev=0.5, min_val=0, max_val=2, p10=0, p25=0, p75=0, p90=1),
        footprint_stat=CategoryStat(mean=2000, median=1800, std_dev=800, min_val=500, max_val=6000, p10=800, p25=1200, p75=2500, p90=3200),
        eco_score_stat=CategoryStat(mean=85, median=85, std_dev=10, min_val=0, max_val=100, p10=70, p25=80, p75=92, p90=98)
    )

    # 6. High Income Eco-Conscious (Aspirational Profile)
    profiles['eco_conscious'] = ReferenceProfile(
        id='eco_conscious',
        name='Eco-Conscious (High Income)',
        description='Average for individuals actively reducing footprints in developed nations.',
        region_code='ECO',
        transport_stat=CategoryStat(mean=1200, median=1000, std_dev=800, min_val=0, max_val=6000, p10=200, p25=500, p75=1500, p90=2200),
        electricity_stat=CategoryStat(mean=2500, median=2000, std_dev=1500, min_val=0, max_val=10000, p10=500, p25=1000, p75=3000, p90=4500),
        diet_stat=CategoryStat(mean=1200, median=1100, std_dev=400, min_val=500, max_val=3000, p10=600, p25=900, p75=1400, p90=1800),
        flights_stat=CategoryStat(mean=1, median=0, std_dev=1, min_val=0, max_val=10, p10=0, p25=0, p75=1, p90=2),
        footprint_stat=CategoryStat(mean=4500, median=4000, std_dev=2000, min_val=1000, max_val=15000, p10=2000, p25=3000, p75=5500, p90=7000),
        eco_score_stat=CategoryStat(mean=75, median=75, std_dev=12, min_val=0, max_val=100, p10=60, p25=68, p75=82, p90=90)
    )
    
    # 7. China Average (High industry, growing consumer)
    profiles['cn'] = ReferenceProfile(
        id='cn',
        name='China Average',
        description='Average environmental footprint in China.',
        region_code='CN',
        transport_stat=CategoryStat(mean=1500, median=1200, std_dev=1000, min_val=0, max_val=8000, p10=200, p25=500, p75=2000, p90=3000),
        electricity_stat=CategoryStat(mean=4500, median=4000, std_dev=2500, min_val=0, max_val=15000, p10=1000, p25=2000, p75=6000, p90=8000),
        diet_stat=CategoryStat(mean=1600, median=1500, std_dev=500, min_val=500, max_val=4000, p10=800, p25=1200, p75=2000, p90=2400),
        flights_stat=CategoryStat(mean=0.5, median=0, std_dev=1.5, min_val=0, max_val=20, p10=0, p25=0, p75=0, p90=2),
        footprint_stat=CategoryStat(mean=8000, median=7500, std_dev=4000, min_val=1000, max_val=25000, p10=2500, p25=4500, p75=10500, p90=13500),
        eco_score_stat=CategoryStat(mean=50, median=50, std_dev=20, min_val=0, max_val=100, p10=25, p25=35, p75=65, p90=75)
    )

    for p in profiles.values():
        p.validate_all()
            
    return profiles
