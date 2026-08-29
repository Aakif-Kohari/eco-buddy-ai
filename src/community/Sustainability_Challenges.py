"""
Personalized Sustainability Recommendations System
With Challenges & Streaks Gamification Features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
import json
import pickle
from typing import Dict, List, Tuple, Optional, Set
import warnings
import random
from collections import defaultdict
warnings.filterwarnings('ignore')

class SustainabilityChallenges:
    """
    Manages sustainability challenges and tracking
    """
    
    def __init__(self):
        """Initialize challenges system"""
        self.challenges = {}
        self.user_challenges = defaultdict(lambda: defaultdict(dict))
        self.streaks = defaultdict(lambda: defaultdict(int))
        self.badges = defaultdict(set)
        self.challenge_templates = self._initialize_challenge_templates()
        self.leaderboard = defaultdict(int)
        
    def _initialize_challenge_templates(self) -> Dict:
        """Initialize challenge templates"""
        return {
            'daily': [
                {
                    'id': 'd1',
                    'name': 'Meatless Monday',
                    'description': 'Skip meat for one day',
                    'category': 'food',
                    'difficulty': 'easy',
                    'points': 10,
                    'co2_saved': 10,  # kg
                    'duration_days': 1,
                    'frequency': 'daily'
                },
                {
                    'id': 'd2',
                    'name': 'Walk More',
                    'description': 'Walk instead of driving for short trips',
                    'category': 'transport',
                    'difficulty': 'easy',
                    'points': 15,
                    'co2_saved': 5,
                    'duration_days': 1,
                    'frequency': 'daily'
                },
                {
                    'id': 'd3',
                    'name': 'Zero Waste Day',
                    'description': 'Produce zero waste for one day',
                    'category': 'waste',
                    'difficulty': 'medium',
                    'points': 25,
                    'co2_saved': 3,
                    'duration_days': 1,
                    'frequency': 'daily'
                }
            ],
            'weekly': [
                {
                    'id': 'w1',
                    'name': '7-Day Vegan Challenge',
                    'description': 'Follow a vegan diet for a week',
                    'category': 'food',
                    'difficulty': 'hard',
                    'points': 100,
                    'co2_saved': 70,
                    'duration_days': 7,
                    'frequency': 'weekly'
                },
                {
                    'id': 'w2',
                    'name': 'Public Transport Week',
                    'description': 'Use only public transport for a week',
                    'category': 'transport',
                    'difficulty': 'medium',
                    'points': 75,
                    'co2_saved': 50,
                    'duration_days': 7,
                    'frequency': 'weekly'
                },
                {
                    'id': 'w3',
                    'name': 'Energy Saving Week',
                    'description': 'Reduce energy consumption by 20%',
                    'category': 'energy',
                    'difficulty': 'medium',
                    'points': 80,
                    'co2_saved': 30,
                    'duration_days': 7,
                    'frequency': 'weekly'
                }
            ],
            'monthly': [
                {
                    'id': 'm1',
                    'name': '30-Day Zero Waste',
                    'description': 'Produce minimal waste for 30 days',
                    'category': 'waste',
                    'difficulty': 'hard',
                    'points': 300,
                    'co2_saved': 100,
                    'duration_days': 30,
                    'frequency': 'monthly'
                },
                {
                    'id': 'm2',
                    'name': 'Bike to Work Month',
                    'description': 'Commute by bike for a month',
                    'category': 'transport',
                    'difficulty': 'hard',
                    'points': 350,
                    'co2_saved': 150,
                    'duration_days': 30,
                    'frequency': 'monthly'
                }
            ]
        }
    
    def generate_daily_challenges(self, user_id: int, num_challenges: int = 3) -> List[Dict]:
        """
        Generate daily challenges for a user
        
        Args:
            user_id: User identifier
            num_challenges: Number of challenges to generate
            
        Returns:
            List of daily challenges
        """
        # Get user profile
        user_profile = self._get_user_profile(user_id)
        
        # Select relevant challenges
        available_challenges = self.challenge_templates['daily'].copy()
        
        # Filter based on user level and preferences
        user_level = self._get_user_level(user_id)
        if user_level < 5:
            # Beginners get easy challenges
            available_challenges = [c for c in available_challenges if c['difficulty'] == 'easy']
        elif user_level < 10:
            available_challenges = [c for c in available_challenges if c['difficulty'] != 'hard']
        
        # Prioritize challenges in areas where user needs improvement
        impact_areas = self._get_user_impact_areas(user_id)
        scored_challenges = []
        
        for challenge in available_challenges:
            score = impact_areas.get(challenge['category'], 0.5)
            # Add randomness
            score += random.uniform(-0.2, 0.2)
            scored_challenges.append((challenge, score))
        
        # Sort by score and select top challenges
        scored_challenges.sort(key=lambda x: x[1], reverse=True)
        selected = [c[0] for c in scored_challenges[:num_challenges]]
        
        # Add challenge details
        for challenge in selected:
            challenge['start_date'] = datetime.now().isoformat()
            challenge['end_date'] = (datetime.now() + timedelta(days=challenge['duration_days'])).isoformat()
            challenge['progress'] = 0
            challenge['completed'] = False
            
            # Store in user challenges
            self.user_challenges[user_id][challenge['id']] = challenge
        
        return selected
    
    def generate_weekly_challenges(self, user_id: int) -> List[Dict]:
        """Generate weekly challenges for a user"""
        user_profile = self._get_user_profile(user_id)
        user_level = self._get_user_level(user_id)
        
        available_challenges = self.challenge_templates['weekly'].copy()
        
        if user_level < 8:
            available_challenges = [c for c in available_challenges if c['difficulty'] != 'hard']
        
        # Select 2-3 weekly challenges
        num_challenges = random.randint(2, 3)
        selected = random.sample(available_challenges, min(num_challenges, len(available_challenges)))
        
        for challenge in selected:
            challenge['start_date'] = datetime.now().isoformat()
            challenge['end_date'] = (datetime.now() + timedelta(days=challenge['duration_days'])).isoformat()
            challenge['progress'] = 0
            challenge['completed'] = False
            
            self.user_challenges[user_id][challenge['id']] = challenge
        
        return selected
    
    def track_challenge_progress(self, user_id: int, challenge_id: str, 
                                progress_increment: float) -> Dict:
        """
        Track progress for a specific challenge
        
        Args:
            user_id: User identifier
            challenge_id: Challenge identifier
            progress_increment: Amount to increment progress
            
        Returns:
            Updated challenge status
        """
        if challenge_id not in self.user_challenges[user_id]:
            return {'error': 'Challenge not found'}
        
        challenge = self.user_challenges[user_id][challenge_id]
        
        if challenge['completed']:
            return {'error': 'Challenge already completed'}
        
        # Update progress
        challenge['progress'] = min(100, challenge['progress'] + progress_increment)
        
        # Check if completed
        if challenge['progress'] >= 100:
            challenge['completed'] = True
            challenge['completion_date'] = datetime.now().isoformat()
            
            # Award points
            self._award_points(user_id, challenge['points'])
            
            # Update streaks
            self._update_streak(user_id, challenge['category'])
            
            # Check for badges
            self._check_badges(user_id)
            
            # Update leaderboard
            self.leaderboard[user_id] += challenge['points']
        
        return challenge
    
    def _update_streak(self, user_id: int, category: str):
        """
        Update user's streak for a category
        
        Args:
            user_id: User identifier
            category: Challenge category
        """
        # Get current streak
        current_streak = self.streaks[user_id].get(category, 0)
        
        # Check if user completed challenges in this category recently
        today = datetime.now().date()
        category_challenges = [
            c for c in self.user_challenges[user_id].values() 
            if c['category'] == category and c['completed']
        ]
        
        if category_challenges:
            # Check if any challenge was completed today
            completed_today = any(
                datetime.fromisoformat(c['completion_date']).date() == today 
                for c in category_challenges
            )
            
            if completed_today:
                # Increase streak
                self.streaks[user_id][category] = current_streak + 1
            else:
                # Check if streak should be reset
                last_completion = max(
                    datetime.fromisoformat(c['completion_date']).date() 
                    for c in category_challenges
                )
                if (today - last_completion).days > 1:
                    self.streaks[user_id][category] = 0
    
    def _check_badges(self, user_id: int):
        """
        Check and award badges based on achievements
        
        Args:
            user_id: User identifier
        """
        # Get total points
        total_points = self.leaderboard[user_id]
        
        # Check streaks
        for category, streak_count in self.streaks[user_id].items():
            if streak_count >= 30:
                self.badges[user_id].add(f"Master of {category}")
            elif streak_count >= 14:
                self.badges[user_id].add(f"Champion of {category}")
            elif streak_count >= 7:
                self.badges[user_id].add(f"Enthusiast of {category}")
        
        # Points-based badges
        if total_points >= 1000:
            self.badges[user_id].add("Sustainability Legend")
        elif total_points >= 500:
            self.badges[user_id].add("Eco Warrior")
        elif total_points >= 200:
            self.badges[user_id].add("Green Champion")
        elif total_points >= 100:
            self.badges[user_id].add("Eco Beginner")
        
        # Challenge completion badges
        completed_challenges = len([c for c in self.user_challenges[user_id].values() if c['completed']])
        if completed_challenges >= 50:
            self.badges[user_id].add("Challenge Master")
        elif completed_challenges >= 25:
            self.badges[user_id].add("Challenge Expert")
        elif completed_challenges >= 10:
            self.badges[user_id].add("Challenge Starter")
    
    def _award_points(self, user_id: int, points: int):
        """Award points to user"""
        self.leaderboard[user_id] += points
    
    def get_user_streaks(self, user_id: int) -> Dict:
        """
        Get all streaks for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of streaks by category
        """
        return dict(self.streaks[user_id])
    
    def get_user_badges(self, user_id: int) -> List[str]:
        """
        Get all badges earned by a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of badges
        """
        return list(self.badges[user_id])
    
    def get_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """
        Get top users by points
        
        Args:
            top_n: Number of top users to return
            
        Returns:
            List of leaderboard entries
        """
        sorted_users = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
        return [
            {'user_id': user_id, 'points': points}
            for user_id, points in sorted_users[:top_n]
        ]
    
    def get_challenge_stats(self, user_id: int) -> Dict:
        """
        Get challenge statistics for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of challenge statistics
        """
        user_challenges = self.user_challenges[user_id]
        
        total = len(user_challenges)
        completed = len([c for c in user_challenges.values() if c['completed']])
        in_progress = len([c for c in user_challenges.values() if not c['completed'] and c['progress'] > 0])
        
        # Calculate completion rate by category
        category_stats = defaultdict(lambda: {'total': 0, 'completed': 0})
        for challenge in user_challenges.values():
            category = challenge['category']
            category_stats[category]['total'] += 1
            if challenge['completed']:
                category_stats[category]['completed'] += 1
        
        # Calculate completion rates
        for category in category_stats:
            category_stats[category]['completion_rate'] = (
                category_stats[category]['completed'] / category_stats[category]['total'] * 100
            )
        
        return {
            'total_challenges': total,
            'completed_challenges': completed,
            'in_progress_challenges': in_progress,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'category_stats': dict(category_stats),
            'total_points': self.leaderboard[user_id],
            'streaks': dict(self.streaks[user_id]),
            'badges': list(self.badges[user_id])
        }
    
    def _get_user_profile(self, user_id: int) -> Dict:
        """Mock user profile retrieval - should be replaced with actual data"""
        # In production, this would query the user database
        return {
            'user_id': user_id,
            'level': self._get_user_level(user_id),
            'preferences': {'difficulty': 'medium'},
            'sustainability_score': 50
        }
    
    def _get_user_level(self, user_id: int) -> int:
        """Calculate user level based on points"""
        points = self.leaderboard[user_id]
        if points >= 1000:
            return 15
        elif points >= 500:
            return 10
        elif points >= 200:
            return 7
        elif points >= 100:
            return 5
        elif points >= 50:
            return 3
        else:
            return 1
    
    def _get_user_impact_areas(self, user_id: int) -> Dict:
        """Get user's impact areas - should be replaced with actual data"""
        # Mock implementation
        return {
            'energy': random.uniform(0.3, 0.8),
            'transport': random.uniform(0.3, 0.8),
            'waste': random.uniform(0.3, 0.8),
            'water': random.uniform(0.3, 0.8),
            'food': random.uniform(0.3, 0.8)
        }


