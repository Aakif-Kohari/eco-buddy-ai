"""
Reward Catalog for EcoBuddy AI
Manages virtual rewards, items, and purchases.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import threading

logger = logging.getLogger(__name__)


class ItemType(Enum):
    """Types of items."""
    BADGE = "badge"
    TITLE = "title"
    THEME = "theme"
    AVATAR = "avatar"
    COSMETIC = "cosmetic"
    UTILITY = "utility"


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class CatalogItem:
    """Data class for a catalog item."""
    id: str
    name: str
    description: str
    type: ItemType
    rarity: ItemRarity
    price: int
    icon: str
    preview: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_limited: bool = False
    limited_until: Optional[str] = None


@dataclass
class PurchaseRecord:
    """Data class for a purchase record."""
    item_id: str
    user_id: int
    price: int
    purchased_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RewardCatalog:
    """
    Manages the virtual reward catalog.
    """
    
    def __init__(self):
        self._items: Dict[str, CatalogItem] = {}
        self._user_inventory: Dict[int, Dict[str, int]] = {}  # user_id -> {item_id: quantity}
        self._purchase_history: Dict[int, List[Dict[str, Any]]] = {}  # user_id -> [purchase records]
        self._lock = threading.Lock()
        
        # Load catalog items
        self._load_catalog_items()
        
        logger.info("RewardCatalog initialized")
    
    def _load_catalog_items(self) -> None:
        """Load catalog items."""
        items = [
            # Badges
            CatalogItem(
                id="badge_eco",
                name="Eco Badge",
                description="Show your commitment to sustainability",
                type=ItemType.BADGE,
                rarity=ItemRarity.COMMON,
                price=50,
                icon="🏅"
            ),
            CatalogItem(
                id="badge_green",
                name="Green Badge",
                description="Display your green lifestyle",
                type=ItemType.BADGE,
                rarity=ItemRarity.UNCOMMON,
                price=100,
                icon="🌿"
            ),
            CatalogItem(
                id="badge_sustainable",
                name="Sustainable Badge",
                description="You've embraced sustainable living",
                type=ItemType.BADGE,
                rarity=ItemRarity.RARE,
                price=200,
                icon="♻️"
            ),
            CatalogItem(
                id="badge_eco_warrior",
                name="Eco Warrior Badge",
                description="You're fighting for the planet",
                type=ItemType.BADGE,
                rarity=ItemRarity.EPIC,
                price=400,
                icon="⚔️"
            ),
            CatalogItem(
                id="badge_legend",
                name="Legendary Eco Badge",
                description="You're a true sustainability legend",
                type=ItemType.BADGE,
                rarity=ItemRarity.LEGENDARY,
                price=800,
                icon="👑"
            ),
            
            # Titles
            CatalogItem(
                id="title_eco_warrior",
                name="Eco Warrior",
                description="Earn the Eco Warrior title",
                type=ItemType.TITLE,
                rarity=ItemRarity.UNCOMMON,
                price=150,
                icon="⚔️"
            ),
            CatalogItem(
                id="title_green_guardian",
                name="Green Guardian",
                description="Earn the Green Guardian title",
                type=ItemType.TITLE,
                rarity=ItemRarity.RARE,
                price=250,
                icon="🛡️"
            ),
            CatalogItem(
                id="title_planet_saver",
                name="Planet Saver",
                description="Earn the Planet Saver title",
                type=ItemType.TITLE,
                rarity=ItemRarity.EPIC,
                price=500,
                icon="🌍"
            ),
            CatalogItem(
                id="title_eco_legend",
                name="Eco Legend",
                description="Earn the Eco Legend title",
                type=ItemType.TITLE,
                rarity=ItemRarity.LEGENDARY,
                price=1000,
                icon="🌟"
            ),
            
            # Themes
            CatalogItem(
                id="theme_dark",
                name="Dark Theme",
                description="Unlock the dark theme",
                type=ItemType.THEME,
                rarity=ItemRarity.COMMON,
                price=200,
                icon="🌙"
            ),
            CatalogItem(
                id="theme_nature",
                name="Nature Theme",
                description="Unlock the nature theme",
                type=ItemType.THEME,
                rarity=ItemRarity.UNCOMMON,
                price=300,
                icon="🌳"
            ),
            CatalogItem(
                id="theme_ocean",
                name="Ocean Theme",
                description="Unlock the ocean theme",
                type=ItemType.THEME,
                rarity=ItemRarity.RARE,
                price=400,
                icon="🌊"
            ),
            CatalogItem(
                id="theme_forest",
                name="Forest Theme",
                description="Unlock the forest theme",
                type=ItemType.THEME,
                rarity=ItemRarity.EPIC,
                price=600,
                icon="🌲"
            ),
            CatalogItem(
                id="theme_galaxy",
                name="Galaxy Theme",
                description="Unlock the galaxy theme",
                type=ItemType.THEME,
                rarity=ItemRarity.LEGENDARY,
                price=1000,
                icon="🌌"
            ),
            
            # Avatars
            CatalogItem(
                id="avatar_eco",
                name="Eco Avatar",
                description="Special eco avatar frame",
                type=ItemType.AVATAR,
                rarity=ItemRarity.UNCOMMON,
                price=400,
                icon="🧑‍🌾"
            ),
            CatalogItem(
                id="avatar_forest",
                name="Forest Avatar",
                description="Forest-themed avatar frame",
                type=ItemType.AVATAR,
                rarity=ItemRarity.RARE,
                price=500,
                icon="🌲"
            ),
            CatalogItem(
                id="avatar_ocean",
                name="Ocean Avatar",
                description="Ocean-themed avatar frame",
                type=ItemType.AVATAR,
                rarity=ItemRarity.EPIC,
                price=700,
                icon="🌊"
            ),
            CatalogItem(
                id="avatar_galaxy",
                name="Galaxy Avatar",
                description="Galaxy-themed avatar frame",
                type=ItemType.AVATAR,
                rarity=ItemRarity.LEGENDARY,
                price=1000,
                icon="🌌"
            ),
            
            # Cosmetics
            CatalogItem(
                id="cosmetic_sparkle",
                name="Sparkle Effect",
                description="Add sparkle effect to your profile",
                type=ItemType.COSMETIC,
                rarity=ItemRarity.RARE,
                price=300,
                icon="✨"
            ),
            CatalogItem(
                id="cosmetic_rainbow",
                name="Rainbow Effect",
                description="Add rainbow effect to your profile",
                type=ItemType.COSMETIC,
                rarity=ItemRarity.EPIC,
                price=500,
                icon="🌈"
            ),
            CatalogItem(
                id="cosmetic_star",
                name="Star Effect",
                description="Add star effect to your profile",
                type=ItemType.COSMETIC,
                rarity=ItemRarity.LEGENDARY,
                price=800,
                icon="⭐"
            ),
            
            # Utilities
            CatalogItem(
                id="utility_xp_boost",
                name="XP Boost",
                description="Double XP for 24 hours",
                type=ItemType.UTILITY,
                rarity=ItemRarity.RARE,
                price=250,
                icon="⚡",
                metadata={'duration_hours': 24, 'boost_multiplier': 2}
            ),
            CatalogItem(
                id="utility_coin_boost",
                name="Coin Boost",
                description="Double coins for 24 hours",
                type=ItemType.UTILITY,
                rarity=ItemRarity.RARE,
                price=250,
                icon="🪙",
                metadata={'duration_hours': 24, 'boost_multiplier': 2}
            ),
            CatalogItem(
                id="utility_streak_freeze",
                name="Streak Freeze",
                description="Protect your streak for 1 day",
                type=ItemType.UTILITY,
                rarity=ItemRarity.UNCOMMON,
                price=150,
                icon="🧊",
                metadata={'duration_days': 1}
            ),
            CatalogItem(
                id="utility_extra_quest",
                name="Extra Quest Slot",
                description="Unlock an additional active quest slot",
                type=ItemType.UTILITY,
                rarity=ItemRarity.EPIC,
                price=500,
                icon="📋",
                metadata={'extra_slots': 1}
            )
        ]
        
        for item in items:
            self._items[item.id] = item
        
        logger.info(f"Loaded {len(items)} catalog items")
    
    def get_item(self, item_id: str) -> Optional[CatalogItem]:
        """Get an item by ID."""
        return self._items.get(item_id)
    
    def get_all_items(
        self,
        item_type: Optional[ItemType] = None,
        rarity: Optional[ItemRarity] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CatalogItem]:
        """Get all items with optional filters."""
        items = list(self._items.values())
        
        if item_type:
            items = [i for i in items if i.type == item_type]
        if rarity:
            items = [i for i in items if i.rarity == rarity]
        
        # Sort by price
        items.sort(key=lambda i: i.price)
        
        return items[offset:offset + limit]
    
    def get_items_by_type(self, item_type: ItemType) -> List[CatalogItem]:
        """Get items by type."""
        return [i for i in self._items.values() if i.type == item_type]
    
    def get_items_by_rarity(self, rarity: ItemRarity) -> List[CatalogItem]:
        """Get items by rarity."""
        return [i for i in self._items.values() if i.rarity == rarity]
    
    def get_user_inventory(self, user_id: int) -> Dict[str, int]:
        """Get user's inventory."""
        return self._user_inventory.get(user_id, {})
    
    def get_user_items(self, user_id: int) -> List[CatalogItem]:
        """Get items owned by a user."""
        inventory = self.get_user_inventory(user_id)
        return [self._items[iid] for iid in inventory.keys() if iid in self._items]
    
    def get_user_item_count(self, user_id: int, item_id: str) -> int:
        """Get quantity of a specific item owned by user."""
        return self._user_inventory.get(user_id, {}).get(item_id, 0)
    
    def purchase_item(self, user_id: int, item_id: str) -> Dict[str, Any]:
        """
        Purchase an item for a user.
        
        Args:
            user_id: User ID
            item_id: Item ID
        
        Returns:
            Result dictionary with success status and message
        """
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return {
                    'success': False,
                    'message': f"Item {item_id} not found"
                }
            
            # Check if item is limited
            if item.is_limited and item.limited_until:
                from datetime import datetime
                if datetime.now() > datetime.fromisoformat(item.limited_until):
                    return {
                        'success': False,
                        'message': "This item is no longer available"
                    }
            
            # Check if user can afford the item
            user_coins = self._get_user_coins(user_id)
            if user_coins < item.price:
                return {
                    'success': False,
                    'message': f"Not enough coins. Need {item.price}, have {user_coins}"
                }
            
            # Check if item is a utility (can have multiple)
            if item.type != ItemType.UTILITY:
                # Check if user already owns this item
                if item_id in self._user_inventory.get(user_id, {}):
                    return {
                        'success': False,
                        'message': f"You already own {item.name}"
                    }
            
            # Deduct coins
            self._deduct_coins(user_id, item.price)
            
            # Add to inventory
            if user_id not in self._user_inventory:
                self._user_inventory[user_id] = {}
            
            if item.type == ItemType.UTILITY:
                # Utilities can stack
                self._user_inventory[user_id][item_id] = self._user_inventory[user_id].get(item_id, 0) + 1
            else:
                self._user_inventory[user_id][item_id] = 1
            
            # Record purchase
            if user_id not in self._purchase_history:
                self._purchase_history[user_id] = []
            
            from datetime import datetime
            self._purchase_history[user_id].append({
                'item_id': item_id,
                'item_name': item.name,
                'price': item.price,
                'purchased_at': datetime.now().isoformat()
            })
            
            logger.info(f"User {user_id} purchased {item.name} for {item.price} coins")
            
            # Create notification
            from .notification_manager import create_notification, NotificationType
            create_notification(
                user_id=user_id,
                type=NotificationType.ACHIEVEMENT,
                template_key='level_up',
                level="shop",
                xp=item.price
            )
            
            return {
                'success': True,
                'message': f"Successfully purchased {item.name}!",
                'item': item,
                'remaining_coins': self._get_user_coins(user_id)
            }
    
    def _get_user_coins(self, user_id: int) -> int:
        """Get user's coin balance."""
        try:
            from .gamification_v2 import get_user_coins
            return get_user_coins(user_id)
        except:
            return 0
    
    def _deduct_coins(self, user_id: int, amount: int) -> None:
        """Deduct coins from user."""
        try:
            from .gamification_v2 import add_coins
            add_coins(user_id, -amount)
        except Exception as e:
            logger.error(f"Failed to deduct coins: {e}")
    
    def use_item(self, user_id: int, item_id: str) -> Dict[str, Any]:
        """
        Use a utility item.
        
        Args:
            user_id: User ID
            item_id: Item ID
        
        Returns:
            Result dictionary
        """
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return {'success': False, 'message': "Item not found"}
            
            if item.type != ItemType.UTILITY:
                return {'success': False, 'message': "This item cannot be used"}
            
            if user_id not in self._user_inventory:
                return {'success': False, 'message': "You don't own this item"}
            
            if self._user_inventory[user_id].get(item_id, 0) <= 0:
                return {'success': False, 'message': "You don't have any of this item"}
            
            # Apply utility effect
            result = self._apply_utility_effect(user_id, item)
            
            if result['success']:
                # Remove one from inventory
                self._user_inventory[user_id][item_id] -= 1
                if self._user_inventory[user_id][item_id] <= 0:
                    del self._user_inventory[user_id][item_id]
                
                logger.info(f"User {user_id} used {item.name}")
            
            return result
    
    def _apply_utility_effect(self, user_id: int, item: CatalogItem) -> Dict[str, Any]:
        """Apply utility item effect."""
        metadata = item.metadata
        
        if 'boost_multiplier' in metadata:
            # XP or Coin boost
            boost_type = 'xp' if 'xp' in item.id else 'coins'
            multiplier = metadata['boost_multiplier']
            duration = metadata.get('duration_hours', 24)
            
            # Store boost in user session
            if 'user_boosts' not in st.session_state:
                st.session_state.user_boosts = {}
            
            from datetime import datetime, timedelta
            st.session_state.user_boosts[user_id] = {
                'type': boost_type,
                'multiplier': multiplier,
                'expires_at': (datetime.now() + timedelta(hours=duration)).isoformat()
            }
            
            return {
                'success': True,
                'message': f"{boost_type.title()} boost activated! {multiplier}x for {duration} hours"
            }
        
        elif 'duration_days' in metadata:
            # Streak freeze
            days = metadata['duration_days']
            
            if 'streak_freeze' not in st.session_state:
                st.session_state.streak_freeze = {}
            
            from datetime import datetime, timedelta
            st.session_state.streak_freeze[user_id] = {
                'active': True,
                'expires_at': (datetime.now() + timedelta(days=days)).isoformat()
            }
            
            return {
                'success': True,
                'message': f"Streak freeze activated for {days} day(s)!"
            }
        
        elif 'extra_slots' in metadata:
            # Extra quest slot
            slots = metadata['extra_slots']
            
            if 'extra_quest_slots' not in st.session_state:
                st.session_state.extra_quest_slots = {}
            
            st.session_state.extra_quest_slots[user_id] = st.session_state.extra_quest_slots.get(user_id, 0) + slots
            
            return {
                'success': True,
                'message': f"Unlocked {slots} extra quest slot(s)!"
            }
        
        return {'success': False, 'message': "Unknown utility effect"}
    
    def get_purchase_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's purchase history."""
        history = self._purchase_history.get(user_id, [])
        return history[-limit:][::-1]  # Most recent first
    
    def get_catalog_stats(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        stats = {
            'total_items': len(self._items),
            'by_type': {},
            'by_rarity': {},
            'total_purchases': 0,
            'unique_purchasers': len(self._purchase_history)
        }
        
        for item in self._items.values():
            stats['by_type'][item.type.value] = stats['by_type'].get(item.type.value, 0) + 1
            stats['by_rarity'][item.rarity.value] = stats['by_rarity'].get(item.rarity.value, 0) + 1
        
        for purchases in self._purchase_history.values():
            stats['total_purchases'] += len(purchases)
        
        return stats
    
    def get_popular_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most popular items based on purchases."""
        purchase_counts = {}
        
        for purchases in self._purchase_history.values():
            for purchase in purchases:
                item_id = purchase['item_id']
                purchase_counts[item_id] = purchase_counts.get(item_id, 0) + 1
        
        sorted_items = sorted(
            purchase_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        result = []
        for item_id, count in sorted_items:
            item = self._items.get(item_id)
            if item:
                result.append({
                    'item': item,
                    'purchase_count': count
                })
        
        return result


# Global reward catalog instance
_reward_catalog: Optional[RewardCatalog] = None
_reward_catalog_lock = threading.Lock()


def get_reward_catalog() -> RewardCatalog:
    """Get or create global reward catalog instance."""
    global _reward_catalog
    with _reward_catalog_lock:
        if _reward_catalog is None:
            _reward_catalog = RewardCatalog()
        return _reward_catalog


def purchase_item(user_id: int, item_id: str) -> Dict[str, Any]:
    """Convenience function to purchase an item."""
    catalog = get_reward_catalog()
    return catalog.purchase_item(user_id, item_id)


def use_item(user_id: int, item_id: str) -> Dict[str, Any]:
    """Convenience function to use an item."""
    catalog = get_reward_catalog()
    return catalog.use_item(user_id, item_id)


def get_user_inventory(user_id: int) -> Dict[str, int]:
    """Convenience function to get user inventory."""
    catalog = get_reward_catalog()
    return catalog.get_user_inventory(user_id)


def get_user_items(user_id: int) -> List[CatalogItem]:
    """Convenience function to get user items."""
    catalog = get_reward_catalog()
    return catalog.get_user_items(user_id)