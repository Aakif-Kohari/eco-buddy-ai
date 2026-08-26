import pytest
from carbon_credits_market import CarbonCreditsMarketplace
from gamification_engine import GamificationEngine
from user_wallet_service import UserWalletService

class TestEcoMarketplace:

    def test_marketplace_initialization(self):
        market = CarbonCreditsMarketplace()
        projects = market.get_available_projects()
        
        assert len(projects) > 0
        assert projects[0]["price_per_ton_usd"] > 0

    def test_purchase_offset_success(self):
        market = CarbonCreditsMarketplace()
        project_id = market.get_available_projects()[0]["id"]
        
        initial_tons = market.get_available_projects()[0]["available_tons"]
        
        res = market.purchase_credits("USER1", project_id, 10)
        assert res["status"] == "success"
        assert res["receipt"]["tons_offset"] == 10
        
        # Verify deducted amount
        updated_project = next(p for p in market.get_available_projects() if p["id"] == project_id)
        assert updated_project["available_tons"] == initial_tons - 10

    def test_purchase_offset_insufficient(self):
        market = CarbonCreditsMarketplace()
        project_id = market.get_available_projects()[0]["id"]
        
        res = market.purchase_credits("USER1", project_id, 99999999) # Too many tons
        assert res["status"] == "error"

    def test_impact_ledger(self):
        market = CarbonCreditsMarketplace()
        project_id = market.get_available_projects()[0]["id"]
        
        market.purchase_credits("USER1", project_id, 5)
        market.purchase_credits("USER1", project_id, 15)
        
        impact = market.get_user_impact("USER1")
        assert impact["total_offset_tons"] == 20
        assert impact["total_spent_usd"] > 0

    def test_wallet_mint_and_spend(self):
        wallet = UserWalletService()
        
        bal = wallet.mint_coins("USER1", 50, "Recycled")
        assert bal == 50
        assert wallet.get_balance("USER1") == 50
        
        success = wallet.spend_coins("USER1", 20, "Premium avatar")
        assert success == True
        assert wallet.get_balance("USER1") == 30
        
        # Insufficient
        success2 = wallet.spend_coins("USER1", 100, "Should fail")
        assert success2 == False
        assert wallet.get_balance("USER1") == 30

    def test_gamification_xp_and_badges(self):
        engine = GamificationEngine()
        
        res = engine.award_xp("USER1", 120, "Testing")
        assert res["new_total_xp"] == 120
        assert "leveled_up" in res
        
        # Level up test (100 is sprout)
        assert res["current_level"] == "Sprout"
        
        badge_awarded = engine.award_badge("USER1", "B01")
        assert badge_awarded == True
        
        profile = engine.get_profile("USER1")
        assert "B01" in profile["badges_earned"]
        assert profile["xp"] > 120 # Because badge gives xp