class EnhancedSustainabilityRecommender(SustainabilityRecommender):
    """
    Enhanced recommender with challenges and gamification
    """
    
    def __init__(self):
        """Initialize enhanced recommender"""
        super().__init__()
        self.challenges_system = SustainabilityChallenges()
        self.eco_actions = self._initialize_eco_actions()
        
    def _initialize_eco_actions(self) -> Dict:
        """Initialize everyday eco-actions for streaks"""
        return {
            'recycling': {'points': 5, 'co2_saved': 1, 'category': 'waste'},
            'composting': {'points': 10, 'co2_saved': 2, 'category': 'waste'},
            'using_reusable_bag': {'points': 3, 'co2_saved': 0.5, 'category': 'waste'},
            'turning_off_lights': {'points': 2, 'co2_saved': 0.3, 'category': 'energy'},
            'using_public_transport': {'points': 8, 'co2_saved': 3, 'category': 'transport'},
            'biking': {'points': 12, 'co2_saved': 4, 'category': 'transport'},
            'eating_plant_based': {'points': 15, 'co2_saved': 5, 'category': 'food'},
            'reducing_water_usage': {'points': 7, 'co2_saved': 1, 'category': 'water'},
            'using_energy_efficient_appliances': {'points': 10, 'co2_saved': 2, 'category': 'energy'},
            'buying_local_produce': {'points': 8, 'co2_saved': 3, 'category': 'food'}
        }
    
    def log_eco_action(self, user_id: int, action_name: str) -> Dict:
        """
        Log an eco-friendly action and update streaks
        
        Args:
            user_id: User identifier
            action_name: Name of the eco action
            
        Returns:
            Action result with points earned
        """
        if action_name not in self.eco_actions:
            return {'error': 'Action not recognized'}
        
        action = self.eco_actions[action_name]
        
        # Award points
        self.challenges_system._award_points(user_id, action['points'])
        
        # Update streak for category
        self.challenges_system._update_streak(user_id, action['category'])
        
        # Check for badges
        self.challenges_system._check_badges(user_id)
        
        return {
            'action': action_name,
            'points_earned': action['points'],
            'co2_saved': action['co2_saved'],
            'category': action['category'],
            'total_points': self.challenges_system.leaderboard[user_id]
        }
    
    def get_dashboard(self, user_id: int) -> Dict:
        """
        Get comprehensive dashboard for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Complete dashboard with recommendations, challenges, and stats
        """
        # Get recommendations
        recommendations = self.generate_recommendations(user_id, num_recommendations=5)
        
        # Get challenges
        daily_challenges = self.challenges_system.generate_daily_challenges(user_id)
        weekly_challenges = self.challenges_system.generate_weekly_challenges(user_id)
        
        # Get stats
        stats = self.challenges_system.get_challenge_stats(user_id)
        
        # Get impact summary
        impact = self.get_impact_summary(user_id)
        
        # Get leaderboard
        leaderboard = self.challenges_system.get_leaderboard(top_n=10)
        
        # Get user profile
        profile = self.get_user_profile(user_id)
        
        return {
            'user_profile': profile,
            'recommendations': recommendations,
            'daily_challenges': daily_challenges,
            'weekly_challenges': weekly_challenges,
            'impact_summary': impact,
            'challenge_stats': stats,
            'leaderboard': leaderboard
        }
    
    def complete_challenge(self, user_id: int, challenge_id: str) -> Dict:
        """
        Mark a challenge as completed
        
        Args:
            user_id: User identifier
            challenge_id: Challenge identifier
            
        Returns:
            Updated challenge status
        """
        return self.challenges_system.track_challenge_progress(
            user_id, challenge_id, 100
        )
    
    def get_streak_summary(self, user_id: int) -> Dict:
        """
        Get detailed streak summary for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Streak summary dictionary
        """
        streaks = self.challenges_system.get_user_streaks(user_id)
        badges = self.challenges_system.get_user_badges(user_id)
        stats = self.challenges_system.get_challenge_stats(user_id)
        
        # Calculate longest streak
        longest_streak = max(streaks.values()) if streaks else 0
        
        return {
            'current_streaks': streaks,
            'longest_streak': longest_streak,
            'badges': badges,
            'total_points': stats['total_points'],
            'completed_challenges': stats['completed_challenges'],
            'completion_rate': stats['completion_rate']
        }
    
    def save_challenges_state(self, filename: str = 'challenges_state.pkl'):
        """
        Save challenges system state to file
        
        Args:
            filename: File to save the state
        """
        with open(filename, 'wb') as f:
            pickle.dump({
                'challenges_system': self.challenges_system,
                'eco_actions': self.eco_actions
            }, f)
    
    def load_challenges_state(self, filename: str = 'challenges_state.pkl'):
        """
        Load challenges system state from file
        
        Args:
            filename: File to load the state from
        """
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            self.challenges_system = data['challenges_system']
            self.eco_actions = data['eco_actions']


