"""
Unit and Integration Tests for Verified Carbon Offsets Marketplace Engine
"""

import unittest
import os
from src.carbon.eco_marketplace_offsets_types import (
    CarbonOffsetProject,
    OffsetProjectType,
    OffsetCertificationStandard,
)
from src.carbon.eco_marketplace_offsets_db import (
    init_marketplace_offsets_db,
    get_all_offset_projects,
    purchase_carbon_offsets,
    get_user_offset_portfolio,
)
from src.carbon.eco_marketplace_offsets_service import EcoMarketplaceOffsetsService

TEST_DB = "test_eco_marketplace_offsets.db"


class TestMarketplaceOffsetsEngine(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_marketplace_offsets_db(TEST_DB)
        self.service = EcoMarketplaceOffsetsService(db_name=TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_database_initialization_and_seeding(self):
        projects = self.service.get_catalog_projects()
        self.assertGreaterEqual(len(projects), 5)
        self.assertEqual(projects[0].certification_standard, OffsetCertificationStandard.GOLD_STANDARD)

    def test_offset_purchase(self):
        projects = self.service.get_catalog_projects()
        proj_id = projects[0].id

        tx = self.service.buy_offsets(user_id=1, project_id=proj_id, tonnes=2.5)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.tonnes_purchased, 2.5)
        self.assertTrue(tx.certificate_id.startswith("CERT-ECO-"))

    def test_portfolio_summary(self):
        projects = self.service.get_catalog_projects()
        proj_id = projects[0].id

        self.service.buy_offsets(user_id=2, project_id=proj_id, tonnes=5.0)
        portfolio = self.service.get_portfolio(user_id=2)

        self.assertEqual(portfolio["summary"].total_tonnes_retired, 5.0)
        self.assertEqual(portfolio["summary"].total_certificates, 1)
        self.assertEqual(len(portfolio["transactions"]), 1)


if __name__ == "__main__":
    unittest.main()
