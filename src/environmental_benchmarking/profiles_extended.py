
from .datasets import REGIONAL_PROFILES_DATA

def load_regional_profiles() -> dict:
    """Loads massive dataset of regional profiles into ReferenceProfile objects."""
    from .models import ReferenceProfile, CategoryStat
    profiles = {}
    for code, data in REGIONAL_PROFILES_DATA.items():
        try:
            p = ReferenceProfile(
                id=code.lower(),
                name=f"{data['name']} Average",
                description=f"Average environmental footprint in {data['name']} ({data['region']}).",
                region_code=code,
                transport_stat=CategoryStat(**data['transport']),
                electricity_stat=CategoryStat(**data['electricity']),
                diet_stat=CategoryStat(**data['diet']),
                flights_stat=CategoryStat(**data['flights']),
                footprint_stat=CategoryStat(**data['footprint']),
                eco_score_stat=CategoryStat(**data['eco_score'])
            )
            p.validate_all()
            profiles[code.lower()] = p
        except Exception as e:
            print(f"Error loading profile {code}: {e}")
    return profiles

def get_default_profiles_extended() -> dict:
    from .profiles import get_default_profiles
    base = get_default_profiles()
    base.update(load_regional_profiles())
    return base