# Example usage
def main():
    """Example usage of enhanced sustainability recommender"""
    
    # Initialize enhanced recommender
    recommender = EnhancedSustainabilityRecommender()
    
    # Test user ID
    user_id = 1
    
    # Log some eco actions
    print("=== Logging Eco Actions ===\n")
    actions = ['biking', 'recycling', 'turning_off_lights', 'eating_plant_based']
    
    for action in actions:
        result = recommender.log_eco_action(user_id, action)
        print(f"Action: {action}")
        print(f"  Points earned: {result['points_earned']}")
        print(f"  CO2 saved: {result['co2_saved']} kg")
        print(f"  Total points: {result['total_points']}\n")
    
    # Get dashboard
    print("=== User Dashboard ===\n")
    dashboard = recommender.get_dashboard(user_id)
    
    print(f"User ID: {user_id}")
    print(f"Sustainability Score: {dashboard['user_profile']['sustainability_score']:.2f}")
    print(f"Total Points: {dashboard['challenge_stats']['total_points']}")
    print(f"Completed Challenges: {dashboard['challenge_stats']['completed_challenges']}")
    print(f"Badges: {', '.join(dashboard['challenge_stats']['badges']) if dashboard['challenge_stats']['badges'] else 'None yet'}\n")
    
    # Display daily challenges
    print("=== Daily Challenges ===")
    for challenge in dashboard['daily_challenges']:
        print(f"• {challenge['name']}")
        print(f"  {challenge['description']}")
        print(f"  Points: {challenge['points']} | Difficulty: {challenge['difficulty']}\n")
    
    # Display recommendations
    print("=== Recommendations ===")
    for i, rec in enumerate(dashboard['recommendations'][:3], 1):
        print(f"{i}. {rec['action_name']}")
        print(f"   Cost: ${rec['cost']:.2f}")
        print(f"   CO2 Reduction: {rec['co2_reduction']:.1f} kg/year\n")
    
    # Get streak summary
    print("=== Streak Summary ===")
    streak_summary = recommender.get_streak_summary(user_id)
    print(f"Longest Streak: {streak_summary['longest_streak']} days")
    print("Current Streaks:")
    for category, days in streak_summary['current_streaks'].items():
        print(f"  {category}: {days} days")
    print(f"Badges: {', '.join(streak_summary['badges']) if streak_summary['badges'] else 'None yet'}\n")
    
    # Simulate completing a challenge
    print("=== Completing Challenge ===")
    if dashboard['daily_challenges']:
        challenge = dashboard['daily_challenges'][0]
        print(f"Completing: {challenge['name']}")
        
        # Simulate progress
        for progress in [25, 50, 75, 100]:
            result = recommender.challenges_system.track_challenge_progress(
                user_id, challenge['id'], 25
            )
            if 'error' not in result:
                print(f"  Progress: {result['progress']}%")
                if result['progress'] >= 100:
                    print("  ✓ Challenge completed!")
                    print(f"  Points earned: {challenge['points']}")
    
    # Show leaderboard
    print("\n=== Leaderboard ===")
    leaderboard = recommender.challenges_system.get_leaderboard()
    for i, entry in enumerate(leaderboard[:5], 1):
        print(f"{i}. User {entry['user_id']}: {entry['points']} points")
    
    # Save state
    recommender.save_challenges_state('challenges_state.pkl')
    print("\nChallenges state saved successfully!")


if __name__ == "__main__":
    main()
