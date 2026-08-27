"""
Eco-Marketplace & Verified Carbon Offsets Service Layer
Encapsulates carbon credit purchasing, project search filtering, and portfolio accounting.
"""

from typing import List, Dict, Any, Optional
import logging

from eco_marketplace_offsets_types import (
    CarbonOffsetProject,
    OffsetProjectType,
    OffsetCertificationStandard,
    OffsetPurchaseTransaction,
    UserOffsetPortfolioSummary,
)
from eco_marketplace_offsets_db import (
    init_marketplace_offsets_db,
    get_all_offset_projects,
    purchase_carbon_offsets,
    get_user_offset_portfolio,
)

logger = logging.getLogger(__name__)


class EcoMarketplaceOffsetsService:
    def __init__(self, db_name: str = "eco_buddy.db"):
        self.db_name = db_name
        init_marketplace_offsets_db(self.db_name)

    def get_catalog_projects(
        self,
        project_type_filter: Optional[str] = None,
        certification_filter: Optional[str] = None
    ) -> List[CarbonOffsetProject]:
        """Retrieves active carbon offset projects with filtering."""
        projects = get_all_offset_projects(self.db_name)
        if project_type_filter and project_type_filter != "All":
            projects = [p for p in projects if p.project_type.value == project_type_filter]
        if certification_filter and certification_filter != "All":
            projects = [p for p in projects if p.certification_standard.value == certification_filter]
        return projects

    def buy_offsets(self, user_id: int, project_id: int, tonnes: float) -> Optional[OffsetPurchaseTransaction]:
        """Executes a verified carbon offset transaction."""
        if tonnes <= 0:
            return None
        return purchase_carbon_offsets(user_id, project_id, tonnes, self.db_name)

    def get_portfolio(self, user_id: int) -> Dict[str, Any]:
        """Fetches user's offset portfolio breakdown and certificate history."""
        return get_user_offset_portfolio(user_id, self.db_name)
